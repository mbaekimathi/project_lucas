/**
 * Teacher dashboard — monthly lesson attendance calendar.
 */
(function () {
  var root = document.getElementById('teacher-lesson-calendar-root');
  if (!root) return;

  var apiUrl =
    (typeof window._teacherLessonCalendarApiUrl !== 'undefined' && window._teacherLessonCalendarApiUrl) ||
    root.getAttribute('data-api-url') ||
    '';
  var attendanceBaseUrl =
    (typeof window._teacherAttendanceRegisterUrl !== 'undefined' && window._teacherAttendanceRegisterUrl) ||
    root.getAttribute('data-attendance-url') ||
    '';
  var teacherId = root.getAttribute('data-teacher-id') || '';
  var grid = document.getElementById('tlc-grid');
  var monthLabel = document.getElementById('tlc-month-label');
  var monthSummary = document.getElementById('tlc-month-summary');
  var termBadge = document.getElementById('tlc-term-badge');
  var loadingEl = document.getElementById('tlc-loading');
  var errorEl = document.getElementById('tlc-error');
  var prevBtn = document.getElementById('tlc-prev-month');
  var nextBtn = document.getElementById('tlc-next-month');

  var now = new Date();
  var state = {
    year: now.getFullYear(),
    month: now.getMonth() + 1,
    termId: null,
    days: [],
  };

  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatDayTitle(dateStr) {
    if (!dateStr) return '—';
    var parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    var d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    return d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }

  function setLoading(on) {
    if (loadingEl) loadingEl.classList.toggle('hidden', !on);
    if (grid) grid.style.opacity = on ? '0.45' : '1';
  }

  function setError(msg) {
    if (!errorEl) return;
    if (msg) {
      errorEl.textContent = msg;
      errorEl.classList.remove('hidden');
    } else {
      errorEl.textContent = '';
      errorEl.classList.add('hidden');
    }
  }

  function summaryClass(percent) {
    if (percent >= 100) return 'text-emerald-700 dark:text-emerald-300';
    if (percent >= 80) return 'text-lime-700 dark:text-lime-300';
    if (percent >= 50) return 'text-amber-700 dark:text-amber-300';
    if (percent > 0) return 'text-orange-700 dark:text-orange-300';
    return 'text-gray-700 dark:text-gray-300';
  }

  function renderSummary(data) {
    if (monthLabel) monthLabel.textContent = data.month_label || '—';
    var s = data.summary || {};
    var attended = parseInt(s.lessons_attended, 10) || 0;
    var allocated = parseInt(s.lessons_allocated, 10) || 0;
    var pct = parseInt(s.percent, 10) || 0;
    if (monthSummary) {
      monthSummary.innerHTML =
        '<span class="' +
        summaryClass(pct) +
        '">' +
        attended +
        ' / ' +
        allocated +
        ' lessons (' +
        pct +
        '%)</span>';
    }
    if (termBadge) {
      if (data.term_name) {
        termBadge.textContent = data.term_name;
        termBadge.classList.remove('hidden');
      } else {
        termBadge.classList.add('hidden');
      }
    }
  }

  function attendanceUrlForDay(dateStr) {
    if (!attendanceBaseUrl || !dateStr) return '#';
    var params = ['filter_type=day', 'day=' + encodeURIComponent(dateStr)];
    if (state.termId) params.push('term_id=' + encodeURIComponent(String(state.termId)));
    return attendanceBaseUrl + (attendanceBaseUrl.indexOf('?') >= 0 ? '&' : '?') + params.join('&');
  }

  function cellHtml(day) {
    if (day.pad) {
      return '<div class="tlc-cell tlc-band-pad" aria-hidden="true"></div>';
    }
    var band = day.band || 'none';
    var clickable = !!(day.in_term && !day.is_future && day.date && attendanceBaseUrl);
    var cls = 'tlc-cell tlc-band-' + esc(band);
    if (clickable) cls += ' tlc-cell-interactive';
    var pctText = '';
    if (day.in_term && !day.is_future && day.allocated > 0) {
      pctText = day.percent + '%';
    } else if (day.attended > 0) {
      pctText = '100%';
    } else if (day.in_term && !day.is_future && day.allocated > 0) {
      pctText = '0%';
    }
    var ratio =
      day.in_term && !day.is_future && (day.allocated > 0 || day.attended > 0)
        ? day.attended + '/' + day.allocated
        : '';
    var inner =
      '<div class="tlc-cell-day">' +
      day.day +
      '</div>' +
      (pctText ? '<div class="tlc-cell-pct">' + esc(pctText) + '</div>' : '') +
      (ratio ? '<div class="tlc-cell-ratio">' + esc(ratio) + '</div>' : '');
    var title = formatDayTitle(day.date) + (clickable ? ' — open subject attendance' : '');
    if (ratio) title += ' (' + ratio + ' lessons)';
    if (clickable) {
      return (
        '<a href="' +
        esc(attendanceUrlForDay(day.date)) +
        '" class="' +
        cls +
        '" title="' +
        esc(title) +
        '">' +
        inner +
        '</a>'
      );
    }
    return '<div class="' + cls + '" title="' + esc(title) + '">' + inner + '</div>';
  }

  function renderGrid(days) {
    if (!grid) return;
    var html = '';
    (days || []).forEach(function (day) {
      html += cellHtml(day);
    });
    grid.innerHTML = html;
  }

  function readJsonResponse(res) {
    var ct = (res.headers.get('content-type') || '').toLowerCase();
    if (ct.indexOf('application/json') === -1) {
      return res.text().then(function () {
        if (res.status === 404) {
          throw new Error(
            'Calendar API not found. Restart the application server and refresh this page.'
          );
        }
        if (res.status === 401) {
          throw new Error('Your session expired. Please sign in again.');
        }
        throw new Error('Unexpected server response. Please refresh the page.');
      });
    }
    return res.json();
  }

  function loadMonth(year, month) {
    if (!apiUrl) {
      setError('Calendar API URL is missing.');
      return;
    }
    setLoading(true);
    setError('');
    var url =
      apiUrl +
      (apiUrl.indexOf('?') >= 0 ? '&' : '?') +
      'year=' +
      encodeURIComponent(year) +
      '&month=' +
      encodeURIComponent(month);
    if (teacherId) url += '&teacher_id=' + encodeURIComponent(teacherId);
    fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (res) {
        return readJsonResponse(res).then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data || !result.data.success) {
          throw new Error((result.data && result.data.message) || 'Could not load calendar');
        }
        var data = result.data;
        state.year = data.year;
        state.month = data.month;
        state.termId = data.term_id || null;
        state.days = data.days || [];
        renderSummary(data);
        renderGrid(state.days);
      })
      .catch(function (err) {
        setError(err.message || 'Could not load calendar');
      })
      .finally(function () {
        setLoading(false);
      });
  }

  function shiftMonth(delta) {
    var m = state.month + delta;
    var y = state.year;
    if (m < 1) {
      m = 12;
      y -= 1;
    } else if (m > 12) {
      m = 1;
      y += 1;
    }
    loadMonth(y, m);
  }

  if (prevBtn) prevBtn.addEventListener('click', function () { shiftMonth(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function () { shiftMonth(1); });

  loadMonth(state.year, state.month);
})();
