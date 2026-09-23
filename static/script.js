const contractModal = document.getElementById("contractModal");
const dataForm = document.getElementById("dataForm");

if (dataForm) {
  dataForm.addEventListener("submit", function (event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    fetch(event.target.action, {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
      .then(({ ok, data }) => {
        const resultEl = document.getElementById("result");
        if (!ok) {
          resultEl.textContent = "Erro: " + data.error;
          return;
        }
        resultEl.textContent = "";
        contractModal.classList.remove("hidden");
      })
      .catch((error) => console.error("Erro:", error));
  });

  document
    .getElementById("viewContractBtn")
    .addEventListener("click", function () {
      window.open(dataForm.dataset.downloadUrl, "_blank");
    });

  document.getElementById("modalClose").addEventListener("click", function () {
    contractModal.classList.add("hidden");
  });

  contractModal.addEventListener("click", function (event) {
    if (event.target === contractModal) {
      contractModal.classList.add("hidden");
    }
  });
}

const loginForm = document.getElementById("LoginForm");

if (loginForm) {
  loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    fetch("/login", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
      .then(({ ok, data }) => {
        const resultEl = document.getElementById("loginResult");
        if (!ok) {
          resultEl.textContent = "Erro: " + data.error;
          return;
        }
        resultEl.textContent = "";
        window.location.href = data.redirect || "/dashboard";
      })
      .catch((error) => console.error("Erro:", error));
  });
}

const logoutLink = document.getElementById("logoutLink");

if (logoutLink) {
  logoutLink.addEventListener("click", function (event) {
    event.preventDefault();
    fetch("/logout", { method: "POST" }).then(() => {
      window.location.href = "/";
    });
  });
}
