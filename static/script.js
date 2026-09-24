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

// navigator.clipboard só existe em HTTPS/localhost; acessando pelo IP da
// rede (http://192.168...) ou se o navegador negar a permissão, caímos no
// execCommand com um textarea temporário.
function copiarTexto(texto) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(texto).catch(function () {
      return copiarTextoLegado(texto);
    });
  }
  return copiarTextoLegado(texto);
}

function copiarTextoLegado(texto) {
  const area = document.createElement("textarea");
  area.value = texto;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  const ok = document.execCommand("copy");
  document.body.removeChild(area);
  return ok ? Promise.resolve() : Promise.reject();
}

document.querySelectorAll(".copy-link-btn").forEach(function (btn) {
  btn.addEventListener("click", function () {
    copiarTexto(btn.dataset.copy).then(function () {
      const toast = document.getElementById("copyToast");
      toast.classList.remove("hidden");
      clearTimeout(toast.hideTimeout);
      toast.hideTimeout = setTimeout(function () {
        toast.classList.add("hidden");
      }, 2000);
    });
  });
});

const linkModal = document.getElementById("linkModal");

if (linkModal) {
  linkModal.querySelector("[data-fechar-modal]").addEventListener("click", function () {
    linkModal.classList.add("hidden");
  });
  linkModal.addEventListener("click", function (event) {
    if (event.target === linkModal) {
      linkModal.classList.add("hidden");
    }
  });
  // Clicar no campo seleciona o link inteiro, pra quem preferir copiar na mão.
  linkModal.querySelector(".modal-link").addEventListener("focus", function (event) {
    event.target.select();
  });
}

// Confirmação de ações destrutivas: formulários com data-confirmar="texto"
// abrem o #confirmModal (base.html) antes de enviar.
const confirmModal = document.getElementById("confirmModal");

if (confirmModal) {
  let formPendente = null;
  const fecharConfirmacao = function () {
    confirmModal.classList.add("hidden");
    formPendente = null;
  };

  document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (form.dataset.confirmado) return;
      event.preventDefault();
      formPendente = form;
      document.getElementById("confirmModalTexto").textContent = form.dataset.confirmar;
      confirmModal.querySelector("[data-confirmar-sim]").textContent = form.dataset.confirmarBotao || "Confirmar";
      confirmModal.classList.remove("hidden");
      confirmModal.querySelector("[data-confirmar-nao]").focus();
    });
  });

  confirmModal.querySelector("[data-confirmar-sim]").addEventListener("click", function () {
    if (!formPendente) return;
    const form = formPendente;
    form.dataset.confirmado = "1";
    fecharConfirmacao();
    form.requestSubmit();
  });
  confirmModal.querySelector("[data-confirmar-nao]").addEventListener("click", fecharConfirmacao);
  confirmModal.addEventListener("click", function (event) {
    if (event.target === confirmModal) fecharConfirmacao();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !confirmModal.classList.contains("hidden")) fecharConfirmacao();
  });
}

document.querySelectorAll(".flash-fechar").forEach(function (botao) {
  botao.addEventListener("click", function () {
    botao.closest(".flash").remove();
  });
});

// Calendário: tocar num dia ocupado mostra só os contratos daquele dia na
// lista abaixo do calendário (no celular não existe hover/tooltip).
const calendarLista = document.querySelector(".calendar-lista");

if (calendarLista) {
  const titulo = document.getElementById("calendarListaTitulo");
  const tituloOriginal = titulo.textContent;
  const mostrarTodos = document.getElementById("calendarMostrarTodos");
  const itens = calendarLista.querySelectorAll("li[data-contrato-id]");

  const limparFiltro = function () {
    document.querySelectorAll(".calendar-day-selecionado").forEach(function (dia) {
      dia.classList.remove("calendar-day-selecionado");
    });
    itens.forEach(function (item) {
      item.classList.remove("hidden");
    });
    titulo.textContent = tituloOriginal;
    mostrarTodos.classList.add("hidden");
  };

  document.querySelectorAll(".calendar-day[data-contratos]").forEach(function (dia) {
    dia.addEventListener("click", function () {
      if (dia.classList.contains("calendar-day-selecionado")) {
        limparFiltro();
        return;
      }
      limparFiltro();
      const ids = dia.dataset.contratos.split(",");
      dia.classList.add("calendar-day-selecionado");
      itens.forEach(function (item) {
        item.classList.toggle("hidden", !ids.includes(item.dataset.contratoId));
      });
      titulo.textContent = "Dia " + dia.dataset.dia;
      mostrarTodos.classList.remove("hidden");
      calendarLista.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });

  mostrarTodos.addEventListener("click", limparFiltro);
}

const contractModal = document.getElementById("contractModal");
const dataForm = document.getElementById("dataForm");

if (dataForm) {
  // Espelha no texto do contrato o que o locatário digita, para ele ler
  // exatamente o que vai assinar.
  dataForm.querySelectorAll("input[name]").forEach(function (input) {
    const spans = document.querySelectorAll(
      '.campo-locatario[data-campo="' + input.name + '"]'
    );
    function atualizar() {
      const valor = input.value.trim();
      spans.forEach(function (span) {
        span.textContent = valor || "[" + input.placeholder + "]";
        span.classList.toggle("vazio", !valor);
      });
    }
    input.addEventListener("input", atualizar);
    atualizar();
  });

  // O aceite só é liberado depois que o locatário rola o contrato até o fim.
  const contratoTexto = document.getElementById("contratoTexto");
  const termos = document.getElementById("terms");
  function liberarAceite() {
    const noFim =
      contratoTexto.scrollTop + contratoTexto.clientHeight >=
      contratoTexto.scrollHeight - 10;
    if (noFim) {
      termos.disabled = false;
      document.getElementById("leituraAviso").classList.add("hidden");
      contratoTexto.removeEventListener("scroll", liberarAceite);
    }
  }
  if (contratoTexto && termos) {
    contratoTexto.addEventListener("scroll", liberarAceite);
    liberarAceite();
  }

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
