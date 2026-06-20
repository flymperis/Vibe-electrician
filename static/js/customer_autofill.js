(function () {
    const select = document.getElementById("id_customer");
    if (!select) return;

    const fields = ["client_name", "client_vat", "client_phone", "client_email", "address"];

    function setField(name, value) {
        const el = document.getElementById("id_" + name);
        if (el) el.value = value || "";
    }

    async function fillFromCustomer(customerId) {
        if (!customerId) return;
        try {
            const response = await fetch("/pelates/" + customerId + "/json/");
            if (!response.ok) return;
            const data = await response.json();
            fields.forEach((name) => setField(name, data[name]));
        } catch (err) {
            /* ignore network errors */
        }
    }

    select.addEventListener("change", function () {
        fillFromCustomer(select.value);
    });
})();
