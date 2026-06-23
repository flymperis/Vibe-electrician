(function () {
    var mobileQuery = window.matchMedia("(max-width: 768px)");
    if (!mobileQuery.matches) {
        return;
    }

    var savedScrollY = 0;
    var fieldSelector = "input, select, textarea";

    function restoreScroll() {
        window.scrollTo(0, savedScrollY);
    }

    document.addEventListener(
        "focusin",
        function (event) {
            if (!event.target.matches(fieldSelector)) {
                return;
            }
            savedScrollY = window.scrollY;
        },
        true
    );

    document.addEventListener(
        "focusout",
        function (event) {
            if (!event.target.matches(fieldSelector)) {
                return;
            }

            var scrollY = savedScrollY;

            function maybeRestore() {
                if (Math.abs(window.scrollY - scrollY) > 40) {
                    window.scrollTo(0, scrollY);
                }
            }

            window.setTimeout(maybeRestore, 50);
            window.setTimeout(maybeRestore, 150);
            window.setTimeout(maybeRestore, 300);

            if (window.visualViewport) {
                var onResize = function () {
                    maybeRestore();
                    window.visualViewport.removeEventListener("resize", onResize);
                };
                window.visualViewport.addEventListener("resize", onResize);
            }
        },
        true
    );
})();
