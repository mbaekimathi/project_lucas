(function () {
  var deferredPrompt = null;
  var DISMISS_KEY = 'pwaInstallBannerDismissed';

  function isStandalone() {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: fullscreen)').matches ||
      window.navigator.standalone === true
    );
  }

  function isIos() {
    return (
      /iPad|iPhone|iPod/.test(navigator.userAgent) &&
      !window.MSStream
    );
  }

  function isDismissed() {
    try {
      return sessionStorage.getItem(DISMISS_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  function setDismissed() {
    try {
      sessionStorage.setItem(DISMISS_KEY, '1');
    } catch (e2) {
      /* ignore */
    }
  }

  window.pwaInstall = {
    canPrompt: function () {
      return !!deferredPrompt && !isStandalone();
    },
    isStandalone: isStandalone,
    isIos: isIos,
    install: function () {
      if (!deferredPrompt) {
        return Promise.resolve(false);
      }
      deferredPrompt.prompt();
      return deferredPrompt.userChoice.then(function (choice) {
        deferredPrompt = null;
        window.dispatchEvent(new CustomEvent('pwa-installed'));
        return choice.outcome === 'accepted';
      });
    },
  };

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    window.dispatchEvent(new CustomEvent('pwa-install-available'));
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    try {
      sessionStorage.removeItem(DISMISS_KEY);
    } catch (e3) {
      /* ignore */
    }
    window.dispatchEvent(new CustomEvent('pwa-installed'));
  });

  function syncBodyPadding() {
    var visible = false;
    document.querySelectorAll('[data-pwa-install-root]').forEach(function (root) {
      if (!root.hidden) {
        visible = true;
      }
    });
    document.body.classList.toggle('has-pwa-install-bar', visible);
  }

  function refreshInstallRoots() {
    document.querySelectorAll('[data-pwa-install-root]').forEach(function (root) {
      if (isStandalone() || isDismissed()) {
        root.hidden = true;
        return;
      }
      var btn = root.querySelector('[data-pwa-install-btn]');
      var iosPanel = root.querySelector('[data-pwa-install-ios-help]');
      var canShow = window.pwaInstall.canPrompt() || isIos();
      root.hidden = !canShow;
      if (!canShow) {
        return;
      }
      if (btn) {
        btn.hidden = false;
        btn.disabled = false;
        var label = btn.querySelector('[data-pwa-install-label]');
        if (label) {
          label.textContent = isIos() ? 'How to' : 'Install';
        }
      }
      if (iosPanel) {
        iosPanel.hidden = true;
      }
    });
    syncBodyPadding();
  }

  function hideAllInstallRoots() {
    document.querySelectorAll('[data-pwa-install-root]').forEach(function (root) {
      root.hidden = true;
    });
    syncBodyPadding();
  }

  document.addEventListener('click', function (e) {
    var dismissBtn = e.target.closest('[data-pwa-install-dismiss]');
    if (dismissBtn) {
      setDismissed();
      hideAllInstallRoots();
      return;
    }
    var btn = e.target.closest('[data-pwa-install-btn]');
    if (!btn || btn.hidden || btn.disabled) {
      return;
    }
    var root = btn.closest('[data-pwa-install-root]');
    if (!root) {
      return;
    }
    if (isIos()) {
      var iosPanel = root.querySelector('[data-pwa-install-ios-help]');
      if (iosPanel) {
        iosPanel.hidden = !iosPanel.hidden;
        syncBodyPadding();
      }
      return;
    }
    if (!window.pwaInstall.canPrompt()) {
      return;
    }
    btn.disabled = true;
    var label = btn.querySelector('[data-pwa-install-label]');
    if (label) {
      label.textContent = '…';
    }
    window.pwaInstall.install().finally(function () {
      btn.disabled = false;
      refreshInstallRoots();
    });
  });

  document.addEventListener('click', function (e) {
    var dismiss = e.target.closest('[data-pwa-install-ios-dismiss]');
    if (!dismiss) {
      return;
    }
    var panel = dismiss.closest('[data-pwa-install-ios-help]');
    if (panel) {
      panel.hidden = true;
      syncBodyPadding();
    }
  });

  window.addEventListener('pwa-install-available', refreshInstallRoots);
  window.addEventListener('pwa-installed', hideAllInstallRoots);

  document.addEventListener('DOMContentLoaded', refreshInstallRoots);
})();
