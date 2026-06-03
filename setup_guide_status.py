"""
Live setup-guide checklist state from the database (accountant & curriculum coordinator).
"""
from __future__ import annotations


def _scalar_count(cursor, sql, params=None):
    try:
        cursor.execute(sql, params or ())
        row = cursor.fetchone()
        if not row:
            return 0
        if isinstance(row, dict):
            return int(list(row.values())[0] or 0)
        return int(row[0] or 0)
    except Exception:
        return 0


def _set_checked(bucket, checklist_id, item_id, done):
    if not done or not checklist_id or not item_id:
        return
    bucket.setdefault(checklist_id, {})[item_id] = True


def _merge_maps(*maps):
    out = {}
    for m in maps or []:
        if not m:
            continue
        for checklist_id, items in m.items():
            if not items:
                continue
            dest = out.setdefault(checklist_id, {})
            for item_id, val in items.items():
                if val:
                    dest[item_id] = True
    return out


def fetch_accountant_setup_system_checked(cursor):
    """Map checklistId -> { itemId: True } for completed finance setup."""
    step1 = {}
    page_fin_settings = {}

    fy_count = _scalar_count(
        cursor,
        """
        SELECT COUNT(*) FROM finance_settings
        WHERE financial_year_start IS NOT NULL AND financial_year_end IS NOT NULL
        """,
    )
    has_fy = fy_count > 0
    for item in ('fy-create', 'view-years'):
        _set_checked(step1, 'fin-step-1', item, has_fy)
        _set_checked(page_fin_settings, 'page-finance-settings', item, has_fy)

    current_open = False
    terms_ok = False
    opening_ok = False
    try:
        cursor.execute(
            """
            SELECT is_current, is_locked, opening_balance
            FROM finance_settings
            WHERE financial_year_start IS NOT NULL AND financial_year_end IS NOT NULL
            ORDER BY is_current DESC, financial_year_start DESC, id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row:
            if isinstance(row, dict):
                is_current = bool(row.get('is_current'))
                is_locked = bool(row.get('is_locked'))
                opening = row.get('opening_balance')
            else:
                is_current = bool(row[0])
                is_locked = bool(row[1])
                opening = row[2]
            current_open = is_current and not is_locked
            try:
                opening_ok = opening is not None and float(opening) != 0
            except (TypeError, ValueError):
                opening_ok = opening is not None
    except Exception:
        pass

    _set_checked(step1, 'fin-step-1', 'fy-open', current_open)
    _set_checked(page_fin_settings, 'page-finance-settings', 'create-open', current_open)
    _set_checked(page_fin_settings, 'page-finance-settings', 'save', current_open)

    try:
        terms_ok = _scalar_count(
            cursor,
            "SELECT COUNT(*) FROM terms WHERE COALESCE(is_current, 0) = 1",
        ) > 0
    except Exception:
        terms_ok = _scalar_count(cursor, "SELECT COUNT(*) FROM terms") > 0

    _set_checked(step1, 'fin-step-1', 'fy-calendar', terms_ok)
    _set_checked(page_fin_settings, 'page-finance-settings', 'opening', opening_ok)

    step2 = {}
    page_accounts = {}
    acct_count = _scalar_count(cursor, "SELECT COUNT(*) FROM finance_accounts")
    typed_count = _scalar_count(
        cursor,
        """
        SELECT COUNT(*) FROM finance_accounts
        WHERE COALESCE(account_category, '') != ''
        """,
    )
    active_count = _scalar_count(
        cursor,
        """
        SELECT COUNT(*) FROM finance_accounts
        WHERE LOWER(COALESCE(account_status, 'active')) = 'active'
        """,
    )
    petty_acct = _scalar_count(
        cursor,
        """
        SELECT COUNT(*) FROM finance_accounts
        WHERE LOWER(account_name) LIKE '%petty%'
           OR LOWER(COALESCE(account_category, '')) LIKE '%petty%'
        """,
    )
    petty_entries = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM petty_cash_expenses",
    ) if _table_exists(cursor, 'petty_cash_expenses') else 0

    has_accounts = acct_count > 0
    for cid in ('fin-step-2',):
        _set_checked(step2, cid, 'accounts', has_accounts)
        _set_checked(step2, cid, 'categories', typed_count > 0 and has_accounts)
        _set_checked(step2, cid, 'petty', petty_acct > 0 or petty_entries > 0)
    for item in ('register', 'type', 'active', 'open-detail'):
        _set_checked(page_accounts, 'page-accounts', 'register', has_accounts)
        _set_checked(page_accounts, 'page-accounts', 'type', typed_count > 0)
        _set_checked(page_accounts, 'page-accounts', 'active', active_count > 0)
        _set_checked(page_accounts, 'page-accounts', 'open-detail', acct_count > 0)

    page_petty = {}
    _set_checked(page_petty, 'page-petty-cash', 'account', petty_acct > 0)
    _set_checked(page_petty, 'page-petty-cash', 'entries', petty_entries > 0)
    _set_checked(page_petty, 'page-petty-cash', 'balance', petty_entries > 0)

    step3 = {}
    page_fee_struct = {}
    fs_count = _scalar_count(cursor, "SELECT COUNT(*) FROM fee_structures")
    votes_count = _scalar_count(cursor, "SELECT COUNT(*) FROM fee_items")
    linked_fs = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM fee_structures WHERE finance_account_id IS NOT NULL",
    )
    _set_checked(step3, 'fin-step-3', 'structure', fs_count > 0)
    _set_checked(step3, 'fin-step-3', 'votes', votes_count > 0)
    _set_checked(step3, 'fin-step-3', 'finance-acct', linked_fs > 0)
    _set_checked(page_fee_struct, 'page-fee-structures', 'add', fs_count > 0)
    _set_checked(page_fee_struct, 'page-fee-structures', 'items', votes_count > 0)
    _set_checked(page_fee_struct, 'page-fee-structures', 'account-link', linked_fs > 0)
    _set_checked(page_fee_struct, 'page-fee-structures', 'activate', fs_count > 0)

    step4 = {}
    page_student_fees = {}
    page_payments_audit = {}
    page_pocket = {}
    reg_count = _scalar_count(cursor, "SELECT COUNT(*) FROM student_fee_votes") if _table_exists(
        cursor, 'student_fee_votes'
    ) else _scalar_count(cursor, "SELECT COUNT(*) FROM student_fees")
    pay_count = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM student_payments WHERE amount_paid > 0",
    ) if _table_exists(cursor, 'student_payments') else 0
    _set_checked(step4, 'fin-step-4', 'register', reg_count > 0)
    _set_checked(step4, 'fin-step-4', 'collect', pay_count > 0)
    _set_checked(step4, 'fin-step-4', 'audit', pay_count > 0)
    _set_checked(page_student_fees, 'page-student-fees', 'assign', reg_count > 0)
    _set_checked(page_student_fees, 'page-student-fees', 'pay', pay_count > 0)
    _set_checked(page_student_fees, 'page-student-fees', 'receipt', pay_count > 0)
    _set_checked(page_payments_audit, 'page-payments-audit', 'review', pay_count > 0)
    _set_checked(page_payments_audit, 'page-payments-audit', 'filters', pay_count > 0)

    step5 = {}
    page_revenue = {}
    page_pay_inv = {}
    revenue_count = _scalar_count(
        cursor,
        """
        SELECT COUNT(*) FROM finance_account_transactions
        WHERE related_type = 'accountant_revenue'
        """,
    ) if _table_exists(cursor, 'finance_account_transactions') else 0
    supplier_pay = _scalar_count(
        cursor,
        """
        SELECT COUNT(*) FROM finance_account_transactions
        WHERE related_type IN ('stock_in_payment_line', 'supplier_pay_all')
          AND LOWER(COALESCE(direction, 'debit')) = 'debit'
        """,
    ) if _table_exists(cursor, 'finance_account_transactions') else 0
    _set_checked(step5, 'fin-step-5', 'revenue', revenue_count > 0)
    _set_checked(step5, 'fin-step-5', 'payments', supplier_pay > 0)
    _set_checked(page_revenue, 'page-revenue', 'register', revenue_count > 0)
    _set_checked(page_revenue, 'page-revenue', 'amount', revenue_count > 0)
    _set_checked(page_revenue, 'page-revenue', 'verify', revenue_count > 0)
    _set_checked(page_pay_inv, 'page-payments-invoices', 'invoice', supplier_pay > 0)
    _set_checked(page_pay_inv, 'page-payments-invoices', 'save', supplier_pay > 0)

    step6 = {}
    page_exp = {}
    page_exp_audit = {}
    page_staff = {}
    page_salary_rec = {}
    expense_count = 0
    if _table_exists(cursor, 'petty_cash_expenses'):
        expense_count += _scalar_count(cursor, "SELECT COUNT(*) FROM petty_cash_expenses")
    if _table_exists(cursor, 'finance_account_transactions'):
        expense_count += _scalar_count(
            cursor,
            """
            SELECT COUNT(*) FROM finance_account_transactions
            WHERE related_type IN ('petty_cash_expense', 'stock_in_payment_line')
              AND LOWER(COALESCE(direction, 'debit')) = 'debit'
            """,
        )
    salary_cfg = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM employee_salaries WHERE is_active = TRUE",
    ) if _table_exists(cursor, 'employee_salaries') else 0
    salary_paid = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM employee_salary_payments",
    ) if _table_exists(cursor, 'employee_salary_payments') else 0
    _set_checked(step6, 'fin-step-6', 'expenses', expense_count > 0)
    _set_checked(step6, 'fin-step-6', 'salaries', salary_cfg > 0)
    _set_checked(step6, 'fin-step-6', 'payroll', salary_paid > 0)
    _set_checked(page_exp, 'page-expense-records', 'new', expense_count > 0)
    _set_checked(page_staff, 'page-staff-salaries', 'salary', salary_cfg > 0)
    _set_checked(page_staff, 'page-staff-salaries', 'pay', salary_paid > 0)
    _set_checked(page_salary_rec, 'page-salary-records', 'verify', salary_paid > 0)
    _set_checked(page_exp_audit, 'page-expense-audits', 'review', expense_count > 0)

    step7 = {}
    page_reports = {}
    page_analytics = {}
    has_data = has_fy and (pay_count > 0 or revenue_count > 0 or expense_count > 0)
    _set_checked(step7, 'fin-step-7', 'reports', has_data)
    _set_checked(step7, 'fin-step-7', 'analytics', has_data)
    _set_checked(page_reports, 'page-finance-overview', 'year', current_open)
    _set_checked(page_reports, 'page-finance-overview', 'report', has_data)
    _set_checked(page_analytics, 'page-visual-analytics', 'year', current_open)
    _set_checked(page_analytics, 'page-visual-analytics', 'tabs', has_data)

    return _merge_maps(
        step1,
        step2,
        page_accounts,
        page_petty,
        step3,
        page_fee_struct,
        step4,
        page_student_fees,
        page_payments_audit,
        page_pocket,
        step5,
        page_revenue,
        page_pay_inv,
        step6,
        page_exp,
        page_exp_audit,
        page_staff,
        page_salary_rec,
        step7,
        page_reports,
        page_analytics,
        page_fin_settings,
    )


def fetch_curriculum_setup_system_checked(cursor):
    """Map checklistId -> { itemId: True } for completed curriculum setup."""
    step1 = {}
    page_academic = {}

    level_count = _scalar_count(
        cursor,
        """
        SELECT COUNT(*) FROM academic_levels
        WHERE COALESCE(level_status, 'active') = 'active'
        """,
    )
    year_count = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM academic_years WHERE COALESCE(is_current, 0) = 1",
    )
    term_count = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM terms WHERE COALESCE(is_current, 0) = 1",
    )
    has_levels = level_count > 0
    has_year = year_count > 0
    has_term = term_count > 0

    for item, done in (
        ('levels', has_levels),
        ('year', has_year),
        ('terms', has_term),
    ):
        _set_checked(step1, 'step-1', item, done)
    for item, done in (
        ('levels-tab', has_levels),
        ('years-tab', has_year),
        ('terms-tab', has_term),
        ('review', has_year and has_term),
    ):
        _set_checked(page_academic, 'page-academic-settings', item, done)

    step2 = {}
    page_tt_settings = {}
    page_schedule = {}
    profile_count = _scalar_count(cursor, "SELECT COUNT(*) FROM academic_coordinator_settings")
    profile_with_days = 0
    profile_with_slots = 0
    try:
        cursor.execute(
            """
            SELECT study_days, class_time_allocation
            FROM academic_coordinator_settings
            """
        )
        import json

        for row in cursor.fetchall() or []:
            if isinstance(row, dict):
                days = row.get('study_days') or ''
                slots_raw = row.get('class_time_allocation') or '[]'
            else:
                days = row[0] or ''
                slots_raw = row[1] or '[]'
            if str(days).strip():
                profile_with_days += 1
            try:
                slots = json.loads(slots_raw) if slots_raw else []
                if isinstance(slots, list) and len(slots) > 0:
                    profile_with_slots += 1
            except Exception:
                pass
    except Exception:
        pass

    _set_checked(step2, 'step-2', 'profile', profile_count > 0)
    _set_checked(step2, 'step-2', 'days', profile_with_days > 0)
    _set_checked(step2, 'step-2', 'slots', profile_with_slots > 0)
    _set_checked(step2, 'step-2', 'save', profile_count > 0 and profile_with_days > 0)
    _set_checked(page_tt_settings, 'page-timetable-settings', 'profile', profile_count > 0)
    _set_checked(page_schedule, 'page-schedule-mgmt', 'profile', profile_count > 0)

    step3 = {}
    page_subjects = {}
    subj_count = _scalar_count(cursor, "SELECT COUNT(*) FROM subjects")
    _set_checked(step3, 'step-3', 'add', subj_count > 0)
    _set_checked(step3, 'step-3', 'category', subj_count > 0)
    _set_checked(page_subjects, 'page-register-subjects', 'add', subj_count > 0)

    step4 = {}
    page_alloc = {}
    tsa_count = _scalar_count(cursor, "SELECT COUNT(*) FROM teacher_subject_assignments")
    missing_alloc = _scalar_count(
        cursor,
        """
        SELECT COUNT(*) FROM subject_academic_levels sal
        LEFT JOIN teacher_subject_assignments tsa
          ON tsa.academic_level_id = sal.academic_level_id
         AND tsa.subject_id = sal.subject_id
        WHERE tsa.id IS NULL
        """,
    ) if _table_exists(cursor, 'subject_academic_levels') else 0
    sal_count = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM subject_academic_levels",
    ) if _table_exists(cursor, 'subject_academic_levels') else 0
    alloc_done = sal_count > 0 and missing_alloc == 0 and tsa_count > 0
    _set_checked(step4, 'step-4', 'level', has_levels)
    _set_checked(step4, 'step-4', 'assign', alloc_done)
    _set_checked(page_alloc, 'page-subject-allocation', 'assign', alloc_done)

    step5 = {}
    page_timetable = {}
    tt_count = _scalar_count(cursor, "SELECT COUNT(*) FROM timetables")
    _set_checked(step5, 'step-5', 'filters', has_year and has_term)
    _set_checked(step5, 'step-5', 'class', tt_count > 0)
    _set_checked(step5, 'step-5', 'fill', tt_count > 0)
    _set_checked(page_timetable, 'page-manage-timetable', 'fill', tt_count > 0)

    step6 = {}
    exam_sessions_ok = False
    try:
        cursor.execute("SHOW COLUMNS FROM school_settings LIKE 'exam_session_settings'")
        if cursor.fetchone():
            cursor.execute(
                "SELECT exam_session_settings FROM school_settings ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            raw = (row.get('exam_session_settings') if isinstance(row, dict) else row[0]) if row else None
            exam_sessions_ok = bool(raw and str(raw).strip() and str(raw).strip() not in ('{}', '[]', 'null'))
    except Exception:
        pass
    exam_subj_ok = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM subjects WHERE exam_total_marks IS NOT NULL AND exam_total_marks > 0",
    ) > 0
    _set_checked(step6, 'step-6', 'sessions', exam_sessions_ok)
    _set_checked(step6, 'step-6', 'exam-subjects', exam_subj_ok)

    step7 = {}
    grades_ok = _scalar_count(cursor, "SELECT COUNT(*) FROM grade_setting_profiles") > 0
    combined_ok = _scalar_count(
        cursor,
        "SELECT COUNT(*) FROM academic_level_combinations",
    ) if _table_exists(cursor, 'academic_level_combinations') else 0
    _set_checked(step7, 'step-7', 'grades', grades_ok)
    _set_checked(step7, 'step-7', 'combined', combined_ok > 0)

    return _merge_maps(step1, page_academic, step2, page_tt_settings, page_schedule, step3, page_subjects, step4, page_alloc, step5, page_timetable, step6, step7)


def _table_exists(cursor, table_name):
    try:
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        return bool(cursor.fetchone())
    except Exception:
        return False


def fetch_setup_guide_system_checked(cursor, role):
    role = (role or '').strip().lower()
    if role == 'accountant':
        return fetch_accountant_setup_system_checked(cursor)
    if role == 'curriculum coordinator':
        return fetch_curriculum_setup_system_checked(cursor)
    return {}


def setup_guide_status_payload(cursor, role):
    checked = fetch_setup_guide_system_checked(cursor, role)
    total = 0
    done = 0
    for items in checked.values():
        for val in items.values():
            if val:
                done += 1
            total += 1
    return {
        'role': role,
        'checked': checked,
        'summary': {'done': done, 'total': total},
    }
