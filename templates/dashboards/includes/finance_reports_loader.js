/**
 * Accounts reports — live filters and table loader.
 */
(function () {
  /** Which filter groups apply per report (keeps UI focused). */
  var FILTER_PROFILES = {
    'revenue-collection': {
      panelTitle: 'Filter income',
      context:
        'Choose a financial year, then narrow the date range within that period. Income type and class filters apply inside the selected year.',
      groups: ['financial_year', 'date', 'source', 'account', 'class', 'search'],
      sourceLabel: 'Income type',
      searchPlaceholder: 'Student name or reference…',
      needDates: true,
    },
    expenditure: {
      panelTitle: 'Filter spending',
      context:
        'Choose a financial year, then narrow the date range. Vote budget = allocated; vote expenditure = actual spend; vote balance = budget minus expenditure.',
      groups: ['financial_year', 'date', 'search'],
      sourceLabel: 'Expense type',
      searchPlaceholder: 'Party, reference, type, or description…',
      needDates: true,
    },
    'financial-statements': {
      panelTitle: 'Report scope',
      context:
        'Select a financial year to view opening/closing balances and ledger snapshot for that period. Dates are limited to the chosen year.',
      groups: ['financial_year', 'date'],
      needDates: true,
    },
    'audit-compliance': {
      panelTitle: 'Filter audit trail',
      context:
        'Choose a financial year and date range within it to review fee, expense, and salary audit activity.',
      groups: ['financial_year', 'date', 'source', 'search'],
      sourceLabel: 'Record type',
      searchPlaceholder: 'Student, reference, or detail…',
      needDates: true,
    },
    'periodic-summary': {
      panelTitle: 'Period summary',
      context:
        'Choose a financial year, then pick how to roll up collections vs spending within that year.',
      groups: ['financial_year', 'date', 'period'],
      needDates: true,
    },
  };

  var activeProfile = null;

  var SOURCE_OPTIONS = {
    'revenue-collection': [
      { v: 'all', l: 'All sources' },
      { v: 'fees', l: 'Fee collections only' },
      { v: 'government', l: 'Government' },
      { v: 'private', l: 'Private / other' },
      { v: 'income', l: 'Income accounts' },
    ],
    expenditure: [
      { v: 'all', l: 'All expenditure' },
      { v: 'salary', l: 'Salaries' },
      { v: 'payment', l: 'Supplier payments' },
      { v: 'store', l: 'Stock-in' },
      { v: 'misc', l: 'Miscellaneous' },
    ],
    'financial-statements': [{ v: 'all', l: 'All (snapshot)' }],
    'audit-compliance': [
      { v: 'all', l: 'All audit types' },
      { v: 'fees', l: 'Fee payments' },
      { v: 'salary', l: 'Salary' },
      { v: 'store', l: 'Store' },
      { v: 'payment', l: 'Payments' },
      { v: 'misc', l: 'Misc' },
    ],
    'periodic-summary': [{ v: 'all', l: 'All sources' }],
    'student-specific': [{ v: 'all', l: 'All' }],
  };

  var DEBOUNCE_MS = 280;
  var SEARCH_DEBOUNCE_MS = 400;
  var fetchAbort = null;
  var debounceTimer = null;
  var searchDebounceTimer = null;

  function readConfig() {
    var el = document.getElementById('fr-page-config');
    if (!el || !el.textContent) return {};
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return {};
    }
  }

  function qs(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function attrEscUrl(url) {
    if (url == null) return '';
    return String(url).replace(/"/g, '&quot;');
  }

  var cfg = readConfig();
  if (!cfg.dataApi) return;
  var spLedger = new URLSearchParams(window.location.search);
  if (spLedger.get('ledger')) cfg.expenditureLedger = spLedger.get('ledger');
  if (spLedger.get('statement')) cfg.financialStatement = spLedger.get('statement');

  var slug = cfg.reportSlug || '';
  var sourceEl = qs('fr-source');
  var periodWrap = qs('fr-period-wrap');
  var periodEl = qs('fr-period');

  function fillSourceOptions() {
    if (!sourceEl) return;
    var prev = sourceEl.value;
    var opts = SOURCE_OPTIONS[slug] || SOURCE_OPTIONS['revenue-collection'];
    sourceEl.innerHTML = opts
      .map(function (o) {
        return '<option value="' + esc(o.v) + '">' + esc(o.l) + '</option>';
      })
      .join('');
    if (prev && Array.prototype.some.call(sourceEl.options, function (o) { return o.value === prev; })) {
      sourceEl.value = prev;
    }
  }

  fillSourceOptions();

  function financialYearById(id) {
    if (id == null || id === '') return null;
    var years = cfg.financialYears || [];
    for (var i = 0; i < years.length; i++) {
      if (String(years[i].id) === String(id)) return years[i];
    }
    return null;
  }

  function selectedFinancialYear() {
    var sel = qs('fr-financial-year');
    if (!sel || !groupActive('financial_year')) return null;
    return financialYearById(sel.value);
  }

  function todayIso() {
    var now = new Date();
    var y = now.getFullYear();
    var m = String(now.getMonth() + 1).padStart(2, '0');
    var d = String(now.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + d;
  }

  function defaultDateToForYear(yr) {
    if (!yr || !yr.end) return todayIso();
    if (yr.is_current) {
      var today = todayIso();
      return today <= yr.end ? today : yr.end;
    }
    return yr.end;
  }

  function updateFinancialYearHint(yr) {
    var hint = qs('fr-fy-range-hint');
    if (!hint) return;
    if (!yr || !yr.start || !yr.end) {
      hint.textContent = '';
      return;
    }
    hint.textContent = 'Dates limited to ' + yr.start + ' – ' + yr.end;
  }

  function clampDateInputsToYear(yr) {
    var df = qs('fr-date-from');
    var dt = qs('fr-date-to');
    if (!yr || !yr.start || !yr.end) {
      if (df) {
        df.removeAttribute('min');
        df.removeAttribute('max');
      }
      if (dt) {
        dt.removeAttribute('min');
        dt.removeAttribute('max');
      }
      updateFinancialYearHint(null);
      return;
    }
    if (df) {
      df.min = yr.start;
      df.max = yr.end;
      if (!df.value || df.value < yr.start) df.value = yr.start;
      if (df.value > yr.end) df.value = yr.end;
    }
    if (dt) {
      dt.min = yr.start;
      dt.max = yr.end;
      if (!dt.value) {
        dt.value = defaultDateToForYear(yr);
      } else {
        if (dt.value > yr.end) dt.value = yr.end;
        if (dt.value < yr.start) dt.value = yr.start;
      }
    }
    if (df && dt && df.value > dt.value) {
      df.value = yr.start;
      dt.value = defaultDateToForYear(yr);
    }
    updateFinancialYearHint(yr);
  }

  function applyFinancialYearSelection(resetDates) {
    var yr = selectedFinancialYear();
    if (!groupActive('financial_year')) return;
    if (!yr) {
      clampDateInputsToYear(null);
      return;
    }
    var df = qs('fr-date-from');
    var dt = qs('fr-date-to');
    if (df) {
      df.min = yr.start;
      df.max = yr.end;
    }
    if (dt) {
      dt.min = yr.start;
      dt.max = yr.end;
    }
    if (resetDates) {
      if (df) df.value = yr.start;
      if (dt) dt.value = defaultDateToForYear(yr);
    } else {
      clampDateInputsToYear(yr);
    }
    updateFinancialYearHint(yr);
  }

  function defaultFinancialYear() {
    var sel = qs('fr-financial-year');
    if (!sel || !groupActive('financial_year')) return;
    var defaultId = cfg.defaultFinancialYearId != null ? String(cfg.defaultFinancialYearId) : '';
    if (defaultId && Array.prototype.some.call(sel.options, function (o) { return o.value === defaultId; })) {
      sel.value = defaultId;
    } else if (sel.options.length) {
      sel.selectedIndex = 0;
    }
    applyFinancialYearSelection(true);
  }

  function profileGroups() {
    return (activeProfile && activeProfile.groups) || [];
  }

  function groupActive(name) {
    return profileGroups().indexOf(name) >= 0;
  }

  function applyFilterProfile() {
    activeProfile = FILTER_PROFILES[slug] || FILTER_PROFILES['revenue-collection'];
    var groups = profileGroups();
    var panel = document.querySelector('.fr-report-filters');
    var grid = qs('fr-filter-grid');
    var titleEl = qs('fr-filter-title');
    var ctxEl = qs('fr-filter-context');
    var srcLabel = qs('fr-source-group-label');

    if (titleEl) titleEl.textContent = activeProfile.panelTitle || 'Filters';
    if (ctxEl) ctxEl.textContent = activeProfile.context || '';

    document.querySelectorAll('[data-fr-group]').forEach(function (node) {
      var g = node.getAttribute('data-fr-group');
      var show = groups.indexOf(g) >= 0;
      node.classList.toggle('hidden', !show);
      if (!show) {
        node.querySelectorAll('input, select').forEach(function (inp) {
          if (inp.tagName === 'SELECT') {
            var first = inp.querySelector('option');
            inp.value = first ? first.value : '';
          } else {
            inp.value = '';
          }
        });
      }
    });

    if (grid) {
      grid.classList.toggle('fr-report-filters__grid--active', groups.length > 0);
    }
    if (panel) {
      panel.classList.toggle('fr-report-filters--minimal', groups.length === 0);
    }

    if (srcLabel && activeProfile.sourceLabel) {
      srcLabel.textContent = activeProfile.sourceLabel;
    }
    var search = qs('fr-search');
    if (search && activeProfile.searchPlaceholder) {
      search.placeholder = activeProfile.searchPlaceholder;
    }

    fillSourceOptions();
    if (sourceEl && groupActive('source')) {
      sourceEl.value = 'all';
    }
    var fySel = qs('fr-financial-year');
    if (groupActive('financial_year') && fySel && !fySel.options.length) {
      var fyWrap = qs('fr-financial-year-wrap');
      if (fyWrap) {
        fyWrap.classList.add('hidden');
      }
    }
  }

  function updateActiveFilterChips() {
    var box = qs('fr-active-filters');
    if (!box) return;
    var chips = [];
    var fySel = qs('fr-financial-year');
    if (groupActive('financial_year') && fySel && fySel.value) {
      var fyOpt = fySel.options[fySel.selectedIndex];
      if (fyOpt) chips.push(fyOpt.text.split('—')[0].trim());
    }
    var df = qs('fr-date-from');
    var dt = qs('fr-date-to');
    if (groupActive('date') && df && df.value && dt && dt.value) {
      chips.push(df.value + ' → ' + dt.value);
    }
    if (groupActive('source') && sourceEl && sourceEl.value && sourceEl.value !== 'all') {
      var opt = sourceEl.options[sourceEl.selectedIndex];
      chips.push(opt ? opt.text : sourceEl.value);
    }
    if (groupActive('account')) {
      var fa = qs('fr-finance-account');
      if (fa && fa.value) {
        var o = fa.options[fa.selectedIndex];
        chips.push(o ? o.text : 'Account');
      }
    }
    if (groupActive('class')) {
      var gr = qs('fr-grade');
      if (gr && gr.value) chips.push(gr.value);
    }
    if (groupActive('period') && periodEl && periodEl.value) {
      var po = periodEl.options[periodEl.selectedIndex];
      chips.push('By ' + (po ? po.text.toLowerCase() : periodEl.value));
    }
    if (groupActive('search')) {
      var q = qs('fr-search');
      if (q && q.value.trim()) chips.push('“' + q.value.trim() + '”');
    }
    if (!chips.length) {
      box.classList.add('hidden');
      box.innerHTML = '';
      return;
    }
    box.classList.remove('hidden');
    box.innerHTML =
      '<span class="text-[0.6875rem] font-semibold uppercase text-slate-500 mr-1">Showing:</span>' +
      chips
        .map(function (c) {
          return '<span class="fr-active-filters__chip">' + esc(c) + '</span>';
        })
        .join('');
  }

  function paramsFromForm() {
    var p = new URLSearchParams();
    var df = qs('fr-date-from');
    var dt = qs('fr-date-to');
    var fa = qs('fr-finance-account');
    var gr = qs('fr-grade');
    var src = qs('fr-source');
    var per = qs('fr-period');
    var q = qs('fr-search');
    var fy = qs('fr-financial-year');
    if (cfg.expenditureVote) {
      p.set('vote', cfg.expenditureVote);
    }
    var ledger = cfg.expenditureLedger || new URLSearchParams(window.location.search).get('ledger') || '';
    if (ledger) {
      p.set('ledger', ledger);
    }
    if (slug === 'financial-statements') {
      var statement = cfg.financialStatement || new URLSearchParams(window.location.search).get('statement') || '';
      if (statement) p.set('statement', statement);
    }
    if (groupActive('financial_year') && fy && fy.value) {
      p.set('financial_year_id', fy.value);
    }
    if (groupActive('date')) {
      if (df && df.value) p.set('date_from', df.value);
      if (dt && dt.value) p.set('date_to', dt.value);
    }
    if (groupActive('account') && fa && fa.value) p.set('finance_account_id', fa.value);
    if (groupActive('class') && gr && gr.value) p.set('grade', gr.value);
    if (groupActive('source') && src && src.value) p.set('source', src.value);
    if (groupActive('period') && per && per.value) p.set('period', per.value);
    if (groupActive('search') && q && q.value.trim()) p.set('q', q.value.trim());
    return p;
  }

  function syncUrl() {
    var p = paramsFromForm();
    var url = window.location.pathname + (p.toString() ? '?' + p.toString() : '');
    window.history.replaceState({}, '', url);
  }

  function readUrlIntoForm() {
    var sp = new URLSearchParams(window.location.search);
    function set(id, key) {
      var el = qs(id);
      if (el && sp.has(key)) el.value = sp.get(key);
    }
    set('fr-date-from', 'date_from');
    set('fr-date-to', 'date_to');
    set('fr-financial-year', 'financial_year_id');
    set('fr-finance-account', 'finance_account_id');
    set('fr-grade', 'grade');
    set('fr-source', 'source');
    set('fr-period', 'period');
    set('fr-search', 'q');
  }

  function defaultDates() {
    if (!groupActive('date')) return;
    if (groupActive('financial_year')) {
      defaultFinancialYear();
      return;
    }
    var df = qs('fr-date-from');
    var dt = qs('fr-date-to');
    if ((df && df.value) || (dt && dt.value)) return;
    if (cfg.defaultDateFrom && cfg.defaultDateTo) {
      if (df) df.value = cfg.defaultDateFrom;
      if (dt) dt.value = cfg.defaultDateTo;
      return;
    }
    var now = new Date();
    var y = now.getFullYear();
    var m = String(now.getMonth() + 1).padStart(2, '0');
    if (dt) dt.value = y + '-' + m + '-' + String(now.getDate()).padStart(2, '0');
    if (df) df.value = y + '-01-01';
  }

  var KPI_ACCENTS = ['fr-kpi--teal', 'fr-kpi--emerald', 'fr-kpi--sky', 'fr-kpi--violet', 'fr-kpi--amber'];

  function renderSummary(cards) {
    var box = qs('fr-summary');
    if (!box) return;
    box.innerHTML = '';
    (cards || []).forEach(function (c, i) {
      var article = document.createElement('article');
      article.className = 'fr-kpi ' + (KPI_ACCENTS[i % KPI_ACCENTS.length] || 'fr-kpi--teal');
      article.innerHTML =
        '<p class="fr-kpi__label">' +
        esc(c.label) +
        '</p><p class="fr-kpi__value">' +
        esc(c.value) +
        '</p>' +
        (c.hint ? '<p class="fr-kpi__hint">' + esc(c.hint) + '</p>' : '');
      box.appendChild(article);
    });
    box.classList.toggle('hidden', !cards || !cards.length);
  }

  function renderVoteDetail(position, opts) {
    opts = opts || {};
    var wrap = qs('fr-vote-detail');
    var summary = qs('fr-summary');
    var compare = qs('fr-vote-budget-actual');
    if (!position || !wrap) {
      if (wrap) wrap.classList.add('hidden');
      return;
    }
    wrap.classList.remove('hidden');
    if (compare) {
      compare.classList.toggle('hidden', !!opts.ledgerView);
    }
    if (summary && !opts.ledgerView) summary.classList.add('hidden');

    function setText(id, text) {
      var el = qs(id);
      if (el) el.textContent = text != null ? text : '—';
    }
    var budget = position.budget_display || '0.00';
    var expenditure = position.expenditure_display || '0.00';
    var balance = position.balance_display || '0.00';
    var collections = position.collections_display || '0.00';
    var periodColl = position.period_collections_display || collections;

    setText('fr-vp-budget', 'KES ' + budget);
    setText('fr-vp-expenditure', 'KES ' + expenditure);
    setText('fr-vp-balance', 'KES ' + balance);
    setText('fr-vp-util', (position.utilization_display || '—') + ' used');
    setText('fr-vp-row-budget', 'KES ' + budget);
    setText('fr-vp-row-expenditure', 'KES ' + expenditure);
    setText('fr-vp-row-collections', 'KES ' + periodColl);
    setText('fr-vp-row-balance', 'KES ' + balance);

    var bar = qs('fr-vp-bar');
    if (bar) {
      var pct = Math.min(100, Math.max(0, parseFloat(position.utilization_pct) || 0));
      bar.style.width = pct + '%';
    }
  }

  function hideVoteDetail() {
    var wrap = qs('fr-vote-detail');
    var compare = qs('fr-vote-budget-actual');
    if (wrap) wrap.classList.add('hidden');
    if (compare) compare.classList.remove('hidden');
  }

  function showStatementsBlank(message) {
    var blank = qs('fr-statements-blank');
    var title = qs('fr-statements-blank-title');
    if (title) title.textContent = message || 'Choose a financial statement from the sidebar.';
    if (blank) blank.classList.remove('hidden');
  }

  function hideStatementsBlank() {
    var blank = qs('fr-statements-blank');
    if (blank) blank.classList.add('hidden');
  }

  function mastheadPeriodLabel() {
    if (!groupActive('date')) {
      return 'All dates (snapshot)';
    }
    var df = qs('fr-date-from');
    var dt = qs('fr-date-to');
    var from = df && df.value ? df.value : '';
    var to = dt && dt.value ? dt.value : '';
    if (from && to) return from + ' to ' + to;
    if (from) return 'From ' + from;
    if (to) return 'Until ' + to;
    return 'All dates';
  }

  function updateMastheadPeriod() {
    var el = document.getElementById('fr-masthead-period');
    if (el) el.textContent = mastheadPeriodLabel();
  }

  function syncSidebarAccountHighlight() {
    if (slug !== 'revenue-collection') return;
    var fa = qs('fr-finance-account');
    var id = fa && fa.value ? String(fa.value) : '';
    var allLink = document.querySelector('[data-fr-sidebar-all-accounts]');
    document.querySelectorAll('[data-fr-sidebar-account]').forEach(function (link) {
      var aid = link.getAttribute('data-fr-sidebar-account') || '';
      var on = id && aid === id;
      link.classList.toggle('sidebar-item-active', on);
      var mark = link.querySelector('.fr-sidebar-active-mark');
      if (on && !mark) {
        mark = document.createElement('i');
        mark.className = 'fas fa-check-circle ml-auto text-green-500 fr-sidebar-active-mark shrink-0';
        mark.setAttribute('aria-hidden', 'true');
        link.appendChild(mark);
      } else if (!on && mark) {
        mark.remove();
      }
    });
    if (allLink) {
      allLink.classList.toggle('sidebar-item-active', !id);
      var allMark = allLink.querySelector('.fr-sidebar-active-mark');
      if (!id && !allMark) {
        allMark = document.createElement('i');
        allMark.className = 'fas fa-check-circle ml-auto text-green-500 fr-sidebar-active-mark';
        allMark.setAttribute('aria-hidden', 'true');
        allLink.appendChild(allMark);
      } else if (id && allMark) {
        allMark.remove();
      }
    }
  }

  function voteRowHref(row) {
    if (!row || !row.vote_name) return '#';
    var base =
      cfg.expenditureListUrl ||
      (cfg.dataApi ? String(cfg.dataApi).replace(/\/data\/?$/, '') : '');
    if (!base) return '#';
    var p = paramsFromForm();
    p.set('vote', row.vote_name);
    return base + '?' + p.toString();
  }

  function updateTableTitle(viewMode, voteName, sectionTitle) {
    var el = qs('fr-table-title');
    if (!el) return;
    if (sectionTitle) {
      el.textContent = sectionTitle;
      return;
    }
    if (viewMode === 'votes') {
      el.textContent = 'Votes — budget, expenditure & balance';
    } else if (viewMode === 'vote_detail') {
      el.textContent = 'Vote Transactions';
    } else if (viewMode === 'vote_ledger' || viewMode === 'expenditure_ledger' || viewMode === 'financial_statement') {
      el.textContent = sectionTitle || 'Ledger';
    } else {
      el.textContent = 'Report detail';
    }
  }

  function renderTable(table, rowCount, viewMode, voteName) {
    var wrap = qs('fr-table-wrap');
    var thead = qs('fr-thead');
    var tbody = qs('fr-tbody');
    var countEl = qs('fr-row-count');
    if (!wrap || !thead || !tbody) return;
    var cols = (table && table.columns) || [];
    var rows = (table && table.rows) || [];
    thead.innerHTML =
      '<tr>' +
      cols
        .map(function (c) {
          var align = c.align === 'right' ? ' text-right' : '';
          return '<th class="' + align.trim() + '">' + esc(c.label) + '</th>';
        })
        .join('') +
      '</tr>';
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="' +
        cols.length +
        '" class="text-center" style="padding:2rem;color:var(--fr-muted)">No rows match these filters.</td></tr>';
    } else {
      var isVotes =
        viewMode === 'votes' ||
        (slug === 'expenditure' && !cfg.expenditureVote && rows.length && rows[0].vote_name);
      tbody.innerHTML = rows
        .map(function (row) {
          var href = isVotes && row.vote_name ? voteRowHref(row) : '';
          var ledgerKind = row._ledger_row || '';
          var trClass = ledgerKind ? ' fr-ledger-row fr-ledger-row--' + ledgerKind : '';
          var cells =
            cols
              .map(function (c) {
                var align = c.align === 'right' ? ' text-right tabular-nums' : '';
                var mono = c.key === 'reference' || c.key === 'ref' ? ' fr-mono' : '';
                var flowClass =
                  c.key === 'flow_label' && row.flow === 'in'
                    ? ' fr-flow-in'
                    : c.key === 'flow_label' && row.flow === 'out'
                      ? ' fr-flow-out'
                      : '';
                var cellVal = row[c.key] != null ? row[c.key] : '—';
                if (isVotes && c.key === 'vote_name' && row.vote_name && href && href !== '#') {
                  cellVal =
                    '<a href="' +
                    attrEscUrl(href) +
                    '" class="fr-vote-name-link">' +
                    esc(row.vote_name) +
                    '</a>';
                } else {
                  cellVal = esc(cellVal);
                }
                return (
                  '<td class="' +
                  (align + mono + flowClass).trim() +
                  '" data-label="' +
                  esc(c.label) +
                  '">' +
                  cellVal +
                  '</td>'
                );
              })
              .join('');
          if (isVotes && row.vote_name && href && href !== '#') {
            return (
              '<tr class="fr-report-row-link' +
              trClass +
              '" tabindex="0" role="link" data-href="' +
              attrEscUrl(href) +
              '" onclick="if(!event.target.closest(\'a\'))window.location.assign(this.getAttribute(\'data-href\'))" title="View expenditure for ' +
              esc(row.vote_name) +
              '">' +
              cells +
              '</tr>'
            );
          }
          return '<tr class="' + trClass.trim() + '">' + cells + '</tr>';
        })
        .join('');
    }
    if (countEl) {
      var n = rowCount != null ? rowCount : rows.length;
      countEl.textContent = n + ' record' + (n === 1 ? '' : 's');
    }
    wrap.classList.remove('hidden');
  }

  function loadReport() {
    var loading = qs('fr-loading');
    var errEl = qs('fr-error');
    var empty = qs('fr-empty');
    var tableWrap = qs('fr-table-wrap');
    var summary = qs('fr-summary');

    if (fetchAbort) {
      fetchAbort.abort();
      fetchAbort = null;
    }
    fetchAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;

    if (tableWrap && slug !== 'expenditure' && slug !== 'financial-statements') {
      tableWrap.classList.add('hidden');
    }
    if (summary) summary.classList.add('hidden');
    if (slug === 'financial-statements') {
      hideVoteDetail();
      if (tableWrap) tableWrap.classList.add('hidden');
    } else if (slug === 'expenditure' && cfg.expenditureVote) {
      /* keep vote detail panels visible while refreshing */
    } else if (slug === 'expenditure' && cfg.expenditureLedger) {
      hideVoteDetail();
    } else {
      hideVoteDetail();
    }
    if (loading) loading.classList.remove('hidden');
    if (errEl) {
      errEl.classList.add('hidden');
      errEl.textContent = '';
    }
    if (empty) empty.classList.add('hidden');

    updateActiveFilterChips();
    updateMastheadPeriod();
    syncSidebarAccountHighlight();
    syncUrl();
    var url = cfg.dataApi + '?' + paramsFromForm().toString();
    var fetchOpts = { credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (fetchAbort) fetchOpts.signal = fetchAbort.signal;

    fetch(url, fetchOpts)
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, body: j };
        });
      })
      .then(function (res) {
        if (loading) loading.classList.add('hidden');
        if (!res.ok || !res.body.success) {
          if (errEl) {
            errEl.textContent = (res.body && res.body.message) || 'Could not load report.';
            errEl.classList.remove('hidden');
          }
          return;
        }
        if (res.body.view_mode === 'vote_detail' || res.body.view_mode === 'vote_ledger') {
          if (res.body.vote_position) {
            renderVoteDetail(res.body.vote_position, {
              ledgerView: res.body.view_mode === 'vote_ledger',
            });
          }
          if (res.body.view_mode === 'vote_ledger') {
            renderSummary(res.body.ledger_summary || res.body.summary);
          }
        } else if (res.body.view_mode === 'expenditure_ledger') {
          hideVoteDetail();
          hideStatementsBlank();
          renderSummary(res.body.ledger_summary || res.body.summary);
        } else if (res.body.view_mode === 'statements_blank') {
          hideVoteDetail();
          if (summary) summary.classList.add('hidden');
          if (tableWrap) tableWrap.classList.add('hidden');
          showStatementsBlank(res.body.books_message || '');
        } else if (res.body.view_mode === 'financial_statement') {
          hideVoteDetail();
          hideStatementsBlank();
          renderSummary(res.body.ledger_summary || res.body.summary);
        } else {
          hideVoteDetail();
          hideStatementsBlank();
          renderSummary(res.body.summary);
        }
        if (res.body.view_mode !== 'statements_blank') {
          renderTable(res.body.table, res.body.row_count, res.body.view_mode, res.body.vote_name);
        }
        updateTableTitle(
          res.body.view_mode,
          res.body.vote_name || cfg.expenditureVote,
          res.body.table_section_title,
        );
        var mastTitle = document.querySelector('.fr-masthead__title');
        var mastDesc = document.querySelector('.fr-masthead__desc');
        if (
          mastTitle &&
          (res.body.view_mode === 'vote_detail' || res.body.view_mode === 'vote_ledger') &&
          res.body.vote_name
        ) {
          mastTitle.textContent = res.body.vote_name;
          if (mastDesc && res.body.vote_description) {
            mastDesc.textContent = res.body.vote_description;
          }
        } else if (mastTitle && slug === 'expenditure' && res.body.view_mode === 'votes') {
          mastTitle.textContent = 'Expenditure by vote';
        } else if (mastTitle && slug === 'expenditure' && res.body.view_mode === 'expenditure_ledger') {
          mastTitle.textContent = res.body.table_section_title || 'Expenditure book';
        } else if (mastTitle && slug === 'financial-statements' && res.body.view_mode === 'financial_statement') {
          mastTitle.textContent = res.body.table_section_title || 'Financial statement';
        } else if (mastTitle && slug === 'financial-statements' && res.body.view_mode === 'statements_blank') {
          mastTitle.textContent = 'Financial Statements';
        }
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        if (loading) loading.classList.add('hidden');
        if (errEl) {
          errEl.textContent = 'Network error loading report.';
          errEl.classList.remove('hidden');
        }
      });
  }

  function scheduleLoad(delay) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      updateActiveFilterChips();
      loadReport();
    }, delay == null ? DEBOUNCE_MS : delay);
  }

  function scheduleSearchLoad() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(loadReport, SEARCH_DEBOUNCE_MS);
  }

  function bindSidebarAccountLinks() {
    if (slug !== 'revenue-collection') return;
    var nav = document.querySelector('.fr-sidebar-nav--reports');
    if (!nav) return;
    nav.addEventListener('click', function (ev) {
      var link = ev.target.closest('[data-fr-sidebar-account], [data-fr-sidebar-all-accounts]');
      if (!link || !nav.contains(link)) return;
      ev.preventDefault();
      var fa = qs('fr-finance-account');
      if (!fa) {
        window.location.assign(link.getAttribute('href') || window.location.pathname);
        return;
      }
      var aid = link.getAttribute('data-fr-sidebar-account');
      fa.value = aid || '';
      scheduleLoad(0);
    });
  }

  function bindLiveFilters() {
    var ids = ['fr-financial-year', 'fr-date-from', 'fr-date-to', 'fr-finance-account', 'fr-grade', 'fr-source', 'fr-period'];
    ids.forEach(function (id) {
      var el = qs(id);
      if (!el) return;
      el.addEventListener('change', function () {
        if (id === 'fr-financial-year') {
          applyFinancialYearSelection(true);
        } else if (id === 'fr-date-from' || id === 'fr-date-to') {
          clampDateInputsToYear(selectedFinancialYear());
        }
        scheduleLoad();
      });
    });

    var search = qs('fr-search');
    if (search) {
      search.addEventListener('input', scheduleSearchLoad);
      search.addEventListener('search', scheduleSearchLoad);
    }
  }

  function resetFilters() {
    document.querySelectorAll('#fr-filter-grid input, #fr-filter-grid select').forEach(function (el) {
      if (el.tagName === 'SELECT') {
        if (el.id === 'fr-period') {
          el.value = 'monthly';
        } else if (el.id !== 'fr-financial-year') {
          var opts = el.options;
          if (opts.length) el.value = opts[0].value;
        }
      } else {
        el.value = '';
      }
    });
    fillSourceOptions();
    if (sourceEl && groupActive('source')) sourceEl.value = 'all';
    defaultDates();
    updateActiveFilterChips();
    scheduleLoad(0);
  }

  applyFilterProfile();
  readUrlIntoForm();
  var sp = new URLSearchParams(window.location.search);
  var hasUrlFilters =
    sp.has('financial_year_id') ||
    sp.has('date_from') ||
    sp.has('date_to') ||
    sp.has('finance_account_id') ||
    sp.has('grade') ||
    sp.has('source') ||
    sp.has('period') ||
    sp.has('q') ||
    sp.has('ledger') ||
    sp.has('statement');

  if (groupActive('financial_year')) {
    var urlFy = sp.get('financial_year_id');
    var fySel = qs('fr-financial-year');
    if (urlFy && fySel && Array.prototype.some.call(fySel.options, function (o) { return o.value === urlFy; })) {
      fySel.value = urlFy;
      applyFinancialYearSelection(false);
    } else if (fySel && fySel.options.length) {
      if (qs('fr-date-from') && qs('fr-date-from').value && qs('fr-date-to') && qs('fr-date-to').value) {
        applyFinancialYearSelection(false);
      } else {
        defaultFinancialYear();
      }
    }
  } else {
    defaultDates();
  }
  bindLiveFilters();
  bindSidebarAccountLinks();
  updateActiveFilterChips();

  var resetBtn = qs('fr-reset');
  var printBtn = qs('fr-print');
  var printTop = qs('fr-print-top');
  function doPrint() {
    window.print();
  }
  if (resetBtn) resetBtn.addEventListener('click', resetFilters);
  if (printBtn) printBtn.addEventListener('click', doPrint);
  if (printTop) printTop.addEventListener('click', doPrint);

  updateMastheadPeriod();
  syncSidebarAccountHighlight();
  scheduleLoad(hasUrlFilters ? 0 : 80);
})();
