document.addEventListener("DOMContentLoaded", function () {
    const fundSelect = document.getElementById("id_fund");
    const residenceSelect = document.getElementById("id_residence");

    if (!fundSelect || !residenceSelect) return;

    
    const currentResidenceId = residenceSelect.value;

    function loadResidences(fundId, preselectId) {
        if (!fundId) {
            residenceSelect.innerHTML = '<option value="">---------</option>';
            return;
        }

        fetch(`/get-residences/?fund_id=${fundId}`)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                residenceSelect.innerHTML = '<option value="">---------</option>';

                data.forEach(function (res) {
                    const option = document.createElement("option");
                    option.value = res.id;
                    option.textContent = res.name;

                    
                    if (preselectId && String(res.id) === String(preselectId)) {
                        option.selected = true;
                    }

                    residenceSelect.appendChild(option);
                });
            })
            .catch(function () {
                residenceSelect.innerHTML = '<option value="">Error al cargar residencias</option>';
            });
    }

    
    fundSelect.addEventListener("change", function () {
        loadResidences(this.value, null);
    });

   
    const initialFundId = fundSelect.value;
    if (initialFundId) {
        loadResidences(initialFundId, currentResidenceId);
    }
});