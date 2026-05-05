import { EUROPE_COUNTRY_LABELS, EUROPE_COUNTRY_PATHS } from "../assets/europeCountries.js";

const NODE_TYPES = {
  card: "card",
  tasks: "task",
  bonus: "bonus",
  station: "fuel",
  garage: "garage",
  peage: "toll",
  event: "event",
  resource: "bonus",
  weather: "weather",
};

const ROAD_SPEED_LABEL = { autoroute: "faible conso, peage eleve", nationale: "conso et usure moyennes", departementale: "forte conso, forte usure" };
const ROAD_DURABILITY_COST = { autoroute: 3, nationale: 7, departementale: 13 };
const CASE_LABEL = { city: "Ville", bonus: "Bonus", malus: "Malus", event: "Evenement", bifurcation: "Bifurcation", empty: "Route" };
const FEATURE_LABELS = {
  card: "Bonus/Malus",
  tasks: "Missions",
  bonus: "Bonus",
  station: "Station",
  garage: "Garage",
  peage: "Peage",
  weather: "Meteo",
};


function showBoardCases(zoom) {
  return zoom >= 1.48;
}


function boardRoutePath(route, progression, zoom) {
  const currentRoute = progression.board_position?.route_id === route.id;
  const connectedToCurrent = route.from_node_id === progression.current_node_id || route.to_node_id === progression.current_node_id;
  const showCases = showBoardCases(zoom) && (currentRoute || connectedToCurrent);
  const width = (showCases ? Math.max(8, 13 / Math.max(1, zoom)) : Math.max(7, 10 / Math.max(0.9, zoom))).toFixed(2);
  const segments = [];
  for (let index = 0; index < route.cases.length - 1; index += 1) {
    const from = route.cases[index];
    const to = route.cases[index + 1];
    segments.push(`<line class="board-segment route-${route.road_type} ${currentRoute ? "is-current-route" : ""} ${showCases ? "is-case-backbone" : "is-overview-line"}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" style="stroke-width:${width}px" />`);
  }
  if (!showCases) {
    return segments.join("");
  }
  const tileHeight = {
    autoroute: 19,
    nationale: 18,
    departementale: 16,
  }[route.road_type] || 17;
  const marker = Math.max(3.5, 7 / Math.max(1, zoom));
  const cases = route.cases.slice(1, -1).map((item) => {
    const previous = route.cases[Math.max(0, item.index - 1)];
    const next = route.cases[Math.min(route.cases.length - 1, item.index + 1)];
    const prevDx = item.x - previous.x;
    const prevDy = item.y - previous.y;
    const nextDx = next.x - item.x;
    const nextDy = next.y - item.y;
    const prevDistance = Math.hypot(prevDx, prevDy);
    const nextDistance = Math.hypot(nextDx, nextDy);
    const dx = nextDistance >= prevDistance ? nextDx : prevDx;
    const dy = nextDistance >= prevDistance ? nextDy : prevDy;
    const angle = Math.atan2(dy, dx) * 180 / Math.PI;
    const tileWidth = Math.max(tileHeight * 1.15, Math.min(66, (prevDistance + nextDistance) / 2 + 4));
    const halfW = tileWidth / 2;
    const halfH = tileHeight / 2;
    return `
      <g class="board-tile ${currentRoute ? "is-current-route" : ""}">
        <rect class="board-case route-${route.road_type} case-${item.kind}" x="${(item.x - halfW).toFixed(2)}" y="${(item.y - halfH).toFixed(2)}" width="${tileWidth.toFixed(2)}" height="${tileHeight.toFixed(2)}" rx="2" transform="rotate(${angle.toFixed(2)} ${item.x} ${item.y})">
          <title>${CASE_LABEL[item.kind] || "Case"} - case ${item.index}/${route.case_count}</title>
        </rect>
        ${item.kind !== "empty" ? `<circle class="board-case-marker marker-${item.kind}" cx="${item.x}" cy="${item.y}" r="${marker.toFixed(2)}" />` : ""}
      </g>
    `;
  }).join("");
  return `${segments.join("")}${cases}`;
}


function octagonPoints(x, y, radius) {
  const points = [];
  for (let index = 0; index < 8; index += 1) {
    const angle = Math.PI / 8 + index * Math.PI / 4;
    points.push(`${(x + Math.cos(angle) * radius).toFixed(2)},${(y + Math.sin(angle) * radius).toFixed(2)}`);
  }
  return points.join(" ");
}


