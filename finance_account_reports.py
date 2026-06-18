"""Per-finance-account accountant reports (ledger, trial balance, etc.)."""

from collections import defaultdict
from datetime import datetime

ACCOUNT_REPORT_NAV = (
    {
        'slug': 'general-ledger',
        'title': 'General Ledger',
        'icon': 'fa-book',
        'description': 'Every debit and credit posted to this account, in date order.',
    },
    {
        'slug': 'trial-balance',
        'title': 'Trial Balance',
        'icon': 'fa-balance-scale',
        'description': 'Opening position, total debits and credits, and closing balance.',
    },
    {
        'slug': 'income-expenditure',
        'title': 'Income & Expenditure',
        'icon': 'fa-chart-line',
        'description': 'Money in (credits) versus money out (debits) for this account.',
    },
    {
        'slug': 'balance-sheet',
        'title': 'Balance Sheet',
        'icon': 'fa-file-invoice-dollar',
        'description': 'Where this account sits on the balance sheet by category.',
    },
    {
        'slug': 'cash-flow',
        'title': 'Cash Flow Statement',
        'icon': 'fa-hand-holding-usd',
        'description': 'Cash in and cash out by month for this account.',
    },
    {
        'slug': 'student-ledger',
        'title': 'Student Ledger',
        'icon': 'fa-user-graduate',
        'description': 'Student fee payments recorded to this account.',
    },
)

ACCOUNT_REPORT_SLUGS = frozenset(item['slug'] for item in ACCOUNT_REPORT_NAV)


def report_meta(slug):
    for item in ACCOUNT_REPORT_NAV:
        if item['slug'] == slug:
            return item
    return {'slug': slug, 'title': slug.replace('-', ' ').title(), 'icon': 'fa-file', 'description': ''}


