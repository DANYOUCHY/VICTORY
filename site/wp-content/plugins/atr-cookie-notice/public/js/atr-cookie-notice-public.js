/**
 * ATR Cookie Notice - Public JavaScript
 *
 * @package Atr_Cookie_Notice
 * @since 1.0.0
 */

/** @format */

// scb-script.js - Vanilla JS cookie consent
(function () {
  const settings = (typeof window.atrCookieNoticeSettings !== 'undefined') ? window.atrCookieNoticeSettings : {};
  const name = settings.cookieName || "atr_cookie_notice_consent";
  const decisionCookieName = settings.decisionCookieName || 'atr_cookie_notice_consent_given';
  const expiryDays = settings.expiryDays || 365;
  const isPrivacyPage = !!settings.isPrivacyPage;
  const enableDebug = !!settings.enableDebug;

  // If simple mode is selected, do nothing in this advanced script (defensive against caches)
  if (settings && settings.mode === 'simple') {
    if (enableDebug && window.console && console.log) {
      console.log('ATR Cookie Notice: Advanced script skipped due to simple mode.');
    }
    return;
  }

  // Prevent multiple initializations
  if (window.atrCookieNoticeInitialized) return;
  window.atrCookieNoticeInitialized = true;

  // Cookie helpers: unify set/clear with SameSite/Lax and Secure on HTTPS
  function setCookie(key, val, { maxAgeSeconds = null } = {}) {
    try {
      let cookie = String(key) + '=' + encodeURIComponent(String(val)) + '; path=/; SameSite=Lax';
      if (typeof maxAgeSeconds === 'number' && isFinite(maxAgeSeconds)) {
        const maxAge = Math.floor(maxAgeSeconds);
        const expires = new Date(Date.now() + maxAge * 1000).toUTCString();
        cookie += '; Max-Age=' + maxAge + '; Expires=' + expires;
      }
      if (window.location && window.location.protocol === 'https:') {
        cookie += '; Secure';
      }
      document.cookie = cookie;
    } catch (e) {
      // Silent error handling
    }
  }

  function deleteCookie(key) {
    try {
      let cookie = String(key) + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax';
      if (window.location && window.location.protocol === 'https:') {
        cookie += '; Secure';
      }
      document.cookie = cookie;
    } catch (e) {
      // Silent error handling
    }
  }

  function saveConsent(obj) {
    try {
      localStorage.setItem(name, JSON.stringify(obj));
    } catch (e) {
      // Storage unavailable; the cookie below still holds the decision
    }
    // Always write the cookie too: the server reads it to decide what to block
    setCookie(name, JSON.stringify(obj), { maxAgeSeconds: expiryDays * 24 * 60 * 60 });
  }

  // Stored consent older than the configured expiry is ignored (localStorage never expires on its own)
  function isExpired(parsed) {
    return typeof parsed.ts === 'number' && (Date.now() - parsed.ts) > expiryDays * 24 * 60 * 60 * 1000;
  }

  function getConsent() {
    try {
      const v = localStorage.getItem(name);
      if (v) {
        const parsed = JSON.parse(v);
        // Validate that consent has required fields
        if (parsed && typeof parsed === 'object' && parsed.essential === true) {
          if (!isExpired(parsed)) {
            return parsed;
          }
          localStorage.removeItem(name);
        }
      }
    } catch (e) {
      // Silent error handling
    }

    // fallback read cookie
    try {
      const match = document.cookie.match(
        new RegExp("(^| )" + name + "=([^;]+)")
      );
      if (match) {
        const parsed = JSON.parse(decodeURIComponent(match[2]));
        // Validate that consent has required fields
        if (parsed && typeof parsed === 'object' && parsed.essential === true && !isExpired(parsed)) {
          return parsed;
        }
      }
    } catch (e) {
      // Silent error handling
    }

    return null;
  }

  // Withdraw consent: forget the stored decision and reload so the banner asks again
  function clearConsent() {
    try {
      localStorage.removeItem(name);
    } catch (e) {
      // Silent error handling
    }
    deleteCookie(name);
    deleteCookie(decisionCookieName);
    location.reload();
  }

  function consentGivenFor(key) {
    const c = getConsent();
    return c && c[key] === true;
  }

  // Replace <script type="text/plain" data-consent="analytics" src="..."></script>
  function activateDataScripts(type) {
    const nodes = document.querySelectorAll(
      'script[type="text/plain"][data-consent="' + type + '"]'
    );
    nodes.forEach((n) => {
      const s = document.createElement("script");
      if (n.src) s.src = n.src;
      if (n.textContent) s.textContent = n.textContent;
      // copy attributes except type
      for (let i = 0; i < n.attributes.length; i++) {
        const a = n.attributes[i];
        if (a.name === "type" || a.name === "data-consent") continue;
        s.setAttribute(a.name, a.value);
      }
      n.parentNode.replaceChild(s, n);
    });
    
    // Remove blocking for this type
    removeTrackingBlocking(type);
    
    // Restore tracking functions when analytics or marketing consent is given
    if (type === 'analytics' || type === 'marketing') {
      restoreTrackingFunctions();
    }
    
    // Special handling for GTM - restore any blocked GTM scripts
    if (type === 'analytics') {
      restoreGTMScripts();
    }
  }
  
  // Restore GTM scripts that were blocked
  function restoreGTMScripts() {
    // Find all GTM scripts that were blocked
    const blockedGTMScripts = document.querySelectorAll('script[src*="googletagmanager"], script[src*="gtm.js"]');
    blockedGTMScripts.forEach(script => {
      if (script.src && script.src.includes('data:text/javascript')) {
        const originalSrc = script.getAttribute('data-original-src');
        if (originalSrc) {
          script.src = originalSrc;
          
          // Trigger GTM initialization if it's the main GTM script
          if (originalSrc.includes('gtm.js')) {
            setTimeout(() => {
            }, 100);
          }
        }
      }
    });
  }
  
  // Remove tracking script blocking after consent
  function removeTrackingBlocking(type) {
    
    if (type === 'analytics') {
      // Remove all blocking for analytics
      
      // Reset override flags to allow re-blocking if needed
      if (window._scbCreateElementOverridden) {
        window._scbCreateElementOverridden = false;
      }
      if (window._scbCreateElementNSOverridden) {
        window._scbCreateElementNSOverridden = false;
      }
      if (window._scbImgBlockingOverridden) {
        window._scbImgBlockingOverridden = false;
      }
      if (window._scbXHROverridden) {
        window._scbXHROverridden = false;
      }
      if (window._scbFetchOverridden) {
        window._scbFetchOverridden = false;
      }
      
      // Restore original DOM methods for analytics
      if (window._scbOriginalCreateElement) {
        document.createElement = window._scbOriginalCreateElement;
      }
      
      // Restore original tracking functions
      if (window.gtag && window.gtag._scbBlocked) {
        if (window.gtag._original) {
          window.gtag = window.gtag._original;
        } else {
          delete window.gtag;
        }
      }
      
      if (window.ga && window.ga._scbBlocked) {
        if (window.ga._original) {
          window.ga = window.ga._original;
        } else {
          delete window.ga;
        }
      }
      
      if (window.dataLayer && window.dataLayer.push && window.dataLayer.push._scbBlocked) {
        if (window.dataLayer._originalPush) {
          window.dataLayer.push = window.dataLayer._originalPush;
        }
      }
      
      // Special handling for GTM
      const gtmScripts = document.querySelectorAll('script[src*="googletagmanager"], script[src*="gtm.js"]');
      gtmScripts.forEach(script => {
        if (script.src && script.src.includes('data:text/javascript')) {
          // Restore original GTM script
          const originalSrc = script.getAttribute('data-original-src') || script.src.replace('data:text/javascript,', '');
          if (originalSrc && !originalSrc.includes('data:text/javascript')) {
            script.src = originalSrc;
          }
        }
      });
      
    }
    
    if (type === 'marketing') {
      // Remove marketing blocking
      
      if (window.fbq && window.fbq._scbBlocked) {
        if (window.fbq._original) {
          window.fbq = window.fbq._original;
        } else {
          delete window.fbq;
        }
      }
      
      if (window._gaq && window._gaq.push && window._gaq.push._scbBlocked) {
        if (window._gaq._originalPush) {
          window._gaq.push = window._gaq._originalPush;
        }
      }
      
    }
    
    // Force remove all blocking completely
    
    // Remove all override flags
    delete window._scbCreateElementOverridden;
    delete window._scbCreateElementNSOverridden;
    delete window._scbImgBlockingOverridden;
    delete window._scbXHROverridden;
    delete window._scbFetchOverridden;
    
    // Restore all blocked functions to their originals
    if (window.gtag && window.gtag._scbBlocked) {
      if (window.gtag._original) {
        window.gtag = window.gtag._original;
      } else {
        delete window.gtag;
      }
    }
    if (window.ga && window.ga._scbBlocked) {
      if (window.ga._original) {
        window.ga = window.ga._original;
      } else {
        delete window.ga;
      }
    }
    if (window.fbq && window.fbq._scbBlocked) {
      if (window.fbq._original) {
        window.fbq = window.fbq._original;
      } else {
        delete window.fbq;
      }
    }
    
  }

  function showBanner() {
    const banner = document.getElementById("scb-banner");
    const overlay = document.getElementById("scb-overlay");
    const autoHideDelay = (settings && typeof settings.autoHideDelay !== 'undefined') ? parseInt(settings.autoHideDelay, 10) || 0 : 0;
    
    if (banner && overlay) {
      // Check if consent is already given - don't show banner if it is
      const currentConsent = getConsent();
      if (currentConsent) {
        return;
      }
      
      // On privacy policy page, don't block content completely
      if (isPrivacyPage) {
        overlay.classList.add('visible', 'privacy-page');
        banner.classList.add('visible');
      } else {
        // Add body class to prevent scroll on other pages
        document.body.classList.add('scb-open');
        overlay.classList.add('visible');
        banner.classList.add('visible');
      }

      // Auto-hide if configured and only when no consent yet
      if (!getConsent() && autoHideDelay > 0) {
        setTimeout(function() {
          hideBanner();
        }, autoHideDelay * 1000);
      }
      
    }
  }

  function hideBanner() {
    const banner = document.getElementById("scb-banner");
    const overlay = document.getElementById("scb-overlay");
    const settings = document.getElementById("scb-settings");
    
    if (banner && overlay) {
      // Remove body class to restore scroll
      document.body.classList.remove('scb-open');
      
      // Hide overlay and banner with smooth transitions
      overlay.classList.remove('visible', 'privacy-page');
      banner.classList.remove('visible');
      
      // Hide settings form
      if (settings) settings.classList.remove('visible');
    }
  }

  function setLoadingState(loading) {
    const banner = document.getElementById("scb-banner");
    if (banner) {
      if (loading) {
        banner.classList.add('loading');
      } else {
        banner.classList.remove('loading');
      }
    }
  }

  // Initialize the banner
  function initBanner() {
    
    const banner = document.getElementById("scb-banner");
    const overlay = document.getElementById("scb-overlay");
    const settings = document.getElementById("scb-settings");
    const form = document.getElementById("scb-form");

    // Check if banner elements exist
    if (!banner || !overlay) {
      return;
    }
    
    // Check consent immediately and return if already given
    const stored = getConsent();
    
    if (stored) {
      // User has already given consent - activate scripts and don't show banner

      // Consent saved by 1.2.0 lives only in localStorage; copy it to the cookie the server reads
      if (!document.cookie.match(new RegExp("(^| )" + name + "="))) {
        const ageSeconds = typeof stored.ts === 'number' ? Math.max(0, (Date.now() - stored.ts) / 1000) : 0;
        setCookie(name, JSON.stringify(stored), { maxAgeSeconds: expiryDays * 24 * 60 * 60 - ageSeconds });
      }

      // Ensure banner is hidden
      banner.classList.remove('visible');
      overlay.classList.remove('visible', 'privacy-page');
      document.body.classList.remove('scb-open');
      
      if (stored.analytics) activateDataScripts("analytics");
      if (stored.marketing) activateDataScripts("marketing");
      
      // Restore tracking functions if consent was already given
      if (stored.analytics || stored.marketing) {
        restoreTrackingFunctions();
      }
      return;
    }

    // On privacy policy page, show banner but don't block content
    if (isPrivacyPage) {
      // Add a note about temporary access
      const privacyNote = document.createElement('div');
      privacyNote.className = 'scb-privacy-note';
      const privacyNoteText = settings.privacyNoteText || '💡 You can read this page while deciding about cookies';
      const small = document.createElement('small');
      small.textContent = privacyNoteText;
      privacyNote.appendChild(small);
      
      const content = banner.querySelector('.scb-content');
      const text = banner.querySelector('.scb-text');
      if (content && text) {
        content.insertBefore(privacyNote, text);
      }
    }

    // No consent yet - show banner immediately to prevent flash
    showBanner();

    // controls
    const btnAcceptAll = document.getElementById("scb-btn-accept-all");
    const btnReject = document.getElementById("scb-btn-reject");
    const btnCustom = document.getElementById("scb-btn-custom");
    const btnCancel = document.getElementById("scb-btn-cancel");
    const btnClose = banner.querySelector(".scb-close");

    btnClose &&
      btnClose.addEventListener("click", function () {
        hideBanner();
      });

    btnAcceptAll &&
      btnAcceptAll.addEventListener("click", function () {
        setLoadingState(true);
        
        const c = {
          essential: true,
          analytics: true,
          marketing: true,
          ts: Date.now(),
        };
        
                 saveConsent(c);
         
        // Set persistent flag indicating a decision has been made
        setCookie(decisionCookieName, '1', { maxAgeSeconds: expiryDays * 24 * 60 * 60 });
         
         // Activate scripts first
         activateDataScripts("analytics");
         activateDataScripts("marketing");
         
         // Restore tracking functions
         restoreTrackingFunctions();
         
         setTimeout(() => {
           hideBanner();
           setLoadingState(false);
           
           // Reload page after a short delay to ensure blocking is completely removed
           setTimeout(() => {
             window.location.reload();
           }, 1000);
         }, 300);
      });

    btnReject &&
      btnReject.addEventListener("click", function () {
        setLoadingState(true);
        
        const c = {
          essential: true,
          analytics: false,
          marketing: false,
          ts: Date.now(),
        };
        
        saveConsent(c);
        
        // Decision made (reject): set persistent flag
        setCookie(decisionCookieName, '1', { maxAgeSeconds: expiryDays * 24 * 60 * 60 });
        
        setTimeout(() => {
          hideBanner();
          setLoadingState(false);
        }, 300);
      });

    btnCustom &&
      btnCustom.addEventListener("click", function () {
        if (settings) {
          settings.classList.toggle('visible');
        }
      });

    btnCancel &&
      btnCancel.addEventListener("click", function () {
        if (settings) settings.classList.remove('visible');
      });

    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        setLoadingState(true);
        
        const formd = new FormData(form);
        const c = {
          essential: true,
          analytics: formd.has("analytics"),
          marketing: formd.has("marketing"),
          ts: Date.now(),
        };
        
        saveConsent(c);
        
        // Decision made (custom): set persistent flag
        setCookie(decisionCookieName, '1', { maxAgeSeconds: expiryDays * 24 * 60 * 60 });
        if (c.analytics) activateDataScripts("analytics");
        if (c.marketing) activateDataScripts("marketing");
        
        // Restore tracking functions if analytics or marketing consent given
        if (c.analytics || c.marketing) {
          restoreTrackingFunctions();
        }

        setTimeout(() => {
          hideBanner();
          setLoadingState(false);
          // Reload so the server stops printing the blockers for the allowed categories
          if (c.analytics || c.marketing) {
            setTimeout(() => {
              window.location.reload();
            }, 1000);
          }
        }, 300);
      });
    }

    // Close banner when clicking outside (mobile-friendly)
    overlay.addEventListener("click", function(e) {
      if (e.target === overlay) {
        hideBanner();
      }
    });

    // Close banner with Escape key
    document.addEventListener("keydown", function(e) {
      if (e.key === "Escape") {
        hideBanner();
      }
    });
  }

  // Wait for DOM to be ready, but also check if elements are already there
  function ready() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initBanner);
    } else {
      // DOM is already ready
      initBanner();
    }
  }

  // Start initialization with a small delay to ensure everything is loaded
  setTimeout(ready, 50);
  
  // Check if consent is already given before setting up blocking
  const initialConsent = getConsent();
  const shouldBlock = !initialConsent || !initialConsent.analytics || !initialConsent.marketing;

  // Simple and effective tracking function blocking - wait for scripts to load first
  // Each category is blocked only while the visitor has not consented to it
  function setupTrackingBlocking() {
    const currentConsent = getConsent();
    const blockAnalytics = !(currentConsent && currentConsent.analytics);
    const blockMarketing = !(currentConsent && currentConsent.marketing);

    if (blockAnalytics) {
    // Block gtag
    if (window.gtag) {
      if (window.gtag && !window.gtag._scbBlocked) {
        window.gtag._original = window.gtag;
        window.gtag._scbBlocked = true;
        window.gtag = function() {
          return false;
        };

      }
    } else {
      window.gtag = function() {
        return false;
      };
      window.gtag._scbBlocked = true;
    }
    
    // Block ga
    if (window.ga) {
      if (window.ga && !window.ga._scbBlocked) {
        window.ga._original = window.ga;
        window.ga._scbBlocked = true;
        window.ga = function() {
          return false;
        };

      }
    } else {
      window.ga = function() {
        return false;
      };
      window.ga._scbBlocked = true;
    }

    // Block dataLayer.push
    if (window.dataLayer) {
      if (window.dataLayer && window.dataLayer.push && !window.dataLayer.push._scbBlocked) {
        window.dataLayer._originalPush = window.dataLayer.push;
        window.dataLayer.push._scbBlocked = true;
        window.dataLayer.push = function() {
          return false;
        };

      }
    }
    }

    if (blockMarketing) {
    // Block fbq
    if (window.fbq) {
      if (window.fbq && !window.fbq._scbBlocked) {
        window.fbq._original = window.fbq;
        window.fbq._scbBlocked = true;
        window.fbq = function() {
          return false;
        };

      }
    } else {
      window.fbq = function() {
        return false;
      };
      window.fbq._scbBlocked = true;
    }
    }

  }

  // Restore original tracking functions when consent is given
  function restoreTrackingFunctions() {
    
    // Restore gtag
    if (window.gtag && window.gtag._original) {
      window.gtag = window.gtag._original;
    }
    
    // Restore ga
    if (window.ga && window.ga._original) {
      window.ga = window.ga._original;
    }
    
    // Restore fbq
    if (window.fbq && window.fbq._original) {
      window.fbq = window.fbq._original;
    }
    
    // Restore dataLayer.push
    if (window.dataLayer && window.dataLayer._originalPush) {
      window.dataLayer.push = window.dataLayer._originalPush;
    }
    
  }
  
  // Block tracking functions immediately to prevent network requests
  // Then re-block after scripts load to ensure complete coverage
  if (shouldBlock) {
    setupTrackingBlocking();
    
    // Also block after a delay to catch any late-loading scripts
    setTimeout(() => {
      // Re-check per category (setupTrackingBlocking skips consented categories)
      setupTrackingBlocking();
    }, 2000); // Wait 2 seconds for any late scripts

    // When debug is enabled, trigger a non-invasive test after setup
    if (enableDebug) {
      setTimeout(() => {
        if (window.atrCookieNotice && window.atrCookieNotice.testTracking) {
          window.atrCookieNotice.testTracking();
        }
      }, 500);
    }
  }

  // "Cookie settings" links (shortcode [atr_cookie_notice_settings]): withdraw/change consent
  document.addEventListener("click", function (e) {
    const link = e.target && e.target.closest ? e.target.closest(".atr-cookie-notice-settings-link") : null;
    if (link) {
      e.preventDefault();
      clearConsent();
    }
  });

  // expose API (includes testing helper only when debug is enabled)
  window.atrCookieNotice = {
    getConsent,
    saveConsent,
    consentGivenFor,
    activateDataScripts,
    showBanner,
    hideBanner,
    restoreTrackingFunctions,
    clearConsent,
    forceShow: function() {
      showBanner();
    },
    testTracking: function() {
      if (!enableDebug) return;
      try {
        if (typeof window.gtag === 'function') {
          window.gtag('event', 'test', { event_category: 'debug', event_label: 'consent_test' });
        }
        if (typeof window.ga === 'function') {
          window.ga('send', 'event', 'test', 'consent_test');
        }
        if (typeof window.fbq === 'function') {
          window.fbq('track', 'test', { event_category: 'debug', event_label: 'consent_test' });
        }
      } catch (e) {}
    },
  };
  
  // Deprecated alias kept for sites that call window.scb (documented in 1.2.0); never overwrites another script's scb
  if (typeof window.scb === 'undefined') {
    window.scb = window.atrCookieNotice;
  }

  // Debug: Log that the API object was created
  if (enableDebug) {
    console.log('ATR Cookie Notice: Script loading...');
    console.log('ATR Cookie Notice: atrCookieNotice object created', window.atrCookieNotice);
    console.log('ATR Cookie Notice: Debug mode enabled');
  }
})();

