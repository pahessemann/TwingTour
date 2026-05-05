import { AuthPanel } from "../components/AuthPanel.js";
import { CardDeck } from "../components/CardDeck.js";
import { CardPopup, CarpoolerPopup, StartingTrajetChoice } from "../components/CardPopup.js";
import { GaragePanel } from "../components/GaragePanel.js";
import { HUD } from "../components/HUD.js";
import { MapView } from "../components/MapView.js";
import { ProgressPanel } from "../components/ProgressPanel.js";
import { SessionPanel } from "../components/SessionPanel.js";
import { ToastStack, TurnNotice } from "../components/Toasts.js";
import { api, getToken, setToken } from "../services/api.js";
import { pushToast, setState, state, subscribe } from "../services/state.js";


const app = document.querySelector("#app");
let turnNoticeTimer = null;
let realtimeTimer = null;
let realtimeBusy = false;

const PRESERVED_SCROLL_SELECTORS = [
  ".side-stack",
  ".inventory-window",
  ".cards-grid",
  ".skins-list",
  ".compact-cards",
  ".lobby-content",
];


function captureScrollPositions() {
  return PRESERVED_SCROLL_SELECTORS.flatMap((selector) => (
    [...app.querySelectorAll(selector)].map((element, index) => ({
      selector,
      index,
      top: element.scrollTop,
      left: element.scrollLeft,
    }))
  ));
}


function restoreScrollPositions(positions) {
  for (const position of positions) {
    const element = app.querySelectorAll(position.selector)[position.index];
    if (!element) {
      continue;
    }
    element.scrollTop = position.top;
    element.scrollLeft = position.left;
  }
}


function renderApp(html) {
  const scrollPositions = captureScrollPositions();
  app.innerHTML = html;
  window.requestAnimationFrame(() => restoreScrollPositions(scrollPositions));
}


function showTurnNotice(previous, next) {
  if (turnNoticeTimer) {
    window.clearTimeout(turnNoticeTimer);
  }
  setState({ turnNotice: { previous, next } });
  turnNoticeTimer = window.setTimeout(() => {
    setState({ turnNotice: null });
    turnNoticeTimer = null;
  }, 3000);
}


function isTurnNoticeStatus(session) {
  return session && ["active", "closing"].includes(session.status);
}


function playerName(session, userId) {
  const player = session?.players?.find((item) => String(item.user_id) === String(userId));
  return player?.display_name || player?.email || "Joueur";
}


function firstMemberSession(sessions) {
  return sessions.find((session) => session.is_member) || null;
}


function activeProgression() {
  const player = state.currentSession?.me;
  if (!player) {
    return state.progression;
  }
  return {
    ...state.progression,
    current_node_id: player.current_node_id,
    visited_nodes: player.visited_nodes,
    fuel: player.fuel,
    fuel_capacity: 35,
    coins: player.coins,
    durability: player.durability,
    mission_locked_turns: player.mission_locked_turns,
    board_position: player.board_position,
    dice_remaining: player.dice_remaining,
    turn_roll: player.turn_roll,
    repairs_needed: player.repairs_needed,
    distance_km: player.distance_km,
    completed_trajets: player.completed_trajets,
    xp: player.xp,
  };
}


