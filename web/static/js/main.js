// detecta se é a tela inicial (tem #status)
const isIndex = !!document.getElementById("status");

// ----- relógio -----
function startClock() {
  const el = document.getElementById("clock");
  if (!el) return;
  const tick = () => {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    el.textContent =
      `${pad(now.getDate())}/${pad(now.getMonth()+1)}/${now.getFullYear()}   ` +
      `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  };
  tick();
  setInterval(tick, 1000);
}

// ----- pontinhos (só na index) -----
function animateDots() {
  const el = document.getElementById("dots");
  if (!el) return;
  let i = 0;
  setInterval(() => {
    el.textContent = ".".repeat(i % 4);
    i++;
  }, 500);
}

// ----- polling + redirecionamento (só na index) -----
let redirected = false;
async function pollRFID() {
  try {
    const r = await fetch("/api/status", { cache: "no-store" });
    const data = await r.json();

    if (isIndex) {
      const statusEl = document.getElementById("status");
      if (statusEl && data.status === "aguardando") {
        statusEl.textContent = "Aguardando";
      }

      if (!redirected) {
        if (data.status === "lido") {
          redirected = true;
          window.location.assign("/painel");
          return;
        }
        if (data.status === "negado") {
          redirected = true;
          window.location.assign("/negado");
          return;
        }
      }
    }
  } catch (e) {
    console.warn("Falha no polling:", e);
  } finally {
    if (isIndex) setTimeout(pollRFID, 600);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  startClock();
  animateDots();
  if (isIndex) {
    // Em produção, o fluxo depende apenas da leitura RFID (ou das rotas de simulação)
    pollRFID();
  }
});
