"""
Student fingerprint enrollment storage and lookup for attendance and other modules.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re

FINGERPRINT_LOCAL_SERVICE_URL = 'http://127.0.0.1:9765'

FINGER_POSITIONS = (
    ('right_thumb', 'Right thumb'),
    ('right_index', 'Right index'),
    ('right_middle', 'Right middle'),
    ('right_ring', 'Right ring'),
    ('right_little', 'Right little'),
    ('left_thumb', 'Left thumb'),
    ('left_index', 'Left index'),
    ('left_middle', 'Left middle'),
    ('left_ring', 'Left ring'),
    ('left_little', 'Left little'),
)

FINGER_CODE_SET = frozenset(code for code, _ in FINGER_POSITIONS)

_TEMPLATE_B64_RE = re.compile(r'^[A-Za-z0-9+/=\s]+$')


def finger_label(finger_code):
    for code, label in FINGER_POSITIONS:
        if code == finger_code:
            return label
    return (finger_code or '').replace('_', ' ').title()


def normalize_finger_code(raw):
    code = (raw or '').strip().lower().replace(' ', '_').replace('-', '_')
    return code if code in FINGER_CODE_SET else ''


def _template_hash(template_b64):
    try:
        raw = base64.b64decode((template_b64 or '').strip(), validate=True)
    except Exception:
        return None
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()


def validate_template_base64(template_b64):
    text = (template_b64 or '').strip()
    if len(text) < 16:
        return False, 'Fingerprint template is too short.'
    if len(text) > 500_000:
        return False, 'Fingerprint template is too large.'
    if not _TEMPLATE_B64_RE.match(text):
        return False, 'Invalid fingerprint template encoding.'
    try:
        decoded = base64.b64decode(text, validate=True)
    except Exception:
        return False, 'Fingerprint template is not valid Base64.'
    if len(decoded) < 8:
        return False, 'Fingerprint template data is invalid.'
    return True, None


def ensure_student_fingerprints_table(cursor):
    try:
        cursor.execute("SHOW TABLES LIKE 'student_fingerprints'")
        if cursor.fetchone():
            return True
    except Exception:
        pass
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_fingerprints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
                finger_code VARCHAR(32) NOT NULL,
                template_base64 LONGTEXT NOT NULL,
                template_format VARCHAR(50) NOT NULL DEFAULT 'binary_v1',
                template_hash CHAR(64) NULL,
                quality_score TINYINT UNSIGNED NULL,
                device_id VARCHAR(120) NULL,
                enrolled_by_employee_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_student_finger (student_id, finger_code),
                INDEX idx_template_hash (template_hash),
                INDEX idx_student_id (student_id),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        return True
    except Exception as exc:
        print(f'ensure_student_fingerprints_table: {exc}')
        return False


def fingerprint_row_to_dict(row):
    if not row:
        return None
    if isinstance(row, dict):
        d = dict(row)
    else:
        d = {
            'id': row[0],
            'student_id': row[1],
            'finger_code': row[2],
            'template_format': row[4] if len(row) > 4 else 'binary_v1',
            'quality_score': row[6] if len(row) > 6 else None,
            'device_id': row[7] if len(row) > 7 else None,
            'created_at': row[9] if len(row) > 9 else None,
            'updated_at': row[10] if len(row) > 10 else None,
        }
    d['finger_label'] = finger_label(d.get('finger_code'))
    d.pop('template_base64', None)
    d.pop('template_hash', None)
    if d.get('created_at') is not None:
        d['created_at'] = str(d['created_at'])
    if d.get('updated_at') is not None:
        d['updated_at'] = str(d['updated_at'])
    return d


def fetch_student_fingerprints(cursor, student_id, include_templates=False):
    ensure_student_fingerprints_table(cursor)
    if include_templates:
        cursor.execute(
            """
            SELECT id, student_id, finger_code, template_base64, template_format,
                   template_hash, quality_score, device_id, enrolled_by_employee_id,
                   created_at, updated_at
            FROM student_fingerprints
            WHERE student_id = %s
            ORDER BY finger_code ASC
            """,
            (student_id,),
        )
    else:
        cursor.execute(
            """
            SELECT id, student_id, finger_code, NULL AS template_base64, template_format,
                   template_hash, quality_score, device_id, enrolled_by_employee_id,
                   created_at, updated_at
            FROM student_fingerprints
            WHERE student_id = %s
            ORDER BY finger_code ASC
            """,
            (student_id,),
        )
    rows = []
    for row in cursor.fetchall() or []:
        item = fingerprint_row_to_dict(row)
        if include_templates and isinstance(row, dict):
            item['template_base64'] = row.get('template_base64')
        elif include_templates and row:
            item['template_base64'] = row[3]
        rows.append(item)
    return rows


def count_student_fingerprints(cursor, student_id):
    ensure_student_fingerprints_table(cursor)
    cursor.execute(
        "SELECT COUNT(*) AS c FROM student_fingerprints WHERE student_id = %s",
        (student_id,),
    )
    row = cursor.fetchone()
    if isinstance(row, dict):
        return int(row.get('c') or 0)
    return int(row[0] or 0) if row else 0


def save_student_fingerprint(
    cursor,
    student_id,
    finger_code,
    template_b64,
    template_format='binary_v1',
    quality_score=None,
    device_id=None,
    enrolled_by_employee_id=None,
):
    ensure_student_fingerprints_table(cursor)
    finger_code = normalize_finger_code(finger_code)
    if not finger_code:
        return False, 'Select a valid finger position.'
    ok, err = validate_template_base64(template_b64)
    if not ok:
        return False, err
    template_b64 = template_b64.strip()
    tpl_hash = _template_hash(template_b64)
    q = None
    if quality_score is not None:
        try:
            q = max(0, min(100, int(quality_score)))
        except (TypeError, ValueError):
            q = None
    cursor.execute(
        """
        INSERT INTO student_fingerprints
            (student_id, finger_code, template_base64, template_format, template_hash,
             quality_score, device_id, enrolled_by_employee_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            template_base64 = VALUES(template_base64),
            template_format = VALUES(template_format),
            template_hash = VALUES(template_hash),
            quality_score = VALUES(quality_score),
            device_id = VALUES(device_id),
            enrolled_by_employee_id = VALUES(enrolled_by_employee_id),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            student_id,
            finger_code,
            template_b64,
            (template_format or 'binary_v1').strip()[:50],
            tpl_hash,
            q,
            (device_id or '')[:120] or None,
            enrolled_by_employee_id,
        ),
    )
    return True, None


