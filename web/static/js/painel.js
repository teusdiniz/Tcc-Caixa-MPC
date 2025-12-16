// static/js/painel.js
document.addEventListener("DOMContentLoaded", function () {
  const main = document.querySelector("main.center");
  if (!main) return;

  const sessaoId    = main.dataset.sessaoId;
  const gavetaAtual = main.dataset.gavetaAtual; // vem do painel.html

  const btnRetirar  = document.getElementById("btnRetirar");
  const btnDevolver = document.getElementById("btnDevolver");
  const btnCancelar = document.getElementById("btnCancelar");

  console.log("[painel.js] sessaoId =", sessaoId, "gavetaAtual =", gavetaAtual);

  // Botão RETIRAR -> tela de escolha de ferramentas
  if (btnRetirar && sessaoId) {
    btnRetirar.addEventListener("click", () => {
      console.log("[painel.js] Clique em RETIRAR -> /retirar/" + sessaoId + "/");
      window.location.href = `/retirar/${sessaoId}/`;
    });
  }

  // Botão DEVOLVER (por enquanto só volta pro painel ou o que você quiser)
  if (btnDevolver && sessaoId) {
    btnDevolver.addEventListener("click", () => {
      console.log("[painel.js] Clique em DEVOLVER -> /devolver/" + sessaoId + "/");
      window.location.href = `/devolver/${sessaoId}/`;
    });
  }

  // Botão CANCELAR -> volta para home
  if (btnCancelar) {
    btnCancelar.addEventListener("click", () => {
      console.log("[painel.js] Clique em CANCELAR -> /");
      window.location.href = "/";
    });
  }

  // 🔥 Fluxo automático: se existir gaveta pendente, já manda pra tela de confirmação
  if (sessaoId && gavetaAtual) {
    console.log(
      "[painel.js] Gaveta pendente detectada. Redirecionando para /retirar-confirmar/",
      "sessao =", sessaoId,
      "gavetaAtual =", gavetaAtual
    );

    // IMPORTANTE: rota correta conforme urls.py
    window.location.href = `/retirar-confirmar/${sessaoId}/`;
  } else {
    console.log("[painel.js] Nenhuma gaveta pendente. Fica no painel.");
  }
});
