/**
 * Books inventory catalog setup — filter subjects by academic category.
 */
(function () {
  var subjectsByCategory = {};

  function parseJsonScript(id) {
    var el = document.getElementById(id);
    if (!el || !el.textContent) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function populateSubjects(form, category) {
    var sel = form.querySelector('.js-setup-subject');
    if (!sel) return;
    var prev = sel.value;
    sel.innerHTML = '';
    var opt0 = document.createElement('option');
    opt0.value = '';
    opt0.textContent = 'Select subject';
    sel.appendChild(opt0);
    var rows = subjectsByCategory[category] || [];
    rows.forEach(function (s) {
      var o = document.createElement('option');
      o.value = String(s.id);
      var label = (s.subject_name || '').toUpperCase();
      if (s.subject_code) label += ' (' + (s.subject_code || '').toUpperCase() + ')';
      o.textContent = label;
      if (String(s.id) === String(prev)) o.selected = true;
      sel.appendChild(o);
    });
    sel.disabled = !category || rows.length === 0;
  }

  function bindForm(form) {
    form.addEventListener('submit', function () {
      var subSel = form.querySelector('.js-setup-subject');
      if (subSel) subSel.disabled = false;
    });
    var catSel = form.querySelector('.js-setup-category');
    if (catSel) {
      catSel.addEventListener('change', function () {
        populateSubjects(form, catSel.value);
        var subSel = form.querySelector('.js-setup-subject');
        if (subSel && !catSel.value) subSel.value = '';
      });
      if (catSel.value) populateSubjects(form, catSel.value);
    }
  }

  function init() {
    subjectsByCategory = parseJsonScript('library-subjects-by-category') || {};
    document.querySelectorAll('.js-book-setup-form').forEach(bindForm);
    var hash = window.location.hash;
    if (hash && hash.indexOf('book-') === 1) {
      var el = document.querySelector(hash);
      if (el && el.scrollIntoView) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
