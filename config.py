# config.py - Centralized Configuration for Dar Traffic Project

def parse_coords(coord_str):
    lat, lon = map(float, coord_str.split(","))
    return [lon, lat]

# 1. THE MASTER ROAD NETWORK
ROADS = [
    {
        "id": "ubungo",
        "name": "Morogoro Rd (Ubungo)",
        "start": "-6.7978,39.2201",
        "end": "-6.8040,39.2300",
        "dist": 1.8,
    },
    {
        "id": "mwenge",
        "name": "Bagamoyo Rd (Mwenge)",
        "start": "-6.7744,39.2431",
        "end": "-6.7631,39.2489",
        "dist": 1.5,
    },
    {
        "id": "selander",
        "name": "Ali Hassan Mwinyi",
        "start": "-6.7950,39.2750",
        "end": "-6.8050,39.2850",
        "dist": 1.4,
    },
    {
        "id": "tazara",
        "name": "Nyerere Rd (Tazara)",
        "start": "-6.8288,39.2600",
        "end": "-6.8400,39.2480",
        "dist": 1.7,
    },
    {
        "id": "mandela_buguruni",
        "name": "Mandela Rd (Port Link)",
        "start": "-6.8285,39.2435",
        "end": "-6.8335,39.2620",
        "dist": 2.5,
    },
    {
        "id": "kilwa_mbagala",
        "name": "Kilwa Rd (Mbagala)",
        "start": "-6.9050,39.2700",
        "end": "-6.8750,39.2800",
        "dist": 3.5,
    },
    {
        "id": "old_bagamoyo",
        "name": "Old Bagamoyo Rd (Victoria)",
        "start": "-6.7720,39.2550",
        "end": "-6.7820,39.2650",
        "dist": 1.5,
    },
    {
        "id": "sam_nujoma",
        "name": "Sam Nujoma Rd (Mwenge-Ubungo)",
        "start": "-6.7755,39.2435",
        "end": "-6.7975,39.2205",
        "dist": 4.2,
    },
    {
        "id": "uhuru_street",
        "name": "Uhuru Street (Ilala)",
        "start": "-6.8220,39.2550",
        "end": "-6.8155,39.2820",
        "dist": 3.2,
    },
    {
        "id": "posta_to_tegeta",
        "name": "Mega-Route: Posta to Tegeta (Bagamoyo Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.6430,39.1550",
        "dist": 22.0,
    },
    {
        "id": "posta_to_kimara",
        "name": "Mega-Route: Posta to Kimara (Morogoro Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.7800,39.1500",
        "dist": 17.5,
    },
    {
        "id": "posta_to_gongolamboto",
        "name": "Mega-Route: Posta to Gongo la Mboto (Nyerere Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.8850,39.1670",
        "dist": 18.0,
    },
    {
        "id": "tabata_dampo",
        "name": "Tabata Road (Mandela to Segerea)",
        "start": "-6.8150,39.2320",
        "end": "-6.8300,39.2050",
        "dist": 3.8,
    },
    {
        "id": "kamata_gerezani",
        "name": "Kamata / Gerezani (Port Entry)",
        "start": "-6.8280,39.2780",
        "end": "-6.8180,39.2850",
        "dist": 1.5,
    },
    {
        "id": "changombe_road",
        "name": "Chang'ombe Road (Temeke)",
        "start": "-6.8350,39.2700",
        "end": "-6.8550,39.2650",
        "dist": 2.5,
    },
    {
        "id": "morocco_intersection",
        "name": "Kawawa Rd (Morocco to Kinondoni)",
        "start": "-6.7820,39.2630",
        "end": "-6.7950,39.2580",
        "dist": 2.0,
    },
    {
        "id": "kigogo_roundabout",
        "name": "Kawawa Rd (Kigogo Choke)",
        "start": "-6.8120,39.2550",
        "end": "-6.8220,39.2500",
        "dist": 1.5,
    },
    {
        "id": "fire_upanga",
        "name": "UN Road (Fire to Upanga)",
        "start": "-6.8120,39.2780",
        "end": "-6.8020,39.2720",
        "dist": 1.2,
    },
    {
        "id": "mwai_kibaki",
        "name": "Mwai Kibaki Rd (Kawe to Mikocheni)",
        "start": "-6.7450,39.2350",
        "end": "-6.7650,39.2500",
        "dist": 3.5,
    },
    {
        "id": "sinza_mori",
        "name": "Sinza Road (Mori to Bamaga)",
        "start": "-6.7780,39.2350",
        "end": "-6.7700,39.2450",
        "dist": 2.0,
    },
    {
        "id": "goba_massana",
        "name": "Goba Road (Massana to Goba Center)",
        "start": "-6.7250,39.2150",
        "end": "-6.7150,39.1850",
        "dist": 4.0,
    },
]

