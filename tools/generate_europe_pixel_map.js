const fs = require("fs");
const path = require("path");

const SOURCE = path.resolve(__dirname, "..", "countries-50m.json");
const TARGET = path.resolve(__dirname, "..", "frontend", "assets", "europeCountries.js");

const VIEW_BOUNDS = {
  minLon: -13.5,
  maxLon: 78,
  minLat: 34,
  maxLat: 72.5,
};

const PIXEL_STEP = 4;
const MIN_AREA = 36;

const EUROPE_NAMES = new Set([
  "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium",
  "Bosnia and Herz.", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark",
  "Estonia", "Faeroe Is.", "Finland", "France", "Georgia", "Germany", "Greece",
  "Hungary", "Ireland", "Italy", "Kosovo", "Latvia", "Liechtenstein", "Lithuania",
  "Luxembourg", "Macedonia", "Malta", "Moldova", "Monaco", "Montenegro",
  "Netherlands", "N. Cyprus", "Norway", "Poland", "Portugal", "Romania", "Russia",
  "San Marino", "Serbia", "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland",
  "Turkey", "Ukraine", "United Kingdom", "Vatican", "Åland",
]);

const BIOMES = new Map([
  ["Norway", "north"],
  ["Sweden", "north"],
  ["Finland", "north"],
  ["Russia", "forest"],
  ["Estonia", "forest"],
  ["Latvia", "forest"],
  ["Lithuania", "forest"],
  ["Belarus", "forest"],
  ["Ukraine", "steppe"],
  ["Moldova", "steppe"],
  ["Turkey", "steppe"],
  ["Georgia", "steppe"],
  ["Armenia", "steppe"],
  ["Azerbaijan", "steppe"],
  ["Spain", "south"],
  ["Portugal", "south"],
  ["Italy", "south"],
  ["Greece", "south"],
  ["Cyprus", "south"],
  ["N. Cyprus", "south"],
  ["Malta", "south"],
  ["Albania", "south"],
  ["Austria", "mountain"],
  ["Switzerland", "mountain"],
  ["Slovenia", "mountain"],
]);

const CITY_GEO_POINTS = [
  ["LIS", -9.14, 38.72], ["OPO", -8.61, 41.15], ["MAD", -3.7, 40.42],
  ["SEV", -5.98, 37.39], ["BCN", 2.17, 41.38], ["VAL", -0.38, 39.47],
  ["BIL", -2.94, 43.26], ["BOR", -0.58, 44.84], ["TOU", 1.44, 43.6],
  ["CLF", 3.08, 45.78], ["PAR", 2.35, 48.86], ["LIL", 3.06, 50.63],
  ["STR", 7.75, 48.58], ["LYO", 4.84, 45.76], ["MAR", 5.37, 43.3],
  ["NCE", 7.26, 43.7], ["DUB", -6.26, 53.35], ["GLA", -4.25, 55.86],
  ["MAN", -2.24, 53.48], ["LON", -0.13, 51.51], ["BRU", 4.35, 50.85],
  ["AMS", 4.9, 52.37], ["COL", 6.96, 50.94], ["FRA", 8.68, 50.11],
  ["STU", 9.18, 48.78], ["MUN", 11.58, 48.14], ["HAM", 9.99, 53.55],
  ["BER", 13.4, 52.52], ["CPH", 12.57, 55.68], ["OSL", 10.75, 59.91],
  ["GOT", 11.97, 57.71], ["STO", 18.07, 59.33], ["HEL", 24.94, 60.17],
  ["TAL", 24.75, 59.44], ["RIG", 24.1, 56.95], ["VIL", 25.28, 54.69],
  ["GDN", 18.65, 54.35], ["WAR", 21.01, 52.23], ["KRA", 19.94, 50.06],
  ["PRG", 14.44, 50.08], ["ZUR", 8.54, 47.37], ["GVA", 6.14, 46.2],
  ["MIL", 9.19, 45.46], ["TUR", 7.68, 45.07], ["VEN", 12.32, 45.44],
  ["ROM", 12.5, 41.9], ["NAP", 14.27, 40.85], ["LJU", 14.51, 46.06],
  ["ZAG", 15.98, 45.81], ["SJJ", 18.41, 43.86], ["BEL", 20.46, 44.81],
  ["SKP", 21.43, 42.0], ["TIR", 19.82, 41.33], ["ATH", 23.73, 37.98],
  ["VIE", 16.37, 48.21], ["BRA", 17.11, 48.15], ["BUD", 19.04, 47.5],
  ["SOF", 23.32, 42.7], ["BUC", 26.1, 44.43], ["IST", 28.98, 41.01],
  ["ANK", 32.85, 39.93], ["CHS", 28.83, 47.01], ["ODS", 30.73, 46.48],
  ["KYI", 30.52, 50.45], ["MIN", 27.56, 53.9], ["SPB", 30.31, 59.94],
  ["MOS", 37.62, 55.75], ["NNV", 44.0, 56.33], ["KAZ", 49.12, 55.79],
  ["PER", 56.23, 58.01], ["YEK", 60.61, 56.84], ["TYU", 65.53, 57.15],
  ["VLG", 31.28, 58.52], ["TVE", 35.91, 56.86], ["YAR", 39.88, 57.63],
  ["VOR", 39.2, 51.67], ["ROS", 39.7, 47.24], ["SAM", 50.1, 53.2],
  ["UFA", 56.04, 54.74], ["CHE", 61.4, 55.16], ["OMS", 73.37, 54.98],
];

