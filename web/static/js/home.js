// web/static/js/home.js

document.addEventListener("DOMContentLoaded", () => {
  const STATUS_URL = "/api/status-frontend/";

  async function checkSession() {
    try {
      const resp = await fetch(STATUS_URL, {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
      });

      if (!resp.ok) {
        console.warn("Falha ao consultar status da sessão:", resp.status);
        return;
      }

      const data = await resp.json();
      console.log("Status sessão:", data);

      // Se houver sessão ativa, manda direto pro painel
      if (data.ok && data.sessao_ativa && data.sessao_id) {
        window.location.href = `/painel/${data.sessao_id}/`;
      }
    } catch (err) {
      console.error("Erro ao consultar status da sessão:", err);
    }
  }

  // chama logo que carrega
  checkSession();

  // e repete a cada 1.5s
  setInterval(checkSession, 1500);
});