// Fallback: Ensure window.atrCookieNotice is always available (run after IIFE)
setTimeout(function() {
  if (typeof window.atrCookieNotice === 'undefined') {
    var debug = !!(window.atrCookieNoticeSettings && window.atrCookieNoticeSettings.enableDebug);
    if (debug && window.console && console.warn) {
      console.warn('ATR Cookie Notice: atrCookieNotice object not created, providing fallback');
    }
    var cn = (window.atrCookieNoticeSettings && window.atrCookieNoticeSettings.cookieName) ? window.atrCookieNoticeSettings.cookieName : 'atr_cookie_notice_consent';
    var decisionCn = (window.atrCookieNoticeSettings && window.atrCookieNoticeSettings.decisionCookieName) ? window.atrCookieNoticeSettings.decisionCookieName : 'atr_cookie_notice_consent_given';
    window.atrCookieNotice = {
      getConsent: function() {
        try {
          var v = localStorage.getItem(cn);
          if (v) {
            var parsed = JSON.parse(v);
            if (parsed && typeof parsed === 'object' && parsed.essential === true) {
              return parsed;
            }
          }
        } catch (e) {}
        try {
          var match = document.cookie.match(new RegExp('(^| )' + cn + '=([^;]+)'));
          if (match) {
            var parsed2 = JSON.parse(decodeURIComponent(match[2]));
            if (parsed2 && typeof parsed2 === 'object' && parsed2.essential === true) {
              return parsed2;
            }
          }
        } catch (e2) {}
        return null;
      },
      saveConsent: function(obj) {
        try { localStorage.setItem(cn, JSON.stringify(obj)); return true; } catch (e) { return false; }
      },
      consentGivenFor: function(key) {
        var c = this.getConsent();
        return !!(c && c[key] === true);
      },
      activateDataScripts: function() { return false; },
      showBanner: function() { return false; },
      hideBanner: function() { return false; },
      restoreTrackingFunctions: function() { return false; },
      clearConsent: function() {
        try {
          localStorage.removeItem(cn);
          document.cookie = cn + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
          document.cookie = decisionCn + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
          location.reload();
        } catch (e) {}
      },
      forceShow: function() { return false; },
      testTracking: function() { return false; }
    };
    if (typeof window.scb === 'undefined') {
      window.scb = window.atrCookieNotice;
    }
  }
}, 100);