function nodeGlyph(node, progression, adjacentIds, cityStates, zoom) {
  const feature = cityStates[node.id]?.feature_type || node.node_type;
  const current = progression.current_node_id === node.id;
  const visited = progression.visited_nodes.includes(node.id);
  const reachable = adjacentIds.has(node.id);
  const priority = node.is_capital || current || reachable;
  const labelSize = ((priority ? 17 : 14) / Math.max(1, zoom * 0.92)).toFixed(2);
  const labelOffset = ((priority ? 38 : 33) / zoom).toFixed(2);
  const dotRadius = (priority ? 18 : 14) / Math.max(0.85, zoom * 0.9);
  const haloRadius = (reachable ? 34 : priority ? 29 : 23) / Math.max(0.85, zoom * 0.9);
  const iconSize = ((priority ? 18 : 15) / Math.max(0.9, zoom * 0.96)).toFixed(2);
  const iconOffset = (iconSize / 2).toFixed(2);
  const capitalSize = (20 / Math.max(1, zoom * 0.92)).toFixed(2);
  return `
    <g class="node ${priority ? "is-priority" : ""} ${node.is_capital ? "is-capital" : ""} ${current ? "is-current" : ""} ${visited ? "is-visited" : ""} ${reachable ? "is-reachable" : ""}" data-node-id="${node.id}" tabindex="0" role="button" aria-label="${node.city}">
      <polygon class="node-halo" points="${octagonPoints(node.x, node.y, haloRadius)}" />
      <polygon class="node-dot" points="${octagonPoints(node.x, node.y, dotRadius)}" />
      <use class="node-icon" href="#icon-${NODE_TYPES[feature] || "city"}" x="${node.x - iconOffset}" y="${node.y - iconOffset}" width="${iconSize}" height="${iconSize}"></use>
      ${node.is_capital ? `<use class="capital-icon" href="#icon-capital" x="${node.x + (12 / zoom)}" y="${node.y - (33 / zoom)}" width="${capitalSize}" height="${capitalSize}"></use>` : ""}
      <text class="node-label ${priority ? "is-priority-label" : ""}" x="${node.x}" y="${node.y + Number(labelOffset)}" style="font-size: ${labelSize}px">${node.city}</text>
    </g>
  `;
}


function tasksForNode(node, cityStates, canAct, isCurrent, session, collapsed) {
  const tasks = cityStates[node.id]?.tasks || [];
  if (!tasks.length) return "";
  const currentUserId = session?.me?.user_id;
  const hasActiveMission = Boolean(session?.missions?.active?.length);
  const hiddenCount = tasks.length;
  return `
    <div class="node-tasks ${collapsed ? "is-collapsed" : ""}">
      <div class="node-tasks-header">
        <strong>Missions disponibles</strong>
        <button class="mini-button" data-action="toggle-city-missions" type="button">${collapsed ? "Afficher" : "Reduire"}</button>
      </div>
      ${collapsed ? `
        <p class="node-tasks-summary">${hiddenCount} mission${hiddenCount > 1 ? "s" : ""} disponible${hiddenCount > 1 ? "s" : ""} dans cette ville.</p>
      ` : tasks.map((task) => {
        const activeByMe = String(task.active_by) === String(currentUserId);
        const activeByOther = task.active_by && !activeByMe;
        const enabled = canAct && isCurrent && !task.completed_by && !activeByOther && (!hasActiveMission || activeByMe);
        const status = task.completed_by ? "Finie" : activeByMe ? "Active" : activeByOther ? "Prise" : `${task.reward_coins} pieces / ${task.duration_turns || 1} tour`;
        return `
          <button class="task-row" data-activate-task="${task.difficulty}" ${enabled ? "" : "disabled"} type="button">
            <span>${task.title}</span>
            <em>${status}</em>
          </button>
        `;
      }).join("")}
    </div>
  `;
}


function nodeName(nodesById, nodeId) {
  return nodesById.get(nodeId)?.city || nodeId;
}


function routeDirection(route, currentNodeId, nodesById, canAct, diceRemaining) {
  const targetNodeId = route.from_node_id === currentNodeId ? route.to_node_id : route.from_node_id;
  return `
    <button class="direction-button route-${route.road_type}" data-move-to="${targetNodeId}" data-route-id="${route.id}" ${canAct && diceRemaining ? "" : "disabled"} type="button">
      <strong>${nodeName(nodesById, targetNodeId)}</strong>
      <span>${route.road_type} · ${route.case_count} cases · ${route.fuel_cost}L · ${route.cost_coins} pieces</span>
    </button>
  `;
}


function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}


function playerInitials(player) {
  const label = player.display_name || player.email || "Joueur";
  return escapeHtml(label.trim().slice(0, 2).toUpperCase() || "J");
}


function playerBoardPoint(player, nodesById, routes) {
  const board = player.board_position || { kind: "city", node_id: player.current_node_id };
  if (board.kind === "route") {
    if (Number.isFinite(Number(board.x)) && Number.isFinite(Number(board.y))) {
      return { x: Number(board.x), y: Number(board.y) };
    }
    const route = routes.find((item) => item.id === board.route_id);
    const routeCase = route?.cases?.find((item) => Number(item.index) === Number(board.index));
    if (routeCase) {
      return { x: routeCase.x, y: routeCase.y };
    }
  }
  const node = nodesById.get(board.node_id || player.current_node_id);
  return node ? { x: node.x, y: node.y } : null;
}


