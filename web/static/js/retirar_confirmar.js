// static/js/retirar_confirmar.js

document.addEventListener("DOMContentLoaded", function () {
  const main = document.querySelector("main.center");
  if (!main) {
    console.warn("[retirar_confirmar.js] main.center não encontrado.");
    return;
  }

  const sessaoId = main.dataset.sessaoId;
  const gavetaAtual = main.dataset.gavetaAtual;
  const btnConfirmar = document.getElementById("btnConfirmar");

  if (!sessaoId || !gavetaAtual || !btnConfirmar) {
    console.warn(
      "[retirar_confirmar.js] Sessão ou gaveta_atual ou botão não definido. " +
        `sessaoId=${sessaoId}, gavetaAtual=${gavetaAtual}, btnConfirmar=${!!btnConfirmar}`
    );
    if (btnConfirmar) btnConfirmar.style.display = "none";
    return;
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return null;
  }

  btnConfirmar.addEventListener("click", async () => {
    const url = `/api/sessoes/${sessaoId}/gaveta/${gavetaAtual}/confirmar-retirada/`;
    console.log("[retirar_confirmar.js] POST", url);

    let data = null;

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken") || "",
        },
      });

      const text = await resp.text();
      console.log("[retirar_confirmar.js] HTTP", resp.status, "body:", text);

      try {
        data = text ? JSON.parse(text) : null;
      } catch (e) {
        console.error(
          "[retirar_confirmar.js] Erro ao fazer parse do JSON da resposta:",
          e
        );
      }
    } catch (err) {
      console.error(
        "[retirar_confirmar.js] Falha de comunicação ao confirmar retirada:",
        err
      );
    }

    console.log("[retirar_confirmar.js] data parseado:", data);

    // Fallbacks de rota
    const fallbackNext = `/retirar-confirmar/${sessaoId}/`;
    const fallbackEnd = "/";

    let destino = null;

    if (data && typeof data.redirect_url === "string" && data.redirect_url.length > 0) {
      destino = data.redirect_url;
      console.log("[retirar_confirmar.js] Usando redirect_url da API:", destino);
    } else if (data && data.sessao_encerrada === true) {
      destino = fallbackEnd;
      console.log(
        "[retirar_confirmar.js] sessao_encerrada=true, usando fallbackEnd:",
        destino
      );
    } else {
      // Se ainda tem gavetas ou deu algum erro de parse, volta pra próxima confirmação
      destino = fallbackNext;
      console.log(
        "[retirar_confirmar.js] Sem redirect_url/sessao_encerrada, usando fallbackNext:",
        destino
      );
    }

    // Se por algum motivo ainda não tem destino, última segurança = home
    if (!destino) {
      destino = "/";
      console.warn(
        "[retirar_confirmar.js] destino vazio, forçando redirecionamento para /"
      );
    }

    window.location.href = destino;
  });
});