def delete_student_fingerprint(cursor, fingerprint_id, student_id):
    ensure_student_fingerprints_table(cursor)
    cursor.execute(
        "DELETE FROM student_fingerprints WHERE id = %s AND student_id = %s",
        (int(fingerprint_id), student_id),
    )
    return cursor.rowcount > 0


def find_student_by_fingerprint_template(cursor, template_b64, template_format=None):
    """
    Match a scanned template to a student (exact template hash match).
    Device/SDK-specific fuzzy matching can be added in a local matcher service.
    """
    ensure_student_fingerprints_table(cursor)
    ok, err = validate_template_base64(template_b64)
    if not ok:
        return None, err
    tpl_hash = _template_hash(template_b64)
    if not tpl_hash:
        return None, 'Invalid template.'
    sql = """
        SELECT sf.student_id, s.full_name, sf.finger_code, sf.template_format
        FROM student_fingerprints sf
        INNER JOIN students s ON s.student_id = sf.student_id
        WHERE sf.template_hash = %s
    """
    params = [tpl_hash]
    if template_format:
        sql += " AND sf.template_format = %s"
        params.append(template_format)
    sql += " LIMIT 1"
    cursor.execute(sql, tuple(params))
    row = cursor.fetchone()
    if not row:
        return None, None
    if isinstance(row, dict):
        return {
            'student_id': row.get('student_id'),
            'full_name': row.get('full_name'),
            'finger_code': row.get('finger_code'),
            'finger_label': finger_label(row.get('finger_code')),
            'template_format': row.get('template_format'),
        }, None
    return {
        'student_id': row[0],
        'full_name': row[1],
        'finger_code': row[2],
        'finger_label': finger_label(row[2]),
        'template_format': row[3],
    }, None


def save_fingerprints_from_json(cursor, student_id, raw_json, enrolled_by_employee_id=None):
    """Persist queued enrollments from admission form [{finger_code, template_base64, ...}]."""
    if not raw_json or not str(raw_json).strip():
        return 0, None
    try:
        items = json.loads(raw_json)
    except json.JSONDecodeError:
        return 0, 'Invalid fingerprint data.'
    if not isinstance(items, list):
        return 0, 'Invalid fingerprint data.'
    saved = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        ok, err = save_student_fingerprint(
            cursor,
            student_id,
            item.get('finger_code'),
            item.get('template_base64'),
            template_format=item.get('template_format') or 'binary_v1',
            quality_score=item.get('quality_score'),
            device_id=item.get('device_id'),
            enrolled_by_employee_id=enrolled_by_employee_id,
        )
        if not ok:
            return saved, err
        saved += 1
    return saved, None
