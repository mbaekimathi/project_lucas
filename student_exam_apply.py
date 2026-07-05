"""Student portal — apply for examinations."""
from datetime import date
from hashlib import sha256

# Suggested defaults when enabling requirements in the registration UI
DEFAULT_CLASS_ATTENDANCE_PCT = 50.0
DEFAULT_SUBJECT_ATTENDANCE_PCT = 50.0
DEFAULT_FEE_PAYMENT_PCT = 100.0


def _apply_rules_key(exam_name, exam_type, academic_year_id, term_id):
    return (
        (exam_name or '').strip().upper(),
        (exam_type or '').strip().upper(),
        int(academic_year_id) if academic_year_id else 0,
        int(term_id) if term_id else 0,
    )


def _parse_optional_pct(value):
    if value is None or value == '':
        return None
    try:
        pct = float(value)
    except (TypeError, ValueError):
        return None
    if pct < 0 or pct > 100:
        return None
    return round(pct, 1)


def _rule_threshold_pct(rules, db_key, norm_key):
    """Read a threshold from DB column names or already-normalized keys."""
    for key in (db_key, norm_key):
        if key not in rules:
            continue
        val = rules.get(key)
        if val is None or val == '':
            continue
        parsed = _parse_optional_pct(val)
        if parsed is not None:
            return parsed
    return None


def normalize_apply_rules(rules):
    """Normalize DB/API rules. NULL threshold = requirement off."""
    empty = {
        'class_min': None,
        'subject_min': None,
        'fee_min': None,
        'any_enabled': False,
        'class_enabled': False,
        'subject_enabled': False,
        'fee_enabled': False,
    }
    if not rules:
        return empty
    class_min = _rule_threshold_pct(rules, 'class_attendance_min_pct', 'class_min')
    subject_min = _rule_threshold_pct(rules, 'subject_attendance_min_pct', 'subject_min')
    fee_min = _rule_threshold_pct(rules, 'fee_payment_min_pct', 'fee_min')
    return {
        'class_min': class_min,
        'subject_min': subject_min,
        'fee_min': fee_min,
        'class_enabled': class_min is not None,
        'subject_enabled': subject_min is not None,
        'fee_enabled': fee_min is not None,
        'any_enabled': any(x is not None for x in (class_min, subject_min, fee_min)),
    }


def parse_apply_requirements_payload(payload):
    """Parse registration form payload into normalized rules for storage."""
    payload = payload if isinstance(payload, dict) else {}
    return normalize_apply_rules({
        'class_attendance_min_pct': payload.get('class_attendance_min_pct'),
        'subject_attendance_min_pct': payload.get('subject_attendance_min_pct'),
        'fee_payment_min_pct': payload.get('fee_payment_min_pct'),
    })


def fetch_exam_apply_rules(cursor, exam_name, exam_type, academic_year_id, term_id):
    """Load application requirements for one registered exam group."""
    en = (exam_name or '').strip().upper()
    et = (exam_type or '').strip().upper()
    if not en or not academic_year_id or not term_id:
        return normalize_apply_rules(None)
    try:
        cursor.execute(
            """
            SELECT class_attendance_min_pct, subject_attendance_min_pct, fee_payment_min_pct
            FROM registered_exam_apply_rules
            WHERE exam_name = %s AND exam_type = %s
              AND academic_year_id = %s AND term_id = %s
            LIMIT 1
            """,
            (en, et, int(academic_year_id), int(term_id)),
        )
        row = cursor.fetchone()
    except Exception:
        return normalize_apply_rules(None)
    if not row:
        return normalize_apply_rules(None)
    if isinstance(row, dict):
        raw = row
    else:
        raw = {
            'class_attendance_min_pct': row[0] if len(row) > 0 else None,
            'subject_attendance_min_pct': row[1] if len(row) > 1 else None,
            'fee_payment_min_pct': row[2] if len(row) > 2 else None,
        }
    return normalize_apply_rules(raw)


