/**
 * Print accounts reports from a hidden iframe (about:blank) so the browser
 * does not stamp the app URL in the print header/footer area.
 */
(function () {
  if (window.__acrAccountsPrintFrame) return;
  window.__acrAccountsPrintFrame = true;

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function syncPrintMeta() {
    if (typeof window.syncAccountsPrintLetterhead === 'function') {
      window.syncAccountsPrintLetterhead();
    } else if (typeof window.syncAcrPrintLetterhead === 'function') {
      window.syncAcrPrintLetterhead();
    }
    if (typeof window.syncAccountsPrintFooter === 'function') {
      window.syncAccountsPrintFooter();
    }
  }

  function collectPrintBrandVars() {
    var root = getComputedStyle(document.documentElement);
    function pick(name, fallback) {
      var value = root.getPropertyValue(name).trim();
      return value || fallback;
    }
    var primary = pick('--print-brand-primary', pick('--brand-primary', '#800020'));
    var secondary = pick('--print-brand-secondary', pick('--brand-secondary', '#A00030'));
    var accent = pick('--print-brand-accent', pick('--brand-accent', '#5C0014'));
    return ':root,html.acr-accounts-print,html.acr-accounts-print-measure{'
      + '--print-brand-primary:' + primary + ';'
      + '--print-brand-secondary:' + secondary + ';'
      + '--print-brand-accent:' + accent + ';'
      + '--brand-primary:' + primary + ';'
      + '--brand-secondary:' + secondary + ';'
      + '--brand-accent:' + accent + ';'
      + '--acr-teal:' + primary + ';'
      + '--print-brand-border:' + primary + ';'
      + '}';
  }

  function collectInlineStyles() {
    var css = collectPrintBrandVars();
    document.querySelectorAll('style').forEach(function (node) {
      css += node.textContent || '';
    });
    css += [
      '@media print{',
      'a[href]::after,a[href^="http"]::after,a[href^="/"]::after{content:none!important;display:none!important;}',
      'html.acr-accounts-print.ar-print-academic-report #ar-preview-wrap,',
      'html.acr-accounts-print.ar-print-academic-report #ar-preview-wrap *,',
      'html.acr-accounts-print.ar-print-academic-report .acr-print-footer,',
      'html.acr-accounts-print.ar-print-academic-report .acr-print-footer *{visibility:visible!important;}',
      '}',
    ].join('');
    return css;
  }

  function absolutizePrintAssetUrls(html) {
    var origin = (window.location.origin || '').replace(/\/$/, '');
    if (!origin || !html) return html || '';
    return String(html)
      .replace(/\ssrc="\/(static|uploads)\//g, ' src="' + origin + '/$1/')
      .replace(/\ssrc='\/(static|uploads)\//g, " src='" + origin + '/$1/')
      .replace(/\shref="\/(static|uploads)\//g, ' href="' + origin + '/$1/');
  }

  function stripPrintLinks(html) {
    if (!html) return '';
    var doc = new DOMParser().parseFromString('<div id="acr-print-root">' + html + '</div>', 'text/html');
    var root = doc.getElementById('acr-print-root');
    if (!root) return html;
    root.querySelectorAll('a[href]').forEach(function (anchor) {
      var span = doc.createElement('span');
      span.innerHTML = anchor.innerHTML;
      if (anchor.className) span.className = anchor.className;
      anchor.parentNode.replaceChild(span, anchor);
    });
    return root.innerHTML;
  }

  function collectStylesheetLinks() {
    var links = [];
    document.querySelectorAll('link[rel="stylesheet"]').forEach(function (node) {
      if (node.href) links.push('<link rel="stylesheet" href="' + escapeHtml(node.href) + '">');
    });
    return links.join('');
  }

  function waitForFrameReady(frameWin, callback) {
    var doc = frameWin.document;
    var pending = doc.querySelectorAll('link[rel="stylesheet"]').length;
    var images = doc.querySelectorAll('img');
    var imgPending = images.length;
    var done = false;

    function finish() {
      if (done) return;
      done = true;
      callback();
    }

    if (!pending && !imgPending) {
      setTimeout(finish, 80);
      return;
    }

    if (pending) {
      doc.querySelectorAll('link[rel="stylesheet"]').forEach(function (link) {
        link.onload = link.onerror = function () {
          pending -= 1;
          if (pending <= 0 && imgPending <= 0) finish();
        };
      });
    }

    if (imgPending) {
      images.forEach(function (img) {
        if (img.complete) {
          imgPending -= 1;
          if (imgPending <= 0 && pending <= 0) finish();
          return;
        }
        img.onload = img.onerror = function () {
          imgPending -= 1;
          if (imgPending <= 0 && pending <= 0) finish();
        };
      });
    }

    setTimeout(finish, 2500);
  }

  function printAccountsInFrame(opts) {
    opts = opts || {};
    syncPrintMeta();

    var html = opts.html;
    if (!html && typeof opts.collect === 'function') html = opts.collect();
    if (!html) return false;

    var title = opts.title || document.title || 'Report';
    var htmlClass = opts.htmlClass || 'acr-accounts-print';
    var bodyClass = opts.bodyClass || htmlClass;
    html = stripPrintLinks(absolutizePrintAssetUrls(html));
    if (html.indexOf('acr-print-flow') === -1) {
      html = '<div class="acr-print-flow">' + html + '</div>';
    }

    var iframe = document.createElement('iframe');
    iframe.setAttribute('title', 'Print preview');
    iframe.setAttribute('aria-hidden', 'true');
    iframe.setAttribute('src', 'about:blank');
    iframe.style.cssText = 'position:fixed;left:-10000px;top:0;width:210mm;height:auto;border:0;visibility:hidden;overflow:visible;z-index:-1';
    document.body.appendChild(iframe);

    var frameWin = iframe.contentWindow;
    var doc = frameWin.document;

    doc.open();
    doc.write(
      '<!DOCTYPE html><html class="' + escapeHtml(htmlClass) + '"><head>' +
      '<meta charset="utf-8">' +
      '<title>' + escapeHtml(title) + '</title>' +
      collectStylesheetLinks() +
      '<style>' + collectInlineStyles() + '</style>' +
      '</head><body class="' + escapeHtml(bodyClass) + '">' +
      html +
      '</body></html>'
    );
    doc.close();

    window.__acrIframePrintActive = true;
    waitForFrameReady(frameWin, function () {
      try {
        var idoc = frameWin.document;
        idoc.documentElement.classList.add('acr-accounts-print');
        htmlClass.split(/\s+/).forEach(function (cls) {
          if (cls) idoc.documentElement.classList.add(cls);
        });
        if (bodyClass) {
          bodyClass.split(/\s+/).forEach(function (cls) {
            if (cls) idoc.body.classList.add(cls);
          });
        }
        if (typeof window.layoutAccountsPrintFooter === 'function') {
          window.requestAnimationFrame(function () {
            window.layoutAccountsPrintFooter(idoc);
            window.setTimeout(function () {
              window.layoutAccountsPrintFooter(idoc);
              frameWin.focus();
              frameWin.print();
            }, 150);
          });
        } else {
          frameWin.focus();
          frameWin.print();
        }
      } finally {
        setTimeout(function () {
          window.__acrIframePrintActive = false;
          if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
        }, 2000);
      }
    });
    return true;
  }

  function stripPrintUiFromClone(root) {
    if (!root) return;
    root.querySelectorAll(
      '.no-print, #acr-print-letterhead, #fr-print-letterhead, .acr-masthead, .fr-masthead, .acr-print-footer, .acr-toolbar, .fr-toolbar, .acr-breadcrumb, .fr-breadcrumb, #fr-fees-print-footer-wrap'
    ).forEach(function (node) {
      if (node.parentNode) node.parentNode.removeChild(node);
    });
  }

  window.acrStripPrintUiFromClone = stripPrintUiFromClone;

  function collectAcrAccountReportHtml() {
    var parts = [];
    var letterhead = document.getElementById('acr-print-letterhead');
    if (letterhead) parts.push(letterhead.outerHTML);
    var body = document.getElementById('acr-report-body');
    if (body) parts.push('<div id="acr-report-body">' + body.innerHTML + '</div>');
    var footer = document.querySelector('.acr-print-footer');
    if (footer) parts.push(footer.outerHTML);
    return parts.join('');
  }

  function collectFrReportShellHtml() {
    var parts = [];
    var letterhead = document.getElementById('fr-print-letterhead');
    if (letterhead) parts.push(letterhead.outerHTML);
    var summary = document.getElementById('fr-summary');
    if (summary && !summary.classList.contains('hidden')) {
      parts.push('<div id="fr-summary">' + summary.innerHTML + '</div>');
    }
    var vote = document.getElementById('fr-vote-detail');
    if (vote && !vote.classList.contains('hidden')) {
      parts.push('<div id="fr-vote-detail">' + vote.innerHTML + '</div>');
    }
    var tableWrap = document.getElementById('fr-table-wrap');
    if (tableWrap && !tableWrap.classList.contains('hidden')) {
      parts.push('<div id="fr-table-wrap">' + tableWrap.innerHTML + '</div>');
    }
    var footer = document.querySelector('.acr-print-footer');
    if (footer) parts.push(footer.outerHTML);
    return parts.join('');
  }

  function collectFeesReportHtml() {
    var wrap = document.getElementById('ar-preview-wrap');
    if (!wrap) return '';
    var clone = wrap.cloneNode(true);
    clone.querySelectorAll('.no-print').forEach(function (node) {
      if (node.parentNode) node.parentNode.removeChild(node);
    });
    var footer = document.getElementById('fr-fees-print-footer')
      || document.getElementById('ar-academic-print-footer')
      || document.getElementById('ar-cal-print-footer')
      || document.querySelector('.acr-print-footer');
    if (footer) {
      var footerId = String(footer.id || '');
      if (footerId && !clone.querySelector('[id="' + footerId.replace(/"/g, '\\"') + '"]')) {
        clone.appendChild(footer.cloneNode(true));
      }
    }
    return clone.outerHTML;
  }

  function collectPcbPrintHtml() {
    var parts = [];
    var letterhead = document.getElementById('acr-print-letterhead');
    if (letterhead) parts.push(letterhead.outerHTML);
    var section = document.getElementById('acr-pcb-book-section');
    if (section) parts.push('<div id="acr-report-body">' + section.outerHTML + '</div>');
    var footer = document.querySelector('.acr-print-footer');
    if (footer) parts.push(footer.outerHTML);
    return parts.join('');
  }

  window.printAccountsInFrame = printAccountsInFrame;
  window.collectAcrAccountReportPrintHtml = collectAcrAccountReportHtml;
  window.collectPcbPrintHtml = collectPcbPrintHtml;
  window.collectFrReportShellPrintHtml = collectFrReportShellHtml;
  window.collectFeesReportPrintHtml = collectFeesReportHtml;

  window.printFrReportShell = function () {
    return printAccountsInFrame({
      title: document.title,
      htmlClass: 'acr-accounts-print fr-print-doc',
      bodyClass: 'acr-accounts-print fr-print-doc',
      collect: collectFrReportShellHtml,
    });
  };

  window.printAccountsPage = function () {
    return printAccountsInFrame({
      title: document.title,
      htmlClass: 'acr-accounts-print acr-report-print-doc',
      bodyClass: 'acr-accounts-print acr-report-print-doc',
      collect: function () {
        var parts = [];
        var letterhead = document.getElementById('acr-print-letterhead');
        if (letterhead) parts.push(letterhead.outerHTML);
        var inner = document.querySelector('.acr-page .acr-inner');
        if (inner) {
          var clone = inner.cloneNode(true);
          if (typeof window.acrStripPrintUiFromClone === 'function') {
            window.acrStripPrintUiFromClone(clone);
          } else {
            clone.querySelectorAll('.no-print').forEach(function (node) {
              node.parentNode.removeChild(node);
            });
          }
          parts.push('<div class="acr-print-content">' + clone.innerHTML + '</div>');
        }
        var footer = document.querySelector('.acr-print-footer');
        if (footer) parts.push(footer.outerHTML);
        return parts.join('');
      },
    });
  };

  function routeAccountsPrintShortcut(event) {
    if (!(event.ctrlKey || event.metaKey) || String(event.key || '').toLowerCase() !== 'p') return;
    var handler = null;
    if (typeof window.printAccountReport === 'function' && document.querySelector('.acr-report-page')) {
      handler = window.printAccountReport;
    } else if (typeof window.printAccountsPage === 'function' && document.getElementById('acr-print-letterhead') && document.querySelector('.acr-page')) {
      handler = window.printAccountsPage;
    } else if (typeof window.printPettyCashBook === 'function' && document.getElementById('acr-pcb-book-section')) {
      handler = window.printPettyCashBook;
    } else if (typeof window.printFrReportShell === 'function' && document.querySelector('.fr-report-shell')) {
      handler = window.printFrReportShell;
    } else if (typeof window.runFeeReportPrint === 'function' && document.getElementById('ar-preview-wrap')) {
      handler = window.runFeeReportPrint;
    }
    if (!handler) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    handler();
  }

  document.addEventListener('keydown', routeAccountsPrintShortcut, true);
})();