function render() {
  if (!state.user) {
    renderApp(AuthPanel(state.authMode) + ToastStack(state.toasts) + TurnNotice(state.turnNotice));
    return;
  }
  const playProgression = activeProgression();
  if (!state.currentSession) {
    renderApp(`
      ${LobbyShell(state)}
      ${ToastStack(state.toasts)}
      ${TurnNotice(state.turnNotice)}
      ${CardPopup(state.drawPopup)}
      ${CarpoolerPopup(state.carpoolerPopup, state.map)}
      ${StartingTrajetChoice(state.currentSession, state.startingChoiceSelection)}
    `);
    return;
  }
  const isPlaying = state.currentSession.status === "active" || state.currentSession.status === "closing";
  const isLobby = state.currentSession.status === "lobby";
  const canPlayTurn = state.currentSession.is_my_turn && !state.currentSession.me?.mission_locked_turns;
  if (isLobby) {
    renderApp(`
      ${LobbyShell(state)}
      ${ToastStack(state.toasts)}
      ${TurnNotice(state.turnNotice)}
      ${CardPopup(state.drawPopup)}
      ${CarpoolerPopup(state.carpoolerPopup, state.map)}
      ${StartingTrajetChoice(state.currentSession, state.startingChoiceSelection)}
    `);
    return;
  }
  renderApp(`
    ${isPlaying ? HUD(state.user, playProgression) : ""}
    <main class="game-layout ${!isPlaying ? "session-only" : ""} ${isLobby ? "lobby-layout" : ""}">
      ${isPlaying ? MapView(state.map, playProgression, state.skins, state.selectedNodeId, state.mapZoom, state.currentSession.city_states, canPlayTurn, state.mapPanX, state.mapPanY, state.currentSession, state.cityMissionsCollapsed) : SessionPanel(state.sessions, state.currentSession, state.spawns)}
      <aside class="side-stack">
        ${isPlaying ? SessionPanel(state.sessions, state.currentSession, state.spawns, state.cityMissionsCollapsed) : ""}
        ${isPlaying ? CardDeck(state.inventory, state.currentSession, state.inventoryTab, state.map) : ""}
      </aside>
    </main>
    ${ToastStack(state.toasts)}
    ${TurnNotice(state.turnNotice)}
    ${CardPopup(state.drawPopup)}
    ${CarpoolerPopup(state.carpoolerPopup, state.map)}
    ${StartingTrajetChoice(state.currentSession, state.startingChoiceSelection)}
  `);
}


subscribe(render);


function LobbyShell(appState) {
  const safeTab = ["lobby", "skins", "success"].includes(appState.lobbyTab) ? appState.lobbyTab : "lobby";
  return `
    <main class="lobby-shell">
      <nav class="lobby-tabs" aria-label="Navigation du salon">
        <button class="ghost-button ${safeTab === "lobby" ? "is-active" : ""}" data-lobby-tab="lobby" type="button">Lobby</button>
        <button class="ghost-button ${safeTab === "skins" ? "is-active" : ""}" data-lobby-tab="skins" type="button">Skins</button>
        <button class="ghost-button ${safeTab === "success" ? "is-active" : ""}" data-lobby-tab="success" type="button">Succes</button>
      </nav>
      <section class="lobby-content">
        ${safeTab === "lobby" ? SessionPanel(appState.sessions, appState.currentSession, appState.spawns) : ""}
        ${safeTab === "skins" ? GaragePanel(appState.skins, appState.lootboxes, appState.skinTab) : ""}
        ${safeTab === "success" ? ProgressPanel(appState.progression, appState.history) : ""}
      </section>
    </main>
  `;
}


async function bootstrap() {
  setState({ loading: true });
  try {
    const [map, catalog, spawnsPayload] = await Promise.all([api.map(), api.catalog(), api.spawns()]);
    setState({ map, catalog, spawns: spawnsPayload.spawns });
    if (getToken()) {
      const me = await api.me();
      const [historyPayload, sessionsPayload] = await Promise.all([api.history(), api.sessions()]);
      const currentSession = firstMemberSession(sessionsPayload.sessions);
      setState({
        user: me.user,
        progression: me.progression,
        inventory: me.inventory,
        skins: me.skins,
        lootboxes: me.lootboxes || 0,
        history: historyPayload.history,
        sessions: sessionsPayload.sessions,
        currentSession,
        selectedNodeId: currentSession?.me?.current_node_id || me.progression.current_node_id,
      });
      startRealtime();
    }
  } catch (error) {
    setToken(null);
    stopRealtime();
    pushToast({ title: "Session", body: error.message, severity: "warning" });
  } finally {
    setState({ loading: false });
  }
}


