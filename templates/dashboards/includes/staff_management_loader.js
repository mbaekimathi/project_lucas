/**
 * Staff / teacher directory — paginated list (50 per page).
 */
(function () {
  var prefix = typeof _staffEmpPrefix !== 'undefined' ? _staffEmpPrefix : '';
  var teachersOnly =
    typeof _staffTeachersOnly !== 'undefined' && _staffTeachersOnly;
  var currentPk =
    typeof _staffCurrentPk !== 'undefined' ? _staffCurrentPk : null;
  var canEdit = typeof _staffCanEdit !== 'undefined' && _staffCanEdit;
  var canDelete = typeof _staffCanDelete !== 'undefined' && _staffCanDelete;

  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function statusPill(st) {
    st = (st || '').toLowerCase();
    if (st === 'active') {
      return '<span class="staff-status-pill bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">Active</span>';
    }
    if (st === 'pending' || st === 'pending approval') {
      return '<span class="staff-status-pill bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300">Pending</span>';
    }
    if (st === 'suspended') {
      return '<span class="staff-status-pill bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300">Suspended</span>';
    }
    if (st === 'fired' || st === 'retired') {
      return (
        '<span class="staff-status-pill bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">' +
        esc(st.charAt(0).toUpperCase() + st.slice(1)) +
        '</span>'
      );
    }
    return (
      '<span class="staff-status-pill bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">' +
      esc(st || '—') +
      '</span>'
    );
  }

  function formatJoined(ca) {
    if (!ca) return '—';
    var s = String(ca);
    return s.length >= 10 ? s.slice(0, 10) : s;
  }

  function rolesHtml(roles) {
    var list = roles && roles.length ? roles : [];
    var html = '<div class="flex flex-wrap gap-1 max-w-[180px]">';
    list.slice(0, 2).forEach(function (r) {
      html +=
        '<span class="modern-badge bg-blue-50 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 capitalize">' +
        esc(r) +
        '</span>';
    });
    if (list.length > 2) {
      html +=
        '<span class="modern-badge bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">+' +
        (list.length - 2) +
        '</span>';
    }
    html += '</div>';
    return html;
  }

  window.staffListState = {
    page: 1,
    pages: 1,
    total: 0,
    loading: false,
    employees: [],
    stats: { total: 0, active: 0, pending: 0, suspended: 0, other: 0 },
  };

  function queryParams(page) {
    var p = new URLSearchParams();
    p.set('page', String(page || 1));
    p.set('per_page', '50');
    p.set('sort', 'created_desc');
    if (teachersOnly) p.set('teachers_only', '1');
    var root = document.querySelector('[x-data*="staffManagement"]');
    if (root && root._x_dataStack && root._x_dataStack[0]) {
      var d = root._x_dataStack[0];
      if (d.statusFilter && d.statusFilter !== 'all') p.set('status', d.statusFilter);
      var q = (d.searchQuery || '').trim();
      if (q) p.set('q', q);
    }
    return p.toString();
  }

  function updatePaginationUi() {
    var bar = document.getElementById('staff-pagination-bar');
    var hint = document.getElementById('staff-page-hint');
    var prev = document.getElementById('staff-prev-page');
    var next = document.getElementById('staff-next-page');
    var st = window.staffListState;
    if (!bar) return;
    if (st.pages <= 1 && !st.loading) {
      bar.classList.add('hidden');
      return;
    }
    bar.classList.remove('hidden');
    if (hint) {
      hint.textContent =
        st.total > 0
          ? 'Page ' + st.page + ' of ' + st.pages + ' · ' + st.total + ' staff'
          : '';
    }
    if (prev) prev.disabled = st.loading || st.page <= 1;
    if (next) next.disabled = st.loading || st.page >= st.pages;
  }

  function buildActions(emp, mobile) {
    var st = (emp.status || '').toLowerCase();
    var isSelf = currentPk != null && emp.id === currentPk;
    var actions = '';
    if (mobile) {
      if (canEdit) {
        actions +=
          '<button type="button" onclick="window.staffOpenEdit(' +
          emp.id +
          ')" class="staff-mobile-action staff-mobile-action--edit" title="Edit" aria-label="Edit"><i class="fas fa-pen text-base"></i><span>Edit</span></button>';
      }
      if (canDelete && !isSelf) {
        actions +=
          '<button type="button" onclick="window.staffOpenDelete(' +
          emp.id +
          ', ' +
          JSON.stringify(emp.full_name || '') +
          ')" class="staff-mobile-action staff-mobile-action--delete" title="Delete" aria-label="Delete"><i class="fas fa-trash-alt text-base"></i><span>Delete</span></button>';
      } else if (canDelete && isSelf) {
        actions +=
          '<span class="staff-mobile-action staff-mobile-action--disabled" title="Cannot delete own account"><i class="fas fa-trash-alt text-base"></i><span>Delete</span></span>';
      }
      if (st !== 'fired' && st !== 'retired' && canEdit) {
        var suspendLabel = st === 'suspended' ? 'Unsuspend' : 'Suspend';
        actions +=
          '<button type="button" onclick="window.staffToggleSuspend(' +
          emp.id +
          ')" class="staff-mobile-action staff-mobile-action--suspend' +
          (st === 'suspended' ? ' staff-mobile-action--suspend-active' : '') +
          '" title="' +
          suspendLabel +
          '" aria-label="' +
          suspendLabel +
          '"><i class="fas fa-pause-circle text-base"></i><span>' +
          suspendLabel +
          '</span></button>';
      }
      return actions;
    }
    if (canEdit) {
      actions +=
        '<button type="button" onclick="window.staffOpenEdit(' +
        emp.id +
        ')" class="staff-action-icon-btn text-blue-600 dark:text-blue-400" title="Edit"><i class="fas fa-pen"></i></button>';
    }
    if (canDelete && !isSelf) {
      actions +=
        '<button type="button" onclick="window.staffOpenDelete(' +
        emp.id +
        ', ' +
        JSON.stringify(emp.full_name || '') +
        ')" class="staff-action-icon-btn text-red-600 dark:text-red-400" title="Delete"><i class="fas fa-trash-alt"></i></button>';
    } else if (canDelete && isSelf) {
      actions +=
        '<span class="staff-action-icon-btn text-gray-300 cursor-not-allowed opacity-60" title="Cannot delete own account"><i class="fas fa-trash-alt"></i></span>';
    }
    if (st !== 'fired' && st !== 'retired' && canEdit) {
      var checked = st === 'suspended' ? ' checked' : '';
      actions +=
        '<label class="staff-action-icon-btn cursor-pointer ' +
        (st === 'suspended' ? 'text-red-500' : 'text-gray-400') +
        '"><input type="checkbox" class="sr-only"' +
        checked +
        ' onchange="window.staffToggleSuspend(' +
        emp.id +
        ')"><i class="fas fa-pause-circle"></i></label>';
    }
    return actions;
  }

  function renderRow(emp) {
    var st = (emp.status || '').toLowerCase();
    var roles = emp.allocated_roles && emp.allocated_roles.length ? emp.allocated_roles : emp.role ? [emp.role] : [];
    var img = emp.profile_picture
      ? '<img src="/static/' + esc(emp.profile_picture) + '" alt="" class="w-full h-full object-cover">'
      : '<i class="fas fa-user text-white text-sm"></i>';
    var actions = buildActions(emp, false);
    return (
      '<tr id="employee-row-' +
      emp.id +
      '" data-employee-id="' +
      emp.id +
      '">' +
      '<td><div class="flex items-center gap-3 min-w-0"><div class="staff-avatar">' +
      img +
      '</div><div class="min-w-0"><p class="font-semibold text-gray-900 dark:text-white truncate max-w-[12rem] lg:max-w-[200px]">' +
      esc(emp.full_name) +
      '</p><p class="text-xs text-gray-500 truncate max-w-[12rem] lg:max-w-[200px]">' +
      esc(emp.email) +
      '</p></div></div></td>' +
      '<td><span class="font-mono text-xs sm:text-sm">' +
      esc(emp.staff_employee_number) +
      '</span></td>' +
      '<td><span class="font-mono text-xs sm:text-sm text-gray-600 dark:text-gray-400">' +
      esc(emp.employee_id || '—') +
      '</span></td>' +
      '<td><span class="text-xs sm:text-sm text-gray-600 dark:text-gray-400">' +
      esc(emp.phone || '—') +
      '</span></td>' +
      '<td>' +
      rolesHtml(roles) +
      '</td>' +
      '<td>' +
      statusPill(st) +
      '</td>' +
      '<td class="text-xs sm:text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">' +
      formatJoined(emp.created_at) +
      '</td>' +
      '<td><div class="flex items-center justify-end gap-0.5 flex-wrap">' +
      actions +
      '</div></td></tr>'
    );
  }

  function renderMobile(emp) {
    var st = (emp.status || '').toLowerCase();
    var roles = emp.allocated_roles && emp.allocated_roles.length ? emp.allocated_roles : emp.role ? [emp.role] : [];
    var roleBadges = '';
    roles.forEach(function (r) {
      roleBadges +=
        '<span class="modern-badge bg-blue-50 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 capitalize">' +
        esc(r) +
        '</span>';
    });
    if (!roleBadges) {
      roleBadges = '<span class="text-xs text-gray-400">No roles assigned</span>';
    }
    var img = emp.profile_picture
      ? '<img src="/static/' + esc(emp.profile_picture) + '" alt="" class="w-full h-full object-cover">'
      : '<i class="fas fa-user text-white"></i>';
    var actions = buildActions(emp, true);
    var actionGrid = actions
      ? '<div class="staff-mobile-actions">' + actions + '</div>'
      : '';
    return (
      '<article id="employee-' +
      emp.id +
      '" class="staff-mobile-card" data-employee-id="' +
      emp.id +
      '">' +
      '<div class="flex gap-3 justify-between items-start">' +
      '<div class="flex items-start gap-3 min-w-0 flex-1">' +
      '<div class="staff-avatar">' +
      img +
      '</div>' +
      '<div class="min-w-0 flex-1">' +
      '<h2 class="text-base font-semibold text-gray-900 dark:text-white leading-snug break-words">' +
      esc(emp.full_name) +
      '</h2>' +
      '<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 break-all">' +
      esc(emp.email) +
      '</p>' +
      '</div></div>' +
      '<div class="shrink-0 ml-2">' +
      statusPill(st) +
      '</div></div>' +
      '<dl class="staff-mobile-meta">' +
      '<div class="min-w-0"><dt>Staff #</dt><dd class="font-mono">' +
      esc(emp.staff_employee_number || '—') +
      '</dd></div>' +
      '<div class="min-w-0"><dt>Portal ID</dt><dd class="font-mono">' +
      esc(emp.employee_id || '—') +
      '</dd></div>' +
      '<div class="min-w-0"><dt>Phone</dt><dd>' +
      esc(emp.phone || '—') +
      '</dd></div>' +
      '<div class="min-w-0"><dt>Joined</dt><dd>' +
      formatJoined(emp.created_at) +
      '</dd></div>' +
      '</dl>' +
      '<div class="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700/80">' +
      roleBadges +
      '</div>' +
      actionGrid +
      '</article>'
    );
  }

  function renderLists() {
    var tbody = document.querySelector('.staff-directory-table tbody');
    var mobile = document.querySelector('#staff-mobile-list');
    var st = window.staffListState;
    if (!st.employees.length) {
      var empty =
        '<tr><td colspan="8" class="py-12 text-center text-gray-500">No staff on this page.</td></tr>';
      if (tbody) tbody.innerHTML = empty;
      if (mobile) mobile.innerHTML = '<p class="text-center text-sm text-gray-500 py-8">No staff on this page.</p>';
      return;
    }
    if (tbody) {
      tbody.innerHTML = st.employees.map(renderRow).join('');
    }
    if (mobile) {
      mobile.innerHTML = st.employees.map(renderMobile).join('');
    }
  }

  function syncAlpine() {
    var root = document.querySelector('[x-data*="staffManagement"]');
    if (root && root._x_dataStack && root._x_dataStack[0]) {
      var d = root._x_dataStack[0];
      d.employeesList = window.staffListState.employees;
      d.page = window.staffListState.page;
      d.pages = window.staffListState.pages;
      d.totalCount = window.staffListState.total;
      d.stats = window.staffListState.stats;
      d.listLoading = window.staffListState.loading;
      d.visibleCount = window.staffListState.employees.length;
    }
  }

  window.staffFetchList = function (page) {
    window.staffListState.loading = true;
    syncAlpine();
    fetch(prefix + '/staff-management/employees?' + queryParams(page), {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        window.staffListState.loading = false;
        if (!data.success) {
          window.staffListState.employees = [];
          renderLists();
          syncAlpine();
          return;
        }
        var meta = data.meta || {};
        window.staffListState.page = meta.page || 1;
        window.staffListState.pages = meta.pages || 1;
        window.staffListState.total = meta.total || 0;
        window.staffListState.employees = data.employees || [];
        renderLists();
        updatePaginationUi();
        syncAlpine();
      })
      .catch(function () {
        window.staffListState.loading = false;
        syncAlpine();
      });
  };

  window.staffFetchStats = function () {
    var q = teachersOnly ? '?teachers_only=1' : '';
    fetch(prefix + '/staff-management/stats' + q, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.success && data.stats) {
          window.staffListState.stats = data.stats;
          syncAlpine();
          ['staff-stat-total', 'staff-stat-active', 'staff-stat-pending', 'staff-stat-suspended'].forEach(
            function (id, i) {
              var el = document.getElementById(id);
              if (!el) return;
              var keys = ['total', 'active', 'pending', 'suspended'];
              el.textContent = String(data.stats[keys[i]] != null ? data.stats[keys[i]] : 0);
            }
          );
          var onFile = document.getElementById('staff-on-file-count');
          if (onFile) onFile.textContent = String(data.stats.total || 0);
        }
      });
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.staffFetchStats();
    window.staffFetchList(1);
    var prev = document.getElementById('staff-prev-page');
    var next = document.getElementById('staff-next-page');
    if (prev) {
      prev.addEventListener('click', function () {
        if (window.staffListState.page > 1) window.staffFetchList(window.staffListState.page - 1);
      });
    }
    if (next) {
      next.addEventListener('click', function () {
        if (window.staffListState.page < window.staffListState.pages) {
          window.staffFetchList(window.staffListState.page + 1);
        }
      });
    }
  });
})();
