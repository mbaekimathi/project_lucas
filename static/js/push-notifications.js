(function () {
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !window.Notification) {
    return;
  }

  var body = document.body;
  if (!body || body.getAttribute('data-push-enabled') !== 'true') {
    return;
  }

  function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    var rawData = window.atob(base64);
    var outputArray = new Uint8Array(rawData.length);
    for (var i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  function hideBanner() {
    var banner = document.getElementById('push-enable-banner');
    if (banner) {
      banner.classList.add('hidden');
    }
  }

  function showBanner() {
    var banner = document.getElementById('push-enable-banner');
    if (!banner || localStorage.getItem('push_prompt_dismissed') === '1') {
      return;
    }
    if (Notification.permission !== 'default') {
      return;
    }
    banner.classList.remove('hidden');
  }

  async function subscribeUser() {
    var keyResp = await fetch('/api/push/vapid-public-key', { credentials: 'same-origin' });
    var keyData = await keyResp.json();
    if (!keyData.configured || !keyData.publicKey || !keyData.pushEnabled) {
      return false;
    }

    var permission = Notification.permission;
    if (permission === 'default') {
      permission = await Notification.requestPermission();
    }
    if (permission !== 'granted') {
      return false;
    }

    var reg = await navigator.serviceWorker.ready;
    var sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(keyData.publicKey),
      });
    }

    var saveResp = await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
      body: JSON.stringify(sub.toJSON()),
    });
    var saveData = await saveResp.json();
    return !!(saveData && saveData.success);
  }

  window.portalEnablePushNotifications = async function () {
    try {
      var ok = await subscribeUser();
      hideBanner();
      if (ok) {
        localStorage.removeItem('push_prompt_dismissed');
      }
      return ok;
    } catch (err) {
      console.warn('portalEnablePushNotifications', err);
      return false;
    }
  };

  window.portalDismissPushPrompt = function () {
    localStorage.setItem('push_prompt_dismissed', '1');
    hideBanner();
  };

  window.addEventListener('load', function () {
    var enableBtn = document.getElementById('push-enable-btn');
    var dismissBtn = document.getElementById('push-dismiss-btn');
    if (enableBtn) {
      enableBtn.addEventListener('click', function () {
        window.portalEnablePushNotifications();
      });
    }
    if (dismissBtn) {
      dismissBtn.addEventListener('click', function () {
        window.portalDismissPushPrompt();
      });
    }

    if (Notification.permission === 'granted') {
      subscribeUser().catch(function () {});
      hideBanner();
    } else if (Notification.permission === 'default') {
      showBanner();
    }
  });
})();