function ascii(value) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^\x20-\x7e]/g, "");
}

function slug(value) {
  return ascii(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "country";
}

function readCityTargets() {
  const seedPath = path.resolve(__dirname, "..", "backend", "services", "seed_service.py");
  const seed = fs.readFileSync(seedPath, "utf8");
  const block = seed.match(/MAP_NODES = \[([\s\S]*?)\]\n\n\ndef make_road/);
  if (!block) throw new Error("Unable to locate MAP_NODES in seed_service.py");
  const targets = new Map();
  for (const line of block[1].split(/\r?\n/)) {
    const match = line.match(/^\s+\("([^"]+)",\s+"[^"]+",\s+"[^"]+",\s+(-?\d+),\s+(-?\d+),/);
    if (match) {
      targets.set(match[1], { x: Number(match[2]), y: Number(match[3]) });
    }
  }
  return targets;
}

function terms(lon, lat) {
  const u = (lon - 18) / 45;
  const v = (lat - 51) / 19;
  return [1, u, v, u * u, u * v, v * v];
}

function solveLinear(matrix, vector) {
  const n = vector.length;
  const a = matrix.map((row, index) => [...row, vector[index]]);
  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < n; row += 1) {
      if (Math.abs(a[row][col]) > Math.abs(a[pivot][col])) pivot = row;
    }
    [a[col], a[pivot]] = [a[pivot], a[col]];
    const div = a[col][col] || 1;
    for (let item = col; item <= n; item += 1) a[col][item] /= div;
    for (let row = 0; row < n; row += 1) {
      if (row === col) continue;
      const factor = a[row][col];
      for (let item = col; item <= n; item += 1) a[row][item] -= factor * a[col][item];
    }
  }
  return a.map((row) => row[n]);
}

const CITY_TARGETS = readCityTargets();

function fitProjection(targetKey) {
  const size = terms(0, 0).length;
  const matrix = Array.from({ length: size }, () => Array(size).fill(0));
  const vector = Array(size).fill(0);
  for (const [id, lon, lat] of CITY_GEO_POINTS) {
    const targetPoint = CITY_TARGETS.get(id);
    if (!targetPoint) throw new Error(`Missing map target for city ${id}`);
    const t = terms(lon, lat);
    const target = targetPoint[targetKey];
    for (let row = 0; row < size; row += 1) {
      vector[row] += t[row] * target;
      for (let col = 0; col < size; col += 1) matrix[row][col] += t[row] * t[col];
    }
  }
  return solveLinear(matrix, vector);
}

const X_COEFFS = fitProjection("x");
const Y_COEFFS = fitProjection("y");

function dot(a, b) {
  return a.reduce((sum, value, index) => sum + value * b[index], 0);
}

function project([lon, lat]) {
  const t = terms(lon, lat);
  return [dot(X_COEFFS, t), dot(Y_COEFFS, t)];
}

function quantize(value) {
  return Math.round(value / PIXEL_STEP) * PIXEL_STEP;
}

function decodeArc(topology, arcIndex) {
  const reverse = arcIndex < 0;
  const raw = topology.arcs[reverse ? ~arcIndex : arcIndex];
  const [sx, sy] = topology.transform.scale;
  const [tx, ty] = topology.transform.translate;
  let x = 0;
  let y = 0;
  const points = raw.map(([dx, dy]) => {
    x += dx;
    y += dy;
    return [x * sx + tx, y * sy + ty];
  });
  return reverse ? points.reverse() : points;
}

function ringFromArcs(topology, ringArcs) {
  const ring = [];
  for (let index = 0; index < ringArcs.length; index += 1) {
    const arc = decodeArc(topology, ringArcs[index]);
    ring.push(...(index ? arc.slice(1) : arc));
  }
  return ring;
}

function inside(point, edge) {
  const [lon, lat] = point;
  if (edge === "left") return lon >= VIEW_BOUNDS.minLon;
  if (edge === "right") return lon <= VIEW_BOUNDS.maxLon;
  if (edge === "bottom") return lat >= VIEW_BOUNDS.minLat;
  return lat <= VIEW_BOUNDS.maxLat;
}

