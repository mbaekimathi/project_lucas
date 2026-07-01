/**
 * Fees reports — academic-reports-style preview, filters, and print.
 */
(function () {
  var cfgEl = document.getElementById('fr-page-config');
  var cfg = {};
  if (cfgEl && cfgEl.textContent) {
    try { cfg = JSON.parse(cfgEl.textContent); } catch (e) { cfg = {}; }
  }

  var GENERATE_API = cfg.generateApi || '';
  var ROSTER_API = cfg.rosterApi || '';
  var SCHOOL_INFO = cfg.school || {};
  var REPORT_CARD_CHUNK_SIZE = 8;

  var levelEl = document.getElementById('fr-level');
  var reportTypeEl = document.getElementById('fr-report-type');
  var studentSelectEl = document.getElementById('fr-student-select');
  var studentHiddenEl = document.getElementById('fr-student');
  var detailsListEl = document.getElementById('ar-details-list');
  var generatedAtEl = document.getElementById('ar-generated-at');
  var reportLoadTimer = null;
  var reportLoadToken = 0;
  var reportLoadAbort = null;
  var classRosterLoadToken = 0;
  var currentReportType = 'payment';
  var REPORT_LOAD_DEBOUNCE_MS = 320;

  function val(id) {
    var el = document.getElementById(id);
    return el ? String(el.value || '').trim() : '';
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtKes(n) {
    if (n === null || n === undefined || n === '' || isNaN(n)) return '—';
    return 'KES ' + Number(n).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function schoolContactsLeftHtml() {
    var parts = [];
    if (SCHOOL_INFO.email) {
      parts.push(
        '<div class="acr-print-letterhead__school-contact">' +
          '<dt class="acr-print-letterhead__detail-label">Email</dt>' +
          '<dd class="acr-print-letterhead__detail-value">' + escapeHtml(SCHOOL_INFO.email) + '</dd>' +
        '</div>'
      );
    }
    if (SCHOOL_INFO.phone) {
      parts.push(
        '<div class="acr-print-letterhead__school-contact">' +
          '<dt class="acr-print-letterhead__detail-label">Tel</dt>' +
          '<dd class="acr-print-letterhead__detail-value">' + escapeHtml(SCHOOL_INFO.phone) + '</dd>' +
        '</div>'
      );
    }
    if (!parts.length) return '';
    return '<dl class="acr-print-letterhead__school-contacts">' + parts.join('') + '</dl>';
  }

  function schoolWebsiteQrHtml() {
    if (!SCHOOL_INFO.websiteQrDataUrl) return '';
    return '<div class="acr-print-letterhead__qr">' +
      '<img src="' + escapeHtml(SCHOOL_INFO.websiteQrDataUrl) + '" alt="QR code — scan to visit school website" class="acr-print-letterhead__qr-img" width="96" height="96">' +
      '<p class="acr-print-letterhead__qr-label">School website</p>' +
      '<p class="acr-print-letterhead__qr-hint">Scan to visit</p>' +
    '</div>';
  }

  function schoolBrandRightHtml() {
    var qr = schoolWebsiteQrHtml();
    if (!qr) return '';
    return '<div class="acr-print-letterhead__brand-right">' + qr + '</div>';
  }

  function schoolContactDetailsHtml() {
    return schoolBrandRightHtml();
  }

  function schoolLocationHtml() {
    if (!SCHOOL_INFO.location) return '';
    return '<p class="acr-print-letterhead__location">' + escapeHtml(SCHOOL_INFO.location) + '</p>';
  }

  function setGeneratedNow() {
    if (!generatedAtEl) return;
    var d = new Date();
    generatedAtEl.textContent = 'Generated: ' + d.toLocaleString();
  }

  function printPageWrapClass(sectionIndex) {
    var i = sectionIndex | 0;
    return 'ar-print-page-sheet' + (i > 0 ? ' ar-print-page-follow' : '');
  }

  function renderParentPortalQrHtml() {
    var qrUrl = cfg.parentLoginQrDataUrl || '';
    if (!qrUrl) return '';
    return '' +
      '<div class="ar-portal-qr-block shrink-0">' +
        '<img src="' + escapeHtml(qrUrl) + '" alt="QR code — scan to open parent login" class="ar-portal-qr-img" width="72" height="72">' +
        '<p class="ar-portal-qr-label">Parent portal</p>' +
        '<p class="ar-portal-qr-hint">Scan to sign in</p>' +
      '</div>';
  }

  function feesReportGeneratedLabel() {
    if (!generatedAtEl) return new Date().toLocaleString();
    var t = String(generatedAtEl.textContent || '').trim();
    if (t.indexOf('Generated:') === 0) return t.replace(/^Generated:\s*/, '') || new Date().toLocaleString();
    return t || new Date().toLocaleString();
  }

  function feesReportPeriodLabel() {
    var lv = levelEl && levelEl.selectedIndex >= 0 ? String(levelEl.options[levelEl.selectedIndex].text || '').trim() : '';
    return lv && lv.indexOf('Select class') === -1 ? lv : 'All classes';
  }

  function renderReportCardHeader(reportTitle) {
    if (!window.AcademicPrintLetterhead || typeof window.AcademicPrintLetterhead.build !== 'function') {
      return '<header class="ar-rc-header"><h2 class="ar-rc-title">' + escapeHtml(reportTitle || 'FEE REPORT') + '</h2></header>';
    }
    return window.AcademicPrintLetterhead.build({
      school: SCHOOL_INFO,
      reportTitle: reportTitle || 'FEE REPORT',
      periodLabel: feesReportPeriodLabel(),
      generatedAt: feesReportGeneratedLabel(),
    });
  }

  function renderMetaWithPhoto(pairs) {
    return '' +
      '<div class="ar-rc-meta-panel ar-rc-meta-panel--with-photo">' +
        '<div class="ar-rc-meta-panel-main">' +
          '<div class="ar-rc-meta-grid">' +
            pairs.map(function (p) {
              return '' +
                '<div class="ar-rc-meta-item">' +
                  '<span class="ar-rc-meta-label">' + escapeHtml(p.label) + '</span>' +
                  '<span class="ar-rc-meta-value">' + escapeHtml(p.value || '—') + '</span>' +
                '</div>';
            }).join('') +
          '</div>' +
        '</div>' +
        '<div class="ar-rc-meta-photo-wrap">' +
          '<div class="ar-rc-photo mx-auto flex items-center justify-center text-[9px] text-gray-400 text-center leading-tight px-1">Fee account</div>' +
        '</div>' +
      '</div>';
  }

  function renderFeeVotesTable(votes) {
    if (!votes || !votes.length) {
      return '<p class="text-sm text-slate-500 dark:text-slate-400 py-4 text-center">No fee votes for the current term.</p>';
    }
    var totExpected = 0;
    var totPaid = 0;
    var totBalance = 0;
    var rows = votes.map(function (v) {
      var expected = Number(v.expected_amount) || 0;
      var paid = Number(v.paid_amount) || 0;
      var balance = Number(v.balance) || 0;
      totExpected += expected;
      totPaid += paid;
      totBalance += balance;
      var balCls = balance > 0 ? 'text-amber-700 dark:text-amber-400' : 'text-green-700 dark:text-green-400';
      return '' +
        '<tr>' +
          '<td class="ar-rc-td-subj">' + escapeHtml(v.vote_name || '—') +
            (v.vote_description ? '<span class="block text-[10px] font-normal text-slate-500">' + escapeHtml(v.vote_description) + '</span>' : '') +
          '</td>' +
          '<td class="ar-rc-td-num text-right">' + escapeHtml(fmtKes(expected)) + '</td>' +
          '<td class="ar-rc-td-num text-right">' + escapeHtml(fmtKes(paid)) + '</td>' +
          '<td class="ar-rc-td-num text-right font-semibold ' + balCls + '">' + escapeHtml(fmtKes(balance)) + '</td>' +
        '</tr>';
    }).join('');
    return '' +
      '<table class="ar-rc-table ar-rc-table--subjects">' +
        '<thead><tr>' +
          '<th class="ar-rc-th-subj text-left">Fee vote</th>' +
          '<th class="text-right">Expected</th>' +
          '<th class="text-right">Paid</th>' +
          '<th class="text-right">Balance</th>' +
        '</tr></thead>' +
        '<tbody>' + rows +
          '<tr class="font-semibold bg-slate-50 dark:bg-slate-800/50">' +
            '<td class="ar-rc-td-subj">Total</td>' +
            '<td class="ar-rc-td-num text-right">' + escapeHtml(fmtKes(totExpected)) + '</td>' +
            '<td class="ar-rc-td-num text-right">' + escapeHtml(fmtKes(totPaid)) + '</td>' +
            '<td class="ar-rc-td-num text-right ' + balanceClass(totBalance) + '">' + escapeHtml(fmtKes(totBalance)) + '</td>' +
          '</tr>' +
        '</tbody>' +
      '</table>';
  }

  function renderPaymentsTable(payments) {
    if (!payments || !payments.length) return '';
    var rows = payments.map(function (p) {
      return '' +
        '<tr>' +
          '<td>' + escapeHtml(p.date || '—') + '</td>' +
          '<td>' + escapeHtml(p.method || '—') + '</td>' +
          '<td>' + escapeHtml(p.reference || '—') + '</td>' +
          '<td class="text-right tabular-nums">' + escapeHtml(fmtKes(p.amount)) + '</td>' +
        '</tr>';
    }).join('');
    return '' +
      '<p class="ar-rc-feedback-title mt-3 mb-1">Payments this term</p>' +
      '<div class="overflow-x-auto">' +
        '<table class="ar-rc-table text-xs">' +
          '<thead><tr>' +
            '<th>Date</th><th>Method</th><th>Reference</th><th class="text-right">Amount</th>' +
          '</tr></thead>' +
          '<tbody>' + rows + '</tbody>' +
        '</table>' +
      '</div>';
  }

  function renderSignatures() {
    return '' +
      '<div class="ar-rc-signatures">' +
        '<div class="ar-rc-sig-block"><p class="ar-rc-sig-title">Parent / guardian</p><p>Signature: ____________________</p><p>Date: ____________________</p></div>' +
        '<div class="ar-rc-sig-block"><p class="ar-rc-sig-title">Accounts office</p><p>Signature / stamp: ____________________</p><p>Date: ____________________</p></div>' +
      '</div>';
  }

  function balanceClass(balance) {
    var b = Number(balance);
    if (!isFinite(b) || b === 0) return 'text-green-700 dark:text-green-400';
    if (b > 0) return 'text-amber-700 dark:text-amber-400';
    return 'text-green-700 dark:text-green-400';
  }

  function renderFeeReportCard(student, sheetIndex) {
    var fs = student.fee_structure || {};
    var billing = fs.billing_period || [fs.term_name, fs.year_name].filter(Boolean).join(' · ') || 'Current term';
    var metaPairs = [
      { label: 'Student name', value: student.full_name },
      { label: 'Admission no.', value: student.student_id },
      { label: 'Class', value: student.class_name },
      { label: 'Parent / guardian', value: student.parent_name },
    ];
    if (student.parent_contact) {
      metaPairs.push({ label: 'Parent contact', value: student.parent_contact });
    }
    metaPairs.push(
      { label: 'Billing period', value: billing },
      { label: 'Invoice ref.', value: student.invoice_number || '—' }
    );

    var statsHtml = '' +
      '<div class="ar-rc-stats-row mt-3" style="grid-template-columns:1fr;">' +
        '<div class="ar-rc-stat"><p class="ar-rc-stat-label">Balance</p><p class="ar-rc-stat-value ' + balanceClass(student.balance_due) + '">' + escapeHtml(fmtKes(student.balance_due)) + '</p></div>' +
      '</div>';

    var pdfBtn = student.download_pdf_url
      ? '<p class="no-print mt-2 text-xs"><a href="' + escapeHtml(student.download_pdf_url) + '" class="text-brand-primary font-semibold hover:underline" target="_blank" rel="noopener"><i class="fas fa-file-pdf mr-1"></i>Download PDF</a></p>'
      : '';

    return '' +
      '<article class="ar-rc ar-rc-individual mb-6 ' + printPageWrapClass(sheetIndex) + '">' +
        '<div class="ar-rc-deco ar-rc-deco--tr"></div>' +
        '<div class="ar-rc-inner">' +
          renderReportCardHeader('FEE PAYMENT REPORT') +
          renderMetaWithPhoto(metaPairs) +
          '<div class="ar-rc-main-body">' +
            renderFeeVotesTable(student.fee_votes) +
            statsHtml +
            renderPaymentsTable(student.payment_details) +
            pdfBtn +
          '</div>' +
          renderSignatures() +
        '</div>' +
      '</article>';
  }

  function renderAllTransactionsTable(transactions) {
    if (!transactions || !transactions.length) {
      return '<p class="text-sm text-slate-500 dark:text-slate-400 py-4 text-center">No fee transactions recorded for this student.</p>';
    }
    var total = 0;
    var rows = transactions.map(function (t) {
      var amount = Number(t.amount) || 0;
      total += amount;
      var notesCell = t.notes
        ? '<span class="block text-[10px] font-normal text-slate-500 mt-0.5">' + escapeHtml(t.notes) + '</span>'
        : '';
      return '' +
        '<tr>' +
          '<td>' + escapeHtml(t.date || '—') + '</td>' +
          '<td>' + escapeHtml(t.method || '—') + '</td>' +
          '<td>' + escapeHtml(t.reference || '—') + '</td>' +
          '<td class="ar-rc-td-subj">' + escapeHtml(t.fee_name || '—') +
            (t.billing_period && t.billing_period !== '—'
              ? '<span class="block text-[10px] font-normal text-slate-500">' + escapeHtml(t.billing_period) + '</span>'
              : '') +
          '</td>' +
          '<td class="text-right tabular-nums">' + escapeHtml(fmtKes(amount)) + '</td>' +
          '<td>' + escapeHtml(t.received_by || '—') + notesCell + '</td>' +
        '</tr>';
    }).join('');
    return '' +
      '<div class="overflow-x-auto">' +
        '<table class="ar-rc-table ar-rc-table--subjects text-xs">' +
          '<thead><tr>' +
            '<th>Date</th>' +
            '<th>Method</th>' +
            '<th>Reference</th>' +
            '<th class="text-left">Fee / period</th>' +
            '<th class="text-right">Amount</th>' +
            '<th>Received by</th>' +
          '</tr></thead>' +
          '<tbody>' + rows +
            '<tr class="font-semibold bg-slate-50 dark:bg-slate-800/50">' +
              '<td colspan="4" class="ar-rc-td-subj">Total paid (' + transactions.length + ' transaction' + (transactions.length === 1 ? '' : 's') + ')</td>' +
              '<td class="text-right tabular-nums">' + escapeHtml(fmtKes(total)) + '</td>' +
              '<td></td>' +
            '</tr>' +
          '</tbody>' +
        '</table>' +
      '</div>';
  }

  function renderFeeTransactionCard(student, sheetIndex) {
    var metaPairs = [
      { label: 'Student name', value: student.full_name },
      { label: 'Admission no.', value: student.student_id },
      { label: 'Class', value: student.class_name },
      { label: 'Parent / guardian', value: student.parent_name },
    ];
    if (student.parent_contact) {
      metaPairs.push({ label: 'Parent contact', value: student.parent_contact });
    }
    metaPairs.push({ label: 'Transactions', value: String(student.transaction_count || 0) });

    var statsHtml = '' +
      '<div class="ar-rc-stats-row mt-3" style="grid-template-columns:1fr;">' +
        '<div class="ar-rc-stat"><p class="ar-rc-stat-label">Total paid (all time)</p><p class="ar-rc-stat-value text-green-700 dark:text-green-400">' + escapeHtml(fmtKes(student.total_paid)) + '</p></div>' +
      '</div>';

    return '' +
      '<article class="ar-rc ar-rc-individual mb-6 ' + printPageWrapClass(sheetIndex) + '">' +
        '<div class="ar-rc-deco ar-rc-deco--tr"></div>' +
        '<div class="ar-rc-inner">' +
          renderReportCardHeader('FEE TRANSACTION REPORT') +
          renderMetaWithPhoto(metaPairs) +
          '<div class="ar-rc-main-body">' +
            renderAllTransactionsTable(student.transactions) +
            statsHtml +
          '</div>' +
          renderSignatures() +
        '</div>' +
      '</article>';
  }

  function renderStudentCard(student, sheetIndex) {
    var type = student.report_type || currentReportType || 'payment';
    if (type === 'transactions') return renderFeeTransactionCard(student, sheetIndex);
    return renderFeeReportCard(student, sheetIndex);
  }

  function reportTypeLabel() {
    return currentReportType === 'transactions' ? 'fee transaction reports' : 'fee reports';
  }

  function renderFilterSummary() {
    return '';
  }

  function paintCardsChunked(summaryHtml, students, token) {
    if (!detailsListEl) return;
    var list = Array.isArray(students) ? students : [];
    if (!list.length) {
      detailsListEl.innerHTML = summaryHtml + '<p class="text-sm text-slate-500 dark:text-slate-400">No students found in this class.</p>';
      return;
    }
    var progressLabel = currentReportType === 'transactions' ? 'fee transaction reports' : 'fee reports';
    var showProgress = list.length > REPORT_CARD_CHUNK_SIZE;
    detailsListEl.innerHTML = summaryHtml +
      '<div id="ar-chunked-cards-root"></div>' +
      (showProgress ? '<p id="ar-chunked-progress" class="text-xs text-slate-500 dark:text-slate-400 mt-2 no-print">Building ' + progressLabel + '…</p>' : '');
    var root = document.getElementById('ar-chunked-cards-root');
    var prog = document.getElementById('ar-chunked-progress');
    if (!showProgress) {
      root.innerHTML = list.map(function (s, i) { return renderStudentCard(s, i); }).join('');
      return;
    }
    var i = 0;
    function step() {
      if (token !== reportLoadToken || !root) return;
      var end = Math.min(i + REPORT_CARD_CHUNK_SIZE, list.length);
      var chunk = '';
      for (; i < end; i++) {
        chunk += renderStudentCard(list[i], i);
      }
      root.insertAdjacentHTML('beforeend', chunk);
      if (prog) {
        if (i < list.length) prog.textContent = 'Rendered ' + i + ' of ' + list.length + ' ' + progressLabel + '…';
        else prog.remove();
      }
      if (i < list.length) setTimeout(function () { requestAnimationFrame(step); }, 0);
    }
    requestAnimationFrame(step);
  }

  function scheduleLoadDetails(immediate) {
    clearTimeout(reportLoadTimer);
    if (immediate) {
      loadDetails();
      return;
    }
    reportLoadTimer = setTimeout(loadDetails, REPORT_LOAD_DEBOUNCE_MS);
  }

  async function loadDetails() {
    if (!detailsListEl || !GENERATE_API) return;
    var levelId = val('fr-level');
    if (!levelId) {
      detailsListEl.innerHTML = '<p class="text-sm text-gray-500 dark:text-gray-400">Select a <span class="font-medium text-gray-700 dark:text-gray-300">class</span> above to generate ' + reportTypeLabel() + '.</p>';
      setGeneratedNow();
      return;
    }

    detailsListEl.innerHTML = '<p class="text-sm text-gray-500 dark:text-gray-400"><i class="fas fa-spinner fa-spin mr-1.5" aria-hidden="true"></i>Loading ' + reportTypeLabel() + '…</p>';
    var token = ++reportLoadToken;
    if (reportLoadAbort) {
      try { reportLoadAbort.abort(); } catch (e) { /* ignore */ }
    }
    reportLoadAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;

    var filters = { level_id: parseInt(levelId, 10) };
    var sid = val('fr-student');
    if (sid) filters.student_id = sid;
    filters.report_type = val('fr-report-type') || 'payment';
    currentReportType = filters.report_type;

    try {
      var fetchOpts = {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters: filters }),
      };
      if (reportLoadAbort) fetchOpts.signal = reportLoadAbort.signal;
      var res = await fetch(GENERATE_API, fetchOpts);
      if (token !== reportLoadToken) return;
      var data = await res.json().catch(function () { return {}; });
      if (token !== reportLoadToken) return;
      if (!res.ok || data.success === false) {
        detailsListEl.innerHTML = '<p class="text-sm text-red-600 dark:text-red-400">' + escapeHtml(data.message || ('Could not load ' + reportTypeLabel() + '.')) + '</p>';
        setGeneratedNow();
        return;
      }
      if (data.report_type) currentReportType = data.report_type;
      updateFeesPrintFooter();
      setGeneratedNow();
      paintCardsChunked(renderFilterSummary(), data.students || [], token);
    } catch (e) {
      if (e && e.name === 'AbortError') return;
      if (token !== reportLoadToken) return;
      detailsListEl.innerHTML = '<p class="text-sm text-red-600 dark:text-red-400">Failed to load ' + reportTypeLabel() + '.</p>';
      setGeneratedNow();
    }
  }

  function renderStudentSelect(students) {
    if (!studentSelectEl) return;
    studentSelectEl.innerHTML = '<option value="">All students</option>';
    (students || []).forEach(function (s) {
      var opt = document.createElement('option');
      opt.value = s.student_id != null ? String(s.student_id) : '';
      opt.textContent = (s.full_name || 'Student') + (s.student_id ? ' (' + s.student_id + ')' : '');
      studentSelectEl.appendChild(opt);
    });
    studentSelectEl.disabled = false;
    if (studentHiddenEl) studentHiddenEl.value = '';
    studentSelectEl.value = '';
  }

  function resetStudentSelect() {
    if (!studentSelectEl) return;
    studentSelectEl.innerHTML = '<option value="">Select a class first…</option>';
    studentSelectEl.disabled = true;
    if (studentHiddenEl) studentHiddenEl.value = '';
  }

  async function loadClassStudentRoster() {
    if (!studentSelectEl || !ROSTER_API) return;
    var lidStr = val('fr-level');
    var token = ++classRosterLoadToken;
    if (!lidStr) {
      resetStudentSelect();
      return;
    }
    studentSelectEl.disabled = true;
    studentSelectEl.innerHTML = '<option value="">Loading students…</option>';
    try {
      var res = await fetch(ROSTER_API, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ list_all: true, level_id: parseInt(lidStr, 10), level_view: 'individual' }),
      });
      var data = await res.json().catch(function () { return {}; });
      if (token !== classRosterLoadToken) return;
      if (!res.ok || data.success === false) {
        studentSelectEl.innerHTML = '<option value="">Could not load students</option>';
        studentSelectEl.disabled = true;
        return;
      }
      renderStudentSelect(Array.isArray(data.students) ? data.students : []);
    } catch (e) {
      if (token !== classRosterLoadToken) return;
      studentSelectEl.innerHTML = '<option value="">Could not load students</option>';
      studentSelectEl.disabled = true;
    }
  }

  function ensureDefaultClassSelected() {
    if (!levelEl || !levelEl.options || levelEl.options.length < 2) return false;
    if (val('fr-level')) return false;
    levelEl.selectedIndex = 1;
    return true;
  }

  function syncPrintPageMode() {
    var wrap = document.getElementById('ar-preview-wrap');
    if (!wrap) return;
    var cards = detailsListEl ? detailsListEl.querySelectorAll('article.ar-rc-individual') : [];
    wrap.classList.remove('ar-print-single-sheet', 'ar-print-individual-batch');
    if (cards.length === 1) wrap.classList.add('ar-print-single-sheet');
    else if (cards.length > 1) wrap.classList.add('ar-print-individual-batch');
  }

  var printPreviewRestore = null;

  function normalizeIndividualReportPrintPages() {
    var wrap = document.getElementById('ar-preview-wrap');
    if (!wrap || !wrap.classList.contains('ar-print-individual-batch')) return;
    var cards = wrap.querySelectorAll('#ar-details-list article.ar-rc-individual');
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      card.classList.add('ar-print-page-sheet');
      if (i > 0) card.classList.add('ar-print-page-follow');
      else card.classList.remove('ar-print-page-follow');
    }
  }

  function detachPreviewForPrint() {
    var wrap = document.getElementById('ar-preview-wrap');
    if (!wrap) return;
    if (printPreviewRestore && wrap.parentNode === document.body) return;
    printPreviewRestore = {
      parent: wrap.parentNode,
      next: wrap.nextSibling,
    };
    document.body.appendChild(wrap);
    document.documentElement.classList.add('ar-print-individual-batch-doc');
  }

  function restorePreviewAfterPrint() {
    document.documentElement.classList.remove('ar-print-individual-batch-doc');
    var wrap = document.getElementById('ar-preview-wrap');
    if (!printPreviewRestore || !wrap || !printPreviewRestore.parent) {
      printPreviewRestore = null;
      return;
    }
    if (printPreviewRestore.next && printPreviewRestore.next.parentNode === printPreviewRestore.parent) {
      printPreviewRestore.parent.insertBefore(wrap, printPreviewRestore.next);
    } else {
      printPreviewRestore.parent.appendChild(wrap);
    }
    printPreviewRestore = null;
  }

  function updateFeesPrintFooter() {
    var footerTitle = document.getElementById('fr-fees-print-footer-title');
    if (!footerTitle) return;
    var title = currentReportType === 'transactions' ? 'Fee transaction report' : 'Fee payment report';
    footerTitle.textContent = title;
  }

  function prepareFeeReportPrint() {
    syncPrintPageMode();
    normalizeIndividualReportPrintPages();
    detachPreviewForPrint();
    var inner = document.querySelector('main.overflow-hidden > div.overflow-y-auto');
    if (inner) inner.scrollTop = 0;
    window.scrollTo(0, 0);
  }

  function runFeeReportPrint(opts) {
    opts = opts || {};
    if (!detailsListEl || !detailsListEl.querySelector('article.ar-rc-individual')) {
      window.alert('Generate the reports first, then print or download.');
      return;
    }
    syncPrintPageMode();
    normalizeIndividualReportPrintPages();
    updateFeesPrintFooter();
    if (typeof window.printAccountsInFrame === 'function') {
      if (opts.pdfHint) {
        var toast = document.getElementById('ar-print-pdf-toast');
        if (toast) {
          toast.classList.remove('hidden');
          window.clearTimeout(runFeeReportPrint._t);
          runFeeReportPrint._t = window.setTimeout(function () { toast.classList.add('hidden'); }, 6000);
        }
      }
      var feeTitle = currentReportType === 'transactions' ? 'Fee transaction report' : 'Fee payment report';
      window.printAccountsInFrame({
        title: (SCHOOL_INFO.name || 'School') + ' — ' + feeTitle,
        htmlClass: 'acr-accounts-print ar-print-academic-report',
        bodyClass: 'acr-accounts-print ar-print-academic-report',
        collect: window.collectFeesReportPrintHtml,
      });
      return;
    }
    prepareFeeReportPrint();
    if (opts.pdfHint) {
      var toast = document.getElementById('ar-print-pdf-toast');
      if (toast) {
        toast.classList.remove('hidden');
        window.clearTimeout(runFeeReportPrint._t);
        runFeeReportPrint._t = window.setTimeout(function () { toast.classList.add('hidden'); }, 6000);
      }
    }
    window.print();
  }

  window.runFeeReportPrint = runFeeReportPrint;

  if (levelEl) {
    levelEl.addEventListener('change', function () {
      loadClassStudentRoster();
      scheduleLoadDetails();
    });
  }
  if (reportTypeEl) {
    reportTypeEl.addEventListener('change', function () {
      scheduleLoadDetails(true);
    });
  }
  if (studentSelectEl) {
    studentSelectEl.addEventListener('change', function () {
      if (studentHiddenEl) studentHiddenEl.value = String(studentSelectEl.value || '').trim();
      scheduleLoadDetails(true);
    });
  }

  var pdfBtn = document.getElementById('ar-download-pdf-btn');
  if (pdfBtn) pdfBtn.addEventListener('click', function () { runFeeReportPrint({ pdfHint: true }); });

  window.addEventListener('beforeprint', function () {
    if (window.__acrIframePrintActive) return;
    if (!document.getElementById('ar-preview-wrap')) return;
    document.documentElement.classList.add('ar-print-academic-report', 'acr-accounts-print');
    if (typeof window.pinAccountsPrintFooters === 'function') {
      window.pinAccountsPrintFooters();
    }
    updateFeesPrintFooter();
    prepareFeeReportPrint();
  });
  window.addEventListener('afterprint', function () {
    document.documentElement.classList.remove('ar-print-academic-report', 'acr-accounts-print');
    if (typeof window.unpinAccountsPrintFooters === 'function') {
      window.unpinAccountsPrintFooters();
    }
    restorePreviewAfterPrint();
    var wrap = document.getElementById('ar-preview-wrap');
    if (wrap) wrap.classList.remove('ar-print-single-sheet', 'ar-print-individual-batch');
  });

  if (ensureDefaultClassSelected()) {
    loadClassStudentRoster();
  }
  setTimeout(function () { scheduleLoadDetails(); }, 80);
})();
