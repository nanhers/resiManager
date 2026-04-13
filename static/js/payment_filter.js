document.addEventListener("DOMContentLoaded", function () {
    const fundSelect = document.getElementById("id_fund");
    const residenceSelect = document.getElementById("id_residence");

    if (!fundSelect || !residenceSelect) return;

    fundSelect.addEventListener("change", function () {
        const fundId = this.value;

        fetch(`/get-residences/?fund_id=${fundId}`)
            .then(response => response.json())
            .then(data => {
                residenceSelect.innerHTML = "";

                data.forEach(res => {
                    const option = document.createElement("option");
                    option.value = res.id;
                    option.textContent = res.name;
                    residenceSelect.appendChild(option);
                });
            });
    });
});