function playerMarkers(session, skins, nodesById, routes) {
  const players = session?.players || [];
  if (!players.length) return "";
  const placed = new Map();
  const markers = players.map((player) => {
    const point = playerBoardPoint(player, nodesById, routes);
    if (!point) return "";
    const key = `${Math.round(point.x)}:${Math.round(point.y)}`;
    const index = placed.get(key) || 0;
    placed.set(key, index + 1);
    const radius = index ? 28 : 0;
    const angle = (index % 6) * Math.PI / 3;
    const offsetX = Math.round(Math.cos(angle) * radius);
    const offsetY = Math.round(Math.sin(angle) * radius);
    const skin = skins.find((item) => item.slug === player.equipped_skin_slug) || skins.find((item) => item.unlocked) || skins[0];
    const name = escapeHtml(player.display_name || player.email || "Joueur");
    const markerClasses = [
      "player-marker",
      player.user_id === session.me?.user_id ? "is-me" : "",
      player.user_id === session.current_turn_user_id ? "is-current-turn" : "",
    ].filter(Boolean).join(" ");
    return `
      <g class="${markerClasses}" transform="translate(${point.x + offsetX} ${point.y + offsetY})">
        <title>${name}</title>
        <circle class="player-marker-backdrop" cx="0" cy="-28" r="22"></circle>
        ${skin?.asset ? `<image href="${skin.asset}" x="-30" y="-52" width="60" height="42" filter="url(#soft-shadow)" />` : ""}
        <text class="player-marker-label" x="0" y="-58">${playerInitials(player)}</text>
      </g>
    `;
  }).join("");
  return `<g class="player-markers">${markers}</g>`;
}


function dicePanel(map, progression, nodesById, canAct, session) {
  const board = progression.board_position || { kind: "city", node_id: progression.current_node_id };
  const locked = session?.me?.mission_locked_turns || 0;
  const canRoll = session?.is_my_turn && !locked && !progression.dice_remaining;
  const canStay = session?.is_my_turn && !locked && board.kind === "city" && progression.dice_remaining > 0;
  let directions = [];
  if (board.kind === "city") {
    directions = (map.board_routes || [])
      .filter((route) => route.from_node_id === progression.current_node_id || route.to_node_id === progression.current_node_id)
      .map((route) => routeDirection(route, progression.current_node_id, nodesById, canAct, progression.dice_remaining));
  } else {
    const route = (map.board_routes || []).find((item) => item.id === board.route_id);
    if (route) {
      const oppositeNodeId = board.target_node_id === route.to_node_id ? route.from_node_id : route.to_node_id;
      const continueRemaining = Math.abs((board.target_node_id === route.to_node_id ? route.case_count : 0) - board.index);
      const returnRemaining = Math.abs((oppositeNodeId === route.to_node_id ? route.case_count : 0) - board.index);
      directions = [
        `
        <button class="direction-button route-${route.road_type}" data-move-to="${board.target_node_id}" data-route-id="${route.id}" ${canAct && progression.dice_remaining ? "" : "disabled"} type="button">
          <strong>Continuer vers ${nodeName(nodesById, board.target_node_id)}</strong>
          <span>${continueRemaining} cases restantes</span>
        </button>
      `,
        `
        <button class="direction-button route-${route.road_type}" data-move-to="${oppositeNodeId}" data-route-id="${route.id}" ${canAct && progression.dice_remaining ? "" : "disabled"} type="button">
          <strong>Faire demi-tour vers ${nodeName(nodesById, oppositeNodeId)}</strong>
          <span>${returnRemaining} cases restantes</span>
        </button>
      `,
      ];
    }
  }
  return `
    <aside class="dice-panel">
      <div class="dice-readout">
        <span>De</span>
        <strong>${progression.dice_remaining ? progression.turn_roll : "-"}</strong>
        <em>${progression.dice_remaining ? `${progression.dice_remaining} case(s) restantes` : "a lancer"}</em>
      </div>
      <button class="primary-button" data-action="roll-die" ${canRoll ? "" : "disabled"} type="button">Lancer le de</button>
      ${canStay ? `<button class="ghost-button" data-action="end-turn" type="button">Rester dans cette ville</button>` : ""}
      <div class="direction-list">
        ${directions.length ? directions.join("") : `<p class="empty-state">Aucune direction disponible.</p>`}
      </div>
    </aside>
  `;
}


function mapLeaderboard(session) {
  const rows = session?.leaderboard || [];
  return `
    <aside class="map-leaderboard">
      <span class="eyebrow">Leaderboard</span>
      <div class="map-leaderboard-list">
        ${rows.length ? rows.slice(0, 5).map((row, index) => `
          <div class="map-leaderboard-row ${String(row.user_id) === String(session?.current_turn_user_id) ? "is-current-turn" : ""}">
            <strong>${index + 1}. ${row.display_name}</strong>
            <span>${row.score} pts${String(row.user_id) === String(session?.current_turn_user_id) ? " · tour" : ""}</span>
          </div>
        `).join("") : `<span class="empty-inline">Aucun score</span>`}
      </div>
    </aside>
  `;
}


