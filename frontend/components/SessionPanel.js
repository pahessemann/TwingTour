function taskMarkup(task, enabled, hasActiveMission, currentUserId) {
  const done = Boolean(task.completed_by);
  const activeByMe = String(task.active_by) === String(currentUserId);
  const activeByOther = task.active_by && !activeByMe;
  const canActivate = enabled && !done && !activeByOther && (!hasActiveMission || activeByMe);
  return `
    <article class="task-card ${done ? "is-done" : ""}">
      <div class="card-topline">
        <span>${task.difficulty}</span>
        <strong>${task.speed}</strong>
      </div>
      <h3>${task.title}</h3>
      <p>${task.description}</p>
      <div class="task-rewards">
        <span>${task.mission_type === "deplacement" ? `Vers ${task.target_node_id}` : "Immobilisation"}</span>
        <span>+${task.reward_coins} pieces</span>
        <span>+${task.reward_xp} XP</span>
        <span>+${task.reward_durability || 0} durabilite</span>
        <span>${task.duration_turns || 1} tour${(task.duration_turns || 1) > 1 ? "s" : ""}</span>
      </div>
      <button class="ghost-button" data-activate-task="${task.difficulty}" ${canActivate ? "" : "disabled"} type="button">${done ? "Finie" : activeByMe ? "Active" : activeByOther ? "Prise" : "Activer"}</button>
    </article>
  `;
}


function playerMarkup(player, currentUserId) {
  return `
    <article class="lobby-player ${player.user_id === currentUserId ? "is-me" : ""}">
      <span>${player.user_id === currentUserId ? "Vous" : "Pilote"}</span>
      <strong>${player.display_name}</strong>
      <em>${player.spawn_node_id || player.current_node_id}</em>
    </article>
  `;
}


function spawnOptions(spawns, current) {
  return spawns.map((node) => `<option value="${node.id}" ${node.id === current ? "selected" : ""}>${node.country} - ${node.city}</option>`).join("");
}


function standings(session) {
  const rows = session.final_standings || [];
  return rows.map((row, index) => `
    <div class="standing-row">
      <strong>${index + 1}. ${row.display_name}</strong>
      <span>Score ${row.final_score} (${row.penalty} malus)</span>
    </div>
  `).join("");
}


function leaderboard(session) {
  const rows = session.leaderboard || [];
  return `
    <div class="leaderboard">
      <span class="eyebrow">Leaderboard</span>
      ${rows.length ? rows.map((row, index) => `
        <div class="leaderboard-row">
          <strong>${index + 1}. ${row.display_name}</strong>
          <span>${row.score} pts</span>
        </div>
      `).join("") : `<p class="empty-state">Aucun score.</p>`}
    </div>
  `;
}


function modeLabel(mode) {
  return mode === "tour_europe" ? "Tour d'Europe" : "Classique";
}


