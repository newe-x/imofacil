function maskPhone(value) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length === 0) return "";
  if (digits.length <= 2) return "(" + digits;
  if (digits.length <= 6) return "(" + digits.slice(0, 2) + ") " + digits.slice(2);
  if (digits.length <= 10) return "(" + digits.slice(0, 2) + ") " + digits.slice(2, 6) + "-" + digits.slice(6);
  return "(" + digits.slice(0, 2) + ") " + digits.slice(2, 7) + "-" + digits.slice(7, 11);
}

document.querySelectorAll('input[type="tel"]').forEach(function (input) {
  input.addEventListener("input", function () {
    input.value = maskPhone(input.value);
  });
});

function maskCPF(value) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return digits.slice(0, 3) + "." + digits.slice(3);
  if (digits.length <= 9) return digits.slice(0, 3) + "." + digits.slice(3, 6) + "." + digits.slice(6);
  return digits.slice(0, 3) + "." + digits.slice(3, 6) + "." + digits.slice(6, 9) + "-" + digits.slice(9, 11);
}

function maskRG(value) {
  const digits = value.replace(/\D/g, "").slice(0, 9);
  if (digits.length <= 2) return digits;
  if (digits.length <= 5) return digits.slice(0, 2) + "." + digits.slice(2);
  if (digits.length <= 8) return digits.slice(0, 2) + "." + digits.slice(2, 5) + "." + digits.slice(5);
  return digits.slice(0, 2) + "." + digits.slice(2, 5) + "." + digits.slice(5, 8) + "-" + digits.slice(8, 9);
}

document.querySelectorAll('input[name="cpf"], input[name="cpf_locatario"]').forEach(function (input) {
  input.addEventListener("input", function () {
    input.value = maskCPF(input.value);
  });
});

document.querySelectorAll('input[name="rg"], input[name="rg_locatario"]').forEach(function (input) {
  input.addEventListener("input", function () {
    input.value = maskRG(input.value);
  });
});

document.querySelectorAll(".toggle-password").forEach(function (icon) {
  icon.addEventListener("click", function () {
    const input = icon.previousElementSibling;
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    icon.classList.toggle("bi-eye-fill", showing);
    icon.classList.toggle("bi-eye-slash-fill", !showing);
  });
});

document.querySelectorAll(".copy-link-btn").forEach(function (btn) {
  btn.addEventListener("click", function () {
    navigator.clipboard.writeText(btn.dataset.copy).then(function () {
      const toast = document.getElementById("copyToast");
      toast.classList.remove("hidden");
      clearTimeout(toast.hideTimeout);
      toast.hideTimeout = setTimeout(function () {
        toast.classList.add("hidden");
      }, 2000);
    });
  });
});

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