function selectedPanel(node, roads, boardRoutes, progression, cityStates, canAct, session, missionsCollapsed) {
  if (!node) {
    return "";
  }
  const feature = cityStates[node.id]?.feature_type || node.node_type;
  const payload = cityStates[node.id]?.feature_payload || {};
  const featureLabel = node.is_capital ? "Capitale - Missions" : (FEATURE_LABELS[feature] || feature);
  const neighbors = roads
    .filter((road) => road.from_node_id === progression.current_node_id || road.to_node_id === progression.current_node_id)
    .map((road) => {
      const target = road.from_node_id === progression.current_node_id ? road.to_node_id : road.from_node_id;
      return { ...road, target };
    })
    .filter((road) => road.target === node.id);
  const road = neighbors[0];
  const isCurrent = progression.current_node_id === node.id;
  const stationAvailable = isCurrent && (feature === "station" || node.is_capital);
  const garageAvailable = isCurrent && (feature === "garage" || node.is_capital);
  const fuelPrice = payload.fuel_price || 38;
  const repairPrice = payload.repair_price || 26;
  return `
    <aside class="node-panel">
      <div>
        <span class="eyebrow">${node.country}</span>
        <h2>${node.city}</h2>
      </div>
      <dl>
        <div><dt>Case</dt><dd>${featureLabel}</dd></div>
        <div><dt>Meteo</dt><dd>${node.weather}</dd></div>
        ${road ? `<div><dt>Route</dt><dd>${road.road_type}</dd></div>` : ""}
        ${road ? `<div><dt>Cout</dt><dd>${road.cost_coins} pieces / ${road.fuel_cost} carburant</dd></div>` : ""}
        ${road ? `<div><dt>Usure</dt><dd>${ROAD_DURABILITY_COST[road.road_type] || 10} durabilite</dd></div>` : ""}
        ${road ? `<div><dt>Profil</dt><dd>${ROAD_SPEED_LABEL[road.road_type] || "route lente"}</dd></div>` : ""}
      </dl>
      ${stationAvailable || garageAvailable ? `
        <div class="service-actions">
          ${stationAvailable ? `<button class="ghost-button" data-use-service="station" ${canAct ? "" : "disabled"} type="button">Plein (${fuelPrice})</button>` : ""}
          ${garageAvailable ? `<button class="ghost-button" data-use-service="garage" ${canAct ? "" : "disabled"} type="button">Reparer (${repairPrice})</button>` : ""}
        </div>
      ` : ""}
      ${tasksForNode(node, cityStates, canAct, isCurrent, session, missionsCollapsed)}
    </aside>
  `;
}


const LANDSCAPE_SPRITES = [
  // Pyrenees and Iberia
  ["mountain", 205, 632, 1.05], ["mountain", 252, 612, 1.18], ["snow-mountain", 302, 620, 1.05],
  ["field", 174, 708, 1.2], ["field", 270, 742, 1.1], ["oak", 335, 690, .95],
  // Alps and northern Italy
  ["snow-mountain", 486, 604, 1.28], ["mountain", 532, 578, 1.42], ["snow-mountain", 580, 590, 1.34],
  ["mountain", 634, 606, 1.22], ["snow-mountain", 690, 622, 1.08], ["pine", 548, 660, 1.05],
  ["field", 622, 696, 1], ["field", 672, 744, .92], ["mountain", 684, 790, .86],
  // Carpathians, Balkans and Greece
  ["mountain", 742, 640, 1.02], ["pine", 792, 628, 1], ["mountain", 850, 666, 1.1],
  ["pine", 908, 690, .98], ["field", 808, 742, 1.05], ["field", 892, 780, .96],
  // France, Benelux and Germany
  ["field", 300, 546, 1.05], ["oak", 364, 522, .96], ["field", 430, 520, 1.1],
  ["oak", 530, 486, 1.05], ["field", 620, 506, 1.08], ["oak", 724, 500, 1],
  ["field", 832, 516, 1.05], ["pine", 870, 454, .98],
  // British Isles
  ["oak", 276, 344, .95], ["field", 330, 376, .92], ["oak", 388, 304, .88], ["field", 416, 350, .9],
  // Scandinavia
  ["snow-mountain", 694, 160, 1.3], ["snow-mountain", 770, 112, 1.45], ["snow-mountain", 852, 132, 1.32],
  ["snow-pine", 684, 242, 1.05], ["pine", 742, 230, 1.08], ["snow-pine", 820, 250, 1.08],
  ["pine", 912, 210, .98], ["snow-pine", 962, 154, .92],
  // Baltic and central plains
  ["pine", 922, 350, 1.05], ["field", 980, 450, 1.05], ["oak", 1038, 410, 1.02],
  ["field", 1088, 510, 1.12], ["field", 1178, 540, 1.04],
  // Russia, taiga and steppe
  ["pine", 1110, 354, 1.12], ["pine", 1210, 370, 1.15], ["snow-pine", 1320, 386, 1.08],
  ["pine", 1426, 438, 1.12], ["snow-pine", 1540, 474, 1.02],
  ["steppe", 1040, 586, 1.1], ["steppe", 1146, 614, 1.18], ["steppe", 1276, 604, 1.12],
  ["steppe", 1398, 638, 1.15], ["steppe", 1530, 604, 1.08],
  // Mediterranean and Black Sea arc
  ["field", 742, 706, .9], ["oak", 934, 724, .92], ["steppe", 1052, 700, .95], ["field", 1182, 686, .9],
];


