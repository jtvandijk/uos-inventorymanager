document.addEventListener("DOMContentLoaded", function () {
    const nameField = document.getElementById("id_name");
    const codeField = document.getElementById("id_code");

    if (!nameField || !codeField) return;

    nameField.addEventListener("input", function () {
        if (codeField.value === "") {
            codeField.value = nameField.value.slice(0, 2).toUpperCase();
        }
    });
});