function startRealtime() {
  if (realtimeTimer) {
    return;
  }
  realtimeTimer = window.setInterval(async () => {
    if (!getToken() || realtimeBusy || state.loading) {
      return;
    }
    realtimeBusy = true;
    try {
      await refreshGame({ showTurnNotice: true });
    } catch (error) {
      // Le polling reste silencieux pour eviter de polluer l'interface en cas de micro-coupure.
    } finally {
      realtimeBusy = false;
    }
  }, 2400);
}


function stopRealtime() {
  if (!realtimeTimer) {
    return;
  }
  window.clearInterval(realtimeTimer);
  realtimeTimer = null;
  realtimeBusy = false;
}


async function refreshGame(options = {}) {
  const previousSession = state.currentSession;
  const [me, historyPayload, sessionsPayload, spawnsPayload] = await Promise.all([api.me(), api.history(), api.sessions(), api.spawns()]);
  const currentSession = previousSession
    ? sessionsPayload.sessions.find((session) => session.code === previousSession.code) || null
    : firstMemberSession(sessionsPayload.sessions);
  setState({
    user: me.user,
    progression: me.progression,
    inventory: me.inventory,
    skins: me.skins,
    lootboxes: me.lootboxes || 0,
    history: historyPayload.history,
    sessions: sessionsPayload.sessions,
    spawns: spawnsPayload.spawns,
    currentSession,
    selectedNodeId: (currentSession && state.selectedNodeId) || currentSession?.me?.current_node_id || me.progression.current_node_id,
  });
  if (
    options.showTurnNotice
    && previousSession
    && currentSession
    && previousSession.code === currentSession.code
    && isTurnNoticeStatus(previousSession)
    && isTurnNoticeStatus(currentSession)
    && previousSession.current_turn_user_id
    && currentSession.current_turn_user_id
    && String(previousSession.current_turn_user_id) !== String(currentSession.current_turn_user_id)
  ) {
    showTurnNotice(playerName(previousSession, previousSession.current_turn_user_id), playerName(currentSession, currentSession.current_turn_user_id));
  }
}


async function handleAuth(form) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  const action = form.dataset.authForm === "register" ? api.register : api.login;
  const result = await action(payload);
  setToken(result.token);
  const [map, historyPayload, sessionsPayload, spawnsPayload, me] = await Promise.all([api.map(), api.history(), api.sessions(), api.spawns(), api.me()]);
  const currentSession = firstMemberSession(sessionsPayload.sessions);
  setState({
    map,
    user: me.user,
    progression: me.progression,
    selectedNodeId: currentSession?.me?.current_node_id || me.progression.current_node_id,
    inventory: me.inventory,
    skins: me.skins,
    lootboxes: me.lootboxes || 0,
    sessions: sessionsPayload.sessions,
    spawns: spawnsPayload.spawns,
    currentSession,
    history: historyPayload.history,
  });
  startRealtime();
  pushToast({ title: "Garage ouvert", body: `Bienvenue ${result.user.display_name}.`, severity: "success" });
}


async function safeAction(task) {
  setState({ loading: true });
  try {
    await task();
  } catch (error) {
    const missing = error.details?.missing_city_ids;
    const suffix = missing ? ` Cases manquantes: ${missing.join(", ")}.` : "";
    pushToast({ title: "Action refusee", body: `${error.message}${suffix}`, severity: "warning" });
  } finally {
    setState({ loading: false });
  }
}


