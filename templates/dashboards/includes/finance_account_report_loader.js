/**
 * Per-account finance reports — live filters without full page reload.
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

  function updateMastheadMeta(periodLabel, generatedAt) {
    var periodEl = qs('acr-masthead-period');
    var genEl = qs('acr-masthead-generated');
    if (periodEl) periodEl.textContent = periodLabel || mastheadPeriodLabel();
    if (genEl && generatedAt) genEl.textContent = generatedAt;
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
    body.setAttribute('aria-busy', 'true');
    body.classList.add('acr-report-body--loading');

    updateActiveFilterChips();
    updateMastheadMeta(mastheadPeriodLabel(), null);
    syncUrl();

    var url = cfg.dataApi + '?' + paramsFromForm().toString();
    var fetchOpts = {
      credentials: 'same-origin',
      headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    };
    if (fetchAbort) fetchOpts.signal = fetchAbort.signal;

    fetch(url, fetchOpts)
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, body: j };
        });
      })
      .then(function (res) {
        if (loading) loading.classList.add('hidden');
        body.classList.remove('acr-report-body--loading');
        body.removeAttribute('aria-busy');
        if (!res.ok || !res.body.success) {
          if (errEl) {
            errEl.textContent = (res.body && res.body.message) || 'Could not load report.';
            errEl.classList.remove('hidden');
          }
          return;
        }
        body.innerHTML = res.body.html || '';
        updateMastheadMeta(res.body.report_period_label, res.body.report_generated_at);
        updateActiveFilterChips();
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        if (loading) loading.classList.add('hidden');
        body.classList.remove('acr-report-body--loading');
        body.removeAttribute('aria-busy');
        if (errEl) {
          errEl.textContent = 'Network error loading report.';
          errEl.classList.remove('hidden');
        }
      });
  }

  function scheduleLoad(delay) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadReport, delay == null ? DEBOUNCE_MS : delay);
  }

  function bindLiveFilters() {
    var form = qs('acr-report-filters');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        scheduleLoad(0);
      });
    }

    var fySel = qs('acr-financial-year');
    if (fySel) {
      fySel.addEventListener('change', function () {
        applyBounds(true);
        scheduleLoad();
      });
    }

    ['acr-date-from', 'acr-date-to'].forEach(function (id) {
      var el = qs(id);
      if (!el) return;
      el.addEventListener('change', function () {
        applyBounds(false);
        scheduleLoad();
      });
    });

    var resetBtn = qs('acr-reset-filters');
    if (resetBtn) {
      resetBtn.addEventListener('click', function (e) {
        e.preventDefault();
        defaultFinancialYear();
        scheduleLoad(0);
      });
    }
  }

  readUrlIntoForm();
  var sp = new URLSearchParams(window.location.search);
  var hasUrlFilters = sp.has('financial_year_id') || sp.has('date_from') || sp.has('date_to');

  if (qs('acr-financial-year')) {
    if (hasUrlFilters || cfg.skipInitialFetch) {
      applyBounds(false);
    } else {
      defaultFinancialYear();
    }
  }

  bindLiveFilters();
  updateActiveFilterChips();
  updateMastheadMeta(mastheadPeriodLabel(), null);

  if (!cfg.skipInitialFetch && !hasUrlFilters) {
    scheduleLoad(0);
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

  function printAccountReport() {
    if (!document.querySelector('.acr-report-page')) {
      window.print();
      return;
    }
    if (!reportHasPrintableData()) {
      window.alert('No report data to print for the selected period.');
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

  window.printAccountReport = printAccountReport;

  window.addEventListener('beforeprint', function () {
    if (window.__acrIframePrintActive) return;
    if (!document.querySelector('.acr-report-page')) return;
    if (document.documentElement.classList.contains('acr-pcb-print-doc')) return;
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
