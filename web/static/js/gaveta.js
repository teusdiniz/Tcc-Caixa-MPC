function initClock(){
  const el = document.getElementById("clock");
  if (!el) return;
  const pad = n => String(n).padStart(2, "0");
  const tick = () => {
    const d = new Date();
    el.textContent =
      `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()}   ` +
      `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  };
  tick();
  setInterval(tick, 1000);
}

async function confirmar(){
  const btn = document.getElementById("btnOk");
  btn.disabled = true;
  try{
    const r = await fetch("/gaveta/confirmar", { method:"POST" });
    const data = await r.json();
    if (data.redirect) window.location.assign(data.redirect);
  }catch(e){
    console.warn("Falha ao confirmar:", e);
    btn.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initClock();
  document.getElementById("btnOk").addEventListener("click", confirmar);

  // enter confirma, ESC volta
  document.addEventListener("keydown", (ev)=>{
    if (ev.key === "Enter") confirmar();
    if (ev.key === "Escape") window.location.assign("/retirar/revisao");
  });
});
