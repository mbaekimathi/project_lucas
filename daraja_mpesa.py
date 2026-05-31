"""
Safaricom Daraja (M-Pesa) API client — STK Push, query, status, balance, reversal, B2C.

Secrets and API config load from environment variables (.env.local locally, .env on server).
Only the parent-portal on/off toggle is stored in integration_settings (mpesa_daraja).
"""
from __future__ import annotations

import base64
import os
import re
import time
from datetime import datetime
from typing import Any, Optional

import requests

DARAJA_SANDBOX_BASE = 'https://sandbox.safaricom.co.ke'
DARAJA_PRODUCTION_BASE = 'https://api.safaricom.co.ke'

# Keys that must never be read from the database (env only).
_DARAJA_SECRET_KEYS = frozenset({
    'consumer_key', 'consumer_secret', 'passkey', 'shortcode', 'till_number',
    'initiator_name', 'security_credential', 'b2c_shortcode',
    'environment', 'timeout_url', 'result_url', 'validation_url', 'confirmation_url',
    'account_balance_initiator', 'account_balance_security_credential',
    'stk_callback_path',
})

_token_cache: dict[str, Any] = {'token': None, 'expires_at': 0}


def _env(key: str, default: str = '') -> str:
    return (os.environ.get(key) or default).strip()


def normalize_mpesa_account_presets(raw) -> list:
    """School M-Pesa paybill/till profiles stored in integration_settings (not secrets)."""
    if not isinstance(raw, list):
        return []
    out = []
    seen_ids = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        label = (item.get('label') or '').strip()
        if not label:
            continue
        mt = (item.get('mpesa_type') or 'paybill').strip().lower()
        if mt not in ('paybill', 'till'):
            mt = 'paybill'
        acct_id = (item.get('id') or '').strip() or f'mpesa-{i + 1}'
        if acct_id in seen_ids:
            acct_id = f'{acct_id}-{i + 1}'
        seen_ids.add(acct_id)
        biz = (item.get('business_name') or '').strip()
        paybill = (item.get('paybill_number') or item.get('mpesa_shortcode') or '').strip()
        till = (item.get('till_number') or item.get('account_number') or '').strip()
        ref_mode = (item.get('paybill_ref_mode') or 'admission').strip().lower()
        if ref_mode not in ('admission', 'account_number'):
            ref_mode = 'admission'
        paybill_acct = (item.get('paybill_account_number') or '').strip()
        if mt != 'paybill':
            ref_mode = 'admission'
            paybill_acct = ''
        elif ref_mode == 'account_number' and not paybill_acct:
            ref_mode = 'admission'
        out.append({
            'id': acct_id,
            'label': label,
            'mpesa_type': mt,
            'business_name': biz,
            'paybill_number': paybill if mt == 'paybill' else '',
            'till_number': till if mt == 'till' else '',
            'paybill_ref_mode': ref_mode if mt == 'paybill' else 'admission',
            'paybill_account_number': paybill_acct if mt == 'paybill' and ref_mode == 'account_number' else '',
        })
    return out


def mpesa_daraja_ui_payload(enabled: bool = False, mpesa_accounts=None) -> dict:
    """JSON stored in integration_settings — toggle + school M-Pesa account profiles."""
    return {
        'enabled': bool(enabled),
        'mpesa_accounts': normalize_mpesa_account_presets(mpesa_accounts or []),
    }


def load_daraja_config_from_env() -> dict:
    """All Daraja configuration from environment variables."""
    env_name = (_env('DARAJA_ENVIRONMENT') or 'sandbox').lower()
    if env_name not in ('sandbox', 'production'):
        env_name = 'sandbox'
    return {
        'environment': env_name,
        'consumer_key': _env('DARAJA_CONSUMER_KEY'),
        'consumer_secret': _env('DARAJA_CONSUMER_SECRET'),
        'passkey': _env('DARAJA_PASSKEY'),
        'shortcode': _env('DARAJA_SHORTCODE'),
        'till_number': _env('DARAJA_TILL_NUMBER'),
        'initiator_name': _env('DARAJA_INITIATOR_NAME') or 'testapi',
        'security_credential': _env('DARAJA_SECURITY_CREDENTIAL'),
        'b2c_shortcode': _env('DARAJA_B2C_SHORTCODE') or _env('DARAJA_SHORTCODE'),
        'stk_callback_path': _env('DARAJA_STK_CALLBACK_PATH') or '/api/mpesa/stk-callback',
        'stk_callback_url': _env('DARAJA_STK_CALLBACK_URL'),
        'callback_base_url': _env('DARAJA_CALLBACK_BASE_URL'),
        'timeout_url': _env('DARAJA_TIMEOUT_URL'),
        'result_url': _env('DARAJA_RESULT_URL'),
        'validation_url': _env('DARAJA_VALIDATION_URL'),
        'confirmation_url': _env('DARAJA_CONFIRMATION_URL'),
        'account_balance_initiator': _env('DARAJA_BALANCE_INITIATOR') or _env('DARAJA_INITIATOR_NAME') or 'testapi',
        'account_balance_security_credential': _env('DARAJA_BALANCE_SECURITY_CREDENTIAL') or _env('DARAJA_SECURITY_CREDENTIAL'),
    }


