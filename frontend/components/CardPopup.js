import { cityName } from "../services/state.js";


function requiredCities(card) {
  if (!card?.trajet) return "";
  return card.trajet.city_ids.map((id) => `<span>${cityName(id)}</span>`).join("");
}


function trajetXp(card) {
  return Math.max(1, Math.round((card?.trajet?.distance_hint || 0) / 100));
}


export function CardPopup(card) {
  if (!card) return "";
  return `
    <div class="modal-backdrop" data-action="close-card-popup">
      <aside class="draw-modal" role="dialog" aria-modal="true">
        <div class="card-topline">
          <span>${card.type}</span>
          <strong>${card.rarity}</strong>
        </div>
        <h2>${card.name}</h2>
        <p>${card.description}</p>
        ${card.trajet ? `<div class="city-tags">${requiredCities(card)}</div>` : ""}
        <button class="primary-button" data-action="close-card-popup" type="button">Mettre dans l'inventaire</button>
      </aside>
    </div>
  `;
}


export function CarpoolerPopup(carpooler, map) {
  if (!carpooler) return "";
  const start = map.nodes.find((node) => node.id === carpooler.start_node_id);
  const destination = map.nodes.find((node) => node.id === carpooler.destination_node_id);
  return `
    <div class="modal-backdrop">
      <aside class="draw-modal carpooler-modal" role="dialog" aria-modal="true">
        <span class="eyebrow">Covoiturage rare</span>
        <h2>${carpooler.name}</h2>
        <p>Rencontre a ${start?.city || carpooler.start_node_id}. Destination ${destination?.city || carpooler.destination_node_id}, gros bonus de score au depot.</p>
        <div class="card-actions">
          <button class="primary-button" data-accept-carpooler="${carpooler.id}" type="button">Accepter</button>
          <button class="ghost-button" data-action="dismiss-carpooler" type="button">Passer</button>
        </div>
      </aside>
    </div>
  `;
}


export function StartingTrajetChoice(session, selection = []) {
  const choices = session?.starting_trajet_choices || [];
  if (!choices.length) return "";
  const selected = new Set(selection.map(Number));
  const selectedCount = choices.filter((card) => selected.has(Number(card.inventory_id))).length;
  return `
    <div class="modal-backdrop start-choice-backdrop">
      <aside class="start-choice-modal" role="dialog" aria-modal="true">
        <div class="start-choice-heading">
          <div>
            <span class="eyebrow">Trajets de depart</span>
            <h2>Choisissez 3 cartes</h2>
          </div>
          <strong>${selectedCount}/3</strong>
        </div>
        <p>Selectionnez vos trajets de depart. Les 5 propositions contiennent 3 trajets faciles et 2 longs, avec au moins un trajet facile depuis votre capitale.</p>
        <div class="start-choice-row">
          ${choices.map((card) => `
            <button class="start-choice-card ${selected.has(Number(card.inventory_id)) ? "is-selected" : ""}" data-start-choice-card="${card.inventory_id}" type="button">
              <span>${card.rarity}</span>
              <strong>${card.name}</strong>
              <em>${card.trajet?.kind === "long" ? "Long trajet" : "Trajet facile"}</em>
              ${card.trajet ? `<div class="city-tags">${requiredCities(card)}</div>` : ""}
              <small>${card.trajet?.distance_hint || 0} km - ${trajetXp(card)} XP</small>
            </button>
          `).join("")}
        </div>
        <div class="start-choice-actions">
          <button class="primary-button" data-action="confirm-start-trajets" ${selectedCount === 3 ? "" : "disabled"} type="button">Mettre dans l'inventaire</button>
        </div>
      </aside>
    </div>
  `;
}
