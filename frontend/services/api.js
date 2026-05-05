const TOKEN_KEY = "eurotwingo_token";


export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}


export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}


async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(path, {
    ...options,
    headers,
  });
  const payload = await response.json().catch(() => ({ ok: false, error: "Reponse invalide." }));
  if (!response.ok || !payload.ok) {
    const error = new Error(payload.error || "Erreur EuroTwingo.");
    error.details = payload.details || {};
    throw error;
  }
  return payload.data;
}


export const api = {
  register(data) {
    return request("/api/auth/register", { method: "POST", body: JSON.stringify(data) });
  },
  login(data) {
    return request("/api/auth/login", { method: "POST", body: JSON.stringify(data) });
  },
  me() {
    return request("/api/me");
  },
  map() {
    return request("/api/map");
  },
  catalog() {
    return request("/api/catalog");
  },
  progression() {
    return request("/api/progression");
  },
  inventory() {
    return request("/api/inventory");
  },
  drawCards(count = 3, sessionCode = null) {
    return request("/api/cards/draw", { method: "POST", body: JSON.stringify({ count, session_code: sessionCode }) });
  },
  drawTrajets(sessionCode) {
    return request("/api/cards/draw-trajets", { method: "POST", body: JSON.stringify({ session_code: sessionCode }) });
  },
  move(toNodeId, sessionCode = null, routeId = null) {
    return request("/api/move", { method: "POST", body: JSON.stringify({ to_node_id: toNodeId, session_code: sessionCode, route_id: routeId }) });
  },
  completeCard(inventoryId) {
    return request("/api/cards/complete", { method: "POST", body: JSON.stringify({ inventory_id: inventoryId }) });
  },
  completeSessionCard(sessionCode, inventoryId) {
    return request("/api/cards/complete", { method: "POST", body: JSON.stringify({ session_code: sessionCode, inventory_id: inventoryId }) });
  },
  applyCard(inventoryId, sessionCode = null) {
    return request("/api/cards/apply", { method: "POST", body: JSON.stringify({ inventory_id: inventoryId, session_code: sessionCode }) });
  },
  discardCard(inventoryId, sessionCode = null) {
    return request("/api/cards/discard", { method: "POST", body: JSON.stringify({ inventory_id: inventoryId, session_code: sessionCode }) });
  },
  skins() {
    return request("/api/skins");
  },
  equipSkin(slug) {
    return request("/api/skins/equip", { method: "POST", body: JSON.stringify({ slug }) });
  },
  openLootbox() {
    return request("/api/skins/open-lootbox", { method: "POST", body: JSON.stringify({}) });
  },
  fuseSkin(slug) {
    return request("/api/skins/fuse", { method: "POST", body: JSON.stringify({ slug }) });
  },
  history() {
    return request("/api/history");
  },
  sessions() {
    return request("/api/sessions");
  },
  spawns() {
    return request("/api/sessions/spawns");
  },
  createSession(data) {
    return request("/api/sessions/create", { method: "POST", body: JSON.stringify(data) });
  },
  joinSession(code) {
    return request("/api/sessions/join", { method: "POST", body: JSON.stringify({ code }) });
  },
  getSession(code) {
    return request("/api/sessions/get", { method: "POST", body: JSON.stringify({ code }) });
  },
  selectSpawn(sessionCode, nodeId) {
    return request("/api/sessions/select-spawn", { method: "POST", body: JSON.stringify({ session_code: sessionCode, node_id: nodeId }) });
  },
  startSession(sessionCode) {
    return request("/api/sessions/start", { method: "POST", body: JSON.stringify({ session_code: sessionCode }) });
  },
  chooseStartingTrajets(sessionCode, inventoryIds) {
    return request("/api/sessions/choose-starting-trajets", { method: "POST", body: JSON.stringify({ session_code: sessionCode, inventory_ids: inventoryIds }) });
  },
  leaveSession(sessionCode) {
    return request("/api/sessions/leave", { method: "POST", body: JSON.stringify({ session_code: sessionCode }) });
  },
  endTurn(sessionCode) {
    return request("/api/sessions/end-turn", { method: "POST", body: JSON.stringify({ session_code: sessionCode }) });
  },
  rollDie(sessionCode) {
    return request("/api/sessions/roll-die", { method: "POST", body: JSON.stringify({ session_code: sessionCode }) });
  },
  completeTask(sessionCode, difficulty) {
    return request("/api/tasks/complete", { method: "POST", body: JSON.stringify({ session_code: sessionCode, difficulty }) });
  },
  activateTask(sessionCode, difficulty) {
    return request("/api/tasks/activate", { method: "POST", body: JSON.stringify({ session_code: sessionCode, difficulty }) });
  },
  useService(sessionCode, serviceType) {
    return request("/api/services/use", { method: "POST", body: JSON.stringify({ session_code: sessionCode, service_type: serviceType }) });
  },
  acceptCarpooler(sessionCode, carpoolerId) {
    return request("/api/carpoolers/accept", { method: "POST", body: JSON.stringify({ session_code: sessionCode, carpooler_id: carpoolerId }) });
  },
  playerInteraction(sessionCode, targetUserId, interactionType) {
    return request("/api/player-interactions/use", { method: "POST", body: JSON.stringify({ session_code: sessionCode, target_user_id: targetUserId, interaction_type: interactionType }) });
  },
};


export function connectEvents(onEvent) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/events`);
  socket.addEventListener("message", (event) => {
    try {
      onEvent(JSON.parse(event.data));
    } catch {
      onEvent({ title: "Signal", body: event.data, severity: "info" });
    }
  });
  return socket;
}
