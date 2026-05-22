"""
Shared helpers for public portal routes: validation, rate limiting, CSRF.
"""
from __future__ import annotations

import re
import secrets
import threading
import time

from flask import request, session

PORTAL_PASSWORD_MIN_LEN = 8

_rate_lock = threading.Lock()
_rate_buckets: dict = {}


def normalize_phone_digits(raw):
    """Digits only from phone input."""
    return re.sub(r'\D', '', (raw or '').strip())


def validate_phone(raw, required=True):
    """
    Validate phone; returns (normalized_digits, error_message).
    Normalized value is digits-only (9–15 digits).
    """
    digits = normalize_phone_digits(raw)
    if not digits:
        if required:
            return None, 'Phone number is required.'
        return None, None
    if len(digits) < 9 or len(digits) > 15:
        return None, 'Enter a valid phone number (at least 9 digits).'
    return digits, None


def validate_email_format(email, required=False):
    """Basic email check; returns (normalized_lower, error)."""
    em = (email or '').strip().lower()
    if not em:
        if required:
            return None, 'Email is required.'
        return None, None
    if '@' not in em or '.' not in em.split('@')[-1]:
        return None, 'Enter a valid email address.'
    if len(em) > 255:
        return None, 'Email is too long.'
    return em, None


def validate_portal_password(password):
    """Return None if OK, else error message."""
    pw = password or ''
    if len(pw) < PORTAL_PASSWORD_MIN_LEN:
        return f'Password must be at least {PORTAL_PASSWORD_MIN_LEN} characters.'
    if not re.search(r'[A-Za-z]', pw):
        return 'Password must include at least one letter.'
    if not re.search(r'\d', pw):
        return 'Password must include at least one number.'
    return None


def portal_csrf_token():
    """Session-backed CSRF token for public forms."""
    tok = session.get('_portal_csrf_token')
    if not tok:
        tok = secrets.token_urlsafe(32)
        session['_portal_csrf_token'] = tok
    return tok


def validate_portal_csrf(form_token):
    """True if form token matches session."""
    expected = session.get('_portal_csrf_token')
    if not expected or not form_token:
        return False
    try:
        return secrets.compare_digest(str(expected), str(form_token))
    except Exception:
        return False


def check_rate_limit(scope, limit=12, window_sec=60):
    """
    Per-IP sliding window rate limit.
    Returns (allowed: bool, retry_after_seconds: int|None).
    Best-effort on single host; use Redis for multi-worker fleets.
    """
    ip = (request.remote_addr or 'unknown').strip()
    key = f'{scope}:{ip}'
    now = time.time()
    with _rate_lock:
        hits = _rate_buckets.get(key, [])
        hits = [t for t in hits if now - t < window_sec]
        if len(hits) >= limit:
            retry = int(window_sec - (now - hits[0])) + 1
            return False, max(1, min(retry, window_sec))
        hits.append(now)
        _rate_buckets[key] = hits
    return True, None


def rate_limit_flash_message(retry_after):
    return (
        f'Too many attempts. Please wait {retry_after} seconds and try again.'
    )
