"""Student portal — browse hostels, book a room, pay deposit and balance."""
import json
from decimal import Decimal, ROUND_HALF_UP

from hostel_settings import (
    build_booking_installment_plan,
    compute_hostel_payment_quote,
    fetch_hostel_payment_settings,
    fetch_hostel_payment_settings_map,
    get_booking_next_payment,
)
from warden_hostels import ensure_hostels_tables

HOSTEL_DEPOSIT_PCT = Decimal('0.25')
BOOKING_ACTIVE_STATUSES = ('reserved', 'occupied')
ROOM_BLOCKED_STATUSES = BOOKING_ACTIVE_STATUSES


def _money(value):
    try:
        return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0.00')


def _split_hostel_amount(total, settings=None):
    quote = compute_hostel_payment_quote(total, settings or {})
    return (
        _money(quote['total_amount']),
        _money(quote['deposit_amount']),
        _money(quote['balance_amount']),
    )


def _ensure_booking_payment_columns(cursor):
    try:
        cols = [
            ("amount_paid", "DECIMAL(12,2) NOT NULL DEFAULT 0"),
            ("installments_paid", "INT NOT NULL DEFAULT 0"),
            ("installment_plan_json", "TEXT NULL"),
        ]
        for col, definition in cols:
            cursor.execute(f"SHOW COLUMNS FROM student_hostel_bookings LIKE '{col}'")
            if not cursor.fetchone():
                cursor.execute(
                    f"ALTER TABLE student_hostel_bookings ADD COLUMN {col} {definition}"
                )
    except Exception as e:
        print(f"_ensure_booking_payment_columns: {e}")


def ensure_student_hostel_bookings_table(cursor):
    ensure_hostels_tables(cursor)
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_hostel_bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) NOT NULL,
                hostel_id INT NOT NULL,
                hostel_room_id INT NOT NULL,
                status ENUM('pending_deposit', 'reserved', 'occupied', 'cancelled')
                    NOT NULL DEFAULT 'pending_deposit',
                total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                deposit_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                balance_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                amount_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
                installments_paid INT NOT NULL DEFAULT 0,
                installment_plan_json TEXT NULL,
                deposit_paid_at DATETIME NULL,
                balance_paid_at DATETIME NULL,
                deposit_receipt VARCHAR(64) NULL,
                balance_receipt VARCHAR(64) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_shb_student (student_id),
                INDEX idx_shb_hostel (hostel_id),
                INDEX idx_shb_room (hostel_room_id),
                INDEX idx_shb_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        _ensure_booking_payment_columns(cursor)
        cursor.execute(
            """
            UPDATE student_hostel_bookings
            SET status = 'cancelled'
            WHERE status = 'pending_deposit'
            """
        )
    except Exception as e:
        print(f"ensure_student_hostel_bookings_table: {e}")


def _row_to_booking(row):
    if isinstance(row, dict):
        return {
            'id': row.get('id'),
            'student_id': row.get('student_id') or '',
            'hostel_id': row.get('hostel_id'),
            'hostel_room_id': row.get('hostel_room_id'),
            'status': (row.get('status') or '').strip().lower(),
            'total_amount': float(row.get('total_amount') or 0),
            'deposit_amount': float(row.get('deposit_amount') or 0),
            'balance_amount': float(row.get('balance_amount') or 0),
            'amount_paid': float(row.get('amount_paid') or 0),
            'installments_paid': int(row.get('installments_paid') or 0),
            'installment_plan_json': row.get('installment_plan_json') or '',
            'installment_plan': _parse_installment_plan(row.get('installment_plan_json')),
            'deposit_paid_at': row.get('deposit_paid_at'),
            'balance_paid_at': row.get('balance_paid_at'),
            'deposit_receipt': row.get('deposit_receipt') or '',
            'balance_receipt': row.get('balance_receipt') or '',
            'created_at': row.get('created_at'),
            'updated_at': row.get('updated_at'),
            'hostel_name': row.get('hostel_name') or '',
            'hostel_location': row.get('hostel_location') or '',
            'hostel_category': row.get('hostel_category') or '',
            'hostel_photo_path': row.get('hostel_photo_path') or '',
            'room_reference': row.get('room_reference') or '',
            'room_price': float(row.get('room_price') or 0),
        }
    return {
        'id': row[0],
        'student_id': row[1] or '',
        'hostel_id': row[2],
        'hostel_room_id': row[3],
        'status': (row[4] or '').strip().lower(),
        'total_amount': float(row[5] or 0),
        'deposit_amount': float(row[6] or 0),
        'balance_amount': float(row[7] or 0),
        'deposit_paid_at': row[8],
        'balance_paid_at': row[9],
        'deposit_receipt': row[10] or '',
        'balance_receipt': row[11] or '',
        'created_at': row[12],
        'updated_at': row[13],
        'amount_paid': float(row[14] or 0) if len(row) > 14 else 0,
        'installments_paid': int(row[15] or 0) if len(row) > 15 else 0,
        'installment_plan_json': row[16] if len(row) > 16 else '',
        'installment_plan': _parse_installment_plan(row[16] if len(row) > 16 else ''),
        'hostel_name': row[17] if len(row) > 17 else '',
        'hostel_location': row[18] if len(row) > 18 else '',
        'hostel_category': row[19] if len(row) > 19 else '',
        'hostel_photo_path': row[20] if len(row) > 20 else '',
        'room_reference': row[21] if len(row) > 21 else '',
        'room_price': float(row[22] or 0) if len(row) > 22 else 0,
    }


