/**
 * Finance overview — paginated students + on-demand summary roll-up.
 */
(function () {
  function readConfig() {
    var el = document.getElementById('fo-page-config');
    if (!el || !el.textContent) return {};
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return {};
    }
  }

  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmtKes(n) {
    if (n === null || n === undefined || isNaN(n)) return 'KES 0.00';
    return 'KES ' + Number(n).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function fmtKesCell(n) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    return fmtKes(n);
  }

  var cfg = readConfig();
  var state = {
    page: 1,
    pages: 1,
    total: 0,
    summaryCache: null,
    summaryLoading: false,
    studentsLoading: false,
    studentRows: [],
  };

  function qs(id) {
    return document.getElementById(id);
  }

  var modeEl = document.getElementById('fo-view-mode');
  var oneClassWrap = document.getElementById('fo-one-class-wrap');
  var oneClassEl = document.getElementById('fo-one-class');
  var viewHint = document.getElementById('fo-view-hint');
  var emptyState = document.getElementById('fo-empty-state');
  var workspace = document.getElementById('fo-workspace');
  var sectionStudent = document.getElementById('fo-section-student-table');
  var sectionSummary = document.getElementById('fo-section-class-summary');
  var levelWrap = document.getElementById('fo-level-wrap');
  var tbody = document.getElementById('fo-student-tbody');
  var summaryTbody = document.getElementById('fo-summary-tbody');
  var searchEl = document.getElementById('fo-search');
  var levelEl = document.getElementById('fo-level');
  var balanceEl = document.getElementById('fo-balance');
  var sortEl = document.getElementById('fo-sort');
  var hintEl = document.getElementById('fo-filter-hint');
  var titleStudent = document.getElementById('fo-section-student-title');
  var cardCount = document.getElementById('fo-card-students-count');
  var cardBilled = document.getElementById('fo-card-billed');
  var cardPaid = document.getElementById('fo-card-paid');
  var cardOut = document.getElementById('fo-card-outstanding');
  var cardStudentsLabel = document.getElementById('fo-card-students-label');
  var listLoading = document.getElementById('fo-list-loading');
  var listError = document.getElementById('fo-list-error');
  var paginationBar = document.getElementById('fo-pagination-bar');
  var pageHint = document.getElementById('fo-page-hint');
  var prevBtn = document.getElementById('fo-prev-page');
  var nextBtn = document.getElementById('fo-next-page');

  var HINTS = {
    '': 'Choose how you want to explore student fee accounts.',
    all: 'Every in-session student with current-term fees. Use search or balance to find who owes fees.',
    by_class: 'One class at a time — pick the level below, then search or filter balances in the list.',
    class_summary: 'One row per class with total billed, paid, and outstanding (no student names).',
  };

  var VIEW_LABELS = {
    '': 'Report view',
    all: 'All students',
    by_class: 'One class',
    class_summary: 'By class totals',
  };

  function setCards(totals, label) {
    if (!totals) return;
    if (cardStudentsLabel && label) cardStudentsLabel.textContent = label;
    if (cardCount) cardCount.textContent = String(totals.student_count != null ? totals.student_count : 0);
    if (cardBilled) cardBilled.textContent = fmtKes(totals.sum_total_amount);
    if (cardPaid) cardPaid.textContent = fmtKes(totals.sum_paid_amount);
    if (cardOut) cardOut.textContent = fmtKes(totals.total_outstanding);
  }

  function setLoading(on) {
    state.studentsLoading = on;
    if (listLoading) listLoading.classList.toggle('hidden', !on);
    if (prevBtn) prevBtn.disabled = on || state.page <= 1;
    if (nextBtn) nextBtn.disabled = on || state.page >= state.pages;
  }

  function updatePagination() {
    if (!paginationBar) return;
    var mode = modeEl ? modeEl.value : '';
    if (mode === 'class_summary' || !mode) {
      paginationBar.classList.add('hidden');
      return;
    }
    paginationBar.classList.remove('hidden');
    if (pageHint) {
      pageHint.textContent =
        state.total > 0
          ? 'Page ' + state.page + ' of ' + state.pages + ' · ' + state.total + ' student(s)'
          : '';
    }
    var nav = document.getElementById('fo-page-nav');
    if (nav) nav.classList.toggle('hidden', state.pages <= 1);
    if (prevBtn) prevBtn.disabled = state.studentsLoading || state.page <= 1;
    if (nextBtn) nextBtn.disabled = state.studentsLoading || state.page >= state.pages;
  }

  function buildQuery(page) {
    var p = new URLSearchParams();
    p.set('page', String(page || 1));
    p.set('per_page', '50');
    p.set('sort', 'name_asc');
    var q = searchEl && searchEl.value.trim();
    var grade = '';
    var mode = modeEl ? modeEl.value : '';
    if (mode === 'by_class' && oneClassEl && oneClassEl.value) {
      grade = oneClassEl.value;
    } else if (levelEl && levelEl.value) {
      grade = levelEl.value;
    }
    if (q) p.set('q', q);
    if (grade) p.set('grade', grade);
    return p.toString();
  }

  function joinDashPath(base, segment) {
    return String(base || '').replace(/\/+$/, '') + '/' + encodeURIComponent(segment || '');
  }

  function renderStudentRow(s, idx) {
    var bal = s.balance;
    var balClass =
      bal != null && bal > 0
        ? 'text-amber-700 dark:text-amber-400'
        : bal != null
          ? 'text-green-700 dark:text-green-400'
          : '';
    var inv = joinDashPath(cfg.invoiceBase, s.student_id) + '?format=pdf&download=true';
    var rec = '';
    if (s.latest_payment_id) {
      rec =
        joinDashPath(cfg.receiptBase, s.student_id) +
        '/' +
        encodeURIComponent(s.latest_payment_id) +
        '?format=pdf&download=true';
    }
    return (
      '<tr class="hover:bg-gray-50 dark:hover:bg-gray-700/30 fo-student-row" data-fo-row data-idx="' +
      idx +
      '" data-class="' +
      esc(s.class_name) +
      '" data-search="' +
      esc((s.full_name + ' ' + s.student_id).toLowerCase()) +
      '" data-balance="' +
      (bal == null ? '' : bal) +
      '" data-total="' +
      (s.total_amount == null ? '' : s.total_amount) +
      '" data-paid="' +
      (s.paid_amount == null ? '' : s.paid_amount) +
      '">' +
      '<td data-label="Class">' +
      esc(s.class_name) +
      '</td>' +
      '<td data-label="Student"><span class="font-semibold">' +
      esc(s.full_name) +
      '</span><span class="fr-mono block" style="color:var(--fr-muted)">' +
      esc(s.student_id) +
      '</span></td>' +
      '<td class="text-right tabular-nums" data-label="Total">' +
      fmtKesCell(s.total_amount) +
      '</td>' +
      '<td class="text-right tabular-nums" data-label="Paid" style="color:#047857">' +
      fmtKesCell(s.paid_amount) +
      '</td>' +
      '<td class="text-right tabular-nums font-semibold ' +
      balClass +
      '" data-label="Balance">' +
      fmtKesCell(s.balance) +
      '</td>' +
      '<td class="text-center" data-label="Invoice"><a href="' +
      esc(inv) +
      '" download class="inline-flex w-10 h-10 items-center justify-center rounded-lg border text-brand-primary" title="Download PDF invoice"><i class="fas fa-file-pdf"></i></a></td>' +
      '<td class="text-center" data-label="Receipt">' +
      (rec
        ? '<a href="' +
          esc(rec) +
          '" download class="inline-flex w-10 h-10 items-center justify-center rounded-lg border text-green-700" title="Download PDF receipt"><i class="fas fa-receipt"></i></a>'
        : '<span class="inline-flex w-10 h-10 items-center justify-center rounded-lg border border-dashed text-gray-300" title="No payments"><i class="fas fa-receipt"></i></span>') +
      '</td></tr>'
    );
  }

  function parseBalance(tr) {
    var raw = tr.getAttribute('data-balance');
    if (raw === null || raw === '') return null;
    var n = parseFloat(raw, 10);
    return isNaN(n) ? null : n;
  }

  function parseNumAttr(tr, name) {
    var raw = tr.getAttribute(name);
    if (raw === null || raw === '') return null;
    var n = parseFloat(raw, 10);
    return isNaN(n) ? null : n;
  }

  function matchesFilters(tr) {
    var q = ((searchEl && searchEl.value) || '').trim().toLowerCase();
    if (q) {
      var hay = (tr.getAttribute('data-search') || '').toLowerCase();
      if (hay.indexOf(q) === -1) return false;
    }
    var level = (levelEl ? levelEl.value : '') || '';
    if (level && (tr.getAttribute('data-class') || '') !== level) return false;
    var mode = (balanceEl ? balanceEl.value : '') || 'all';
    var b = parseBalance(tr);
    if (mode === 'outstanding') {
      if (b === null || b <= 0) return false;
    } else if (mode === 'clear') {
      if (b !== null && b > 0) return false;
    }
    return true;
  }

  function compareBalanceAsc(a, b) {
    var av = parseBalance(a);
    var bv = parseBalance(b);
    if (av === null && bv === null) return 0;
    if (av === null) return 1;
    if (bv === null) return -1;
    return av - bv;
  }

  function refreshClientFilters() {
    if (!tbody) return;
    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr[data-fo-row]'));
    var total = rows.length;
    var matched = rows.filter(matchesFilters);
    var sortMode = (sortEl ? sortEl.value : '') || 'original';
    if (sortMode === 'balance-asc') {
      matched.sort(compareBalanceAsc);
    } else if (sortMode === 'balance-desc') {
      matched.sort(function (a, b) {
        return -compareBalanceAsc(a, b);
      });
    } else {
      matched.sort(function (a, b) {
        return parseInt(a.getAttribute('data-idx') || '0', 10) - parseInt(b.getAttribute('data-idx') || '0', 10);
      });
    }
    var unmatched = rows.filter(function (tr) {
      return matched.indexOf(tr) === -1;
    });
    matched.concat(unmatched).forEach(function (tr) {
      tbody.appendChild(tr);
    });
    matched.forEach(function (tr) {
      tr.classList.remove('hidden');
    });
    unmatched.forEach(function (tr) {
      tr.classList.add('hidden');
    });
    if (hintEl) {
      var onPage = state.total;
      hintEl.textContent =
        matched.length === total
          ? 'Showing all ' + total + ' on this page' +
            (onPage < state.total ? ' (page ' + state.page + ' of ' + state.pages + ')' : '') +
            '. Balance filter applies to this page.'
          : 'Showing ' + matched.length + ' of ' + total + ' on this page. Balance filter applies to this page.';
    }
    var n = 0,
      st = 0,
      sp = 0,
      so = 0;
    matched.forEach(function (tr) {
      n += 1;
      var t = parseNumAttr(tr, 'data-total');
      var p = parseNumAttr(tr, 'data-paid');
      var b = parseBalance(tr);
      if (t !== null) st += t;
      if (p !== null) sp += p;
      if (b !== null && b > 0) so += b;
    });
    if (cardCount) cardCount.textContent = String(n);
    if (cardBilled) cardBilled.textContent = fmtKes(st);
    if (cardPaid) cardPaid.textContent = fmtKes(sp);
    if (cardOut) cardOut.textContent = fmtKes(so);
  }

  function renderStudents(list) {
    if (!tbody) return;
    if (!list.length) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="py-10 px-4 text-center text-gray-500">No students on this page.</td></tr>';
      if (hintEl) hintEl.textContent = '';
      return;
    }
    var html = '';
    list.forEach(function (s, i) {
      html += renderStudentRow(s, i);
    });
    tbody.innerHTML = html;
    refreshClientFilters();
  }

  function fetchStudents(page) {
    if (!cfg.studentsApi) return;
    var mode = modeEl ? modeEl.value : '';
    if (mode === 'by_class' && oneClassEl && !oneClassEl.value) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="py-10 text-center text-gray-500">Select a class above.</td></tr>';
      return;
    }
    setLoading(true);
    if (listError) {
      listError.classList.add('hidden');
      listError.textContent = '';
    }
    fetch(cfg.studentsApi + '?' + buildQuery(page), {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        setLoading(false);
        if (!data.success) {
          if (listError) {
            listError.textContent = data.message || 'Could not load';
            listError.classList.remove('hidden');
          }
          renderStudents([]);
          return;
        }
        var meta = data.meta || {};
        state.page = meta.page || 1;
        state.pages = meta.pages || 1;
        state.total = meta.total || 0;
        state.studentRows = data.students || [];
        renderStudents(state.studentRows);
        updatePagination();
      })
      .catch(function () {
        setLoading(false);
        if (listError) {
          listError.textContent = 'Could not load students';
          listError.classList.remove('hidden');
        }
      });
  }

  function renderClassSummaries(summaries) {
    if (!summaryTbody) return;
    if (!summaries || !summaries.length) {
      summaryTbody.innerHTML =
        '<tr><td colspan="5" class="py-10 text-center text-gray-500">No class-level data.</td></tr>';
      return;
    }
    var html = '';
    summaries.forEach(function (c) {
      html +=
        '<tr>' +
        '<td data-label="Class" class="font-semibold">' +
        esc(c.class_name) +
        '</td>' +
        '<td class="text-right tabular-nums" data-label="Students">' +
        c.student_count +
        '</td>' +
        '<td class="text-right tabular-nums" data-label="Billed">' +
        fmtKes(c.sum_total_amount) +
        '</td>' +
        '<td class="text-right tabular-nums" data-label="Paid" style="color:#047857">' +
        fmtKes(c.sum_paid_amount) +
        '</td>' +
        '<td class="text-right tabular-nums font-semibold" data-label="Outstanding" style="color:#b45309">' +
        fmtKes(c.total_outstanding) +
        '</td></tr>';
    });
    summaryTbody.innerHTML = html;
  }

  function fetchSummary(callback) {
    if (!cfg.summaryApi) return;
    if (state.summaryCache) {
      if (callback) callback(state.summaryCache);
      return;
    }
    state.summaryLoading = true;
    if (listLoading) listLoading.classList.remove('hidden');
    fetch(cfg.summaryApi, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        state.summaryLoading = false;
        if (listLoading) listLoading.classList.add('hidden');
        if (data.success) {
          state.summaryCache = data;
          if (callback) callback(data);
        }
      })
      .catch(function () {
        state.summaryLoading = false;
        if (listLoading) listLoading.classList.add('hidden');
      });
  }

  function updateStudentViewChips() {
    var mode = modeEl ? modeEl.value : '';
    var chips = qs('fo-active-filters');
    if (!chips) return;
    if (!mode) {
      chips.classList.add('hidden');
      chips.innerHTML = '';
      return;
    }
    var parts = [VIEW_LABELS[mode] || mode];
    if (mode === 'by_class' && oneClassEl && oneClassEl.value) {
      parts.push(oneClassEl.value);
    }
    if (searchEl && searchEl.value.trim() && (mode === 'all' || mode === 'by_class')) {
      parts.push('Search: “' + searchEl.value.trim() + '”');
    }
    if (balanceEl && balanceEl.value && balanceEl.value !== 'all') {
      var bo = balanceEl.options[balanceEl.selectedIndex];
      if (bo) parts.push(bo.text);
    }
    chips.classList.remove('hidden');
    chips.innerHTML =
      '<span class="text-[0.6875rem] font-semibold uppercase text-slate-500 mr-1">Showing:</span>' +
      parts
        .map(function (p) {
          return '<span class="fr-active-filters__chip">' + esc(p) + '</span>';
        })
        .join('');
  }

  function applyViewMode() {
    var mode = modeEl ? modeEl.value : '';
    if (viewHint) {
      viewHint.textContent = HINTS[mode] || HINTS[''];
    }
    updateStudentViewChips();

    if (!mode) {
      emptyState.classList.remove('hidden');
      workspace.classList.add('hidden');
      return;
    }
    emptyState.classList.add('hidden');
    workspace.classList.remove('hidden');

    if (mode === 'class_summary') {
      if (oneClassWrap) oneClassWrap.classList.add('hidden');
      sectionStudent.classList.add('hidden');
      sectionSummary.classList.remove('hidden');
      if (paginationBar) paginationBar.classList.add('hidden');
      fetchSummary(function (data) {
        setCards(data.totals, 'Students (in session)');
        renderClassSummaries(data.class_summaries);
      });
      return;
    }

    sectionSummary.classList.add('hidden');
    sectionStudent.classList.remove('hidden');

    fetchSummary(function (data) {
      setCards(data.totals, 'Students (in session)');
    });

    if (mode === 'by_class') {
      if (oneClassWrap) oneClassWrap.classList.remove('hidden');
      if (levelWrap) levelWrap.classList.add('hidden');
      var cls = oneClassEl ? oneClassEl.value : '';
      if (levelEl) levelEl.value = cls;
      if (titleStudent) {
        titleStudent.textContent = cls
          ? 'Student fee accounts — ' + cls
          : 'Student fee accounts — pick a class';
      }
      if (!cls) {
        if (tbody) {
          tbody.innerHTML =
            '<tr><td colspan="7" class="py-10 text-center text-gray-500">Select a class above.</td></tr>';
        }
        if (hintEl) hintEl.textContent = 'Select a class above.';
        updatePagination();
        return;
      }
    } else {
      if (oneClassWrap) oneClassWrap.classList.add('hidden');
      if (levelWrap) levelWrap.classList.remove('hidden');
      if (levelEl) levelEl.value = '';
      if (titleStudent) titleStudent.textContent = 'Student fee accounts';
    }

    fetchStudents(1);
  }

  var searchTimer;
  function debouncedFetch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      fetchStudents(1);
    }, 350);
  }

  function bindStudentReportFilters() {
    if (modeEl) modeEl.addEventListener('change', applyViewMode);
    if (oneClassEl) {
      oneClassEl.addEventListener('change', function () {
        updateStudentViewChips();
        applyViewMode();
      });
    }
    if (searchEl) {
      searchEl.addEventListener('input', function () {
        var mode = modeEl ? modeEl.value : '';
        updateStudentViewChips();
        if (mode === 'all' || mode === 'by_class') debouncedFetch();
        else if (mode) refreshClientFilters();
      });
      searchEl.addEventListener('search', function () {
        var mode = modeEl ? modeEl.value : '';
        updateStudentViewChips();
        if (mode === 'all' || mode === 'by_class') debouncedFetch();
        else if (mode) refreshClientFilters();
      });
    }
    if (levelEl) {
      levelEl.addEventListener('change', function () {
        updateStudentViewChips();
        if (modeEl && modeEl.value) fetchStudents(1);
      });
    }
    if (balanceEl) {
      balanceEl.addEventListener('change', function () {
        refreshClientFilters();
        updateStudentViewChips();
      });
    }
    if (sortEl) sortEl.addEventListener('change', refreshClientFilters);
    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        if (state.page > 1) fetchStudents(state.page - 1);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        if (state.page < state.pages) fetchStudents(state.page + 1);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindStudentReportFilters);
  } else {
    bindStudentReportFilters();
  }
})();