app.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-auth-form]");
  if (form) {
    event.preventDefault();
    safeAction(() => handleAuth(form));
    return;
  }
  const createSession = event.target.closest("[data-session-create]");
  if (createSession) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(createSession).entries());
    safeAction(async () => {
      const session = await api.createSession(payload);
      const sessionsPayload = await api.sessions();
      setState({ currentSession: session, sessions: sessionsPayload.sessions, selectedNodeId: session.me.current_node_id, lobbyTab: "lobby" });
      pushToast({ title: "Partie creee", body: `Code ${session.code}`, severity: "success" });
    });
    return;
  }
  const joinSession = event.target.closest("[data-session-join]");
  if (joinSession) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(joinSession).entries());
    safeAction(async () => {
      const session = await api.joinSession(payload.code);
      const sessionsPayload = await api.sessions();
      setState({ currentSession: session, sessions: sessionsPayload.sessions, selectedNodeId: session.me.current_node_id, lobbyTab: "lobby" });
      pushToast({ title: "Partie rejointe", body: `Code ${session.code}`, severity: "success" });
    });
    return;
  }
  const spawnForm = event.target.closest("[data-spawn-form]");
  if (spawnForm) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(spawnForm).entries());
    safeAction(async () => {
      const session = await api.selectSpawn(state.currentSession.code, payload.node_id);
      setState({ currentSession: session, selectedNodeId: session.me.current_node_id });
      pushToast({ title: "Spawn choisi", body: payload.node_id, severity: "success" });
    });
  }
});