def merge_daraja_settings(stored: Optional[dict]) -> dict:
    """
    Effective runtime settings: secrets from .env, enabled flag from DB (UI toggle).
    Legacy secret keys in stored JSON are ignored.
    """
    ui = stored if isinstance(stored, dict) else {}
    enabled = bool(ui.get('enabled'))
    merged = load_daraja_config_from_env()
    merged['enabled'] = enabled
    merged['mpesa_accounts'] = normalize_mpesa_account_presets(ui.get('mpesa_accounts'))
    return merged


def credentials_configured(settings: dict) -> bool:
    """True when required STK credentials are present in env."""
    return bool(
        (settings.get('consumer_key') or '').strip()
        and (settings.get('consumer_secret') or '').strip()
        and (settings.get('passkey') or '').strip()
    )


def daraja_env_status() -> list[dict[str, Any]]:
    """Status rows for the integration settings UI (no secret values)."""
    rows = [
        ('DARAJA_CONSUMER_KEY', 'consumer_key', 'Consumer key', True),
        ('DARAJA_CONSUMER_SECRET', 'consumer_secret', 'Consumer secret', True),
        ('DARAJA_PASSKEY', 'passkey', 'Lipa Na M-Pesa passkey', True),
        ('DARAJA_ENVIRONMENT', 'environment', 'Environment (sandbox / production)', False),
        ('DARAJA_SHORTCODE', 'shortcode', 'Default paybill shortcode (fallback)', False),
        ('DARAJA_INITIATOR_NAME', 'initiator_name', 'Initiator name (advanced APIs)', False),
        ('DARAJA_SECURITY_CREDENTIAL', 'security_credential', 'Security credential (advanced)', False),
        ('DARAJA_B2C_SHORTCODE', 'b2c_shortcode', 'B2C shortcode', False),
        ('DARAJA_STK_CALLBACK_URL', 'stk_callback_url', 'STK callback URL (public HTTPS)', False),
        ('DARAJA_CALLBACK_BASE_URL', 'callback_base_url', 'Public site URL for local STK callback', False),
        ('DARAJA_RESULT_URL', 'result_url', 'Result URL (async callbacks)', False),
        ('DARAJA_TIMEOUT_URL', 'timeout_url', 'Queue timeout URL', False),
    ]
    cfg = load_daraja_config_from_env()
    out = []
    for env_var, key, label, required in rows:
        val = (cfg.get(key) or '').strip()
        if key == 'environment':
            configured = bool(val)
            display = val or 'sandbox (default)'
        else:
            configured = bool(val)
            display = 'Set in .env' if configured else 'Not set'
        out.append({
            'env_var': env_var,
            'label': label,
            'required': required,
            'configured': configured,
            'display': display,
        })
    return out


def _is_local_callback_url(url: str) -> bool:
    lower = (url or '').strip().lower()
    return '127.0.0.1' in lower or 'localhost' in lower


def is_valid_daraja_callback_url(url: str) -> bool:
    """Daraja STK CallBackURL must be HTTPS and not localhost."""
    u = (url or '').strip()
    if not u.lower().startswith('https://'):
        return False
    if _is_local_callback_url(u):
        return False
    return len(u) > 16


