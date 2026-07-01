"""Finance overview report navigation, filters, and data payloads."""

from collections import defaultdict
from datetime import datetime

import finance_account_reports as finance_account_reports_mod

FINANCE_REPORT_NAV = (
    {
        'slug': 'revenue-collection',
        'title': 'Revenue & Collection',
        'icon': 'fa-hand-holding-usd',
        'description': 'Fee collections, registered revenue, and collection rates.',
    },
    {
        'slug': 'expenditure',
        'title': 'Expenditure',
        'icon': 'fa-receipt',
        'description': 'Fee votes — vote budget, expenditure, balance, and transactions.',
    },
    {
        'slug': 'financial-statements',
        'title': 'Financial Statements',
        'icon': 'fa-balance-scale',
        'description': 'Ledger balances, income, outflows, and net position.',
    },
    {
        'slug': 'audit-compliance',
        'title': 'Audit & Compliance',
        'icon': 'fa-shield-alt',
        'description': 'Payment, expense, and salary audit trails.',
    },
    {
        'slug': 'periodic-summary',
        'title': 'Periodic Summary',
        'icon': 'fa-calendar-alt',
        'description': 'Revenue and spending rolled up by period.',
    },
    {
        'slug': 'student-specific',
        'title': 'Student-Specific',
        'icon': 'fa-user-graduate',
        'description': 'Per-student fee accounts, balances, and class roll-ups.',
    },
)

FINANCE_REPORT_SLUGS = frozenset(item['slug'] for item in FINANCE_REPORT_NAV)

# Core trio shown on the unified accounts report page (tabs, not separate hubs).
FINANCE_CORE_REPORT_NAV = FINANCE_REPORT_NAV[:3]
FINANCE_CORE_REPORT_SLUGS = frozenset(item['slug'] for item in FINANCE_CORE_REPORT_NAV)

# Revenue & Collection — account book views (General Ledger / Cash Book).
REVENUE_BOOK_NAV = (
    {
        'slug': 'general-ledger',
        'title': 'The General Ledger',
        'icon': 'fa-book',
        'description': 'Debits, credits, and running balance by vote for the selected account.',
    },
    {
        'slug': 'cash-book',
        'title': 'The Cash Book',
        'icon': 'fa-money-check',
        'description': 'Receipts, payments, and running cash balance for the selected account.',
    },
)
REVENUE_BOOK_SLUGS = frozenset(item['slug'] for item in REVENUE_BOOK_NAV)

VOTE_LEDGER_NAV = (
    {
        'slug': 'general-ledger',
        'title': 'Vote General Ledger',
        'icon': 'fa-book',
        'description': 'Credits and debits for this vote with running balance.',
    },
    {
        'slug': 'expenditure-ledger',
        'title': 'Vote Expenditure Ledger',
        'icon': 'fa-file-invoice',
        'description': 'All expenditure outflows for this vote.',
    },
    {
        'slug': 'accounts-payable-ledger',
        'title': 'Vote Accounts Payable Ledger',
        'icon': 'fa-hand-holding-usd',
        'description': 'Stock-in payables and settlement status for this vote.',
    },
    {
        'slug': 'payroll-ledger',
        'title': 'Vote Payroll Ledger',
        'icon': 'fa-users',
        'description': 'Salary disbursements in the selected period (school-wide).',
    },
    {
        'slug': 'cheque-register',
        'title': 'Vote Cheque Register',
        'icon': 'fa-money-check',
        'description': 'Cash book listing of receipts and payments with running balance.',
    },
)

VOTE_LEDGER_SLUGS = frozenset(item['slug'] for item in VOTE_LEDGER_NAV)

# School-wide expenditure books (all votes) — sidebar on expenditure list page
EXPENDITURE_BOOKS_NAV = (
    {
        'slug': 'general-ledger',
        'title': 'General Ledger',
        'icon': 'fa-book',
        'description': 'All votes — credits, debits and running balance.',
    },
    {
        'slug': 'expenditure-ledger',
        'title': 'Expenditure Ledger',
        'icon': 'fa-file-invoice',
        'description': 'All votes — expenditure outflows with cumulative totals.',
    },
    {
        'slug': 'accounts-payable-ledger',
        'title': 'Accounts Payable Ledger',
        'icon': 'fa-hand-holding-usd',
        'description': 'All votes — supplier invoices and settlements.',
    },
    {
        'slug': 'payroll-ledger',
        'title': 'Payroll Ledger',
        'icon': 'fa-users',
        'description': 'Staff salary disbursements in the selected period.',
    },
    {
        'slug': 'cheque-register',
        'title': 'Cheque Register',
        'icon': 'fa-money-check',
        'description': 'All votes — receipts and payments with running balance.',
    },
)

EXPENDITURE_LEDGER_SLUGS = VOTE_LEDGER_SLUGS
EXPENDITURE_BOOKS_INLINE_SLUGS = frozenset(
    item['slug'] for item in EXPENDITURE_BOOKS_NAV if not item.get('external_path')
)

# School-wide financial statements — sidebar on financial-statements report page
FINANCIAL_STATEMENTS_NAV = (
    {
        'slug': 'income-and-expenditure',
        'title': 'Income and Expenditure Account',
        'icon': 'fa-chart-line',
        'description': 'Income and expenditure for the period with surplus or deficit.',
    },
    {
        'slug': 'balance-sheet',
        'title': 'Balance Sheet',
        'icon': 'fa-balance-scale',
        'description': 'Assets, liabilities and funds at the period end.',
    },
    {
        'slug': 'receipts-and-payments',
        'title': 'Receipts and Payments Account',
        'icon': 'fa-money-check-alt',
        'description': 'Cash receipts and payments with opening and closing balances.',
    },
    {
        'slug': 'cash-flow',
        'title': 'Cash Flow Statement',
        'icon': 'fa-water',
        'description': 'Cash inflows and outflows by period.',
    },
)

FINANCIAL_STATEMENT_SLUGS = frozenset(item['slug'] for item in FINANCIAL_STATEMENTS_NAV)


def report_meta(slug):
    for item in FINANCE_REPORT_NAV:
        if item['slug'] == slug:
            return item
    return None


def parse_filters(request):
    """Query-string filters shared across finance reports."""
    date_from = (request.args.get('date_from') or '').strip()[:10]
    date_to = (request.args.get('date_to') or '').strip()[:10]
    grade = (request.args.get('grade') or '').strip()
    source = (request.args.get('source') or 'all').strip().lower()
    period = (request.args.get('period') or 'monthly').strip().lower()
    if period not in ('daily', 'weekly', 'monthly', 'term'):
        period = 'monthly'
    if source not in ('all', 'fees', 'government', 'private', 'income', 'store', 'payment', 'misc', 'salary'):
        source = 'all'
    academic_year_id = request.args.get('academic_year_id', type=int)
    term_id = request.args.get('term_id', type=int)
    finance_account_id = request.args.get('finance_account_id', type=int)
    financial_year_id = request.args.get('financial_year_id', type=int)
    page = max(1, request.args.get('page', 1, type=int) or 1)
    per_page = max(1, min(request.args.get('per_page', 50, type=int) or 50, 100))
    q = (request.args.get('q') or '').strip()
    vote = (request.args.get('vote') or '').strip().upper()
    ledger = (request.args.get('ledger') or '').strip().lower()
    if ledger and ledger not in EXPENDITURE_LEDGER_SLUGS:
        ledger = ''
    statement = (request.args.get('statement') or '').strip().lower()
    if statement and statement not in FINANCIAL_STATEMENT_SLUGS:
        statement = ''
    book = (request.args.get('book') or 'general-ledger').strip().lower()
    if book not in REVENUE_BOOK_SLUGS:
        book = 'general-ledger'
    return {
        'date_from': date_from,
        'date_to': date_to,
        'grade': grade,
        'source': source,
        'period': period,
        'academic_year_id': academic_year_id,
        'term_id': term_id,
        'finance_account_id': finance_account_id,
        'financial_year_id': financial_year_id,
        'page': page,
        'per_page': per_page,
        'q': q,
        'vote': vote,
        'ledger': ledger,
        'statement': statement,
        'book': book,
    }


def _fmt_kes(amount):
    try:
        return f'{float(amount):,.2f}'
    except (TypeError, ValueError):
        return '0.00'


