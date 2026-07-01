"""Per-finance-account accountant reports (ledger, trial balance, etc.)."""

from collections import defaultdict
from datetime import datetime, timedelta

ACCOUNT_REPORT_NAV = (
    {
        'slug': 'general-ledger',
        'title': 'General Ledger',
        'icon': 'fa-book',
        'description': 'Each expense vote has its own ledger with opening balance, movements, and closing balance.',
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
    {
        'slug': 'cash-book',
        'title': 'Cash Book',
        'icon': 'fa-cash-register',
        'description': 'Receipts and payments by cash or bank, with vote allocation in priority order.',
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


def _is_cash_payment_method(method):
    """True when payment is physical cash (not bank, M-Pesa, cheque, etc.)."""
    m = (method or '').strip().lower()
    return m in ('cash', 'petty cash')


def _vote_column_key(vote_name):
    """Stable column key for a vote label."""
    slug = ''.join(
        ch if ch.isalnum() else '_'
        for ch in (vote_name or '').strip().upper()
    ).strip('_')
    return f'vote_{slug or "UNASSIGNED"}'


def _allocate_amount_by_vote_priority(amount, vote_order, outstanding_by_vote):
    """Waterfall allocation — first vote to last, not equal split."""
    remaining = round(float(amount or 0), 2)
    result = {vote: 0.0 for vote in (vote_order or [])}
    if remaining <= 0 or not vote_order:
        return result
    for vote in vote_order:
        if remaining <= 0:
            break
        owed = round(float(outstanding_by_vote.get(vote, 0) or 0), 2)
        if owed <= 0:
            continue
        take = min(remaining, owed)
        result[vote] = round(take, 2)
        remaining = round(remaining - take, 2)
    if remaining > 0:
        anchor = vote_order[0]
        result[anchor] = round(result.get(anchor, 0.0) + remaining, 2)
    return result


def _norm_cash_book_vote_key(name):
    return (name or '').strip().upper()


def _collect_cash_book_vote_meta(cursor, account_id, helpers, ledger_rows=None):
    """Registered votes with display names in priority order (first to last)."""
    by_key = {}
    order = []

    def _add(name, description=''):
        key = _norm_cash_book_vote_key(name)
        if not key or key == '—':
            return
        display = (name or '').strip() or key
        desc = (description or '').strip()
        if key not in by_key:
            by_key[key] = {'key': key, 'name': display, 'description': desc}
            order.append(key)
        else:
            if display and by_key[key]['name'] in (key, by_key[key]['key']):
                by_key[key]['name'] = display
            if desc and not by_key[key]['description']:
                by_key[key]['description'] = desc

    desc_map = {}
    load_desc = helpers.get('load_expense_vote_descriptions')
    if load_desc:
        try:
            desc_map = load_desc(cursor) or {}
        except Exception as e:
            print(f'_collect_cash_book_vote_meta descriptions: {e}')

    load_votes = helpers.get('load_account_expense_votes')
    if load_votes:
        try:
            for name in load_votes(cursor, account_id) or []:
                key = _norm_cash_book_vote_key(name)
                _add(name, desc_map.get(key, ''))
        except Exception as e:
            print(f'_collect_cash_book_vote_meta registered: {e}')

    load_meta = helpers.get('load_account_fee_votes_meta')
    if load_meta:
        try:
            for item in load_meta(cursor, account_id) or []:
                if isinstance(item, dict):
                    _add(item.get('name') or item.get('key'), item.get('description'))
                else:
                    _add(item)
        except Exception as e:
            print(f'_collect_cash_book_vote_meta fee items: {e}')

    for entry in ledger_rows or []:
        vote_label = (entry.get('vote_name') or '').strip()
        if not vote_label or vote_label == '—':
            continue
        for part in vote_label.split(','):
            part = part.strip()
            if part:
                _add(part, desc_map.get(_norm_cash_book_vote_key(part), ''))

    if not order:
        return [{'key': '—', 'name': '—', 'description': ''}]
    return [by_key[k] for k in order]


def _collect_cash_book_votes(cursor, account_id, helpers, ledger_rows=None):
    """Vote keys for allocation (uppercase)."""
    return [v['key'] for v in _collect_cash_book_vote_meta(
        cursor, account_id, helpers, ledger_rows,
    )]


def _cash_book_vote_order(votes):
    return [v for v in (votes or []) if v and v != '—']


def _build_cash_book_columns(vote_meta):
    columns = [
        {'key': 'date', 'label': 'Date'},
        {'key': 'particular', 'label': 'Particular'},
        {'key': 'reference', 'label': 'Reference'},
        {'key': 'cash_display', 'label': 'Cash (KES)', 'align': 'right'},
        {'key': 'bank_display', 'label': 'Bank (KES)', 'align': 'right'},
        {'key': 'total_display', 'label': 'Total (KES)', 'align': 'right'},
    ]
    for vote in vote_meta or []:
        key = vote.get('key') or '—'
        columns.append({
            'key': _vote_column_key(key),
            'label': vote.get('name') or key,
            'description': vote.get('description') or '',
            'align': 'right',
            'vote_name': key,
        })
    return columns


def _cash_book_row_vote_cells(vote_alloc, votes):
    cells = {}
    for vote in votes:
        amt = float(vote_alloc.get(vote, 0) or 0)
        key = _vote_column_key(vote)
        cells[key] = _fmt_kes(amt) if amt else '—'
    return cells


def _map_vote_allocation_to_columns(vote_alloc, votes):
    """Map allocation dict onto the cash book column vote list."""
    out = {vote: 0.0 for vote in votes}
    for vote, share in (vote_alloc or {}).items():
        key = (vote or '').strip().upper()
        if key in out:
            out[key] = round(float(share or 0), 2)
    return out


def _cash_book_allocate_entry(cursor, entry, votes, helpers, student_paid_state, account_id):
    """Return {vote_name: amount} for one ledger line."""
    amount = round(
        float(entry.get('credit') or 0) + float(entry.get('debit') or 0),
        2,
    )
    if amount <= 0:
        return {vote: 0.0 for vote in votes}

    related_type = (entry.get('related_type') or '').strip().lower()
    related_id = entry.get('related_id')
    direction = 'credit' if float(entry.get('credit') or 0) > 0 else 'debit'

    if direction == 'debit':
        vote = (entry.get('vote_name') or '').strip().upper()
        if vote and vote != '—' and vote in votes:
            return {v: (amount if v == vote else 0.0) for v in votes}
        if votes:
            return {v: (amount if v == votes[0] else 0.0) for v in votes}
        return {}

    if related_type == 'student_payment' and related_id is not None:
        loader = helpers.get('load_student_payment_vote_context')
        vote_order = _cash_book_vote_order(votes)
        if loader:
            try:
                ctx = loader(cursor, int(related_id), account_id, votes) or {}
            except Exception as e:
                print(f'_cash_book_allocate_entry student_payment: {e}')
                ctx = {}
            if ctx:
                student_id = ctx.get('student_id')
                fee_structure_id = ctx.get('fee_structure_id')
                vote_order = ctx.get('vote_order') or vote_order
                expected = ctx.get('expected') or {}
                state_key = (student_id, fee_structure_id)
                paid_map = student_paid_state.setdefault(state_key, defaultdict(float))
                outstanding = {
                    vote: max(
                        0.0,
                        round(
                            float(expected.get(vote, 0) or 0) - float(paid_map.get(vote, 0) or 0),
                            2,
                        ),
                    )
                    for vote in vote_order
                }
                alloc = _allocate_amount_by_vote_priority(amount, vote_order, outstanding)
                for vote, share in alloc.items():
                    paid_map[vote] = round(float(paid_map.get(vote, 0) or 0) + float(share or 0), 2)
                return _map_vote_allocation_to_columns(alloc, votes)
        if vote_order:
            alloc = _allocate_amount_by_vote_priority(
                amount,
                vote_order,
                {vote: amount for vote in vote_order},
            )
            return _map_vote_allocation_to_columns(alloc, votes)

    vote = (entry.get('vote_name') or '').strip().upper()
    if vote and vote != '—':
        for part in vote.split(','):
            part = part.strip()
            if part in votes:
                return {v: (amount if v == part else 0.0) for v in votes}
    vote_order = _cash_book_vote_order(votes)
    if vote_order:
        alloc = _allocate_amount_by_vote_priority(
            amount,
            vote_order,
            {vote: amount for vote in vote_order},
        )
        return _map_vote_allocation_to_columns(alloc, votes)
    return {}


def _build_account_cash_book_rows(cursor, account_id, ledger, votes, helpers, student_paid_state=None):
    """Cash book lines with cash/bank split and per-vote columns."""
    student_paid_state = student_paid_state if student_paid_state is not None else {}
    rows = []
    totals = {
        'cash': 0.0,
        'bank': 0.0,
        'total': 0.0,
        'votes': defaultdict(float),
    }

    for entry in ledger or []:
        credit = float(entry.get('credit') or 0)
        debit = float(entry.get('debit') or 0)
        amount = round(credit + debit, 2)
        if amount <= 0:
            continue

        method = entry.get('payment_method') or ''
        is_cash = _is_cash_payment_method(method)
        cash_amt = amount if is_cash else 0.0
        bank_amt = amount if not is_cash else 0.0

        vote_alloc = _cash_book_allocate_entry(
            cursor, entry, votes, helpers, student_paid_state, account_id,
        )
        row = {
            'date': entry.get('date', '—'),
            'particular': entry.get('description', '—'),
            'reference': entry.get('reference', '—'),
            'cash_display': _fmt_kes(cash_amt) if cash_amt else '—',
            'bank_display': _fmt_kes(bank_amt) if bank_amt else '—',
            'total_display': _fmt_kes(amount),
        }
        row.update(_cash_book_row_vote_cells(vote_alloc, votes))
        rows.append(row)

        totals['cash'] = round(totals['cash'] + cash_amt, 2)
        totals['bank'] = round(totals['bank'] + bank_amt, 2)
        totals['total'] = round(totals['total'] + amount, 2)
        for vote in votes:
            totals['votes'][vote] = round(
                totals['votes'][vote] + float(vote_alloc.get(vote, 0) or 0),
                2,
            )

    total_row = {
        'date': '—',
        'particular': 'Period totals',
        'reference': '—',
        'cash_display': _fmt_kes(totals['cash']),
        'bank_display': _fmt_kes(totals['bank']),
        'total_display': _fmt_kes(totals['total']),
        '_ledger_row': 'total',
    }
    total_row.update(_cash_book_row_vote_cells(totals['votes'], votes))
    if rows:
        rows.append(total_row)

    return rows, totals


def _parse_dates(filters):
    date_from = (filters.get('date_from') or '').strip() or None
    date_to = (filters.get('date_to') or '').strip() or None
    return date_from, date_to


def _row_date_iso(row):
    """Best-effort YYYY-MM-DD from a revenue/ledger row."""
    created = row.get('created_at')
    if created and hasattr(created, 'strftime'):
        return created.strftime('%Y-%m-%d')
    display = (row.get('created_at_display') or row.get('date') or '').strip()
    if not display or display == '—':
        return ''
    if len(display) >= 10 and display[4] == '-':
        return display[:10]
    for fmt, max_len in (
        ('%d %b %Y, %H:%M', 20),
        ('%d %b %Y', 11),
        ('%Y-%m-%d', 10),
    ):
        try:
            return datetime.strptime(display[:max_len], fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return ''


def _row_in_period(row, date_from, date_to):
    if not date_from and not date_to:
        return True
    iso = _row_date_iso(row)
    if not iso:
        return True
    if date_from and iso < date_from:
        return False
    if date_to and iso > date_to:
        return False
    return True


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


def _ledger_struct_row(kind, **fields):
    row = dict(fields)
    row['_ledger_row'] = kind
    return row


def _enrich_ledger_with_votes(cursor, account_id, rows, helpers):
    """Resolve and attach vote_name on each ledger row."""
    vote_map_fn = helpers.get('ledger_vote_map')
    if not vote_map_fn:
        _apply_ledger_vote_names(rows, {})
        return
    try:
        vote_map = vote_map_fn(cursor, account_id, rows) or {}
    except Exception as e:
        print(f'_enrich_ledger_with_votes: {e}')
        vote_map = {}
    _apply_ledger_vote_names(rows, vote_map)


def _day_before_iso(date_iso):
    if not date_iso:
        return None
    try:
        d = datetime.strptime(str(date_iso).strip()[:10], '%Y-%m-%d').date()
        return (d - timedelta(days=1)).isoformat()
    except ValueError:
        return None


def _fetch_prior_ledger_rows(cursor, account_id, before_date, helpers):
    """Ledger lines strictly before before_date (for per-vote opening balances)."""
    end = _day_before_iso(before_date)
    if not end:
        return []
    rows = fetch_ledger_rows(cursor, account_id, None, end, helpers, opening_balance=0.0)
    _enrich_ledger_with_votes(cursor, account_id, rows, helpers)
    return rows


def _aggregate_ledger_by_vote(rows):
    """Sum debits and credits per vote from ledger transaction rows."""
    buckets = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0})
    for row in rows or []:
        vote = (row.get('vote_name') or '—').strip() or '—'
        buckets[vote]['debit'] += float(row.get('debit') or 0)
        buckets[vote]['credit'] += float(row.get('credit') or 0)
    for vote in buckets:
        buckets[vote]['debit'] = round(buckets[vote]['debit'], 2)
        buckets[vote]['credit'] = round(buckets[vote]['credit'], 2)
    return buckets


def _vote_net_balance(debit, credit):
    return round(float(credit or 0) - float(debit or 0), 2)


def _build_account_trial_balance_by_vote(
    prior_rows, period_rows, account_opening, total_debit, total_credit, closing,
):
    """Trial balance lines — one row per vote plus account total."""
    prior = _aggregate_ledger_by_vote(prior_rows)
    period = _aggregate_ledger_by_vote(period_rows)
    all_votes = sorted(
        set(prior.keys()) | set(period.keys()),
        key=lambda v: (v == '—', v),
    )

    trial_lines = []
    for vote in all_votes:
        prior_amt = prior.get(vote, {'debit': 0.0, 'credit': 0.0})
        period_amt = period.get(vote, {'debit': 0.0, 'credit': 0.0})
        opening_bal = _vote_net_balance(prior_amt['debit'], prior_amt['credit'])
        period_debit = period_amt['debit']
        period_credit = period_amt['credit']
        closing_bal = round(opening_bal + period_credit - period_debit, 2)
        trial_lines.append({
            'label': vote,
            'vote_name': vote,
            'opening': _fmt_kes(opening_bal),
            'debit': _fmt_kes(period_debit) if period_debit else '—',
            'credit': _fmt_kes(period_credit) if period_credit else '—',
            'balance': _fmt_kes(closing_bal),
        })

    if not trial_lines:
        trial_lines.append({
            'label': '—',
            'vote_name': '—',
            'opening': _fmt_kes(account_opening),
            'debit': '—',
            'credit': '—',
            'balance': _fmt_kes(closing),
        })

    trial_lines.append({
        'label': 'Total',
        'vote_name': 'Total',
        '_ledger_row': 'total',
        'opening': _fmt_kes(account_opening),
        'debit': _fmt_kes(total_debit),
        'credit': _fmt_kes(total_credit),
        'balance': _fmt_kes(closing),
    })
    return trial_lines


ACCOUNT_GENERAL_LEDGER_COLUMNS = (
    {'key': 'date', 'label': 'Date'},
    {'key': 'reference', 'label': 'Reference'},
    {'key': 'description', 'label': 'Description'},
    {'key': 'debit_display', 'label': 'Debit (KES)', 'align': 'right'},
    {'key': 'credit_display', 'label': 'Credit (KES)', 'align': 'right'},
    {'key': 'balance_display', 'label': 'Balance (KES)', 'align': 'right'},
)


def _group_ledger_by_vote(rows):
    """Group ledger transaction rows by vote name."""
    grouped = defaultdict(list)
    for row in rows or []:
        vote = (row.get('vote_name') or '—').strip() or '—'
        grouped[vote].append(row)
    return grouped


def _collect_vote_names(prior_rows, period_rows, linked_votes=None):
    """All vote keys for this account — linked votes plus any with ledger activity."""
    votes = set(_group_ledger_by_vote(prior_rows).keys())
    votes |= set(_group_ledger_by_vote(period_rows).keys())
    for name in linked_votes or []:
        vote = (name or '').strip().upper()
        if vote:
            votes.add(vote)
    if not votes:
        votes.add('—')
    return sorted(votes, key=lambda v: (v == '—', v))


def _build_vote_general_ledger_section(vote_name, prior_txns, period_txns):
    """One vote's ledger — own opening, running balance, period totals, and closing."""
    opening = _vote_net_balance(
        sum(float(r.get('debit') or 0) for r in prior_txns),
        sum(float(r.get('credit') or 0) for r in prior_txns),
    )
    total_debit = round(sum(float(r.get('debit') or 0) for r in period_txns), 2)
    total_credit = round(sum(float(r.get('credit') or 0) for r in period_txns), 2)
    closing = round(opening + total_credit - total_debit, 2)

    running = opening
    txn_rows = []
    for row in period_txns:
        running = round(
            running + float(row.get('credit') or 0) - float(row.get('debit') or 0),
            2,
        )
        txn_rows.append({
            'date': row.get('date', '—'),
            'reference': row.get('reference', '—'),
            'description': row.get('description', '—'),
            'debit_display': row.get('debit_display', '—'),
            'credit_display': row.get('credit_display', '—'),
            'balance_display': _fmt_kes(running),
        })

    rows = [
        _ledger_struct_row(
            'opening',
            date='—',
            reference='—',
            description='Opening balance (brought forward)',
            debit_display='—',
            credit_display='—',
            balance_display=_fmt_kes(opening),
        ),
    ]
    rows.extend(txn_rows)
    rows.append(
        _ledger_struct_row(
            'total',
            date='—',
            reference='—',
            description='Period totals',
            debit_display=_fmt_kes(total_debit),
            credit_display=_fmt_kes(total_credit),
            balance_display='—',
        ),
    )
    rows.append(
        _ledger_struct_row(
            'closing',
            date='—',
            reference='—',
            description='Closing balance (carried forward)',
            debit_display='—',
            credit_display='—',
            balance_display=_fmt_kes(closing),
        ),
    )
    return {
        'vote_name': vote_name,
        'opening': opening,
        'closing': closing,
        'opening_display': _fmt_kes(opening),
        'closing_display': _fmt_kes(closing),
        'total_debit': total_debit,
        'total_credit': total_credit,
        'summary': _period_ledger_summary(opening, total_debit, total_credit, closing),
        'columns': list(ACCOUNT_GENERAL_LEDGER_COLUMNS),
        'rows': rows,
        'transaction_count': len(period_txns),
    }


def _build_per_vote_general_ledgers(prior_rows, period_rows, linked_votes=None):
    """Separate general ledger section per vote (each vote is its own sub-account)."""
    prior_by = _group_ledger_by_vote(prior_rows)
    period_by = _group_ledger_by_vote(period_rows)
    sections = []
    for vote in _collect_vote_names(prior_rows, period_rows, linked_votes):
        sections.append(_build_vote_general_ledger_section(
            vote,
            prior_by.get(vote, []),
            period_by.get(vote, []),
        ))
    return sections


def _resolve_account_period(cursor, account_id, date_from, date_to, account, helpers):
    """Opening/closing balances and ledger lines for the selected date range."""
    balance_before = helpers.get('account_balance_before')
    balance_through = helpers.get('account_balance_through')
    has_period = bool(date_from or date_to)

    if date_from and balance_before:
        opening = float(balance_before(cursor, account_id, date_from))
    else:
        opening = 0.0

    ledger = fetch_ledger_rows(
        cursor, account_id, date_from, date_to, helpers, opening_balance=0.0,
    )
    _enrich_ledger_with_votes(cursor, account_id, ledger, helpers)
    total_debit = round(sum(r['debit'] for r in ledger), 2)
    total_credit = round(sum(r['credit'] for r in ledger), 2)
    period_net = round(total_credit - total_debit, 2)

    if date_to and balance_through:
        closing = float(balance_through(cursor, account_id, date_to))
    elif has_period:
        closing = round(opening + period_net, 2)
    else:
        closing = float(account.get('current_balance') or 0)

    return {
        'opening': opening,
        'closing': closing,
        'ledger': ledger,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'period_net': period_net,
        'has_period': has_period,
    }


def _period_ledger_summary(opening, total_debit, total_credit, closing):
    """KPI cards shared by ledger-style account reports."""
    return [
        {
            'label': 'Opening balance',
            'value': f'KES {_fmt_kes(opening)}',
            'hint': 'Account position before selected period',
        },
        {
            'label': 'Period debits',
            'value': f'KES {_fmt_kes(total_debit)}',
            'hint': 'Money out in selected period',
        },
        {
            'label': 'Period credits',
            'value': f'KES {_fmt_kes(total_credit)}',
            'hint': 'Money in during selected period',
        },
        {
            'label': 'Closing balance',
            'value': f'KES {_fmt_kes(closing)}',
            'hint': 'Opening + credits − debits',
        },
    ]


def _apply_ledger_vote_names(rows, vote_map):
    """Attach vote_name to each ledger transaction row."""
    vote_map = vote_map or {}
    for row in rows or []:
        related_type = (row.get('related_type') or '').strip().lower()
        related_id = row.get('related_id')
        key = None
        if related_type and related_id is not None:
            try:
                key = (related_type, int(related_id))
            except (TypeError, ValueError):
                key = None
        row['vote_name'] = vote_map.get(key, '—') if key else '—'


def fetch_ledger_rows(cursor, account_id, date_from=None, date_to=None, helpers=None, opening_balance=0.0):
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
                   related_type, related_id, balance_after, recorded_by_name, created_at
            FROM finance_account_transactions
            WHERE finance_account_id = %s{extra}
            ORDER BY created_at ASC, id ASC
            LIMIT 3000
            """,
            tuple(params),
        )
        has_period = bool(date_from or date_to)
        running = round(float(opening_balance or 0), 2)
        for r in cursor.fetchall() or []:
            direction = (_row_val(r, 'direction', 1) or '').strip().lower()
            amt = float(_row_val(r, 'amount', 2) or 0)
            debit = amt if direction == 'debit' else 0.0
            credit = amt if direction == 'credit' else 0.0
            running = round(running + credit - debit, 2)
            created = _row_val(r, 'created_at', 10)
            period_key = ''
            if created and hasattr(created, 'strftime'):
                dt_display = created.strftime('%d %b %Y')
                period_key = created.strftime('%Y-%m')
            else:
                dt_display = str(created or '—').split(' ')[0]
                period_key = dt_display[:7] if len(dt_display) >= 7 else ''
            bal_after = _row_val(r, 'balance_after', 8)
            if has_period or bal_after is None:
                balance_display = _fmt_kes(running)
            else:
                balance_display = _fmt_kes(bal_after)
            rows.append({
                'date': dt_display,
                'reference': (_row_val(r, 'reference_code', 4) or '—').strip() or '—',
                'description': (_row_val(r, 'description', 5) or '—').strip() or '—',
                'debit_display': _fmt_kes(debit) if debit else '—',
                'credit_display': _fmt_kes(credit) if credit else '—',
                'balance_display': balance_display,
                'recorded_by': (_row_val(r, 'recorded_by_name', 9) or '—').strip() or '—',
                'debit': debit,
                'credit': credit,
                'payment_method': (_row_val(r, 'payment_method', 3) or '').strip(),
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

    period = _resolve_account_period(cursor, account_id, date_from, date_to, account, helpers)
    opening = period['opening']
    closing = period['closing']
    ledger = period['ledger']
    total_debit = period['total_debit']
    total_credit = period['total_credit']
    period_net = period['period_net']

    if slug == 'general-ledger':
        prior_ledger = _fetch_prior_ledger_rows(cursor, account_id, date_from, helpers)
        linked_votes = []
        load_votes = helpers.get('load_account_expense_votes')
        if load_votes:
            try:
                linked_votes = load_votes(cursor, account_id) or []
            except Exception as e:
                print(f'fetch_account_report_payload linked votes: {e}')
        vote_ledgers = _build_per_vote_general_ledgers(prior_ledger, ledger, linked_votes)
        return {
            'report_type': slug,
            'summary': _period_ledger_summary(opening, total_debit, total_credit, closing),
            'vote_ledgers': vote_ledgers,
            'columns': list(ACCOUNT_GENERAL_LEDGER_COLUMNS),
            'rows': [],
            'transaction_count': len(ledger),
        }

    if slug == 'trial-balance':
        prior_ledger = _fetch_prior_ledger_rows(cursor, account_id, date_from, helpers)
        trial_lines = _build_account_trial_balance_by_vote(
            prior_ledger, ledger, opening, total_debit, total_credit, closing,
        )
        vote_count = max(len(trial_lines) - 1, 0)
        return {
            'report_type': slug,
            'summary': _period_ledger_summary(opening, total_debit, total_credit, closing),
            'trial_lines': trial_lines,
            'transaction_count': vote_count,
            'rows': [],
        }

    if slug == 'income-expenditure':
        income_rows = [r for r in ledger if r['credit'] > 0]
        expense_rows = [r for r in ledger if r['debit'] > 0]
        return {
            'report_type': slug,
            'summary': [
                {'label': 'Opening balance', 'value': f'KES {_fmt_kes(opening)}'},
                {'label': 'Period income (credits)', 'value': f'KES {_fmt_kes(total_credit)}'},
                {'label': 'Period expenditure (debits)', 'value': f'KES {_fmt_kes(total_debit)}'},
                {'label': 'Surplus / (deficit)', 'value': f'KES {_fmt_kes(period_net)}'},
                {'label': 'Closing balance', 'value': f'KES {_fmt_kes(closing)}'},
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
            'summary': [
                {'label': 'Account', 'value': account.get('account_name') or '—'},
                {'label': 'Category', 'value': cat},
                {'label': 'Opening balance', 'value': f'KES {_fmt_kes(opening)}'},
                {'label': 'Closing balance', 'value': f'KES {_fmt_kes(closing)}'},
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
                {'label': 'Opening balance', 'value': f'KES {_fmt_kes(opening)}'},
                {'label': 'Cash in', 'value': f'KES {_fmt_kes(total_credit)}'},
                {'label': 'Cash out', 'value': f'KES {_fmt_kes(total_debit)}'},
                {'label': 'Net cash flow', 'value': f'KES {_fmt_kes(period_net)}'},
                {'label': 'Closing balance', 'value': f'KES {_fmt_kes(closing)}'},
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
        fee_rows = [r for r in fee_rows if _row_in_period(r, date_from, date_to)]
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
                {'label': 'Opening balance', 'value': f'KES {_fmt_kes(opening)}'},
                {'label': 'Period payments', 'value': str(len(display))},
                {'label': 'Fees received', 'value': f'KES {_fmt_kes(fee_total)}'},
                {'label': 'Closing balance', 'value': f'KES {_fmt_kes(closing)}'},
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

    if slug == 'cash-book':
        prior_ledger = _fetch_prior_ledger_rows(cursor, account_id, date_from, helpers)
        _enrich_ledger_with_votes(cursor, account_id, prior_ledger, helpers)
        _enrich_ledger_with_votes(cursor, account_id, ledger, helpers)
        vote_meta = _collect_cash_book_vote_meta(
            cursor, account_id, helpers, (prior_ledger or []) + (ledger or []),
        )
        votes = [v['key'] for v in vote_meta]
        student_paid_state = {}
        for entry in prior_ledger or []:
            _cash_book_allocate_entry(
                cursor, entry, votes, helpers, student_paid_state, account_id,
            )
        cb_rows, cb_totals = _build_account_cash_book_rows(
            cursor, account_id, ledger, votes, helpers, student_paid_state,
        )
        return {
            'report_type': slug,
            'summary': [
                {'label': 'Opening balance', 'value': f'KES {_fmt_kes(opening)}'},
                {'label': 'Cash receipts & payments', 'value': f'KES {_fmt_kes(cb_totals["cash"])}'},
                {'label': 'Bank receipts & payments', 'value': f'KES {_fmt_kes(cb_totals["bank"])}'},
                {'label': 'Closing balance', 'value': f'KES {_fmt_kes(closing)}'},
            ],
            'columns': _build_cash_book_columns(vote_meta),
            'vote_names': [v.get('name') or v.get('key') for v in vote_meta],
            'vote_meta': vote_meta,
            'rows': cb_rows,
            'transaction_count': max(len(cb_rows) - (1 if cb_rows else 0), 0),
        }

    return {'error': 'Unknown report'}


def _petty_cash_expense_book_row(exp, vote_desc_map):
    """One petty cash expense line for the cash book."""
    vote = (exp.get('vote_name') or '').strip() or '—'
    vote_key = vote.upper()
    notes = (exp.get('notes') or '').strip()
    vote_desc = (vote_desc_map.get(vote_key) or '').strip()
    description = notes or vote_desc or '—'

    name = (exp.get('paid_to_name') or '').strip()
    phone = (exp.get('paid_to_phone') or '').strip()
    if name and phone:
        company = f'{name} · {phone}'
    elif name:
        company = name
    elif phone:
        company = phone
    else:
        company = '—'

    amount = float(exp.get('amount') or 0)
    ref = (
        (exp.get('reference_number') or exp.get('payment_reference') or '').strip() or '—'
    )
    return {
        'expense_vote': vote,
        'expense_description': description,
        'company_display': company,
        'reference': ref,
        'debit_display': _fmt_kes(amount) if amount else '—',
        'credit_display': '—',
    }


def fetch_petty_cash_book_payload(cursor, account_id, filters, helpers):
    """Petty cash book — opening balance, dated expenses/top-ups, closing balance."""
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

    period = _resolve_account_period(cursor, account_id, date_from, date_to, account, helpers)
    opening = period['opening']
    closing = period['closing']
    ledger = period['ledger']
    total_topup = round(sum(float(r.get('credit') or 0) for r in ledger), 2)
    total_expenses = round(
        sum(
            float(r.get('debit') or 0)
            for r in ledger
            if r.get('related_type') == 'petty_cash_expense'
        ),
        2,
    )

    vote_desc_map = {}
    load_vote_descriptions = helpers.get('load_expense_vote_descriptions')
    if load_vote_descriptions:
        try:
            vote_desc_map = load_vote_descriptions(cursor) or {}
        except Exception as e:
            print(f'fetch_petty_cash_book_payload vote descriptions: {e}')

    expense_data = []
    load_expense_rows = helpers.get('load_petty_cash_expense_rows')
    if load_expense_rows:
        try:
            expense_data = load_expense_rows(cursor, account_id, filters) or []
        except Exception as e:
            print(f'fetch_petty_cash_book_payload expense rows: {e}')

    expense_by_id = {}
    for exp in expense_data:
        eid = exp.get('id')
        if eid is not None:
            try:
                expense_by_id[int(eid)] = exp
            except (TypeError, ValueError):
                pass

    rows = [{
        'date': '—',
        'expense_vote': 'Opening balance',
        'expense_description': 'Balance brought forward',
        'company_display': '—',
        'reference': '—',
        'debit_display': '—',
        'credit_display': _fmt_kes(opening) if opening else '—',
        '_ledger_row': 'opening',
    }]

    transaction_count = 0
    for entry in ledger:
        debit = float(entry.get('debit') or 0)
        credit = float(entry.get('credit') or 0)
        related_type = (entry.get('related_type') or '').strip().lower()
        related_id = entry.get('related_id')
        row_date = entry.get('date', '—')

        if credit > 0:
            desc = (entry.get('description') or '').strip() or 'Petty cash top up'
            rows.append({
                'date': row_date,
                'expense_vote': 'Top up',
                'expense_description': desc,
                'company_display': '—',
                'reference': entry.get('reference', '—'),
                'debit_display': '—',
                'credit_display': entry.get('credit_display', '—'),
            })
            transaction_count += 1
            continue

        if debit <= 0:
            continue

        if related_type == 'petty_cash_expense' and related_id is not None:
            try:
                exp = expense_by_id.get(int(related_id))
            except (TypeError, ValueError):
                exp = None
            if exp:
                line = _petty_cash_expense_book_row(exp, vote_desc_map)
            else:
                line = {
                    'expense_vote': '—',
                    'expense_description': (entry.get('description') or '—').strip() or '—',
                    'company_display': '—',
                    'reference': entry.get('reference', '—'),
                    'debit_display': entry.get('debit_display', '—'),
                    'credit_display': '—',
                }
        else:
            line = {
                'expense_vote': '—',
                'expense_description': (entry.get('description') or '—').strip() or '—',
                'company_display': '—',
                'reference': entry.get('reference', '—'),
                'debit_display': entry.get('debit_display', '—'),
                'credit_display': '—',
            }
        line['date'] = row_date
        rows.append(line)
        transaction_count += 1

    rows.append({
        'date': '—',
        'expense_vote': 'Closing balance',
        'expense_description': 'Balance carried forward',
        'company_display': '—',
        'reference': '—',
        'debit_display': '—',
        'credit_display': _fmt_kes(closing) if closing else '—',
        '_ledger_row': 'closing',
    })

    return {
        'report_type': 'petty-cash-book',
        'summary': [
            {'label': 'Opening balance', 'value': f'KES {_fmt_kes(opening)}'},
            {'label': 'Top up', 'value': f'KES {_fmt_kes(total_topup)}'},
            {'label': 'Period expenses', 'value': f'KES {_fmt_kes(total_expenses)}'},
            {'label': 'Closing balance', 'value': f'KES {_fmt_kes(closing)}'},
        ],
        'columns': [
            {'key': 'date', 'label': 'Date'},
            {'key': 'expense_vote', 'label': 'Expense vote'},
            {'key': 'expense_description', 'label': 'Expense description'},
            {'key': 'company_display', 'label': 'Company name & number'},
            {'key': 'reference', 'label': 'Reference'},
            {'key': 'debit_display', 'label': 'Debit (KES)', 'align': 'right'},
            {'key': 'credit_display', 'label': 'Credit (KES)', 'align': 'right'},
        ],
        'rows': rows,
        'transaction_count': transaction_count,
    }


def petty_cash_book_empty_payload():
    """Placeholder book layout when no petty cash account exists yet."""
    return {
        'report_type': 'petty-cash-book',
        'summary': [
            {'label': 'Opening balance', 'value': 'KES 0.00'},
            {'label': 'Top up', 'value': 'KES 0.00'},
            {'label': 'Closing balance', 'value': 'KES 0.00'},
        ],
        'columns': [
            {'key': 'date', 'label': 'Date'},
            {'key': 'expense_vote', 'label': 'Expense vote'},
            {'key': 'expense_description', 'label': 'Expense description'},
            {'key': 'company_display', 'label': 'Company name & number'},
            {'key': 'reference', 'label': 'Reference'},
            {'key': 'debit_display', 'label': 'Debit (KES)', 'align': 'right'},
            {'key': 'credit_display', 'label': 'Credit (KES)', 'align': 'right'},
        ],
        'rows': [],
        'transaction_count': 0,
        'empty_state': True,
    }