def resolve_stk_callback_url(settings: dict, fallback_url: str = '') -> tuple[Optional[str], Optional[str]]:
    """
    Resolve the STK CallBackURL sent to Daraja.

    Safaricom rejects http://127.0.0.1 — even in sandbox. When you run Flask locally,
    set DARAJA_STK_CALLBACK_URL (or DARAJA_CALLBACK_BASE_URL) to your school's public
    HTTPS domain. Register that path in the Daraja app. Payment status is confirmed
    via STK query polling on the page — no tunnel required.
    """
    path = (settings.get('stk_callback_path') or '/api/mpesa/stk-callback').strip()
    if path and not path.startswith('/'):
        path = '/' + path

    explicit = (settings.get('stk_callback_url') or _env('DARAJA_STK_CALLBACK_URL') or '').strip()
    if explicit and is_valid_daraja_callback_url(explicit):
        return explicit, None

    candidates: list[str] = []

    callback_base = (_env('DARAJA_CALLBACK_BASE_URL') or '').strip().rstrip('/')
    if callback_base:
        candidates.append(callback_base + path)

    app_domain = (_env('APP_DOMAIN') or '').strip().rstrip('/')
    if app_domain and not _is_local_callback_url(app_domain):
        candidates.append(app_domain + path)

    result_url = (settings.get('result_url') or '').strip()
    if result_url and not _is_local_callback_url(result_url):
        candidates.append(result_url)

    fallback = (fallback_url or '').strip()
    if fallback and not _is_local_callback_url(fallback):
        candidates.append(fallback)

    for url in candidates:
        if is_valid_daraja_callback_url(url):
            return url, None

    return None, (
        'Set DARAJA_STK_CALLBACK_URL in .env.local to your school HTTPS callback, e.g. '
        'https://kanyakine.kwetudeliveries.com/api/mpesa/stk-callback '
        '(register it in Daraja → Lipa Na M-Pesa). Local testing uses status polling — localhost cannot be the callback.'
    )


def daraja_base_url(settings: dict) -> str:
    env = (settings.get('environment') or 'sandbox').lower()
    return DARAJA_PRODUCTION_BASE if env == 'production' else DARAJA_SANDBOX_BASE


def normalize_msisdn(phone: str) -> tuple[Optional[str], Optional[str]]:
    """Return (2547XXXXXXXX, error)."""
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('0') and len(digits) >= 10:
        digits = '254' + digits[1:]
    elif digits.startswith('7') and len(digits) == 9:
        digits = '254' + digits
    elif digits.startswith('254'):
        pass
    elif len(digits) == 9 and digits[0] == '7':
        digits = '254' + digits
    if not re.match(r'^2547\d{8}$', digits):
        return None, 'Enter a valid M-Pesa number (e.g. 0712 345 678).'
    return digits, None


def stk_password(shortcode: str, passkey: str) -> tuple[str, str]:
    """Lipa Na M-Pesa Password = Base64(BusinessShortCode + Passkey + Timestamp)."""
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    data = f'{shortcode}{passkey}{ts}'
    pwd = base64.b64encode(data.encode('utf-8')).decode('utf-8')
    return pwd, ts


def sandbox_stk_shortcode(settings: dict, business_shortcode: str) -> str:
    """Sandbox STK only works with the app shortcode (usually 174379), not live paybills."""
    if (settings.get('environment') or 'sandbox').lower() != 'sandbox':
        return business_shortcode
    return (settings.get('shortcode') or business_shortcode or '174379').strip()


def get_access_token(settings: dict) -> tuple[Optional[str], Optional[str]]:
    key = settings.get('consumer_key') or ''
    secret = settings.get('consumer_secret') or ''
    if not key or not secret:
        return None, 'Daraja Consumer Key and Secret are not configured in .env.'
    cache_key = f"{key[:8]}:{settings.get('environment')}"
    now = time.time()
    if (
        _token_cache.get('key') == cache_key
        and _token_cache.get('token')
        and _token_cache.get('expires_at', 0) > now + 30
    ):
        return _token_cache['token'], None
    url = f"{daraja_base_url(settings)}/oauth/v1/generate?grant_type=client_credentials"
    try:
        r = requests.get(url, auth=(key, secret), timeout=30)
        data = r.json() if r.content else {}
        if r.status_code != 200:
            return None, data.get('errorMessage') or data.get('error_description') or f'OAuth failed ({r.status_code}).'
        token = data.get('access_token')
        if not token:
            return None, 'No access token returned from Daraja.'
        expires_in = int(data.get('expires_in') or 3500)
        _token_cache.update({
            'key': cache_key,
            'token': token,
            'expires_at': now + expires_in,
        })
        return token, None
    except requests.RequestException as e:
        return None, f'Could not reach Daraja OAuth: {e}'


