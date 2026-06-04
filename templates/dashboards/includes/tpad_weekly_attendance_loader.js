/**
 * TPAD weekly attendance — teachers with lessons attended vs allocated for selected range.
 */
(function () {
  var apiUrl = typeof _tpadWeeklyTeachersApiUrl !== 'undefined' ? _tpadWeeklyTeachersApiUrl : '';
  var detailBase = typeof _tpadWeeklyTeacherDetailBase !== 'undefined' ? _tpadWeeklyTeacherDetailBase : '';
  if (!apiUrl || !window.TpadAttendanceFilter) return;

  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function teacherDetailUrl(teacherId, params) {
    if (!detailBase || teacherId == null || teacherId === '') return '#';
    return TpadAttendanceFilter.appendQuery(
      detailBase + '/' + encodeURIComponent(String(teacherId)),
      params
    );
  }

  function lessonCell(attended, allocated) {
    attended = parseInt(attended, 10) || 0;
    allocated = parseInt(allocated, 10) || 0;
    var cls = 'text-gray-700 dark:text-gray-300';
    if (allocated && attended >= allocated) {
      cls = 'text-green-700 dark:text-green-300';
    } else if (attended) {
      cls = 'text-amber-700 dark:text-amber-300';
    }
    return (
      '<span class="font-semibold ' +
      cls +
      '">' +
      attended +
      ' / ' +
      allocated +
      '</span>'
    );
  }

  function renderRows(teachers, filterMeta, params) {
    var tbody = document.getElementById('tpad-weekly-teachers-tbody');
    var empty = document.getElementById('tpad-weekly-teachers-empty');
    var tableWrap = document.getElementById('tpad-weekly-teachers-table-wrap');
    var countEl = document.getElementById('tpad-weekly-teachers-count');
    if (!tbody) return;

    TpadAttendanceFilter.updateRangeLabel(filterMeta || {});

    if (!teachers || !teachers.length) {
      tbody.innerHTML = '';
      if (tableWrap) tableWrap.classList.add('hidden');
      if (empty) empty.classList.remove('hidden');
      if (countEl) countEl.textContent = '0';
      return;
    }

    if (tableWrap) tableWrap.classList.remove('hidden');
    if (empty) empty.classList.add('hidden');
    if (countEl) countEl.textContent = String(teachers.length);

    var html = '';
    teachers.forEach(function (emp) {
      var detailUrl = teacherDetailUrl(emp.id, params);
      var name = esc(emp.full_name || '—');
      html +=
        '<tr class="hover:bg-gray-50/80 dark:hover:bg-gray-800/50 group">' +
        '<td class="py-3 px-3 sm:px-4 font-medium text-gray-900 dark:text-white">' +
        '<a href="' +
        esc(detailUrl) +
        '" class="tpad-teacher-detail-link inline-flex items-center gap-2 text-inherit hover:text-brand-primary dark:hover:text-brand-secondary" data-teacher-id="' +
        esc(emp.id) +
        '">' +
        name +
        '</a></td>' +
        '<td class="py-3 px-3 sm:px-4 text-right tabular-nums">' +
        '<a href="' +
        esc(detailUrl) +
        '" class="tpad-teacher-detail-link inline-block hover:opacity-80" title="View class breakdown" data-teacher-id="' +
        esc(emp.id) +
        '">' +
        lessonCell(emp.lessons_attended, emp.lessons_allocated) +
        '</a></td>' +
        '<td class="py-3 px-3 sm:px-4 text-center">' +
        '<a href="' +
        esc(detailUrl) +
        '" class="tpad-teacher-detail-link inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 dark:text-gray-400 hover:text-brand-primary dark:hover:text-brand-secondary hover:bg-teal-50 dark:hover:bg-teal-950/40 border border-transparent hover:border-teal-200 dark:hover:border-teal-800 touch-btn" title="View class breakdown for ' +
        name +
        '" data-teacher-id="' +
        esc(emp.id) +
        '">' +
        '<i class="fas fa-eye" aria-hidden="true"></i>' +
        '<span class="sr-only">View ' +
        name +
        '</span></a></td></tr>';
    });
    tbody.innerHTML = html;
  }

  function setLoading(loading) {
    var el = document.getElementById('tpad-weekly-teachers-loading');
    if (el) el.classList.toggle('hidden', !loading);
    TpadAttendanceFilter.setLoading(loading);
  }

  function setError(msg) {
    var el = document.getElementById('tpad-weekly-teachers-error');
    if (!el) return;
    if (msg) {
      el.textContent = msg;
      el.classList.remove('hidden');
    } else {
      el.textContent = '';
      el.classList.add('hidden');
    }
  }

  function loadTeachers(params) {
    params = params || TpadAttendanceFilter.getParams();
    setLoading(true);
    setError('');
    var url = apiUrl + (apiUrl.indexOf('?') >= 0 ? '&' : '?') + TpadAttendanceFilter.toQueryString(params);
    fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data || !result.data.success) {
          throw new Error(
            (result.data && result.data.message) || 'Could not load teachers'
          );
        }
        var meta = result.data.filter_meta || result.data.weekly_meta || {};
        renderRows(result.data.teachers || [], meta, params);
      })
      .catch(function (err) {
        setError(err.message || 'Could not load teachers');
      })
      .finally(function () {
        setLoading(false);
      });
  }

  function syncDetailLinks(params) {
    document.querySelectorAll('.tpad-teacher-detail-link').forEach(function (link) {
      var tid = link.getAttribute('data-teacher-id');
      if (tid) link.setAttribute('href', teacherDetailUrl(tid, params));
    });
  }

  TpadAttendanceFilter.init({
    onChange: function (params) {
      syncDetailLinks(params);
      loadTeachers(params);
    },
  });
})();