def save_exam_apply_rules(cursor, exam_name, exam_type, academic_year_id, term_id, apply_rules):
    """Upsert optional application requirements (NULL pct = off)."""
    en = (exam_name or '').strip().upper()
    et = (exam_type or '').strip().upper()
    if not en or not academic_year_id or not term_id:
        return False
    norm = normalize_apply_rules(apply_rules if isinstance(apply_rules, dict) else {
        'class_attendance_min_pct': apply_rules,
    })
    if not norm['any_enabled']:
        delete_exam_apply_rules(cursor, en, et, academic_year_id, term_id)
        return True
    cursor.execute(
        """
        INSERT INTO registered_exam_apply_rules (
            exam_name, exam_type, academic_year_id, term_id,
            class_attendance_min_pct, subject_attendance_min_pct, fee_payment_min_pct
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            class_attendance_min_pct = VALUES(class_attendance_min_pct),
            subject_attendance_min_pct = VALUES(subject_attendance_min_pct),
            fee_payment_min_pct = VALUES(fee_payment_min_pct),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            en,
            et,
            int(academic_year_id),
            int(term_id),
            norm['class_min'],
            norm['subject_min'],
            norm['fee_min'],
        ),
    )
    return True


def delete_exam_apply_rules(cursor, exam_name, exam_type, academic_year_id, term_id):
    en = (exam_name or '').strip().upper()
    et = (exam_type or '').strip().upper()
    if not en or not academic_year_id or not term_id:
        return
    try:
        cursor.execute(
            """
            DELETE FROM registered_exam_apply_rules
            WHERE exam_name = %s AND exam_type = %s
              AND academic_year_id = %s AND term_id = %s
            """,
            (en, et, int(academic_year_id), int(term_id)),
        )
    except Exception:
        pass


def fetch_apply_rules_for_sitting(cursor, sitting):
    return fetch_exam_apply_rules(
        cursor,
        sitting.get('exam_name'),
        sitting.get('exam_type'),
        sitting.get('academic_year_id'),
        sitting.get('term_id'),
    )


def fetch_all_exam_apply_rules_map(cursor):
    """Map exam group key -> normalized apply rules for exam evaluation UI."""
    out = {}
    try:
        cursor.execute(
            """
            SELECT exam_name, exam_type, academic_year_id, term_id,
                   class_attendance_min_pct, subject_attendance_min_pct, fee_payment_min_pct
            FROM registered_exam_apply_rules
            """
        )
        for row in cursor.fetchall() or []:
            if isinstance(row, dict):
                raw = row
            else:
                raw = {
                    'exam_name': row[0], 'exam_type': row[1],
                    'academic_year_id': row[2], 'term_id': row[3],
                    'class_attendance_min_pct': row[4] if len(row) > 4 else None,
                    'subject_attendance_min_pct': row[5] if len(row) > 5 else None,
                    'fee_payment_min_pct': row[6] if len(row) > 6 else None,
                }
            key = '|'.join([
                str((raw.get('exam_name') or '').strip().upper()),
                str((raw.get('exam_type') or '').strip().upper()),
                str(raw.get('academic_year_id') or ''),
                str(raw.get('term_id') or ''),
            ])
            out[key] = normalize_apply_rules(raw)
    except Exception:
        pass
    return out


def exam_group_key(exam_name, exam_type, academic_year_id, term_id):
    return '|'.join([
        str((exam_name or '').strip().upper()),
        str((exam_type or '').strip().upper()),
        str(academic_year_id or ''),
        str(term_id or ''),
    ])


def exam_sitting_key(year_name, term_name, exam_name):
    raw = '|'.join([
        (year_name or '').strip().lower(),
        (term_name or '').strip().lower(),
        (exam_name or '').strip().lower(),
    ])
    return sha256(raw.encode('utf-8')).hexdigest()[:16]


def _format_exam_date(ed):
    if ed is None:
        return ''
    if hasattr(ed, 'strftime'):
        return ed.strftime('%Y-%m-%d')
    return str(ed)[:10]


def _group_open_exam_rows(rows):
    """Group exam timetable rows into logical sittings (year + term + exam name)."""
    order = []
    groups = {}
    for row in rows or []:
        yn = row.get('year_name') or ''
        tn = row.get('term_name') or ''
        en = row.get('exam_name') or ''
        key = exam_sitting_key(yn, tn, en)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)

    sittings = []
    today = date.today().isoformat()
    for key in order:
        items = groups[key]
        first = items[0]
        dates = sorted(set(_format_exam_date(r.get('exam_date')) for r in items if _format_exam_date(r.get('exam_date'))))
        exam_date_str = dates[0] if len(dates) == 1 else ''
        exam_date_note = ''
        if len(dates) > 1:
            exam_date_note = f'{dates[0]} – {dates[-1]}'
        # Hide sittings whose last date is more than 30 days in the past
        last_date = dates[-1] if dates else ''
        if last_date and last_date < today:
            try:
                from datetime import datetime as dt
                ld = dt.strptime(last_date, '%Y-%m-%d').date()
                if (date.today() - ld).days > 30:
                    continue
            except ValueError:
                pass
        parts = [x for x in (first.get('year_name'), first.get('term_name'), first.get('exam_name')) if x]
        rep_id = min(int(r.get('id') or 0) for r in items if r.get('id') is not None) or first.get('id')
        sittings.append({
            'sitting_key': key,
            'exam_id': rep_id,
            'exam_name': first.get('exam_name') or '',
            'exam_type': first.get('exam_type') or '',
            'year_name': first.get('year_name') or '',
            'term_name': first.get('term_name') or '',
            'label': ' · '.join(parts) if parts else 'Exam',
            'exam_date_str': exam_date_str,
            'exam_date_note': exam_date_note,
            'status': first.get('status') or 'scheduled',
            'academic_year_id': first.get('academic_year_id'),
            'term_id': first.get('term_id'),
            'academic_level_id': first.get('academic_level_id'),
        })
    return sittings


def fetch_open_exam_sittings(cursor, academic_level_id):
    if not academic_level_id:
        return []
    cursor.execute(
        """
        SELECT e.id, e.exam_name, e.exam_type, e.exam_date, e.status,
               e.academic_year_id, e.term_id, e.academic_level_id,
               ay.year_name, t.term_name
        FROM exams e
        INNER JOIN academic_years ay ON e.academic_year_id = ay.id
        INNER JOIN terms t ON e.term_id = t.id
        WHERE e.academic_level_id = %s
          AND LOWER(TRIM(COALESCE(e.status, ''))) IN ('scheduled', 'ongoing')
        ORDER BY e.exam_date ASC, e.exam_name ASC, e.id ASC
        """,
        (int(academic_level_id),),
    )
    rows = []
    for r in cursor.fetchall() or []:
        if isinstance(r, dict):
            rows.append(dict(r))
        else:
            rows.append({
                'id': r[0], 'exam_name': r[1], 'exam_type': r[2], 'exam_date': r[3],
                'status': r[4], 'academic_year_id': r[5], 'term_id': r[6],
                'academic_level_id': r[7], 'year_name': r[8], 'term_name': r[9],
            })
    return _group_open_exam_rows(rows)


def fetch_student_exam_applications(cursor, student_id):
    cursor.execute(
        """
        SELECT id, sitting_key, exam_id, exam_name, exam_type,
               year_name, term_name, exam_date_str, notes, status, applied_at,
               review_notes
        FROM student_exam_applications
        WHERE TRIM(student_id) = TRIM(%s)
        ORDER BY applied_at DESC, id DESC
        """,
        (student_id,),
    )
    out = []
    for r in cursor.fetchall() or []:
        if isinstance(r, dict):
            out.append(dict(r))
        else:
            out.append({
                'id': r[0], 'sitting_key': r[1], 'exam_id': r[2], 'exam_name': r[3],
                'exam_type': r[4], 'year_name': r[5], 'term_name': r[6],
                'exam_date_str': r[7], 'notes': r[8], 'status': r[9],
                'applied_at': r[10], 'review_notes': r[11],
            })
    for row in out:
        parts = [x for x in (row.get('year_name'), row.get('term_name'), row.get('exam_name')) if x]
        row['label'] = ' · '.join(parts) if parts else (row.get('exam_name') or 'Exam')
        at = row.get('applied_at')
        if at and hasattr(at, 'strftime'):
            row['applied_at_str'] = at.strftime('%d %b %Y, %H:%M')
        else:
            row['applied_at_str'] = str(at)[:16] if at else '—'
    return out


def submit_student_exam_application(cursor, student_id, sitting_key, open_sittings, notes='', student_meta=None):
    sitting_key = (sitting_key or '').strip()
    if not sitting_key:
        return False, 'Please select an exam to apply for.'
    sitting = next((s for s in (open_sittings or []) if s.get('sitting_key') == sitting_key), None)
    if not sitting:
        return False, 'That exam is no longer open for applications.'
    if student_meta and sitting.get('term_id'):
        apply_rules = sitting.get('apply_rules')
        if apply_rules is None:
            apply_rules = fetch_apply_rules_for_sitting(cursor, sitting)
        eligibility = build_exam_apply_eligibility(
            cursor,
            student_id,
            student_meta,
            sitting.get('term_id'),
            sitting.get('academic_year_id'),
            apply_rules=apply_rules,
        )
        if apply_rules.get('any_enabled') and not eligibility.get('eligible'):
            return False, eligibility_block_message(eligibility)
    notes = (notes or '').strip()[:500]
    cursor.execute(
        """
        SELECT id, status FROM student_exam_applications
        WHERE TRIM(student_id) = TRIM(%s) AND sitting_key = %s
        LIMIT 1
        """,
        (student_id, sitting_key),
    )
    existing = cursor.fetchone()
    if existing:
        st = existing.get('status') if isinstance(existing, dict) else existing[1]
        if st in ('pending', 'approved'):
            return False, 'You have already applied for this exam.'
        if st == 'withdrawn':
            cursor.execute(
                """
                UPDATE student_exam_applications
                SET status = 'pending', notes = %s, applied_at = CURRENT_TIMESTAMP,
                    reviewed_at = NULL, reviewed_by = NULL, review_notes = NULL,
                    exam_id = %s, exam_name = %s, exam_type = %s,
                    academic_year_id = %s, term_id = %s, academic_level_id = %s,
                    year_name = %s, term_name = %s, exam_date_str = %s
                WHERE TRIM(student_id) = TRIM(%s) AND sitting_key = %s
                """,
                (
                    notes or None,
                    sitting.get('exam_id'),
                    sitting.get('exam_name'),
                    sitting.get('exam_type') or None,
                    sitting.get('academic_year_id'),
                    sitting.get('term_id'),
                    sitting.get('academic_level_id'),
                    sitting.get('year_name'),
                    sitting.get('term_name'),
                    sitting.get('exam_date_str') or sitting.get('exam_date_note') or None,
                    student_id,
                    sitting_key,
                ),
            )
            return True, 'Your application has been resubmitted and is pending review.'
    else:
        cursor.execute(
            """
            INSERT INTO student_exam_applications (
                student_id, sitting_key, exam_id, exam_name, exam_type,
                academic_year_id, term_id, academic_level_id,
                year_name, term_name, exam_date_str, notes, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """,
            (
                student_id,
                sitting_key,
                sitting.get('exam_id'),
                sitting.get('exam_name'),
                sitting.get('exam_type') or None,
                sitting.get('academic_year_id'),
                sitting.get('term_id'),
                sitting.get('academic_level_id'),
                sitting.get('year_name'),
                sitting.get('term_name'),
                sitting.get('exam_date_str') or sitting.get('exam_date_note') or None,
                notes or None,
            ),
        )
    return True, 'Your exam application has been submitted. The examinations office will review it.'


def merge_sittings_with_applications(open_sittings, applications):
    applied_keys = {a.get('sitting_key') for a in (applications or []) if a.get('status') in ('pending', 'approved')}
    available = []
    for s in open_sittings or []:
        row = dict(s)
        row['already_applied'] = s.get('sitting_key') in applied_keys
        eligible = row.get('eligible_to_apply')
        if eligible is None:
            eligible = True
        row['can_apply'] = not row['already_applied'] and eligible
        available.append(row)
    return available


def serialize_sittings_for_student_apply(exam_sittings):
    """JSON-safe sitting list for student apply page (per-exam eligibility)."""
    out = []
    for ex in exam_sittings or []:
        if ex.get('already_applied'):
            continue
        elig = ex.get('eligibility') or {}
        out.append({
            'sitting_key': ex.get('sitting_key') or '',
            'exam_name': ex.get('exam_name') or 'Exam',
            'term_label': elig.get('term_label') or ex.get('term_name') or '',
            'can_apply': bool(ex.get('can_apply')),
            'requirements_enabled': bool(elig.get('requirements_enabled')),
            'eligible': bool(elig.get('eligible', True)),
            'unmet_messages': list(elig.get('unmet_messages') or []),
            'class_attendance': _serialize_eligibility_metric(elig.get('class_attendance') or {}),
            'subject_attendance': _serialize_eligibility_metric(elig.get('subject_attendance') or {}),
            'fee_payment': _serialize_eligibility_metric(elig.get('fee_payment') or {}, is_fee=True),
        })
    return out


def _serialize_eligibility_metric(metric, is_fee=False):
    metric = metric or {}
    base = {
        'label': metric.get('label') or '',
        'required_enabled': bool(metric.get('required_enabled')),
        'required_pct': metric.get('required_pct'),
        'met': bool(metric.get('met')),
        'pct': metric.get('pct'),
    }
    if is_fee:
        base.update({
            'has_structure': bool(metric.get('has_structure')),
            'total_paid': float(metric.get('total_paid') or 0),
            'total_amount': float(metric.get('total_amount') or 0),
        })
    else:
        base.update({
            'has_data': bool(metric.get('has_data')),
            'present': int(metric.get('present') or 0),
            'total': int(metric.get('total') or 0),
        })
    return base


def _fee_structure_category_clause(student_category):
    """Return (WHERE fragment, ORDER BY CASE) for fee structure category matching."""
    cat = (student_category or '').strip().lower()
    if cat == 'self sponsored':
        return (
            " AND (fs.category = 'self sponsored' OR fs.category = 'both')",
            """CASE WHEN fs.category = 'self sponsored' THEN 1 WHEN fs.category = 'both' THEN 2 ELSE 3 END""",
        )
    if cat == 'sponsored':
        return (
            " AND (fs.category = 'sponsored' OR fs.category = 'both')",
            """CASE WHEN fs.category = 'sponsored' THEN 1 WHEN fs.category = 'both' THEN 2 ELSE 3 END""",
        )
    if cat == 'both':
        return (
            '',
            """CASE
                WHEN fs.category = 'both' THEN 1
                WHEN fs.category = 'self sponsored' THEN 2
                WHEN fs.category = 'sponsored' THEN 3
                ELSE 4
            END""",
        )
    return (" AND fs.category = 'both'", '1')


def _term_attendance_summary(cursor, student_id, term_id, *, class_mode=True):
    """Attendance rate for one student/term (class register or subject sessions)."""
    sid = (student_id or '').strip()
    empty = {'has_data': False, 'present': 0, 'total': 0, 'pct': 0.0}
    if not sid or not term_id:
        return empty
    try:
        if class_mode:
            cursor.execute(
                """
                SELECT sar.present
                FROM student_attendance_records sar
                WHERE sar.student_id = %s AND sar.term_id = %s
                  AND COALESCE(sar.subject_id, 0) = 0
                """,
                (sid, int(term_id)),
            )
        else:
            cursor.execute(
                """
                SELECT sar.present
                FROM student_attendance_records sar
                WHERE sar.student_id = %s AND sar.term_id = %s
                  AND COALESCE(sar.subject_id, 0) > 0
                """,
                (sid, int(term_id)),
            )
        rows = cursor.fetchall() or []
    except Exception:
        return empty
    total = len(rows)
    if not total:
        return empty
    present = 0
    for r in rows:
        pres = r.get('present') if isinstance(r, dict) else r[0]
        if pres is not None and bool(int(pres)):
            present += 1
    pct = round(100.0 * present / total, 1)
    return {'has_data': True, 'present': present, 'total': total, 'pct': pct}


def _term_fee_payment_summary(cursor, student_id, academic_level_id, academic_year_id, term_id, student_category):
    """Fee payment progress for one student/term."""
    sid = (student_id or '').strip()
    empty = {
        'has_structure': False,
        'fee_name': '',
        'total_amount': 0.0,
        'total_paid': 0.0,
        'pct': 0.0,
        'balance': 0.0,
    }
    if not sid or not academic_level_id or not term_id:
        return empty
    cat_sql, cat_order = _fee_structure_category_clause(student_category)
    params = [int(academic_level_id), int(term_id)]
    year_sql = ''
    if academic_year_id:
        year_sql = ' AND fs.academic_year_id = %s'
        params.append(int(academic_year_id))
    try:
        cursor.execute(
            f"""
            SELECT fs.id, fs.fee_name, fs.total_amount
            FROM fee_structures fs
            WHERE fs.academic_level_id = %s
              AND fs.term_id = %s
              AND fs.status = 'active'
              {year_sql}
              {cat_sql}
            ORDER BY {cat_order}, fs.created_at DESC
            LIMIT 1
            """,
            tuple(params),
        )
        fs = cursor.fetchone()
    except Exception:
        return empty
    if not fs:
        return empty
    if isinstance(fs, dict):
        fs_id = fs.get('id')
        fee_name = (fs.get('fee_name') or '').strip()
        total_amount = float(fs.get('total_amount') or 0)
    else:
        fs_id = fs[0]
        fee_name = (fs[1] or '').strip() if len(fs) > 1 else ''
        total_amount = float(fs[2] if len(fs) > 2 and fs[2] else 0)
    cursor.execute(
        """
        SELECT COALESCE(SUM(amount_paid), 0) AS total_paid
        FROM student_payments
        WHERE student_id = %s AND fee_structure_id = %s
        """,
        (sid, fs_id),
    )
    pay = cursor.fetchone()
    total_paid = float(
        (pay.get('total_paid') if isinstance(pay, dict) else pay[0]) or 0
    ) if pay else 0.0
    if total_amount <= 0:
        pct = 100.0 if total_paid >= 0 else 0.0
        balance = 0.0
    else:
        pct = min(100.0, round(100.0 * total_paid / total_amount, 1))
        balance = max(0.0, total_amount - total_paid)
    return {
        'has_structure': True,
        'fee_name': fee_name,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'pct': pct,
        'balance': balance,
    }


def _term_label(cursor, term_id, fallback=''):
    if not term_id:
        return fallback or 'This term'
    try:
        cursor.execute(
            """
            SELECT t.term_name, ay.year_name
            FROM terms t
            LEFT JOIN academic_years ay ON ay.id = t.academic_year_id
            WHERE t.id = %s
            LIMIT 1
            """,
            (int(term_id),),
        )
        row = cursor.fetchone()
    except Exception:
        return fallback or 'This term'
    if not row:
        return fallback or 'This term'
    if isinstance(row, dict):
        tn = (row.get('term_name') or '').strip()
        yn = (row.get('year_name') or '').strip()
    else:
        tn = (row[0] or '').strip() if len(row) > 0 else ''
        yn = (row[1] or '').strip() if len(row) > 1 else ''
    parts = [x for x in (yn, tn) if x]
    return ' · '.join(parts) if parts else (fallback or 'This term')


def build_exam_apply_eligibility(cursor, student_id, student_meta, term_id, academic_year_id=None, apply_rules=None):
    """Check whether a student meets exam application requirements for a term."""
    level_id = (student_meta or {}).get('academic_level_id')
    category = (student_meta or {}).get('student_category') or ''
    norm = normalize_apply_rules(apply_rules)
    class_att = _term_attendance_summary(cursor, student_id, term_id, class_mode=True)
    subject_att = _term_attendance_summary(cursor, student_id, term_id, class_mode=False)
    fee = _term_fee_payment_summary(
        cursor, student_id, level_id, academic_year_id, term_id, category,
    )
    elig_core = _eligibility_from_summaries(class_att, subject_att, fee, norm)

    unmet = []
    if norm['any_enabled']:
        if norm['class_enabled'] and not elig_core['class_met']:
            if not class_att['has_data']:
                unmet.append('class attendance has not been recorded yet')
            else:
                unmet.append(
                    f'class attendance is {class_att["pct"]:.1f}% (minimum {norm["class_min"]:.0f}%)'
                )
        if norm['subject_enabled'] and not elig_core['subject_met']:
            if not subject_att['has_data']:
                unmet.append('subject attendance has not been recorded yet')
            else:
                unmet.append(
                    f'subject attendance is {subject_att["pct"]:.1f}% (minimum {norm["subject_min"]:.0f}%)'
                )
        if norm['fee_enabled'] and not elig_core['fee_met']:
            if not fee['has_structure']:
                unmet.append('fees for this term are not set up yet')
            else:
                unmet.append(
                    f'fee payment is {fee["pct"]:.1f}% (must be {norm["fee_min"]:.0f}%)'
                )

    return {
        'term_id': term_id,
        'term_label': _term_label(cursor, term_id),
        'eligible': elig_core['eligible'],
        'requirements_enabled': norm['any_enabled'],
        'apply_rules': norm,
        'class_attendance': {
            **class_att,
            'required_pct': norm['class_min'],
            'required_enabled': norm['class_enabled'],
            'met': elig_core['class_met'],
            'label': 'Class attendance',
        },
        'subject_attendance': {
            **subject_att,
            'required_pct': norm['subject_min'],
            'required_enabled': norm['subject_enabled'],
            'met': elig_core['subject_met'],
            'label': 'Subject attendance',
        },
        'fee_payment': {
            **fee,
            'required_pct': norm['fee_min'],
            'required_enabled': norm['fee_enabled'],
            'met': elig_core['fee_met'],
            'label': 'Term fee payment',
        },
        'unmet_messages': unmet,
    }


def build_eligibility_for_sittings(cursor, student_id, student_meta, open_sittings):
    """Build eligibility keyed by term_id and attach to each sitting."""
    by_term = {}
    rules_cache = {}
    for sitting in open_sittings or []:
        rk = _apply_rules_key(
            sitting.get('exam_name'),
            sitting.get('exam_type'),
            sitting.get('academic_year_id'),
            sitting.get('term_id'),
        )
        if rk not in rules_cache:
            rules_cache[rk] = fetch_exam_apply_rules(
                cursor,
                sitting.get('exam_name'),
                sitting.get('exam_type'),
                sitting.get('academic_year_id'),
                sitting.get('term_id'),
            )
    enriched = []
    for sitting in open_sittings or []:
        row = dict(sitting)
        rk = _apply_rules_key(
            row.get('exam_name'),
            row.get('exam_type'),
            row.get('academic_year_id'),
            row.get('term_id'),
        )
        apply_rules = rules_cache.get(rk) or normalize_apply_rules(None)
        row['apply_rules'] = apply_rules
        tid = sitting.get('term_id')
        if tid:
            key = int(tid)
            cache_key = (key, rk)
            if cache_key not in by_term:
                by_term[cache_key] = build_exam_apply_eligibility(
                    cursor,
                    student_id,
                    student_meta,
                    key,
                    sitting.get('academic_year_id'),
                    apply_rules=apply_rules,
                )
            row['eligibility'] = by_term[cache_key]
        else:
            row['eligibility'] = None
        if apply_rules.get('any_enabled'):
            row['eligible_to_apply'] = bool(row['eligibility'] and row['eligibility'].get('eligible'))
        else:
            row['eligible_to_apply'] = True
        enriched.append(row)
    primary = None
    if enriched:
        primary = enriched[0].get('eligibility')
    return enriched, by_term, primary


def eligibility_block_message(eligibility):
    """Human-readable reason when student cannot apply."""
    if not eligibility:
        return 'Could not verify your eligibility for this exam.'
    if eligibility.get('eligible'):
        return ''
    parts = eligibility.get('unmet_messages') or []
    if not parts:
        return 'You do not meet the requirements to apply for examinations yet.'
    if len(parts) == 1:
        return f'You cannot apply yet: {parts[0]}.'
    return 'You cannot apply yet: ' + '; '.join(parts) + '.'


def _batch_term_attendance_pct(cursor, student_ids, term_id, *, class_mode=True):
    """Return {student_id: {has_data, present, total, pct}} for many students."""
    out = {sid: {'has_data': False, 'present': 0, 'total': 0, 'pct': 0.0} for sid in student_ids}
    if not student_ids or not term_id:
        return out
    placeholders = ','.join(['%s'] * len(student_ids))
    subj_clause = 'COALESCE(sar.subject_id, 0) = 0' if class_mode else 'COALESCE(sar.subject_id, 0) > 0'
    try:
        cursor.execute(
            f"""
            SELECT sar.student_id, sar.present
            FROM student_attendance_records sar
            WHERE sar.term_id = %s AND {subj_clause}
              AND sar.student_id IN ({placeholders})
            """,
            [int(term_id)] + list(student_ids),
        )
        acc = {sid: [0, 0] for sid in student_ids}
        for r in cursor.fetchall() or []:
            sid = (r.get('student_id') if isinstance(r, dict) else r[0]) or ''
            sid = str(sid).strip()
            if sid not in acc:
                continue
            acc[sid][1] += 1
            pres = r.get('present') if isinstance(r, dict) else r[1]
            if pres is not None and bool(int(pres)):
                acc[sid][0] += 1
        for sid, (present, total) in acc.items():
            if total:
                out[sid] = {
                    'has_data': True,
                    'present': present,
                    'total': total,
                    'pct': round(100.0 * present / total, 1),
                }
    except Exception:
        pass
    return out


def _resolve_fee_structure_for_category(cursor, academic_level_id, academic_year_id, term_id, student_category):
    """Pick active fee structure for level/term/category (same rules as student portal)."""
    if not academic_level_id or not term_id:
        return None
    cat_sql, cat_order = _fee_structure_category_clause(student_category)
    params = [int(academic_level_id), int(term_id)]
    year_sql = ''
    if academic_year_id:
        year_sql = ' AND fs.academic_year_id = %s'
        params.append(int(academic_year_id))
    try:
        cursor.execute(
            f"""
            SELECT fs.id, fs.fee_name, fs.total_amount
            FROM fee_structures fs
            WHERE fs.academic_level_id = %s
              AND fs.term_id = %s
              AND fs.status = 'active'
              {year_sql}
              {cat_sql}
            ORDER BY {cat_order}, fs.created_at DESC
            LIMIT 1
            """,
            tuple(params),
        )
        row = cursor.fetchone()
    except Exception:
        return None
    if not row:
        return None
    if isinstance(row, dict):
        return {
            'id': row.get('id'),
            'fee_name': (row.get('fee_name') or '').strip(),
            'total_amount': float(row.get('total_amount') or 0),
        }
    return {
        'id': row[0],
        'fee_name': (row[1] or '').strip() if len(row) > 1 else '',
        'total_amount': float(row[2] if len(row) > 2 and row[2] else 0),
    }


def _batch_fee_payment_pct(cursor, students, academic_level_id, academic_year_id, term_id):
    """Return {student_id: fee summary dict} aligned with _term_fee_payment_summary."""
    sids = [s['student_id'] for s in students if s.get('student_id')]
    empty = {
        'has_structure': False,
        'fee_name': '',
        'total_amount': 0.0,
        'total_paid': 0.0,
        'pct': 0.0,
        'balance': 0.0,
    }
    out = {sid: dict(empty) for sid in sids}
    if not sids or not academic_level_id or not term_id:
        return out

    fs_by_cat = {}
    for cat in {((s.get('student_category') or '').strip().lower()) for s in students}:
        fs_by_cat[cat] = _resolve_fee_structure_for_category(
            cursor, academic_level_id, academic_year_id, term_id, cat,
        )

    fs_ids = {fs['id'] for fs in fs_by_cat.values() if fs and fs.get('id')}
    paid_by_student_fs = {}
    if fs_ids:
        placeholders = ','.join(['%s'] * len(fs_ids))
        sid_placeholders = ','.join(['%s'] * len(sids))
        try:
            cursor.execute(
                f"""
                SELECT sp.student_id, sp.fee_structure_id, COALESCE(SUM(sp.amount_paid), 0) AS paid
                FROM student_payments sp
                WHERE sp.student_id IN ({sid_placeholders})
                  AND sp.fee_structure_id IN ({placeholders})
                GROUP BY sp.student_id, sp.fee_structure_id
                """,
                list(sids) + list(fs_ids),
            )
            for r in cursor.fetchall() or []:
                if isinstance(r, dict):
                    key = (str(r.get('student_id') or '').strip(), int(r.get('fee_structure_id') or 0))
                    paid_by_student_fs[key] = float(r.get('paid') or 0)
                else:
                    key = (str(r[0] or '').strip(), int(r[1] or 0))
                    paid_by_student_fs[key] = float(r[2] if len(r) > 2 and r[2] else 0)
        except Exception:
            pass

    for stu in students:
        sid = stu.get('student_id')
        if not sid:
            continue
        cat = (stu.get('student_category') or '').strip().lower()
        fs = fs_by_cat.get(cat)
        if not fs:
            continue
        total_amount = float(fs.get('total_amount') or 0)
        total_paid = paid_by_student_fs.get((sid, int(fs['id'])), 0.0)
        if total_amount <= 0:
            pct = 100.0
            balance = 0.0
        else:
            pct = min(100.0, round(100.0 * total_paid / total_amount, 1))
            balance = max(0.0, total_amount - total_paid)
        out[sid] = {
            'has_structure': True,
            'fee_name': fs.get('fee_name') or '',
            'total_amount': total_amount,
            'total_paid': total_paid,
            'pct': pct,
            'balance': balance,
        }
    return out


def _batch_student_exam_applications(cursor, student_ids):
    """Return {student_id: [application rows]} newest first."""
    out = {sid: [] for sid in student_ids}
    if not student_ids:
        return out
    placeholders = ','.join(['%s'] * len(student_ids))
    try:
        cursor.execute(
            f"""
            SELECT student_id, exam_name, year_name, term_name, status, applied_at, sitting_key
            FROM student_exam_applications
            WHERE student_id IN ({placeholders})
            ORDER BY applied_at DESC, id DESC
            """,
            list(student_ids),
        )
        for r in cursor.fetchall() or []:
            if isinstance(r, dict):
                sid = str(r.get('student_id') or '').strip()
                row = dict(r)
            else:
                sid = str(r[0] or '').strip()
                row = {
                    'exam_name': r[1], 'year_name': r[2], 'term_name': r[3],
                    'status': r[4], 'applied_at': r[5], 'sitting_key': r[6],
                }
            if sid not in out:
                continue
            at = row.get('applied_at')
            if at and hasattr(at, 'strftime'):
                row['applied_at_str'] = at.strftime('%d %b %Y')
            else:
                row['applied_at_str'] = str(at)[:10] if at else '—'
            parts = [x for x in (row.get('year_name'), row.get('term_name'), row.get('exam_name')) if x]
            row['label'] = ' · '.join(parts) if parts else (row.get('exam_name') or 'Exam')
            out[sid].append(row)
    except Exception:
        pass
    return out


def _eligibility_from_summaries(class_att, subject_att, fee, apply_rules=None):
    norm = normalize_apply_rules(apply_rules)
    if not norm['any_enabled']:
        return {
            'eligible': True,
            'class_met': True,
            'subject_met': True,
            'fee_met': True,
            'requirements_enabled': False,
        }
    class_met = True
    if norm['class_enabled']:
        class_met = class_att['has_data'] and class_att['pct'] >= norm['class_min']
    subject_met = True
    if norm['subject_enabled']:
        subject_met = subject_att['has_data'] and subject_att['pct'] >= norm['subject_min']
    fee_met = True
    if norm['fee_enabled']:
        fee_met = fee['has_structure'] and fee['pct'] >= norm['fee_min']
    return {
        'eligible': class_met and subject_met and fee_met,
        'class_met': class_met,
        'subject_met': subject_met,
        'fee_met': fee_met,
        'requirements_enabled': True,
    }


def fetch_level_exam_apply_overview(cursor, academic_level_id, term_id=None, academic_year_id=None, apply_rules=None):
    """
    Students in one academic level with attendance, fees, eligibility, and applications.
    Uses current term/year when term_id is omitted.
    """
    empty = {
        'level': None,
        'term_id': term_id,
        'term_label': '',
        'students': [],
        'summary': {'total': 0, 'eligible': 0, 'applied': 0},
    }
    if not academic_level_id:
        return empty

    try:
        level_id = int(academic_level_id)
    except (TypeError, ValueError):
        return empty

    cursor.execute(
        """
        SELECT id, level_category, level_name
        FROM academic_levels
        WHERE id = %s AND level_status = 'active'
        LIMIT 1
        """,
        (level_id,),
    )
    level_row = cursor.fetchone()
    if not level_row:
        return empty
    if isinstance(level_row, dict):
        level = {
            'id': level_row.get('id'),
            'level_category': level_row.get('level_category') or '',
            'level_name': level_row.get('level_name') or '',
        }
    else:
        level = {
            'id': level_row[0],
            'level_category': level_row[1] or '',
            'level_name': level_row[2] or '',
        }

    if not term_id:
        cursor.execute(
            """
            SELECT ay.id AS year_id, t.id AS term_id, t.term_name, ay.year_name
            FROM academic_years ay
            INNER JOIN terms t ON t.academic_year_id = ay.id
            WHERE ay.is_current = TRUE AND ay.status = 'active'
              AND t.is_current = TRUE AND t.status = 'active'
            LIMIT 1
            """
        )
        cur = cursor.fetchone()
        if cur:
            if isinstance(cur, dict):
                academic_year_id = academic_year_id or cur.get('year_id')
                term_id = cur.get('term_id')
                term_label = ' · '.join(
                    x for x in ((cur.get('year_name') or ''), (cur.get('term_name') or '')) if x
                )
            else:
                academic_year_id = academic_year_id or cur[0]
                term_id = cur[1]
                term_label = ' · '.join(x for x in ((cur[3] or ''), (cur[2] or '')) if x)
        else:
            term_label = ''
    else:
        term_label = _term_label(cursor, term_id)

    cursor.execute(
        """
        SELECT s.student_id, s.full_name, s.current_grade,
               LOWER(TRIM(COALESCE(s.student_category, ''))) AS student_category
        FROM students s
        WHERE s.status = 'in session'
          AND TRIM(LOWER(s.current_grade)) = TRIM(LOWER(%s))
        ORDER BY s.full_name ASC, s.student_id ASC
        """,
        (level['level_name'],),
    )
    students_raw = cursor.fetchall() or []
    students = []
    for r in students_raw:
        if isinstance(r, dict):
            students.append({
                'student_id': (r.get('student_id') or '').strip(),
                'full_name': (r.get('full_name') or '').strip(),
                'current_grade': (r.get('current_grade') or '').strip(),
                'student_category': (r.get('student_category') or '').strip(),
            })
        else:
            students.append({
                'student_id': (r[0] or '').strip(),
                'full_name': (r[1] or '').strip(),
                'current_grade': (r[2] or '').strip(),
                'student_category': (r[3] or '').strip() if len(r) > 3 else '',
            })

    sids = [s['student_id'] for s in students if s.get('student_id')]
    class_att = _batch_term_attendance_pct(cursor, sids, term_id, class_mode=True)
    subject_att = _batch_term_attendance_pct(cursor, sids, term_id, class_mode=False)
    fee_att = _batch_fee_payment_pct(cursor, students, level_id, academic_year_id, term_id)
    apps = _batch_student_exam_applications(cursor, sids)

    rows = []
    eligible_count = 0
    applied_count = 0
    for stu in students:
        sid = stu['student_id']
        ca = class_att.get(sid, {'has_data': False, 'present': 0, 'total': 0, 'pct': 0.0})
        sa = subject_att.get(sid, {'has_data': False, 'present': 0, 'total': 0, 'pct': 0.0})
        fe = fee_att.get(sid, {'has_structure': False, 'pct': 0.0, 'total_paid': 0.0, 'total_amount': 0.0})
        elig = _eligibility_from_summaries(ca, sa, fe, apply_rules)
        if elig['eligible']:
            eligible_count += 1
        stu_apps = apps.get(sid, [])
        active_apps = [a for a in stu_apps if (a.get('status') or '') in ('pending', 'approved')]
        has_applied = bool(active_apps)
        if has_applied:
            applied_count += 1
        rows.append({
            **stu,
            'class_attendance_pct': ca['pct'] if ca['has_data'] else None,
            'class_attendance_detail': f"{ca['present']}/{ca['total']}" if ca['has_data'] else '—',
            'subject_attendance_pct': sa['pct'] if sa['has_data'] else None,
            'subject_attendance_detail': f"{sa['present']}/{sa['total']}" if sa['has_data'] else '—',
            'fee_pct': fe['pct'] if fe['has_structure'] else None,
            'fee_detail': (
                f"KES {fe['total_paid']:,.0f} / {fe['total_amount']:,.0f}"
                if fe['has_structure'] else '—'
            ),
            'eligible': elig['eligible'],
            'has_applied': has_applied,
            'applications': stu_apps,
            'active_applications': active_apps,
            'application_summary': (
                ', '.join(
                    f"{a.get('exam_name') or 'Exam'} ({a.get('status') or 'pending'})"
                    for a in active_apps[:3]
                )
                if active_apps else ''
            ),
        })

    norm = normalize_apply_rules(apply_rules)

    return {
        'level': level,
        'term_id': term_id,
        'academic_year_id': academic_year_id,
        'term_label': term_label or _term_label(cursor, term_id),
        'students': rows,
        'requirements_enabled': norm['any_enabled'],
        'apply_rules': norm,
        'summary': {
            'total': len(rows),
            'eligible': eligible_count,
            'applied': applied_count,
            'class_min_pct': norm['class_min'],
            'subject_min_pct': norm['subject_min'],
            'fee_min_pct': norm['fee_min'],
            'class_required': norm['class_enabled'],
            'subject_required': norm['subject_enabled'],
            'fee_required': norm['fee_enabled'],
        },
    }