def stk_push(
    settings: dict,
    *,
    phone: str,
    amount: float,
    account_reference: str,
    transaction_desc: str,
    callback_url: str,
    business_shortcode: str,
    transaction_type: str = 'CustomerPayBillOnline',
    party_b_shortcode: Optional[str] = None,
) -> dict:
    """Lipa Na M-Pesa STK Push."""
    msisdn, err = normalize_msisdn(phone)
    if err:
        return {'ok': False, 'error': err}
    try:
        amt = int(round(float(amount)))
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Invalid amount.'}
    if amt < 1:
        return {'ok': False, 'error': 'Amount must be at least KES 1.'}
    if amt > 300000:
        return {'ok': False, 'error': 'Amount exceeds M-Pesa STK limit.'}

    shortcode = sandbox_stk_shortcode(settings, (business_shortcode or settings.get('shortcode') or '').strip())
    party_b = sandbox_stk_shortcode(settings, (party_b_shortcode or shortcode or '').strip())
    passkey = (settings.get('passkey') or '').strip()
    if not shortcode or not passkey:
        return {'ok': False, 'error': 'M-Pesa paybill/till or Daraja passkey is not configured in .env.'}

    token, terr = get_access_token(settings)
    if terr:
        return {'ok': False, 'error': terr}

    pwd, ts = stk_password(shortcode, passkey)
    ref = (account_reference or '')[:12]
    desc = (transaction_desc or 'Payment')[:13]
    payload = {
        'BusinessShortCode': shortcode,
        'Password': pwd,
        'Timestamp': ts,
        'TransactionType': transaction_type,
        'Amount': amt,
        'PartyA': msisdn,
        'PartyB': party_b,
        'PhoneNumber': msisdn,
        'CallBackURL': callback_url,
        'AccountReference': ref,
        'TransactionDesc': desc,
    }
    url = f"{daraja_base_url(settings)}/mpesa/stkpush/v1/processrequest"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=45,
        )
        data = r.json() if r.content else {}
        if r.status_code != 200:
            return {
                'ok': False,
                'error': data.get('errorMessage') or data.get('error_description') or f'STK push failed ({r.status_code}).',
                'raw': data,
            }
        code = str(data.get('ResponseCode', ''))
        if code != '0':
            desc = data.get('ResponseDescription') or 'STK push was rejected.'
            if 'wrong credential' in desc.lower():
                env = (settings.get('environment') or 'sandbox').lower()
                if env == 'sandbox':
                    desc += (
                        ' Sandbox: use DARAJA_SHORTCODE=174379, the sandbox passkey from Daraja, '
                        'and a sandbox test phone (see Daraja portal Test Credentials).'
                    )
            return {
                'ok': False,
                'error': desc,
                'raw': data,
            }
        return {
            'ok': True,
            'checkout_request_id': data.get('CheckoutRequestID'),
            'merchant_request_id': data.get('MerchantRequestID'),
            'customer_message': data.get('CustomerMessage') or 'Check your phone to enter M-Pesa PIN.',
            'raw': data,
        }
    except requests.RequestException as e:
        return {'ok': False, 'error': f'STK push request failed: {e}'}


def stk_query(settings: dict, checkout_request_id: str, business_shortcode: str) -> dict:
    """Query STK push status by CheckoutRequestID."""
    shortcode = sandbox_stk_shortcode(settings, (business_shortcode or settings.get('shortcode') or '').strip())
    passkey = (settings.get('passkey') or '').strip()
    if not shortcode or not passkey or not checkout_request_id:
        return {'ok': False, 'error': 'Missing data for STK query.'}
    token, terr = get_access_token(settings)
    if terr:
        return {'ok': False, 'error': terr}
    pwd, ts = stk_password(shortcode, passkey)
    payload = {
        'BusinessShortCode': shortcode,
        'Password': pwd,
        'Timestamp': ts,
        'CheckoutRequestID': checkout_request_id,
    }
    url = f"{daraja_base_url(settings)}/mpesa/stkpush/v1/query"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )
        data = r.json() if r.content else {}
        if r.status_code != 200:
            return {
                'ok': False,
                'error': data.get('errorMessage') or data.get('error_description') or f'STK query failed ({r.status_code}).',
                'error_code': data.get('errorCode'),
                'raw': data,
            }
        if data.get('errorCode'):
            return {
                'ok': False,
                'error': data.get('errorMessage') or 'STK query failed.',
                'error_code': data.get('errorCode'),
                'raw': data,
            }
        return {
            'ok': True,
            'raw': data,
            'result_code': data.get('ResultCode'),
            'result_desc': data.get('ResultDesc'),
        }
    except requests.RequestException as e:
        return {'ok': False, 'error': str(e)}


