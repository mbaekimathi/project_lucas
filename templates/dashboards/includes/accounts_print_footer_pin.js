/**
 * Accounts print layout: header once at top, footer once at bottom of last page.
 * A spacer before the footer fills the remaining space on the final printed page.
 */
(function () {
  if (window.__acrAccountsPrintFooterPin) return;
  window.__acrAccountsPrintFooterPin = true;

  var relocatedFooters = [];
  var spacerNodes = [];

  var PAGE_HEIGHT_MM = 297;
  var PAGE_MARGIN_TOP_MM = 7;
  var PAGE_MARGIN_BOTTOM_MM = 8;
  var PAGE_MARGIN_SIDE_MM = 8;
  var PAGE_WIDTH_MM = 210;

  function findPrintFooter(doc) {
    doc = doc || document;
    return doc.getElementById('acr-print-footer')
      || doc.getElementById('fr-print-footer')
      || doc.getElementById('fr-fees-print-footer')
      || doc.getElementById('ar-academic-print-footer')
      || doc.getElementById('ar-cal-print-footer')
      || doc.getElementById('pay-print-footer')
      || doc.getElementById('sd-print-footer')
      || doc.querySelector('.acr-print-footer');
  }

  function findPrintFlowAnchor(doc) {
    doc = doc || document;
    return doc.getElementById('acr-report-body')
      || doc.getElementById('acr-pcb-book-section')
      || doc.getElementById('fr-table-wrap')
      || doc.getElementById('fr-vote-detail')
      || doc.getElementById('fr-summary')
      || doc.getElementById('ar-preview-wrap')
      || doc.getElementById('ar-details-list')
      || doc.querySelector('.acr-print-content')
      || doc.querySelector('.acr-page .acr-inner, .fr-report-shell .fr-inner, .acr-pcb-page .acr-inner');
  }

  function mmToPx(mm, doc) {
    doc = doc || document;
    var host = doc.body || doc.documentElement;
    if (!host) return Math.round(mm * 3.7795275591);
    var probe = doc.createElement('div');
    probe.style.cssText = 'position:absolute;visibility:hidden;height:' + mm + 'mm;width:1px;pointer-events:none;';
    host.appendChild(probe);
    var px = probe.offsetHeight;
    probe.parentNode.removeChild(probe);
    return px;
  }

  function getPrintablePageHeightPx(doc) {
    return mmToPx(PAGE_HEIGHT_MM - PAGE_MARGIN_TOP_MM - PAGE_MARGIN_BOTTOM_MM, doc);
  }

  function getPrintablePageWidthPx(doc) {
    return mmToPx(PAGE_WIDTH_MM - (PAGE_MARGIN_SIDE_MM * 2), doc);
  }

  function measureElementHeight(el, doc) {
    if (!el) return 0;
    doc = doc || el.ownerDocument || document;
    var win = doc.defaultView || window;
    var h = el.offsetHeight || el.getBoundingClientRect().height || 0;
    var style = win.getComputedStyle(el);
    h += parseFloat(style.marginTop) || 0;
    h += parseFloat(style.marginBottom) || 0;
    return Math.ceil(h);
  }

  function topWithin(el, ancestor) {
    if (!el || !ancestor) return 0;
    return el.getBoundingClientRect().top - ancestor.getBoundingClientRect().top;
  }

  function contentEndY(flow, anchor, footer) {
    if (anchor) {
      return topWithin(anchor, flow) + anchor.scrollHeight;
    }
    return topWithin(footer, flow);
  }

  function computeFooterSpacerPx(pageH, contentStartY, contentEndY, footerH) {
    var contentLen = Math.max(0, contentEndY - contentStartY);

    if (contentLen <= 0) {
      return Math.max(0, pageH - contentStartY - footerH);
    }

    var firstPageRoom = Math.max(0, pageH - contentStartY);

    if (contentLen <= firstPageRoom) {
      return Math.max(0, pageH - contentEndY - footerH);
    }

    var afterFirst = contentLen - firstPageRoom;
    var remainder = afterFirst % pageH;

    if (remainder === 0) {
      return Math.max(0, pageH - footerH);
    }

    var spaceLeft = pageH - remainder;
    if (spaceLeft >= footerH) {
      return Math.max(0, spaceLeft - footerH);
    }

    return Math.max(0, spaceLeft + (pageH - footerH));
  }

  function ensurePrintFlowWrap(doc) {
    var body = doc.body;
    if (!body) return null;
    var existing = body.querySelector('.acr-print-flow');
    if (existing && existing.parentNode === body) return existing;
    var flow = doc.createElement('div');
    flow.className = 'acr-print-flow';
    while (body.firstChild) {
      flow.appendChild(body.firstChild);
    }
    body.appendChild(flow);
    return flow;
  }

  function ensureFooterSpacer(doc, footer) {
    var spacer = footer.previousElementSibling;
    if (!spacer || !spacer.classList.contains('acr-print-footer-spacer')) {
      spacer = doc.createElement('div');
      spacer.className = 'acr-print-footer-spacer';
      spacer.setAttribute('aria-hidden', 'true');
      footer.parentNode.insertBefore(spacer, footer);
      if (doc === document) {
        spacerNodes.push({ node: spacer, parent: spacer.parentNode });
      }
    }
    return spacer;
  }

  function applyMeasureLayout(doc) {
    var body = doc.body;
    var flow = doc.querySelector('.acr-print-flow');
    if (!body) return;
    var widthPx = getPrintablePageWidthPx(doc);
    body.style.width = widthPx + 'px';
    body.style.maxWidth = widthPx + 'px';
    body.style.margin = '0';
    body.style.padding = '0';
    body.style.boxSizing = 'border-box';
    if (flow) {
      flow.style.width = '100%';
      flow.style.maxWidth = '100%';
      flow.style.boxSizing = 'border-box';
    }
  }

  function clearMeasureLayout(doc) {
    var body = doc.body;
    var flow = doc.querySelector('.acr-print-flow');
    if (body) {
      body.style.width = '';
      body.style.maxWidth = '';
      body.style.margin = '';
      body.style.padding = '';
      body.style.boxSizing = '';
    }
    if (flow) {
      flow.style.width = '';
      flow.style.maxWidth = '';
      flow.style.boxSizing = '';
    }
  }

  function placeFooterAfterContent(doc) {
    doc = doc || document;
    if (doc === document && window.__acrIframePrintActive) return;
    var footer = findPrintFooter(doc);
    var anchor = findPrintFlowAnchor(doc);
    if (!footer || !anchor || !anchor.parentNode) return;
    if (footer.dataset.acrFlowPlaced === '1') return;
    if (doc === document) {
      relocatedFooters.push({
        node: footer,
        parent: footer.parentNode,
        next: footer.nextSibling,
      });
    }
    footer.dataset.acrFlowPlaced = '1';
    anchor.parentNode.insertBefore(footer, anchor.nextSibling);
  }

  function forceReflow(doc) {
    if (!doc || !doc.body) return;
    void doc.body.offsetHeight;
  }

  function layoutAccountsPrintFooter(doc) {
    doc = doc || document;
    var footer = findPrintFooter(doc);
    if (!footer) return;

    var htmlEl = doc.documentElement;
    var measure = doc !== document;
    if (measure) htmlEl.classList.add('acr-accounts-print-measure');

    try {
      ensurePrintFlowWrap(doc);
      placeFooterAfterContent(doc);

      var flow = doc.querySelector('.acr-print-flow') || doc.body;
      if (!flow) return;

      applyMeasureLayout(doc);

      var spacer = ensureFooterSpacer(doc, footer);
      spacer.style.height = '0px';
      spacer.style.minHeight = '0';
      spacer.style.width = '100%';
      spacer.style.display = 'block';
      forceReflow(doc);

      var letterhead = flow.querySelector('.acr-print-letterhead, #acr-print-letterhead, #fr-print-letterhead');
      var anchor = findPrintFlowAnchor(doc);
      var pageH = getPrintablePageHeightPx(doc);
      var footerH = measureElementHeight(footer, doc);
      var contentStartY = anchor
        ? topWithin(anchor, flow)
        : (letterhead
          ? topWithin(letterhead, flow) + measureElementHeight(letterhead, doc)
          : 0);
      var endY = contentEndY(flow, anchor, footer);
      var spacerPx = computeFooterSpacerPx(pageH, contentStartY, endY, footerH);
      spacerPx = Math.min(spacerPx, Math.max(0, pageH - footerH));

      spacer.style.height = Math.max(0, spacerPx) + 'px';
      forceReflow(doc);
    } finally {
      clearMeasureLayout(doc);
      if (measure) htmlEl.classList.remove('acr-accounts-print-measure');
    }
  }

  function restoreFooterPlacement() {
    while (relocatedFooters.length) {
      var item = relocatedFooters.pop();
      var footer = item.node;
      if (!footer || !item.parent) continue;
      delete footer.dataset.acrFlowPlaced;
      if (item.next && item.next.parentNode === item.parent) {
        item.parent.insertBefore(footer, item.next);
      } else if (item.parent) {
        item.parent.appendChild(footer);
      }
    }
  }

  function cleanupFooterSpacers() {
    spacerNodes.forEach(function (item) {
      var spacer = item.node;
      if (!spacer || !spacer.parentNode) return;
      spacer.style.height = '';
      spacer.style.minHeight = '';
      spacer.style.width = '';
      spacer.style.display = '';
      if (spacer.parentNode) spacer.parentNode.removeChild(spacer);
    });
    spacerNodes = [];
  }

  function preparePrintFlow() {
    if (window.__acrIframePrintActive) return;
    document.documentElement.classList.add('acr-accounts-print');
    layoutAccountsPrintFooter(document);
  }

  function cleanupPrintFlow() {
    document.documentElement.classList.remove('acr-accounts-print');
    cleanupFooterSpacers();
    restoreFooterPlacement();
  }

  window.layoutAccountsPrintFooter = layoutAccountsPrintFooter;
  window.pinAccountsPrintHeaders = function () {};
  window.unpinAccountsPrintHeaders = function () {};
  window.pinAccountsPrintFooters = preparePrintFlow;
  window.unpinAccountsPrintFooters = cleanupPrintFlow;
  window.pinAccountsPrintChrome = preparePrintFlow;
  window.unpinAccountsPrintChrome = cleanupPrintFlow;
  window.addEventListener('beforeprint', preparePrintFlow);
  window.addEventListener('afterprint', cleanupPrintFlow);
})();