function contractPanel(session) {
  const contracts = session.contracts || [];
  const active = contracts.filter((contract) => contract.status === "active");
  const claimed = contracts.filter((contract) => contract.status === "claimed");
  return `
    <div class="contract-panel">
      <span class="eyebrow">Evenement rare</span>
      ${active.length ? active.map((contract) => `
        <article class="contract-card">
          <strong>${contract.title}</strong>
          <p>${contract.description}</p>
          <div class="task-rewards">
            <span>${contract.target_city}, ${contract.target_country}</span>
            <span>+${contract.reward_coins} pieces</span>
            <span>+${contract.reward_victory_points} pts</span>
            <span>Expire manche ${contract.expires_round}</span>
          </div>
        </article>
      `).join("") : `<p class="empty-state">Aucun contrat public actif. Ils apparaissent rarement au debut d'une manche.</p>`}
      ${claimed.length ? `<div class="mini-history">${claimed.map((contract) => `<span>${contract.title}: ${contract.claimed_by_name || "reclame"}</span>`).join("")}</div>` : ""}
    </div>
  `;
}


function tourPanel(session) {
  if (session.game_mode !== "tour_europe") return "";
  const target = session.tour_country_target || 12;
  return `
    <div class="tour-panel">
      <span class="eyebrow">Tour d'Europe</span>
      ${session.players.map((player) => `
        <div class="tour-row ${player.user_id === session.current_turn_user_id ? "is-current-turn" : ""}">
          <strong>${player.display_name}</strong>
          <span>${player.visited_countries_count || 0}/${target} pays</span>
        </div>
      `).join("")}
    </div>
  `;
}


function interactionPanel(session, lockedTurns) {
  const canAct = session.is_my_turn && !lockedTurns;
  const others = session.players.filter((player) => player.user_id !== session.me?.user_id);
  if (!others.length) return "";
  return `
    <div class="interaction-panel">
      <span class="eyebrow">Interactions</span>
      ${others.map((player) => `
        <article class="interaction-row">
          <strong>${player.display_name}</strong>
          <div>
            <button class="ghost-button" data-player-interaction="gift_coins" data-target-user-id="${player.user_id}" ${canAct ? "" : "disabled"} type="button">+10 pieces</button>
            <button class="ghost-button" data-player-interaction="gift_fuel" data-target-user-id="${player.user_id}" ${canAct ? "" : "disabled"} type="button">+5L</button>
            <button class="ghost-button" data-player-interaction="twingo_challenge" data-target-user-id="${player.user_id}" ${canAct ? "" : "disabled"} type="button">Defi</button>
          </div>
        </article>
      `).join("")}
    </div>
  `;
}


function inviteUrl(code) {
  if (typeof window === "undefined") {
    return code;
  }
  const url = new URL(window.location.href);
  url.searchParams.set("join", code);
  return url.toString();
}


function sessionRow(session) {
  const isMember = Boolean(session.is_member);
  const visibility = session.visibility === "public" ? "Publique" : "Privee";
  const actionAttr = isMember ? `data-open-session="${session.code}"` : `data-public-session-join="${session.code}"`;
  const actionLabel = isMember ? "Ouvrir" : "Rejoindre";
  return `
    <button class="session-row" ${actionAttr} type="button">
      <strong>${session.name}</strong>
      <span>${session.code} - ${visibility} - ${modeLabel(session.game_mode)} - ${session.status} - ${actionLabel}</span>
    </button>
  `;
}


export function SessionPanel(sessions, currentSession, spawns = [], cityMissionsCollapsed = false) {
  if (!currentSession) {
    const inviteCode = typeof window !== "undefined"
      ? (new URLSearchParams(window.location.search).get("join") || "").replace(/[^a-z0-9]/gi, "").slice(0, 6).toUpperCase()
      : "";
    return `
      <section class="session-panel lobby-home-panel">
        <div class="lobby-home-hero">
          <div>
            <span class="eyebrow">EuroTwingo</span>
            <h2>Salon de depart</h2>
            <p>Creer une partie, rejoindre un code ou reprendre une session en attente.</p>
          </div>
          <img src="/assets/twingo-common.svg" alt="" />
        </div>
        <div class="lobby-home-actions">
          <form class="session-form lobby-card-form" data-session-create>
            <span class="eyebrow">Nouvelle partie</span>
            <input name="name" type="text" placeholder="Nom de partie" />
            <select name="visibility" aria-label="Visibilite de la partie">
              <option value="public">Publique</option>
              <option value="private" selected>Privee</option>
            </select>
            <select name="game_mode" aria-label="Mode de jeu">
              <option value="classic" selected>Classique</option>
              <option value="tour_europe">Tour d'Europe</option>
            </select>
            <button class="primary-button" type="submit">Creer</button>
          </form>
          <form class="session-form lobby-card-form" data-session-join>
            <span class="eyebrow">Invitation</span>
            <input name="code" type="text" maxlength="6" placeholder="Code de partie" value="${inviteCode}" />
            <button class="ghost-button" type="submit">Rejoindre</button>
          </form>
        </div>
        <div class="panel-heading compact">
          <div>
            <span class="eyebrow">Sessions</span>
            <h2>Parties disponibles</h2>
          </div>
        </div>
        <div class="session-list">
          ${sessions.length ? sessions.map(sessionRow).join("") : `<p class="empty-state">Creez une partie ou entrez un code.</p>`}
        </div>
      </section>
    `;
  }

  if (currentSession.status === "finished") {
    return `
      <section class="session-panel victory-panel">
        <div class="panel-heading">
          <div>
            <span class="eyebrow">Partie terminee</span>
            <h2>${currentSession.name}</h2>
          </div>
          <button class="icon-button" title="Quitter la partie" aria-label="Quitter la partie" data-action="leave-session" type="button">X</button>
        </div>
        <div class="victory-screen">
          <strong>Victoire</strong>
          <p>La course est close. Les malus ont ete deduits et le classement final est pret.</p>
          <div class="standings">${standings(currentSession)}</div>
        </div>
      </section>
    `;
  }

  if (currentSession.status === "lobby") {
    const isHost = currentSession.created_by_user_id === currentSession.me?.user_id;
    return `
      <section class="session-panel lobby-panel">
        <div class="lobby-room-hero">
          <div>
            <span class="eyebrow">Salon ${currentSession.code}</span>
            <h2>${currentSession.name}</h2>
            <p>${currentSession.players.length}/${currentSession.max_players} pilotes prets a partir. Mode ${modeLabel(currentSession.game_mode)}.</p>
          </div>
          <button class="icon-button" title="Quitter la partie" aria-label="Quitter la partie" data-action="leave-session" type="button">X</button>
        </div>
        <div class="lobby-room-grid">
          <div class="lobby-invite-card">
            <span class="eyebrow">Invitation</span>
            <strong>${currentSession.code}</strong>
            <input type="text" readonly value="${inviteUrl(currentSession.code)}" />
          </div>
          <form class="lobby-spawn-card" data-spawn-form>
            <span class="eyebrow">Capitale de depart</span>
            <select name="node_id">${spawnOptions(spawns, currentSession.me?.spawn_node_id)}</select>
            <button class="ghost-button" type="submit">Choisir</button>
          </form>
        </div>
        <div class="lobby-road-preview">
          <img src="/assets/twingo-common.svg" alt="" />
        </div>
        <div class="lobby-player-grid">
          ${currentSession.players.map((player) => playerMarkup(player, currentSession.me?.user_id)).join("")}
        </div>
        <div class="lobby-launch-row">
          <button class="primary-button" data-action="start-session" ${isHost ? "" : "disabled"} type="button">${isHost ? "Lancer la partie" : "En attente de l'hote"}</button>
        </div>
      </section>
    `;
  }

  const currentCity = currentSession.current_city_state;
  const tasks = currentCity?.tasks || [];
  const hasActiveMission = Boolean(currentSession.missions?.active?.length);
  const lockedTurns = currentSession.me?.mission_locked_turns || 0;
  return `
    <section class="session-panel">
      <div class="panel-heading">
        <div>
          <span class="eyebrow">Code ${currentSession.code}</span>
          <h2>${currentSession.name}</h2>
        </div>
        <button class="ghost-button" data-action="leave-session" type="button">Changer</button>
      </div>
      <div class="turn-box ${currentSession.is_my_turn ? "is-active" : ""}">
        <span>Tour ${currentSession.turn_number} - Manche ${currentSession.round_number}</span>
        <strong>${currentSession.is_my_turn && lockedTurns ? `Mission en cours: ${lockedTurns} tour restant` : `${currentSession.current_player?.display_name || "En attente"} ${currentSession.status === "closing" ? "- derniere manche" : ""}`}</strong>
        ${currentSession.me?.dice_remaining ? `<em>De ${currentSession.me.turn_roll}: ${currentSession.me.dice_remaining} case(s) restantes</em>` : ""}
      </div>
      <div class="player-strip">
        ${currentSession.players.map((player) => playerMarkup(player, currentSession.current_turn_user_id)).join("")}
      </div>
      ${leaderboard(currentSession)}
      ${tourPanel(currentSession)}
      ${contractPanel(currentSession)}
      ${interactionPanel(currentSession, lockedTurns)}
      <div class="city-feature">
        <span class="eyebrow">Ville actuelle</span>
        <strong>${currentCity?.feature_type || "tasks"}</strong>
      </div>
      <div class="task-list-heading">
        <strong>Missions de la ville</strong>
        ${tasks.length ? `<button class="mini-button" data-action="toggle-city-missions" type="button">${cityMissionsCollapsed ? "Afficher" : "Reduire"}</button>` : ""}
      </div>
      <div class="task-list ${cityMissionsCollapsed ? "is-collapsed" : ""}">
        ${cityMissionsCollapsed && tasks.length
          ? `<p class="node-tasks-summary">${tasks.length} mission${tasks.length > 1 ? "s" : ""} masquee${tasks.length > 1 ? "s" : ""}.</p>`
          : tasks.length ? tasks.map((task) => taskMarkup(task, currentSession.is_my_turn && !lockedTurns, hasActiveMission, currentSession.me?.user_id)).join("") : `<p class="empty-state">Aucune mission ici.</p>`}
      </div>
      <button class="primary-button" data-action="end-turn" ${currentSession.is_my_turn ? "" : "disabled"} type="button">Fin du tour</button>
    </section>
  `;
}
