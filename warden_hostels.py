"""Warden portal — register and list school hostels with rooms."""
import os
import re
from datetime import datetime

from werkzeug.utils import secure_filename

from image_optimizer import optimize_and_save, static_relative_path

HOSTEL_CATEGORIES = ('Boys', 'Girls', 'Mixed', 'Staff')
HOSTEL_PHOTO_FOLDER = 'static/uploads/hostels'
HOSTEL_PHOTO_EXTENSIONS = frozenset({'png', 'jpg', 'jpeg', 'gif', 'webp'})
MAX_HOSTEL_ROOMS = 200
MAX_HOSTEL_OCCUPANTS = 5000
MAX_ROOM_OCCUPANTS = 50


def _ensure_hostel_occupant_count_column(cursor):
    try:
        cursor.execute("SHOW COLUMNS FROM hostels LIKE 'occupant_count'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE hostels
                ADD COLUMN occupant_count INT NOT NULL DEFAULT 0
                AFTER room_count
            """)
    except Exception as e:
        print(f"_ensure_hostel_occupant_count_column: {e}")


def _ensure_hostel_status_column(cursor):
    try:
        cursor.execute("SHOW COLUMNS FROM hostels LIKE 'status'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE hostels
                ADD COLUMN status ENUM('active', 'suspended') NOT NULL DEFAULT 'active'
                AFTER occupant_count
            """)
    except Exception as e:
        print(f"_ensure_hostel_status_column: {e}")


def _ensure_hostel_photo_column(cursor):
    try:
        cursor.execute("SHOW COLUMNS FROM hostels LIKE 'photo_path'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE hostels
                ADD COLUMN photo_path VARCHAR(500) NULL
                AFTER status
            """)
    except Exception as e:
        print(f"_ensure_hostel_photo_column: {e}")


def _ensure_hostel_room_occupant_count_column(cursor):
    try:
        cursor.execute("SHOW COLUMNS FROM hostel_rooms LIKE 'occupant_count'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE hostel_rooms
                ADD COLUMN occupant_count INT NOT NULL DEFAULT 0
                AFTER price
            """)
    except Exception as e:
        print(f"_ensure_hostel_room_occupant_count_column: {e}")


