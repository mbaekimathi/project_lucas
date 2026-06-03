/**
 * Paginated student fees register (loaded from /student-fees/students).
 */
(function () {
  function readConfig() {
    var el = document.getElementById('sf-page-config');
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

  function money(n) {
    var x = Number(n) || 0;
    return 'KES ' + x.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatCategoryLabel(cat) {
    var c = String(cat || '').toLowerCase().trim();
    if (!c) return 'Not set';
    if (c === 'self sponsored') return 'Self sponsored';
    if (c === 'sponsored') return 'Sponsored';
    if (c === 'both') return 'Both';
    return c.charAt(0).toUpperCase() + c.slice(1);
  }

  function categoryBadge(cat) {
    var c = String(cat || '').toLowerCase().trim();
    var label = formatCategoryLabel(cat);
    var cls = 'sf-cat-badge sf-cat-badge--neutral';
    if (c === 'self sponsored') cls = 'sf-cat-badge sf-cat-badge--self';
    else if (c === 'sponsored') cls = 'sf-cat-badge sf-cat-badge--sponsored';
    else if (c === 'both') cls = 'sf-cat-badge sf-cat-badge--both';
    return '<span class="' + cls + '" title="Student category">' + esc(label) + '</span>';
  }

  function statusBadge(st) {
    if (st === 'overdue') {
      return '<span class="inline-flex px-2 py-0.5 text-[11px] font-semibold rounded-md bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-200">Overdue</span>';
    }
    if (st === 'pending') {
      return '<span class="inline-flex px-2 py-0.5 text-[11px] font-semibold rounded-md bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200">Pending</span>';
    }
    if (st === 'paid') {
      return '<span class="inline-flex px-2 py-0.5 text-[11px] font-semibold rounded-md bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200">Paid</span>';
    }
    return '<span class="inline-flex px-2 py-0.5 text-[11px] font-semibold rounded-md bg-slate-100 dark:bg-gray-700 text-slate-600 dark:text-slate-300">No structure</span>';
  }

  function dueText(s) {
    var fs = s.fee_structure;
    if (!fs) return { main: '—', cls: 'text-slate-400 dark:text-slate-500' };
    var due = Number(s.total_amount_due || fs.total_amount) || 0;
    return { main: money(due), cls: 'sf-money-cell' };
  }

  function paidText(s) {
    var fs = s.fee_structure;
    if (!fs) return { main: '—', cls: 'text-slate-400 dark:text-slate-500' };
    var paid = Number(s.total_paid) || 0;
    return { main: money(paid), cls: 'sf-money-cell sf-money-cell--paid' };
  }

  function balanceText(s) {
    var fs = s.fee_structure;
    if (!fs) return { main: '—', cls: 'text-slate-400 dark:text-slate-500' };
    var bal = Number(s.balance) || 0;
    if (bal > 0) return { main: money(bal), cls: 'text-red-600 dark:text-red-400' };
    if (bal === 0) return { main: 'KES 0.00', cls: 'text-emerald-600 dark:text-emerald-400' };
    return { main: money(-bal) + ' cr.', cls: 'text-blue-600 dark:text-blue-400' };
  }

  function joinDashPath(base, segment) {
    return String(base || '').replace(/\/+$/, '') + '/' + encodeURIComponent(segment || '');
  }

  function actionButtons(s, cfg) {
    var fs = s.fee_structure;
    var html = '<div class="flex items-center justify-end gap-1">';
    if (fs && cfg.canRecordPayments) {
      html +=
        '<button type="button" class="sf-record-payment inline-flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-300" title="Record payment" ' +
        'data-student-id="' + esc(s.student_id) + '" data-fs-id="' + esc(fs.id) + '" data-name="' + esc(s.full_name) + '" data-due="' + esc(s.total_amount_due || fs.total_amount) + '" data-balance="' + esc(s.balance) + '">' +
        '<i class="fas fa-money-check-alt text-xs"></i></button>';
    }
    html +=
      '<button type="button" class="sf-view-tx inline-flex h-8 w-8 items-center justify-center rounded-lg bg-sky-100 text-sky-700 hover:bg-sky-200 dark:bg-sky-900/50 dark:text-sky-300" title="View transactions" ' +
      'data-student-id="' + esc(s.student_id) + '" data-name="' + esc(s.full_name) + '">' +
      '<i class="fas fa-history text-xs"></i></button>';
    if (cfg.canGenerateInvoices) {
      var invPdf = joinDashPath(cfg.invoiceBase, s.student_id) + '?format=pdf&download=true';
      var invView = joinDashPath(cfg.invoiceBase, s.student_id);
      html +=
        '<a href="' + esc(invPdf) + '" download class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-violet-100 text-violet-700 hover:bg-violet-200 dark:bg-violet-900/50 dark:text-violet-300" title="Download invoice PDF">' +
        '<i class="fas fa-file-pdf text-xs"></i></a>';
      html +=
        '<a href="' + esc(invView) + '" target="_blank" rel="noopener" class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-violet-600 hover:bg-violet-50 dark:text-violet-300 dark:hover:bg-violet-950/40 ring-1 ring-violet-200/80 dark:ring-violet-800/60" title="View invoice">' +
        '<i class="fas fa-file-invoice text-xs"></i></a>';
    }
    html += '</div>';
    return html;
  }

  function tableRow(s, cfg) {
    var level = (s.academic_level && s.academic_level.level_name) || s.current_grade || '—';
    var due = dueText(s);
    var paid = paidText(s);
    var bal = balanceText(s);
    var statusMob = '<div class="sm:hidden mt-1.5">' + statusBadge(s.payment_status) + '</div>';
    var dueMob = s.fee_structure
      ? '<div class="md:hidden text-[11px] text-[var(--acc-muted)] mt-1">Due ' + esc(due.main) + ' · Paid ' + esc(paid.main) + '</div>'
      : '';

    return (
      '<tr class="student-row hover:bg-teal-50/50 dark:hover:bg-teal-950/10 transition-colors" ' +
      'data-student-id="' + esc(s.student_id) + '" data-student-name="' + esc((s.full_name || '').toLowerCase()) + '" data-grade="' + esc((s.current_grade || '').toLowerCase()) + '" data-category="' + esc((s.student_category || '').toLowerCase()) + '">' +
      '<td class="px-3 sm:px-4 lg:px-5 py-3 min-w-[10rem]">' +
      '<div class="text-sm font-semibold text-[var(--acc-ink)] leading-snug">' + esc(s.full_name) + '</div>' +
      '<div class="sf-student-meta">' +
      '<span class="text-xs text-[var(--acc-muted)] font-mono">' + esc(s.student_id) + '</span>' +
      categoryBadge(s.student_category) +
      '</div>' +
      '<div class="sm:hidden text-[11px] text-[var(--acc-muted)] mt-0.5">' + esc(level) + '</div>' +
      dueMob +
      statusMob +
      '</td>' +
      '<td class="hidden sm:table-cell px-3 sm:px-4 lg:px-5 py-3 text-sm text-[var(--acc-ink)] whitespace-nowrap">' + esc(level) + '</td>' +
      '<td class="hidden md:table-cell sf-col-money px-3 sm:px-4 lg:px-5 py-3 whitespace-nowrap">' +
      '<div class="' + due.cls + '">' + esc(due.main) + '</div></td>' +
      '<td class="hidden md:table-cell sf-col-money px-3 sm:px-4 lg:px-5 py-3 whitespace-nowrap">' +
      '<div class="' + paid.cls + '">' + esc(paid.main) + '</div></td>' +
      '<td class="sf-col-balance px-3 sm:px-4 lg:px-5 py-3 whitespace-nowrap">' +
      '<div class="sf-balance-cell ' + bal.cls + '">' + esc(bal.main) + '</div></td>' +
      '<td class="hidden sm:table-cell px-3 sm:px-4 lg:px-5 py-3 text-center">' + statusBadge(s.payment_status) + '</td>' +
      '<td class="px-3 sm:px-4 lg:px-5 py-3 text-right">' + actionButtons(s, cfg) + '</td></tr>'
    );
  }

  function emptyRow(colspan, title, sub) {
    return (
      '<tr><td colspan="' + colspan + '" class="px-6 py-14 text-center text-gray-500">' +
      '<i class="fas fa-inbox text-4xl mb-3 block text-emerald-300"></i>' +
      '<p class="text-sm font-semibold">' + esc(title) + '</p>' +
      '<p class="text-xs mt-1">' + esc(sub) + '</p></td></tr>'
    );
  }

  var state = {
    cfg: readConfig(),
    page: 1,
    pages: 1,
    total: 0,
    loading: false,
    searchTimer: null,
  };

  function qs(id) {
    return document.getElementById(id);
  }

  function setLoading(on) {
    state.loading = on;
    var ld = qs('sfListLoading');
    if (ld) ld.classList.toggle('hidden', !on);
  }

  function updatePagination() {
    var bar = qs('sfPaginationBar');
    var hint = qs('sfPageHint');
    var nav = qs('sfPageNav');
    var prev = qs('sfPrevPage');
    var next = qs('sfNextPage');
    if (!bar) return;
    if (state.total > 0 || state.loading) {
      bar.classList.remove('hidden');
    } else {
      bar.classList.add('hidden');
    }
    if (hint) {
      hint.textContent =
        state.total > 0
          ? 'Page ' + state.page + ' of ' + state.pages + ' · ' + state.total + ' student(s) in session'
          : '';
    }
    if (nav) nav.classList.toggle('hidden', state.pages <= 1);
    if (prev) prev.disabled = state.page <= 1 || state.loading;
    if (next) next.disabled = state.page >= state.pages || state.loading;
  }

  function buildQuery(page) {
    var p = new URLSearchParams();
    p.set('page', String(page || 1));
    p.set('per_page', '50');
    p.set('sort', 'name_asc');
    var search = qs('searchStudents');
    var grade = qs('filterGrade');
    var cat = qs('filterCategory');
    if (search && search.value.trim()) p.set('q', search.value.trim());
    if (grade && grade.value) p.set('grade', grade.value);
    if (cat && cat.value) p.set('category', cat.value);
    return p.toString();
  }

  function renderStudents(list) {
    var tbody = qs('studentsTableBody');
    if (!tbody) return;
    if (!list.length) {
      var title = state.total === 0 ? 'No students found' : 'No students match your filters';
      var sub =
        state.total === 0
          ? 'Students will appear here once they are registered.'
          : 'Try different search words or filters.';
      tbody.innerHTML = emptyRow(7, title, sub);
      return;
    }
    var html = '';
    list.forEach(function (s) {
      html += tableRow(s, state.cfg);
    });
    tbody.innerHTML = html;
  }

  function fetchStudents(page) {
    if (!state.cfg.studentsApi) return;
    setLoading(true);
    qs('sfListError') && qs('sfListError').classList.add('hidden');
    fetch(state.cfg.studentsApi + '?' + buildQuery(page), {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        setLoading(false);
        if (!data.success) {
          if (qs('sfListError')) {
            qs('sfListError').textContent = data.message || 'Could not load students';
            qs('sfListError').classList.remove('hidden');
          }
          renderStudents([]);
          return;
        }
        var meta = data.meta || {};
        state.page = meta.page || 1;
        state.pages = meta.pages || 1;
        state.total = meta.total || 0;
        renderStudents(data.students || []);
        updatePagination();
      })
      .catch(function () {
        setLoading(false);
        if (qs('sfListError')) {
          qs('sfListError').textContent = 'Could not load students';
          qs('sfListError').classList.remove('hidden');
        }
        renderStudents([]);
      });
  }

  window.sfReloadList = function (page) {
    fetchStudents(page != null ? page : state.page);
  };

  function bindActions() {
    document.body.addEventListener('click', function (e) {
      var pay = e.target.closest('.sf-record-payment');
      if (pay && window.Alpine && Alpine.store('paymentModal')) {
        Alpine.store('paymentModal').openPaymentModal(
          pay.dataset.studentId,
          parseInt(pay.dataset.fsId, 10),
          pay.dataset.name || '',
          parseFloat(pay.dataset.due) || 0,
          parseFloat(pay.dataset.balance) || 0
        );
        return;
      }
      var tx = e.target.closest('.sf-view-tx');
      if (tx && window.Alpine && Alpine.store('transactionsModal')) {
        Alpine.store('transactionsModal').openTransactionsModal(tx.dataset.studentId, tx.dataset.name || '');
      }
    });
  }

  function scheduleSearch() {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(function () {
      fetchStudents(1);
    }, 350);
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindActions();
    var searchInput = qs('searchStudents');
    var filterGrade = qs('filterGrade');
    var filterCategory = qs('filterCategory');
    var prev = qs('sfPrevPage');
    var next = qs('sfNextPage');

    if (searchInput) {
      searchInput.addEventListener('input', function () {
        if (typeof updateActiveFilters === 'function') updateActiveFilters();
        scheduleSearch();
      });
    }
    if (filterGrade) {
      filterGrade.addEventListener('change', function () {
        if (typeof updateActiveFilters === 'function') updateActiveFilters();
        fetchStudents(1);
      });
    }
    if (filterCategory) {
      filterCategory.addEventListener('change', function () {
        if (typeof updateActiveFilters === 'function') updateActiveFilters();
        fetchStudents(1);
      });
    }
    if (prev) prev.addEventListener('click', function () {
      if (state.page > 1) fetchStudents(state.page - 1);
    });
    if (next) next.addEventListener('click', function () {
      if (state.page < state.pages) fetchStudents(state.page + 1);
    });

    fetchStudents(1);
  });
})();
