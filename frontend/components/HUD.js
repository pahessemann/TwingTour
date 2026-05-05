import { cityName } from "../services/state.js";


function meter(value, max, label, tone) {
  const width = Math.max(0, Math.min(100, (value / max) * 100));
  return `
    <div class="meter ${tone}">
      <div class="meter-head">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
      <div class="meter-track"><span style="width: ${width}%"></span></div>
    </div>
  `;
}


export function HUD(user, progression) {
  if (!user || !progression) {
    return "";
  }
  const fuelCapacity = progression.fuel_capacity || 100;
  const durability = progression.durability ?? 100;
  return `
    <header class="hud">
      <div class="hud-player">
        <span class="hud-avatar">${user.display_name.slice(0, 2).toUpperCase()}</span>
        <div>
          <strong>${user.display_name}</strong>
          <span>${cityName(progression.current_node_id)}</span>
        </div>
      </div>
      <div class="hud-stats">
        ${meter(progression.fuel, fuelCapacity, "Carburant", "fuel")}
        ${meter(durability, 100, "Durabilite", durability < 30 ? "durability danger" : "durability")}
        ${meter(progression.xp % 250, 250, `Niveau ${progression.level}`, "xp")}
        <div class="stat-chip"><span>De</span><strong>${progression.dice_remaining ? `${progression.dice_remaining}/${progression.turn_roll}` : "-"}</strong></div>
        <div class="stat-chip"><span>Pieces partie</span><strong>${progression.coins}</strong></div>
        <div class="stat-chip"><span>Km</span><strong>${progression.distance_km}</strong></div>
        <div class="stat-chip ${progression.repairs_needed ? "danger" : ""}"><span>Panne</span><strong>${progression.repairs_needed ? "Oui" : "Non"}</strong></div>
      </div>
      <button class="icon-button" title="Quitter" aria-label="Quitter" data-action="close-session-or-logout" type="button">X</button>
    </header>
  `;
}
