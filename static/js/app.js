/* ==========================================================================
   Car Management — App shell scripts
   Theme toggle, sidebar, toasts, global HTMX feedback, count-up, dropzones.
   ========================================================================== */
(function () {
  "use strict";

  const STORAGE_THEME = "cm.theme";
  const STORAGE_SIDEBAR = "cm.sidebar";

  /* -----------------------------------------------------------------------
     THEME (dark / light)
     ----------------------------------------------------------------------- */
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    document.querySelectorAll(".cm-theme-icon-moon").forEach((el) => {
      el.style.display = theme === "dark" ? "inline-block" : "none";
    });
    document.querySelectorAll(".cm-theme-icon-sun").forEach((el) => {
      el.style.display = theme === "dark" ? "none" : "inline-block";
    });
  }

  function initTheme() {
    let theme = null;
    try {
      theme = localStorage.getItem(STORAGE_THEME);
    } catch (e) { /* private mode */ }
    if (!theme) {
      theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    applyTheme(theme);

    document.querySelectorAll(".cm-theme-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = document.documentElement.getAttribute("data-bs-theme") === "dark"
          ? "light"
          : "dark";
        applyTheme(next);
        try { localStorage.setItem(STORAGE_THEME, next); } catch (e) { /* noop */ }
      });
    });
  }

  /* -----------------------------------------------------------------------
     SIDEBAR (desktop collapse / mobile drawer)
     ----------------------------------------------------------------------- */
  const mqMobile = window.matchMedia("(max-width: 991.98px)");

  function isMobile() {
    return mqMobile.matches;
  }

  function setSidebarCollapsed(collapsed) {
    const shell = document.querySelector(".cm-shell");
    if (!shell) return;
    shell.classList.toggle("sidebar-collapsed", collapsed);
    try { localStorage.setItem(STORAGE_SIDEBAR, collapsed ? "1" : "0"); } catch (e) { /* noop */ }
  }

  function setSidebarOpen(open) {
    const shell = document.querySelector(".cm-shell");
    if (!shell) return;
    shell.classList.toggle("sidebar-open", open);
    document.body.style.overflow = open ? "hidden" : "";
  }

  function initSidebar() {
    let collapsed = false;
    try {
      collapsed = localStorage.getItem(STORAGE_SIDEBAR) === "1";
    } catch (e) { /* noop */ }
    if (!isMobile() && collapsed) {
      document.querySelector(".cm-shell")?.classList.add("sidebar-collapsed");
    }

    document.querySelectorAll("[data-sidebar-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (isMobile()) {
          const shell = document.querySelector(".cm-shell");
          setSidebarOpen(!(shell && shell.classList.contains("sidebar-open")));
        } else {
          const shell = document.querySelector(".cm-shell");
          setSidebarCollapsed(!(shell && shell.classList.contains("sidebar-collapsed")));
        }
      });
    });

    document.querySelectorAll("[data-sidebar-close]").forEach((el) => {
      el.addEventListener("click", () => setSidebarOpen(false));
    });

    mqMobile.addEventListener("change", () => {
      if (!mqMobile.matches) setSidebarOpen(false);
    });
  }

  /* -----------------------------------------------------------------------
     TOASTS
     ----------------------------------------------------------------------- */
  const TOAST_ICONS = {
    success: "bi-check-circle-fill",
    danger: "bi-x-octagon-fill",
    warning: "bi-exclamation-triangle-fill",
    info: "bi-info-circle-fill",
  };

  function showToast(message, kind, title) {
    const stack = document.querySelector(".cm-toast-stack");
    if (!stack) return;
    const icon = TOAST_ICONS[kind] || TOAST_ICONS.info;
    const toast = document.createElement("div");
    toast.className = "toast cm-toast toast-" + kind;
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.setAttribute("aria-atomic", "true");
    toast.innerHTML =
      '<div class="toast-body">' +
      '<i class="bi ' + icon + ' toast-icon"></i>' +
      '<div class="flex-grow-1"><div class="fw-semibold small">' +
      (title || "") +
      '</div><div>' + message + "</div></div>" +
      '<button type="button" class="btn-close ms-1" style="font-size:.7rem" aria-label="Fechar"></button>' +
      "</div>" +
      '<div class="toast-progress"></div>';
    stack.appendChild(toast);
    const close = () => {
      toast.classList.add("opacity-0");
      toast.style.transition = "opacity .3s";
      setTimeout(() => toast.remove(), 320);
    };
    toast.querySelector(".btn-close").addEventListener("click", close);
    setTimeout(close, 4800);
  }

  function initServerToasts() {
    document.querySelectorAll(".cm-toast-stack > .toast").forEach((toast) => {
      setTimeout(() => {
        toast.classList.add("opacity-0");
        toast.style.transition = "opacity .3s";
        setTimeout(() => toast.remove(), 320);
      }, 4800);
      toast.querySelector(".btn-close")?.addEventListener("click", () => toast.remove());
    });
  }

  /* -----------------------------------------------------------------------
     GLOBAL HTMX FEEDBACK
     ----------------------------------------------------------------------- */
  function setTriggerLoading(elt, loading) {
    if (!elt) return;
    const btn = elt.closest("button, a.btn, .cm-switch-item");
    if (btn) {
      btn.classList.toggle("cm-loading", loading);
    }
  }

  function initHtmxFeedback() {
    if (!window.htmx) return;

    document.body.addEventListener("htmx:beforeRequest", (e) => {
      setTriggerLoading(e.detail.elt, true);
      const target = e.detail.target;
      if (target && !target.classList.contains("cm-skeleton")) {
        target.classList.add("cm-skeleton");
      }
    });

    document.body.addEventListener("htmx:afterRequest", (e) => {
      setTriggerLoading(e.detail.elt, false);
      if (e.detail.target) {
        e.detail.target.classList.remove("cm-skeleton");
      }
    });

    document.body.addEventListener("htmx:responseError", (e) => {
      const status = e.detail.xhr?.status || 0;
      let msg = "Ocorreu um erro na requisição. Tente novamente.";
      if (status === 500) msg = "Erro interno do servidor. Tente novamente.";
      if (status === 403) msg = "Sessão expirada. Atualize a página.";
      showToast(msg, "danger", "Erro");
    });

    document.body.addEventListener("htmx:sendError", () => {
      showToast("Falha de conexão. Verifique sua internet.", "danger", "Erro");
    });
  }

  /* -----------------------------------------------------------------------
     FORM SUBMIT LOADING (prevent double submit)
     ----------------------------------------------------------------------- */
  function initFormLoading() {
    document.addEventListener("submit", (e) => {
      const form = e.target;
      if (!(form instanceof HTMLFormElement)) return;
      const btn = form.querySelector("button[type=submit]");
      if (!btn) return;
      btn.classList.add("cm-loading");
      btn.disabled = true;
      const original = btn.innerHTML;
      const spinner = '<span class="cm-spinner me-1"></span>';
      btn.setAttribute("data-cm-original", original);
      btn.insertAdjacentHTML("afterbegin", spinner);
    });
  }

  /* -----------------------------------------------------------------------
     KPI COUNT-UP
     ----------------------------------------------------------------------- */
  function formatNumber(value, decimals) {
    try {
      return value.toLocaleString("pt-BR", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
    } catch (e) {
      return value.toFixed(decimals);
    }
  }

  function initCountUp() {
    document.querySelectorAll("[data-countup]").forEach((el) => {
      const raw = el.getAttribute("data-countup") || "0";
      const target = parseFloat(raw.replace(/,/g, ".")) || 0;
      const decimals = parseInt(el.getAttribute("data-decimals") || "0", 10);
      const prefix = el.getAttribute("data-prefix") || "";
      const suffix = el.getAttribute("data-suffix") || "";
      const duration = parseInt(el.getAttribute("data-duration") || "700", 10);
      const start = performance.now();

      function frame(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const value = target * eased;
        el.textContent = prefix + formatNumber(value, decimals) + suffix;
        if (progress < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    });
  }

  /* -----------------------------------------------------------------------
     DROPZONES (drag & drop for file inputs)
     ----------------------------------------------------------------------- */
  function initDropzones() {
    document.querySelectorAll("[data-dropzone]").forEach((zone) => {
      const input = zone.querySelector("input[type=file]");
      if (!input) return;

      ["dragenter", "dragover"].forEach((ev) =>
        zone.addEventListener(ev, (e) => {
          e.preventDefault();
          zone.classList.add("dragover");
        })
      );
      ["dragleave", "drop"].forEach((ev) =>
        zone.addEventListener(ev, (e) => {
          e.preventDefault();
          zone.classList.remove("dragover");
        })
      );
      zone.addEventListener("drop", (e) => {
        const files = e.dataTransfer?.files;
        if (files && files.length) {
          input.files = files;
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
      zone.addEventListener("click", () => input.click());
    });
  }

  /* -----------------------------------------------------------------------
     BOOT
     ----------------------------------------------------------------------- */
  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initSidebar();
    initServerToasts();
    initHtmxFeedback();
    initFormLoading();
    initCountUp();
    initDropzones();
  });

  window.CarManagement = {
    showToast,
    applyTheme,
  };
})();
