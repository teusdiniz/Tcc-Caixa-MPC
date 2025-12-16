document.addEventListener("DOMContentLoaded", () => {
  const main = document.querySelector("main[data-sessao-id]");
  if (!main) return;

  const sessaoId = main.dataset.sessaoId;
  const btnAvancar = document.getElementById("btnAvancar");
  const toolCards = document.querySelectorAll(".tool-card");

  // Conjunto com os IDs selecionados
  const selecionadas = new Set();

  // Toggle de seleção visual + lógica
  function toggleCard(card) {
    const id = card.getAttribute("data-id");
    if (!id) return;

    if (selecionadas.has(id)) {
      selecionadas.delete(id);
      card.classList.remove("selected");
      card.setAttribute("aria-pressed", "false");
    } else {
      selecionadas.add(id);
      card.classList.add("selected");
      card.setAttribute("aria-pressed", "true");
    }
  }

  // Clique em cada cartão de ferramenta
  toolCards.forEach((card) => {
    card.addEventListener("click", () => toggleCard(card));
    card.addEventListener("keydown", (ev) => {
      if (ev.key === " " || ev.key === "Enter") {
        ev.preventDefault();
        toggleCard(card);
      }
    });
  });

  // Botão "Próximo"
  if (btnAvancar) {
    btnAvancar.addEventListener("click", async () => {
      if (!sessaoId) {
        alert("Sessão inválida.");
        return;
      }

      const ids = Array.from(selecionadas);
      if (!ids.length) {
        alert("Selecione pelo menos uma ferramenta para devolver.");
        return;
      }

      try {
        const resp = await fetch(`/devolver/selecionar?sessao_id=${sessaoId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ ferramentas_ids: ids }),
        });

        const data = await resp.json().catch(() => null);

        if (!resp.ok) {
          alert((data && data.error) || "Erro ao registrar seleção.");
          return;
        }

        if (!data || !data.next_url) {
          alert("Resposta inválida do servidor.");
          return;
        }

        // AGORA SIM: usa a URL vinda do backend
        window.location.href = data.next_url;
      } catch (err) {
        console.error("Erro ao enviar seleção:", err);
        alert("Falha na comunicação com o servidor.");
      }
    });
  }
});
