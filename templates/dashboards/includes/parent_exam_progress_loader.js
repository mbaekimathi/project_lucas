/**
 * Parent exam progress — live filters without full page reload.
 */
(function () {
  function readConfig() {
    var el = document.getElementById('pep-page-config');
    if (!el || !el.textContent) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function destroyCharts() {
    var list = window.__parentExamChartInstances || [];
    list.forEach(function (c) {
      try {
        if (c) c.destroy();
      } catch (e) { /* ignore */ }
    });
    window.__parentExamChartInstances = [];
    window.__parentExamChartsBuilt = false;
  }

  function refillSelect(selectId, placeholder, items, getVal, getLabel, selectedVal) {
    var sel = document.getElementById(selectId);
    if (!sel) return;
    while (sel.options.length > 1) sel.remove(1);
    if (sel.options.length === 0) {
      var ph = document.createElement('option');
      ph.value = '';
      ph.textContent = placeholder;
      sel.appendChild(ph);
    } else {
      sel.options[0].value = '';
      sel.options[0].textContent = placeholder;
    }
    (items || []).forEach(function (item) {
      var o = document.createElement('option');
      o.value = String(getVal(item));
      o.textContent = getLabel(item);
      sel.appendChild(o);
    });
    var next = selectedVal != null && selectedVal !== '' ? String(selectedVal) : '';
    if (Array.prototype.some.call(sel.options, function (opt) { return opt.value === next; })) {
      sel.value = next;
    } else {
      sel.value = '';
    }
  }

  function brandRgba(rootStyle, cssVar, alpha) {
    var raw = (rootStyle.getPropertyValue(cssVar) || '').trim();
    if (!raw) return 'rgba(128, 0, 32, ' + alpha + ')';
    var hex = raw.replace('#', '');
    if (hex.length === 3) hex = hex.split('').map(function (c) { return c + c; }).join('');
    if (hex.length !== 6) return 'rgba(128, 0, 32, ' + alpha + ')';
    return 'rgba(' + parseInt(hex.slice(0, 2), 16) + ',' + parseInt(hex.slice(2, 4), 16) + ',' + parseInt(hex.slice(4, 6), 16) + ',' + alpha + ')';
  }

  function barColors(values) {
    return values.map(function (v) {
      if (v >= 70) return 'rgba(34, 197, 94, 0.75)';
      if (v >= 50) return 'rgba(245, 158, 11, 0.75)';
      return 'rgba(239, 68, 68, 0.75)';
    });
  }

  window.__refreshParentExamProgressCharts = function (bySubject, byExam, byPeriod) {
    if (typeof Chart === 'undefined') return;
    destroyCharts();
    window.__parentExamChartInstances = window.__parentExamChartInstances || [];

    var isDark = document.documentElement.classList.contains('dark');
    var textColor = isDark ? '#e5e7eb' : '#374151';
    var gridColor = isDark ? 'rgba(75, 85, 99, 0.3)' : 'rgba(209, 213, 219, 0.5)';
    var rootStyle = getComputedStyle(document.documentElement);

    var subjectData = bySubject || [];
    var subjectEl = document.getElementById('subjectChart');
    if (subjectData.length > 0 && subjectEl) {
      var sc = new Chart(subjectEl, {
        type: 'bar',
        data: {
          labels: subjectData.map(function (s) { return s.subject_name; }),
          datasets: [{
            label: 'Mean %',
            data: subjectData.map(function (s) { return s.mean; }),
            backgroundColor: barColors(subjectData.map(function (s) { return s.mean; })),
            borderWidth: 0,
            borderRadius: 4
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { min: 0, max: 100, grid: { color: gridColor }, ticks: { color: textColor } },
            y: { grid: { display: false }, ticks: { color: textColor, font: { size: 11 } } }
          }
        }
      });
      window.__parentExamChartInstances.push(sc);
    }

    var examData = byExam || [];
    var examEl = document.getElementById('examChart');
    if (examData.length > 0 && examEl) {
      var examLabels = examData.map(function (e) {
        var parts = (e.exam_name || e.label || 'Exam').split(' · ');
        return parts[parts.length - 1] || e.label;
      });
      var ec = new Chart(examEl, {
        type: 'bar',
        data: {
          labels: examLabels,
          datasets: [{
            label: 'Exam mean %',
            data: examData.map(function (e) { return e.mean; }),
            backgroundColor: brandRgba(rootStyle, '--brand-primary', 0.72),
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { color: textColor, maxRotation: 45, minRotation: 0, font: { size: 10 } } },
            y: { min: 0, max: 100, grid: { color: gridColor }, ticks: { color: textColor } }
          }
        }
      });
      window.__parentExamChartInstances.push(ec);
    }

    var periodData = byPeriod || [];
    var trendEl = document.getElementById('trendChart');
    if (periodData.length > 0 && trendEl) {
      var tc = new Chart(trendEl, {
        type: 'line',
        data: {
          labels: periodData.map(function (p) { return p.label; }),
          datasets: [{
            label: 'Term mean %',
            data: periodData.map(function (p) { return p.mean; }),
            fill: true,
            borderColor: brandRgba(rootStyle, '--brand-primary', 1),
            backgroundColor: brandRgba(rootStyle, '--brand-primary', 0.12),
            tension: 0.3
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: { min: 0, max: 100, grid: { color: gridColor }, ticks: { color: textColor } }
          }
        }
      });
      window.__parentExamChartInstances.push(tc);
    }
    window.__parentExamChartsBuilt = true;
  };

  window.__initParentExamProgressCharts = function () {
    var cfg = readConfig();
    if (!cfg || !cfg.initial) return;
    window.__refreshParentExamProgressCharts(
      cfg.initial.by_subject,
      cfg.initial.by_exam,
      cfg.initial.by_period
    );
  };

  document.addEventListener('alpine:init', function () {
    Alpine.data('parentExamProgressPage', function () {
      var cfg = readConfig() || {};
      var initial = cfg.initial || {};
      var selected = initial.selected || {};

      return {
        loading: false,
        loadError: null,
        filters: {
          academic_year_id: selected.academic_year_id != null ? String(selected.academic_year_id) : '',
          term_id: selected.term_id != null ? String(selected.term_id) : '',
          exam_id: selected.exam_id != null ? String(selected.exam_id) : '',
          subject_id: selected.subject_id != null ? String(selected.subject_id) : ''
        },
        filterOpts: initial.filters || { academic_years: [], terms: [], exams: [], subjects: [] },
        live: {
          has_exam_marks: !!initial.has_exam_marks,
          filter_no_results: !!initial.filter_no_results,
          filters_active: !!initial.filters_active,
          summary: initial.summary || null,
          by_subject: initial.by_subject || [],
          by_exam: initial.by_exam || [],
          by_period: initial.by_period || [],
          exams_count: initial.exams_count || 0,
          subjects_count: initial.subjects_count || 0
        },
        _fetchTimer: null,
        _fetchAbort: null,

        init: function () {
          var self = this;
          self.syncFilterSelects();
          self.$nextTick(function () {
            if (self.hasResults()) self.refreshCharts();
          });
        },

        syncFilterSelects: function () {
          var opts = this.filterOpts || {};
          refillSelect('pep-academic-year', 'All years', opts.academic_years || [], function (y) { return y.id; }, function (y) { return y.year_name; }, this.filters.academic_year_id);
          refillSelect('pep-term', 'All terms', opts.terms || [], function (t) { return t.id; }, function (t) { return (t.year_name ? t.year_name + ' · ' : '') + t.term_name; }, this.filters.term_id);
          refillSelect('pep-exam', 'All exams', opts.exams || [], function (ex) { return ex.id; }, function (ex) { return ex.label; }, this.filters.exam_id);
          refillSelect('pep-subject', 'All subjects', opts.subjects || [], function (s) { return s.id; }, function (s) { return s.subject_name; }, this.filters.subject_id);
        },

        refreshCharts: function () {
          window.__refreshParentExamProgressCharts(
            this.live.by_subject,
            this.live.by_exam,
            this.live.by_period
          );
        },

        markClass: function (marks) {
          if (marks >= 70) return 'text-green-600 dark:text-green-400';
          if (marks >= 50) return 'text-amber-600 dark:text-amber-400';
          return 'text-red-600 dark:text-red-400';
        },

        markClassStrong: function (marks) {
          if (marks >= 70) return 'text-green-700 dark:text-green-400';
          if (marks >= 50) return 'text-amber-700 dark:text-amber-400';
          return 'text-red-700 dark:text-red-400';
        },

        barClass: function (mean) {
          if (mean >= 70) return 'bg-green-500';
          if (mean >= 50) return 'bg-amber-500';
          return 'bg-red-500';
        },

        cellMark: function (subjName, exam) {
          var subs = exam.subjects || [];
          for (var i = 0; i < subs.length; i++) {
            if (subs[i].subject_name === subjName) return subs[i].marks;
          }
          return null;
        },

        hasResults: function () {
          return this.live.summary && this.live.summary.total_entries > 0;
        },

        filterPageUrl: cfg.filterPageUrl || '',

        scheduleFetch: function () {
          var self = this;
          clearTimeout(self._fetchTimer);
          self._fetchTimer = setTimeout(function () { self.fetchLive(); }, 280);
        },

        resetFilters: function () {
          this.filters = { academic_year_id: '', term_id: '', exam_id: '', subject_id: '' };
          this.scheduleFetch();
        },

        syncUrl: function () {
          try {
            var url = new URL(window.location.href);
            ['academic_year_id', 'term_id', 'exam_id', 'subject_id'].forEach(function (k) {
              var v = this.filters[k];
              if (v) url.searchParams.set(k, v);
              else url.searchParams.delete(k);
            }.bind(this));
            history.replaceState({}, '', url.toString());
          } catch (e) { /* ignore */ }
        },

        fetchLive: async function () {
          if (!cfg.dataUrl) return;
          var self = this;
          if (self._fetchAbort) {
            try { self._fetchAbort.abort(); } catch (e) { /* ignore */ }
          }
          self._fetchAbort = new AbortController();
          self.loading = true;
          self.loadError = null;

          var params = new URLSearchParams();
          ['academic_year_id', 'term_id', 'exam_id', 'subject_id'].forEach(function (k) {
            if (self.filters[k]) params.set(k, self.filters[k]);
          });

          try {
            var res = await fetch(cfg.dataUrl + (params.toString() ? '?' + params.toString() : ''), {
              signal: self._fetchAbort.signal,
              headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
            });
            var data = await res.json();
            if (!res.ok || !data.success) {
              throw new Error((data && data.message) || 'Could not load exam data');
            }
            self.live = {
              has_exam_marks: !!data.has_exam_marks,
              filter_no_results: !!data.filter_no_results,
              filters_active: !!data.filters_active,
              summary: data.summary || null,
              by_subject: data.by_subject || [],
              by_exam: data.by_exam || [],
              by_period: data.by_period || [],
              exams_count: data.exams_count || 0,
              subjects_count: data.subjects_count || 0
            };
            if (data.filters) {
              self.filterOpts = data.filters;
              self.syncFilterSelects();
            }
            if (data.selected) {
              self.filters.academic_year_id = data.selected.academic_year_id != null ? String(data.selected.academic_year_id) : '';
              self.filters.term_id = data.selected.term_id != null ? String(data.selected.term_id) : '';
              self.filters.exam_id = data.selected.exam_id != null ? String(data.selected.exam_id) : '';
              self.filters.subject_id = data.selected.subject_id != null ? String(data.selected.subject_id) : '';
              self.syncFilterSelects();
            }
            self.syncUrl();
            self.$nextTick(function () {
              if (self.hasResults()) self.refreshCharts();
            });
          } catch (err) {
            if (err && err.name === 'AbortError') return;
            self.loadError = (err && err.message) || 'Could not update results';
          } finally {
            self.loading = false;
          }
        }
      };
    });
  });
})();
