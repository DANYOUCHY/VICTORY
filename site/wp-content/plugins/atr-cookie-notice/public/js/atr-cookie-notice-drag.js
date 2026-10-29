/**
 * ATR Cookie Notice - Drag handle
 * Lets visitors move the banner out of the way (mouse, touch, keyboard arrows).
 * Moving the banner is not consent. The position is not stored.
 *
 * @package Atr_Cookie_Notice
 * @since 1.3.0
 */
(function () {
  'use strict';

  var KEY_STEP = 20;

  function init() {
    var banner = document.getElementById('scb-banner');
    var handle = banner ? banner.querySelector('.scb-drag-handle') : null;
    if (!handle) {
      return;
    }

    var dragging = false;
    var startX = 0;
    var startY = 0;
    var startLeft = 0;
    var startTop = 0;

    // Keep the banner fully inside the viewport
    function place(left, top) {
      var maxLeft = Math.max(0, window.innerWidth - banner.offsetWidth);
      var maxTop = Math.max(0, window.innerHeight - banner.offsetHeight);
      banner.style.left = Math.min(Math.max(0, left), maxLeft) + 'px';
      banner.style.top = Math.min(Math.max(0, top), maxTop) + 'px';
      banner.style.right = 'auto';
      banner.style.bottom = 'auto';
      banner.style.transform = 'none';
    }

    handle.addEventListener('pointerdown', function (e) {
      if (e.button !== 0) {
        return;
      }
      var rect = banner.getBoundingClientRect();
      startX = e.clientX;
      startY = e.clientY;
      startLeft = rect.left;
      startTop = rect.top;
      dragging = true;
      handle.setPointerCapture(e.pointerId);
      banner.classList.add('scb-dragging');
      e.preventDefault();
    });

    handle.addEventListener('pointermove', function (e) {
      if (dragging) {
        place(startLeft + e.clientX - startX, startTop + e.clientY - startY);
      }
    });

    function endDrag() {
      dragging = false;
      banner.classList.remove('scb-dragging');
    }
    handle.addEventListener('pointerup', endDrag);
    handle.addEventListener('pointercancel', endDrag);

    handle.addEventListener('keydown', function (e) {
      var moves = { ArrowLeft: [-KEY_STEP, 0], ArrowRight: [KEY_STEP, 0], ArrowUp: [0, -KEY_STEP], ArrowDown: [0, KEY_STEP] };
      var d = moves[e.key];
      if (!d) {
        return;
      }
      var rect = banner.getBoundingClientRect();
      place(rect.left + d[0], rect.top + d[1]);
      e.preventDefault();
    });

    // After a move, keep the banner on screen when the viewport changes (e.g. rotation)
    window.addEventListener('resize', function () {
      if (banner.style.left) {
        var rect = banner.getBoundingClientRect();
        place(rect.left, rect.top);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
