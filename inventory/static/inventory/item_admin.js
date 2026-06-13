document.addEventListener("DOMContentLoaded", function () {

    const categoryField = document.querySelector("select[name='category']");
    const sizeField = document.querySelector("select[name='size']");

    if (!categoryField || !sizeField) return;

    categoryField.addEventListener("change", function () {
        const categoryId = categoryField.value;

        fetch(`/inventory/get-sizes/?category_id=${categoryId}`)
            .then(res => res.json())
            .then(data => {

                sizeField.innerHTML = "";

                const defaultOption = document.createElement("option");
                defaultOption.value = "";
                defaultOption.text = "---------";
                sizeField.appendChild(defaultOption);

                data.sizes.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s.value;
                    opt.text = s.label;
                    sizeField.appendChild(opt);
                });
            });
    });

});