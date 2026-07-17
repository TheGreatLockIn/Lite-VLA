(function () {
  "use strict";

  var toggle = document.querySelector(".concepts-sidebar-toggle");
  var sidebar = document.querySelector(".concepts-sidebar");
  var backdrop = document.querySelector(".concepts-backdrop");
  var localLinks = document.querySelectorAll(".concepts-nav-local a[href^='#']");

  function setSidebarOpen(open) {
    if (!sidebar) return;
    sidebar.classList.toggle("is-open", open);
    if (backdrop) backdrop.classList.toggle("is-visible", open);
    if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      setSidebarOpen(!sidebar.classList.contains("is-open"));
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", function () {
      setSidebarOpen(false);
    });
  }

  document.querySelectorAll(".concepts-nav-global a").forEach(function (link) {
    link.addEventListener("click", function () {
      if (window.matchMedia("(max-width: 959px)").matches) {
        setSidebarOpen(false);
      }
    });
  });

  if (localLinks.length === 0) return;

  var headings = [];
  localLinks.forEach(function (link) {
    var id = link.getAttribute("href").slice(1);
    var el = document.getElementById(id);
    if (el) headings.push({ id: id, el: el, link: link });
  });

  function setActive(id) {
    localLinks.forEach(function (link) {
      link.classList.toggle("is-active", link.getAttribute("href") === "#" + id);
    });
  }

  if ("IntersectionObserver" in window && headings.length) {
    var observer = new IntersectionObserver(
      function (entries) {
        var visible = entries
          .filter(function (e) {
            return e.isIntersecting;
          })
          .sort(function (a, b) {
            return a.boundingClientRect.top - b.boundingClientRect.top;
          });
        if (visible.length) {
          setActive(visible[0].target.id);
        }
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: 0 }
    );
    headings.forEach(function (h) {
      observer.observe(h.el);
    });
  }

  localLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      if (window.matchMedia("(max-width: 959px)").matches) {
        setSidebarOpen(false);
      }
    });
  });
})();
