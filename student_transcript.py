"""Student exam transcript helpers (portal gazetted results)."""
from hashlib import sha256


def _norm_int(val):
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _progress_group_key(row):
    """Same logical exam: year + term + exam name."""
    ay = _norm_int(row.get('exam_academic_year_id'))
    tid = _norm_int(row.get('exam_term_id'))
    name_key = (row.get('exam_name') or '').strip().lower()
    if ay is not None and tid is not None and name_key:
        return ('id', ay, tid, name_key)
    return (
        'lbl',
        (row.get('year_name') or '').strip(),
        (row.get('term_name') or '').strip(),
        name_key,
    )


def exam_sitting_hash(year_name, term_name, exam_name):
    parts = [
        (year_name or '').strip().lower(),
        (term_name or '').strip().lower(),
        (exam_name or '').strip().lower(),
    ]
    return sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]


def build_student_exam_transcripts(progress_data, grade_bands=None, grade_from_pct=None):
    """Group gazetted progress rows into official exam transcript sittings."""
    grade_fn = grade_from_pct or (lambda _pct, _bands: ('', None))

    exam_order = []
    exam_rows = {}
    for row in progress_data or []:
        key = _progress_group_key(row)
        if key not in exam_rows:
            exam_rows[key] = []
            exam_order.append(key)
        exam_rows[key].append(row)

    transcripts = []
    for key in exam_order:
        rows = exam_rows[key]
        first = rows[0]
        subjects = []
        marks_list = []
        seen_subjects = set()
        for r in rows:
            if r.get('marks') is None and r.get('marks_raw') is None:
                continue
            sk = (r.get('subject_name') or 'N/A').strip().lower()
            if sk in seen_subjects:
                continue
            seen_subjects.add(sk)
            pct = r.get('marks')
            if pct is not None:
                marks_list.append(pct)
            grade_code, points = grade_fn(pct, grade_bands) if pct is not None else ('', None)
            subjects.append({
                'subject_name': r.get('subject_name') or 'N/A',
                'marks_pct': pct,
                'marks_raw': r.get('marks_raw'),
                'grade_code': grade_code or '—',
                'points': points,
            })
        if not subjects:
            continue
        subjects.sort(key=lambda x: x['subject_name'])
        date_strs = []
        for r in rows:
            ed = r.get('exam_date')
            if ed and hasattr(ed, 'strftime'):
                date_strs.append(ed.strftime('%Y-%m-%d'))
            elif ed:
                date_strs.append(str(ed)[:10])
        unique_dates = sorted(set(d for d in date_strs if d))
        exam_date_str = unique_dates[0] if len(unique_dates) == 1 else ''
        exam_date_note = ''
        if len(unique_dates) > 1:
            exam_date_note = f"{unique_dates[0]} – {unique_dates[-1]}"
        mean_pct = round(sum(marks_list) / len(marks_list), 1) if marks_list else None
        pass_count = sum(1 for m in marks_list if m >= 50)
        parts = [x for x in (first.get('year_name'), first.get('term_name'), first.get('exam_name')) if x]
        yn = first.get('year_name') or ''
        tn = first.get('term_name') or ''
        en = first.get('exam_name') or ''
        transcripts.append({
            'sitting_id': exam_sitting_hash(yn, tn, en),
            'year_name': yn,
            'term_name': tn,
            'exam_name': en,
            'exam_type': first.get('exam_type') or '',
            'label': ' · '.join(parts) if parts else 'Exam',
            'exam_date_str': exam_date_str,
            'exam_date_note': exam_date_note,
            'subjects': subjects,
            'mean_pct': mean_pct,
            'subjects_count': len(subjects),
            'pass_count': pass_count,
            'pass_rate': round(100 * pass_count / len(marks_list), 0) if marks_list else 0,
        })

    transcripts.sort(
        key=lambda x: (x.get('exam_date_str') or '', x.get('year_name') or '', x.get('term_name') or ''),
        reverse=True,
    )

    year_map = {}
    year_order = []
    for t in transcripts:
        yn = t.get('year_name') or 'Unknown year'
        if yn not in year_map:
            year_map[yn] = []
            year_order.append(yn)
        year_map[yn].append(t)

    by_year = [{'year_name': yn, 'transcripts': year_map[yn]} for yn in year_order]
    return {
        'transcripts': transcripts,
        'by_year': by_year,
        'total_sittings': len(transcripts),
        'total_subject_entries': sum(t['subjects_count'] for t in transcripts),
    }