def _row_val(row, key, idx=0, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    return row[idx] if row and len(row) > idx else default


def _date_display(val):
    if not val:
        return '—'
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    s = str(val).strip()
    return s.split(' ')[0] if s else '—'


def _append_date_clause(column, filters, where, params):
    if filters.get('date_from'):
        where.append(f'DATE({column}) >= %s')
        params.append(filters['date_from'])
    if filters.get('date_to'):
        where.append(f'DATE({column}) <= %s')
        params.append(filters['date_to'])


def load_filter_options(cursor, current_year_term_fn):
    """Academic years, terms, finance accounts, classes for report filter UI."""
    class_options = []
    cursor.execute(
        """
        SELECT level_name FROM academic_levels
        WHERE level_status = 'active'
        ORDER BY level_name ASC
        """
    )
    for r in cursor.fetchall() or []:
        ln = _row_val(r, 'level_name', 0)
        if ln:
            class_options.append(ln)

    academic_years = []
    try:
        cursor.execute(
            """
            SELECT id, year_name, is_current
            FROM academic_years
            WHERE status = 'active'
            ORDER BY year_name DESC
            """
        )
        for r in cursor.fetchall() or []:
            academic_years.append({
                'id': int(_row_val(r, 'id', 0) or 0),
                'name': _row_val(r, 'year_name', 1) or '—',
                'is_current': bool(_row_val(r, 'is_current', 2)),
            })
    except Exception as e:
        print(f'finance_reports academic_years: {e}')

    terms = []
    try:
        cursor.execute(
            """
            SELECT t.id, t.term_name, t.academic_year_id, t.is_current,
                   ay.year_name
            FROM terms t
            INNER JOIN academic_years ay ON ay.id = t.academic_year_id
            WHERE t.status = 'active'
            ORDER BY ay.year_name DESC, t.term_name ASC
            """
        )
        for r in cursor.fetchall() or []:
            terms.append({
                'id': int(_row_val(r, 'id', 0) or 0),
                'name': _row_val(r, 'term_name', 1) or '—',
                'academic_year_id': int(_row_val(r, 'academic_year_id', 2) or 0),
                'is_current': bool(_row_val(r, 'is_current', 3)),
                'year_name': _row_val(r, 'year_name', 4) or '',
            })
    except Exception as e:
        print(f'finance_reports terms: {e}')

    finance_accounts = []
    try:
        cursor.execute(
            """
            SELECT id, account_name, account_category, account_status
            FROM finance_accounts
            ORDER BY account_name ASC
            """
        )
        for r in cursor.fetchall() or []:
            finance_accounts.append({
                'id': int(_row_val(r, 'id', 0) or 0),
                'name': _row_val(r, 'account_name', 1) or '—',
                'category': _row_val(r, 'account_category', 2) or '',
                'status': _row_val(r, 'account_status', 3) or '',
            })
    except Exception as e:
        print(f'finance_reports finance_accounts: {e}')

    cy, ct = current_year_term_fn(cursor) if current_year_term_fn else (None, None)
    return {
        'class_options': class_options,
        'academic_years': academic_years,
        'terms': terms,
        'finance_accounts': finance_accounts,
        'default_academic_year_id': cy,
        'default_term_id': ct,
    }


def _summary_cards(items):
    return [{'label': x['label'], 'value': x['value'], 'hint': x.get('hint', '')} for x in items]


def _fy_balance_summary_cards(fy_ctx):
    """Opening/closing balance KPIs from the active financial year."""
    if not fy_ctx or not fy_ctx.get('is_configured'):
        return []
    label = fy_ctx.get('year_label') or 'Financial year'
    period_hint = ''
    if fy_ctx.get('financial_year_start_display') and fy_ctx.get('financial_year_end_display'):
        period_hint = (
            f"{fy_ctx['financial_year_start_display']} — "
            f"{fy_ctx['financial_year_end_display']}"
        )
    return [
        {
            'label': f'Opening balance ({label})',
            'value': f"KES {fy_ctx.get('opening_balance_display', '0.00')}",
            'hint': period_hint,
        },
        {
            'label': f'Closing balance ({label})',
            'value': f"KES {fy_ctx.get('closing_balance_display', '0.00')}",
            'hint': 'Live · updates with ledger activity',
        },
    ]


def _table(columns, rows):
    return {'columns': columns, 'rows': rows}


def build_vote_position(vote_meta, vote_name=''):
    """Budget / expenditure / balance snapshot for a single vote."""
    meta = vote_meta or {}
    name = (vote_name or meta.get('vote_name') or '').strip().upper()
    budget = float(meta.get('allocated') or 0)
    expenditure = float(meta.get('used') or 0)
    collections = float(meta.get('available') or 0)
    balance = budget - expenditure
    util = (expenditure / budget * 100.0) if budget > 0 else None
    return {
        'vote_name': name,
        'description': meta.get('description') or '—',
        'budget': budget,
        'budget_display': meta.get('allocated_display') or _fmt_kes(budget),
        'expenditure': expenditure,
        'expenditure_display': meta.get('used_display') or _fmt_kes(expenditure),
        'balance': balance,
        'balance_display': _fmt_kes(balance),
        'collections': collections,
        'collections_display': meta.get('available_display') or _fmt_kes(collections),
        'utilization_display': f'{util:.1f}%' if util is not None else '—',
        'utilization_pct': util if util is not None else 0,
    }


def _ledger_struct_row(kind, **fields):
    row = dict(fields)
    row['_ledger_row'] = kind
    return row


def _chronological_sort_key(row):
    txn_order = 0 if row.get('_txn_type') == 'invoice' else 1
    return (row.get('date') or '', row.get('_sort_ts', 0), txn_order)


def _gl_particulars(row):
    """Accounting narration for general ledger entries."""
    payee = (row.get('payee') or '').strip() or '—'
    desc = (row.get('description') or '').strip()
    method = (row.get('payment_method') or '').strip()
    if row.get('flow') == 'in':
        via = method or 'Cash/Bank'
        base = f'By {via} — Fee collected from {payee}'
        return f'{base} ({desc})' if desc and desc not in base else base
    via = method or 'Cash/Bank'
    base = f'To {payee} — {desc}' if desc else f'To {payee}'
    return f'{base} · via {via}' if method and method not in base else base


def _expenditure_particulars(row):
    desc = (row.get('description') or '').strip()
    item = desc.split(' · ')[0] if desc else ''
    return item or desc or 'Vote expenditure'


def _vote_movement_amounts(row):
    amt = float(row.get('amount') or 0)
    if row.get('flow') == 'in':
        return 0.0, amt
    if row.get('flow') == 'out':
        return amt, 0.0
    return 0.0, 0.0


def _vote_fund_balance_pack(cursor, filters, vote_filter, vote_meta, helpers):
    """Opening, period movement and closing balances for a vote fund."""
    fetch_detail = helpers.get('fetch_expenditure_vote_detail_rows')
    period_rows = fetch_detail(cursor, filters, vote_filter) if fetch_detail else []
    all_filters = dict(filters)
    all_filters['date_from'] = ''
    all_filters['date_to'] = ''
    all_rows = fetch_detail(cursor, all_filters, vote_filter) if fetch_detail else []

    position = build_vote_position(vote_meta, vote_filter)
    date_from = (filters.get('date_from') or '').strip()

    def is_before_period(r):
        d = (r.get('date') or '').strip()
        return bool(date_from and d and d < date_from)

    opening_debits = opening_credits = 0.0
    for r in all_rows:
        if is_before_period(r):
            debit, credit = _vote_movement_amounts(r)
            opening_debits += debit
            opening_credits += credit

    opening_fund = round(opening_credits - opening_debits, 2)
    opening_expenditure = round(opening_debits, 2)

    period_debits = period_credits = 0.0
    for r in period_rows:
        debit, credit = _vote_movement_amounts(r)
        period_debits += debit
        period_credits += credit

    period_debits = round(period_debits, 2)
    period_credits = round(period_credits, 2)
    closing_fund = round(opening_fund + period_credits - period_debits, 2)
    closing_expenditure = round(opening_expenditure + period_debits, 2)

    all_debits = round(sum(_vote_movement_amounts(r)[0] for r in all_rows), 2)
    all_credits = round(sum(_vote_movement_amounts(r)[1] for r in all_rows), 2)
    budget = float(position.get('budget') or 0)
    budget_remaining = round(budget - all_debits, 2)

    return {
        'position': position,
        'period_rows': period_rows,
        'opening_fund': opening_fund,
        'opening_expenditure': opening_expenditure,
        'period_debits': period_debits,
        'period_credits': period_credits,
        'closing_fund': closing_fund,
        'closing_expenditure': closing_expenditure,
        'all_debits': all_debits,
        'all_credits': all_credits,
        'budget_remaining': budget_remaining,
    }


def _build_vote_general_ledger(pack):
    opening = pack['opening_fund']
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            particulars='Opening balance (brought forward)',
            debit_display='—',
            credit_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    running = opening
    for r in sorted(pack['period_rows'], key=_chronological_sort_key):
        debit, credit = _vote_movement_amounts(r)
        running = round(running + credit - debit, 2)
        rows.append({
            'date': r.get('date', '—'),
            'reference': r.get('reference', '—'),
            'particulars': _gl_particulars(r),
            'debit_display': _fmt_kes(debit) if debit else '—',
            'credit_display': _fmt_kes(credit) if credit else '—',
            'balance_display': _fmt_kes(running),
        })
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            particulars='Period totals',
            debit_display=_fmt_kes(pack['period_debits']),
            credit_display=_fmt_kes(pack['period_credits']),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            particulars='Closing balance (carried forward)',
            debit_display='—',
            credit_display='—',
            balance_display=_fmt_kes(pack['closing_fund']),
        ),
    )
    summary = [
        {'label': 'Opening balance', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'Fund position before selected period'},
        {'label': 'Period debits', 'value': f"KES {_fmt_kes(pack['period_debits'])}", 'hint': 'Expenditure in period'},
        {'label': 'Period credits', 'value': f"KES {_fmt_kes(pack['period_credits'])}", 'hint': 'Collections in period'},
        {'label': 'Closing balance', 'value': f"KES {_fmt_kes(pack['closing_fund'])}", 'hint': 'Opening + credits − debits'},
        {'label': 'Budget remaining', 'value': f"KES {_fmt_kes(pack['budget_remaining'])}", 'hint': 'Vote budget minus all-time expenditure'},
    ]
    return rows, summary


def _build_vote_expenditure_ledger(pack):
    opening = pack['opening_expenditure']
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            payee='—',
            particulars='Opening expenditure (brought forward)',
            method_label='—',
            amount_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    running = opening
    out_rows = [r for r in pack['period_rows'] if r.get('flow') == 'out']
    for r in sorted(out_rows, key=_chronological_sort_key):
        amt = float(r.get('amount') or 0)
        running = round(running + amt, 2)
        method = (r.get('payment_method') or '').strip() or '—'
        rows.append({
            'date': r.get('date', '—'),
            'reference': r.get('reference', '—'),
            'payee': r.get('payee', '—'),
            'particulars': _expenditure_particulars(r),
            'method_label': method,
            'amount_display': r.get('amount_display', _fmt_kes(amt)),
            'balance_display': _fmt_kes(running),
        })
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            payee='—',
            particulars='Period expenditure total',
            method_label='—',
            amount_display=_fmt_kes(pack['period_debits']),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            payee='—',
            particulars='Cumulative expenditure (carried forward)',
            method_label='—',
            amount_display='—',
            balance_display=_fmt_kes(pack['closing_expenditure']),
        ),
    )
    summary = [
        {'label': 'Opening expenditure', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'Spend before selected period'},
        {'label': 'Period expenditure', 'value': f"KES {_fmt_kes(pack['period_debits'])}", 'hint': 'Outflows in period'},
        {'label': 'Cumulative expenditure', 'value': f"KES {_fmt_kes(pack['closing_expenditure'])}", 'hint': 'All spend through period end'},
        {'label': 'Budget remaining', 'value': f"KES {_fmt_kes(pack['budget_remaining'])}", 'hint': 'Vote budget minus cumulative spend'},
    ]
    return rows, summary


def _ap_line_in_period(line, filters):
    date_from = (filters.get('date_from') or '').strip()
    date_to = (filters.get('date_to') or '').strip()
    d = (line.get('date') or '').strip()
    if date_from and d and d < date_from:
        return False
    if date_to and d and d > date_to:
        return False
    return True


def _build_vote_ap_ledger(raw_rows, filters):
    """Creditors/AP subsidiary ledger — invoice lines then payment lines, chronological."""
    all_lines = sorted(raw_rows, key=_chronological_sort_key)
    date_from = (filters.get('date_from') or '').strip()

    opening = 0.0
    for line in all_lines:
        d = (line.get('date') or '').strip()
        if date_from and d and d < date_from:
            opening += float(line.get('_invoice') or 0) - float(line.get('_payment') or 0)
    opening = round(opening, 2)

    period_lines = [ln for ln in all_lines if _ap_line_in_period(ln, filters)]
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            supplier='—',
            particulars='Opening balance (brought forward)',
            invoice_display='—',
            payment_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    running = opening
    total_invoice = total_payment = 0.0
    for line in period_lines:
        invoiced = float(line.get('_invoice') or 0)
        paid = float(line.get('_payment') or 0)
        total_invoice += invoiced
        total_payment += paid
        running = round(running + invoiced - paid, 2)
        rows.append({
            'date': line.get('date', '—'),
            'reference': line.get('reference', '—'),
            'supplier': line.get('supplier', '—'),
            'particulars': line.get('particulars', '—'),
            'invoice_display': _fmt_kes(invoiced) if invoiced else '—',
            'payment_display': _fmt_kes(paid) if paid else '—',
            'balance_display': _fmt_kes(running),
        })
    total_invoice = round(total_invoice, 2)
    total_payment = round(total_payment, 2)
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            supplier='—',
            particulars='Period totals',
            invoice_display=_fmt_kes(total_invoice),
            payment_display=_fmt_kes(total_payment),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            supplier='—',
            particulars='Closing balance (carried forward)',
            invoice_display='—',
            payment_display='—',
            balance_display=_fmt_kes(running),
        ),
    )
    summary = [
        {'label': 'Opening payables', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'Balance before selected period'},
        {'label': 'Invoices (period)', 'value': f"KES {_fmt_kes(total_invoice)}", 'hint': 'New supplier invoices'},
        {'label': 'Payments (period)', 'value': f"KES {_fmt_kes(total_payment)}", 'hint': 'Settlements made'},
        {'label': 'Closing payables', 'value': f"KES {_fmt_kes(running)}", 'hint': 'Outstanding at period end'},
    ]
    return rows, summary


