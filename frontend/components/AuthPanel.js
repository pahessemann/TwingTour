export function AuthPanel(mode) {
  const isRegister = mode === "register";
  return `
    <main class="auth-screen">
      <section class="auth-board">
        <div class="brand-lockup">
          <img src="/assets/twingo-common.svg" alt="" class="brand-car" />
          <div>
            <p class="eyebrow">EuroTwingo</p>
            <h1>EuroTwingo</h1>
          </div>
        </div>
        <form class="auth-form" data-auth-form="${mode}">
          <label>
            <span>Email</span>
            <input name="email" type="email" autocomplete="email" required placeholder="pilote@eurotwingo.fr" />
          </label>
          <label>
            <span>Mot de passe</span>
            <input name="password" type="password" autocomplete="${isRegister ? "new-password" : "current-password"}" required minlength="6" placeholder="6 caracteres minimum" />
          </label>
          ${isRegister ? `
            <label>
              <span>Pseudo</span>
              <input name="display_name" type="text" autocomplete="nickname" placeholder="Pilote Twingo" />
            </label>
          ` : ""}
          <button class="primary-button" type="submit">${isRegister ? "Creer le compte" : "Entrer dans le garage"}</button>
        </form>
        <div class="auth-switch">
          <button class="ghost-button ${mode === "login" ? "is-active" : ""}" data-auth-mode="login" type="button">Connexion</button>
          <button class="ghost-button ${mode === "register" ? "is-active" : ""}" data-auth-mode="register" type="button">Compte</button>
        </div>
      </section>
      <section class="auth-map-preview" aria-hidden="true">
        <div class="preview-road"></div>
        <img src="/assets/twingo-kenzo.svg" alt="" class="preview-car" />
      </section>
    </main>
  `;
}
