/* ==========================================================================
   ClientFlow — core front-end behaviors (no framework, vanilla JS)
   ========================================================================== */

(function () {
  "use strict";

  /* ---------------------------------------------------------- THEME TOGGLE */
  const root = document.documentElement;
  const THEME_KEY = "clientflow-theme";

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    document.querySelectorAll("[data-theme-icon]").forEach((el) => {
      el.className = theme === "light" ? "bi bi-moon-stars-fill" : "bi bi-sun-fill";
    });
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) ||
      (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    applyTheme(saved);
  }

  document.addEventListener("click", (e) => {
    const toggle = e.target.closest("[data-theme-toggle]");
    if (!toggle) return;
    const current = root.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  });

  initTheme();

  /* ---------------------------------------------------------- MOBILE NAV / SIDEBAR */
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-toggle-nav]");
    if (t) {
      document.querySelector(".mobile-menu")?.classList.toggle("show");
    }
    const s = e.target.closest("[data-toggle-sidebar]");
    if (s) {
      document.querySelector(".sidebar")?.classList.toggle("open");
    }
  });

  /* ---------------------------------------------------------- SCROLL REVEAL */
  const revealEls = document.querySelectorAll(".reveal");
  if (revealEls.length) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    revealEls.forEach((el) => io.observe(el));
  }

  /* ---------------------------------------------------------- STICKY NAVBAR SHADOW */
  const navbar = document.querySelector(".navbar-glass");
  if (navbar) {
    window.addEventListener("scroll", () => {
      navbar.style.boxShadow = window.scrollY > 8 ? "0 8px 30px rgba(0,0,0,.25)" : "none";
    });
  }

  /* ---------------------------------------------------------- FAQ ACCORDION */
  document.querySelectorAll(".acc-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const panel = btn.nextElementSibling;
      const isOpen = btn.classList.contains("open");
      document.querySelectorAll(".acc-btn.open").forEach((openBtn) => {
        if (openBtn !== btn) {
          openBtn.classList.remove("open");
          openBtn.nextElementSibling.style.maxHeight = null;
        }
      });
      btn.classList.toggle("open", !isOpen);
      panel.style.maxHeight = !isOpen ? panel.scrollHeight + "px" : null;
    });
  });

  /* ---------------------------------------------------------- TOASTS */
  function ensureToastStack() {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      document.body.appendChild(stack);
    }
    return stack;
  }

  const ICONS = {
    success: "bi-check-circle-fill",
    danger: "bi-x-circle-fill",
    warning: "bi-exclamation-triangle-fill",
    info: "bi-info-circle-fill",
  };

  window.showToast = function (message, category = "info") {
    const stack = ensureToastStack();
    const el = document.createElement("div");
    el.className = `toast-item glass ${category}`;
    el.innerHTML = `<i class="bi ${ICONS[category] || ICONS.info}"></i><div>${message}</div>`;
    stack.appendChild(el);
    setTimeout(() => {
      el.style.transition = "opacity .4s ease, transform .4s ease";
      el.style.opacity = "0";
      el.style.transform = "translateX(40px)";
      setTimeout(() => el.remove(), 400);
    }, 4500);
  };

  // Render server-side flash messages as toasts
  document.querySelectorAll("[data-flash]").forEach((el) => {
    window.showToast(el.dataset.flash, el.dataset.category || "info");
  });

  /* ---------------------------------------------------------- DROPZONE (file upload) */
  document.querySelectorAll("[data-dropzone]").forEach((zone) => {
    const inputId = zone.dataset.dropzone;
    const input = document.getElementById(inputId);
    const listEl = document.getElementById(inputId + "-list");
    if (!input) return;

    zone.addEventListener("click", () => input.click());
    ["dragenter", "dragover"].forEach((evt) =>
      zone.addEventListener(evt, (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((evt) =>
      zone.addEventListener(evt, (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
      })
    );
    zone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files.length) {
        input.files = dt.files;
        renderFileList();
      }
    });
    input.addEventListener("change", renderFileList);

    function renderFileList() {
      if (!listEl) return;
      listEl.innerHTML = "";
      Array.from(input.files).forEach((file) => {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.innerHTML = `<i class="bi bi-paperclip"></i> ${file.name}`;
        listEl.appendChild(chip);
      });
    }
  });

  /* ---------------------------------------------------------- NOTIFICATION POLLING */
  const notifBadge = document.querySelector("[data-notif-count]");
  if (notifBadge) {
    async function poll() {
      try {
        const res = await fetch("/api/notifications/unread-count");
        if (!res.ok) return;
        const data = await res.json();
        if (data.count > 0) {
          notifBadge.textContent = data.count > 9 ? "9+" : data.count;
          notifBadge.style.display = "flex";
        } else {
          notifBadge.style.display = "none";
        }
      } catch (err) { /* silent fail, non-critical */ }
    }
    poll();
    setInterval(poll, 30000);
  }

  /* ---------------------------------------------------------- PASSWORD VISIBILITY */
  document.querySelectorAll("[data-toggle-password]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.togglePassword);
      if (!input) return;
      input.type = input.type === "password" ? "text" : "password";
      btn.querySelector("i").className = input.type === "password" ? "bi bi-eye" : "bi bi-eye-slash";
    });
  });

  /* ---------------------------------------------------------- COUNT-UP STATS */
  const counters = document.querySelectorAll("[data-count-to]");
  if (counters.length) {
    const cio = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          const target = parseInt(el.dataset.countTo, 10);
          const duration = 1400;
          const start = performance.now();
          function tick(now) {
            const progress = Math.min((now - start) / duration, 1);
            el.textContent = Math.floor(progress * target).toLocaleString();
            if (progress < 1) requestAnimationFrame(tick);
            else el.textContent = target.toLocaleString();
          }
          requestAnimationFrame(tick);
          cio.unobserve(el);
        });
      },
      { threshold: 0.4 }
    );
    counters.forEach((c) => cio.observe(c));
  }

  /* ---------------------------------------------------------- PORTFOLIO DEMO TRIGGERS */
  document.querySelectorAll(".demo-trigger").forEach((btn) => {
    btn.addEventListener("click", () => {
      const url = btn.dataset.demoUrl;
      const credsBox = btn.nextElementSibling;
      if (credsBox && credsBox.classList.contains("demo-credentials")) {
        credsBox.style.display = "block";
      }
      if (url) {
        window.open(url, "_blank", "noopener");
      }
    });
  });

  /* ---------------------------------------------------------- AUTO-DISMISS ALERTS */
  document.querySelectorAll(".alert-dismiss").forEach((el) => {
    setTimeout(() => el.remove(), 6000);
  });
})();
