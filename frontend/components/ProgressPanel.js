export function ProgressPanel(progression, history) {
  if (!progression) {
    return `
      <section class="progress-panel">
        <div class="panel-heading">
          <div>
            <span class="eyebrow">Succes</span>
            <h2>Compte</h2>
          </div>
        </div>
        <p class="empty-state">Connectez-vous pour voir vos succes.</p>
      </section>
    `;
  }
  const nextDistance = progression.next_level_distance_km || 1000;
  const distance = progression.distance_km || 0;
  const distancePercent = Math.min(100, Math.round(distance / nextDistance * 100));
  return `
    <section class="progress-panel">
      <div class="panel-heading">
        <div>
          <span class="eyebrow">Succes</span>
          <h2>Compte niveau ${progression.level}</h2>
        </div>
      </div>
      <div class="level-progress">
        <div class="meter-head">
          <span>Kilometrage de compte</span>
          <strong>${distance} / ${nextDistance} km</strong>
        </div>
        <div class="meter-track"><span style="width:${distancePercent}%"></span></div>
      </div>
      <div class="progress-grid">
        <div><span>Trajets</span><strong>${progression.completed_trajets}</strong></div>
        <div><span>Evenements</span><strong>${progression.successful_events}</strong></div>
        <div><span>Distance</span><strong>${progression.distance_km}</strong></div>
        <div><span>Skins</span><strong>${progression.unlocked_skins.length}</strong></div>
      </div>
      <div class="achievements">
        ${progression.achievements.length ? progression.achievements.map((item) => `<span>${item}</span>`).join("") : `<span>Aucun succes</span>`}
      </div>
      <div class="panel-heading compact">
        <div>
          <span class="eyebrow">Historique</span>
          <h2>Trajets</h2>
        </div>
      </div>
      <div class="history-list">
        ${history.length ? history.slice(0, 4).map((item) => `<span>${item.title}</span>`).join("") : `<span>Vide</span>`}
      </div>
    </section>
  `;
}