def _parse_installment_plan(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _fetch_blocked_room_ids(cursor):
    ensure_student_hostel_bookings_table(cursor)
    placeholders = ','.join(['%s'] * len(ROOM_BLOCKED_STATUSES))
    cursor.execute(
        f"""
        SELECT DISTINCT hostel_room_id
        FROM student_hostel_bookings
        WHERE status IN ({placeholders})
        """,
        ROOM_BLOCKED_STATUSES,
    )
    blocked = set()
    for row in cursor.fetchall() or []:
        rid = row.get('hostel_room_id') if isinstance(row, dict) else row[0]
        try:
            blocked.add(int(rid))
        except (TypeError, ValueError):
            continue
    return blocked


def fetch_student_hostel_booking(cursor, student_id):
    """Return the student's paid booking (reserved or occupied only)."""
    sid = (student_id or '').strip()
    if not sid:
        return None
    ensure_student_hostel_bookings_table(cursor)
    placeholders = ','.join(['%s'] * len(BOOKING_ACTIVE_STATUSES))
    cursor.execute(
        f"""
        SELECT b.id, b.student_id, b.hostel_id, b.hostel_room_id, b.status,
               b.total_amount, b.deposit_amount, b.balance_amount,
               b.deposit_paid_at, b.balance_paid_at, b.deposit_receipt, b.balance_receipt,
               b.created_at, b.updated_at,
               b.amount_paid, b.installments_paid, b.installment_plan_json,
               h.name AS hostel_name, h.location AS hostel_location, h.category AS hostel_category,
               h.photo_path AS hostel_photo_path,
               r.reference_number AS room_reference, r.price AS room_price
        FROM student_hostel_bookings b
        JOIN hostels h ON h.id = b.hostel_id
        JOIN hostel_rooms r ON r.id = b.hostel_room_id
        WHERE LOWER(TRIM(b.student_id)) = LOWER(TRIM(%s))
          AND b.status IN ({placeholders})
        ORDER BY b.id DESC
        LIMIT 1
        """,
        (sid, *BOOKING_ACTIVE_STATUSES),
    )
    row = cursor.fetchone()
    return _row_to_booking(row) if row else None


def fetch_booking_by_id(cursor, booking_id):
    ensure_student_hostel_bookings_table(cursor)
    try:
        booking_id = int(booking_id)
    except (TypeError, ValueError):
        return None
    cursor.execute(
        """
        SELECT b.id, b.student_id, b.hostel_id, b.hostel_room_id, b.status,
               b.total_amount, b.deposit_amount, b.balance_amount,
               b.deposit_paid_at, b.balance_paid_at, b.deposit_receipt, b.balance_receipt,
               b.created_at, b.updated_at,
               b.amount_paid, b.installments_paid, b.installment_plan_json,
               h.name AS hostel_name, h.location AS hostel_location, h.category AS hostel_category,
               h.photo_path AS hostel_photo_path,
               r.reference_number AS room_reference, r.price AS room_price
        FROM student_hostel_bookings b
        JOIN hostels h ON h.id = b.hostel_id
        JOIN hostel_rooms r ON r.id = b.hostel_room_id
        WHERE b.id = %s
        LIMIT 1
        """,
        (booking_id,),
    )
    row = cursor.fetchone()
    return _row_to_booking(row) if row else None


def _student_has_active_booking(cursor, student_id):
    return fetch_student_hostel_booking(cursor, student_id) is not None


def validate_hostel_room_payment(cursor, student_id, hostel_room_id):
    """Validate room/student before starting deposit or full STK. No DB booking is created."""
    sid = (student_id or '').strip()
    if not sid:
        return {'ok': False, 'message': 'Student not found.'}
    try:
        room_id = int(hostel_room_id)
    except (TypeError, ValueError):
        return {'ok': False, 'message': 'Select a valid room.'}

    ensure_student_hostel_bookings_table(cursor)
    existing = fetch_student_hostel_booking(cursor, sid)
    if existing:
        st = existing.get('status') or ''
        if st == 'occupied':
            return {'ok': False, 'message': 'You already have an occupied hostel room.'}
        return {'ok': False, 'message': 'You already have a reserved booking. Pay the balance to move in.'}

    blocked = _fetch_blocked_room_ids(cursor)
    if room_id in blocked:
        return {'ok': False, 'message': 'That room is no longer available.'}

    cursor.execute(
        """
        SELECT r.id, r.hostel_id, r.reference_number, r.price, h.status, h.name
        FROM hostel_rooms r
        JOIN hostels h ON h.id = r.hostel_id
        WHERE r.id = %s
        LIMIT 1
        """,
        (room_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {'ok': False, 'message': 'Room not found.'}
    if isinstance(row, dict):
        hostel_status = (row.get('status') or '').strip().lower()
        hostel_id = int(row.get('hostel_id') or 0)
        room_ref = row.get('reference_number') or ''
        room_price = float(row.get('price') or 0)
        hostel_name = row.get('name') or ''
    else:
        hostel_status = (row[4] or '').strip().lower()
        hostel_id = int(row[1] or 0)
        room_ref = row[2] or ''
        room_price = float(row[3] or 0)
        hostel_name = row[5] or ''

    if hostel_status != 'active':
        return {'ok': False, 'message': 'This hostel is not available for booking.'}
    if room_price <= 0:
        return {'ok': False, 'message': 'This room has no price set. Contact the warden.'}

    payment_settings = fetch_hostel_payment_settings(cursor, hostel_id)
    quote = compute_hostel_payment_quote(room_price, payment_settings)
    return {
        'ok': True,
        'hostel_room_id': room_id,
        'hostel_id': hostel_id,
        'hostel_name': hostel_name,
        'room_reference': room_ref,
        'total_amount': quote['total_amount'],
        'deposit_amount': quote['deposit_amount'],
        'balance_amount': quote['balance_amount'],
        'reservation_amount': quote['reservation_amount'],
        'reservation_pct': quote['reservation_pct'],
        'full_amount': quote['full_amount'],
        'allow_full_payment': quote['allow_full_payment'],
        'allow_installment_payment': quote['allow_installment_payment'],
        'allow_reservation': quote['allow_reservation'],
        'installments': quote['installments'],
        'payment_settings': payment_settings,
    }


def fetch_available_hostels_for_student(cursor):
    """Active hostels with rooms marked available or taken."""
    ensure_hostels_tables(cursor)
    ensure_student_hostel_bookings_table(cursor)
    blocked = _fetch_blocked_room_ids(cursor)
    cursor.execute("""
        SELECT id, category, name, description, location, room_count, occupant_count, status, photo_path,
               created_by, created_at, updated_at
        FROM hostels
        WHERE LOWER(TRIM(status)) = 'active'
        ORDER BY name ASC, id ASC
    """)
    rows = cursor.fetchall() or []
    hostels = []
    for row in rows:
        if isinstance(row, dict):
            hid = int(row.get('id') or 0)
            hostel = {
                'id': hid,
                'category': row.get('category') or '',
                'name': row.get('name') or '',
                'description': row.get('description') or '',
                'location': row.get('location') or '',
                'room_count': int(row.get('room_count') or 0),
                'occupant_count': int(row.get('occupant_count') or 0),
                'status': (row.get('status') or 'active').strip().lower(),
                'photo_path': row.get('photo_path') or '',
                'rooms': [],
                'available_room_count': 0,
            }
        else:
            hid = int(row[0] or 0)
            hostel = {
                'id': hid,
                'category': row[1] or '',
                'name': row[2] or '',
                'description': row[3] or '',
                'location': row[4] or '',
                'room_count': int(row[5] or 0),
                'occupant_count': int(row[6] or 0),
                'status': (row[7] or 'active').strip().lower(),
                'photo_path': row[8] or '',
                'rooms': [],
                'available_room_count': 0,
            }
        hostels.append(hostel)

    if not hostels:
        return []

    settings_map = fetch_hostel_payment_settings_map(cursor)
    hostel_ids = [h['id'] for h in hostels]
    placeholders = ','.join(['%s'] * len(hostel_ids))
    cursor.execute(
        f"""
        SELECT id, hostel_id, reference_number, price, occupant_count, sort_order
        FROM hostel_rooms
        WHERE hostel_id IN ({placeholders})
        ORDER BY hostel_id ASC, sort_order ASC, id ASC
        """,
        hostel_ids,
    )
    by_id = {h['id']: h for h in hostels}
    for rr in cursor.fetchall() or []:
        if isinstance(rr, dict):
            rid = int(rr.get('id') or 0)
            hid = int(rr.get('hostel_id') or 0)
            price = float(rr.get('price') or 0)
        else:
            rid = int(rr[0] or 0)
            hid = int(rr[1] or 0)
            price = float(rr[3] or 0)
        hostel = by_id.get(hid)
        payment_settings = settings_map.get(hid)
        quote = compute_hostel_payment_quote(price, payment_settings)
        allow_full = bool(quote['allow_full_payment'])
        allow_inst = bool(quote['allow_installment_payment'])
        if allow_full and allow_inst:
            allow_full = False
        room = {
            'id': rid,
            'reference_number': (rr.get('reference_number') if isinstance(rr, dict) else rr[2]) or '',
            'price': price,
            'deposit_amount': quote['deposit_amount'],
            'balance_amount': quote['balance_amount'],
            'reservation_pct': quote['reservation_pct'],
            'allow_full_payment': allow_full,
            'allow_reservation': quote['allow_reservation'],
            'allow_installment_payment': allow_inst,
            'installments': quote['installments'],
            'occupant_count': int(rr.get('occupant_count') if isinstance(rr, dict) else rr[4] or 0),
            'sort_order': int(rr.get('sort_order') if isinstance(rr, dict) else rr[5] or 0),
            'is_available': rid not in blocked,
        }
        if hostel is not None:
            hostel['rooms'].append(room)
            if room['is_available']:
                hostel['available_room_count'] += 1
    return hostels


def validate_hostel_deposit_payment(cursor, student_id, hostel_room_id):
    """Alias for validate_hostel_room_payment."""
    return validate_hostel_room_payment(cursor, student_id, hostel_room_id)


def _create_reserved_booking_on_deposit(cursor, student_id, hostel_room_id, amount, receipt):
    """Create booking as RESERVED only after successful deposit payment."""
    from datetime import datetime

    quote = validate_hostel_room_payment(cursor, student_id, hostel_room_id)
    if not quote.get('ok'):
        return False, quote.get('message') or 'Cannot book this room.', None

    paid = _money(amount)
    expected = _money(quote.get('deposit_amount'))
    if paid < expected:
        return False, f'Deposit must be at least KES {float(expected):,.2f}.', None

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    receipt = (receipt or '').strip()[:64]
    total = _money(quote.get('total_amount'))
    deposit = _money(quote.get('deposit_amount'))
    balance = _money(quote.get('balance_amount'))
    inst_plan = build_booking_installment_plan(quote)
    allow_res = bool(quote.get('allow_reservation'))
    allow_inst = bool(quote.get('allow_installment_payment'))
    installments_paid = 0
    amount_paid = deposit

    if allow_inst and not allow_res and inst_plan:
        for inst in inst_plan:
            if int(inst.get('no') or 0) == 1:
                inst['paid'] = True
                break
        installments_paid = 1

    inst_json = json.dumps(inst_plan) if inst_plan else None

    cursor.execute(
        """
        INSERT INTO student_hostel_bookings (
            student_id, hostel_id, hostel_room_id, status,
            total_amount, deposit_amount, balance_amount,
            amount_paid, installments_paid, installment_plan_json,
            deposit_paid_at, deposit_receipt
        ) VALUES (%s, %s, %s, 'reserved', %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            (student_id or '').strip(),
            int(quote['hostel_id']),
            int(hostel_room_id),
            total,
            deposit,
            balance,
            amount_paid,
            installments_paid,
            inst_json,
            now,
            receipt or None,
        ),
    )
    booking_id = cursor.lastrowid
    room_ref = quote.get('room_reference') or 'room'
    hostel_name = quote.get('hostel_name') or 'hostel'
    if allow_inst and not allow_res:
        return True, f'Installment 1 received. Room {room_ref} at {hostel_name} is now RESERVED.', booking_id
    return True, f'Hostel deposit received. Room {room_ref} at {hostel_name} is now RESERVED.', booking_id


def _create_occupied_booking_on_full_payment(cursor, student_id, hostel_room_id, amount, receipt):
    """Create booking as OCCUPIED only after successful full payment."""
    from datetime import datetime

    quote = validate_hostel_room_payment(cursor, student_id, hostel_room_id)
    if not quote.get('ok'):
        return False, quote.get('message') or 'Cannot book this room.', None

    paid = _money(amount)
    expected = _money(quote.get('total_amount'))
    if paid < expected:
        return False, f'Full payment must be at least KES {float(expected):,.2f}.', None

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    receipt = (receipt or '').strip()[:64]
    total = _money(quote.get('total_amount'))
    deposit = _money(quote.get('deposit_amount'))
    balance = _money(quote.get('balance_amount'))

    cursor.execute(
        """
        INSERT INTO student_hostel_bookings (
            student_id, hostel_id, hostel_room_id, status,
            total_amount, deposit_amount, balance_amount,
            amount_paid, installments_paid, installment_plan_json,
            deposit_paid_at, balance_paid_at, deposit_receipt, balance_receipt
        ) VALUES (%s, %s, %s, 'occupied', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            (student_id or '').strip(),
            int(quote['hostel_id']),
            int(hostel_room_id),
            total,
            deposit,
            balance,
            total,
            0,
            None,
            now,
            now,
            receipt or None,
            receipt or None,
        ),
    )
    booking_id = cursor.lastrowid
    room_ref = quote.get('room_reference') or 'room'
    hostel_name = quote.get('hostel_name') or 'hostel'
    return True, f'Full hostel payment received. Room {room_ref} at {hostel_name} is now OCCUPIED.', booking_id


def apply_hostel_mpesa_payment(cursor, purpose, booking_id, student_id, amount, receipt, hostel_room_id=None):
    """
    Apply deposit or balance payment. Status changes only here, after successful payment.
    Returns (ok, message, booking_id_or_none).
    """
    from datetime import datetime

    paid = _money(amount)
    receipt = (receipt or '').strip()[:64]
    purpose = (purpose or '').strip().lower()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sid = (student_id or '').strip()

    if purpose == 'hostel_deposit':
        if booking_id:
            booking = fetch_booking_by_id(cursor, booking_id)
            if booking and booking.get('status') == 'pending_deposit':
                if (booking.get('student_id') or '').strip().lower() != sid.lower():
                    return False, 'This booking does not belong to you.', None
                expected = _money(booking.get('deposit_amount'))
                if paid < expected:
                    return False, f'Deposit must be at least KES {float(expected):,.2f}.', None
                cursor.execute(
                    """
                    UPDATE student_hostel_bookings
                    SET status = 'reserved', deposit_paid_at = %s, deposit_receipt = %s
                    WHERE id = %s AND status = 'pending_deposit'
                    """,
                    (now, receipt or None, int(booking_id)),
                )
                if cursor.rowcount < 1:
                    return False, 'Could not update booking status.', None
                return True, 'Hostel deposit received. Your room is now RESERVED.', int(booking_id)
        if not hostel_room_id:
            return False, 'Missing room for deposit payment.', None
        ok, msg, new_id = _create_reserved_booking_on_deposit(
            cursor, sid, hostel_room_id, amount, receipt,
        )
        return ok, msg, new_id

    if purpose == 'hostel_full':
        if not hostel_room_id:
            return False, 'Missing room for full payment.', None
        ok, msg, new_id = _create_occupied_booking_on_full_payment(
            cursor, sid, hostel_room_id, amount, receipt,
        )
        return ok, msg, new_id

    if purpose == 'hostel_balance':
        booking = fetch_booking_by_id(cursor, booking_id)
        if not booking:
            return False, 'Booking not found.', None
        if (booking.get('student_id') or '').strip().lower() != sid.lower():
            return False, 'This booking does not belong to you.', None
        if booking.get('status') != 'reserved':
            return False, 'This booking is not awaiting the balance payment.', None
        expected = _money(booking.get('balance_amount'))
        if paid < expected:
            return False, f'Balance payment must be at least KES {float(expected):,.2f}.', None
        cursor.execute(
            """
            UPDATE student_hostel_bookings
            SET status = 'occupied', balance_paid_at = %s, balance_receipt = %s,
                amount_paid = total_amount, installments_paid = COALESCE(installments_paid, 0)
            WHERE id = %s AND status = 'reserved'
            """,
            (now, receipt or None, int(booking_id)),
        )
        if cursor.rowcount < 1:
            return False, 'Could not update booking status.', None
        return True, 'Balance received. Your room is now OCCUPIED.', int(booking_id)

    if purpose == 'hostel_installment':
        booking = fetch_booking_by_id(cursor, booking_id)
        if not booking:
            return False, 'Booking not found.', None
        if (booking.get('student_id') or '').strip().lower() != sid.lower():
            return False, 'This booking does not belong to you.', None
        if booking.get('status') != 'reserved':
            return False, 'This booking is not awaiting an installment payment.', None
        next_amount, _, _ = get_booking_next_payment(booking)
        if next_amount is None:
            return False, 'No installment is due on this booking.', None
        expected = _money(next_amount)
        if paid < expected:
            return False, f'Installment must be at least KES {float(expected):,.2f}.', None

        plan = booking.get('installment_plan') or _parse_installment_plan(booking.get('installment_plan_json'))
        installments_paid = int(booking.get('installments_paid') or 0) + 1
        for inst in plan:
            if int(inst.get('no') or 0) == installments_paid:
                inst['paid'] = True
                break

        amount_paid = _money(booking.get('amount_paid')) + expected
        total = _money(booking.get('total_amount'))
        remaining = (total - amount_paid).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        new_status = 'occupied' if remaining <= 0 else 'reserved'
        balance_paid_at = now if new_status == 'occupied' else booking.get('balance_paid_at')
        balance_receipt = receipt if new_status == 'occupied' else booking.get('balance_receipt')

        cursor.execute(
            """
            UPDATE student_hostel_bookings
            SET installments_paid = %s,
                installment_plan_json = %s,
                amount_paid = %s,
                balance_amount = %s,
                status = %s,
                balance_paid_at = %s,
                balance_receipt = %s
            WHERE id = %s AND status = 'reserved'
            """,
            (
                installments_paid,
                json.dumps(plan) if plan else None,
                amount_paid,
                max(remaining, Decimal('0.00')),
                new_status,
                balance_paid_at,
                balance_receipt,
                int(booking_id),
            ),
        )
        if cursor.rowcount < 1:
            return False, 'Could not update booking status.', None
        if new_status == 'occupied':
            return True, 'All installments received. Your room is now OCCUPIED.', int(booking_id)
        return True, f'Installment {installments_paid} received. Pay the next installment when due.', int(booking_id)

    return False, 'Invalid hostel payment type.', None


def allocate_hostel_room_manually(cursor, student_id, hostel_room_id):
    """Register student to a room without payment when hostel payments are disabled."""
    from datetime import datetime

    from hostel_settings import fetch_hostel_payment_settings

    sid = (student_id or '').strip()
    if not sid:
        return {'ok': False, 'message': 'Student not found.'}
    try:
        room_id = int(hostel_room_id)
    except (TypeError, ValueError):
        return {'ok': False, 'message': 'Select a valid room.'}

    ensure_student_hostel_bookings_table(cursor)
    existing = fetch_student_hostel_booking(cursor, sid)
    if existing:
        st = existing.get('status') or ''
        if st == 'occupied':
            return {'ok': False, 'message': 'You already have an occupied hostel room.'}
        return {'ok': False, 'message': 'You already have a hostel booking.'}

    blocked = _fetch_blocked_room_ids(cursor)
    if room_id in blocked:
        return {'ok': False, 'message': 'That room is no longer available.'}

    cursor.execute(
        """
        SELECT r.id, r.hostel_id, r.reference_number, r.price, h.status, h.name
        FROM hostel_rooms r
        JOIN hostels h ON h.id = r.hostel_id
        WHERE r.id = %s
        LIMIT 1
        """,
        (room_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {'ok': False, 'message': 'Room not found.'}
    if isinstance(row, dict):
        hostel_id = int(row.get('hostel_id') or 0)
        hostel_status = (row.get('status') or '').strip().lower()
        room_ref = row.get('reference_number') or ''
        room_price = float(row.get('price') or 0)
        hostel_name = row.get('name') or ''
    else:
        hostel_id = int(row[1] or 0)
        hostel_status = (row[4] or '').strip().lower()
        room_ref = row[2] or ''
        room_price = float(row[3] or 0)
        hostel_name = row[5] or ''

    if hostel_status != 'active':
        return {'ok': False, 'message': 'This hostel is not available for booking.'}
    if room_price <= 0:
        return {'ok': False, 'message': 'This room has no price set. Contact the warden.'}

    settings = fetch_hostel_payment_settings(cursor, hostel_id)
    if bool(settings.get('payments_enabled', True)):
        return {
            'ok': False,
            'message': 'Online payments are enabled for this hostel. Use the payment options to book.',
        }

    total = _money(room_price)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute(
        """
        INSERT INTO student_hostel_bookings (
            student_id, hostel_id, hostel_room_id, status,
            total_amount, deposit_amount, balance_amount,
            amount_paid, installments_paid, installment_plan_json,
            deposit_paid_at, balance_paid_at
        ) VALUES (%s, %s, %s, 'occupied', %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            sid,
            hostel_id,
            room_id,
            total,
            Decimal('0.00'),
            Decimal('0.00'),
            Decimal('0.00'),
            0,
            None,
            now,
            now,
        ),
    )
    booking_id = cursor.lastrowid
    return {
        'ok': True,
        'message': f'You have been allocated room {room_ref} at {hostel_name}. Status: OCCUPIED.',
        'booking_id': booking_id,
    }


def fetch_warden_hostel_student_occupations(cursor, search=None, occupation_filter=None):
    """
    List in-session students with their current hostel occupation (if any).
    occupation_filter: 'all' | 'assigned' | 'unassigned' | 'occupied' | 'reserved'
    """
    ensure_student_hostel_bookings_table(cursor)
    search = (search or '').strip()
    occupation_filter = (occupation_filter or 'all').strip().lower()
    if occupation_filter not in ('all', 'assigned', 'unassigned', 'occupied', 'reserved'):
        occupation_filter = 'all'

    placeholders = ','.join(['%s'] * len(BOOKING_ACTIVE_STATUSES))
    sql = f"""
        SELECT
            s.student_id,
            s.full_name,
            s.current_grade,
            s.gender,
            s.status AS student_status,
            b.id AS booking_id,
            b.status AS occupation_status,
            b.total_amount,
            b.amount_paid,
            b.created_at AS booked_at,
            h.id AS hostel_id,
            h.name AS hostel_name,
            h.location AS hostel_location,
            h.category AS hostel_category,
            r.id AS hostel_room_id,
            r.reference_number AS room_reference,
            r.price AS room_price
        FROM students s
        LEFT JOIN student_hostel_bookings b
            ON LOWER(TRIM(b.student_id)) = LOWER(TRIM(s.student_id))
           AND b.status IN ({placeholders})
           AND b.id = (
                SELECT MAX(b2.id)
                FROM student_hostel_bookings b2
                WHERE LOWER(TRIM(b2.student_id)) = LOWER(TRIM(s.student_id))
                  AND b2.status IN ({placeholders})
           )
        LEFT JOIN hostels h ON h.id = b.hostel_id
        LEFT JOIN hostel_rooms r ON r.id = b.hostel_room_id
        WHERE LOWER(TRIM(s.status)) = 'in session'
    """
    params = list(BOOKING_ACTIVE_STATUSES) + list(BOOKING_ACTIVE_STATUSES)

    if search:
        like = f'%{search}%'
        sql += """
          AND (
                LOWER(TRIM(s.student_id)) LIKE LOWER(%s)
             OR LOWER(TRIM(s.full_name)) LIKE LOWER(%s)
             OR LOWER(TRIM(COALESCE(h.name, ''))) LIKE LOWER(%s)
             OR LOWER(TRIM(COALESCE(h.location, ''))) LIKE LOWER(%s)
             OR LOWER(TRIM(COALESCE(r.reference_number, ''))) LIKE LOWER(%s)
          )
        """
        params.extend([like, like, like, like, like])

    if occupation_filter == 'assigned':
        sql += " AND b.id IS NOT NULL"
    elif occupation_filter == 'unassigned':
        sql += " AND b.id IS NULL"
    elif occupation_filter == 'occupied':
        sql += " AND b.status = 'occupied'"
    elif occupation_filter == 'reserved':
        sql += " AND b.status = 'reserved'"

    sql += " ORDER BY s.full_name ASC, s.student_id ASC"

    cursor.execute(sql, params)
    rows = cursor.fetchall() or []
    out = []
    for row in rows:
        if isinstance(row, dict):
            occ_status = (row.get('occupation_status') or '').strip().lower()
            out.append({
                'student_id': (row.get('student_id') or '').strip(),
                'full_name': (row.get('full_name') or '').strip(),
                'current_grade': (row.get('current_grade') or '').strip(),
                'gender': (row.get('gender') or '').strip(),
                'student_status': (row.get('student_status') or '').strip(),
                'booking_id': row.get('booking_id'),
                'occupation_status': occ_status,
                'has_occupation': bool(row.get('booking_id')),
                'hostel_id': row.get('hostel_id'),
                'hostel_name': (row.get('hostel_name') or '').strip(),
                'hostel_location': (row.get('hostel_location') or '').strip(),
                'hostel_category': (row.get('hostel_category') or '').strip(),
                'hostel_room_id': row.get('hostel_room_id'),
                'room_reference': (row.get('room_reference') or '').strip(),
                'room_price': float(row.get('room_price') or 0),
                'total_amount': float(row.get('total_amount') or 0),
                'amount_paid': float(row.get('amount_paid') or 0),
                'booked_at': row.get('booked_at'),
            })
        else:
            occ_status = (row[6] or '').strip().lower() if len(row) > 6 else ''
            out.append({
                'student_id': (row[0] or '').strip(),
                'full_name': (row[1] or '').strip(),
                'current_grade': (row[2] or '').strip(),
                'gender': (row[3] or '').strip() if len(row) > 3 else '',
                'student_status': (row[4] or '').strip() if len(row) > 4 else '',
                'booking_id': row[5] if len(row) > 5 else None,
                'occupation_status': occ_status,
                'has_occupation': bool(row[5]) if len(row) > 5 else False,
                'hostel_id': row[10] if len(row) > 10 else None,
                'hostel_name': (row[11] or '').strip() if len(row) > 11 else '',
                'hostel_location': (row[12] or '').strip() if len(row) > 12 else '',
                'hostel_category': (row[13] or '').strip() if len(row) > 13 else '',
                'hostel_room_id': row[14] if len(row) > 14 else None,
                'room_reference': (row[15] or '').strip() if len(row) > 15 else '',
                'room_price': float(row[16] or 0) if len(row) > 16 else 0,
                'total_amount': float(row[7] or 0) if len(row) > 7 else 0,
                'amount_paid': float(row[8] or 0) if len(row) > 8 else 0,
                'booked_at': row[9] if len(row) > 9 else None,
            })
    return out


def build_occupation_filter_options(rows):
    """Distinct gender, hostel, and price values for live filters."""
    rows = rows or []
    genders = set()
    hostels = set()
    prices = set()
    for row in rows:
        gender = (row.get('gender') or '').strip()
        if gender:
            genders.add(gender)
        hostel = (row.get('hostel_name') or '').strip()
        if hostel:
            hostels.add(hostel)
        if row.get('has_occupation'):
            price = row.get('room_price') or row.get('total_amount') or 0
            try:
                price = float(price)
            except (TypeError, ValueError):
                price = 0
            if price > 0:
                prices.add(price)
    return {
        'genders': sorted(genders, key=lambda x: x.lower()),
        'hostels': sorted(hostels, key=lambda x: x.lower()),
        'prices': sorted(prices),
    }


def booking_status_label(status):
    st = (status or '').strip().lower()
    if st == 'reserved':
        return 'RESERVED'
    if st == 'occupied':
        return 'OCCUPIED'
    if st == 'cancelled':
        return 'Cancelled'
    return st.upper() if st else '—'