def transaction_status_query(
    settings: dict,
    transaction_id: str,
    identifier_type: str = '4',
    remarks: str = 'Status query',
    occasion: str = '',
) -> dict:
    """Initiate async transaction status query (advanced)."""
    token, terr = get_access_token(settings)
    if terr:
        return {'ok': False, 'error': terr}
    shortcode = (settings.get('shortcode') or '').strip()
    initiator = (settings.get('initiator_name') or 'testapi').strip()
    credential = (settings.get('security_credential') or '').strip()
    if not credential:
        return {'ok': False, 'error': 'Security credential required for transaction status (.env).'}
    payload = {
        'Initiator': initiator,
        'SecurityCredential': credential,
        'CommandID': 'TransactionStatusQuery',
        'TransactionID': transaction_id,
        'PartyA': shortcode,
        'IdentifierType': str(identifier_type),
        'ResultURL': settings.get('result_url') or settings.get('stk_callback_path', ''),
        'QueueTimeOutURL': settings.get('timeout_url') or settings.get('result_url', ''),
        'Remarks': remarks[:100],
        'Occasion': occasion[:100],
    }
    url = f"{daraja_base_url(settings)}/mpesa/transactionstatus/v1/query"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )
        data = r.json() if r.content else {}
        return {'ok': r.status_code == 200, 'raw': data, 'error': data.get('errorMessage')}
    except requests.RequestException as e:
        return {'ok': False, 'error': str(e)}


def account_balance_query(settings: dict, remarks: str = 'Balance query') -> dict:
    """Initiate account balance query (advanced)."""
    token, terr = get_access_token(settings)
    if terr:
        return {'ok': False, 'error': terr}
    shortcode = (settings.get('shortcode') or '').strip()
    initiator = (settings.get('account_balance_initiator') or settings.get('initiator_name') or 'testapi').strip()
    credential = (settings.get('account_balance_security_credential') or settings.get('security_credential') or '').strip()
    if not credential:
        return {'ok': False, 'error': 'Security credential required for balance query (.env).'}
    payload = {
        'Initiator': initiator,
        'SecurityCredential': credential,
        'CommandID': 'AccountBalance',
        'PartyA': shortcode,
        'IdentifierType': '4',
        'Remarks': remarks[:100],
        'QueueTimeOutURL': settings.get('timeout_url') or '',
        'ResultURL': settings.get('result_url') or '',
    }
    url = f"{daraja_base_url(settings)}/mpesa/accountbalance/v1/query"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )
        data = r.json() if r.content else {}
        return {'ok': r.status_code == 200, 'raw': data}
    except requests.RequestException as e:
        return {'ok': False, 'error': str(e)}


def reversal_request(
    settings: dict,
    transaction_id: str,
    amount: float,
    receiver_party: str,
    remarks: str = 'Reversal',
) -> dict:
    """Reverse a transaction (advanced)."""
    token, terr = get_access_token(settings)
    if terr:
        return {'ok': False, 'error': terr}
    initiator = (settings.get('initiator_name') or 'testapi').strip()
    credential = (settings.get('security_credential') or '').strip()
    if not credential:
        return {'ok': False, 'error': 'Security credential required for reversal (.env).'}
    shortcode = (settings.get('shortcode') or '').strip()
    try:
        amt = int(round(float(amount)))
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Invalid amount.'}
    payload = {
        'Initiator': initiator,
        'SecurityCredential': credential,
        'CommandID': 'TransactionReversal',
        'TransactionID': transaction_id,
        'Amount': amt,
        'ReceiverParty': receiver_party or shortcode,
        'RecieverParty': receiver_party or shortcode,
        'Remarks': remarks[:100],
        'Occasion': '',
        'QueueTimeOutURL': settings.get('timeout_url') or '',
        'ResultURL': settings.get('result_url') or '',
    }
    url = f"{daraja_base_url(settings)}/mpesa/reversal/v1/request"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )
        data = r.json() if r.content else {}
        return {'ok': r.status_code == 200, 'raw': data}
    except requests.RequestException as e:
        return {'ok': False, 'error': str(e)}


