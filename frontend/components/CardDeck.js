import { cityName } from "../services/state.js";


function requiredCities(card) {
  if (!card.trajet) {
    return "";
  }
  return card.trajet.city_ids.map((id) => `<span>${cityName(id)}</span>`).join("");
}


function trajetXp(card) {
  return Math.max(1, Math.round((card?.trajet?.distance_hint || 0) / 100));
}


function cardActions(card) {
  if (card.status === "completed") {
    return `<button class="ghost-button" disabled type="button">Validee</button>`;
  }
  if (card.type === "trajet") {
    return `
      <div class="card-actions">
        <button class="ghost-button" data-complete-card="${card.inventory_id}" type="button">Valider</button>
        <button class="ghost-button" data-discard-card="${card.inventory_id}" type="button">Abandonner</button>
      </div>
    `;
  }
  return `<button class="ghost-button" data-apply-card="${card.inventory_id}" type="button">Jouer</button>`;
}


function cardMarkup(card) {
  return `
    <article class="game-card ${card.type} ${card.status === "completed" ? "is-done" : ""}">
      <div class="card-topline">
        <span>${card.type}</span>
        <strong>${card.rarity}</strong>
      </div>
      <h3>${card.name}</h3>
      <p>${card.description}</p>
      ${card.trajet ? `<div class="city-tags">${requiredCities(card)}</div>` : ""}
      ${card.trajet ? `<div class="task-rewards"><span>${card.trajet.distance_hint} km</span><span>${trajetXp(card)} XP</span></div>` : ""}
      ${cardActions(card)}
    </article>
  `;
}


function missionTypeLabel(mission) {
  if (mission.mission_type === "deplacement") return `Vers ${mission.target_node_id}`;
  if (mission.mission_type === "teleport_capital") return `Teleport capitale ${mission.target_node_id}`;
  if (mission.mission_type === "teleport_random") return `Teleport mystere ${mission.target_node_id}`;
  if (mission.mission_type === "meteo_double") return "Double de immediat";
  if (mission.mission_type === "meteo_block") return "Intemperies";
  return "Immobilisation";
}


function missionMarkup(mission, active, canAct) {
  return `
    <article class="mission-card ${active ? "is-active" : "is-done"}">
      <div class="card-topline">
        <span>${mission.country}</span>
        <strong>${mission.difficulty}</strong>
      </div>
      <h3>${mission.title}</h3>
      <p>${mission.city} - ${mission.description}</p>
      <div class="task-rewards">
        <span>${missionTypeLabel(mission)}</span>
        <span>+${mission.reward_coins} pieces</span>
        <span>+${mission.reward_xp} XP</span>
        <span>+${mission.reward_durability || 0} durabilite</span>
        <span>${mission.duration_turns || 1} tour${(mission.duration_turns || 1) > 1 ? "s" : ""}</span>
      </div>
      ${active ? `<button class="primary-button" data-complete-task="${mission.difficulty}" ${canAct ? "" : "disabled"} type="button">Realiser</button>` : `<button class="ghost-button" disabled type="button">Finie</button>`}
    </article>
  `;
}


function missionPanel(session) {
  const missions = session?.missions || { active: [], completed: [] };
  const canAct = Boolean(session?.is_my_turn && !session?.me?.mission_locked_turns);
  return `
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">Mission</span>
        <h2>Active</h2>
      </div>
    </div>
    <div class="cards-grid compact-cards">
      ${missions.active.length ? missions.active.map((mission) => missionMarkup(mission, true, canAct)).join("") : `<p class="empty-state">Aucune mission active.</p>`}
    </div>
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">Mission</span>
        <h2>Finies</h2>
      </div>
    </div>
    <div class="cards-grid compact-cards">
      ${missions.completed.length ? missions.completed.map((mission) => missionMarkup(mission, false, canAct)).join("") : `<p class="empty-state">Aucune mission finie.</p>`}
    </div>
  `;
}


