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

  function moneyShort(n) {
    var x = Number(n) || 0;
    return 'KES ' + x.toLocaleString('en-KE', { maximumFractionDigits: 0 });
  }

  function feeStructureDueMeta(fs) {
    if (!fs) return '';
    var html = '';
    if (fs.fee_name) {
      html += '<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">' + esc(fs.fee_name) + '</div>';
    }
    var bits = [];
    if (fs.finance_account_name) bits.push(esc(fs.finance_account_name));
    if (fs.term_name) bits.push(esc(fs.term_name));
    if (bits.length) {
      html += '<div class="text-[11px] text-gray-400 dark:text-gray-500 mt-0.5">' + bits.join(' · ') + '</div>';
    }
    return html;
  }

  function statusBadge(st) {
    if (st === 'overdue') {
      return '<span class="inline-flex px-2.5 py-1 text-xs font-bold rounded-full bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200 ring-1 ring-red-200/90 dark:ring-red-800/60">Overdue</span>';
    }
    if (st === 'pending') {
      return '<span class="inline-flex px-2.5 py-1 text-xs font-bold rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-900 dark:text-amber-200 ring-1 ring-amber-200/90 dark:ring-amber-800/60">Pending</span>';
    }
    if (st === 'paid') {
      return '<span class="inline-flex px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-900 dark:text-emerald-200 ring-1 ring-emerald-200/90 dark:ring-emerald-800/60">Paid</span>';
    }
    return '<span class="inline-flex px-2.5 py-1 text-xs font-bold rounded-full bg-slate-100 dark:bg-gray-700 text-slate-600 dark:text-slate-300 ring-1 ring-slate-200 dark:ring-gray-600">No structure</span>';
  }

  function mobileBorder(st) {
    if (st === 'overdue') return 'border-l-red-500 dark:border-l-red-400';
    if (st === 'pending') return 'border-l-amber-400 dark:border-l-amber-500';
    if (st === 'paid') return 'border-l-emerald-500 dark:border-l-emerald-400';
    return 'border-l-slate-300 dark:border-l-slate-600';
  }

  function balanceHtml(s) {
    var fs = s.fee_structure;
    if (!fs) {
      return '<div class="text-sm font-semibold text-gray-400 dark:text-gray-500">KES 0.00</div>';
    }
    var bal = Number(s.balance) || 0;
    if (bal > 0) {
      return '<div class="text-sm font-semibold text-red-600 dark:text-red-400">' + money(bal) + '</div>';
    }
    if (bal === 0) {
      return '<div class="text-sm font-semibold text-green-600 dark:text-green-400">KES 0.00</div>';
    }
    return '<div class="text-sm font-semibold text-blue-600 dark:text-blue-400">' + money(-bal) + ' (Overpaid)</div>';
  }

  function joinDashPath(base, segment) {
    return String(base || '').replace(/\/+$/, '') + '/' + encodeURIComponent(segment || '');
  }

  function actionButtons(s, cfg) {
    var fs = s.fee_structure;
    var html = '<div class="flex items-center justify-end gap-1.5">';
    if (fs && cfg.canRecordPayments) {
      html +=
        '<button type="button" class="sf-record-payment inline-flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-300 shadow-sm" title="Record Payment" ' +
        'data-student-id="' + esc(s.student_id) + '" data-fs-id="' + esc(fs.id) + '" data-name="' + esc(s.full_name) + '" data-due="' + esc(s.total_amount_due || fs.total_amount) + '" data-balance="' + esc(s.balance) + '">' +
        '<i class="fas fa-money-check-alt text-sm"></i></button>';
    }
    html +=
      '<button type="button" class="sf-view-tx inline-flex h-9 w-9 items-center justify-center rounded-xl bg-sky-100 text-sky-700 hover:bg-sky-200 dark:bg-sky-900/50 dark:text-sky-300 shadow-sm" title="View Transactions" ' +
      'data-student-id="' + esc(s.student_id) + '" data-name="' + esc(s.full_name) + '">' +
      '<i class="fas fa-eye text-sm"></i></button>';
    if (cfg.canGenerateInvoices) {
      var invPdf = joinDashPath(cfg.invoiceBase, s.student_id) + '?format=pdf&download=true';
      var invView = joinDashPath(cfg.invoiceBase, s.student_id);
      html +=
        '<a href="' + esc(invPdf) + '" download class="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-violet-100 text-violet-700 hover:bg-violet-200 dark:bg-violet-900/50 dark:text-violet-300 shadow-sm" title="Download PDF invoice">' +
        '<i class="fas fa-file-pdf text-sm"></i></a>';
      html +=
        '<a href="' + esc(invView) + '" target="_blank" rel="noopener" class="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-violet-50 text-violet-600 hover:bg-violet-100 dark:bg-violet-950/40 dark:text-violet-300 shadow-sm ring-1 ring-violet-200/80 dark:ring-violet-800/60" title="View / print invoice">' +
        '<i class="fas fa-file-invoice text-sm"></i></a>';
    }
    html += '</div>';
    return html;
  }

  function desktopRow(s, cfg, idx) {
    var fs = s.fee_structure;
    var level = (s.academic_level && s.academic_level.level_name) || s.current_grade || '';
    var dueBlock = '';
    if (fs) {
      dueBlock =
        '<div class="text-sm font-semibold text-gray-900 dark:text-white">' + money(s.total_amount_due || fs.total_amount) + '</div>';
      dueBlock += feeStructureDueMeta(fs);
      if ((s.previous_term_balance || 0) > 0) {
        dueBlock += '<div class="text-xs text-orange-600 dark:text-orange-400 mt-0.5">Balance from last term: ' + money(s.previous_term_balance) + '</div>';
      }
    } else {
      dueBlock = '<div class="text-sm text-gray-400 dark:text-gray-500 italic">No fee structure</div>';
    }
    var paidBlock =
      '<div class="text-sm font-semibold text-green-600 dark:text-green-400">' + money(s.total_paid || 0) + '</div>';
    if ((s.carry_forward || 0) > 0) {
      paidBlock += '<div class="text-xs text-blue-600 dark:text-blue-400 mt-0.5">+ ' + money(s.carry_forward) + ' (Carry Forward)</div>';
    }
    var cat = s.student_category ? '<span class="px-2 py-0.5 text-xs font-semibold rounded bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300 capitalize">' + esc(s.student_category) + '</span>' : '';
    var gradeBadge = level
      ? '<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">' + esc(level) + '</span>'
      : '';

    return (
      '<tr class="student-row odd:bg-white even:bg-emerald-50/40 dark:odd:bg-gray-800 dark:even:bg-emerald-950/15 hover:bg-emerald-50/70 transition-colors" ' +
      'data-student-id="' + esc(s.student_id) + '" data-student-name="' + esc((s.full_name || '').toLowerCase()) + '" data-grade="' + esc((s.current_grade || '').toLowerCase()) + '" data-category="' + esc((s.student_category || '').toLowerCase()) + '">' +
      '<td class="px-4 sm:px-6 py-4"><div class="flex items-center"><div class="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center flex-shrink-0"><i class="fas fa-user-graduate text-white text-sm"></i></div>' +
      '<div class="ml-3 min-w-0"><div class="text-sm font-medium text-gray-900 dark:text-white">' + esc(s.full_name) + '</div>' +
      '<div class="text-xs text-gray-500">ID: ' + esc(s.student_id) + '</div><div class="flex gap-2 mt-1.5 flex-wrap">' + gradeBadge + cat + '</div></div></div></td>' +
      '<td class="px-6 py-4"><div class="text-sm text-gray-900 dark:text-white">' + esc(s.parent_name || 'N/A') + '</div>' +
      (s.parent_phone ? '<div class="text-xs text-gray-500">' + esc(s.parent_phone) + '</div>' : '') + '</td>' +
      '<td class="px-6 py-4 whitespace-nowrap">' + dueBlock + '</td>' +
      '<td class="px-6 py-4 whitespace-nowrap">' + paidBlock + '</td>' +
      '<td class="px-6 py-4 whitespace-nowrap">' + balanceHtml(s) + '</td>' +
      '<td class="px-6 py-4 text-center">' + statusBadge(s.payment_status) + '</td>' +
      '<td class="px-6 py-4 text-right">' + actionButtons(s, cfg) + '</td></tr>'
    );
  }

  function mobileRow(s, cfg) {
    var fs = s.fee_structure;
    var level = (s.academic_level && s.academic_level.level_name) || s.current_grade || '';
    var due = fs ? moneyShort(s.total_amount_due || fs.total_amount) : '—';
    var feeMeta = fs && (fs.fee_name || fs.finance_account_name)
      ? '<div class="text-[10px] text-gray-500 mt-0.5 truncate">' + esc(fs.fee_name || fs.finance_account_name) + '</div>'
      : '';
    var bal = '—';
    if (fs) {
      var b = Number(s.balance) || 0;
      if (b > 0) bal = moneyShort(b);
      else if (b === 0) bal = '0';
      else bal = '+' + moneyShort(-b) + ' cr.';
    }
    var mobActions = '<div class="mt-3 ml-[52px] flex justify-end gap-1.5">' + actionButtons(s, cfg).replace(/justify-end gap-1\.5"><div/g, 'justify-end gap-1.5"><div') + '</div>';
    return (
      '<div class="student-list-row rounded-xl border bg-white/95 dark:bg-gray-800/95 shadow-sm pl-3 pr-3 py-3 border-l-4 ' + mobileBorder(s.payment_status) + '" ' +
      'data-student-id="' + esc(s.student_id) + '" data-student-name="' + esc((s.full_name || '').toLowerCase()) + '" data-grade="' + esc((s.current_grade || '').toLowerCase()) + '" data-category="' + esc((s.student_category || '').toLowerCase()) + '">' +
      '<div class="font-semibold text-sm">' + esc(s.full_name) + '</div>' +
      '<div class="text-[11px] text-gray-500 mt-1">ID ' + esc(s.student_id) + (level ? ' · ' + esc(level) : '') + '</div>' +
      '<div class="mt-2 text-[11px]">Parent: ' + esc(s.parent_name || 'N/A') + '</div>' +
      '<div class="mt-2 grid grid-cols-3 gap-2 text-[11px]"><div><span class="text-slate-500">Due</span><div class="font-bold">' + due + '</div>' + feeMeta + '</div>' +
      '<div><span class="text-emerald-700">Paid</span><div class="font-bold text-emerald-800">' + moneyShort(s.total_paid || 0) + '</div></div>' +
      '<div><span>Bal.</span><div class="font-bold">' + bal + '</div></div></div>' +
      mobActions + '</div>'
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
    var mobile = qs('studentsMobileList');
    if (!tbody) return;
    if (!list.length) {
      var title = state.total === 0 ? 'No students found' : 'No students match your filters';
      var sub =
        state.total === 0
          ? 'Students will appear here once they are registered.'
          : 'Try different search words or filters.';
      tbody.innerHTML = emptyRow(7, title, sub);
      if (mobile) {
        mobile.innerHTML =
          '<div class="px-4 py-12 text-center text-gray-500"><p class="text-sm font-semibold">' +
          esc(title) +
          '</p><p class="text-xs mt-1">' +
          esc(sub) +
          '</p></div>';
      }
      return;
    }
    var html = '';
    var mob = '<div class="px-2 pt-3 pb-3 space-y-2.5">';
    list.forEach(function (s, i) {
      html += desktopRow(s, state.cfg, i);
      mob += mobileRow(s, state.cfg);
    });
    mob += '</div>';
    tbody.innerHTML = html;
    if (mobile) mobile.innerHTML = mob;
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
