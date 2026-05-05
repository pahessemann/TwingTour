const listeners = new Set();


export const state = {
  authMode: "login",
  user: null,
  progression: null,
  map: { nodes: [], roads: [] },
  catalog: { cards: [], skins: [] },
  inventory: [],
  skins: [],
  lootboxes: 0,
  history: [],
  sessions: [],
  currentSession: null,
  spawns: [],
  drawPopup: null,
  carpoolerPopup: null,
  startingChoiceSelection: [],
  turnNotice: null,
  selectedNodeId: null,
  toasts: [],
  loading: false,
  inventoryTab: "trajets",
  lobbyTab: "lobby",
  skinTab: "owned",
  cityMissionsCollapsed: false,
  mapZoom: 1.18,
  mapPanX: 0,
  mapPanY: 0,
};


export function setState(patch) {
  Object.assign(state, patch);
  listeners.forEach((listener) => listener(state));
}


export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}


export function cityName(nodeId) {
  const node = state.map.nodes.find((item) => item.id === nodeId);
  return node ? node.city : nodeId;
}


export function pushToast(toast) {
  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  setState({
    toasts: [
      { id, severity: "info", ...toast },
      ...state.toasts,
    ].slice(0, 4),
  });
  window.setTimeout(() => {
    setState({ toasts: state.toasts.filter((item) => item.id !== id) });
  }, 5200);
}
