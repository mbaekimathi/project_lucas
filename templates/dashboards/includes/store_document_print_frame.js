/**
 * Print store LPO / GRN documents via the shared accounts print iframe.
 */
(function () {
  if (window.__sdStoreDocumentPrint) return;
  window.__sdStoreDocumentPrint = true;

  window.printStoreDocument = function (opts) {
    opts = opts || {};
    if (typeof window.syncStorePrintFooter === 'function') {
      window.syncStorePrintFooter();
    }
    var root = document.querySelector('.sd-doc-print-root');
    if (!root || typeof window.printAccountsInFrame !== 'function') {
      window.print();
      return;
    }
    var clone = root.cloneNode(true);
    clone.querySelectorAll('.no-print, .sd-doc-actions, .sd-doc-banner').forEach(function (node) {
      if (node.parentNode) node.parentNode.removeChild(node);
    });
    var footerId = opts.footerId || 'sd-print-footer';
    var footer = document.getElementById(footerId);
    var html = clone.innerHTML;
    if (footer && !clone.querySelector('[id="' + footerId.replace(/"/g, '\\"') + '"]')) {
      html += footer.outerHTML;
    }
    window.printAccountsInFrame({
      title: opts.title || document.title,
      html: html,
      htmlClass: 'acr-accounts-print sd-doc-print',
      bodyClass: 'acr-accounts-print sd-doc-page sd-doc-page--compact',
    });
  };
})();
