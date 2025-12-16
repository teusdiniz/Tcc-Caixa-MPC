document.addEventListener("DOMContentLoaded", function () {
  const main = document.querySelector("main.center");
  if (!main) return;

  const sessaoId = main.dataset.sessaoId;
  const cards = document.querySelectorAll(".tool-card");
  const btnNext = document.getElementById("btnNext");

  function updateButton() {
    const hasSelected = document.querySelector('.tool-card[aria-pressed="true"]');
    if (btnNext) {
      btnNext.disabled = !hasSelected;
    }
  }

  // Toggle seleção dos cards
  cards.forEach((card) => {
    card.addEventListener("click", () => {
      const pressed = card.getAttribute("aria-pressed") === "true";
      card.setAttribute("aria-pressed", (!pressed).toString());
      card.classList.toggle("tool-card--selected", !pressed);
      updateButton();
    });
  });

  // Pega CSRF do cookie
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return null;
  }

  if (btnNext) {
    btnNext.addEventListener("click", async () => {
      const selecionadas = Array.from(
        document.querySelectorAll('.tool-card[aria-pressed="true"]')
      );

      if (!selecionadas.length) {
        // sem popup, só ignora o clique
        return;
      }

      const ids = selecionadas.map((card) => parseInt(card.dataset.id, 10));

      try {
        const resp = await fetch(`/api/sessoes/${sessaoId}/retiradas/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          body: JSON.stringify({
            ferramentas_ids: ids,
          }),
        });

        if (!resp.ok) {
          // sem alert, só loga no console
          const txt = await resp.text();
          console.error("Erro ao registrar retirada:", resp.status, txt);
          return;
        }

        // antes: window.location.href = `/painel/${sessaoId}/?gaveta=${data.primeira_gaveta}`;
        // agora: manda para tela de confirmação
        window.location.href = `/retirar-confirmar/${sessaoId}/`;
      } catch (err) {
        console.error("Falha na requisição:", err);
      }
    });
  }

  updateButton();
});