# 2. DYNAMIC LOOKUP MAPS
ROAD_MAP = {r["id"]: r["name"] for r in ROADS}
REVERSE_ROAD_MAP = {r["name"]: r["id"] for r in ROADS}
TARGET_ROADS = [r["id"] for r in ROADS]
ROAD_PATHS = {r["id"]: [parse_coords(r["start"]), parse_coords(r["end"])] for r in ROADS}

ROAD_COORDS = {}
for r in ROADS:
    start_lat, start_lon = map(float, r["start"].split(","))
    end_lat, end_lon = map(float, r["end"].split(","))
    ROAD_COORDS[r["id"]] = {"lat": (start_lat + end_lat)/2, "lon": (start_lon + end_lon)/2}

# 3. ROUTE PLANNER GRAPH
ROUTES = {
    ("Kimara", "Posta / CBD"): {
        "Route 1 — Morogoro Rd Direct": ["posta_to_kimara", "ubungo"],
        "Route 2 — Via Sam Nujoma": ["sam_nujoma", "morocco_intersection", "tazara"],
    },
    ("Tegeta", "Posta / CBD"): {
        "Route 1 — Bagamoyo Rd Direct": ["posta_to_tegeta", "mwenge"],
        "Route 2 — Via Mwenge + Sam Nujoma": ["old_bagamoyo", "mwenge", "sam_nujoma"],
    },
    ("Mbagala", "Posta / CBD"): {
        "Route 1 — Kilwa Rd": ["kilwa_mbagala", "changombe_road"],
        "Route 2 — Mandela + Nyerere": ["mandela_buguruni", "tazara"],
    },
    ("Goba", "Posta / CBD"): {
        "Route 1 — Goba Rd + Kawawa": ["goba_massana", "morocco_intersection", "sam_nujoma"],
        "Route 2 — Via Mwenge": ["goba_massana", "mwenge"],
    },
    ("Morocco / Kinondoni", "Posta / CBD"): {
        "Route 1 — Kawawa Rd Direct": ["morocco_intersection", "sam_nujoma"],
        "Route 2 — Via Bagamoyo Rd": ["mwenge", "selander"],
    },
    ("Port / Bandarini", "Posta / CBD"): {
        "Route 1 — Mandela Rd": ["mandela_buguruni", "kamata_gerezani"],
        "Route 2 — Via Nyerere Rd": ["tazara", "uhuru_street"],
    },
    ("TAZARA / Kigamboni", "Posta / CBD"): {
        "Route 1 — Nyerere Rd Direct": ["tazara", "changombe_road"],
        "Route 2 — Via Mandela": ["mandela_buguruni", "tazara"],
    },
    ("Gongo la Mboto", "Posta / CBD"): {
        "Route 1 — Direct Corridor": ["posta_to_gongolamboto", "tazara"],
        "Route 2 — Via Tabata": ["tabata_dampo", "tazara"],
    },
    ("Sinza / Kinondoni", "Posta / CBD"): {
        "Route 1 — Sinza + Sam Nujoma": ["sinza_mori", "sam_nujoma"],
        "Route 2 — Via Kawawa": ["sinza_mori", "kigogo_roundabout", "uhuru_street"],
    },
    ("Kawe / Mikocheni", "Posta / CBD"): {
        "Route 1 — Mwai Kibaki + Old Bagamoyo": ["mwai_kibaki", "old_bagamoyo", "selander"],
        "Route 2 — Via Mwenge": ["mwai_kibaki", "mwenge", "sam_nujoma"],
    },
    
    # CROSS-CITY ROUTES
    ("Ubungo", "Mwenge / Makumbusho"): {
        "Route 1 — Sam Nujoma Direct": ["sam_nujoma"],
        "Route 2 — Via Sinza": ["sinza_mori", "mwenge"],
    },
    ("Tegeta", "Ubungo"): {
        "Route 1 — Bagamoyo Rd + Sam Nujoma": ["posta_to_tegeta", "mwenge", "sam_nujoma"],
        "Route 2 — Via Goba": ["goba_massana", "sam_nujoma"],
    },
    ("Posta / CBD", "Airport (JNIA)"): {
        "Route 1 — Nyerere Rd Direct": ["tazara", "posta_to_gongolamboto"],
        "Route 2 — Via Uhuru St & Mandela": ["uhuru_street", "mandela_buguruni", "tazara"],
    },
    ("Mwenge / Makumbusho", "Airport (JNIA)"): {
        "Route 1 — Sam Nujoma + Mandela": ["sam_nujoma", "mandela_buguruni", "tazara"],
        "Route 2 — Via Kawawa & Nyerere": ["morocco_intersection", "kigogo_roundabout", "tazara"],
    },
    ("Tabata", "Posta / CBD"): {
        "Route 1 — Uhuru St": ["tabata_dampo", "uhuru_street"],
        "Route 2 — Via Mandela & Nyerere": ["tabata_dampo", "mandela_buguruni", "tazara"],
    },
    ("Tabata", "Mwenge / Makumbusho"): {
        "Route 1 — Mandela + Sam Nujoma": ["tabata_dampo", "mandela_buguruni", "sam_nujoma"],
        "Route 2 — Via Kigogo & Kawawa": ["tabata_dampo", "kigogo_roundabout", "morocco_intersection"],
    },
    
    # LOGISTICS CORRIDORS
    ("Port / Bandarini", "Ubungo"): {
        "Route 1 — Mandela Rd": ["kamata_gerezani", "mandela_buguruni", "ubungo"],
    },
    ("Port / Bandarini", "Tegeta"): {
        "Route 1 — Via Mandela & Sam Nujoma": ["kamata_gerezani", "mandela_buguruni", "sam_nujoma", "mwenge", "posta_to_tegeta"],
        "Route 2 — Via Selander Bridge": ["kamata_gerezani", "selander", "old_bagamoyo", "posta_to_tegeta"],
    },
    ("Mbagala", "Airport (JNIA)"): {
        "Route 1 — Via Chang'ombe": ["kilwa_mbagala", "changombe_road", "tazara", "posta_to_gongolamboto"],
        "Route 2 — Via Mandela": ["kilwa_mbagala", "mandela_buguruni", "tazara", "posta_to_gongolamboto"],
    },
    
    # SUBURB TO SUBURB
    ("Kimara", "Mwenge / Makumbusho"): {
        "Route 1 — Sam Nujoma Traverse": ["posta_to_kimara", "sam_nujoma", "mwenge"],
        "Route 2 — Via Sinza": ["posta_to_kimara", "sinza_mori", "mwenge"],
    },
    ("Gongo la Mboto", "Ubungo"): {
        "Route 1 — Nyerere & Mandela": ["posta_to_gongolamboto", "mandela_buguruni", "ubungo"],
    },
    ("Mbagala", "Mwenge / Makumbusho"): {
        "Route 1 — Mandela to Sam Nujoma": ["kilwa_mbagala", "mandela_buguruni", "sam_nujoma", "mwenge"],
        "Route 2 — Via Kawawa Rd": ["kilwa_mbagala", "changombe_road", "kigogo_roundabout", "morocco_intersection", "mwenge"],
    },

    # REVERSE COMMUTE (CBD TO SUBURBS)
    ("Posta / CBD", "Kimara"): {
        "Route 1 — Morogoro Rd Direct": ["ubungo", "posta_to_kimara"],
        "Route 2 — Via Kawawa & Sam Nujoma": ["tazara", "morocco_intersection", "sam_nujoma", "posta_to_kimara"],
    },
    ("Posta / CBD", "Tegeta"): {
        "Route 1 — Bagamoyo Rd Direct": ["mwenge", "posta_to_tegeta"],
        "Route 2 — Via Sam Nujoma": ["sam_nujoma", "mwenge", "old_bagamoyo", "posta_to_tegeta"],
    },
    ("Posta / CBD", "Mbagala"): {
        "Route 1 — Kilwa Rd Direct": ["changombe_road", "kilwa_mbagala"],
        "Route 2 — Via Mandela": ["tazara", "mandela_buguruni", "kilwa_mbagala"],
    },
    ("Posta / CBD", "Goba"): {
        "Route 1 — Kawawa & Goba Rd": ["sam_nujoma", "morocco_intersection", "goba_massana"],
        "Route 2 — Via Bagamoyo Rd": ["mwenge", "goba_massana"],
    }
}
