export function ToastStack(toasts) {
  return `
    <div class="toast-stack" aria-live="polite">
      ${toasts.map((toast) => `
        <aside class="toast ${toast.severity || "info"}">
          <strong>${toast.title || "EuroTwingo"}</strong>
          <span>${toast.body || ""}</span>
        </aside>
      `).join("")}
    </div>
  `;
}


export function TurnNotice(notice) {
  if (!notice) {
    return "";
  }
  return `
    <div class="turn-notice" role="status" aria-live="polite">
      <aside>
        <span>${notice.previous || "Joueur"} a fini son tour</span>
        <strong>Au tour de ${notice.next || "joueur suivant"}</strong>
      </aside>
    </div>
  `;
}
