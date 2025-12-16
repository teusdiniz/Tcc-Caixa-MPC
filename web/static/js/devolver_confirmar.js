// web/static/js/devolver_confirmar.js

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("formConfirmar");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const sessaoId = form.dataset.sessaoId;
    const gavetaNumero = form.dataset.gavetaNumero;

    if (!sessaoId || !gavetaNumero) {
      console.error("Sessão ou gaveta não definidos no form.");
      alert("Erro interno: sessão ou gaveta não definidos.");
      return;
    }

    try {
      const resp = await fetch(
        `/api/sessoes/${sessaoId}/gaveta/${gavetaNumero}/confirmar-devolucao/`,
        {
          method: "POST",
          headers: {
            "Accept": "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({}),
        }
      );

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        console.error("Erro ao confirmar devolução:", resp.status, errData);
        alert("Falha ao confirmar devolução. Veja o console para detalhes.");
        return;
      }

      const data = await resp.json();
      console.log("Resposta confirmar devolução:", data);

      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        alert("Devolução confirmada, mas sem redirect_url. Atualize a página.");
      }
    } catch (err) {
      console.error("Erro de rede ao confirmar devolução:", err);
      alert("Erro de rede ao confirmar devolução.");
    }
  });
});
