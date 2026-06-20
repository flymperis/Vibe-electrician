(function () {
    function scrollToPaginatedSection() {
        var hash = window.location.hash;
        if (hash) {
            var hashTarget = document.querySelector(hash);
            if (hashTarget) {
                hashTarget.scrollIntoView({ block: "start" });
                return;
            }
        }

        var params = new URLSearchParams(window.location.search);
        var sections = document.querySelectorAll("[data-pagination-section]");
        var index;
        for (index = 0; index < sections.length; index += 1) {
            var section = sections[index];
            var pageParam = section.getAttribute("data-page-param");
            if (!pageParam) {
                continue;
            }
            var page = parseInt(params.get(pageParam) || "1", 10);
            if (page > 1) {
                section.scrollIntoView({ block: "start" });
                return;
            }
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", scrollToPaginatedSection);
    } else {
        scrollToPaginatedSection();
    }
})();