def _row_val(row, key, idx=0, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    if idx < len(row):
        return row[idx]
    return default


def _fmt_kes(amount):
    try:
        return f'{float(amount):,.2f}'
    except (TypeError, ValueError):
        return '0.00'


def _parse_dates(filters):
    date_from = (filters.get('date_from') or '').strip() or None
    date_to = (filters.get('date_to') or '').strip() or None
    return date_from, date_to


def _ledger_date_clause(date_from, date_to, params):
    parts = []
    if date_from:
        parts.append('DATE(created_at) >= %s')
        params.append(date_from)
    if date_to:
        parts.append('DATE(created_at) <= %s')
        params.append(date_to)
    if not parts:
        return '', params
    return ' AND ' + ' AND '.join(parts), params


def fetch_ledger_rows(cursor, account_id, date_from=None, date_to=None, helpers=None):
    ensure = (helpers or {}).get('ensure_ledger_table')
    if ensure:
        ensure(cursor)
    params = [int(account_id)]
    extra, params = _ledger_date_clause(date_from, date_to, params)
    rows = []
    try:
        cursor.execute(
            f"""
            SELECT id, direction, amount, payment_method, reference_code, description,
                   related_type, balance_after, recorded_by_name, created_at
            FROM finance_account_transactions
            WHERE finance_account_id = %s{extra}
            ORDER BY created_at ASC, id ASC
            LIMIT 3000
            """,
            tuple(params),
        )
        running = 0.0
        for r in cursor.fetchall() or []:
            direction = (_row_val(r, 'direction', 1) or '').strip().lower()
            amt = float(_row_val(r, 'amount', 2) or 0)
            debit = amt if direction == 'debit' else 0.0
            credit = amt if direction == 'credit' else 0.0
            running += credit - debit
            created = _row_val(r, 'created_at', 9)
            period_key = ''
            if created and hasattr(created, 'strftime'):
                dt_display = created.strftime('%d %b %Y')
                period_key = created.strftime('%Y-%m')
            else:
                dt_display = str(created or '—').split(' ')[0]
                period_key = dt_display[:7] if len(dt_display) >= 7 else ''
            bal_after = _row_val(r, 'balance_after', 8)
            rows.append({
                'date': dt_display,
                'reference': (_row_val(r, 'reference_code', 4) or '—').strip() or '—',
                'description': (_row_val(r, 'description', 5) or '—').strip() or '—',
                'debit_display': _fmt_kes(debit) if debit else '—',
                'credit_display': _fmt_kes(credit) if credit else '—',
                'balance_display': _fmt_kes(bal_after if bal_after is not None else running),
                'recorded_by': (_row_val(r, 'recorded_by_name', 9) or '—').strip() or '—',
                'debit': debit,
                'credit': credit,
                'period_key': period_key,
                'related_type': (_row_val(r, 'related_type', 6) or '').strip().lower(),
                'related_id': _row_val(r, 'related_id', 7),
            })
    except Exception as e:
        print(f'fetch_ledger_rows: {e}')
    return rows


def fetch_account_report_payload(cursor, account_id, report_slug, filters, helpers):
    """Build view model for one account report."""
    slug = (report_slug or '').strip().lower()
    if slug not in ACCOUNT_REPORT_SLUGS:
        return {'error': 'Unknown report'}

    load_account = helpers.get('load_account')
    account = helpers.get('preloaded_account')
    if not account and load_account:
        account = load_account(cursor, account_id)
    if not account:
        return {'error': 'Account not found'}

    date_from, date_to = _parse_dates(filters)
    refresh = helpers.get('refresh_balances')
    if refresh:
        try:
            refresh(cursor, account_id)
        except TypeError:
            try:
                refresh(cursor)
            except Exception as e:
                print(f'fetch_account_report_payload refresh: {e}')
        except Exception as e:
            print(f'fetch_account_report_payload refresh: {e}')
        try:
            cursor.execute(
                """
                SELECT COALESCE(current_balance, 0) AS bal
                FROM finance_accounts WHERE id = %s LIMIT 1
                """,
                (int(account_id),),
            )
            br = cursor.fetchone()
            if br:
                bal = float(
                    _row_val(br, 'bal', 0, 0) or 0
                )
                account['current_balance'] = bal
        except Exception as e:
            print(f'fetch_account_report_payload balance reload: {e}')

    fy_fn = helpers.get('fetch_financial_year_context')
    fy_ctx = fy_fn(cursor, filters) if fy_fn else {}
    balance_before = helpers.get('account_balance_before')
    balance_through = helpers.get('account_balance_through')

    if date_from and balance_before:
        opening = float(balance_before(cursor, account_id, date_from))
    else:
        opening = float(account.get('current_balance') or 0)

    ledger = fetch_ledger_rows(cursor, account_id, date_from, date_to, helpers)
    total_debit = sum(r['debit'] for r in ledger)
    total_credit = sum(r['credit'] for r in ledger)
    period_net = total_credit - total_debit

    if date_from or date_to:
        closing = round(opening + period_net, 2)
    elif balance_through and date_to:
        closing = float(balance_through(cursor, account_id, date_to))
    else:
        closing = float(account.get('current_balance') or 0)

    fy_summary = []
    if fy_ctx.get('is_configured'):
        fy_label = fy_ctx.get('year_label') or 'FY'
        fy_summary = [
            {
                'label': f'School opening ({fy_label})',
                'value': f"KES {_fmt_kes(fy_ctx.get('opening_balance', 0))}",
            },
            {
                'label': f'School closing ({fy_label})',
                'value': f"KES {_fmt_kes(fy_ctx.get('closing_balance', 0))}",
            },
        ]

    if slug == 'general-ledger':
        return {
            'report_type': slug,
            'summary': fy_summary + [
                {'label': 'Account opening', 'value': f'KES {_fmt_kes(opening)}'},
                {'label': 'Transactions', 'value': str(len(ledger))},
                {'label': 'Total debits', 'value': f'KES {_fmt_kes(total_debit)}'},
                {'label': 'Total credits', 'value': f'KES {_fmt_kes(total_credit)}'},
                {'label': 'Account closing', 'value': f'KES {_fmt_kes(closing)}'},
            ],
            'columns': [
                {'key': 'date', 'label': 'Date'},
                {'key': 'reference', 'label': 'Reference'},
                {'key': 'description', 'label': 'Description'},
                {'key': 'debit_display', 'label': 'Debit (KES)', 'align': 'right'},
                {'key': 'credit_display', 'label': 'Credit (KES)', 'align': 'right'},
                {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
            ],
            'rows': ledger,
        }

    if slug == 'trial-balance':
        return {
            'report_type': slug,
            'summary': fy_summary + [
                {'label': 'Account opening', 'value': f'KES {_fmt_kes(opening)}'},
                {'label': 'Total debits', 'value': f'KES {_fmt_kes(total_debit)}'},
                {'label': 'Total credits', 'value': f'KES {_fmt_kes(total_credit)}'},
                {'label': 'Account closing', 'value': f'KES {_fmt_kes(closing)}'},
            ],
            'trial_lines': [
                {'label': 'Opening balance', 'debit': '', 'credit': '', 'balance': _fmt_kes(opening)},
                {'label': 'Period debits', 'debit': _fmt_kes(total_debit), 'credit': '', 'balance': ''},
                {'label': 'Period credits', 'debit': '', 'credit': _fmt_kes(total_credit), 'balance': ''},
                {'label': 'Closing balance', 'debit': '', 'credit': '', 'balance': _fmt_kes(closing)},
            ],
            'rows': [],
        }

    if slug == 'income-expenditure':
        income_rows = [r for r in ledger if r['credit'] > 0]
        expense_rows = [r for r in ledger if r['debit'] > 0]
        return {
            'report_type': slug,
            'summary': fy_summary + [
                {'label': 'Total income (credits)', 'value': f'KES {_fmt_kes(total_credit)}'},
                {'label': 'Total expenditure (debits)', 'value': f'KES {_fmt_kes(total_debit)}'},
                {'label': 'Surplus / (deficit)', 'value': f'KES {_fmt_kes(period_net)}'},
            ],
            'income_rows': income_rows,
            'expense_rows': expense_rows,
        }

    if slug == 'balance-sheet':
        cat = (account.get('account_category') or 'Other').strip()
        cat_lower = cat.lower()
        if cat_lower in ('income',):
            section = 'Income / revenue'
        elif cat_lower in ('asset', 'assets', 'bank', 'cash', 'petty cash'):
            section = 'Assets'
        elif cat_lower in ('liability', 'liabilities'):
            section = 'Liabilities'
        else:
            section = 'Equity & other'
        return {
            'report_type': slug,
            'summary': fy_summary + [
                {'label': 'Account', 'value': account.get('account_name') or '—'},
                {'label': 'Category', 'value': cat},
                {'label': 'Balance', 'value': f'KES {_fmt_kes(closing)}'},
            ],
            'balance_sheet_lines': [
                {'section': section, 'name': account.get('account_name'), 'amount_display': _fmt_kes(closing)},
            ],
            'rows': [],
        }

    if slug == 'cash-flow':
        by_month = defaultdict(lambda: {'in': 0.0, 'out': 0.0})
        for r in ledger:
            month_key = r.get('period_key') or 'Unknown'
            by_month[month_key]['in'] += r['credit']
            by_month[month_key]['out'] += r['debit']
        cf_rows = []
        for mk in sorted(by_month.keys()):
            inn = by_month[mk]['in']
            out = by_month[mk]['out']
            label = mk
            if len(mk) == 7 and mk[4] == '-':
                try:
                    label = datetime.strptime(mk + '-01', '%Y-%m-%d').strftime('%b %Y')
                except ValueError:
                    label = mk
            cf_rows.append({
                'period': label,
                'cash_in_display': _fmt_kes(inn),
                'cash_out_display': _fmt_kes(out),
                'net_display': _fmt_kes(inn - out),
            })
        return {
            'report_type': slug,
            'summary': [
                {'label': 'Cash in', 'value': f'KES {_fmt_kes(total_credit)}'},
                {'label': 'Cash out', 'value': f'KES {_fmt_kes(total_debit)}'},
                {'label': 'Net cash flow', 'value': f'KES {_fmt_kes(total_credit - total_debit)}'},
            ],
            'columns': [
                {'key': 'period', 'label': 'Period'},
                {'key': 'cash_in_display', 'label': 'Cash in (KES)', 'align': 'right'},
                {'key': 'cash_out_display', 'label': 'Cash out (KES)', 'align': 'right'},
                {'key': 'net_display', 'label': 'Net (KES)', 'align': 'right'},
            ],
            'rows': cf_rows,
        }

    if slug == 'student-ledger':
        load_fees = helpers.get('load_student_fee_rows')
        fee_rows = load_fees(cursor, account_id) if load_fees else []
        fee_total = 0.0
        display = []
        for r in fee_rows:
            amt = float(r.get('amount') or r.get('amount_paid') or 0)
            fee_total += amt
            display.append({
                'date': r.get('created_at_display', '—'),
                'reference': r.get('reference_number', '—'),
                'student': r.get('name', '—'),
                'fee_name': r.get('fee_name', '—'),
                'amount_display': r.get('amount_display', _fmt_kes(amt)),
            })
        return {
            'report_type': slug,
            'summary': [
                {'label': 'Payments', 'value': str(len(display))},
                {'label': 'Total fees received', 'value': f'KES {_fmt_kes(fee_total)}'},
            ],
            'columns': [
                {'key': 'date', 'label': 'Date'},
                {'key': 'student', 'label': 'Student'},
                {'key': 'fee_name', 'label': 'Fee'},
                {'key': 'reference', 'label': 'Reference'},
                {'key': 'amount_display', 'label': 'Amount (KES)', 'align': 'right'},
            ],
            'rows': display,
        }

    return {'error': 'Unknown report'}


def fetch_petty_cash_book_payload(cursor, account_id, filters, helpers):
    """Petty cash book — receipts and payments with running balance."""
    load_account = helpers.get('load_account')
    account = helpers.get('preloaded_account')
    if not account and load_account:
        account = load_account(cursor, account_id)
    if not account:
        return {'error': 'Account not found'}

    cat = (account.get('account_category') or '').strip().lower()
    if cat != 'petty cash':
        return {'error': 'Not a petty cash account'}

    date_from, date_to = _parse_dates(filters)
    refresh = helpers.get('refresh_balances')
    if refresh:
        try:
            refresh(cursor, account_id)
        except TypeError:
            try:
                refresh(cursor)
            except Exception as e:
                print(f'fetch_petty_cash_book_payload refresh: {e}')
        except Exception as e:
            print(f'fetch_petty_cash_book_payload refresh: {e}')

    balance_before = helpers.get('account_balance_before')
    if date_from and balance_before:
        opening = float(balance_before(cursor, account_id, date_from))
    else:
        opening = 0.0

    ledger = fetch_ledger_rows(cursor, account_id, date_from, date_to, helpers)
    expense_particulars = {}
    load_expenses = helpers.get('load_petty_cash_expense_particulars')
    if load_expenses:
        try:
            expense_particulars = load_expenses(cursor, account_id) or {}
        except Exception as e:
            print(f'fetch_petty_cash_book_payload expense particulars: {e}')

    rows = []
    running = opening
    total_receipt = total_payment = 0.0
    transaction_rows = []
    for r in ledger:
        receipt = float(r.get('credit') or 0)
        payment = float(r.get('debit') or 0)
        total_receipt += receipt
        total_payment += payment
        running = round(running + receipt - payment, 2)
        particulars = r.get('description', '—')
        exp_id = r.get('related_id')
        if r.get('related_type') == 'petty_cash_expense' and exp_id:
            exp = expense_particulars.get(int(exp_id))
            if exp:
                particulars = exp.get('particulars') or particulars
        transaction_rows.append({
            'date': r.get('date', '—'),
            'reference': r.get('reference', '—'),
            'particulars': particulars,
            'receipt_display': r.get('credit_display', '—'),
            'payment_display': r.get('debit_display', '—'),
            'balance_display': _fmt_kes(running),
            'recorded_by': r.get('recorded_by', '—'),
        })
    total_receipt = round(total_receipt, 2)
    total_payment = round(total_payment, 2)
    closing = round(opening + total_receipt - total_payment, 2)

    transaction_rows.reverse()
    rows.extend(transaction_rows)
    rows.append({
        'date': '—',
        'reference': '—',
        'particulars': 'Opening balance (brought forward)',
        'receipt_display': '—',
        'payment_display': '—',
        'balance_display': _fmt_kes(opening),
        '_ledger_row': 'opening',
    })
    rows.append({
        'date': '—',
        'reference': '—',
        'particulars': 'Period totals',
        'receipt_display': _fmt_kes(total_receipt),
        'payment_display': _fmt_kes(total_payment),
        'balance_display': '—',
        '_ledger_row': 'total',
    })
    rows.append({
        'date': '—',
        'reference': '—',
        'particulars': 'Closing balance (carried forward)',
        'receipt_display': '—',
        'payment_display': '—',
        'balance_display': _fmt_kes(closing),
        '_ledger_row': 'closing',
    })

    return {
        'report_type': 'petty-cash-book',
        'summary': [
            {'label': 'Opening balance', 'value': f'KES {_fmt_kes(opening)}'},
            {'label': 'Total receipts', 'value': f'KES {_fmt_kes(total_receipt)}'},
            {'label': 'Total payments', 'value': f'KES {_fmt_kes(total_payment)}'},
            {'label': 'Closing balance', 'value': f'KES {_fmt_kes(closing)}'},
        ],
        'columns': [
            {'key': 'date', 'label': 'Date'},
            {'key': 'reference', 'label': 'Reference'},
            {'key': 'particulars', 'label': 'Particulars'},
            {'key': 'receipt_display', 'label': 'Receipt (KES)', 'align': 'right'},
            {'key': 'payment_display', 'label': 'Payment (KES)', 'align': 'right'},
            {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
        ],
        'rows': rows,
        'transaction_count': len(ledger),
    }


def petty_cash_book_empty_payload():
    """Placeholder book layout when no petty cash account exists yet."""
    return {
        'report_type': 'petty-cash-book',
        'summary': [
            {'label': 'Opening balance', 'value': 'KES 0.00'},
            {'label': 'Total receipts', 'value': 'KES 0.00'},
            {'label': 'Total payments', 'value': 'KES 0.00'},
            {'label': 'Closing balance', 'value': 'KES 0.00'},
        ],
        'columns': [
            {'key': 'date', 'label': 'Date'},
            {'key': 'reference', 'label': 'Reference'},
            {'key': 'particulars', 'label': 'Particulars'},
            {'key': 'receipt_display', 'label': 'Receipt (KES)', 'align': 'right'},
            {'key': 'payment_display', 'label': 'Payment (KES)', 'align': 'right'},
            {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
        ],
        'rows': [],
        'transaction_count': 0,
        'empty_state': True,
    }