function trajetsPanel(activeTrajets, completedTrajets) {
  return `
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">Trajets</span>
        <h2>A terminer</h2>
      </div>
    </div>
    <div class="cards-grid">
      ${activeTrajets.length ? activeTrajets.map(cardMarkup).join("") : `<p class="empty-state">Aucun trajet actif.</p>`}
    </div>
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">Archive</span>
        <h2>Trajets de la partie</h2>
      </div>
    </div>
    <div class="mini-history">
      ${completedTrajets.length ? completedTrajets.map((card) => `<span>${card.name}</span>`).join("") : `<span>Vide</span>`}
    </div>
  `;
}


function specialsPanel(activeSpecials, completedSpecials) {
  return `
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">Malus / Bonus</span>
        <h2>En attente</h2>
      </div>
    </div>
    <div class="cards-grid compact-cards">
      ${activeSpecials.length ? activeSpecials.map(cardMarkup).join("") : `<p class="empty-state">Aucune carte bonus/malus.</p>`}
    </div>
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">Jouees</span>
        <h2>Ce tour de route</h2>
      </div>
    </div>
    <div class="mini-history">
      ${completedSpecials.length ? completedSpecials.map((card) => `<span>${card.name}</span>`).join("") : `<span>Vide</span>`}
    </div>
  `;
}


function nodeLabel(map, nodeId) {
  const node = map?.nodes?.find((item) => item.id === nodeId);
  return node ? `${node.city}, ${node.country}` : nodeId;
}


function carpoolerMarkup(carpooler, map, session) {
  const assignedToMe = String(carpooler.assigned_user_id || "") === String(session?.me?.user_id || "");
  const atStartCity = session?.me?.current_node_id === carpooler.start_node_id;
  const canAccept = session?.is_my_turn && atStartCity && carpooler.status === "waiting" && !session?.me?.mission_locked_turns && !session?.carpoolers?.some((item) => (
    String(item.assigned_user_id || "") === String(session?.me?.user_id || "") && item.status === "active"
  ));
  return `
    <article class="carpooler-card ${carpooler.status}">
      <div class="card-topline">
        <span>${carpooler.status === "active" && assignedToMe ? "A bord" : carpooler.status}</span>
        <strong>${carpooler.victory_points} pts</strong>
      </div>
      <h3>${carpooler.name}</h3>
      <p>${nodeLabel(map, carpooler.start_node_id)} vers ${nodeLabel(map, carpooler.destination_node_id)}</p>
      <div class="task-rewards">
        <span>+${carpooler.reward_coins || 0} pieces</span>
        <span>+${carpooler.reward_durability || 0} durabilite</span>
        <span>${carpooler.min_turns || 2} tours min.</span>
        ${carpooler.status === "waiting" ? `<span>${atStartCity ? "Rencontre ici" : "A rencontrer"}</span>` : ""}
      </div>
      ${carpooler.status === "waiting" ? `<button class="ghost-button" data-accept-carpooler="${carpooler.id}" ${canAccept ? "" : "disabled"} type="button">Accepter</button>` : ""}
    </article>
  `;
}


function carpoolingPanel(session, map) {
  const carpoolers = session?.carpoolers || [];
  const myId = String(session?.me?.user_id || "");
  const active = carpoolers.filter((item) => item.status === "active" && String(item.assigned_user_id || "") === myId);
  const waitingHere = carpoolers.filter((item) => item.status === "waiting" && item.start_node_id === session?.me?.current_node_id);
  const waitingElsewhere = carpoolers.filter((item) => item.status === "waiting" && item.start_node_id !== session?.me?.current_node_id);
  const delivered = carpoolers.filter((item) => item.status === "delivered" && String(item.assigned_user_id || "") === myId);
  return `
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">Covoiturage</span>
        <h2>A bord</h2>
      </div>
    </div>
    <div class="cards-grid compact-cards">
      ${active.length ? active.map((item) => carpoolerMarkup(item, map, session)).join("") : `<p class="empty-state">Aucun passager dans la Twingo.</p>`}
    </div>
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">Disponibles</span>
        <h2>Dans cette ville</h2>
      </div>
    </div>
    <div class="cards-grid compact-cards">
      ${waitingHere.length ? waitingHere.map((item) => carpoolerMarkup(item, map, session)).join("") : `<p class="empty-state">Aucun covoitureur a rencontrer ici.</p>`}
    </div>
    <div class="panel-heading compact">
      <div>
        <span class="eyebrow">A trouver</span>
        <h2>Points de depart</h2>
      </div>
    </div>
    <div class="cards-grid compact-cards">
      ${waitingElsewhere.length ? waitingElsewhere.map((item) => carpoolerMarkup(item, map, session)).join("") : `<p class="empty-state">Aucun autre depart connu.</p>`}
    </div>
    <div class="mini-history">
      ${delivered.length ? delivered.map((item) => `<span>${item.name} depose</span>`).join("") : `<span>Aucun depot</span>`}
    </div>
  `;
}