def _build_vote_payroll_ledger(raw_rows):
    """Salary disbursement register — chronological payment listing."""
    lines = sorted(raw_rows, key=_chronological_sort_key)
    rows = []
    total = 0.0
    for r in lines:
        amt = float(r.get('_amount') or 0)
        total += amt
        rows.append({
            'date': r.get('date', '—'),
            'reference': r.get('reference', '—'),
            'payee': r.get('payee', '—'),
            'pay_period': r.get('pay_period', '—'),
            'method_label': r.get('method_label', '—'),
            'amount_display': r.get('amount_display', _fmt_kes(amt)),
        })
    total = round(total, 2)
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            payee='—',
            pay_period='—',
            method_label='—',
            amount_display=_fmt_kes(total),
        ),
    )
    summary = [
        {'label': 'Total disbursed', 'value': f"KES {_fmt_kes(total)}", 'hint': 'School-wide salaries in period'},
        {'label': 'Payments', 'value': str(len(lines)), 'hint': 'Not linked to individual votes'},
    ]
    return rows, summary


def _build_vote_cheque_register(raw_rows, pack):
    """Cash book / payment register — receipts and payments with running balance."""
    opening = pack.get('opening_fund', 0.0)
    lines = sorted(raw_rows, key=_chronological_sort_key)
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            particulars='Opening balance (brought forward)',
            receipt_display='—',
            payment_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    running = opening
    total_in = total_out = 0.0
    for r in lines:
        amt = float(r.get('_amount') or 0)
        flow = r.get('_flow') or ('in' if r.get('type_label') == 'Fee collection' else 'out')
        method = (r.get('method_label') or '').strip()
        payee = (r.get('payee') or '').strip() or '—'
        ref = (r.get('reference') or '').strip() or '—'
        if flow == 'in':
            total_in += amt
            receipt, payment = amt, 0.0
            particulars = f"Receipt from {payee}"
            if method:
                particulars += f' · {method}'
        else:
            total_out += amt
            receipt, payment = 0.0, amt
            particulars = f"Payment to {payee}"
            if method:
                particulars += f' · {method}'
        running = round(running + receipt - payment, 2)
        rows.append({
            'date': r.get('date', '—'),
            'reference': ref,
            'particulars': particulars,
            'receipt_display': _fmt_kes(receipt) if receipt else '—',
            'payment_display': _fmt_kes(payment) if payment else '—',
            'balance_display': _fmt_kes(running),
        })
    total_in = round(total_in, 2)
    total_out = round(total_out, 2)
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            particulars='Period totals',
            receipt_display=_fmt_kes(total_in),
            payment_display=_fmt_kes(total_out),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            particulars='Closing balance (carried forward)',
            receipt_display='—',
            payment_display='—',
            balance_display=_fmt_kes(running),
        ),
    )
    summary = [
        {'label': 'Opening balance', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'Before selected period'},
        {'label': 'Total receipts', 'value': f"KES {_fmt_kes(total_in)}", 'hint': 'Fee collections for this vote'},
        {'label': 'Total payments', 'value': f"KES {_fmt_kes(total_out)}", 'hint': 'Supplier disbursements'},
        {'label': 'Closing balance', 'value': f"KES {_fmt_kes(running)}", 'hint': 'Opening + receipts − payments'},
    ]
    return rows, summary


def _display_ledger_rows(rows, keys):
    display = []
    for r in rows:
        d = {k: r.get(k, '—') for k in keys}
        if r.get('_ledger_row'):
            d['_ledger_row'] = r['_ledger_row']
        display.append(d)
    return display


def _filter_vote_period_rows(rows, q):
    if not q:
        return rows
    ql = q.lower()
    return [
        r for r in rows
        if ql in (r.get('payee') or '').lower()
        or ql in (r.get('reference') or '').lower()
        or ql in (r.get('description') or '').lower()
        or ql in (r.get('particulars') or '').lower()
        or ql in (r.get('type_label') or '').lower()
    ]


def _recompute_pack_period_totals(pack):
    period_debits = period_credits = 0.0
    for r in pack['period_rows']:
        debit, credit = _vote_movement_amounts(r)
        period_debits += debit
        period_credits += credit
    pack['period_debits'] = round(period_debits, 2)
    pack['period_credits'] = round(period_credits, 2)
    pack['closing_fund'] = round(pack['opening_fund'] + pack['period_credits'] - pack['period_debits'], 2)
    pack['closing_expenditure'] = round(pack['opening_expenditure'] + pack['period_debits'], 2)


def _all_votes_fund_balance_pack(cursor, filters, vote_rows, helpers):
    """Opening, period movement and closing balances aggregated across all votes."""
    fetch_detail = helpers.get('fetch_all_votes_expenditure_detail_rows')
    period_rows = fetch_detail(cursor, filters) if fetch_detail else []
    all_filters = dict(filters)
    all_filters['date_from'] = ''
    all_filters['date_to'] = ''
    all_rows = fetch_detail(cursor, all_filters) if fetch_detail else []

    date_from = (filters.get('date_from') or '').strip()

    def is_before_period(r):
        d = (r.get('date') or '').strip()
        return bool(date_from and d and d < date_from)

    opening_debits = opening_credits = 0.0
    for r in all_rows:
        if is_before_period(r):
            debit, credit = _vote_movement_amounts(r)
            opening_debits += debit
            opening_credits += credit

    opening_fund = round(opening_credits - opening_debits, 2)
    opening_expenditure = round(opening_debits, 2)

    period_debits = period_credits = 0.0
    for r in period_rows:
        debit, credit = _vote_movement_amounts(r)
        period_debits += debit
        period_credits += credit

    period_debits = round(period_debits, 2)
    period_credits = round(period_credits, 2)
    closing_fund = round(opening_fund + period_credits - period_debits, 2)
    closing_expenditure = round(opening_expenditure + period_debits, 2)

    all_debits = round(sum(_vote_movement_amounts(r)[0] for r in all_rows), 2)
    all_credits = round(sum(_vote_movement_amounts(r)[1] for r in all_rows), 2)
    total_budget = sum(float(v.get('allocated') or 0) for v in vote_rows)
    budget_remaining = round(total_budget - all_debits, 2)

    position = {
        'budget': total_budget,
        'budget_display': _fmt_kes(total_budget),
        'expenditure': all_debits,
        'expenditure_display': _fmt_kes(all_debits),
        'balance': round(total_budget - all_debits, 2),
        'balance_display': _fmt_kes(total_budget - all_debits),
        'collections': all_credits,
        'collections_display': _fmt_kes(all_credits),
    }

    return {
        'position': position,
        'period_rows': period_rows,
        'opening_fund': opening_fund,
        'opening_expenditure': opening_expenditure,
        'period_debits': period_debits,
        'period_credits': period_credits,
        'closing_fund': closing_fund,
        'closing_expenditure': closing_expenditure,
        'all_debits': all_debits,
        'all_credits': all_credits,
        'budget_remaining': budget_remaining,
    }


def _build_books_general_ledger(pack):
    """School-wide general ledger with vote column."""
    opening = pack['opening_fund']
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            vote_name='—',
            particulars='Opening balance (brought forward)',
            debit_display='—',
            credit_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    running = opening
    for r in sorted(pack['period_rows'], key=_chronological_sort_key):
        debit, credit = _vote_movement_amounts(r)
        running = round(running + credit - debit, 2)
        rows.append({
            'date': r.get('date', '—'),
            'reference': r.get('reference', '—'),
            'vote_name': r.get('vote_name', '—'),
            'particulars': _gl_particulars(r),
            'debit_display': _fmt_kes(debit) if debit else '—',
            'credit_display': _fmt_kes(credit) if credit else '—',
            'balance_display': _fmt_kes(running),
        })
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            vote_name='—',
            particulars='Period totals',
            debit_display=_fmt_kes(pack['period_debits']),
            credit_display=_fmt_kes(pack['period_credits']),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            vote_name='—',
            particulars='Closing balance (carried forward)',
            debit_display='—',
            credit_display='—',
            balance_display=_fmt_kes(pack['closing_fund']),
        ),
    )
    summary = [
        {'label': 'Opening balance', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'All votes — before selected period'},
        {'label': 'Period debits', 'value': f"KES {_fmt_kes(pack['period_debits'])}", 'hint': 'Expenditure in period'},
        {'label': 'Period credits', 'value': f"KES {_fmt_kes(pack['period_credits'])}", 'hint': 'Collections in period'},
        {'label': 'Closing balance', 'value': f"KES {_fmt_kes(pack['closing_fund'])}", 'hint': 'Opening + credits − debits'},
        {'label': 'Budget remaining', 'value': f"KES {_fmt_kes(pack['budget_remaining'])}", 'hint': 'Total vote budget minus all-time expenditure'},
    ]
    return rows, summary


def _build_books_expenditure_ledger(pack):
    """School-wide expenditure ledger with vote column."""
    opening = pack['opening_expenditure']
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            vote_name='—',
            payee='—',
            particulars='Opening expenditure (brought forward)',
            method_label='—',
            amount_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    running = opening
    out_rows = [r for r in pack['period_rows'] if r.get('flow') == 'out']
    for r in sorted(out_rows, key=_chronological_sort_key):
        amt = float(r.get('amount') or 0)
        running = round(running + amt, 2)
        method = (r.get('payment_method') or '').strip() or '—'
        rows.append({
            'date': r.get('date', '—'),
            'reference': r.get('reference', '—'),
            'vote_name': r.get('vote_name', '—'),
            'payee': r.get('payee', '—'),
            'particulars': _expenditure_particulars(r),
            'method_label': method,
            'amount_display': r.get('amount_display', _fmt_kes(amt)),
            'balance_display': _fmt_kes(running),
        })
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            vote_name='—',
            payee='—',
            particulars='Period expenditure total',
            method_label='—',
            amount_display=_fmt_kes(pack['period_debits']),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            vote_name='—',
            payee='—',
            particulars='Cumulative expenditure (carried forward)',
            method_label='—',
            amount_display='—',
            balance_display=_fmt_kes(pack['closing_expenditure']),
        ),
    )
    summary = [
        {'label': 'Opening expenditure', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'All votes — before selected period'},
        {'label': 'Period expenditure', 'value': f"KES {_fmt_kes(pack['period_debits'])}", 'hint': 'Outflows in period'},
        {'label': 'Cumulative expenditure', 'value': f"KES {_fmt_kes(pack['closing_expenditure'])}", 'hint': 'All spend through period end'},
        {'label': 'Budget remaining', 'value': f"KES {_fmt_kes(pack['budget_remaining'])}", 'hint': 'Total vote budget minus cumulative spend'},
    ]
    return rows, summary


