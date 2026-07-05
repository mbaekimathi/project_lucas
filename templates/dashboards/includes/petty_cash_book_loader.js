/**
 * Petty cash book — extends account report live filters with finance_account_id.
 */
(function () {
  function readConfig() {
    var el = document.getElementById('acr-page-config');
    if (!el || !el.textContent) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  var cfg = readConfig();
  if (!cfg || !cfg.dataApi) return;

  var DEBOUNCE_MS = 280;
  var debounceTimer = null;
  var fetchAbort = null;

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

  function todayIso() {
    var now = new Date();
    var y = now.getFullYear();
    var m = String(now.getMonth() + 1).padStart(2, '0');
    var d = String(now.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + d;
  }

  function defaultDateToForBounds(b) {
    if (!b || !b.end) return todayIso();
    if (b.isCurrent) {
      var today = todayIso();
      return today <= b.end ? today : b.end;
    }
    return b.end;
  }

  function yearBounds() {
    var fySel = qs('acr-financial-year');
    if (!fySel || !fySel.value) return null;
    var opt = fySel.options[fySel.selectedIndex];
    if (!opt) return null;
    return {
      start: opt.getAttribute('data-start'),
      end: opt.getAttribute('data-end'),
      isCurrent: opt.getAttribute('data-is-current') === '1',
      label: (opt.textContent || '').split('—')[0].trim(),
    };
  }

  function applyBounds(resetDates) {
    var b = yearBounds();
    var df = qs('acr-date-from');
    var dt = qs('acr-date-to');
    if (!b || !b.start || !b.end) {
      updateFyHint(null);
      return;
    }
    if (df) {
      df.min = b.start;
      df.max = b.end;
    }
    if (dt) {
      dt.min = b.start;
      dt.max = b.end;
    }
    if (resetDates) {
      if (df) df.value = b.start;
      if (dt) dt.value = defaultDateToForBounds(b);
    } else {
      if (df && df.value) {
        if (df.value < b.start) df.value = b.start;
        if (df.value > b.end) df.value = b.end;
      }
      if (dt && dt.value) {
        if (dt.value > b.end) dt.value = b.end;
        if (dt.value < b.start) dt.value = b.start;
      }
    }
    updateFyHint(b);
  }

  function updateFyHint(b) {
    var hint = qs('acr-fy-range-hint');
    if (!hint) return;
    if (!b || !b.start || !b.end) {
      hint.textContent = '';
      return;
    }
    hint.textContent = 'Dates limited to ' + b.start + ' – ' + b.end;
  }

  function updateActiveFilterChips() {
    var box = qs('acr-active-filters');
    if (!box) return;
    var chips = [];
    var b = yearBounds();
    if (b && b.label) chips.push(b.label);
    var df = qs('acr-date-from');
    var dt = qs('acr-date-to');
    if (df && df.value && dt && dt.value) {
      chips.push(df.value + ' → ' + dt.value);
    }
    if (!chips.length) {
      box.classList.add('hidden');
      box.innerHTML = '';
      return;
    }
    box.classList.remove('hidden');
    box.innerHTML =
      '<span class="acr-active-filters__label">Showing:</span>' +
      chips
        .map(function (c) {
          return '<span class="acr-active-filters__chip">' + esc(c) + '</span>';
        })
        .join('');
  }

  function mastheadPeriodLabel() {
    var df = qs('acr-date-from');
    var dt = qs('acr-date-to');
    var from = df && df.value ? df.value : '';
    var to = dt && dt.value ? dt.value : '';
    if (from && to) return from + ' to ' + to;
    if (from) return 'From ' + from;
    if (to) return 'Until ' + to;
    return 'All dates';
  }

  function paramsFromForm() {
    var p = new URLSearchParams();
    if (cfg.financeAccountId != null) {
      p.set('finance_account_id', String(cfg.financeAccountId));
    }
    var fy = qs('acr-financial-year');
    var df = qs('acr-date-from');
    var dt = qs('acr-date-to');
    if (fy && fy.value) p.set('financial_year_id', fy.value);
    if (df && df.value) p.set('date_from', df.value);
    if (dt && dt.value) p.set('date_to', dt.value);
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
    set('acr-financial-year', 'financial_year_id');
    set('acr-date-from', 'date_from');
    set('acr-date-to', 'date_to');
  }

  function defaultFinancialYear() {
    var fySel = qs('acr-financial-year');
    if (!fySel || !fySel.options.length) return;
    var defaultId = cfg.defaultFinancialYearId != null ? String(cfg.defaultFinancialYearId) : '';
    if (defaultId && Array.prototype.some.call(fySel.options, function (o) { return o.value === defaultId; })) {
      fySel.value = defaultId;
    }
    applyBounds(true);
  }

  function syncPrintLetterhead() {
    if (typeof window.syncAcrPrintLetterhead === 'function') {
      window.syncAcrPrintLetterhead();
    }
  }

  function updateMastheadMeta(periodLabel, generatedAt, accountName) {
    var periodEl = qs('acr-masthead-period');
    var genEl = qs('acr-masthead-generated');
    var acctEl = qs('acr-masthead-account');
    if (periodEl) periodEl.textContent = periodLabel || mastheadPeriodLabel();
    if (genEl && generatedAt) genEl.textContent = generatedAt;
    if (acctEl && accountName) acctEl.textContent = accountName;
    syncPrintLetterhead();
  }

  function loadReport() {
    var body = qs('acr-report-body');
    var loading = qs('acr-report-loading');
    var errEl = qs('acr-report-error');
    if (!body) return;

    if (fetchAbort) {
      fetchAbort.abort();
      fetchAbort = null;
    }
    fetchAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;

    if (loading) loading.classList.remove('hidden');
    if (errEl) {
      errEl.classList.add('hidden');
      errEl.textContent = '';
    }

    var url = cfg.dataApi + '?' + paramsFromForm().toString();
    var opts = { credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (fetchAbort) opts.signal = fetchAbort.signal;

    fetch(url, opts)
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (loading) loading.classList.add('hidden');
        if (!result.ok || !result.data.success) {
          if (errEl) {
            errEl.textContent = (result.data && result.data.message) || 'Could not update book.';
            errEl.classList.remove('hidden');
          }
          return;
        }
        body.innerHTML = result.data.html || '';
        updateMastheadMeta(
          result.data.report_period_label,
          result.data.report_generated_at,
          result.data.account_name
        );
        syncUrl();
        updateActiveFilterChips();
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        if (loading) loading.classList.add('hidden');
        if (errEl) {
          errEl.textContent = 'Network error while updating book.';
          errEl.classList.remove('hidden');
        }
      });
  }

  function scheduleLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadReport, DEBOUNCE_MS);
  }

  function resetFilters() {
    var fySel = qs('acr-financial-year');
    if (fySel && cfg.defaultFinancialYearId != null) {
      fySel.value = String(cfg.defaultFinancialYearId);
    }
    applyBounds(true);
    scheduleLoad();
  }

  readUrlIntoForm();
  defaultFinancialYear();
  updateActiveFilterChips();

  ['acr-financial-year', 'acr-date-from', 'acr-date-to'].forEach(function (id) {
    var el = qs(id);
    if (el) el.addEventListener('change', scheduleLoad);
  });

  var resetBtn = qs('acr-reset-filters');
  if (resetBtn) resetBtn.addEventListener('click', resetFilters);

  if (!cfg.skipInitialFetch) {
    scheduleLoad();
  }

  function reportHasPrintableData() {
    var body = qs('acr-report-body');
    if (!body) return false;
    return !!body.querySelector('.acr-report-section .acr-table tbody tr, .acr-report-section table tbody tr');
  }

  function printDocumentTitle() {
    var bits = [];
    var title = document.getElementById('acr-print-title');
    var acct = document.getElementById('acr-print-account');
    var period = document.getElementById('acr-print-period');
    if (title && title.textContent) bits.push(title.textContent.trim());
    if (acct && acct.textContent) bits.push(acct.textContent.trim());
    if (period && period.textContent) bits.push(period.textContent.trim());
    return bits.join(' — ');
  }

  function printPettyCashBook() {
    if (!reportHasPrintableData()) {
      window.alert('No petty cash book data to print for the selected period.');
      return;
    }
    var nextTitle = printDocumentTitle();
    if (typeof window.printAccountsInFrame === 'function') {
      window.printAccountsInFrame({
        title: nextTitle || document.title,
        htmlClass: 'acr-accounts-print acr-report-print-doc',
        bodyClass: 'acr-accounts-print acr-report-print-doc',
        collect: window.collectAcrAccountReportPrintHtml,
      });
      return;
    }
    syncPrintLetterhead();
    if (typeof window.pinAccountsPrintFooters === 'function') {
      window.pinAccountsPrintFooters();
    }
    var prevTitle = document.title;
    if (nextTitle) document.title = nextTitle;
    document.documentElement.classList.add('acr-report-print-doc', 'acr-accounts-print');
    window.print();
    window.setTimeout(function () {
      document.documentElement.classList.remove('acr-report-print-doc', 'acr-accounts-print');
      if (typeof window.unpinAccountsPrintFooters === 'function') {
        window.unpinAccountsPrintFooters();
      }
      document.title = prevTitle;
    }, 500);
  }

  window.printPettyCashBook = printPettyCashBook;
  window.printAccountReport = printPettyCashBook;

  window.addEventListener('beforeprint', function () {
    if (window.__acrIframePrintActive) return;
    if (!document.querySelector('.acr-pcb-page')) return;
    if (!document.getElementById('acr-pcb-book-section')) return;
    syncPrintLetterhead();
    document.documentElement.classList.add('acr-report-print-doc', 'acr-accounts-print');
    if (typeof window.pinAccountsPrintFooters === 'function') {
      window.pinAccountsPrintFooters();
    }
  });
  window.addEventListener('afterprint', function () {
    document.documentElement.classList.remove('acr-report-print-doc', 'acr-accounts-print');
    if (typeof window.unpinAccountsPrintFooters === 'function') {
      window.unpinAccountsPrintFooters();
    }
  });
})();
