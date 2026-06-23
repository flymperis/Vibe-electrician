(function () {
    const picker = document.getElementById("customer-picker");
    if (!picker) return;

    const searchUrl = picker.dataset.searchUrl;
    const hiddenInput = document.getElementById("id_customer");
    const searchArea = document.getElementById("customer-search-area");
    const searchInput = document.getElementById("customer-search-input");
    const resultsList = document.getElementById("customer-search-results");
    const selectedBox = document.getElementById("customer-selected");
    const selectedLabel = document.getElementById("customer-selected-label");
    const clearBtn = document.getElementById("customer-clear-btn");
    const manualHint = document.getElementById("customer-manual-hint");
    const selectedHint = document.getElementById("customer-selected-hint");

    const fields = ["client_name", "client_vat", "client_phone", "client_email", "address"];

    if (!hiddenInput || !searchInput || !resultsList) return;

    let debounceTimer = null;
    let activeIndex = -1;

    function setField(name, value) {
        const el = document.getElementById("id_" + name);
        if (el) el.value = value || "";
    }

    function setFieldsReadonly(readonly) {
        fields.forEach((name) => {
            const el = document.getElementById("id_" + name);
            if (!el) return;
            if (readonly) {
                el.setAttribute("readonly", "readonly");
                el.classList.add("is-readonly");
            } else {
                el.removeAttribute("readonly");
                el.classList.remove("is-readonly");
            }
        });
    }

    function setHintMode(selected) {
        if (manualHint) manualHint.hidden = selected;
        if (selectedHint) selectedHint.hidden = !selected;
    }

    function fillSnapshot(data) {
        fields.forEach((name) => setField(name, data[name]));
    }

    function clearSnapshot() {
        fields.forEach((name) => setField(name, ""));
    }

    function showSearch() {
        searchArea.hidden = false;
        selectedBox.hidden = true;
        searchInput.value = "";
        hiddenInput.value = "";
        clearSnapshot();
        setFieldsReadonly(false);
        setHintMode(false);
        hideResults();
        searchInput.focus();
    }

    function showSelected(label) {
        selectedLabel.textContent = label;
        selectedBox.hidden = false;
        searchArea.hidden = true;
        hideResults();
    }

    function hideResults() {
        resultsList.hidden = true;
        resultsList.innerHTML = "";
        activeIndex = -1;
    }

    function renderResults(results) {
        resultsList.innerHTML = "";
        if (!results.length) {
            const empty = document.createElement("li");
            empty.className = "customer-picker__results-empty";
            empty.textContent = "Δεν βρέθηκαν πελάτες.";
            resultsList.appendChild(empty);
            resultsList.hidden = false;
            return;
        }
        results.forEach((item, index) => {
            const li = document.createElement("li");
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "customer-picker__result";
            btn.textContent = item.label;
            btn.dataset.index = String(index);
            btn.addEventListener("click", () => selectCustomer(item));
            li.appendChild(btn);
            resultsList.appendChild(li);
        });
        resultsList.hidden = false;
    }

    function selectCustomer(item) {
        hiddenInput.value = String(item.id);
        fillSnapshot(item);
        setFieldsReadonly(true);
        setHintMode(true);
        showSelected(item.label);
    }

    async function runSearch(query) {
        try {
            const url = searchUrl + "?q=" + encodeURIComponent(query);
            const response = await fetch(url);
            if (!response.ok) {
                hideResults();
                return;
            }
            const data = await response.json();
            renderResults(data.results || []);
        } catch (err) {
            hideResults();
        }
    }

    searchInput.addEventListener("input", function () {
        const query = searchInput.value.trim();
        window.clearTimeout(debounceTimer);
        if (query.length < 2) {
            hideResults();
            return;
        }
        debounceTimer = window.setTimeout(() => runSearch(query), 250);
    });

    searchInput.addEventListener("keydown", function (event) {
        const items = resultsList.querySelectorAll(".customer-picker__result");
        if (!items.length || resultsList.hidden) return;

        if (event.key === "ArrowDown") {
            event.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
            items.forEach((el, i) => el.classList.toggle("is-active", i === activeIndex));
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            items.forEach((el, i) => el.classList.toggle("is-active", i === activeIndex));
        } else if (event.key === "Enter" && activeIndex >= 0) {
            event.preventDefault();
            items[activeIndex].click();
        } else if (event.key === "Escape") {
            hideResults();
        }
    });

    document.addEventListener("click", function (event) {
        if (!picker.contains(event.target)) {
            hideResults();
        }
    });

    if (clearBtn) {
        clearBtn.addEventListener("click", showSearch);
    }

    if (hiddenInput.value) {
        setFieldsReadonly(true);
        setHintMode(true);
    } else {
        setFieldsReadonly(false);
        setHintMode(false);
    }
})();