app.addEventListener("click", (event) => {
  const authMode = event.target.closest("[data-auth-mode]");
  if (authMode) {
    setState({ authMode: authMode.dataset.authMode });
    return;
  }

  const node = event.target.closest("[data-node-id]");
  if (node) {
    setState({ selectedNodeId: node.dataset.nodeId, cityMissionsCollapsed: false });
    return;
  }

  const action = event.target.closest("[data-action]")?.dataset.action;
  const lobbyTab = event.target.closest("[data-lobby-tab]");
  if (lobbyTab) {
    setState({ lobbyTab: lobbyTab.dataset.lobbyTab });
    return;
  }
  const skinTab = event.target.closest("[data-skin-tab]");
  if (skinTab) {
    setState({ skinTab: skinTab.dataset.skinTab });
    return;
  }
  if (action === "close-session-or-logout") {
    if (state.currentSession) {
      safeAction(async () => {
        await api.leaveSession(state.currentSession.code);
        const sessionsPayload = await api.sessions();
        setState({ currentSession: null, sessions: sessionsPayload.sessions, lobbyTab: "lobby" });
      });
      return;
    }
    stopRealtime();
    setToken(null);
    setState({ user: null, progression: null, inventory: [], skins: [], lootboxes: 0, history: [], sessions: [], currentSession: null, lobbyTab: "lobby", skinTab: "owned" });
    return;
  }
  if (action === "leave-session") {
    safeAction(async () => {
      await api.leaveSession(state.currentSession.code);
      const sessionsPayload = await api.sessions();
      setState({ currentSession: null, sessions: sessionsPayload.sessions, lobbyTab: "lobby" });
    });
    return;
  }
  if (action === "start-session") {
    safeAction(async () => {
      const session = await api.startSession(state.currentSession.code);
      const me = await api.me();
      setState({
        currentSession: session,
        inventory: me.inventory,
        selectedNodeId: session.me.current_node_id,
        inventoryTab: "trajets",
        drawPopup: null,
        startingChoiceSelection: [],
      });
      pushToast({ title: "Partie lancee", body: "Choisissez 3 trajets de depart parmi les 5 cartes.", severity: "success" });
    });
    return;
  }
  if (action === "close-card-popup") {
    setState({ drawPopup: null });
    return;
  }
  if (action === "dismiss-carpooler") {
    setState({ carpoolerPopup: null });
    return;
  }
  if (action === "toggle-city-missions") {
    setState({ cityMissionsCollapsed: !state.cityMissionsCollapsed });
    return;
  }
  if (action === "end-turn") {
    safeAction(async () => {
      const previousPlayer = state.currentSession.current_player?.display_name || state.user?.display_name || "Joueur";
      const session = await api.endTurn(state.currentSession.code);
      setState({ currentSession: session });
      showTurnNotice(previousPlayer, session.current_player?.display_name || "joueur suivant");
    });
    return;
  }
  if (action === "roll-die") {
    safeAction(async () => {
      const result = await api.rollDie(state.currentSession.code);
      setState({ currentSession: result.session });
      pushToast({ title: "De lance", body: `${result.roll} case${result.roll > 1 ? "s" : ""} a parcourir.`, severity: "success" });
    });
    return;
  }
  if (action === "draw-cards") {
    safeAction(async () => {
      const result = await api.drawCards(1, state.currentSession?.code || null);
      setState({
        inventory: result.inventory,
        currentSession: result.session || state.currentSession,
        drawPopup: result.drawn[0] || null,
      });
    });
    return;
  }
  const inventoryTab = event.target.closest("[data-inventory-tab]");
  if (inventoryTab) {
    setState({ inventoryTab: inventoryTab.dataset.inventoryTab });
    return;
  }
  if (action === "draw-trajets") {
    safeAction(async () => {
      const result = await api.drawTrajets(state.currentSession.code);
      setState({
        inventory: result.inventory,
        currentSession: result.session,
        inventoryTab: "trajets",
        drawPopup: result.drawn[0] || null,
      });
      pushToast({ title: "Trajets pioches", body: "1 long et 2 courts maximum.", severity: "success" });
    });
    return;
  }
  const startChoiceCard = event.target.closest("[data-start-choice-card]");
  if (startChoiceCard) {
    const inventoryId = Number(startChoiceCard.dataset.startChoiceCard);
    const selected = new Set(state.startingChoiceSelection.map(Number));
    if (selected.has(inventoryId)) {
      selected.delete(inventoryId);
    } else if (selected.size < 3) {
      selected.add(inventoryId);
    } else {
      pushToast({ title: "Selection", body: "Vous ne pouvez choisir que 3 trajets.", severity: "warning" });
    }
    setState({ startingChoiceSelection: [...selected] });
    return;
  }
  if (action === "confirm-start-trajets") {
    safeAction(async () => {
      if (state.startingChoiceSelection.length !== 3) {
        pushToast({ title: "Selection", body: "Choisissez exactement 3 cartes.", severity: "warning" });
        return;
      }
      const result = await api.chooseStartingTrajets(state.currentSession.code, state.startingChoiceSelection);
      setState({
        currentSession: result.session,
        inventory: result.inventory,
        inventoryTab: "trajets",
        startingChoiceSelection: [],
      });
      pushToast({ title: "Trajets choisis", body: "Les 3 cartes sont dans l'inventaire.", severity: "success" });
    });
    return;
  }
  if (action === "zoom-in") {
    setState({ mapZoom: Math.min(2.2, state.mapZoom + 0.25) });
    return;
  }
  if (action === "zoom-out") {
    setState({ mapZoom: Math.max(0.75, state.mapZoom - 0.25) });
    return;
  }
  if (action === "zoom-reset") {
    setState({ mapZoom: 1.18, mapPanX: 0, mapPanY: 0 });
    return;
  }
  if (action === "pan-west") {
    setState({ mapPanX: state.mapPanX - 180 });
    return;
  }
  if (action === "pan-east") {
    setState({ mapPanX: state.mapPanX + 180 });
    return;
  }
  if (action === "pan-north") {
    setState({ mapPanY: state.mapPanY - 140 });
    return;
  }
  if (action === "pan-south") {
    setState({ mapPanY: state.mapPanY + 140 });
    return;
  }

  const move = event.target.closest("[data-move-to]");
  if (move) {
    safeAction(async () => {
      const result = await api.move(move.dataset.moveTo, state.currentSession?.code || null, move.dataset.routeId || null);
      const nextSession = result.session || state.currentSession;
      setState({
        progression: result.progression,
        currentSession: nextSession,
        selectedNodeId: nextSession?.me?.current_node_id || result.progression.current_node_id,
        mapPanX: 0,
        mapPanY: 0,
        inventory: result.drawn?.length ? [...result.drawn, ...state.inventory] : state.inventory,
        drawPopup: result.drawn?.[0] || state.drawPopup,
        carpoolerPopup: result.carpooler || null,
      });
      if (result.move.messages.length) {
        pushToast({ title: "Case", body: result.move.messages.join(" "), severity: "info" });
      }
      if (result.event && !["radar", "covoiture"].includes(result.event.slug)) {
        pushToast({ title: result.event.name, body: result.event.description, severity: result.event.type === "bonus" ? "success" : "warning" });
      }
    });
    return;
  }

  const complete = event.target.closest("[data-complete-card]");
  if (complete) {
    safeAction(async () => {
      const inventoryId = Number(complete.dataset.completeCard);
      const result = state.currentSession
        ? await api.completeSessionCard(state.currentSession.code, inventoryId)
        : await api.completeCard(inventoryId);
      setState({ progression: result.progression, inventory: result.inventory, currentSession: result.session || state.currentSession });
      await refreshGame();
      pushToast({ title: "Trajet complete", body: result.completed, severity: "success" });
    });
    return;
  }

  const apply = event.target.closest("[data-apply-card]");
  if (apply) {
    safeAction(async () => {
      const result = await api.applyCard(Number(apply.dataset.applyCard), state.currentSession?.code || null);
      setState({ progression: result.progression, inventory: result.inventory, currentSession: result.session || state.currentSession });
      pushToast({ title: "Carte jouee", body: result.applied, severity: "info" });
    });
    return;
  }

  const equip = event.target.closest("[data-equip-skin]");
  if (equip) {
    safeAction(async () => {
      const result = await api.equipSkin(equip.dataset.equipSkin);
      setState({ progression: result.progression, skins: result.skins, lootboxes: result.lootboxes ?? state.lootboxes });
      await refreshGame({ showTurnNotice: false });
      pushToast({ title: "Skin equipe", body: equip.dataset.equipSkin, severity: "success" });
    });
    return;
  }

  if (action === "open-lootbox") {
    safeAction(async () => {
      const result = await api.openLootbox();
      setState({ progression: result.progression, skins: result.skins, lootboxes: result.lootboxes, skinTab: "owned" });
      pushToast({ title: "Lootbox ouverte", body: `${result.skin.name} (${result.skin.rarity})`, severity: "success" });
    });
    return;
  }

  const fuse = event.target.closest("[data-fuse-skin]");
  if (fuse) {
    safeAction(async () => {
      const result = await api.fuseSkin(fuse.dataset.fuseSkin);
      setState({ progression: result.progression, skins: result.skins, lootboxes: result.lootboxes, skinTab: "owned" });
      pushToast({ title: "Fusion reussie", body: `${result.skin.name} obtenu.`, severity: "success" });
    });
    return;
  }

  const openSession = event.target.closest("[data-open-session]");
  if (openSession) {
    safeAction(async () => {
      const session = await api.getSession(openSession.dataset.openSession);
      setState({ currentSession: session, selectedNodeId: session.me.current_node_id, lobbyTab: "lobby" });
    });
    return;
  }

  const publicSession = event.target.closest("[data-public-session-join]");
  if (publicSession) {
    safeAction(async () => {
      const session = await api.joinSession(publicSession.dataset.publicSessionJoin);
      const sessionsPayload = await api.sessions();
      setState({ currentSession: session, sessions: sessionsPayload.sessions, selectedNodeId: session.me.current_node_id, lobbyTab: "lobby" });
      pushToast({ title: "Partie rejointe", body: `Code ${session.code}`, severity: "success" });
    });
    return;
  }

  const completeTask = event.target.closest("[data-complete-task]");
  if (completeTask) {
    safeAction(async () => {
      const result = await api.completeTask(state.currentSession.code, completeTask.dataset.completeTask);
      setState({ progression: result.progression, currentSession: result.session, inventoryTab: "missions" });
      pushToast({
        title: "Mission terminee",
        body: result.penalty ? `${result.task.title}. ${result.penalty}` : result.task.title,
        severity: result.penalty ? "warning" : "success",
      });
    });
    return;
  }

  const activateTask = event.target.closest("[data-activate-task]");
  if (activateTask) {
    safeAction(async () => {
      const result = await api.activateTask(state.currentSession.code, activateTask.dataset.activateTask);
      setState({ currentSession: result.session, inventoryTab: "missions" });
      pushToast({ title: "Mission activee", body: result.task.title, severity: "success" });
    });
    return;
  }

  const discard = event.target.closest("[data-discard-card]");
  if (discard) {
    safeAction(async () => {
      const result = await api.discardCard(Number(discard.dataset.discardCard), state.currentSession?.code || null);
      setState({ inventory: result.inventory, progression: result.progression || state.progression, currentSession: result.session || state.currentSession });
      pushToast({ title: "Trajet abandonne", body: `${result.discarded} pour ${result.cost} pieces.`, severity: "warning" });
    });
    return;
  }

  const acceptCarpooler = event.target.closest("[data-accept-carpooler]");
  if (acceptCarpooler) {
    safeAction(async () => {
      const session = await api.acceptCarpooler(state.currentSession.code, Number(acceptCarpooler.dataset.acceptCarpooler));
      setState({ currentSession: session, carpoolerPopup: null });
      pushToast({ title: "Covoitureur accepte", body: "Deposez-le pour gagner un gros bonus de score.", severity: "success" });
    });
    return;
  }

  const playerInteraction = event.target.closest("[data-player-interaction]");
  if (playerInteraction) {
    safeAction(async () => {
      const result = await api.playerInteraction(
        state.currentSession.code,
        Number(playerInteraction.dataset.targetUserId),
        playerInteraction.dataset.playerInteraction,
      );
      setState({ currentSession: result.session });
      pushToast({ title: "Interaction", body: result.summary, severity: "success" });
    });
    return;
  }

  const service = event.target.closest("[data-use-service]");
  if (service) {
    safeAction(async () => {
      const result = await api.useService(state.currentSession.code, service.dataset.useService);
      setState({ currentSession: result.session });
      pushToast({ title: "Service", body: result.summary, severity: "success" });
    });
  }
});