def _expenditure_books_ledger_specs():
    return {
        'general-ledger': (
            [
                {'key': 'date', 'label': 'Date'},
                {'key': 'reference', 'label': 'Journal ref'},
                {'key': 'vote_name', 'label': 'Vote'},
                {'key': 'particulars', 'label': 'Particulars'},
                {'key': 'debit_display', 'label': 'Debit (KES)', 'align': 'right'},
                {'key': 'credit_display', 'label': 'Credit (KES)', 'align': 'right'},
                {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
            ],
            ('date', 'reference', 'vote_name', 'particulars', 'debit_display', 'credit_display', 'balance_display'),
        ),
        'expenditure-ledger': (
            [
                {'key': 'date', 'label': 'Date'},
                {'key': 'reference', 'label': 'Voucher no'},
                {'key': 'vote_name', 'label': 'Vote'},
                {'key': 'payee', 'label': 'Payee'},
                {'key': 'particulars', 'label': 'Particulars'},
                {'key': 'method_label', 'label': 'Method'},
                {'key': 'amount_display', 'label': 'Amount (KES)', 'align': 'right'},
                {'key': 'balance_display', 'label': 'Cumulative (KES)', 'align': 'right'},
            ],
            ('date', 'reference', 'vote_name', 'payee', 'particulars', 'method_label', 'amount_display', 'balance_display'),
        ),
        'accounts-payable-ledger': (
            [
                {'key': 'date', 'label': 'Date'},
                {'key': 'reference', 'label': 'Ref'},
                {'key': 'vote_name', 'label': 'Vote'},
                {'key': 'supplier', 'label': 'Supplier'},
                {'key': 'particulars', 'label': 'Particulars'},
                {'key': 'invoice_display', 'label': 'Invoice (Dr)', 'align': 'right'},
                {'key': 'payment_display', 'label': 'Payment (Cr)', 'align': 'right'},
                {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
            ],
            ('date', 'reference', 'vote_name', 'supplier', 'particulars', 'invoice_display', 'payment_display', 'balance_display'),
        ),
        'cheque-register': (
            [
                {'key': 'date', 'label': 'Date'},
                {'key': 'reference', 'label': 'Cheque / ref'},
                {'key': 'particulars', 'label': 'Particulars'},
                {'key': 'receipt_display', 'label': 'Receipts (KES)', 'align': 'right'},
                {'key': 'payment_display', 'label': 'Payments (KES)', 'align': 'right'},
                {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
            ],
            ('date', 'reference', 'particulars', 'receipt_display', 'payment_display', 'balance_display'),
        ),
        'payroll-ledger': (
            [
                {'key': 'date', 'label': 'Pay date'},
                {'key': 'reference', 'label': 'Ref'},
                {'key': 'payee', 'label': 'Employee'},
                {'key': 'pay_period', 'label': 'Pay period'},
                {'key': 'method_label', 'label': 'Method'},
                {'key': 'amount_display', 'label': 'Net paid (KES)', 'align': 'right'},
            ],
            ('date', 'reference', 'payee', 'pay_period', 'method_label', 'amount_display'),
        ),
    }


def _build_books_ap_ledger(raw_rows, filters):
    """AP ledger for all votes — adds vote_name column."""
    all_lines = sorted(raw_rows, key=_chronological_sort_key)
    date_from = (filters.get('date_from') or '').strip()

    opening = 0.0
    for line in all_lines:
        d = (line.get('date') or '').strip()
        if date_from and d and d < date_from:
            opening += float(line.get('_invoice') or 0) - float(line.get('_payment') or 0)
    opening = round(opening, 2)

    period_lines = [ln for ln in all_lines if _ap_line_in_period(ln, filters)]
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            vote_name='—',
            supplier='—',
            particulars='Opening balance (brought forward)',
            invoice_display='—',
            payment_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    running = opening
    total_invoice = total_payment = 0.0
    for line in period_lines:
        inv = float(line.get('_invoice') or 0)
        pay = float(line.get('_payment') or 0)
        total_invoice += inv
        total_payment += pay
        running = round(running + inv - pay, 2)
        rows.append({
            'date': line.get('date', '—'),
            'reference': line.get('reference', '—'),
            'vote_name': line.get('vote_name', '—'),
            'supplier': line.get('supplier', '—'),
            'particulars': line.get('particulars', '—'),
            'invoice_display': _fmt_kes(inv) if inv else '—',
            'payment_display': _fmt_kes(pay) if pay else '—',
            'balance_display': _fmt_kes(running),
        })
    total_invoice = round(total_invoice, 2)
    total_payment = round(total_payment, 2)
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            vote_name='—',
            supplier='—',
            particulars='Period totals',
            invoice_display=_fmt_kes(total_invoice),
            payment_display=_fmt_kes(total_payment),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            vote_name='—',
            supplier='—',
            particulars='Closing balance (carried forward)',
            invoice_display='—',
            payment_display='—',
            balance_display=_fmt_kes(running),
        ),
    )
    summary = [
        {'label': 'Opening payables', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'All votes — before selected period'},
        {'label': 'Invoices (Dr)', 'value': f"KES {_fmt_kes(total_invoice)}", 'hint': 'Stock-in invoices in period'},
        {'label': 'Payments (Cr)', 'value': f"KES {_fmt_kes(total_payment)}", 'hint': 'Settlements in period'},
        {'label': 'Closing payables', 'value': f"KES {_fmt_kes(running)}", 'hint': 'Outstanding supplier balance'},
    ]
    return rows, summary


def fetch_report_payload(cursor, slug, filters, helpers):
    """Build JSON payload for a finance report (summary cards + table)."""
    if slug == 'revenue-collection':
        return _report_revenue_collection(cursor, filters, helpers)
    if slug == 'expenditure':
        return _report_expenditure(cursor, filters, helpers)
    if slug == 'financial-statements':
        return _report_financial_statements(cursor, filters, helpers)
    if slug == 'audit-compliance':
        return _report_audit_compliance(cursor, filters, helpers)
    if slug == 'periodic-summary':
        return _report_periodic_summary(cursor, filters, helpers)
    if slug == 'student-specific':
        return {'student_specific': True, 'message': 'Use student table on this page.'}
    return {'error': 'Unknown report'}


def _report_revenue_collection_blank(message):
    return {
        'view_mode': 'revenue_books_blank',
        'books_message': message,
        'summary': [],
        'table': _table([], []),
        'row_count': 0,
    }


def _report_revenue_collection_for_account(cursor, filters, helpers, account_id, book):
    """General Ledger or Cash Book for one finance account."""
    acct_helpers = helpers.get('account_report_helpers') or {}
    load_account = acct_helpers.get('load_account')
    account = load_account(cursor, account_id) if load_account else None
    if not account:
        return _report_revenue_collection_blank('Finance account not found.')

    refresh = acct_helpers.get('refresh_balances')
    if refresh:
        try:
            refresh(cursor, account_id)
        except TypeError:
            try:
                refresh(cursor)
            except Exception as e:
                print(f'_report_revenue_collection_for_account refresh: {e}')
        except Exception as e:
            print(f'_report_revenue_collection_for_account refresh: {e}')

    date_from = filters.get('date_from') or ''
    date_to = filters.get('date_to') or ''
    period = finance_account_reports_mod._resolve_account_period(
        cursor, account_id, date_from, date_to, account, acct_helpers,
    )
    prior_rows = finance_account_reports_mod._fetch_prior_ledger_rows(
        cursor, account_id, date_from, acct_helpers,
    )
    period_rows = period.get('ledger') or []

    if filters.get('q'):
        ql = filters['q'].lower()
        period_rows = [
            r for r in period_rows
            if ql in (r.get('description') or '').lower()
            or ql in (r.get('reference') or '').lower()
        ]

    linked_votes = []
    load_votes = acct_helpers.get('load_account_expense_votes')
    if load_votes:
        try:
            linked_votes = load_votes(cursor, account_id) or []
        except Exception as e:
            print(f'_report_revenue_collection_for_account votes: {e}')

    account_name = (account.get('account_name') or 'Account').strip()
    opening = period.get('opening', 0.0)
    closing = period.get('closing', 0.0)
    total_debit = period.get('total_debit', 0.0)
    total_credit = period.get('total_credit', 0.0)
    summary = finance_account_reports_mod._period_ledger_summary(
        opening, total_debit, total_credit, closing,
    )

    if book == 'cash-book':
        cash_lines = [
            {
                'date': r.get('date', '—'),
                'reference': r.get('reference', '—'),
                'particulars': r.get('description', '—'),
                'receipt': float(r.get('credit') or 0),
                'payment': float(r.get('debit') or 0),
            }
            for r in period_rows
        ]
        pack = {'opening_fund': opening}
        rows, cb_summary, columns, _keys = _build_cash_book_rows(pack, cash_lines)
        return {
            'view_mode': 'revenue_cash_book',
            'account_name': account_name,
            'section_title': f'{account_name} — The Cash Book',
            'summary': cb_summary,
            'table': _table(columns, rows),
            'row_count': len([r for r in rows if not r.get('_ledger_row')]),
        }

    vote_ledgers = finance_account_reports_mod._build_per_vote_general_ledgers(
        prior_rows, period_rows, linked_votes,
    )
    return {
        'view_mode': 'revenue_general_ledger',
        'account_name': account_name,
        'section_title': f'{account_name} — The General Ledger',
        'summary': summary,
        'vote_ledgers': vote_ledgers,
        'row_count': sum(int(s.get('transaction_count') or 0) for s in vote_ledgers),
    }


def _report_revenue_collection(cursor, filters, helpers):
    book = (filters.get('book') or 'general-ledger').strip().lower()
    if book not in REVENUE_BOOK_SLUGS:
        book = 'general-ledger'

    account_id = filters.get('finance_account_id')
    if not account_id:
        accounts = helpers.get('finance_accounts') or []
        if not accounts:
            load_opts = helpers.get('load_filter_options')
            if load_opts:
                try:
                    accounts = (load_opts(cursor) or {}).get('finance_accounts') or []
                except Exception as e:
                    print(f'_report_revenue_collection accounts: {e}')
        if len(accounts) == 1:
            account_id = accounts[0].get('id')
        elif accounts:
            return _report_revenue_collection_blank(
                'Choose a finance account from the filters or sidebar to view its General Ledger and Cash Book.',
            )
        else:
            return _report_revenue_collection_blank(
                'Register a finance account first, then return here to view its books.',
            )

    return _report_revenue_collection_for_account(
        cursor, filters, helpers, int(account_id), book,
    )


def _vote_position_summary(position):
    return _summary_cards([
        {'label': 'Vote Budget', 'value': f"KES {position['budget_display']}", 'hint': 'Total allocated for this vote'},
        {'label': 'Vote Expenditure', 'value': f"KES {position['expenditure_display']}", 'hint': 'Supplier payments (actual spend)'},
        {'label': 'Vote Balance', 'value': f"KES {position['balance_display']}", 'hint': 'Budget minus expenditure'},
    ])


def _report_expenditure_vote(cursor, filters, helpers, vote_filter, vote_meta, fy_ctx):
    """Vote overview or vote-scoped ledger report."""
    fetch_vote_detail = helpers.get('fetch_expenditure_vote_detail_rows')
    ledger = (filters.get('ledger') or '').strip().lower()
    position = build_vote_position(vote_meta, vote_filter)

    if ledger and ledger in VOTE_LEDGER_SLUGS:
        pack = _vote_fund_balance_pack(cursor, filters, vote_filter, vote_meta, helpers)
        position = pack['position']
        if filters.get('q') and ledger in ('general-ledger', 'expenditure-ledger'):
            pack['period_rows'] = _filter_vote_period_rows(pack['period_rows'], filters['q'])
            _recompute_pack_period_totals(pack)
        fetch_map = {
            'accounts-payable-ledger': helpers.get('fetch_vote_accounts_payable_ledger_rows'),
            'payroll-ledger': helpers.get('fetch_vote_payroll_ledger_rows'),
            'cheque-register': helpers.get('fetch_vote_cheque_register_rows'),
        }
        meta = next((m for m in VOTE_LEDGER_NAV if m['slug'] == ledger), {})
        ledger_specs = {
            'general-ledger': (
                [
                    {'key': 'date', 'label': 'Date'},
                    {'key': 'reference', 'label': 'Journal ref'},
                    {'key': 'particulars', 'label': 'Particulars'},
                    {'key': 'debit_display', 'label': 'Debit (KES)', 'align': 'right'},
                    {'key': 'credit_display', 'label': 'Credit (KES)', 'align': 'right'},
                    {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
                ],
                ('date', 'reference', 'particulars', 'debit_display', 'credit_display', 'balance_display'),
            ),
            'expenditure-ledger': (
                [
                    {'key': 'date', 'label': 'Date'},
                    {'key': 'reference', 'label': 'Voucher no'},
                    {'key': 'payee', 'label': 'Payee'},
                    {'key': 'particulars', 'label': 'Particulars'},
                    {'key': 'method_label', 'label': 'Method'},
                    {'key': 'amount_display', 'label': 'Amount (KES)', 'align': 'right'},
                    {'key': 'balance_display', 'label': 'Cumulative (KES)', 'align': 'right'},
                ],
                ('date', 'reference', 'payee', 'particulars', 'method_label', 'amount_display', 'balance_display'),
            ),
            'accounts-payable-ledger': (
                [
                    {'key': 'date', 'label': 'Date'},
                    {'key': 'reference', 'label': 'Ref'},
                    {'key': 'supplier', 'label': 'Supplier'},
                    {'key': 'particulars', 'label': 'Particulars'},
                    {'key': 'invoice_display', 'label': 'Invoice (Dr)', 'align': 'right'},
                    {'key': 'payment_display', 'label': 'Payment (Cr)', 'align': 'right'},
                    {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
                ],
                ('date', 'reference', 'supplier', 'particulars', 'invoice_display', 'payment_display', 'balance_display'),
            ),
            'payroll-ledger': (
                [
                    {'key': 'date', 'label': 'Pay date'},
                    {'key': 'reference', 'label': 'Ref'},
                    {'key': 'payee', 'label': 'Employee'},
                    {'key': 'pay_period', 'label': 'Pay period'},
                    {'key': 'method_label', 'label': 'Method'},
                    {'key': 'amount_display', 'label': 'Net paid (KES)', 'align': 'right'},
                ],
                ('date', 'reference', 'payee', 'pay_period', 'method_label', 'amount_display'),
            ),
            'cheque-register': (
                [
                    {'key': 'date', 'label': 'Date'},
                    {'key': 'reference', 'label': 'Cheque / ref'},
                    {'key': 'particulars', 'label': 'Particulars'},
                    {'key': 'receipt_display', 'label': 'Receipts (KES)', 'align': 'right'},
                    {'key': 'payment_display', 'label': 'Payments (KES)', 'align': 'right'},
                    {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
                ],
                ('date', 'reference', 'particulars', 'receipt_display', 'payment_display', 'balance_display'),
            ),
        }
        columns, keys = ledger_specs[ledger]
        title = meta.get('title') or 'Vote ledger'

        if ledger == 'general-ledger':
            ledger_rows, ledger_summary = _build_vote_general_ledger(pack)
        elif ledger == 'expenditure-ledger':
            ledger_rows, ledger_summary = _build_vote_expenditure_ledger(pack)
        else:
            fetch_fn = fetch_map.get(ledger)
            raw_rows = fetch_fn(cursor, filters, vote_filter) if fetch_fn else []
            if filters.get('q'):
                ql = filters['q'].lower()
                raw_rows = [
                    r for r in raw_rows
                    if ql in (r.get('payee') or r.get('party') or r.get('supplier') or '').lower()
                    or ql in (r.get('reference') or '').lower()
                    or ql in (r.get('description') or r.get('particulars') or '').lower()
                    or ql in (r.get('type_label') or '').lower()
                ]
            if ledger == 'accounts-payable-ledger':
                ledger_rows, ledger_summary = _build_vote_ap_ledger(raw_rows, filters)
            elif ledger == 'payroll-ledger':
                ledger_rows, ledger_summary = _build_vote_payroll_ledger(raw_rows)
            else:
                ledger_rows, ledger_summary = _build_vote_cheque_register(raw_rows, pack)

        txn_count = sum(1 for r in ledger_rows if not r.get('_ledger_row'))
        summary = _summary_cards(ledger_summary)
        display = _display_ledger_rows(ledger_rows, keys)
        return {
            'summary': summary,
            'ledger_summary': ledger_summary,
            'table': _table(columns, display),
            'row_count': txn_count,
            'view_mode': 'vote_ledger',
            'vote_name': vote_filter,
            'vote_description': vote_meta.get('description') or '',
            'vote_position': position,
            'vote_ledger': ledger,
            'table_section_title': title,
            'vote_ledger_balance': {
                'opening_fund': pack.get('opening_fund'),
                'closing_fund': pack.get('closing_fund'),
                'period_debits': pack.get('period_debits'),
                'period_credits': pack.get('period_credits'),
                'budget_remaining': pack.get('budget_remaining'),
            },
        }

    detail_rows = fetch_vote_detail(cursor, filters, vote_filter) if fetch_vote_detail else []
    if filters.get('q'):
        ql = filters['q'].lower()
        detail_rows = [
            r for r in detail_rows
            if ql in (r.get('payee') or '').lower()
            or ql in (r.get('reference') or '').lower()
            or ql in (r.get('description') or '').lower()
            or ql in (r.get('type_label') or '').lower()
            or ql in (r.get('flow_label') or '').lower()
        ]
    total_in = sum(float(r.get('amount') or 0) for r in detail_rows if r.get('flow') == 'in')
    total_out = sum(float(r.get('amount') or 0) for r in detail_rows if r.get('flow') == 'out')
    position['period_collections'] = total_in
    position['period_collections_display'] = _fmt_kes(total_in)
    position['period_expenditure'] = total_out
    position['period_expenditure_display'] = _fmt_kes(total_out)
    summary = _vote_position_summary(position)
    columns = [
        {'key': 'date', 'label': 'Date'},
        {'key': 'flow_label', 'label': 'Flow'},
        {'key': 'type_label', 'label': 'Type'},
        {'key': 'reference', 'label': 'Reference'},
        {'key': 'payee', 'label': 'Party'},
        {'key': 'description', 'label': 'Description'},
        {'key': 'amount_display', 'label': 'Amount (KES)', 'align': 'right'},
    ]
    display = [
        {
            'date': r.get('date', '—'),
            'flow': r.get('flow', ''),
            'flow_label': r.get('flow_label', '—'),
            'type_label': r.get('type_label', '—'),
            'reference': r.get('reference', '—'),
            'payee': r.get('payee', '—'),
            'description': r.get('description', '—'),
            'amount_display': r.get('amount_display', '0.00'),
        }
        for r in detail_rows[:500]
    ]
    return {
        'summary': summary,
        'table': _table(columns, display),
        'row_count': len(detail_rows),
        'view_mode': 'vote_detail',
        'vote_name': vote_filter,
        'vote_description': vote_meta.get('description') or '',
        'vote_position': position,
        'vote_ledger': '',
        'table_section_title': 'Vote Transactions',
    }


def _report_expenditure_books(cursor, filters, helpers, vote_rows, fy_ctx):
    """School-wide expenditure books (all votes) when ledger query param is set."""
    ledger = (filters.get('ledger') or '').strip().lower()
    if ledger not in EXPENDITURE_BOOKS_INLINE_SLUGS:
        return {'error': 'Unknown ledger'}

    meta = next((m for m in EXPENDITURE_BOOKS_NAV if m['slug'] == ledger), {})
    title = meta.get('title') or 'Expenditure ledger'
    ledger_specs = _expenditure_books_ledger_specs()
    if ledger not in ledger_specs:
        return {'error': f'Ledger not configured: {ledger}'}
    columns, keys = ledger_specs[ledger]

    if ledger == 'payroll-ledger':
        fetch_fn = helpers.get('fetch_expenditure_books_payroll_lines')
        raw_rows = fetch_fn(cursor, filters) if fetch_fn else []
        if filters.get('q'):
            ql = filters['q'].lower()
            raw_rows = [
                r for r in raw_rows
                if ql in (r.get('payee') or '').lower()
                or ql in (r.get('reference') or '').lower()
                or ql in (r.get('pay_period') or '').lower()
                or ql in (r.get('method_label') or '').lower()
            ]
        ledger_rows, ledger_summary = _build_vote_payroll_ledger(raw_rows)
        position = {
            'budget': sum(float(v.get('allocated') or 0) for v in vote_rows),
            'expenditure': sum(float(v.get('used') or 0) for v in vote_rows),
        }
        txn_count = sum(1 for r in ledger_rows if not r.get('_ledger_row'))
        display = _display_ledger_rows(ledger_rows, keys)
        return {
            'summary': _summary_cards(ledger_summary),
            'ledger_summary': ledger_summary,
            'table': _table(columns, display),
            'row_count': txn_count,
            'view_mode': 'expenditure_ledger',
            'expenditure_ledger': ledger,
            'expenditure_position': position,
            'table_section_title': title,
        }

    pack = _all_votes_fund_balance_pack(cursor, filters, vote_rows, helpers)
    position = pack['position']

    if filters.get('q') and ledger in ('general-ledger', 'expenditure-ledger'):
        pack['period_rows'] = _filter_vote_period_rows(pack['period_rows'], filters['q'])
        _recompute_pack_period_totals(pack)

    fetch_map = {
        'accounts-payable-ledger': helpers.get('fetch_expenditure_books_ap_lines'),
        'cheque-register': helpers.get('fetch_expenditure_books_cheque_register'),
    }

    if ledger == 'general-ledger':
        ledger_rows, ledger_summary = _build_books_general_ledger(pack)
    elif ledger == 'expenditure-ledger':
        ledger_rows, ledger_summary = _build_books_expenditure_ledger(pack)
    else:
        fetch_fn = fetch_map.get(ledger)
        raw_rows = fetch_fn(cursor, filters) if fetch_fn else []
        if filters.get('q'):
            ql = filters['q'].lower()
            raw_rows = [
                r for r in raw_rows
                if ql in (r.get('payee') or r.get('party') or r.get('supplier') or '').lower()
                or ql in (r.get('reference') or '').lower()
                or ql in (r.get('description') or r.get('particulars') or '').lower()
                or ql in (r.get('type_label') or '').lower()
                or ql in (r.get('vote_name') or '').lower()
                or ql in (r.get('pay_period') or '').lower()
            ]
        if ledger == 'accounts-payable-ledger':
            ledger_rows, ledger_summary = _build_books_ap_ledger(raw_rows, filters)
        else:
            ledger_rows, ledger_summary = _build_vote_cheque_register(raw_rows, pack)

    txn_count = sum(1 for r in ledger_rows if not r.get('_ledger_row'))
    summary = _summary_cards(ledger_summary)
    display = _display_ledger_rows(ledger_rows, keys)
    return {
        'summary': summary,
        'ledger_summary': ledger_summary,
        'table': _table(columns, display),
        'row_count': txn_count,
        'view_mode': 'expenditure_ledger',
        'expenditure_ledger': ledger,
        'expenditure_position': position,
        'table_section_title': title,
        'expenditure_ledger_balance': {
            'opening_fund': pack.get('opening_fund'),
            'closing_fund': pack.get('closing_fund'),
            'period_debits': pack.get('period_debits'),
            'period_credits': pack.get('period_credits'),
            'budget_remaining': pack.get('budget_remaining'),
        },
    }


def _report_expenditure(cursor, filters, helpers):
    fy_fn = helpers.get('fetch_financial_year_context')
    fy_ctx = fy_fn(cursor, filters) if fy_fn else {}
    fetch_vote_summary = helpers.get('fetch_expenditure_vote_summary')
    fetch_vote_detail = helpers.get('fetch_expenditure_vote_detail_rows')
    vote_filter = (filters.get('vote') or '').strip().upper()
    ledger = (filters.get('ledger') or '').strip().lower()

    vote_rows = fetch_vote_summary(cursor, filters) if fetch_vote_summary else []
    if filters.get('q') and not ledger:
        ql = filters['q'].lower()
        vote_rows = [
            v for v in vote_rows
            if ql in (v.get('vote_name') or '').lower()
            or ql in (v.get('description') or '').lower()
        ]

    if vote_filter:
        vote_meta = next((v for v in vote_rows if (v.get('vote_name') or '').upper() == vote_filter), {})
        return _report_expenditure_vote(cursor, filters, helpers, vote_filter, vote_meta, fy_ctx)

    if ledger and ledger in EXPENDITURE_BOOKS_INLINE_SLUGS:
        return _report_expenditure_books(cursor, filters, helpers, vote_rows, fy_ctx)

    total_budget = sum(float(v.get('allocated') or 0) for v in vote_rows)
    total_exp = sum(float(v.get('used') or 0) for v in vote_rows)
    total_bal = sum(float(v.get('balance') or 0) for v in vote_rows)
    summary = _fy_balance_summary_cards(fy_ctx) + _summary_cards([
        {'label': 'Votes', 'value': str(len(vote_rows))},
        {'label': 'Total vote budget', 'value': f'KES {_fmt_kes(total_budget)}'},
        {'label': 'Total vote expenditure', 'value': f'KES {_fmt_kes(total_exp)}'},
        {'label': 'Total vote balance', 'value': f'KES {_fmt_kes(total_bal)}'},
    ])
    columns = [
        {'key': 'vote_name', 'label': 'Vote'},
        {'key': 'description', 'label': 'Description'},
        {'key': 'budget_display', 'label': 'Vote Budget (KES)', 'align': 'right'},
        {'key': 'expenditure_display', 'label': 'Vote Expenditure (KES)', 'align': 'right'},
        {'key': 'balance_display', 'label': 'Vote Balance (KES)', 'align': 'right'},
    ]
    display = [
        {
            'vote_name': v.get('vote_name', '—'),
            'description': v.get('description', '—'),
            'budget_display': v.get('allocated_display', '0.00'),
            'expenditure_display': v.get('used_display', '0.00'),
            'balance_display': v.get('balance_display', '0.00'),
            'vote_slug': v.get('vote_slug', ''),
        }
        for v in vote_rows
    ]
    return {
        'summary': summary,
        'table': _table(columns, display),
        'row_count': len(vote_rows),
        'view_mode': 'votes',
    }


def _statements_blank_payload(message, books_ready=False):
    return {
        'summary': [],
        'table': _table([], []),
        'row_count': 0,
        'view_mode': 'statements_blank',
        'books_ready': books_ready,
        'books_message': message or '',
        'table_section_title': '',
    }


def _financial_books_can_be_kept(cursor, filters, helpers):
    """True when vote books, finance accounts and financial year support proper statements."""
    fy_fn = helpers.get('fetch_financial_year_context')
    fy_ctx = fy_fn(cursor, filters) if fy_fn else {}
    if not fy_ctx.get('is_configured'):
        return False, 'Configure an active financial year before keeping the books of account.'

    fetch_votes = helpers.get('fetch_expenditure_vote_summary')
    vote_rows = fetch_votes(cursor, filters) if fetch_votes else []
    if not vote_rows:
        return False, 'Expenditure vote books are not set up. Add fee votes to keep the books of account.'

    if not helpers.get('fetch_all_votes_expenditure_detail_rows'):
        return False, 'Ledger data is not available for this period.'

    analytics = helpers.get('fetch_dashboard_analytics')
    data = analytics(cursor, filters) if analytics else {}
    accounts = data.get('accounts') or {}
    if not int(accounts.get('total_accounts') or 0):
        return False, 'Register finance accounts before preparing financial statements.'

    total_budget = sum(float(v.get('allocated') or 0) for v in vote_rows)
    pack = _all_votes_fund_balance_pack(cursor, filters, vote_rows, helpers)
    has_activity = bool(pack.get('period_rows'))
    if total_budget <= 0 and not has_activity:
        return False, 'Vote budgets or period transactions are required to keep the books of account.'

    return True, ''


def _books_section_row(title, **fields):
    """Section heading row in a book of accounts."""
    fields.pop('particulars', None)
    row = _ledger_struct_row('section', particulars=title, **fields)
    return row


def _statement_context(cursor, filters, helpers):
    """Shared figures for school-wide financial statements."""
    fy_fn = helpers.get('fetch_financial_year_context')
    fy_ctx = fy_fn(cursor, filters) if fy_fn else {}
    fetch_votes = helpers.get('fetch_expenditure_vote_summary')
    vote_rows = fetch_votes(cursor, filters) if fetch_votes else []
    pack = _all_votes_fund_balance_pack(cursor, filters, vote_rows, helpers)
    analytics = helpers.get('fetch_dashboard_analytics')
    data = analytics(cursor, filters) if analytics else {}
    rev_pos = data.get('revenue_position') or {}
    accounts = data.get('accounts') or {}
    rev_summary_fn = helpers.get('fetch_revenue_summary')
    rev_summary = rev_summary_fn(cursor, filters) if rev_summary_fn else {}
    payroll_fn = helpers.get('fetch_expenditure_books_payroll_lines')
    payroll_rows = payroll_fn(cursor, filters) if payroll_fn else []
    payroll_total = round(sum(float(r.get('_amount') or 0) for r in payroll_rows), 2)
    ap_fn = helpers.get('fetch_expenditure_books_ap_lines')
    ap_lines = ap_fn(cursor, filters) if ap_fn else []
    ap_opening = _ap_opening_balance(ap_lines, filters)
    ap_closing = _ap_closing_balance(ap_lines, filters)
    return {
        'fy_ctx': fy_ctx,
        'vote_rows': vote_rows,
        'pack': pack,
        'rev_pos': rev_pos,
        'rev_summary': rev_summary,
        'accounts': accounts,
        'payroll_rows': payroll_rows,
        'payroll_total': payroll_total,
        'ap_lines': ap_lines,
        'ap_opening': ap_opening,
        'ap_closing': ap_closing,
        'other_income': {
            'government': float(rev_summary.get('government_amount') or 0),
            'private': float(rev_summary.get('private_amount') or 0),
        },
    }


def _ap_opening_balance(ap_lines, filters):
    """Payables balance before the selected period."""
    date_from = (filters.get('date_from') or '').strip()
    opening = 0.0
    for line in sorted(ap_lines, key=_chronological_sort_key):
        d = (line.get('date') or '').strip()
        if date_from and d and d < date_from:
            opening += float(line.get('_invoice') or 0) - float(line.get('_payment') or 0)
    return round(opening, 2)


def _ap_closing_balance(ap_lines, filters):
    """Outstanding payables at period end."""
    opening = _ap_opening_balance(ap_lines, filters)
    running = opening
    for line in sorted(ap_lines, key=_chronological_sort_key):
        if _ap_line_in_period(line, filters):
            running = round(running + float(line.get('_invoice') or 0) - float(line.get('_payment') or 0), 2)
    return running


def _cash_movement_lines(pack, payroll_rows):
    """Chronological cash receipts and payments from vote books and payroll."""
    lines = []
    for r in sorted(pack.get('period_rows') or [], key=_chronological_sort_key):
        amt = float(r.get('amount') or 0)
        if amt <= 0:
            continue
        if r.get('flow') == 'in':
            lines.append({
                '_sort_ts': r.get('_sort_ts', 0),
                'date': r.get('date', '—'),
                'reference': r.get('reference', '—'),
                'particulars': _gl_particulars(r),
                'vote_name': r.get('vote_name', '—'),
                'flow_class': 'receipt',
                'receipt': amt,
                'payment': 0.0,
            })
        elif r.get('flow') == 'out':
            lines.append({
                '_sort_ts': r.get('_sort_ts', 0),
                'date': r.get('date', '—'),
                'reference': r.get('reference', '—'),
                'particulars': _expenditure_particulars(r),
                'vote_name': r.get('vote_name', '—'),
                'flow_class': 'payment',
                'receipt': 0.0,
                'payment': amt,
            })
    for pr in sorted(payroll_rows or [], key=_chronological_sort_key):
        amt = float(pr.get('_amount') or 0)
        if amt <= 0:
            continue
        payee = (pr.get('payee') or '—').strip()
        period = (pr.get('pay_period') or '').strip()
        narr = f'Salary — {payee}'
        if period:
            narr += f' ({period})'
        lines.append({
            '_sort_ts': pr.get('_sort_ts', 0),
            'date': pr.get('date', '—'),
            'reference': pr.get('reference', '—'),
            'particulars': narr,
            'vote_name': '—',
            'flow_class': 'payroll',
            'receipt': 0.0,
            'payment': amt,
        })
    lines.sort(key=_chronological_sort_key)
    return lines


def _build_cash_book_rows(pack, cash_lines, opening_label='Opening balance (brought forward)'):
    """Receipts & payments style cash book with running balance."""
    opening = pack.get('opening_fund', 0.0)
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            particulars=opening_label,
            receipt_display='—',
            payment_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    running = opening
    total_in = total_out = 0.0
    for line in cash_lines:
        receipt = float(line.get('receipt') or 0)
        payment = float(line.get('payment') or 0)
        total_in += receipt
        total_out += payment
        running = round(running + receipt - payment, 2)
        vote = (line.get('vote_name') or '').strip()
        particulars = line.get('particulars', '—')
        if vote and vote != '—' and vote not in particulars:
            particulars = f'{particulars} · {vote}'
        rows.append({
            'date': line.get('date', '—'),
            'reference': line.get('reference', '—'),
            'particulars': particulars,
            'receipt_display': _fmt_kes(receipt) if receipt else '—',
            'payment_display': _fmt_kes(payment) if payment else '—',
            'balance_display': _fmt_kes(running),
        })
    total_in = round(total_in, 2)
    total_out = round(total_out, 2)
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            particulars='Period totals',
            receipt_display=_fmt_kes(total_in),
            payment_display=_fmt_kes(total_out),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            particulars='Closing balance (carried forward)',
            receipt_display='—',
            payment_display='—',
            balance_display=_fmt_kes(running),
        ),
    )
    summary = [
        {'label': 'Opening balance', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'Cash position before period'},
        {'label': 'Total receipts', 'value': f"KES {_fmt_kes(total_in)}", 'hint': 'Collections in period'},
        {'label': 'Total payments', 'value': f"KES {_fmt_kes(total_out)}", 'hint': 'Disbursements in period'},
        {'label': 'Closing balance', 'value': f"KES {_fmt_kes(running)}", 'hint': 'Opening + receipts − payments'},
    ]
    columns = [
        {'key': 'date', 'label': 'Date'},
        {'key': 'reference', 'label': 'Ref'},
        {'key': 'particulars', 'label': 'Particulars'},
        {'key': 'receipt_display', 'label': 'Receipts (KES)', 'align': 'right'},
        {'key': 'payment_display', 'label': 'Payments (KES)', 'align': 'right'},
        {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
    ]
    return rows, summary, columns, ('date', 'reference', 'particulars', 'receipt_display', 'payment_display', 'balance_display')


def _build_income_expenditure_statement(ctx):
    """Income & Expenditure Account — two-column book with accumulated fund."""
    pack = ctx['pack']
    payroll_rows = ctx.get('payroll_rows') or []
    other = ctx.get('other_income') or {}

    income_by_vote = defaultdict(float)
    expense_by_vote = defaultdict(float)
    for r in pack.get('period_rows') or []:
        amt = float(r.get('amount') or 0)
        vote = (r.get('vote_name') or '—').strip()
        if r.get('flow') == 'in':
            income_by_vote[vote] += amt
        elif r.get('flow') == 'out':
            expense_by_vote[vote] += amt

    gov = round(float(other.get('government') or 0), 2)
    private = round(float(other.get('private') or 0), 2)
    total_income = round(sum(income_by_vote.values()) + gov + private, 2)
    payroll_total = round(sum(float(r.get('_amount') or 0) for r in payroll_rows), 2)
    total_expense = round(sum(expense_by_vote.values()) + payroll_total, 2)
    surplus = round(total_income - total_expense, 2)
    opening_fund = pack.get('opening_fund', 0.0)
    closing_fund = round(opening_fund + surplus, 2)

    rows = [
        _ledger_struct_row(
            'opening',
            particulars='Accumulated fund brought forward',
            income_display='—',
            expenditure_display='—',
            fund_display=_fmt_kes(opening_fund),
        ),
        _books_section_row('Income', income_display='—', expenditure_display='—', fund_display='—'),
    ]
    for vote in sorted(income_by_vote.keys(), key=lambda x: x.lower()):
        rows.append({
            'particulars': f'Fee collections — {vote}',
            'income_display': _fmt_kes(income_by_vote[vote]),
            'expenditure_display': '—',
            'fund_display': '—',
        })
    if gov:
        rows.append({
            'particulars': 'Government grants (registered revenue)',
            'income_display': _fmt_kes(gov),
            'expenditure_display': '—',
            'fund_display': '—',
        })
    if private:
        rows.append({
            'particulars': 'Private / other income (registered revenue)',
            'income_display': _fmt_kes(private),
            'expenditure_display': '—',
            'fund_display': '—',
        })
    rows.append(
        _ledger_struct_row(
            'total',
            particulars='Total income',
            income_display=_fmt_kes(total_income),
            expenditure_display='—',
            fund_display='—',
        ),
    )
    rows.append(
        _books_section_row('Expenditure', income_display='—', expenditure_display='—', fund_display='—'),
    )
    for vote in sorted(expense_by_vote.keys(), key=lambda x: x.lower()):
        rows.append({
            'particulars': f'Supplier & store payments — {vote}',
            'income_display': '—',
            'expenditure_display': _fmt_kes(expense_by_vote[vote]),
            'fund_display': '—',
        })
    for pr in sorted(payroll_rows, key=_chronological_sort_key):
        amt = float(pr.get('_amount') or 0)
        if amt <= 0:
            continue
        payee = (pr.get('payee') or '—').strip()
        period = (pr.get('pay_period') or '').strip()
        label = f'Salaries — {payee}'
        if period:
            label += f' · {period}'
        rows.append({
            'particulars': label,
            'income_display': '—',
            'expenditure_display': _fmt_kes(amt),
            'fund_display': '—',
        })
    rows.append(
        _ledger_struct_row(
            'total',
            particulars='Total expenditure',
            income_display='—',
            expenditure_display=_fmt_kes(total_expense),
            fund_display='—',
        ),
    )
    if surplus >= 0:
        rows.append(
            _ledger_struct_row(
                'total',
                particulars='Excess of income over expenditure',
                income_display=_fmt_kes(surplus),
                expenditure_display='—',
                fund_display='—',
            ),
        )
    else:
        deficit = abs(surplus)
        rows.append(
            _ledger_struct_row(
                'total',
                particulars='Excess of expenditure over income',
                income_display='—',
                expenditure_display=_fmt_kes(deficit),
                fund_display='—',
            ),
        )
    rows.append(
        _ledger_struct_row(
            'closing',
            particulars='Accumulated fund carried forward',
            income_display='—',
            expenditure_display='—',
            fund_display=_fmt_kes(closing_fund),
        ),
    )
    summary = [
        {'label': 'Accumulated fund b/f', 'value': f"KES {_fmt_kes(opening_fund)}", 'hint': 'Before selected period'},
        {'label': 'Total income', 'value': f"KES {_fmt_kes(total_income)}", 'hint': 'Collections and registered revenue'},
        {'label': 'Total expenditure', 'value': f"KES {_fmt_kes(total_expense)}", 'hint': 'Suppliers and payroll'},
        {'label': 'Surplus / (deficit)', 'value': f"KES {_fmt_kes(surplus)}", 'hint': 'Income minus expenditure'},
        {'label': 'Accumulated fund c/f', 'value': f"KES {_fmt_kes(closing_fund)}", 'hint': 'Fund carried forward'},
    ]
    columns = [
        {'key': 'particulars', 'label': 'Particulars'},
        {'key': 'income_display', 'label': 'Income (KES)', 'align': 'right'},
        {'key': 'expenditure_display', 'label': 'Expenditure (KES)', 'align': 'right'},
        {'key': 'fund_display', 'label': 'Fund (KES)', 'align': 'right'},
    ]
    return rows, summary, columns, ('particulars', 'income_display', 'expenditure_display', 'fund_display')


def _build_balance_sheet_statement(ctx):
    """Balance Sheet — assets, liabilities and accumulated fund at period end."""
    accounts = ctx['accounts']
    pack = ctx['pack']
    ap_closing = ctx['ap_closing']
    ap_opening = ctx.get('ap_opening', 0.0)

    asset_total = 0.0
    rows = [
        _ledger_struct_row(
            'opening',
            section='—',
            particulars='Balance sheet as at period end',
            amount_display='—',
            side_display='—',
        ),
        _books_section_row('Assets', section='Assets', amount_display='—', side_display='—'),
    ]
    for a in accounts.get('all_accounts') or accounts.get('top_accounts') or []:
        bal = float(a.get('balance') or 0)
        asset_total += bal
        cat = (a.get('account_category') or 'Cash / bank').strip()
        rows.append({
            'section': 'Assets',
            'particulars': f"{a.get('account_name', '—')} ({cat})",
            'amount_display': a.get('balance_display', _fmt_kes(bal)),
            'side_display': 'Dr',
        })
    asset_total = round(asset_total, 2)
    rows.append(
        _ledger_struct_row(
            'total',
            section='Assets',
            particulars='Total assets',
            amount_display=_fmt_kes(asset_total),
            side_display='—',
        ),
    )

    liab_total = round(ap_closing, 2)
    rows.append(_books_section_row('Liabilities', section='Liabilities', amount_display='—', side_display='—'))
    rows.append({
        'section': 'Liabilities',
        'particulars': 'Accounts payable — suppliers (closing)',
        'amount_display': _fmt_kes(liab_total) if liab_total else '0.00',
        'side_display': 'Cr',
    })
    if ap_opening != ap_closing:
        rows.append({
            'section': 'Liabilities',
            'particulars': 'Accounts payable — opening (reference)',
            'amount_display': _fmt_kes(ap_opening),
            'side_display': 'Note',
        })
    rows.append(
        _ledger_struct_row(
            'total',
            section='Liabilities',
            particulars='Total liabilities',
            amount_display=_fmt_kes(liab_total),
            side_display='—',
        ),
    )

    fund_balance = round(asset_total - liab_total, 2)
    pack_fund = round(pack.get('closing_fund', 0.0), 2)
    rows.append(_books_section_row('Accumulated fund', section='Fund', amount_display='—', side_display='—'))
    rows.append({
        'section': 'Fund',
        'particulars': 'Accumulated fund / reserves (Assets − Liabilities)',
        'amount_display': _fmt_kes(fund_balance),
        'side_display': 'Cr',
    })
    rows.append({
        'section': 'Fund',
        'particulars': 'Vote books closing fund (cross-check)',
        'amount_display': _fmt_kes(pack_fund),
        'side_display': 'Note',
    })
    equity_total = round(liab_total + fund_balance, 2)
    rows.append(
        _ledger_struct_row(
            'closing',
            section='—',
            particulars='Total liabilities and accumulated fund',
            amount_display=_fmt_kes(equity_total),
            side_display='—',
        ),
    )
    balanced = abs(asset_total - equity_total) < 0.02
    summary = [
        {'label': 'Total assets', 'value': f"KES {_fmt_kes(asset_total)}", 'hint': 'Finance account balances'},
        {'label': 'Total liabilities', 'value': f"KES {_fmt_kes(liab_total)}", 'hint': 'Outstanding payables'},
        {'label': 'Accumulated fund', 'value': f"KES {_fmt_kes(fund_balance)}", 'hint': 'Balancing fund position'},
        {
            'label': 'Books balanced',
            'value': 'Yes' if balanced else 'Review required',
            'hint': 'Assets = Liabilities + Fund' if balanced else f'Gap KES {_fmt_kes(abs(asset_total - equity_total))}',
        },
    ]
    columns = [
        {'key': 'section', 'label': 'Section'},
        {'key': 'particulars', 'label': 'Particulars'},
        {'key': 'amount_display', 'label': 'Amount (KES)', 'align': 'right'},
        {'key': 'side_display', 'label': 'Dr / Cr', 'align': 'center'},
    ]
    return rows, summary, columns, ('section', 'particulars', 'amount_display', 'side_display')


def _build_receipts_payments_statement(ctx):
    """Receipts & Payments Account — full cash book from vote books."""
    pack = ctx['pack']
    cash_lines = _cash_movement_lines(pack, ctx.get('payroll_rows') or [])
    return _build_cash_book_rows(
        pack,
        cash_lines,
        opening_label='Opening cash balance (brought forward)',
    )


def _build_cash_flow_statement(ctx, cursor, filters, helpers):
    """Cash Flow Statement — operating activities with running cash balance."""
    pack = ctx['pack']
    cash_lines = _cash_movement_lines(pack, ctx.get('payroll_rows') or [])
    opening = pack.get('opening_fund', 0.0)
    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            particulars='Opening cash balance (brought forward)',
            receipt_display='—',
            payment_display='—',
            balance_display=_fmt_kes(opening),
        ),
        _books_section_row(
            'Operating activities',
            date='—',
            reference='—',
            particulars='Operating activities',
            receipt_display='—',
            payment_display='—',
            balance_display='—',
        ),
    ]
    running = opening
    total_in = total_out = 0.0
    receipt_sub = payment_sub = 0.0
    last_class = None
    for line in cash_lines:
        flow_class = line.get('flow_class') or 'payment'
        if last_class == 'receipt' and flow_class != 'receipt' and receipt_sub:
            rows.append(
                _ledger_struct_row(
                    'total',
                    date='—',
                    reference='—',
                    particulars='Subtotal — cash receipts',
                    receipt_display=_fmt_kes(receipt_sub),
                    payment_display='—',
                    balance_display='—',
                ),
            )
            receipt_sub = 0.0
        if last_class in ('payment', 'payroll') and flow_class == 'receipt' and payment_sub:
            rows.append(
                _ledger_struct_row(
                    'total',
                    date='—',
                    reference='—',
                    particulars='Subtotal — cash payments',
                    receipt_display='—',
                    payment_display=_fmt_kes(payment_sub),
                    balance_display='—',
                ),
            )
            payment_sub = 0.0
        if flow_class == 'receipt' and last_class != 'receipt':
            rows.append(
                _books_section_row(
                    'Cash receipts',
                    date='—',
                    reference='—',
                    particulars='Cash receipts from operations',
                    receipt_display='—',
                    payment_display='—',
                    balance_display='—',
                ),
            )
        if flow_class in ('payment', 'payroll') and last_class not in ('payment', 'payroll'):
            rows.append(
                _books_section_row(
                    'Cash payments',
                    date='—',
                    reference='—',
                    particulars='Cash payments for operations',
                    receipt_display='—',
                    payment_display='—',
                    balance_display='—',
                ),
            )
        receipt = float(line.get('receipt') or 0)
        payment = float(line.get('payment') or 0)
        total_in += receipt
        total_out += payment
        if flow_class == 'receipt':
            receipt_sub += receipt
        else:
            payment_sub += payment
        running = round(running + receipt - payment, 2)
        vote = (line.get('vote_name') or '').strip()
        particulars = line.get('particulars', '—')
        if vote and vote != '—' and vote not in particulars:
            particulars = f'{particulars} · {vote}'
        rows.append({
            'date': line.get('date', '—'),
            'reference': line.get('reference', '—'),
            'particulars': particulars,
            'receipt_display': _fmt_kes(receipt) if receipt else '—',
            'payment_display': _fmt_kes(payment) if payment else '—',
            'balance_display': _fmt_kes(running),
        })
        last_class = flow_class
    if receipt_sub:
        rows.append(
            _ledger_struct_row(
                'total',
                date='—',
                reference='—',
                particulars='Subtotal — cash receipts',
                receipt_display=_fmt_kes(receipt_sub),
                payment_display='—',
                balance_display='—',
            ),
        )
    if payment_sub:
        rows.append(
            _ledger_struct_row(
                'total',
                date='—',
                reference='—',
                particulars='Subtotal — cash payments',
                receipt_display='—',
                payment_display=_fmt_kes(payment_sub),
                balance_display='—',
            ),
        )
    total_in = round(total_in, 2)
    total_out = round(total_out, 2)
    net = round(total_in - total_out, 2)
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            particulars='Net cash from operating activities',
            receipt_display=_fmt_kes(total_in),
            payment_display=_fmt_kes(total_out),
            balance_display=_fmt_kes(net),
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            particulars='Closing cash balance (carried forward)',
            receipt_display='—',
            payment_display='—',
            balance_display=_fmt_kes(running),
        ),
    )
    summary = [
        {'label': 'Opening cash', 'value': f"KES {_fmt_kes(opening)}", 'hint': 'Before selected period'},
        {'label': 'Cash inflows', 'value': f"KES {_fmt_kes(total_in)}", 'hint': 'Operating receipts'},
        {'label': 'Cash outflows', 'value': f"KES {_fmt_kes(total_out)}", 'hint': 'Operating payments'},
        {'label': 'Net movement', 'value': f"KES {_fmt_kes(net)}", 'hint': 'Inflows minus outflows'},
        {'label': 'Closing cash', 'value': f"KES {_fmt_kes(running)}", 'hint': 'Opening + net movement'},
    ]
    columns = [
        {'key': 'date', 'label': 'Date'},
        {'key': 'reference', 'label': 'Ref'},
        {'key': 'particulars', 'label': 'Particulars'},
        {'key': 'receipt_display', 'label': 'Inflows (KES)', 'align': 'right'},
        {'key': 'payment_display', 'label': 'Outflows (KES)', 'align': 'right'},
        {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
    ]
    return rows, summary, columns, ('date', 'reference', 'particulars', 'receipt_display', 'payment_display', 'balance_display')


def _report_financial_statements(cursor, filters, helpers):
    fy_fn = helpers.get('fetch_financial_year_context')
    fy_ctx = fy_fn(cursor, filters) if fy_fn else {}
    statement = (filters.get('statement') or '').strip().lower()

    books_ready, books_message = _financial_books_can_be_kept(cursor, filters, helpers)
    if not books_ready:
        payload = _statements_blank_payload(books_message, books_ready=False)
        payload['financial_statement'] = statement
        return payload

    if not statement:
        payload = _statements_blank_payload(
            'Choose a financial statement from the sidebar.',
            books_ready=True,
        )
        payload['financial_statement'] = ''
        return payload

    meta = next((m for m in FINANCIAL_STATEMENTS_NAV if m['slug'] == statement), {})
    title = meta.get('title') or 'Financial statement'
    ctx = _statement_context(cursor, filters, helpers)

    if statement == 'income-and-expenditure':
        rows, stmt_summary, columns, keys = _build_income_expenditure_statement(ctx)
    elif statement == 'balance-sheet':
        rows, stmt_summary, columns, keys = _build_balance_sheet_statement(ctx)
    elif statement == 'receipts-and-payments':
        rows, stmt_summary, columns, keys = _build_receipts_payments_statement(ctx)
    elif statement == 'cash-flow':
        rows, stmt_summary, columns, keys = _build_cash_flow_statement(ctx, cursor, filters, helpers)
    else:
        return _statements_blank_payload('Unknown financial statement.', books_ready=True)

    txn_count = sum(1 for r in rows if not r.get('_ledger_row'))
    fy_cards = _fy_balance_summary_cards(fy_ctx)
    display = _display_ledger_rows(rows, keys)
    return {
        'summary': fy_cards + _summary_cards(stmt_summary),
        'ledger_summary': stmt_summary,
        'table': _table(columns, display),
        'row_count': txn_count,
        'view_mode': 'financial_statement',
        'books_ready': True,
        'books_message': '',
        'financial_statement': statement,
        'table_section_title': title,
    }


def _report_audit_compliance(cursor, filters, helpers):
    fetch_audits = helpers.get('fetch_audit_rows')
    fy_fn = helpers.get('fetch_financial_year_context')
    fy_ctx = fy_fn(cursor, filters) if fy_fn else {}
    rows = fetch_audits(cursor, filters) if fetch_audits else []
    summary = _fy_balance_summary_cards(fy_ctx) + _summary_cards([
        {'label': 'Audit entries', 'value': str(len(rows))},
        {'label': 'Fee payment changes', 'value': str(sum(1 for r in rows if r.get('audit_type') == 'Fee payment'))},
        {'label': 'Expense events', 'value': str(sum(1 for r in rows if r.get('audit_type') == 'Expense'))},
        {'label': 'Salary events', 'value': str(sum(1 for r in rows if r.get('audit_type') == 'Salary'))},
    ])
    columns = [
        {'key': 'date', 'label': 'When'},
        {'key': 'audit_type', 'label': 'Type'},
        {'key': 'action', 'label': 'Action'},
        {'key': 'reference', 'label': 'Reference'},
        {'key': 'subject', 'label': 'Subject'},
        {'key': 'detail', 'label': 'Detail'},
        {'key': 'by', 'label': 'By'},
    ]
    display = [{k: r.get(k, '—') for k in ('date', 'audit_type', 'action', 'reference', 'subject', 'detail', 'by')} for r in rows[:500]]
    return {'summary': summary, 'table': _table(columns, display), 'row_count': len(rows)}


def _report_periodic_summary(cursor, filters, helpers):
    fetch_periods = helpers.get('fetch_periodic_rows')
    fy_fn = helpers.get('fetch_financial_year_context')
    fy_ctx = fy_fn(cursor, filters) if fy_fn else {}
    rows = fetch_periods(cursor, filters) if fetch_periods else []
    total_in = sum(float(r.get('revenue') or 0) for r in rows)
    total_out = sum(float(r.get('expenditure') or 0) for r in rows)
    summary = _fy_balance_summary_cards(fy_ctx) + _summary_cards([
        {'label': 'Periods in view', 'value': str(len(rows))},
        {'label': 'Total collections / revenue', 'value': f'KES {_fmt_kes(total_in)}'},
        {'label': 'Total expenditure', 'value': f'KES {_fmt_kes(total_out)}'},
        {'label': 'Net for periods', 'value': f'KES {_fmt_kes(total_in - total_out)}'},
    ])
    columns = [
        {'key': 'period_label', 'label': 'Period'},
        {'key': 'revenue_display', 'label': 'Revenue / collections', 'align': 'right'},
        {'key': 'expenditure_display', 'label': 'Expenditure', 'align': 'right'},
        {'key': 'net_display', 'label': 'Net', 'align': 'right'},
    ]
    display = [{k: r.get(k, '—') for k in ('period_label', 'revenue_display', 'expenditure_display', 'net_display')} for r in rows]
    return {'summary': summary, 'table': _table(columns, display), 'row_count': len(rows)}
