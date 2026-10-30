"""Endpoint pairs monitored by the collector and displayed in the dashboard."""

ROADS = [
    {
        "id": "ubungo",
        "name": "Morogoro Rd (Ubungo)",
        "start": "-6.7978,39.2201",
        "end": "-6.8040,39.2300",
    },
    {
        "id": "mwenge",
        "name": "Bagamoyo Rd (Mwenge)",
        "start": "-6.7744,39.2431",
        "end": "-6.7631,39.2489",
    },
    {
        "id": "selander",
        "name": "Ali Hassan Mwinyi",
        "start": "-6.7950,39.2750",
        "end": "-6.8050,39.2850",
    },
    {
        "id": "tazara",
        "name": "Nyerere Rd (Tazara)",
        "start": "-6.8288,39.2600",
        "end": "-6.8400,39.2480",
    },
    {
        "id": "mandela_buguruni",
        "name": "Mandela Rd (Port Link)",
        "start": "-6.8285,39.2435",
        "end": "-6.8335,39.2620",
    },
    {
        "id": "kilwa_mbagala",
        "name": "Kilwa Rd (Mbagala)",
        "start": "-6.9050,39.2700",
        "end": "-6.8750,39.2800",
    },
    {
        "id": "old_bagamoyo",
        "name": "Old Bagamoyo Rd (Victoria)",
        "start": "-6.7720,39.2550",
        "end": "-6.7820,39.2650",
    },
    {
        "id": "sam_nujoma",
        "name": "Sam Nujoma Rd (Mwenge-Ubungo)",
        "start": "-6.7755,39.2435",
        "end": "-6.7975,39.2205",
    },
    {
        "id": "uhuru_street",
        "name": "Uhuru Street (Ilala)",
        "start": "-6.8220,39.2550",
        "end": "-6.8155,39.2820",
    },
    {
        "id": "posta_to_tegeta",
        "name": "Posta to Tegeta (Bagamoyo Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.6430,39.1550",
    },
    {
        "id": "posta_to_kimara",
        "name": "Posta to Kimara (Morogoro Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.7800,39.1500",
    },
    {
        "id": "posta_to_gongolamboto",
        "name": "Posta to Gongo la Mboto (Nyerere Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.8850,39.1670",
    },
    {
        "id": "tabata_dampo",
        "name": "Tabata Road (Mandela to Segerea)",
        "start": "-6.8150,39.2320",
        "end": "-6.8300,39.2050",
    },
    {
        "id": "kamata_gerezani",
        "name": "Kamata / Gerezani (Port Entry)",
        "start": "-6.8280,39.2780",
        "end": "-6.8180,39.2850",
    },
    {
        "id": "changombe_road",
        "name": "Chang'ombe Road (Temeke)",
        "start": "-6.8350,39.2700",
        "end": "-6.8550,39.2650",
    },
    {
        "id": "morocco_intersection",
        "name": "Kawawa Rd (Morocco to Kinondoni)",
        "start": "-6.7820,39.2630",
        "end": "-6.7950,39.2580",
    },
    {
        "id": "kigogo_roundabout",
        "name": "Kawawa Rd (Kigogo)",
        "start": "-6.8120,39.2550",
        "end": "-6.8220,39.2500",
    },
    {
        "id": "fire_upanga",
        "name": "UN Road (Fire to Upanga)",
        "start": "-6.8120,39.2780",
        "end": "-6.8020,39.2720",
    },
    {
        "id": "mwai_kibaki",
        "name": "Mwai Kibaki Rd (Kawe to Mikocheni)",
        "start": "-6.7450,39.2350",
        "end": "-6.7650,39.2500",
    },
    {
        "id": "sinza_mori",
        "name": "Sinza Road (Mori to Bamaga)",
        "start": "-6.7780,39.2350",
        "end": "-6.7700,39.2450",
    },
    {
        "id": "goba_massana",
        "name": "Goba Road (Massana to Goba Center)",
        "start": "-6.7250,39.2150",
        "end": "-6.7150,39.1850",
    },
]

ROAD_MAP = {road["id"]: road["name"] for road in ROADS}
