"""Warden portal — per-hostel payment settings (account, methods, and payment plan)."""
import json
from decimal import Decimal, ROUND_HALF_UP

HOSTEL_PAYMENT_MODE_KEYS = ('mpesa', 'cash', 'cheque', 'bank')
HOSTEL_PAYMENT_MODE_LABELS = {
    'mpesa': 'M-Pesa',
    'cash': 'Cash',
    'cheque': 'Cheque',
    'bank': 'Bank',
}
HOSTEL_DEFAULT_RESERVATION_PCT = Decimal('25.00')
HOSTEL_MIN_INSTALLMENTS = 2
HOSTEL_MAX_INSTALLMENTS = 12


def _money(value):
    try:
        return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0.00')


def _pct(value, default=None):
    try:
        p = Decimal(str(value))
    except Exception:
        p = default if default is not None else HOSTEL_DEFAULT_RESERVATION_PCT
    if p < 0:
        p = Decimal('0')
    if p > 100:
        p = Decimal('100')
    return p.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _ensure_payment_plan_columns(cursor):
    try:
        cols = [
            ("allow_full_payment", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("allow_installment_payment", "TINYINT(1) NOT NULL DEFAULT 0"),
            ("allow_reservation", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("reservation_pct", "DECIMAL(5,2) NOT NULL DEFAULT 25.00"),
            ("installment_count", "INT NOT NULL DEFAULT 2"),
            ("installment_pcts_json", "TEXT NULL"),
            ("payments_enabled", "TINYINT(1) NOT NULL DEFAULT 1"),
        ]
        for col, definition in cols:
            cursor.execute(f"SHOW COLUMNS FROM hostel_payment_settings LIKE '{col}'")
            if not cursor.fetchone():
                cursor.execute(
                    f"ALTER TABLE hostel_payment_settings ADD COLUMN {col} {definition}"
                )
    except Exception as e:
        print(f"_ensure_payment_plan_columns: {e}")


def _ensure_payments_enabled_column(cursor):
    try:
        cursor.execute("SHOW COLUMNS FROM hostel_payment_settings LIKE 'payments_enabled'")
        if not cursor.fetchone():
            cursor.execute(
                "ALTER TABLE hostel_payment_settings "
                "ADD COLUMN payments_enabled TINYINT(1) NOT NULL DEFAULT 1"
            )
        cursor.execute("SHOW COLUMNS FROM hostel_payment_settings LIKE 'finance_account_id'")
        col = cursor.fetchone()
        if col:
            null_ok = (col.get('Null') if isinstance(col, dict) else col[2] or '').upper() == 'YES'
            if not null_ok:
                cursor.execute(
                    "ALTER TABLE hostel_payment_settings "
                    "MODIFY COLUMN finance_account_id INT NULL"
                )
    except Exception as e:
        print(f"_ensure_payments_enabled_column: {e}")


def ensure_hostel_payment_settings_table(cursor):
    """Per-hostel payment routing (one finance account + allowed modes each)."""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hostel_payment_settings (
                hostel_id INT NOT NULL PRIMARY KEY,
                finance_account_id INT NULL,
                allow_mpesa TINYINT(1) NOT NULL DEFAULT 0,
                allow_cash TINYINT(1) NOT NULL DEFAULT 0,
                allow_cheque TINYINT(1) NOT NULL DEFAULT 0,
                allow_bank TINYINT(1) NOT NULL DEFAULT 0,
                allow_full_payment TINYINT(1) NOT NULL DEFAULT 1,
                allow_installment_payment TINYINT(1) NOT NULL DEFAULT 0,
                allow_reservation TINYINT(1) NOT NULL DEFAULT 1,
                reservation_pct DECIMAL(5,2) NOT NULL DEFAULT 25.00,
                installment_count INT NOT NULL DEFAULT 2,
                installment_pcts_json TEXT NULL,
                payments_enabled TINYINT(1) NOT NULL DEFAULT 1,
                updated_by INT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_hps_account (finance_account_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        _migrate_hostel_payment_settings_from_singleton(cursor)
        _ensure_payment_plan_columns(cursor)
        _ensure_payments_enabled_column(cursor)
    except Exception as e:
        print(f"ensure_hostel_payment_settings_table: {e}")


def _migrate_hostel_payment_settings_from_singleton(cursor):
    """Drop legacy singleton row/columns if an old schema is still present."""
    try:
        cursor.execute("SHOW COLUMNS FROM hostel_payment_settings LIKE 'id'")
        if not cursor.fetchone():
            return
        cursor.execute("SHOW COLUMNS FROM hostel_payment_settings LIKE 'hostel_id'")
        if cursor.fetchone():
            return
        cursor.execute("DROP TABLE IF EXISTS hostel_payment_settings")
        cursor.execute("""
            CREATE TABLE hostel_payment_settings (
                hostel_id INT NOT NULL PRIMARY KEY,
                finance_account_id INT NOT NULL,
                allow_mpesa TINYINT(1) NOT NULL DEFAULT 0,
                allow_cash TINYINT(1) NOT NULL DEFAULT 0,
                allow_cheque TINYINT(1) NOT NULL DEFAULT 0,
                allow_bank TINYINT(1) NOT NULL DEFAULT 0,
                allow_full_payment TINYINT(1) NOT NULL DEFAULT 1,
                allow_installment_payment TINYINT(1) NOT NULL DEFAULT 0,
                allow_reservation TINYINT(1) NOT NULL DEFAULT 1,
                reservation_pct DECIMAL(5,2) NOT NULL DEFAULT 25.00,
                installment_count INT NOT NULL DEFAULT 2,
                installment_pcts_json TEXT NULL,
                updated_by INT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_hps_account (finance_account_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    except Exception as e:
        print(f"_migrate_hostel_payment_settings_from_singleton: {e}")


def _parse_installment_pcts_json(raw):
    if raw is None or raw == '':
        return []
    if isinstance(raw, list):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
    out = []
    for item in data:
        try:
            out.append(float(_pct(item)))
        except Exception:
            continue
    return out


def _default_installment_pcts(count):
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 2
    count = max(HOSTEL_MIN_INSTALLMENTS, min(HOSTEL_MAX_INSTALLMENTS, count))
    each = (Decimal('100') / Decimal(count)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    pcts = [float(each)] * count
    diff = 100.0 - sum(pcts)
    if pcts:
        pcts[-1] = round(pcts[-1] + diff, 2)
    return pcts


def _payment_plan_from_row(row):
    if not row:
        return {
            'allow_full_payment': True,
            'allow_installment_payment': False,
            'allow_reservation': True,
            'reservation_pct': float(HOSTEL_DEFAULT_RESERVATION_PCT),
            'installment_count': 2,
            'installment_pcts': _default_installment_pcts(2),
            'installment_pcts_json': json.dumps(_default_installment_pcts(2)),
            'payments_enabled': True,
        }
    if isinstance(row, dict):
        allow_full = bool(int(row.get('allow_full_payment') if row.get('allow_full_payment') is not None else 1))
        allow_inst = bool(int(row.get('allow_installment_payment') or 0))
        allow_res = bool(int(row.get('allow_reservation') if row.get('allow_reservation') is not None else 1))
        reservation_pct = float(_pct(row.get('reservation_pct'), HOSTEL_DEFAULT_RESERVATION_PCT))
        inst_count = int(row.get('installment_count') or 2)
        raw_pcts = row.get('installment_pcts_json')
        payments_enabled = bool(int(row.get('payments_enabled') if row.get('payments_enabled') is not None else 1))
    else:
        allow_full = bool(int(row[6] or 1)) if len(row) > 6 else True
        allow_inst = bool(int(row[7] or 0)) if len(row) > 7 else False
        allow_res = bool(int(row[8] or 1)) if len(row) > 8 else True
        reservation_pct = float(_pct(row[9] if len(row) > 9 else HOSTEL_DEFAULT_RESERVATION_PCT, HOSTEL_DEFAULT_RESERVATION_PCT))
        inst_count = int(row[10] or 2) if len(row) > 10 else 2
        raw_pcts = row[11] if len(row) > 11 else None
        payments_enabled = bool(int(row[12] or 1)) if len(row) > 12 else True

    inst_count = max(HOSTEL_MIN_INSTALLMENTS, min(HOSTEL_MAX_INSTALLMENTS, inst_count))
    pcts = _parse_installment_pcts_json(raw_pcts)
    if len(pcts) != inst_count:
        pcts = _default_installment_pcts(inst_count)
    return {
        'allow_full_payment': allow_full,
        'allow_installment_payment': allow_inst,
        'allow_reservation': allow_res,
        'reservation_pct': reservation_pct,
        'installment_count': inst_count,
        'installment_pcts': pcts,
        'installment_pcts_json': json.dumps(pcts),
        'payments_enabled': payments_enabled,
    }


def _modes_from_row(row):
    if isinstance(row, dict):
        allow_mpesa = bool(int(row.get('allow_mpesa') or 0))
        allow_cash = bool(int(row.get('allow_cash') or 0))
        allow_cheque = bool(int(row.get('allow_cheque') or 0))
        allow_bank = bool(int(row.get('allow_bank') or 0))
    else:
        allow_mpesa = bool(int(row[2] or 0)) if len(row) > 2 else False
        allow_cash = bool(int(row[3] or 0)) if len(row) > 3 else False
        allow_cheque = bool(int(row[4] or 0)) if len(row) > 4 else False
        allow_bank = bool(int(row[5] or 0)) if len(row) > 5 else False
    modes = []
    if allow_mpesa:
        modes.append('mpesa')
    if allow_cash:
        modes.append('cash')
    if allow_cheque:
        modes.append('cheque')
    if allow_bank:
        modes.append('bank')
    return allow_mpesa, allow_cash, allow_cheque, allow_bank, modes


def _row_to_hostel_payment_settings(row):
    if not row:
        base = {
            'hostel_id': None,
            'finance_account_id': None,
            'allow_mpesa': False,
            'allow_cash': False,
            'allow_cheque': False,
            'allow_bank': False,
            'allowed_payment_modes': [],
            'is_configured': False,
        }
        base.update(_payment_plan_from_row(None))
        base['payments_enabled'] = True
        return base
    if isinstance(row, dict):
        hostel_id = row.get('hostel_id')
        account_id = row.get('finance_account_id')
    else:
        hostel_id = row[0] if len(row) > 0 else None
        account_id = row[1] if len(row) > 1 else None
    allow_mpesa, allow_cash, allow_cheque, allow_bank, modes = _modes_from_row(row)
    plan = _payment_plan_from_row(row)
    payments_enabled = bool(plan.get('payments_enabled', True))
    configured = bool(not payments_enabled or (account_id and modes))
    return {
        'hostel_id': int(hostel_id) if hostel_id else None,
        'finance_account_id': int(account_id) if account_id else None,
        'allow_mpesa': allow_mpesa,
        'allow_cash': allow_cash,
        'allow_cheque': allow_cheque,
        'allow_bank': allow_bank,
        'allowed_payment_modes': modes,
        'payments_enabled': payments_enabled,
        'is_configured': configured,
        **plan,
    }


_HOSTEL_PAYMENT_SELECT = """
    SELECT hostel_id, finance_account_id,
           allow_mpesa, allow_cash, allow_cheque, allow_bank,
           allow_full_payment, allow_installment_payment,
           allow_reservation, reservation_pct,
           installment_count, installment_pcts_json,
           payments_enabled, updated_by, updated_at
    FROM hostel_payment_settings
"""


def fetch_hostel_payment_settings_map(cursor):
    """Return {hostel_id: settings_dict} for all configured hostels."""
    ensure_hostel_payment_settings_table(cursor)
    cursor.execute(_HOSTEL_PAYMENT_SELECT)
    out = {}
    for row in cursor.fetchall() or []:
        settings = _row_to_hostel_payment_settings(row)
        hid = settings.get('hostel_id')
        if hid:
            out[int(hid)] = settings
    return out


def fetch_hostel_payment_settings(cursor, hostel_id):
    """Return payment settings for one hostel."""
    try:
        hid = int(hostel_id)
    except (TypeError, ValueError):
        return _row_to_hostel_payment_settings(None)
    ensure_hostel_payment_settings_table(cursor)
    cursor.execute(
        _HOSTEL_PAYMENT_SELECT + " WHERE hostel_id = %s LIMIT 1",
        (hid,),
    )
    return _row_to_hostel_payment_settings(cursor.fetchone())


def validate_payment_plan_payload(payment_plan, label='this hostel'):
    """Validate payment plan fields. Returns (plan_dict, error_message)."""
    payment_plan = payment_plan or {}
    allow_full = bool(payment_plan.get('allow_full_payment'))
    allow_inst = bool(payment_plan.get('allow_installment_payment'))
    allow_res = bool(payment_plan.get('allow_reservation'))

    if allow_full and allow_inst:
        return None, f'Choose either full payment or installments for {label}, not both.'
    if not allow_full and not allow_inst:
        return None, f'Choose full payment or installments for {label}.'

    reservation_pct = float(_pct(payment_plan.get('reservation_pct'), HOSTEL_DEFAULT_RESERVATION_PCT))
    if allow_res:
        if reservation_pct <= 0 or reservation_pct >= 100:
            return None, f'Reservation percentage for {label} must be between 0.01 and 99.99.'

    inst_count = payment_plan.get('installment_count')
    try:
        inst_count = int(inst_count)
    except (TypeError, ValueError):
        inst_count = HOSTEL_MIN_INSTALLMENTS
    inst_count = max(HOSTEL_MIN_INSTALLMENTS, min(HOSTEL_MAX_INSTALLMENTS, inst_count))

    pcts = payment_plan.get('installment_pcts')
    if not isinstance(pcts, list):
        pcts = _parse_installment_pcts_json(payment_plan.get('installment_pcts_json'))
    cleaned = []
    for item in pcts[:inst_count]:
        try:
            val = float(_pct(item))
        except Exception:
            val = 0.0
        if val <= 0:
            return None, f'Each installment for {label} must be greater than 0%.'
        cleaned.append(val)
    while len(cleaned) < inst_count:
        cleaned = _default_installment_pcts(inst_count)
        break

    if allow_inst:
        total_pct = round(sum(cleaned), 2)
        if abs(total_pct - 100.0) > 0.05:
            return None, f'Installment percentages for {label} must add up to 100% (currently {total_pct:.2f}%).'

    return {
        'allow_full_payment': allow_full,
        'allow_installment_payment': allow_inst,
        'allow_reservation': allow_res,
        'reservation_pct': reservation_pct,
        'installment_count': inst_count,
        'installment_pcts': cleaned,
        'installment_pcts_json': json.dumps(cleaned),
    }, None


def compute_hostel_payment_quote(total_amount, settings):
    """
    Build student-facing amounts from room total and hostel payment settings.
    Installments apply to the balance remaining after reservation (if any).
    """
    settings = settings or {}
    total = _money(total_amount)
    allow_full = bool(settings.get('allow_full_payment', True))
    allow_inst = bool(settings.get('allow_installment_payment', False))
    allow_res = bool(settings.get('allow_reservation', True))
    reservation_pct = _pct(settings.get('reservation_pct'), HOSTEL_DEFAULT_RESERVATION_PCT)

    reservation_amount = Decimal('0.00')
    if allow_res:
        reservation_amount = (total * reservation_pct / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP,
        )

    remaining = (total - reservation_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if remaining < 0:
        remaining = Decimal('0.00')

    inst_pcts = settings.get('installment_pcts') or _default_installment_pcts(
        settings.get('installment_count') or 2,
    )
    installments = []
    if allow_inst and remaining > 0:
        running = Decimal('0.00')
        for idx, pct in enumerate(inst_pcts):
            pct_dec = _pct(pct)
            if idx == len(inst_pcts) - 1:
                amt = (remaining - running).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                amt = (remaining * pct_dec / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP,
                )
                running += amt
            installments.append({
                'no': idx + 1,
                'pct': float(pct_dec),
                'amount': float(amt),
            })

    balance_amount = remaining
    if not allow_res and allow_inst and installments:
        reservation_amount = _money(installments[0]['amount'])
        balance_amount = (total - reservation_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        'total_amount': float(total),
        'allow_full_payment': allow_full,
        'allow_installment_payment': allow_inst,
        'allow_reservation': allow_res,
        'reservation_pct': float(reservation_pct),
        'reservation_amount': float(reservation_amount),
        'deposit_amount': float(reservation_amount),
        'balance_amount': float(balance_amount),
        'full_amount': float(total),
        'installments': installments,
        'installment_count': len(installments),
    }


def build_booking_installment_plan(quote):
    """Snapshot installment schedule for a booking after reservation."""
    installments = quote.get('installments') or []
    if not installments:
        return []
    return [
        {'no': inst['no'], 'pct': inst['pct'], 'amount': inst['amount'], 'paid': False}
        for inst in installments
    ]


def get_booking_next_payment(booking):
    """Return (amount, purpose_label, purpose_key) for the next payment on a booking."""
    booking = booking or {}
    status = (booking.get('status') or '').strip().lower()
    total = _money(booking.get('total_amount'))
    amount_paid = _money(booking.get('amount_paid'))
    if status == 'occupied':
        return None, None, None

    plan = booking.get('installment_plan') or []
    if isinstance(plan, str):
        try:
            plan = json.loads(plan)
        except Exception:
            plan = []

    installments_paid = int(booking.get('installments_paid') or 0)
    if plan and installments_paid < len(plan):
        for inst in plan:
            if not inst.get('paid') and int(inst.get('no') or 0) == installments_paid + 1:
                return float(inst.get('amount') or 0), f"Installment {inst.get('no')}", 'hostel_installment'

    balance = _money(booking.get('balance_amount'))
    remaining = (total - amount_paid).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if remaining <= 0:
        return None, None, None
    pay_amount = balance if balance > 0 else remaining
    if status == 'reserved':
        return float(pay_amount), 'Remaining balance', 'hostel_balance'
    return None, None, None


def _validate_finance_account_id(cursor, finance_account_id, label):
    try:
        fid = int(finance_account_id)
    except (TypeError, ValueError):
        return None, f'Select a finance account for {label}.'
    cursor.execute(
        """
        SELECT id, account_name, account_status
        FROM finance_accounts
        WHERE id = %s
        LIMIT 1
        """,
        (fid,),
    )
    row = cursor.fetchone()
    if not row:
        return None, f'The selected account for {label} was not found.'
    if isinstance(row, dict):
        name = (row.get('account_name') or '').strip()
        status = (row.get('account_status') or 'active').strip().lower()
    else:
        name = (row[1] or '').strip() if len(row) > 1 else ''
        status = (row[2] or 'active').strip().lower() if len(row) > 2 else 'active'
    if status != 'active':
        return None, f'{name or "That account"} is not active.'
    return fid, None


def save_hostel_payment_settings_single(
    cursor, hostel_id, hostel_name, finance_account_id, modes,
    employee_id=None, payment_plan=None, payments_enabled=True,
):
    """Save payment settings for one hostel. Returns {ok, message}."""
    ensure_hostel_payment_settings_table(cursor)
    try:
        hid = int(hostel_id)
    except (TypeError, ValueError):
        return {'ok': False, 'message': 'Invalid hostel.'}
    name = (hostel_name or '').strip() or f'Hostel {hid}'
    payments_on = bool(payments_enabled)

    existing = fetch_hostel_payment_settings(cursor, hid)
    fid = existing.get('finance_account_id')

    if payments_on:
        fid, err = _validate_finance_account_id(cursor, finance_account_id, name)
        if err:
            return {'ok': False, 'message': err}

        mode_set = set()
        for mode in modes or []:
            m = (mode or '').strip().lower()
            if m in HOSTEL_PAYMENT_MODE_KEYS:
                mode_set.add(m)
        if not mode_set:
            return {'ok': False, 'message': f'Select at least one payment method for {name}.'}

        plan, plan_err = validate_payment_plan_payload(payment_plan, name)
        if plan_err:
            return {'ok': False, 'message': plan_err}
    else:
        if finance_account_id:
            validated, err = _validate_finance_account_id(cursor, finance_account_id, name)
            if not err:
                fid = validated
        mode_set = set()
        for mode in modes or []:
            m = (mode or '').strip().lower()
            if m in HOSTEL_PAYMENT_MODE_KEYS:
                mode_set.add(m)
        if not mode_set and existing:
            for mode in HOSTEL_PAYMENT_MODE_KEYS:
                if existing.get(f'allow_{mode}'):
                    mode_set.add(mode)
        plan = validate_payment_plan_payload(payment_plan or {}, name)[0]
        if not plan:
            plan = _payment_plan_from_row(existing if existing.get('hostel_id') else None)

    updated_by = None
    if employee_id is not None:
        try:
            updated_by = int(employee_id)
        except (TypeError, ValueError):
            updated_by = None

    cursor.execute(
        """
        INSERT INTO hostel_payment_settings (
            hostel_id, finance_account_id,
            allow_mpesa, allow_cash, allow_cheque, allow_bank,
            allow_full_payment, allow_installment_payment,
            allow_reservation, reservation_pct,
            installment_count, installment_pcts_json,
            payments_enabled, updated_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            finance_account_id = VALUES(finance_account_id),
            allow_mpesa = VALUES(allow_mpesa),
            allow_cash = VALUES(allow_cash),
            allow_cheque = VALUES(allow_cheque),
            allow_bank = VALUES(allow_bank),
            allow_full_payment = VALUES(allow_full_payment),
            allow_installment_payment = VALUES(allow_installment_payment),
            allow_reservation = VALUES(allow_reservation),
            reservation_pct = VALUES(reservation_pct),
            installment_count = VALUES(installment_count),
            installment_pcts_json = VALUES(installment_pcts_json),
            payments_enabled = VALUES(payments_enabled),
            updated_by = VALUES(updated_by),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            hid,
            fid,
            1 if 'mpesa' in mode_set else 0,
            1 if 'cash' in mode_set else 0,
            1 if 'cheque' in mode_set else 0,
            1 if 'bank' in mode_set else 0,
            1 if plan.get('allow_full_payment') else 0,
            1 if plan.get('allow_installment_payment') else 0,
            1 if plan.get('allow_reservation') else 0,
            plan.get('reservation_pct'),
            plan.get('installment_count'),
            plan.get('installment_pcts_json'),
            1 if payments_on else 0,
            updated_by,
        ),
    )
    msg = f'Payment settings saved for {name}.' if payments_on else f'Manual allocation enabled for {name} (payments off).'
    return {'ok': True, 'message': msg}


def save_hostel_payment_settings_from_form(cursor, form, hostels, employee_id=None):
    """Save per-hostel account + payment modes. Returns {ok, message}."""
    ensure_hostel_payment_settings_table(cursor)
    if not hostels:
        return {'ok': False, 'message': 'Register at least one hostel before setting up payments.'}

    saved = 0
    for hostel in hostels:
        try:
            hid = int(hostel.get('id') if isinstance(hostel, dict) else hostel)
        except (TypeError, ValueError):
            continue
        name = (hostel.get('name') if isinstance(hostel, dict) else '') or f'Hostel {hid}'
        raw_account = (form.get(f'finance_account_id_{hid}') or '').strip()
        if not raw_account:
            return {'ok': False, 'message': f'Select a finance account for {name}.'}

        modes = []
        for mode in HOSTEL_PAYMENT_MODE_KEYS:
            if (form.get(f'allow_{hid}_{mode}') or '').strip().lower() in ('1', 'on', 'true', 'yes'):
                modes.append(mode)

        payment_plan = {
            'allow_full_payment': (form.get(f'allow_full_{hid}') or '').strip().lower() in ('1', 'on', 'true', 'yes'),
            'allow_installment_payment': (form.get(f'allow_installments_{hid}') or '').strip().lower() in ('1', 'on', 'true', 'yes'),
            'allow_reservation': (form.get(f'allow_reservation_{hid}') or '').strip().lower() in ('1', 'on', 'true', 'yes'),
            'reservation_pct': form.get(f'reservation_pct_{hid}'),
            'installment_count': form.get(f'installment_count_{hid}'),
            'installment_pcts_json': form.get(f'installment_pcts_json_{hid}'),
        }

        result = save_hostel_payment_settings_single(
            cursor, hid, name, raw_account, modes,
            employee_id=employee_id, payment_plan=payment_plan,
        )
        if not result.get('ok'):
            return result
        saved += 1

    if saved < 1:
        return {'ok': False, 'message': 'No hostel payment settings were saved.'}
    return {'ok': True, 'message': f'Payment settings saved for {saved} hostel{"s" if saved != 1 else ""}.'}


def hostel_payment_method_allowed(settings, method):
    settings = settings or {}
    mode = (method or '').strip().lower()
    if mode == 'mpesa':
        return bool(settings.get('allow_mpesa'))
    if mode == 'cash':
        return bool(settings.get('allow_cash'))
    if mode == 'cheque':
        return bool(settings.get('allow_cheque'))
    if mode == 'bank':
        return bool(settings.get('allow_bank'))
    return mode in (settings.get('allowed_payment_modes') or [])


def hostel_payment_purpose_allowed(settings, purpose):
    """Check if a payment purpose is allowed for this hostel."""
    settings = settings or {}
    if not bool(settings.get('payments_enabled', True)):
        return False
    purpose = (purpose or '').strip().lower()
    if purpose == 'hostel_full':
        return bool(settings.get('allow_full_payment', True))
    if purpose == 'hostel_deposit':
        if bool(settings.get('allow_reservation', True)):
            return True
        return bool(settings.get('allow_installment_payment'))
    if purpose in ('hostel_balance', 'hostel_installment'):
        return bool(settings.get('allow_installment_payment')) or bool(settings.get('allow_reservation'))
    return False


def resolve_hostel_finance_account_id(cursor, hostel_id, settings=None):
    """Finance account for a hostel's payments. Returns (finance_account_id, error_message)."""
    try:
        hid = int(hostel_id)
    except (TypeError, ValueError):
        return None, 'Invalid hostel for payment.'

    settings = settings or fetch_hostel_payment_settings(cursor, hid)
    if not bool(settings.get('payments_enabled', True)):
        return None, 'Online payments are disabled for this hostel.'
    account_id = settings.get('finance_account_id')
    if not account_id:
        return None, 'Payment settings are not configured for this hostel. Contact the warden.'

    fid, err = _validate_finance_account_id(cursor, account_id, 'this hostel')
    if err:
        return None, err
    return fid, None


def attach_payment_settings_to_hostels(hostels, settings_map):
    """Merge payment settings into hostel dicts for templates/API."""
    settings_map = settings_map or {}
    for hostel in hostels or []:
        hid = hostel.get('id') or hostel.get('hostel_id')
        try:
            hid = int(hid)
        except (TypeError, ValueError):
            hid = None
        ps = settings_map.get(hid) if hid else None
        if ps:
            hostel['payment_settings'] = ps
            hostel['payments_enabled'] = bool(ps.get('payments_enabled', True))
            hostel['manual_allocation_allowed'] = not hostel['payments_enabled']
            hostel['payment_configured'] = bool(ps.get('is_configured'))
            hostel['mpesa_payment_allowed'] = bool(ps.get('allow_mpesa')) and hostel['payments_enabled']
            hostel['allow_full_payment'] = bool(ps.get('allow_full_payment', True))
            hostel['allow_installment_payment'] = bool(ps.get('allow_installment_payment'))
            if hostel['allow_full_payment'] and hostel['allow_installment_payment']:
                hostel['allow_full_payment'] = False
            hostel['allow_reservation'] = bool(ps.get('allow_reservation', True))
            hostel['reservation_pct'] = float(ps.get('reservation_pct') or HOSTEL_DEFAULT_RESERVATION_PCT)
        else:
            hostel['payment_settings'] = _row_to_hostel_payment_settings(None)
            hostel['payments_enabled'] = True
            hostel['manual_allocation_allowed'] = False
            hostel['payment_configured'] = False
            hostel['mpesa_payment_allowed'] = False
            hostel['allow_full_payment'] = True
            hostel['allow_installment_payment'] = False
            hostel['allow_reservation'] = True
            hostel['reservation_pct'] = float(HOSTEL_DEFAULT_RESERVATION_PCT)
    return hostels