def b2c_payment(
    settings: dict,
    phone: str,
    amount: float,
    remarks: str = 'Payment',
    occasion: str = '',
) -> dict:
    """B2C single payment (advanced)."""
    msisdn, err = normalize_msisdn(phone)
    if err:
        return {'ok': False, 'error': err}
    token, terr = get_access_token(settings)
    if terr:
        return {'ok': False, 'error': terr}
    initiator = (settings.get('initiator_name') or 'testapi').strip()
    credential = (settings.get('security_credential') or '').strip()
    shortcode = (settings.get('b2c_shortcode') or settings.get('shortcode') or '').strip()
    if not credential:
        return {'ok': False, 'error': 'Security credential required for B2C (.env).'}
    try:
        amt = int(round(float(amount)))
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Invalid amount.'}
    payload = {
        'InitiatorName': initiator,
        'SecurityCredential': credential,
        'CommandID': 'BusinessPayment',
        'Amount': amt,
        'PartyA': shortcode,
        'PartyB': msisdn,
        'Remarks': remarks[:100],
        'QueueTimeOutURL': settings.get('timeout_url') or '',
        'ResultURL': settings.get('result_url') or '',
        'Occasion': occasion[:100],
    }
    url = f"{daraja_base_url(settings)}/mpesa/b2c/v1/paymentrequest"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=45,
        )
        data = r.json() if r.content else {}
        return {'ok': r.status_code == 200, 'raw': data, 'error': data.get('errorMessage')}
    except requests.RequestException as e:
        return {'ok': False, 'error': str(e)}


def parse_stk_callback(body: dict) -> dict:
    """Extract STK callback metadata from Daraja Body.stkCallback."""
    out = {
        'checkout_request_id': None,
        'merchant_request_id': None,
        'result_code': None,
        'result_desc': None,
        'mpesa_receipt': None,
        'amount': None,
        'phone': None,
        'transaction_date': None,
    }
    if not body:
        return out
    stk = body.get('Body', {}).get('stkCallback') or body.get('stkCallback') or body
    out['checkout_request_id'] = stk.get('CheckoutRequestID')
    out['merchant_request_id'] = stk.get('MerchantRequestID')
    out['result_code'] = stk.get('ResultCode')
    out['result_desc'] = stk.get('ResultDesc')
    meta = stk.get('CallbackMetadata', {}).get('Item') or []
    for item in meta:
        name = item.get('Name')
        val = item.get('Value')
        if name == 'MpesaReceiptNumber':
            out['mpesa_receipt'] = str(val) if val is not None else None
        elif name == 'Amount':
            out['amount'] = val
        elif name == 'PhoneNumber':
            out['phone'] = str(val) if val is not None else None
        elif name == 'TransactionDate':
            out['transaction_date'] = str(val) if val is not None else None
    return out


# STK query / callback result codes (Daraja Lipa Na M-Pesa)
STK_RESULT_PENDING = frozenset({'4999', ''})
STK_RESULT_CANCELLED = frozenset({'1032', '1031'})
STK_RESULT_FAILED = frozenset({'1', '1001', '1019', '1025', '1037', '2001', '2029', '8006'})


def parse_stk_query_response(raw: dict) -> dict:
    """Extract ResultCode, description, and receipt from STK Push Query response."""
    out = {
        'result_code': None,
        'result_desc': None,
        'mpesa_receipt': None,
        'amount': None,
        'phone': None,
        'error_code': None,
        'error_message': None,
    }
    if not raw:
        return out
    if raw.get('errorCode'):
        out['error_code'] = raw.get('errorCode')
        out['error_message'] = raw.get('errorMessage')
        return out
    out['result_code'] = raw.get('ResultCode')
    out['result_desc'] = raw.get('ResultDesc')
    meta = raw.get('CallbackMetadata', {}).get('Item') or []
    for item in meta:
        name = item.get('Name')
        val = item.get('Value')
        if name == 'MpesaReceiptNumber':
            out['mpesa_receipt'] = str(val) if val is not None else None
        elif name == 'Amount':
            out['amount'] = val
        elif name == 'PhoneNumber':
            out['phone'] = str(val) if val is not None else None
    return out


def stk_query_result_status(result_code) -> str:
    """Map Daraja STK ResultCode to pending | completed | cancelled | failed."""
    rc = str(result_code if result_code is not None else '').strip()
    if rc == '0':
        return 'completed'
    if rc in STK_RESULT_CANCELLED:
        return 'cancelled'
    if rc in STK_RESULT_PENDING:
        return 'pending'
    if rc in STK_RESULT_FAILED or (rc.isdigit() and rc not in STK_RESULT_PENDING):
        return 'failed'
    return 'pending'
