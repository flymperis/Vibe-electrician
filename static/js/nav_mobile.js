(function () {
    const nav = document.getElementById("site-nav");
    const toggle = nav && nav.querySelector(".nav-toggle");
    const menu = document.getElementById("nav-menu");
    if (!nav || !toggle || !menu) {
        return;
    }

    const mobileQuery = window.matchMedia("(max-width: 768px)");

    function closeMenu() {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
    }

    function openMenu() {
        nav.classList.add("is-open");
        toggle.setAttribute("aria-expanded", "true");
    }

    toggle.addEventListener("click", function () {
        if (nav.classList.contains("is-open")) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    menu.querySelectorAll("a, button").forEach(function (element) {
        element.addEventListener("click", function () {
            if (mobileQuery.matches) {
                closeMenu();
            }
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMenu();
        }
    });

    mobileQuery.addEventListener("change", function (event) {
        if (!event.matches) {
            closeMenu();
        }
    });
})();
