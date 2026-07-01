/**
 * Build shared accounts-style print letterhead HTML for academic / fees reports.
 */
(function () {
  if (window.AcademicPrintLetterhead) return;

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function schoolLocationHtml(info) {
    var loc = (info && (info.location || info.address)) || '';
    if (!loc) return '';
    return '<p class="acr-print-letterhead__location">' + escapeHtml(loc) + '</p>';
  }

  function schoolContactsHtml(info) {
    info = info || {};
    var parts = [];
    if (info.email) {
      parts.push(
        '<div class="acr-print-letterhead__school-contact">' +
          '<dt class="acr-print-letterhead__detail-label">Email</dt>' +
          '<dd class="acr-print-letterhead__detail-value">' + escapeHtml(info.email) + '</dd>' +
        '</div>'
      );
    }
    if (info.phone) {
      parts.push(
        '<div class="acr-print-letterhead__school-contact">' +
          '<dt class="acr-print-letterhead__detail-label">Tel</dt>' +
          '<dd class="acr-print-letterhead__detail-value">' + escapeHtml(info.phone) + '</dd>' +
        '</div>'
      );
    }
    if (!parts.length) return '';
    return '<dl class="acr-print-letterhead__school-contacts">' + parts.join('') + '</dl>';
  }

  function schoolWebsiteQrHtml(info) {
    var url = (info && info.websiteQrDataUrl) || '';
    if (!url) return '';
    return '' +
      '<div class="acr-print-letterhead__qr">' +
        '<img src="' + escapeHtml(url) + '" alt="QR code — scan to visit school website" class="acr-print-letterhead__qr-img" width="96" height="96">' +
        '<p class="acr-print-letterhead__qr-label">School website</p>' +
        '<p class="acr-print-letterhead__qr-hint">Scan to visit</p>' +
      '</div>';
  }

  function schoolBrandRightHtml(info) {
    var qr = schoolWebsiteQrHtml(info);
    if (!qr) {
      return '<div class="acr-print-letterhead__brand-right acr-print-letterhead__brand-right--empty"></div>';
    }
    return '<div class="acr-print-letterhead__brand-right">' + qr + '</div>';
  }

  function build(opts) {
    opts = opts || {};
    var info = opts.school || {};
    var title = opts.reportTitle || 'Report';
    var period = opts.periodLabel != null ? opts.periodLabel : (opts.period || '—');
    var generated = opts.generatedAt != null ? opts.generatedAt : (opts.generated || '—');
    var logoInner = info.logo
      ? '<img src="' + escapeHtml(info.logo) + '" alt="School logo" class="acr-print-letterhead__logo">'
      : '';
    var metaExtra = opts.metaExtra
      ? '<p class="acr-print-letterhead__meta-extra">' + escapeHtml(opts.metaExtra) + '</p>'
      : '';
    var primaryHtml = '';
    if (opts.metaPrimary) {
      primaryHtml =
        '<div class="acr-print-letterhead__meta-item">' +
          '<dt>' + escapeHtml(opts.metaPrimaryLabel || 'Account') + '</dt>' +
          '<dd>' + escapeHtml(opts.metaPrimary) + '</dd>' +
        '</div>';
    }
    var variant = String(opts.variant || '').trim();
    var letterheadClass = 'acr-print-letterhead' + (variant ? ' acr-print-letterhead--' + variant : '');
    var showPeriod = opts.showPeriod !== false;
    var showGenerated = opts.showGenerated !== false;
    var periodHtml = showPeriod
      ? '<div class="acr-print-letterhead__meta-item">' +
          '<dt>Period</dt>' +
          '<dd>' + escapeHtml(period) + '</dd>' +
        '</div>'
      : '';
    var generatedHtml = showGenerated
      ? '<div class="acr-print-letterhead__meta-item">' +
          '<dt>Generated</dt>' +
          '<dd>' + escapeHtml(generated) + '</dd>' +
        '</div>'
      : '';
    var subtitleHtml = opts.subtitle
      ? '<p class="acr-print-letterhead__meta-subtitle">' + escapeHtml(opts.subtitle) + '</p>'
      : '';
    return '' +
      '<header class="ar-rc-header">' +
        '<div class="' + letterheadClass + '">' +
          '<div class="acr-print-letterhead__brand">' +
            '<div class="acr-print-letterhead__brand-left">' + logoInner + '</div>' +
            '<div class="acr-print-letterhead__school-block min-w-0">' +
              '<h1 class="acr-print-letterhead__school">' + escapeHtml(info.name || 'School') + '</h1>' +
              schoolLocationHtml(info) +
              schoolContactsHtml(info) +
            '</div>' +
            schoolBrandRightHtml(info) +
          '</div>' +
          '<div class="acr-print-letterhead__doc">' +
            '<h2 class="acr-print-letterhead__title">' + escapeHtml(title) + '</h2>' +
            '<dl class="acr-print-letterhead__meta-grid">' +
              primaryHtml +
              periodHtml +
              generatedHtml +
            '</dl>' +
            subtitleHtml +
            metaExtra +
          '</div>' +
        '</div>' +
      '</header>';
  }

  window.AcademicPrintLetterhead = {
    build: build,
    escapeHtml: escapeHtml,
  };
})();