function landscapeSprites() {
  return LANDSCAPE_SPRITES.map(([type, x, y, scale], index) => {
    const size = {
      "snow-mountain": 48,
      mountain: 46,
      "snow-pine": 34,
      pine: 32,
      oak: 30,
      field: 42,
      steppe: 42,
    }[type] || 32;
    return `<use class="landscape-sprite landscape-${type}" href="#sprite-${type}" x="${x}" y="${y}" width="${Math.round(size * scale)}" height="${Math.round(size * scale)}" data-landscape-index="${index}"></use>`;
  }).join("");
}


function pixelCoastHighlights() {
  return `
    <g class="coast-pixels">
      <rect class="coast-sand" x="112" y="676" width="20" height="20"></rect>
      <rect class="coast-sand" x="126" y="738" width="42" height="10"></rect>
      <rect class="coast-sand" x="214" y="772" width="58" height="10"></rect>
      <rect class="coast-sand" x="320" y="812" width="40" height="12"></rect>
      <rect class="coast-sand" x="344" y="612" width="46" height="10"></rect>
      <rect class="coast-sand" x="472" y="684" width="72" height="10"></rect>
      <rect class="coast-sand" x="604" y="684" width="46" height="10"></rect>
      <rect class="coast-sand" x="672" y="824" width="38" height="10"></rect>
      <rect class="coast-sand" x="706" y="890" width="36" height="10"></rect>
      <rect class="coast-sand" x="738" y="318" width="70" height="10"></rect>
      <rect class="coast-sand" x="910" y="286" width="58" height="10"></rect>
      <rect class="coast-sand" x="934" y="666" width="92" height="10"></rect>
      <rect class="coast-sand" x="1138" y="708" width="74" height="10"></rect>
      <rect class="coast-sand" x="1506" y="650" width="60" height="10"></rect>
      <rect class="coast-foam" x="96" y="710" width="34" height="8"></rect>
      <rect class="coast-foam" x="188" y="848" width="54" height="8"></rect>
      <rect class="coast-foam" x="244" y="574" width="48" height="8"></rect>
      <rect class="coast-foam" x="332" y="408" width="58" height="8"></rect>
      <rect class="coast-foam" x="418" y="214" width="30" height="8"></rect>
      <rect class="coast-foam" x="646" y="296" width="62" height="8"></rect>
      <rect class="coast-foam" x="770" y="64" width="70" height="8"></rect>
      <rect class="coast-foam" x="942" y="112" width="52" height="8"></rect>
      <rect class="coast-foam" x="872" y="918" width="42" height="8"></rect>
      <rect class="coast-foam" x="1010" y="842" width="90" height="8"></rect>
      <rect class="coast-foam" x="1242" y="610" width="96" height="8"></rect>
      <rect class="coast-foam" x="1572" y="520" width="54" height="8"></rect>
    </g>
  `;
}


function countryPaths(layerClass, includeTitle = false) {
  return EUROPE_COUNTRY_PATHS.flatMap((country) => (
    country.paths.map((path, index) => (
      `<path class="${layerClass} country-${country.id} biome-${country.biome}" d="${path}">${includeTitle ? `<title>${country.name}</title>` : ""}</path>`
    ))
  )).join("");
}


function countryLandmass() {
  const waterEdges = countryPaths("country-shoreline shore-water");
  const sandEdges = countryPaths("country-shoreline shore-sand");
  const lands = countryPaths("country-land", true);
  return `${waterEdges}${sandEdges}${lands}`;
}


function countryLabels() {
  return `
    <g class="country-labels">
      ${EUROPE_COUNTRY_LABELS.map(([label, x, y, size]) => (
        `<text class="country-name ${size === "large" ? "country-name-large" : ""}" x="${x}" y="${y}">${label}</text>`
      )).join("")}
    </g>
  `;
}


