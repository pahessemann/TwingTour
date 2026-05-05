function skinCard(skin) {
  const action = skin.unlocked
    ? `<button class="ghost-button" ${skin.equipped ? "disabled" : `data-equip-skin="${skin.slug}"`} type="button">${skin.equipped ? "Equipee" : "Equiper"}</button>`
    : `<button class="ghost-button" disabled type="button">A trouver</button>`;
  return `
    <article class="skin-card ${skin.equipped ? "is-equipped" : ""}">
      <img src="${skin.asset}" alt="" />
      <div>
        <div class="card-topline">
          <span>${skin.rarity}</span>
          <strong>${skin.inspired_by}</strong>
        </div>
        <h3>${skin.name}</h3>
        <p>${skin.description}</p>
        <div class="skin-count">
          <span>${skin.unlocked ? `${skin.owned_count} copie${skin.owned_count > 1 ? "s" : ""}` : "Non obtenu"}</span>
          <span>Tier ${skin.min_level}</span>
        </div>
        <div class="swatches">
          ${skin.palette.map((color) => `<i style="background:${color}"></i>`).join("")}
        </div>
      </div>
      <div class="skin-actions">
        ${action}
        <button class="ghost-button" data-fuse-skin="${skin.slug}" ${skin.can_fuse ? "" : "disabled"} type="button">Fusion 5x</button>
      </div>
    </article>
  `;
}


export function GaragePanel(skins, lootboxes = 0, activeTab = "owned") {
  const safeTab = activeTab === "all" ? "all" : "owned";
  const ownedSkins = skins.filter((skin) => skin.unlocked);
  const visibleSkins = safeTab === "owned" ? ownedSkins : skins;
  return `
    <section class="garage-panel">
      <div class="panel-heading">
        <div>
          <span class="eyebrow">Garage</span>
          <h2>Skins Twingo</h2>
        </div>
      </div>
      <nav class="garage-tabs" aria-label="Filtres de skins">
        <button class="ghost-button ${safeTab === "owned" ? "is-active" : ""}" data-skin-tab="owned" type="button">
          Possedes (${ownedSkins.length})
        </button>
        <button class="ghost-button ${safeTab === "all" ? "is-active" : ""}" data-skin-tab="all" type="button">
          Tous les skins (${skins.length})
        </button>
      </nav>
      <div class="lootbox-bar">
        <div>
          <strong>${lootboxes}</strong>
          <span>lootbox${lootboxes > 1 ? "es" : ""} disponible${lootboxes > 1 ? "s" : ""}</span>
        </div>
        <button class="primary-button" data-action="open-lootbox" ${lootboxes > 0 ? "" : "disabled"} type="button">Ouvrir</button>
      </div>
      <div class="skins-list">
        ${visibleSkins.length ? visibleSkins.map(skinCard).join("") : `<p class="empty-state">Aucun skin dans cet onglet.</p>`}
      </div>
    </section>
  `;
}
