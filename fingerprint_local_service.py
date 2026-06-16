#!/usr/bin/env python3
"""
Local fingerprint capture service for the school browser UI.

Run on the enrollment PC (same machine as the USB scanner):
    python fingerprint_local_service.py

Default URL: http://127.0.0.1:9765

Supports pyfingerprint (R307 / ZFM modules on serial/USB). Without hardware,
returns a clear error so the UI can prompt to connect a scanner.
"""

from __future__ import annotations

import base64
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

PORT = int(os.environ.get('FINGERPRINT_SERVICE_PORT', '9765'))
ALLOW_SIMULATE = os.environ.get('FINGERPRINT_ALLOW_SIMULATE', '').lower() in ('1', 'true', 'yes')


@app.after_request
def _cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return resp


def _capture_with_pyfingerprint():
    try:
        from pyfingerprint.pyfingerprint import PyFingerprint
    except ImportError:
        return None, 'pyfingerprint is not installed. Run: pip install pyfingerprint'

    port = os.environ.get('FINGERPRINT_SERIAL_PORT', '')
    baud = int(os.environ.get('FINGERPRINT_SERIAL_BAUD', '57600'))
    address = int(os.environ.get('FINGERPRINT_MODULE_ADDRESS', '0xFFFFFFFF'), 0)
    password = int(os.environ.get('FINGERPRINT_MODULE_PASSWORD', '0x00000000'), 0)

    kwargs = {'baudRate': baud, 'address': address, 'password': password}
    if port:
        kwargs['port'] = port

    try:
        sensor = PyFingerprint(**kwargs)
        if not sensor.verifyPassword():
            return None, 'Fingerprint sensor password is incorrect.'
        sensor.readImage()
        sensor.convertImage(0x01)
        result = sensor.createTemplate()
        if result != 0:
            return None, 'Could not create fingerprint template. Try again with a clean finger.'
        template = sensor.downloadCharacteristics(0x01)
        raw = bytes(template)
        return {
            'template_base64': base64.b64encode(raw).decode('ascii'),
            'template_format': 'pyfingerprint_v1',
            'quality_score': 85,
            'device_id': port or 'pyfingerprint',
        }, None
    except Exception as exc:
        return None, f'Scanner error: {exc}'


def _simulate_capture():
    raw = secrets.token_bytes(256)
    return {
        'template_base64': base64.b64encode(raw).decode('ascii'),
        'template_format': 'simulated_v1',
        'quality_score': 50,
        'device_id': 'simulator',
    }, None


@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        return '', 204
    device = 'unknown'
    ready = False
    try:
        from pyfingerprint.pyfingerprint import PyFingerprint
        device = 'pyfingerprint'
        ready = True
    except ImportError:
        device = 'simulator' if ALLOW_SIMULATE else 'none'
        ready = ALLOW_SIMULATE
    return jsonify({
        'ok': True,
        'ready': ready,
        'device': device,
        'simulate': ALLOW_SIMULATE,
        'port': PORT,
    })


@app.route('/api/capture', methods=['POST', 'OPTIONS'])
def capture():
    if request.method == 'OPTIONS':
        return '', 204
    payload, err = _capture_with_pyfingerprint()
    if payload:
        return jsonify({'success': True, **payload})
    if ALLOW_SIMULATE:
        payload, err = _simulate_capture()
        if payload:
            return jsonify({'success': True, **payload, 'simulated': True})
    return jsonify({
        'success': False,
        'message': err or 'Fingerprint scanner not available.',
        'hint': 'Connect a USB scanner, install pyfingerprint, and set FINGERPRINT_SERIAL_PORT if needed.',
    }), 503


if __name__ == '__main__':
    print(f'Fingerprint capture service on http://127.0.0.1:{PORT}')
    if ALLOW_SIMULATE:
        print('Simulation mode enabled (FINGERPRINT_ALLOW_SIMULATE=1)')
    app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True)