export function MapView(map, progression, skins, selectedNodeId, zoom, cityStates = {}, canAct = true, panX = 0, panY = 0, session = null, missionsCollapsed = false) {
  const nodesById = new Map(map.nodes.map((node) => [node.id, node]));
  const current = nodesById.get(progression.current_node_id);
  const boardPosition = progression.board_position || { kind: "city", node_id: progression.current_node_id };
  const focusPoint = boardPosition.kind === "route" ? boardPosition : current;
  const selected = nodesById.get(selectedNodeId) || current;
  const adjacentIds = new Set();
  if (boardPosition.kind === "city") {
    for (const road of map.roads) {
      if (road.from_node_id === progression.current_node_id) adjacentIds.add(road.to_node_id);
      if (road.to_node_id === progression.current_node_id) adjacentIds.add(road.from_node_id);
    }
  }
  const mapWidth = map.width || 980;
  const mapHeight = map.height || 980;
  const viewWidth = Math.min(mapWidth, Math.round(mapWidth / zoom));
  const viewHeight = Math.min(mapHeight, Math.round(mapHeight / zoom));
  const maxViewX = Math.max(0, mapWidth - viewWidth);
  const maxViewY = Math.max(0, mapHeight - viewHeight);
  const viewX = focusPoint ? Math.max(0, Math.min(maxViewX, focusPoint.x + panX - viewWidth / 2)) : 0;
  const viewY = focusPoint ? Math.max(0, Math.min(maxViewY, focusPoint.y + panY - viewHeight / 2)) : 0;
  const zoomBand = zoom < 1.15 ? "zoom-wide" : zoom < 1.85 ? "zoom-mid" : "zoom-close";
  const terrainTransform = `translate(${map.terrain_offset_x || 0} ${map.terrain_offset_y || 0}) scale(${map.terrain_scale_x || 1} ${map.terrain_scale_y || 1})`;

  return `
    <section class="map-workbench">
      <div class="map-toolbar">
        <div class="legend">
          <span><i class="legend-road autoroute"></i>Autoroute</span>
          <span><i class="legend-road nationale"></i>Nationale</span>
          <span><i class="legend-road departementale"></i>Departementale</span>
        </div>
        <div class="toolbar-buttons">
          <button class="icon-button" title="Zoom arriere" aria-label="Zoom arriere" data-action="zoom-out" type="button">-</button>
          <button class="icon-button" title="Centrer" aria-label="Centrer" data-action="zoom-reset" type="button">O</button>
          <button class="icon-button" title="Zoom avant" aria-label="Zoom avant" data-action="zoom-in" type="button">+</button>
          <button class="icon-button" title="Ouest" aria-label="Ouest" data-action="pan-west" type="button">&lt;</button>
          <button class="icon-button" title="Nord" aria-label="Nord" data-action="pan-north" type="button">^</button>
          <button class="icon-button" title="Sud" aria-label="Sud" data-action="pan-south" type="button">v</button>
          <button class="icon-button" title="Est" aria-label="Est" data-action="pan-east" type="button">&gt;</button>
        </div>
      </div>
      <div class="map-stage">
        <svg class="europe-map ${zoomBand}" viewBox="${viewX} ${viewY} ${viewWidth} ${viewHeight}" role="img" aria-label="Carte EuroTwingo">
          <defs>
            <filter id="soft-shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#152436" flood-opacity=".18" />
            </filter>
            <pattern id="sea-pixel" width="64" height="64" patternUnits="userSpaceOnUse">
              <rect width="64" height="64" fill="#4f9fbd" />
              <rect x="0" y="0" width="16" height="16" fill="#76c2d7" opacity=".92" />
              <rect x="16" y="16" width="16" height="16" fill="#66b7d0" opacity=".74" />
              <rect x="32" y="32" width="16" height="16" fill="#3f88ad" opacity=".66" />
              <rect x="48" y="48" width="16" height="16" fill="#317da6" opacity=".55" />
              <rect x="48" y="8" width="16" height="16" fill="#a7dcea" opacity=".55" />
            </pattern>
            <pattern id="sea-lines" width="96" height="96" patternUnits="userSpaceOnUse">
              <rect x="8" y="18" width="18" height="6" fill="rgba(255,255,255,.18)" />
              <rect x="28" y="18" width="30" height="6" fill="rgba(255,255,255,.11)" />
              <rect x="46" y="50" width="22" height="6" fill="rgba(255,255,255,.14)" />
              <rect x="18" y="78" width="42" height="6" fill="rgba(255,255,255,.12)" />
            </pattern>
            <pattern id="sand-pixel" width="32" height="32" patternUnits="userSpaceOnUse">
              <rect width="32" height="32" fill="#e6c86d" />
              <rect x="0" y="0" width="16" height="16" fill="#f2da86" />
              <rect x="16" y="16" width="16" height="16" fill="#cda956" opacity=".9" />
              <rect x="24" y="0" width="8" height="8" fill="#fff0a8" opacity=".75" />
            </pattern>
            <pattern id="land-pixel" width="56" height="56" patternUnits="userSpaceOnUse">
              <rect width="56" height="56" fill="#7fb35a" />
              <rect x="0" y="0" width="14" height="14" fill="#a7cb67" />
              <rect x="14" y="14" width="14" height="14" fill="#95bf5f" />
              <rect x="28" y="28" width="14" height="14" fill="#639b52" />
              <rect x="42" y="42" width="14" height="14" fill="#5b8d49" />
              <rect x="42" y="0" width="14" height="14" fill="#c7ca75" opacity=".85" />
              <rect x="0" y="42" width="14" height="14" fill="#4f7d43" opacity=".72" />
            </pattern>
            <pattern id="forest-pixel" width="42" height="42" patternUnits="userSpaceOnUse">
              <rect width="42" height="42" fill="#347643" />
              <rect x="0" y="0" width="14" height="14" fill="#285f38" />
              <rect x="14" y="14" width="14" height="14" fill="#468a48" />
              <rect x="28" y="28" width="14" height="14" fill="#6ca65b" opacity=".86" />
            </pattern>
            <pattern id="steppe-pixel" width="42" height="42" patternUnits="userSpaceOnUse">
              <rect width="42" height="42" fill="#b9a85c" />
              <rect x="0" y="0" width="14" height="14" fill="#d2c46f" />
              <rect x="14" y="14" width="14" height="14" fill="#c2b163" />
              <rect x="28" y="28" width="14" height="14" fill="#9c8c4d" opacity=".78" />
            </pattern>
            <pattern id="snow-pixel" width="42" height="42" patternUnits="userSpaceOnUse">
              <rect width="42" height="42" fill="#dbecef" />
              <rect x="0" y="0" width="14" height="14" fill="#ffffff" />
              <rect x="14" y="14" width="14" height="14" fill="#e9f6f7" />
              <rect x="28" y="28" width="14" height="14" fill="#bdd8de" opacity=".82" />
            </pattern>
            <pattern id="water-pixel" width="42" height="42" patternUnits="userSpaceOnUse">
              <rect width="42" height="42" fill="#4f9fbd" />
              <rect x="0" y="0" width="14" height="14" fill="#7ac7d9" opacity=".75" />
              <rect x="14" y="14" width="14" height="14" fill="#68b8ce" opacity=".68" />
              <rect x="28" y="28" width="14" height="14" fill="#347fa6" opacity=".72" />
            </pattern>
            <symbol id="sprite-mountain" viewBox="0 0 46 46">
              <rect class="sprite-shadow" x="8" y="34" width="30" height="6" />
              <rect class="sprite-rock-dark" x="14" y="26" width="22" height="8" />
              <rect class="sprite-rock" x="18" y="18" width="16" height="8" />
              <rect class="sprite-rock-light" x="22" y="10" width="8" height="8" />
              <rect class="sprite-snow" x="22" y="10" width="8" height="4" />
            </symbol>
            <symbol id="sprite-snow-mountain" viewBox="0 0 48 48">
              <rect class="sprite-shadow" x="8" y="36" width="32" height="6" />
              <rect class="sprite-rock-dark" x="12" y="28" width="28" height="8" />
              <rect class="sprite-rock" x="16" y="20" width="20" height="8" />
              <rect class="sprite-snow" x="20" y="12" width="12" height="8" />
              <rect class="sprite-snow-bright" x="24" y="8" width="6" height="4" />
            </symbol>
            <symbol id="sprite-pine" viewBox="0 0 32 36">
              <rect class="sprite-trunk" x="14" y="24" width="5" height="8" />
              <rect class="sprite-pine-dark" x="8" y="18" width="18" height="8" />
              <rect class="sprite-pine" x="10" y="10" width="14" height="8" />
              <rect class="sprite-pine-light" x="13" y="4" width="8" height="8" />
            </symbol>
            <symbol id="sprite-snow-pine" viewBox="0 0 34 38">
              <rect class="sprite-trunk" x="15" y="26" width="5" height="8" />
              <rect class="sprite-pine-dark" x="8" y="20" width="20" height="8" />
              <rect class="sprite-snow" x="10" y="18" width="16" height="4" />
              <rect class="sprite-pine" x="11" y="12" width="15" height="8" />
              <rect class="sprite-snow-bright" x="13" y="10" width="11" height="4" />
              <rect class="sprite-pine-light" x="14" y="5" width="8" height="7" />
            </symbol>
            <symbol id="sprite-oak" viewBox="0 0 30 32">
              <rect class="sprite-trunk" x="13" y="20" width="5" height="8" />
              <rect class="sprite-oak-dark" x="7" y="12" width="18" height="10" />
              <rect class="sprite-oak" x="10" y="6" width="14" height="10" />
              <rect class="sprite-oak-light" x="15" y="3" width="8" height="7" />
            </symbol>
            <symbol id="sprite-field" viewBox="0 0 42 30">
              <rect class="sprite-field-base" x="2" y="4" width="36" height="22" />
              <rect class="sprite-field-light" x="6" y="8" width="28" height="4" />
              <rect class="sprite-field-dark" x="6" y="16" width="28" height="4" />
              <rect class="sprite-field-edge" x="2" y="4" width="4" height="22" />
              <rect class="sprite-field-edge" x="34" y="4" width="4" height="22" />
            </symbol>
            <symbol id="sprite-steppe" viewBox="0 0 42 28">
              <rect class="sprite-steppe-base" x="2" y="8" width="36" height="14" />
              <rect class="sprite-steppe-light" x="6" y="6" width="10" height="4" />
              <rect class="sprite-steppe-dark" x="18" y="18" width="18" height="4" />
              <rect class="sprite-steppe-light" x="25" y="10" width="10" height="4" />
            </symbol>
            <symbol id="icon-fuel" viewBox="0 0 24 24"><path d="M6 3h8v18H5V4c0-.6.4-1 1-1Zm2 4h4V5H8v2Zm7 1 3 3v8c0 1.3 2 1.3 2 0v-5h-2v-3l-3-3Z"/></symbol>
            <symbol id="icon-garage" viewBox="0 0 24 24"><path d="M3 10 12 3l9 7v11h-4v-7H7v7H3V10Zm6 11v-5h6v5H9Z"/></symbol>
            <symbol id="icon-task" viewBox="0 0 24 24"><path d="M6 3h12v18H6V3Zm3 4h6v2H9V7Zm0 4h6v2H9v-2Zm0 4h4v2H9v-2Z"/></symbol>
            <symbol id="icon-card" viewBox="0 0 24 24"><path d="M6 4 18 2l3 16-12 2L6 4Zm-3 4h3l2 12h10v2H3V8Z"/></symbol>
            <symbol id="icon-toll" viewBox="0 0 24 24"><path d="M4 5h16v4H4V5Zm2 6h12v8H6v-8Zm2 2v4h2v-4H8Zm4 0v4h2v-4h-2Z"/></symbol>
            <symbol id="icon-weather" viewBox="0 0 24 24"><path d="M8 18h10a4 4 0 0 0 0-8 6 6 0 0 0-11-2 5 5 0 0 0 1 10Zm1 3h2v-2H9v2Zm4 0h2v-2h-2v2Z"/></symbol>
            <symbol id="icon-bonus" viewBox="0 0 24 24"><path d="M12 2 9 9H2l6 4-3 8 7-5 7 5-3-8 6-4h-7l-3-7Z"/></symbol>
            <symbol id="icon-event" viewBox="0 0 24 24"><path d="M11 2h2v12h-2V2Zm1 20a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z"/></symbol>
            <symbol id="icon-city" viewBox="0 0 24 24"><path d="M4 21V7h5v14H4Zm7 0V3h6v18h-6Zm8 0V10h3v11h-3Z"/></symbol>
            <symbol id="icon-capital" viewBox="0 0 24 24"><path d="M12 2 15 8l7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1 3-6Z"/></symbol>
          </defs>
          <rect class="sea" x="0" y="0" width="${mapWidth}" height="${mapHeight}" rx="0"></rect>
          <rect class="sea-pattern" x="0" y="0" width="${mapWidth}" height="${mapHeight}" rx="0"></rect>
          <g class="landmass country-landmass pixel-map-layer" transform="${terrainTransform}">
            ${countryLandmass()}
          </g>
          <g class="terrain-detail landscape-layer" transform="${terrainTransform}">
            ${pixelCoastHighlights()}
            ${landscapeSprites()}
            ${countryLabels()}
          </g>
          <g class="terrain-lines" transform="${terrainTransform}">
            <polyline class="terrain-ridge" points="250,600 310,600 310,580 382,580 382,604 430,604" />
            <polyline class="terrain-ridge" points="500,620 555,620 555,596 638,596 638,622 705,622" />
            <polyline class="terrain-ridge" points="630,555 716,555 716,534 808,534 808,560 900,560" />
            <polyline class="terrain-ridge" points="720,205 780,205 780,150 880,150 880,170 970,170" />
            <polyline class="terrain-ridge" points="1325,410 1370,410 1370,368 1430,368 1430,430 1490,430" />
            <polyline class="river" points="570,500 610,500 610,526 650,526 650,546 735,546 735,566 830,566 830,624 875,624 875,666 985,666" />
            <polyline class="river" points="555,535 520,535 520,505 492,505 492,455 500,455" />
            <polyline class="river" points="1080,395 1160,395 1160,418 1210,418 1210,455 1270,455" />
          </g>
          <g class="water-surfaces" transform="${terrainTransform}">
            <path class="water baltic-sea" d="M780 296 H866 V314 H924 V368 H862 V386 H790 V366 H735 V390 H718 V334 H735 V315 H780 Z" />
            <path class="water black-sea" d="M912 660 H1010 V620 H1115 V640 H1172 V708 H1086 V754 H984 V730 H912 Z" />
            <path class="water caspian-hint" d="M1285 560 H1360 V582 H1405 V625 H1388 V704 H1312 V680 H1260 V640 H1285 Z" />
          </g>
          <g class="board-routes">
            ${(map.board_routes || []).map((route) => boardRoutePath(route, progression, zoom)).join("")}
          </g>
          <g class="nodes">
            ${map.nodes.map((node) => nodeGlyph(node, progression, adjacentIds, cityStates, zoom)).join("")}
          </g>
          ${playerMarkers(session, skins, nodesById, map.board_routes || [])}
        </svg>
        ${mapLeaderboard(session)}
        ${selectedPanel(selected, map.roads, map.board_routes || [], progression, cityStates, canAct, session, missionsCollapsed)}
        ${dicePanel(map, progression, nodesById, canAct, session)}
      </div>
    </section>
  `;
}