function intersection(a, b, edge) {
  const [ax, ay] = a;
  const [bx, by] = b;
  if (edge === "left" || edge === "right") {
    const x = edge === "left" ? VIEW_BOUNDS.minLon : VIEW_BOUNDS.maxLon;
    const ratio = (x - ax) / ((bx - ax) || 1);
    return [x, ay + (by - ay) * ratio];
  }
  const y = edge === "bottom" ? VIEW_BOUNDS.minLat : VIEW_BOUNDS.maxLat;
  const ratio = (y - ay) / ((by - ay) || 1);
  return [ax + (bx - ax) * ratio, y];
}

function clipRing(points) {
  let output = points;
  for (const edge of ["left", "right", "bottom", "top"]) {
    const input = output;
    output = [];
    for (let index = 0; index < input.length; index += 1) {
      const current = input[index];
      const previous = input[(index + input.length - 1) % input.length];
      const currentInside = inside(current, edge);
      const previousInside = inside(previous, edge);
      if (currentInside) {
        if (!previousInside) output.push(intersection(previous, current, edge));
        output.push(current);
      } else if (previousInside) {
        output.push(intersection(previous, current, edge));
      }
    }
    if (output.length < 3) return [];
  }
  return output;
}

function ringArea(points) {
  let area = 0;
  for (let index = 0; index < points.length; index += 1) {
    const [ax, ay] = points[index];
    const [bx, by] = points[(index + 1) % points.length];
    area += ax * by - bx * ay;
  }
  return Math.abs(area / 2);
}

function simplifyProjected(points) {
  const projected = points.map((point) => {
    const [x, y] = project(point);
    return [quantize(x), quantize(y)];
  });
  const deduped = projected.filter((point, index) => {
    const previous = projected[(index + projected.length - 1) % projected.length];
    return point[0] !== previous[0] || point[1] !== previous[1];
  });
  if (deduped.length < 3) return [];
  const simplified = [];
  for (let index = 0; index < deduped.length; index += 1) {
    const a = deduped[(index + deduped.length - 1) % deduped.length];
    const b = deduped[index];
    const c = deduped[(index + 1) % deduped.length];
    const abx = b[0] - a[0];
    const aby = b[1] - a[1];
    const bcx = c[0] - b[0];
    const bcy = c[1] - b[1];
    const cross = abx * bcy - aby * bcx;
    const sameDirection = abx * bcx + aby * bcy >= 0;
    if (cross === 0 && sameDirection) continue;
    simplified.push(b);
  }
  return simplified.length >= 3 ? simplified : deduped;
}

function pathFromRing(points) {
  return `M${points.map(([x, y]) => `${x},${y}`).join("L")}Z`;
}

function geometryPolygons(geometry) {
  if (geometry.type === "Polygon") return geometry.arcs;
  if (geometry.type === "MultiPolygon") return geometry.arcs.flat();
  return [];
}

function buildCountry(topology, geometry) {
  const paths = [];
  for (const ringArcs of geometryPolygons(geometry)) {
    const clipped = clipRing(ringFromArcs(topology, ringArcs));
    if (!clipped.length) continue;
    const simplified = simplifyProjected(clipped);
    if (simplified.length < 3 || ringArea(simplified) < MIN_AREA) continue;
    paths.push(pathFromRing(simplified));
  }
  return paths;
}

function main() {
  const topology = JSON.parse(fs.readFileSync(SOURCE, "utf8"));
  const countries = topology.objects.countries.geometries
    .filter((geometry) => EUROPE_NAMES.has(geometry.properties.name))
    .map((geometry) => {
      const name = geometry.properties.name;
      return {
        id: slug(name),
        name: ascii(name),
        biome: BIOMES.get(name) || "west",
        paths: buildCountry(topology, geometry),
      };
    })
    .filter((country) => country.paths.length)
    .sort((a, b) => a.name.localeCompare(b.name));

  const labels = [
    ["FRANCE", 415, 590], ["ESPAGNE", 235, 705], ["ALLEMAGNE", 570, 470],
    ["ITALIE", 665, 745], ["POLOGNE", 810, 505], ["UKRAINE", 980, 585],
    ["RUSSIE", 1245, 475, "large"], ["SUEDE", 820, 185], ["FINLANDE", 965, 205],
    ["ROYAUME-UNI", 388, 330], ["TURQUIE", 1085, 818],
  ];

  const output = `// Generated from World Atlas 50m / Natural Earth via tools/generate_europe_pixel_map.js.
// Pixel step: ${PIXEL_STEP} map units. Keep ASCII for browser portability.
export const EUROPE_COUNTRY_PATHS = ${JSON.stringify(countries, null, 2)};

export const EUROPE_COUNTRY_LABELS = ${JSON.stringify(labels, null, 2)};
`;
  fs.writeFileSync(TARGET, output);
  console.log(`Generated ${countries.length} countries into ${path.relative(process.cwd(), TARGET)}`);
}

main();
