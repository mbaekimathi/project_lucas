/**
 * TPAD teacher detail — class breakdown with live date filter.
 */
(function () {
  var apiUrl = typeof _tpadTeacherClassesApiUrl !== 'undefined' ? _tpadTeacherClassesApiUrl : '';
  if (!apiUrl || !window.TpadAttendanceFilter) return;

  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
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

  function updateTotal(totals) {
    var el = document.getElementById('tpad-teacher-total-value');
    if (!el || !totals) return;
    var attended = parseInt(totals.lessons_attended, 10) || 0;
    var allocated = parseInt(totals.lessons_allocated, 10) || 0;
    el.textContent = attended + ' / ' + allocated;
    el.className = 'font-bold ';
    if (allocated && attended >= allocated) {
      el.className += 'text-green-700 dark:text-green-300';
    } else if (attended) {
      el.className += 'text-amber-700 dark:text-amber-300';
    }
  }

  function renderRows(classRows, filterMeta, totals) {
    var tbody = document.getElementById('tpad-teacher-classes-tbody');
    var empty = document.getElementById('tpad-teacher-classes-empty');
    var tableWrap = document.getElementById('tpad-teacher-classes-table-wrap');
    if (!tbody) return;

    TpadAttendanceFilter.updateRangeLabel(filterMeta || {});
    updateTotal(totals || {});

    if (!classRows || !classRows.length) {
      tbody.innerHTML = '';
      if (tableWrap) tableWrap.classList.add('hidden');
      if (empty) empty.classList.remove('hidden');
      return;
    }

    if (tableWrap) tableWrap.classList.remove('hidden');
    if (empty) empty.classList.add('hidden');

    var html = '';
    classRows.forEach(function (row) {
      var levelName = esc(row.level_name || '—');
      var levelCat = row.level_category
        ? '<span class="block text-xs font-normal text-gray-500 dark:text-gray-400 mt-0.5">' +
          esc(row.level_category) +
          '</span>'
        : '';
      var subjectName = esc(row.subject_name || '—');
      var subjectCode = row.subject_code
        ? '<span class="block text-xs text-gray-500 dark:text-gray-400 mt-0.5">' +
          esc(row.subject_code) +
          '</span>'
        : '';
      html +=
        '<tr class="hover:bg-gray-50/80 dark:hover:bg-gray-800/50">' +
        '<td class="py-3 px-3 sm:px-4 font-medium text-gray-900 dark:text-white">' +
        levelName +
        levelCat +
        '</td>' +
        '<td class="py-3 px-3 sm:px-4 text-gray-700 dark:text-gray-300">' +
        subjectName +
        subjectCode +
        '</td>' +
        '<td class="py-3 px-3 sm:px-4 text-right tabular-nums">' +
        lessonCell(row.lessons_attended, row.lessons_allocated) +
        '</td></tr>';
    });
    tbody.innerHTML = html;
  }

  function setLoading(loading) {
    var el = document.getElementById('tpad-teacher-classes-loading');
    if (el) el.classList.toggle('hidden', !loading);
    TpadAttendanceFilter.setLoading(loading);
  }

  function setError(msg) {
    var el = document.getElementById('tpad-teacher-classes-error');
    if (!el) return;
    if (msg) {
      el.textContent = msg;
      el.classList.remove('hidden');
    } else {
      el.textContent = '';
      el.classList.add('hidden');
    }
  }

  function loadClasses(params) {
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
            (result.data && result.data.message) || 'Could not load classes'
          );
        }
        renderRows(
          result.data.class_rows || [],
          result.data.filter_meta || {},
          result.data.totals || {}
        );
      })
      .catch(function (err) {
        setError(err.message || 'Could not load classes');
      })
      .finally(function () {
        setLoading(false);
      });
  }

  TpadAttendanceFilter.init({
    onChange: loadClasses,
  });
})();