def ensure_hostels_tables(cursor):
    """Create hostels and hostel_rooms tables if missing."""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hostels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(80) NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT NULL,
                location VARCHAR(255) NOT NULL,
                room_count INT NOT NULL DEFAULT 0,
                occupant_count INT NOT NULL DEFAULT 0,
                status ENUM('active', 'suspended') NOT NULL DEFAULT 'active',
                photo_path VARCHAR(500) NULL,
                created_by INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_hostels_category (category),
                INDEX idx_hostels_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hostel_rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hostel_id INT NOT NULL,
                reference_number VARCHAR(80) NOT NULL,
                price DECIMAL(12,2) NOT NULL DEFAULT 0,
                occupant_count INT NOT NULL DEFAULT 0,
                sort_order INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_hostel_room_ref (hostel_id, reference_number),
                INDEX idx_hostel_rooms_hostel (hostel_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        _ensure_hostel_occupant_count_column(cursor)
        _ensure_hostel_status_column(cursor)
        _ensure_hostel_photo_column(cursor)
        _ensure_hostel_room_occupant_count_column(cursor)
    except Exception as e:
        print(f"ensure_hostels_tables: {e}")


def _allowed_hostel_photo(filename):
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in HOSTEL_PHOTO_EXTENSIONS


def save_hostel_photo(file_storage, hostel_id=None):
    """Save hostel photo; returns static-relative path or None."""
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None
    filename = (file_storage.filename or '').strip()
    if not filename or not _allowed_hostel_photo(filename):
        return None
    os.makedirs(HOSTEL_PHOTO_FOLDER, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = secure_filename(str(hostel_id or 'new'))[:20] or 'new'
    dest_path = os.path.join(HOSTEL_PHOTO_FOLDER, f'hostel_{stamp}_{suffix}.jpg')
    saved_path = optimize_and_save(file_storage, dest_path, preset='gallery')
    if not saved_path:
        return None
    return static_relative_path(saved_path)


def remove_hostel_photo_file(image_path):
    if not image_path:
        return
    rel = str(image_path).lstrip('/').replace('\\', '/')
    if rel.lower().startswith('static/'):
        rel = rel[7:]
    full = os.path.join('static', rel)
    try:
        if os.path.isfile(full):
            os.remove(full)
    except OSError as e:
        print(f"remove_hostel_photo_file: {e}")


def _parse_hostel_photo_upload(file_storage, required=False):
    """Return (photo_path, error_message)."""
    has_file = bool(
        file_storage
        and getattr(file_storage, 'filename', None)
        and (file_storage.filename or '').strip()
    )
    if not has_file:
        if required:
            return None, 'Please upload a photo of the hostel.'
        return None, None
    if not _allowed_hostel_photo(file_storage.filename):
        return None, 'Upload a valid hostel photo (JPG, PNG, GIF, or WebP).'
    photo_path = save_hostel_photo(file_storage)
    if not photo_path:
        return None, 'Could not save the hostel photo. Try another image.'
    return photo_path, None


def _hostel_code_from_name(name):
    """Short uppercase code from hostel name for auto reference numbers."""
    cleaned = re.sub(r'[^A-Za-z0-9]', '', (name or '').strip().upper())
    return (cleaned[:6] or 'HOSTEL')


def _parse_hostel_rooms_from_form(form, hostel_name):
    """Return (rooms_list, error_message)."""
    try:
        count = int(form.get('room_count') or 0)
    except (TypeError, ValueError):
        count = 0
    if count < 1:
        return None, 'Enter the number of rooms in the hostel.'
    if count > MAX_HOSTEL_ROOMS:
        return None, f'A hostel may have at most {MAX_HOSTEL_ROOMS} rooms.'

    code = _hostel_code_from_name(hostel_name)
    rooms = []
    seen_refs = set()
    for i in range(count):
        ref = (form.get(f'room_ref_{i}') or '').strip().upper()
        if not ref:
            ref = f'{code}-R{i + 1:03d}'
        if ref in seen_refs:
            return None, f'Duplicate room reference number: {ref}.'
        seen_refs.add(ref)
        price_raw = (form.get(f'room_price_{i}') or '').strip()
        try:
            price = float(price_raw) if price_raw else 0.0
        except (TypeError, ValueError):
            return None, f'Invalid price for room {i + 1}.'
        if price < 0:
            return None, f'Room {i + 1} price cannot be negative.'
        occupant_raw = (form.get(f'room_occupant_{i}') or '').strip()
        try:
            occupants = int(occupant_raw) if occupant_raw else 0
        except (TypeError, ValueError):
            return None, f'Invalid occupants for room {i + 1}.'
        if occupants < 1:
            return None, f'Enter the number of occupants for room {i + 1}.'
        if occupants > MAX_ROOM_OCCUPANTS:
            return None, f'Room {i + 1} cannot exceed {MAX_ROOM_OCCUPANTS} occupants.'
        rooms.append({
            'reference_number': ref,
            'price': round(price, 2),
            'occupant_count': occupants,
            'sort_order': i + 1,
        })
    return rooms, None


def _parse_hostel_fields_from_form(form):
    """Return (fields_dict, rooms_list, error_message)."""
    category = (form.get('hostel_category') or '').strip()
    if category not in HOSTEL_CATEGORIES:
        return None, None, 'Select a valid hostel category.'

    name = (form.get('hostel_name') or '').strip().upper()
    if not name:
        return None, None, 'Hostel name is required.'
    if len(name) > 200:
        return None, None, 'Hostel name is too long.'

    description = (form.get('hostel_description') or '').strip().upper() or None
    location = (form.get('hostel_location') or '').strip().upper()
    if not location:
        return None, None, 'Hostel location is required.'

    rooms, room_err = _parse_hostel_rooms_from_form(form, name)
    if room_err:
        return None, None, room_err

    occupant_count = sum(int(r.get('occupant_count') or 0) for r in rooms)
    return {
        'category': category,
        'name': name,
        'description': description,
        'location': location,
        'room_count': len(rooms),
        'occupant_count': occupant_count,
    }, rooms, None


def _row_to_hostel(row):
    if isinstance(row, dict):
        return {
            'id': row.get('id'),
            'category': row.get('category') or '',
            'name': row.get('name') or '',
            'description': row.get('description') or '',
            'location': row.get('location') or '',
            'room_count': int(row.get('room_count') or 0),
            'occupant_count': int(row.get('occupant_count') or 0),
            'status': (row.get('status') or 'active').strip().lower(),
            'photo_path': row.get('photo_path') or '',
            'created_by': row.get('created_by'),
            'created_at': row.get('created_at'),
            'updated_at': row.get('updated_at'),
            'rooms': [],
        }
    return {
        'id': row[0],
        'category': row[1] or '',
        'name': row[2] or '',
        'description': row[3] or '',
        'location': row[4] or '',
        'room_count': int(row[5] or 0),
        'occupant_count': int(row[6] or 0),
        'status': (row[7] or 'active').strip().lower(),
        'photo_path': row[8] or '',
        'created_by': row[9],
        'created_at': row[10],
        'updated_at': row[11],
        'rooms': [],
    }


def _row_to_room(row):
    if isinstance(row, dict):
        return {
            'id': row.get('id'),
            'reference_number': row.get('reference_number') or '',
            'price': float(row.get('price') or 0),
            'occupant_count': int(row.get('occupant_count') or 0),
            'sort_order': int(row.get('sort_order') or 0),
        }
    return {
        'id': row[0],
        'reference_number': row[1] or '',
        'price': float(row[2] or 0),
        'occupant_count': int(row[3] or 0),
        'sort_order': int(row[4] or 0),
    }


def _attach_rooms_to_hostels(cursor, hostels):
    hostel_ids = [int(h['id']) for h in hostels if h.get('id')]
    if not hostel_ids:
        return hostels
    placeholders = ','.join(['%s'] * len(hostel_ids))
    cursor.execute(f"""
        SELECT id, hostel_id, reference_number, price, occupant_count, sort_order
        FROM hostel_rooms
        WHERE hostel_id IN ({placeholders})
        ORDER BY hostel_id ASC, sort_order ASC, id ASC
    """, hostel_ids)
    by_id = {h['id']: h for h in hostels}
    for rr in cursor.fetchall() or []:
        if isinstance(rr, dict):
            hid = int(rr.get('hostel_id') or 0)
            room = {
                'id': rr.get('id'),
                'reference_number': rr.get('reference_number') or '',
                'price': float(rr.get('price') or 0),
                'occupant_count': int(rr.get('occupant_count') or 0),
                'sort_order': int(rr.get('sort_order') or 0),
            }
        else:
            hid = int(rr[1] or 0)
            room = {
                'id': rr[0],
                'reference_number': rr[2] or '',
                'price': float(rr[3] or 0),
                'occupant_count': int(rr[4] or 0),
                'sort_order': int(rr[5] or 0),
            }
        hostel = by_id.get(hid)
        if hostel is not None:
            hostel['rooms'].append(room)
    for hostel in hostels:
        room_occupants = sum(int(r.get('occupant_count') or 0) for r in hostel.get('rooms') or [])
        hostel['room_occupant_total'] = room_occupants
        hostel['occupant_count'] = room_occupants
    return hostels


_HOSTEL_SELECT_COLUMNS = """
    id, category, name, description, location, room_count, occupant_count, status, photo_path,
    created_by, created_at, updated_at
"""


def _insert_hostel_rooms(cursor, hostel_id, rooms):
    for room in rooms:
        cursor.execute(
            """
            INSERT INTO hostel_rooms (hostel_id, reference_number, price, occupant_count, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (hostel_id, room['reference_number'], room['price'], room['occupant_count'], room['sort_order']),
        )


def fetch_hostel_by_id(cursor, hostel_id):
    """Return one hostel with rooms, or None."""
    ensure_hostels_tables(cursor)
    try:
        hostel_id = int(hostel_id)
    except (TypeError, ValueError):
        return None
    cursor.execute(f"""
        SELECT {_HOSTEL_SELECT_COLUMNS}
        FROM hostels
        WHERE id = %s
        LIMIT 1
    """, (hostel_id,))
    row = cursor.fetchone()
    if not row:
        return None
    hostel = _row_to_hostel(row)
    _attach_rooms_to_hostels(cursor, [hostel])
    return hostel


def fetch_hostels_with_rooms(cursor):
    """Return hostels with nested rooms list."""
    ensure_hostels_tables(cursor)
    cursor.execute(f"""
        SELECT {_HOSTEL_SELECT_COLUMNS}
        FROM hostels
        ORDER BY name ASC, id ASC
    """)
    rows = cursor.fetchall() or []
    hostels = [_row_to_hostel(row) for row in rows]
    return _attach_rooms_to_hostels(cursor, hostels)


def register_hostel_from_request(cursor, form, employee_id=None, photo_file=None):
    """Validate form and insert hostel + rooms. Returns {ok, message}."""
    ensure_hostels_tables(cursor)
    fields, rooms, err = _parse_hostel_fields_from_form(form)
    if err:
        return {'ok': False, 'message': err}

    photo_path, photo_err = _parse_hostel_photo_upload(photo_file, required=True)
    if photo_err:
        return {'ok': False, 'message': photo_err}

    cursor.execute(
        """
        SELECT id FROM hostels
        WHERE UPPER(TRIM(name)) = %s AND UPPER(TRIM(location)) = %s
        LIMIT 1
        """,
        (fields['name'], fields['location']),
    )
    if cursor.fetchone():
        if photo_path:
            remove_hostel_photo_file(photo_path)
        return {'ok': False, 'message': 'A hostel with this name and location already exists.'}

    created_by = None
    if employee_id is not None:
        try:
            created_by = int(employee_id)
        except (TypeError, ValueError):
            created_by = None

    cursor.execute(
        """
        INSERT INTO hostels (
            category, name, description, location, room_count, occupant_count, status, photo_path, created_by
        ) VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s)
        """,
        (
            fields['category'], fields['name'], fields['description'], fields['location'],
            fields['room_count'], fields['occupant_count'], photo_path, created_by,
        ),
    )
    hostel_id = cursor.lastrowid
    _insert_hostel_rooms(cursor, hostel_id, rooms)
    return {
        'ok': True,
        'message': (
            f'Hostel "{fields["name"]}" registered with {len(rooms)} room(s) '
            f'({fields["occupant_count"]} occupant{"s" if fields["occupant_count"] != 1 else ""} across rooms).'
        ),
    }


def update_hostel_from_request(cursor, hostel_id, form, photo_file=None):
    """Update hostel details and replace its rooms."""
    ensure_hostels_tables(cursor)
    hostel = fetch_hostel_by_id(cursor, hostel_id)
    if not hostel:
        return {'ok': False, 'message': 'Hostel not found.'}

    fields, rooms, err = _parse_hostel_fields_from_form(form)
    if err:
        return {'ok': False, 'message': err}

    photo_path = hostel.get('photo_path') or ''
    new_photo_path, photo_err = _parse_hostel_photo_upload(photo_file, required=False)
    if photo_err:
        return {'ok': False, 'message': photo_err}
    if new_photo_path:
        if photo_path and photo_path != new_photo_path:
            remove_hostel_photo_file(photo_path)
        photo_path = new_photo_path

    cursor.execute(
        """
        SELECT id FROM hostels
        WHERE UPPER(TRIM(name)) = %s AND UPPER(TRIM(location)) = %s AND id != %s
        LIMIT 1
        """,
        (fields['name'], fields['location'], int(hostel_id)),
    )
    if cursor.fetchone():
        return {'ok': False, 'message': 'Another hostel with this name and location already exists.'}

    cursor.execute(
        """
        UPDATE hostels
        SET category = %s, name = %s, description = %s, location = %s,
            room_count = %s, occupant_count = %s, photo_path = %s
        WHERE id = %s
        """,
        (
            fields['category'], fields['name'], fields['description'], fields['location'],
            fields['room_count'], fields['occupant_count'], photo_path or None, int(hostel_id),
        ),
    )
    cursor.execute("DELETE FROM hostel_rooms WHERE hostel_id = %s", (int(hostel_id),))
    _insert_hostel_rooms(cursor, int(hostel_id), rooms)
    return {
        'ok': True,
        'message': (
            f'Hostel "{fields["name"]}" updated with {len(rooms)} room(s) '
            f'({fields["occupant_count"]} occupant{"s" if fields["occupant_count"] != 1 else ""} across rooms).'
        ),
    }


def toggle_hostel_suspend(cursor, hostel_id):
    """Toggle hostel between active and suspended."""
    ensure_hostels_tables(cursor)
    hostel = fetch_hostel_by_id(cursor, hostel_id)
    if not hostel:
        return {'ok': False, 'message': 'Hostel not found.'}
    current = (hostel.get('status') or 'active').strip().lower()
    new_status = 'suspended' if current == 'active' else 'active'
    cursor.execute(
        "UPDATE hostels SET status = %s WHERE id = %s",
        (new_status, int(hostel_id)),
    )
    label = 'suspended' if new_status == 'suspended' else 'reactivated'
    return {'ok': True, 'message': f'Hostel {label} successfully.'}


def delete_hostel(cursor, hostel_id):
    """Delete a hostel and its rooms."""
    ensure_hostels_tables(cursor)
    hostel = fetch_hostel_by_id(cursor, hostel_id)
    if not hostel:
        return {'ok': False, 'message': 'Hostel not found.'}
    name = hostel.get('name') or 'Hostel'
    remove_hostel_photo_file(hostel.get('photo_path'))
    cursor.execute("DELETE FROM hostel_rooms WHERE hostel_id = %s", (int(hostel_id),))
    cursor.execute("DELETE FROM hostels WHERE id = %s", (int(hostel_id),))
    return {'ok': True, 'message': f'Hostel "{name}" deleted successfully.'}
