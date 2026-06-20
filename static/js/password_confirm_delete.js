(function () {
    const dialog = document.getElementById("password-delete-dialog");
    if (!dialog) {
        return;
    }

    const titleEl = document.getElementById("password-delete-title");
    const messageEl = document.getElementById("password-delete-message");
    const passwordInput = document.getElementById("password-delete-input");
    const errorEl = document.getElementById("password-delete-error");
    const confirmBtn = dialog.querySelector("[data-password-delete-confirm]");
    const cancelBtn = dialog.querySelector("[data-password-delete-cancel]");

    let activeForm = null;

    function clearError() {
        if (!errorEl) {
            return;
        }
        errorEl.hidden = true;
        errorEl.textContent = "";
    }

    function showError(message) {
        if (!errorEl) {
            return;
        }
        errorEl.textContent = message;
        errorEl.hidden = false;
    }

    function openDialog(form, title, message) {
        activeForm = form;
        titleEl.textContent = title || "Επιβεβαίωση διαγραφής";
        messageEl.textContent = message || "";
        passwordInput.value = "";
        clearError();
        dialog.showModal();
        passwordInput.focus();
    }

    function closeDialog() {
        activeForm = null;
        passwordInput.value = "";
        clearError();
        dialog.close();
    }

    document.addEventListener("click", function (event) {
        const trigger = event.target.closest("[data-password-delete-trigger]");
        if (!trigger) {
            return;
        }
        event.preventDefault();
        const form = trigger.closest("form");
        if (!form) {
            return;
        }
        openDialog(
            form,
            trigger.dataset.deleteTitle,
            trigger.dataset.deleteMessage
        );
    });

    cancelBtn.addEventListener("click", closeDialog);

    dialog.addEventListener("cancel", function (event) {
        event.preventDefault();
        closeDialog();
    });

    dialog.addEventListener("click", function (event) {
        if (event.target === dialog) {
            closeDialog();
        }
    });

    confirmBtn.addEventListener("click", function () {
        if (!activeForm) {
            return;
        }
        const password = passwordInput.value.trim();
        if (!password) {
            showError("Εισάγετε τον κωδικό σας.");
            passwordInput.focus();
            return;
        }
        const hidden = activeForm.querySelector('input[name="confirm_password"]');
        if (hidden) {
            hidden.value = password;
        }
        activeForm.submit();
    });

    passwordInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            confirmBtn.click();
        }
    });
})();
