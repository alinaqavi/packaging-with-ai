// static/js/screenshot_block.js
(function () {
  async function overwriteClipboard(text) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      }
    } catch (_) {}
  }

  function hardenElement(el) {
    if (!el) return;
    el.style.userSelect = 'none';
    el.style.webkitUserSelect = 'none';
    el.style.msUserSelect = 'none';
    el.setAttribute('unselectable', 'on');
    el.addEventListener('contextmenu', (e) => e.preventDefault(), { passive: false });
    el.addEventListener('dragstart', (e) => e.preventDefault());
  }

  function protectPreviewImages(selector = '.message-image') {
    const applyProtection = (img) => {
      if (!img) return;
      img.style.pointerEvents = 'none';
      hardenElement(img);
      const parent = img.parentElement;
      if (parent && !parent.querySelector('.__overlay')) {
        const overlay = document.createElement('div');
        overlay.className = '__overlay';
        overlay.style.position = 'absolute';
        overlay.style.left = '0';
        overlay.style.top = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.background = 'transparent';
        overlay.style.pointerEvents = 'auto';
        overlay.style.zIndex = '10';
        overlay.addEventListener('contextmenu', e => e.preventDefault());
        overlay.addEventListener('mousedown', e => e.preventDefault());
        parent.style.position = parent.style.position || 'relative';
        parent.appendChild(overlay);
      }
    };

    document.querySelectorAll(selector).forEach(applyProtection);

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((m) => {
        m.addedNodes.forEach((node) => {
          if (node.nodeType === 1) {
            if (node.matches(selector)) applyProtection(node);
            node.querySelectorAll?.(selector).forEach(applyProtection);
          }
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function interceptScreenshotKeys() {
    window.addEventListener('keydown', async (e) => {
      if (e.key === 'PrintScreen' || e.key === 'Print') {
        await overwriteClipboard('Screenshot blocked.');
        alert('Screenshots are disabled for protected mockups.');
        e.preventDefault();
      }
      if ((e.ctrlKey || e.metaKey) && ['s', 'S', 'p', 'P'].includes(e.key)) e.preventDefault();
    });
  }

  function concealOnHidden() {
    document.addEventListener('visibilitychange', () => {
      const imgs = document.querySelectorAll('.message-image');
      imgs.forEach((img) => {
        img.style.filter = document.hidden ? 'blur(5px)' : '';
      });
    });
  }

  function interceptCopyEvent() {
    document.addEventListener('copy', async (e) => {
      if (e.target && e.target.closest('.message-image')) {
        e.preventDefault();
        await overwriteClipboard('Copy blocked: protected mockup.');
      }
    });
  }

  function initScreenshotBlock(opts = {}) {
    const selector = opts.selector || '.message-image';
    protectPreviewImages(selector);
    interceptScreenshotKeys();
    concealOnHidden();
    interceptCopyEvent();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => initScreenshotBlock());
  } else {
    initScreenshotBlock();
  }
})();
