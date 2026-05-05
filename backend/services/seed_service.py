import json
from urllib.parse import quote


FUEL_CAPACITY_LITERS = 35


DEFAULT_SKIN_SLUG = "twingo-bleu-mediterranee"
RARITY_LEVELS = {
    "Commun": 1,
    "Peu commun": 2,
    "Rare": 3,
    "Epique": 4,
    "Legendaire": 5,
    "Mythique": 6,
}


def _twingo_face_asset(body, accent, glass, detail="#263544", pattern="plain"):
    gradient = ""
    body_fill = body
    if pattern in {"sunset", "gold", "space", "ghost"}:
        gradient = f"""
          <linearGradient id="body" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="{body}" />
            <stop offset="1" stop-color="{accent}" />
          </linearGradient>
        """
        body_fill = "url(#body)"
    decals = {
        "rally": '<path d="M88 28 68 140" stroke="#f7f7ff" stroke-width="10"/><path d="M113 26 93 143" stroke="#1f2937" stroke-width="6"/>',
        "street": '<path d="M72 113 C86 101 102 123 118 108 S150 105 157 118" fill="none" stroke="#f6e05e" stroke-width="7" stroke-linecap="round"/>',
        "pastel": '<circle cx="76" cy="111" r="11" fill="#b8f2d0"/><circle cx="144" cy="111" r="11" fill="#ffc6d9"/>',
        "kenzo": '<path d="M78 116 C88 94 107 132 119 108 S145 98 151 122" fill="none" stroke="#f7f7ff" stroke-width="5" stroke-linecap="round"/>',
        "art": '<circle cx="82" cy="118" r="12" fill="#ffd84d"/><path d="M116 105 146 134" stroke="#3a86ff" stroke-width="10" stroke-linecap="round"/>',
        "neon": '<path d="M56 129 C88 151 132 151 164 129" fill="none" stroke="#53ffbd" stroke-width="8" stroke-linecap="round"/>',
        "taxi": '<rect x="88" y="18" width="44" height="18" rx="5" fill="#ffd84d" stroke="#263544" stroke-width="4"/><path d="M92 27h36" stroke="#263544" stroke-width="3"/>',
        "dragon": '<path d="M60 55 35 37 49 70 Z" fill="#ffcf33"/><path d="M160 55 185 37 171 70 Z" fill="#ffcf33"/><path d="M95 118 C110 96 124 96 139 118" fill="none" stroke="#ff3d3d" stroke-width="6" stroke-linecap="round"/>',
        "pixel": '<rect x="66" y="88" width="16" height="16" fill="#111827"/><rect x="138" y="88" width="16" height="16" fill="#111827"/><rect x="98" y="122" width="24" height="8" fill="#111827"/>',
        "noel": '<path d="M63 48 C85 13 134 13 157 48" fill="#d7263d"/><circle cx="158" cy="48" r="8" fill="#fff"/>',
        "halloween": '<path d="M77 86 98 92 76 101 Z" fill="#fff06a"/><path d="M143 86 122 92 144 101 Z" fill="#fff06a"/>',
    }.get(pattern, "")
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 170" role="img" aria-label="Twingo face">
      <defs>{gradient}</defs>
      <path d="M55 128 C49 112 46 90 51 70 C58 41 78 25 110 25 C142 25 162 41 169 70 C174 90 171 112 165 128 L155 143 L65 143 Z" fill="{body_fill}" stroke="{detail}" stroke-width="4"/>
      {decals}
      <path d="M70 69 C77 47 91 37 110 37 C129 37 143 47 150 69 C135 78 85 78 70 69 Z" fill="{glass}" stroke="{detail}" stroke-width="4"/>
      <path d="M67 88 C77 80 89 80 99 88 C93 101 74 101 67 88 Z" fill="#fff7a8" stroke="{detail}" stroke-width="3"/>
      <path d="M153 88 C143 80 131 80 121 88 C127 101 146 101 153 88 Z" fill="#fff7a8" stroke="{detail}" stroke-width="3"/>
      <circle cx="82" cy="91" r="4" fill="{detail}"/><circle cx="138" cy="91" r="4" fill="{detail}"/>
      <path d="M76 113 C92 124 128 124 144 113" fill="none" stroke="{detail}" stroke-width="7" stroke-linecap="round"/>
      <path d="M62 122 C84 135 136 135 158 122 L155 143 L65 143 Z" fill="{accent}" stroke="{detail}" stroke-width="4"/>
      <circle cx="69" cy="143" r="18" fill="{detail}"/><circle cx="151" cy="143" r="18" fill="{detail}"/>
      <circle cx="69" cy="143" r="8" fill="#eef6ff"/><circle cx="151" cy="143" r="8" fill="#eef6ff"/>
      <path d="M91 34 C100 30 120 30 129 34" fill="none" stroke="#f7f7ff" stroke-width="5" stroke-linecap="round"/>
    </svg>
    """
    return f"data:image/svg+xml;charset=utf-8,{quote(' '.join(svg.split()))}"


def _skin(slug, name, rarity, inspired_by, description, palette, pattern="plain"):
    return {
        "slug": slug,
        "name": name,
        "rarity": rarity,
        "inspired_by": inspired_by,
        "description": description,
        "palette": palette,
        "min_level": RARITY_LEVELS[rarity],
        "asset": _twingo_face_asset(palette[0], palette[1], palette[2], palette[3] if len(palette) > 3 else "#263544", pattern),
    }


SKINS = [
    _skin("twingo-bleu-mediterranee", "Twingo Bleu Mediterranee", "Commun", "Palette Twingo", "Bleu vif, regard rond, base parfaite du garage.", ["#2f80ed", "#20a39e", "#9ee8f6"]),
    _skin("twingo-jaune-indien", "Twingo Jaune Indien", "Commun", "Palette Twingo", "Jaune chaud et pare-chocs pop.", ["#ffd84d", "#ff8f3d", "#9ee8f6"]),
    _skin("twingo-rouge-vif", "Twingo Rouge Vif", "Commun", "Palette Twingo", "Rouge franc, petite grenouille nerveuse.", ["#d7263d", "#ffd84d", "#bdefff"]),
    _skin("twingo-vert-coriandre", "Twingo Vert Coriandre", "Commun", "Palette Twingo", "Vert frais, sourire de ville.", ["#38b000", "#ffd84d", "#c8f7ff"]),
    _skin("twingo-blanc-glacier", "Twingo Blanc Glacier", "Commun", "Palette Twingo", "Blanc lumineux, phares bien ronds.", ["#f7f7ff", "#9aa7b5", "#c8f7ff"]),
    _skin("twingo-noir-nacre", "Twingo Noir Nacre", "Commun", "Palette Twingo", "Noir nacre, discret mais bien campe.", ["#23272f", "#596273", "#9ee8f6", "#111827"]),
    _skin("twingo-rayures-rallye", "Twingo Rayures Rallye", "Peu commun", "Rallye urbain", "Deux bandes sportives sur une face de Twingo tres sure d'elle.", ["#ff4f7b", "#1f2937", "#bdefff"], "rally"),
    _skin("twingo-urban-street", "Twingo Urban Street", "Peu commun", "Street art", "Marquage urbain et pare-chocs contrastes.", ["#4b5563", "#ff4f7b", "#bdefff"], "street"),
    _skin("twingo-pastel-edition", "Twingo Pastel Edition", "Peu commun", "Pastel", "Rose pastel et vert menthe pour une Twingo douce.", ["#ffc6d9", "#b8f2d0", "#e2fbff"], "pastel"),
    _skin("twingo-night-blue", "Twingo Night Blue", "Peu commun", "Nocturne", "Bleu nuit, vitres froides, grenouille de minuit.", ["#182a88", "#67e8f9", "#bdefff", "#101828"]),
    _skin("twingo-sunset", "Twingo Sunset", "Peu commun", "Coucher de soleil", "Degrade orange rose pour rouler au soleil bas.", ["#ff8f3d", "#ff4f7b", "#ffe1cc"], "sunset"),
    _skin("twingo-kenzo", "Twingo Kenzo", "Rare", "Twingo Kenzo", "Motifs doux et esprit serie speciale.", ["#65c7f7", "#2f80ed", "#f7f7ff"], "kenzo"),
    _skin("twingo-initiale", "Twingo Initiale", "Rare", "Initiale", "Finition chic, sombre et propre.", ["#263544", "#d6b36a", "#dceeff"], "plain"),
    _skin("twingo-pepito", "Twingo Pepito", "Rare", "Fantaisie snack", "Brun biscuit, creme et petite bouille malicieuse.", ["#7a4a28", "#f4d487", "#ffe6c7"], "pastel"),
    _skin("twingo-art-car", "Twingo Art Car", "Rare", "Art Car", "Taches, lignes et bonne humeur graphique.", ["#f7f7ff", "#ff4f7b", "#9ee8f6"], "art"),
    _skin("twingo-iceberg", "Twingo Iceberg", "Rare", "Grand froid", "Bleu pale et reflets givres.", ["#a7f3ff", "#e0f7ff", "#f7fdff"], "plain"),
    _skin("twingo-rs-tribute", "Twingo RS Tribute", "Epique", "Jaune Sirius", "Jaune sport, regard large, hommage RS.", ["#ffd400", "#111827", "#bdefff"], "rally"),
    _skin("twingo-rally-monte-carlo", "Twingo Rally Monte-Carlo", "Epique", "Monte-Carlo", "Rouge, blanc, noir: speciale de montagne.", ["#f7f7ff", "#d7263d", "#bdefff"], "rally"),
    _skin("twingo-neon-drift", "Twingo Neon Drift", "Epique", "Neon", "Contours lumineux pour deraper dans les villes.", ["#111827", "#ff4fbd", "#84ffff"], "neon"),
    _skin("twingo-off-road", "Twingo Off-Road", "Epique", "Aventure", "Verte, robuste et prete a manger les departementales.", ["#587347", "#d6b36a", "#dff7ff"], "street"),
    _skin("twingo-taxi-parisien", "Twingo Taxi Parisien", "Epique", "Taxi", "La Twingo taxi qui connait toutes les rocades.", ["#ffd84d", "#111827", "#dff7ff"], "taxi"),
    _skin("twingo-renault-f1-team", "Twingo Renault F1 Team", "Legendaire", "Renault F1 Team", "Ultra rare, livree noire et jaune de paddock.", ["#111827", "#ffd400", "#bdefff"], "rally"),
    _skin("twingo-renault-sport-concept", "Twingo Renault Sport Concept", "Legendaire", "Renault Sport Concept", "Concept car compacte, sourire agressif.", ["#ff8f3d", "#111827", "#dff7ff"], "neon"),
    _skin("twingo-v6-swap", "Twingo V6 Swap", "Legendaire", "V6 Swap", "Petite face, grosse legende mecanique.", ["#6d28d9", "#f97316", "#dff7ff"], "street"),
    _skin("twingo-gordini", "Twingo Gordini", "Legendaire", "Gordini", "Bleu profond et double bande blanche.", ["#1d4ed8", "#f7f7ff", "#bdefff"], "rally"),
    _skin("twingo-dragon", "Twingo Dragon", "Legendaire", "Fantaisie", "Cornes et regard de feu, toujours Twingo.", ["#147a3d", "#ff3d3d", "#ffd6a3"], "dragon"),
    _skin("twingo-space-odyssey", "Twingo Space Odyssey", "Legendaire", "Fantaisie", "Noir spatial, cockpit froid, mission orbitale.", ["#111827", "#7dd3fc", "#dff7ff"], "space"),
    _skin("twingo-gold-edition", "Twingo Gold Edition", "Legendaire", "Fantaisie", "Gold total, pare-chocs bijou.", ["#f5c542", "#fff3a3", "#dff7ff"], "gold"),
    _skin("twingo-pixel-art", "Twingo Pixel Art", "Legendaire", "Fantaisie", "Une Twingo arcade aux phares carres.", ["#3a86ff", "#ff4f7b", "#dff7ff"], "pixel"),
    _skin("twingo-ghost", "Twingo Ghost", "Legendaire", "Fantaisie", "Blanche fantomatique et presque transparente.", ["#f7f7ff", "#c7d2fe", "#ffffff"], "ghost"),
    _skin("twingo-charade-classic", "Twingo Charade Classic Edition", "Mythique", "Evenement Charade", "Edition circuit classique, tres speciale.", ["#0f766e", "#f4d487", "#dff7ff"], "rally"),
    _skin("twingo-alpine-tribute", "Twingo Alpine Tribute", "Mythique", "Alpine Tribute", "Bleu Alpine, bandes fines, grande classe.", ["#1d9bf0", "#f7f7ff", "#dff7ff"], "rally"),
    _skin("twingo-prototype-1993", "Twingo Prototype 1993", "Mythique", "Prototype 1993", "La Twingo originelle, presque concept.", ["#74c69d", "#ffd84d", "#dff7ff"], "plain"),
    _skin("twingo-noel", "Twingo Noel", "Mythique", "Evenement Noel", "Bonnet rouge et phares joyeux.", ["#d7263d", "#f7f7ff", "#dff7ff"], "noel"),
    _skin("twingo-halloween", "Twingo Halloween", "Mythique", "Evenement Halloween", "Regard citrouille et face orange.", ["#f97316", "#111827", "#ffe6c7"], "halloween"),
]


MAP_WIDTH = 2300
MAP_HEIGHT = 1400
COORD_SCALE_X = 1.36
COORD_SCALE_Y = 1.28
COORD_OFFSET_X = 70
COORD_OFFSET_Y = 55

CAPITAL_NODE_IDS = {
    "LIS", "MAD", "PAR", "DUB", "LON", "BRU", "AMS", "BER", "CPH", "OSL",
    "STO", "HEL", "TAL", "RIG", "VIL", "WAR", "PRG", "VIE", "BRA", "BUD",
    "LJU", "ZAG", "SJJ", "BEL", "SKP", "TIR", "ATH", "SOF", "BUC", "IST",
    "ANK", "CHS", "KYI", "MIN", "MOS",
}


MAP_NODES = [
    ("LIS", "Lisbon", "Portugal", 136, 752, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -16}, "fog"),
    ("OPO", "Porto", "Portugal", 157, 688, "resource", {"coins": 10}, "rain"),
    ("MAD", "Madrid", "Spain", 271, 726, "resource", {"coins": 16}, "heat"),
    ("SEV", "Seville", "Spain", 213, 797, "event", {}, "heat"),
    ("BCN", "Barcelona", "Spain", 409, 721, "event", {}, "clear"),
    ("VAL", "Valencia", "Spain", 349, 763, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -16}, "clear"),
    ("BIL", "Bilbao", "Spain", 297, 650, "garage", {"repair": -22}, "rain"),
    ("BOR", "Bordeaux", "France", 356, 614, "resource", {"coins": 10}, "rain"),
    ("TOU", "Toulouse", "France", 396, 657, "event", {}, "clear"),
    ("CLF", "Clermont-Ferrand", "France", 439, 600, "garage", {"repair": -22}, "fog"),
    ("PAR", "Paris", "France", 440, 503, "resource", {"coins": 12}, "clear"),
    ("LIL", "Lille", "France", 468, 450, "peage", {"coins": -7}, "rain"),
    ("STR", "Strasbourg", "France", 547, 533, "resource", {"coins": 9}, "fog"),
    ("LYO", "Lyon", "France", 476, 607, "garage", {"repair": -22}, "rain"),
    ("MAR", "Marseille", "France", 482, 680, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -18}, "clear"),
    ("NCE", "Nice", "France", 524, 675, "event", {}, "clear"),
    ("DUB", "Dublin", "Ireland", 317, 320, "resource", {"coins": 12}, "fog"),
    ("GLA", "Glasgow", "United Kingdom", 391, 241, "garage", {"repair": -26}, "rain"),
    ("MAN", "Manchester", "United Kingdom", 396, 333, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -18}, "rain"),
    ("LON", "London", "United Kingdom", 414, 408, "peage", {"coins": -8}, "fog"),
    ("BRU", "Brussels", "Belgium", 495, 448, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -18}, "rain"),
    ("AMS", "Amsterdam", "Netherlands", 518, 401, "event", {}, "rain"),
    ("COL", "Cologne", "Germany", 546, 456, "resource", {"coins": 10}, "rain"),
    ("FRA", "Frankfurt", "Germany", 573, 489, "peage", {"coins": -8}, "fog"),
    ("STU", "Stuttgart", "Germany", 577, 533, "garage", {"repair": -24}, "rain"),
    ("MUN", "Munich", "Germany", 622, 561, "garage", {"repair": -28}, "rain"),
    ("HAM", "Hamburg", "Germany", 622, 382, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -18}, "clear"),
    ("BER", "Berlin", "Germany", 676, 430, "event", {}, "fog"),
    ("CPH", "Copenhagen", "Denmark", 685, 321, "weather", {}, "wind"),
    ("OSL", "Oslo", "Norway", 703, 161, "garage", {"repair": -30}, "snow"),
    ("GOT", "Gothenburg", "Sweden", 696, 247, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -20}, "wind"),
    ("STO", "Stockholm", "Sweden", 810, 215, "resource", {"coins": 14}, "snow"),
    ("HEL", "Helsinki", "Finland", 921, 214, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -22}, "snow"),
    ("TAL", "Tallinn", "Estonia", 912, 239, "event", {}, "snow"),
    ("RIG", "Riga", "Latvia", 885, 324, "resource", {"coins": 10}, "fog"),
    ("VIL", "Vilnius", "Lithuania", 893, 406, "garage", {"repair": -24}, "clear"),
    ("GDN", "Gdansk", "Poland", 780, 391, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -18}, "wind"),
    ("WAR", "Warsaw", "Poland", 812, 469, "resource", {"coins": 10}, "clear"),
    ("KRA", "Krakow", "Poland", 787, 534, "event", {}, "clear"),
    ("PRG", "Prague", "Czechia", 684, 512, "peage", {"coins": -6}, "clear"),
    ("ZUR", "Zurich", "Switzerland", 558, 573, "peage", {"coins": -10}, "snow"),
    ("GVA", "Geneva", "Switzerland", 505, 599, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -16}, "snow"),
    ("MIL", "Milan", "Italy", 567, 632, "peage", {"coins": -10}, "rain"),
    ("TUR", "Turin", "Italy", 534, 638, "resource", {"coins": 8}, "rain"),
    ("VEN", "Venice", "Italy", 632, 644, "resource", {"coins": 8, "fuel": 5}, "clear"),
    ("ROM", "Rome", "Italy", 640, 743, "event", {}, "clear"),
    ("NAP", "Naples", "Italy", 683, 777, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -18}, "clear"),
    ("LJU", "Ljubljana", "Slovenia", 678, 634, "garage", {"repair": -22}, "rain"),
    ("ZAG", "Zagreb", "Croatia", 708, 646, "resource", {"fuel": 12}, "rain"),
    ("SJJ", "Sarajevo", "Bosnia and Herzegovina", 762, 710, "event", {}, "rain"),
    ("BEL", "Belgrade", "Serbia", 801, 690, "garage", {"repair": -24}, "clear"),
    ("SKP", "Skopje", "North Macedonia", 834, 770, "resource", {"coins": 9}, "clear"),
    ("TIR", "Tirana", "Albania", 803, 782, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -16}, "clear"),
    ("ATH", "Athens", "Greece", 916, 878, "event", {}, "clear"),
    ("VIE", "Vienna", "Austria", 716, 577, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -20}, "clear"),
    ("BRA", "Bratislava", "Slovakia", 731, 582, "resource", {"coins": 8}, "clear"),
    ("BUD", "Budapest", "Hungary", 768, 608, "event", {}, "fog"),
    ("SOF", "Sofia", "Bulgaria", 870, 758, "garage", {"repair": -24}, "clear"),
    ("BUC", "Bucharest", "Romania", 917, 720, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -18}, "clear"),
    ("IST", "Istanbul", "Turkey", 1003, 820, "peage", {"coins": -12}, "clear"),
    ("ANK", "Ankara", "Turkey", 1097, 858, "resource", {"coins": 14}, "heat"),
    ("CHS", "Chisinau", "Moldova", 959, 657, "event", {}, "clear"),
    ("ODS", "Odesa", "Ukraine", 998, 678, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -18}, "wind"),
    ("KYI", "Kyiv", "Ukraine", 980, 561, "resource", {"coins": 12}, "clear"),
    ("MIN", "Minsk", "Belarus", 929, 441, "garage", {"repair": -26}, "snow"),
    ("SPB", "Saint Petersburg", "Russia", 997, 244, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -22}, "snow"),
    ("MOS", "Moscow", "Russia", 1093, 418, "event", {}, "snow"),
    ("NNV", "Nizhny Novgorod", "Russia", 1189, 423, "resource", {"coins": 12}, "snow"),
    ("KAZ", "Kazan", "Russia", 1266, 459, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -22}, "snow"),
    ("PER", "Perm", "Russia", 1356, 412, "garage", {"repair": -30}, "snow"),
    ("YEK", "Yekaterinburg", "Russia", 1422, 466, "event", {}, "snow"),
    ("TYU", "Tyumen", "Russia", 1485, 473, "resource", {"coins": 16}, "snow"),
    ("VLG", "Veliky Novgorod", "Russia", 1004, 299, "resource", {"coins": 10}, "snow"),
    ("TVE", "Tver", "Russia", 1068, 374, "garage", {"repair": -26}, "snow"),
    ("YAR", "Yaroslavl", "Russia", 1128, 363, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -20}, "snow"),
    ("VOR", "Voronezh", "Russia", 1126, 554, "event", {}, "clear"),
    ("ROS", "Rostov-on-Don", "Russia", 1161, 687, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -20}, "wind"),
    ("SAM", "Samara", "Russia", 1294, 545, "resource", {"coins": 12}, "snow"),
    ("UFA", "Ufa", "Russia", 1373, 517, "garage", {"repair": -28}, "snow"),
    ("CHE", "Chelyabinsk", "Russia", 1447, 522, "resource", {"coins": 14}, "snow"),
    ("OMS", "Omsk", "Russia", 1613, 567, "station", {"fuel": FUEL_CAPACITY_LITERS, "coins": -24}, "snow"),
]


def make_road(from_node, to_node, road_type, distance_km):
    if road_type == "autoroute":
        return (from_node, to_node, road_type, distance_km, max(12, round(distance_km / 22)), max(2, round(distance_km / 75)), 0.09)
    if road_type == "nationale":
        return (from_node, to_node, road_type, distance_km, 0, max(2, round(distance_km / 55)), 0.15)
    return (from_node, to_node, road_type, distance_km, 0, max(3, round(distance_km / 38)), 0.22)


def scaled_node(node):
    node_id, city, country, x, y, node_type, resource, weather = node
    return (
        node_id,
        city,
        country,
        round(x * COORD_SCALE_X + COORD_OFFSET_X),
        round(y * COORD_SCALE_Y + COORD_OFFSET_Y),
        node_type,
        json.dumps(resource),
        weather,
    )


ROADS = [
    # Iberia and western France
    make_road("LIS", "OPO", "nationale", 315),
    make_road("LIS", "MAD", "nationale", 625),
    make_road("OPO", "BIL", "departementale", 705),
    make_road("BIL", "BOR", "nationale", 335),
    make_road("MAD", "SEV", "departementale", 530),
    make_road("MAD", "VAL", "nationale", 360),
    make_road("MAD", "BCN", "autoroute", 620),
    make_road("VAL", "BCN", "nationale", 350),
    make_road("BOR", "TOU", "departementale", 245),
    make_road("TOU", "BCN", "nationale", 395),
    make_road("BOR", "PAR", "autoroute", 585),
    make_road("BOR", "CLF", "nationale", 370),
    make_road("TOU", "CLF", "departementale", 375),
    make_road("TOU", "LYO", "nationale", 540),

    # France, Alps and Italy
    make_road("PAR", "LIL", "autoroute", 225),
    make_road("PAR", "CLF", "departementale", 425),
    make_road("PAR", "LYO", "autoroute", 465),
    make_road("PAR", "STR", "autoroute", 490),
    make_road("CLF", "LYO", "nationale", 165),
    make_road("CLF", "MAR", "autoroute", 475),
    make_road("LYO", "MAR", "autoroute", 315),
    make_road("MAR", "NCE", "nationale", 200),
    make_road("NCE", "TUR", "departementale", 280),
    make_road("LYO", "GVA", "departementale", 150),
    make_road("GVA", "ZUR", "nationale", 280),
    make_road("STR", "FRA", "nationale", 220),
    make_road("STR", "STU", "nationale", 150),
    make_road("STR", "ZUR", "departementale", 230),
    make_road("ZUR", "MIL", "autoroute", 280),
    make_road("MIL", "TUR", "departementale", 145),
    make_road("MIL", "VEN", "nationale", 270),
    make_road("VEN", "ROM", "autoroute", 525),
    make_road("ROM", "NAP", "nationale", 230),

    # British Isles and Benelux
    make_road("DUB", "MAN", "nationale", 285),
    make_road("MAN", "GLA", "nationale", 345),
    make_road("MAN", "LON", "autoroute", 335),
    make_road("LON", "PAR", "autoroute", 470),
    make_road("LON", "BRU", "nationale", 365),
    make_road("PAR", "BRU", "autoroute", 315),
    make_road("PAR", "AMS", "nationale", 510),
    make_road("LIL", "BRU", "nationale", 115),
    make_road("BRU", "AMS", "nationale", 210),
    make_road("BRU", "COL", "autoroute", 210),
    make_road("COL", "AMS", "nationale", 265),
    make_road("COL", "FRA", "autoroute", 190),

    # German and central hubs
    make_road("FRA", "STU", "autoroute", 205),
    make_road("STU", "MUN", "autoroute", 220),
    make_road("FRA", "PRG", "nationale", 520),
    make_road("MUN", "ZUR", "autoroute", 315),
    make_road("MUN", "PRG", "nationale", 380),
    make_road("MUN", "VIE", "autoroute", 435),
    make_road("HAM", "AMS", "autoroute", 465),
    make_road("HAM", "BER", "autoroute", 290),
    make_road("HAM", "CPH", "nationale", 335),
    make_road("BER", "CPH", "autoroute", 440),
    make_road("BER", "WAR", "nationale", 575),
    make_road("BER", "GDN", "nationale", 500),
    make_road("BER", "PRG", "autoroute", 350),

    # Scandinavia and Baltic arc
    make_road("CPH", "OSL", "departementale", 610),
    make_road("CPH", "GOT", "nationale", 315),
    make_road("RIG", "GOT", "nationale", 780),
    make_road("GOT", "OSL", "nationale", 295),
    make_road("GOT", "STO", "autoroute", 470),
    make_road("STO", "HEL", "nationale", 480),
    make_road("HEL", "TAL", "departementale", 85),
    make_road("TAL", "RIG", "nationale", 310),
    make_road("RIG", "VIL", "nationale", 295),
    make_road("VIL", "GDN", "departementale", 430),
    make_road("GDN", "WAR", "autoroute", 340),

    # Poland, Danube and Balkans
    make_road("WAR", "KRA", "autoroute", 300),
    make_road("KRA", "PRG", "nationale", 530),
    make_road("PRG", "VIE", "nationale", 330),
    make_road("PRG", "BUD", "departementale", 530),
    make_road("VIE", "BRA", "departementale", 80),
    make_road("BRA", "BUD", "autoroute", 200),
    make_road("VIE", "BUD", "autoroute", 245),
    make_road("VIE", "LJU", "nationale", 380),
    make_road("BUD", "ZAG", "nationale", 345),
    make_road("ZAG", "LJU", "departementale", 140),
    make_road("LJU", "VEN", "nationale", 240),
    make_road("ZAG", "BEL", "departementale", 395),
    make_road("BEL", "SJJ", "departementale", 295),
    make_road("SJJ", "TIR", "departementale", 390),
    make_road("TIR", "ATH", "nationale", 705),
    make_road("BEL", "SKP", "nationale", 430),
    make_road("SKP", "ATH", "nationale", 695),
    make_road("BEL", "SOF", "nationale", 395),
    make_road("SOF", "BUC", "nationale", 385),
    make_road("BUC", "IST", "departementale", 640),
    make_road("SOF", "IST", "autoroute", 550),
    make_road("IST", "ANK", "autoroute", 450),

    # Black Sea, Ukraine and Belarus
    make_road("BUC", "CHS", "nationale", 465),
    make_road("CHS", "ODS", "departementale", 180),
    make_road("ODS", "KYI", "nationale", 475),
    make_road("KYI", "VOR", "nationale", 650),
    make_road("KYI", "MIN", "nationale", 560),
    make_road("WAR", "MIN", "nationale", 545),
    make_road("VIL", "MIN", "nationale", 185),
    make_road("MIN", "MOS", "autoroute", 715),

    # Russia, Volga and Ural arc
    make_road("SPB", "HEL", "nationale", 390),
    make_road("SPB", "TAL", "departementale", 365),
    make_road("SPB", "VLG", "nationale", 195),
    make_road("VLG", "TVE", "departementale", 360),
    make_road("TVE", "MOS", "autoroute", 175),
    make_road("SPB", "MOS", "autoroute", 710),
    make_road("MOS", "NNV", "autoroute", 420),
    make_road("MOS", "YAR", "nationale", 270),
    make_road("YAR", "NNV", "departementale", 365),
    make_road("MOS", "VOR", "nationale", 520),
    make_road("VOR", "ROS", "autoroute", 565),
    make_road("VOR", "SAM", "nationale", 760),
    make_road("NNV", "KAZ", "nationale", 395),
    make_road("NNV", "SAM", "nationale", 680),
    make_road("SAM", "KAZ", "departementale", 360),
    make_road("KAZ", "PER", "nationale", 600),
    make_road("ROS", "UFA", "departementale", 1420),
    make_road("SAM", "UFA", "autoroute", 460),
    make_road("UFA", "PER", "nationale", 480),
    make_road("UFA", "CHE", "departementale", 420),
    make_road("CHE", "YEK", "autoroute", 215),
    make_road("PER", "YEK", "departementale", 360),
    make_road("YEK", "TYU", "nationale", 330),
    make_road("TYU", "OMS", "nationale", 625),
    make_road("CHE", "OMS", "departementale", 910),
]


TRAJETS = [
    {
        "title": "Paris -> Rome",
        "kind": "long",
        "cities": ["PAR", "ROM"],
        "distance_hint": 1420,
        "reward_xp": 190,
        "reward_coins": 80,
        "description": "Relier les boulevards parisiens aux ruelles romaines.",
    },
    {
        "title": "Lyon -> Geneva",
        "kind": "court",
        "cities": ["LYO", "GVA"],
        "distance_hint": 150,
        "reward_xp": 65,
        "reward_coins": 30,
        "description": "Un saut alpin rapide, parfait pour tester les nationales.",
    },
    {
        "title": "Berlin -> Vienna",
        "kind": "long",
        "cities": ["BER", "VIE"],
        "distance_hint": 680,
        "reward_xp": 130,
        "reward_coins": 55,
        "description": "Descendre vers la musique et les garages bien ranges.",
    },
    {
        "title": "Madrid -> Lisbon",
        "kind": "court",
        "cities": ["MAD", "LIS"],
        "distance_hint": 625,
        "reward_xp": 90,
        "reward_coins": 45,
        "description": "Ouest iberique, soleil, carburant et routes economes.",
    },
    {
        "title": "Amsterdam -> Copenhagen -> Stockholm",
        "kind": "long",
        "cities": ["AMS", "CPH", "STO"],
        "distance_hint": 1455,
        "reward_xp": 220,
        "reward_coins": 95,
        "description": "Une montee nordique avec brouillard, ponts et neige.",
    },
    {
        "title": "Lisbon -> Tyumen",
        "kind": "long",
        "cities": ["LIS", "TYU"],
        "distance_hint": 5600,
        "reward_xp": 420,
        "reward_coins": 170,
        "description": "La traversee totale du plateau europeen.",
    },
    {
        "title": "London -> Istanbul",
        "kind": "long",
        "cities": ["LON", "IST"],
        "distance_hint": 3000,
        "reward_xp": 280,
        "reward_coins": 120,
        "description": "Du tunnel aux rives du Bosphore.",
    },
    {
        "title": "Oslo -> Athens",
        "kind": "long",
        "cities": ["OSL", "ATH"],
        "distance_hint": 3600,
        "reward_xp": 320,
        "reward_coins": 140,
        "description": "Neige, montagnes, puis soleil grec.",
    },
    {
        "title": "Dublin -> Moscow",
        "kind": "long",
        "cities": ["DUB", "MOS"],
        "distance_hint": 3400,
        "reward_xp": 300,
        "reward_coins": 130,
        "description": "Une diagonale humide, urbaine et tres longue.",
    },
    {
        "title": "Nice -> Ljubljana -> Budapest",
        "kind": "court",
        "cities": ["NCE", "LJU", "BUD"],
        "distance_hint": 980,
        "reward_xp": 140,
        "reward_coins": 65,
        "description": "Un trajet rapide entre mer, Alpes et Danube.",
    },
]


STARTER_TRAJETS = [
    ("Lisbon -> Madrid", ["LIS", "MAD"], 625),
    ("Madrid -> Valencia", ["MAD", "VAL"], 355),
    ("Paris -> Brussels", ["PAR", "BRU"], 315),
    ("Dublin -> Manchester", ["DUB", "MAN"], 270),
    ("London -> Brussels", ["LON", "BRU"], 370),
    ("Brussels -> Amsterdam", ["BRU", "AMS"], 210),
    ("Amsterdam -> Cologne", ["AMS", "COL"], 265),
    ("Berlin -> Prague", ["BER", "PRG"], 350),
    ("Copenhagen -> Gothenburg", ["CPH", "GOT"], 315),
    ("Oslo -> Gothenburg", ["OSL", "GOT"], 290),
    ("Stockholm -> Helsinki", ["STO", "HEL"], 400),
    ("Helsinki -> Tallinn", ["HEL", "TAL"], 85),
    ("Tallinn -> Riga", ["TAL", "RIG"], 310),
    ("Riga -> Vilnius", ["RIG", "VIL"], 295),
    ("Vilnius -> Minsk", ["VIL", "MIN"], 185),
    ("Warsaw -> Krakow", ["WAR", "KRA"], 295),
    ("Prague -> Vienna", ["PRG", "VIE"], 335),
    ("Vienna -> Bratislava", ["VIE", "BRA"], 80),
    ("Bratislava -> Budapest", ["BRA", "BUD"], 200),
    ("Budapest -> Zagreb", ["BUD", "ZAG"], 345),
    ("Ljubljana -> Venice", ["LJU", "VEN"], 245),
    ("Zagreb -> Ljubljana", ["ZAG", "LJU"], 140),
    ("Sarajevo -> Belgrade", ["SJJ", "BEL"], 295),
    ("Belgrade -> Sofia", ["BEL", "SOF"], 395),
    ("Skopje -> Belgrade", ["SKP", "BEL"], 430),
    ("Tirana -> Sarajevo", ["TIR", "SJJ"], 390),
    ("Athens -> Skopje", ["ATH", "SKP"], 700),
    ("Sofia -> Istanbul", ["SOF", "IST"], 550),
    ("Bucharest -> Chisinau", ["BUC", "CHS"], 450),
    ("Istanbul -> Ankara", ["IST", "ANK"], 450),
    ("Ankara -> Istanbul", ["ANK", "IST"], 450),
    ("Chisinau -> Odesa", ["CHS", "ODE"], 180),
    ("Kyiv -> Voronezh", ["KYI", "VOR"], 650),
    ("Minsk -> Vilnius", ["MIN", "VIL"], 185),
    ("Moscow -> Tver", ["MOS", "TVE"], 170),
]


TRAJETS.extend(
    {
        "title": title,
        "kind": "court",
        "cities": cities,
        "distance_hint": distance,
        "reward_xp": max(45, min(120, round(distance / 5))),
        "reward_coins": max(22, min(58, round(distance / 12))),
        "description": "Trajet facile de depart depuis une capitale.",
    }
    for title, cities, distance in STARTER_TRAJETS
    if not any(existing["title"] == title for existing in TRAJETS)
)


SPECIAL_CARDS = [
    ("radar", "malus", "Radar", "Peu commun", "Vous avez ete flashe: rejoignez la capitale la plus proche pour regler 35 gold.", {"requires_capital_fine": 35, "durability": 0, "event": "radar"}),
    ("crevaison", "malus", "Crevaison", "Commun", "Rendez-vous au garage le plus proche. Tant que ce n'est pas repare, -5% durabilite par tour.", {"mechanical_malus": "flat_tire", "requires_garage_repair": True, "durability_loss_percent_per_turn": 5, "durability": 0, "event": "crevaison"}),
    ("panne-moteur", "malus", "Panne moteur", "Rare", "Le moteur fatigue: -10% durabilite par tour jusqu'au garage ou a un ami mecano.", {"mechanical_malus": "engine", "requires_garage_repair": True, "durability_loss_percent_per_turn": 10, "durability": 0, "event": "panne_moteur"}),
    ("reservoir-perce", "malus", "Reservoir perce", "Peu commun", "Vous perdez 30% du carburant restant.", {"fuel_percent": -30, "durability": 0, "event": "reservoir"}),
    ("mamie-enterrement", "malus", "Mamie est decedee", "Rare", "Allez a son enterrement: la famille vous appelle vers une ville eloignee.", {"xp": -5, "dice_remaining": -1, "durability": 0, "event": "enterrement"}),
    ("radar-automatique", "malus", "Radar automatique", "Commun", "Le flash part tout seul: -20 XP.", {"xp": -20, "durability": 0, "event": "radar_auto"}),
    ("pluie-battante", "malus", "Pluie battante", "Commun", "La visibilite chute: -1 case sur le de en cours.", {"dice_remaining": -1, "durability": 0, "event": "pluie"}),
    ("bouchon-monstrueux", "malus", "Bouchon monstrueux", "Rare", "Deux tours sautes dans un trafic infernal.", {"skip_turns": 2, "durability": 0, "event": "bouchon"}),
    ("essence-contaminee", "malus", "Essence contaminee", "Rare", "Consommation x2 pendant 2 tours.", {"fuel_multiplier": 2, "turns": 2, "durability": 0, "event": "essence_contaminee"}),
    ("facture-garage", "malus", "Facture de garage", "Commun", "Votre derniere reparation n'etait pas gratuite: -15 gold.", {"coins": -15, "durability": 0, "event": "facture"}),
    ("vol-gps", "malus", "Vol de GPS", "Peu commun", "Un joueur vous vole votre GPS: -10 gold pour vous, +10 gold pour lui.", {"steal_gold_random": 10, "durability": 0, "event": "gps"}),
    ("controle-technique", "malus", "Controle technique surprise", "Peu commun", "Un controle bloque la Twingo: -8 durabilite.", {"durability": -8, "event": "controle"}),
    ("kit-anticrevaison", "bonus", "Kit anticrevaison", "Commun", "Annule une crevaison active.", {"resolve_mechanical": "flat_tire", "durability": 0, "successful_events": 1, "event": "kit"}),
    ("anniversaire", "bonus", "C'est votre anniversaire", "Rare", "Chaque joueur vous offre 20 gold.", {"coins_from_each_player": 20, "durability": 0, "successful_events": 1, "event": "anniversaire"}),
    ("essence-eco", "bonus", "Essence Eco", "Peu commun", "-25% consommation pendant 2 tours.", {"fuel_discount_percent": 25, "turns": 2, "durability": 0, "successful_events": 1, "event": "eco"}),
    ("route-secrete", "bonus", "Route secrete", "Peu commun", "+1 case au choix sur le de en cours.", {"dice_remaining": 1, "durability": 0, "successful_events": 1, "event": "route_secrete"}),
    ("ami-mecano", "bonus", "Ami mecano", "Rare", "Supprime un malus mecanique actif.", {"resolve_mechanical": "any", "durability": 0, "successful_events": 1, "event": "mecano"}),
    ("demi-plein-offert", "bonus", "Demi-plein offert", "Commun", "+50% essence.", {"fuel_capacity_percent": 50, "durability": 0, "successful_events": 1, "event": "demi_plein"}),
    ("sponsor-local", "bonus", "Sponsor local", "Peu commun", "Un commerce local vous sponsorise: +30 gold.", {"coins": 30, "durability": 0, "successful_events": 1, "event": "sponsor"}),
    ("livraison-amazon", "bonus", "Livraison Amazon", "Peu commun", "Livrez vite un colis dans une capitale proche: avance immediate de +40 gold.", {"coins": 40, "durability": 0, "successful_events": 1, "event": "amazon"}),
    ("ami-perdu", "bonus", "Ami perdu", "Peu commun", "Un ami vous demande de venir le chercher: +30 XP si vous acceptez le detour.", {"xp": 30, "durability": 0, "successful_events": 1, "event": "ami_perdu"}),
    ("defi-twingo-club", "bonus", "Defi Twingo Club", "Rare", "Le club vous chauffe: +20 gold et +1 case si vous tentez le defi.", {"coins": 20, "dice_remaining": 1, "durability": 0, "successful_events": 1, "event": "defi"}),
    ("meteo-parfaite", "bonus", "Meteo parfaite", "Commun", "Le soleil vous porte chance: +2 cases au prochain deplacement.", {"dice_remaining": 2, "durability": 0, "successful_events": 1, "event": "meteo_parfaite"}),
    ("aire-de-repos", "bonus", "Aire de repos", "Commun", "Petite pause, grosse respiration: +8 durabilite.", {"durability": 8, "successful_events": 1, "event": "repos"}),
    ("cafe-serre", "bonus", "Cafe serre", "Commun", "Le conducteur est reveille: +10 XP.", {"xp": 10, "durability": 0, "successful_events": 1, "event": "cafe"}),
    ("klaxon-amical", "bonus", "Klaxon amical", "Commun", "Un salut de Twingo a Twingo: +8 gold et le moral remonte.", {"coins": 8, "durability": 1, "successful_events": 1, "event": "klaxon"}),
    ("creneau-parfait", "bonus", "Creneau parfait", "Commun", "La manoeuvre est magnifique: +1 case et +5 XP.", {"dice_remaining": 1, "xp": 5, "durability": 0, "successful_events": 1, "event": "creneau"}),
    ("autoradio-nostalgie", "bonus", "Autoradio bloque sur Nostalgie", "Commun", "Tout le monde chante, meme la boite a gants: +15 XP.", {"xp": 15, "durability": 0, "successful_events": 1, "event": "autoradio"}),
    ("sticker-93", "bonus", "Sticker 93", "Peu commun", "Un autocollant collector donne du style: +10 gold, +3 durabilite.", {"coins": 10, "durability": 3, "successful_events": 1, "event": "sticker_93"}),
    ("appel-de-phare-club", "bonus", "Appel de phare Twingo Club", "Peu commun", "Le club vous ouvre la voie: +1 case, +5 durabilite.", {"dice_remaining": 1, "durability": 5, "successful_events": 1, "event": "appel_phare"}),
]


EVENTS = [
    ("radar", "Radar", "malus", "Petit exces repere sur l'autoroute.", {"coins": -15, "xp": -5, "durability": -1}),
    ("bouchon", "Bouchon", "malus", "Ca klaxonne mais la Twingo garde le sourire.", {"fuel": -3, "durability": -3}),
    ("panne", "Panne", "malus", "Voyant allume: le prochain vrai arret doit etre un garage.", {"repairs_needed": 1, "durability": -15}),
    ("garage", "Garage obligatoire", "malus", "Controle technique improvise.", {"repairs_needed": 1, "durability": -8}),
    ("covoiture", "Covoitureurs", "bonus", "Des passagers laissent un bon pourboire.", {"coins": 25, "xp": 15, "durability": 3, "successful_events": 1}),
    ("courses", "Courses a faire", "bonus", "Detour utile, mini-objectif coche.", {"xp": 20, "durability": 4, "successful_events": 1}),
]


ACHIEVEMENTS = [
    ("premier-trajet", "Premier trajet", "Completer une carte Trajet.", "completed_trajets", 1, 30),
    ("routard-1000", "Routard 1000", "Parcourir 1000 km.", "distance_km", 1000, 40),
    ("anti-galere", "Anti-galere", "Reussir 3 evenements bonus.", "successful_events", 3, 50),
]


def table_has_rows(conn, table_name):
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return row["count"] > 0


def seed_database(conn):
    skin_slugs = [skin["slug"] for skin in SKINS]
    skin_placeholders = ",".join("?" for _ in skin_slugs)
    old_skin_ids = [
        row["id"]
        for row in conn.execute(
            f"SELECT id FROM skins WHERE slug NOT IN ({skin_placeholders})",
            skin_slugs,
        ).fetchall()
    ] if skin_slugs else []
    if old_skin_ids:
        old_placeholders = ",".join("?" for _ in old_skin_ids)
        conn.execute(
            f"UPDATE inventory SET status = 'archived' WHERE item_type = 'skin' AND item_id IN ({old_placeholders})",
            old_skin_ids,
        )
        conn.execute(f"DELETE FROM skins WHERE id IN ({old_placeholders})", old_skin_ids)
    conn.executemany(
        """
        INSERT INTO skins (slug, name, rarity, inspired_by, description, palette_json, min_level, asset)
        VALUES (:slug, :name, :rarity, :inspired_by, :description, :palette_json, :min_level, :asset)
        ON CONFLICT(slug) DO UPDATE SET
            name = excluded.name,
            rarity = excluded.rarity,
            inspired_by = excluded.inspired_by,
            description = excluded.description,
            palette_json = excluded.palette_json,
            min_level = excluded.min_level,
            asset = excluded.asset
        """,
        [
            {
                **skin,
                "palette_json": json.dumps(skin["palette"]),
            }
            for skin in SKINS
        ],
    )

    conn.executemany(
        """
        INSERT INTO map_nodes (id, city, country, x, y, node_type, resource_json, weather)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            city = excluded.city,
            country = excluded.country,
            x = excluded.x,
            y = excluded.y,
            node_type = excluded.node_type,
            resource_json = excluded.resource_json,
            weather = excluded.weather
        """,
        [scaled_node(node) for node in MAP_NODES],
    )

    conn.execute("DELETE FROM roads")
    conn.executemany(
        """
        INSERT INTO roads (from_node_id, to_node_id, road_type, distance_km, cost_coins, fuel_cost, event_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ROADS,
    )

    for trajet in TRAJETS:
        existing = conn.execute("SELECT id FROM trajets WHERE title = ?", (trajet["title"],)).fetchone()
        if not existing:
            cursor = conn.execute(
                """
                INSERT INTO trajets (title, kind, city_ids_json, distance_hint, reward_xp, reward_coins, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trajet["title"],
                    trajet["kind"],
                    json.dumps(trajet["cities"]),
                    trajet["distance_hint"],
                    trajet["reward_xp"],
                    trajet["reward_coins"],
                    trajet["description"],
                ),
            )
            trajet_id = cursor.lastrowid
        else:
            trajet_id = existing["id"]

        conn.execute(
            """
            INSERT OR IGNORE INTO cards (slug, type, name, rarity, description, effect_json, trajet_id)
            VALUES (?, 'trajet', ?, ?, ?, ?, ?)
            """,
            (
                "trajet-" + trajet["title"].lower().replace(" -> ", "-").replace(" ", "-"),
                trajet["title"],
                "Long" if trajet["kind"] == "long" else "Court",
                trajet["description"],
                json.dumps({"required_cities": trajet["cities"]}),
                trajet_id,
            ),
        )

    special_slugs = [card[0] for card in SPECIAL_CARDS]
    placeholders = ",".join("?" for _ in special_slugs)
    old_special_ids = [
        row["id"]
        for row in conn.execute(
            f"SELECT id FROM cards WHERE type IN ('bonus', 'malus') AND slug NOT IN ({placeholders})",
            special_slugs,
        ).fetchall()
    ]
    if old_special_ids:
        old_placeholders = ",".join("?" for _ in old_special_ids)
        conn.execute(
            f"UPDATE inventory SET status = 'archived' WHERE item_type = 'card' AND item_id IN ({old_placeholders})",
            old_special_ids,
        )
        conn.execute(f"DELETE FROM cards WHERE id IN ({old_placeholders})", old_special_ids)

    for slug, card_type, name, rarity, description, effect in SPECIAL_CARDS:
        conn.execute(
            """
            INSERT OR IGNORE INTO cards (slug, type, name, rarity, description, effect_json, trajet_id)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (slug, card_type, name, rarity, description, json.dumps(effect)),
        )
        conn.execute(
            """
            UPDATE cards
            SET type = ?, name = ?, rarity = ?, description = ?, effect_json = ?, trajet_id = NULL
            WHERE slug = ?
            """,
            (card_type, name, rarity, description, json.dumps(effect), slug),
        )

    for slug, name, event_type, description, effect in EVENTS:
        conn.execute(
            """
            INSERT OR IGNORE INTO events (slug, name, event_type, description, effect_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (slug, name, event_type, description, json.dumps(effect)),
        )
        conn.execute(
            """
            UPDATE events
            SET name = ?, event_type = ?, description = ?, effect_json = ?
            WHERE slug = ?
            """,
            (name, event_type, description, json.dumps(effect), slug),
        )

    if not table_has_rows(conn, "achievements"):
        conn.executemany(
            """
            INSERT INTO achievements (slug, name, description, condition_key, threshold, reward_xp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ACHIEVEMENTS,
        )