export function CardDeck(inventory, session, tab = "trajets", map = { nodes: [] }) {
  const sessionId = session?.id;
  const scopedInventory = sessionId
    ? inventory.filter((card) => card.session_id === sessionId || (card.status === "active" && card.session_id == null))
    : inventory;
  const active = scopedInventory.filter((card) => card.status === "active");
  const activeTrajets = active.filter((card) => card.type === "trajet");
  const activeSpecials = active.filter((card) => card.type !== "trajet");
  const completedTrajets = scopedInventory.filter((card) => card.status === "completed" && card.type === "trajet" && card.session_id === sessionId).slice(0, 6);
  const completedSpecials = scopedInventory.filter((card) => card.status === "completed" && card.type !== "trajet" && card.session_id === sessionId).slice(0, 6);
  const activeMissionCount = session?.missions?.active?.length || 0;
  const activeCarpoolers = session?.carpoolers?.filter((item) => item.status === "active" && String(item.assigned_user_id || "") === String(session?.me?.user_id || "")).length || 0;
  const canDrawTrajets = session?.is_my_turn && session?.status !== "lobby" && !session?.me?.mission_locked_turns && activeTrajets.length < 3;
  const safeTab = ["trajets", "specials", "missions", "carpooling"].includes(tab) ? tab : "trajets";
  const title = {
    trajets: `${activeTrajets.length} trajet${activeTrajets.length > 1 ? "s" : ""}`,
    specials: `${activeSpecials.length} carte${activeSpecials.length > 1 ? "s" : ""}`,
    missions: `${activeMissionCount} mission${activeMissionCount > 1 ? "s" : ""}`,
    carpooling: `${activeCarpoolers}/1 passager`,
  }[safeTab];
  return `
    <section class="deck-panel inventory-window">
      <div class="panel-heading">
        <div>
          <span class="eyebrow">Inventaire</span>
          <h2>${title}</h2>
        </div>
        <div class="draw-buttons">
          <button class="primary-button" data-action="draw-trajets" ${canDrawTrajets ? "" : "disabled"} type="button">Piocher trajets</button>
        </div>
      </div>
      <div class="inventory-tabs">
        <button class="ghost-button ${safeTab === "trajets" ? "is-active" : ""}" data-inventory-tab="trajets" type="button">Trajets</button>
        <button class="ghost-button ${safeTab === "specials" ? "is-active" : ""}" data-inventory-tab="specials" type="button">Malus / Bonus</button>
        <button class="ghost-button ${safeTab === "missions" ? "is-active" : ""}" data-inventory-tab="missions" type="button">Missions</button>
        <button class="ghost-button ${safeTab === "carpooling" ? "is-active" : ""}" data-inventory-tab="carpooling" type="button">Covoiturage</button>
      </div>
      <div class="inventory-rule">
        <strong>${activeTrajets.length}/3</strong>
        <span>trajets actifs. Pioche limitee a 1 long et 2 courts par tour.</span>
      </div>
      ${safeTab === "trajets" ? trajetsPanel(activeTrajets, completedTrajets) : ""}
      ${safeTab === "specials" ? specialsPanel(activeSpecials, completedSpecials) : ""}
      ${safeTab === "missions" ? missionPanel(session) : ""}
      ${safeTab === "carpooling" ? carpoolingPanel(session, map) : ""}
    </section>
  `;
}