app.addEventListener("wheel", (event) => {
  if (!event.target.closest(".map-stage")) return;
  event.preventDefault();
  const delta = event.deltaY < 0 ? 0.12 : -0.12;
  setState({ mapZoom: Math.max(0.75, Math.min(3.2, state.mapZoom + delta)) });
}, { passive: false });


window.addEventListener("keydown", (event) => {
  if (!state.currentSession || !["active", "closing"].includes(state.currentSession.status)) return;
  const targetName = event.target?.tagName?.toLowerCase();
  if (["input", "select", "textarea", "button"].includes(targetName)) return;
  const key = event.key.toLowerCase();
  const moves = {
    arrowleft: { mapPanX: state.mapPanX - 180 },
    q: { mapPanX: state.mapPanX - 180 },
    arrowright: { mapPanX: state.mapPanX + 180 },
    d: { mapPanX: state.mapPanX + 180 },
    arrowup: { mapPanY: state.mapPanY - 140 },
    z: { mapPanY: state.mapPanY - 140 },
    arrowdown: { mapPanY: state.mapPanY + 140 },
    s: { mapPanY: state.mapPanY + 140 },
  };
  const patch = moves[key];
  if (!patch) return;
  event.preventDefault();
  setState(patch);
});


render();
bootstrap();
