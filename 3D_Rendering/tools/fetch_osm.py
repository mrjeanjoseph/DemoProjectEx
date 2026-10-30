"""Download downtown Raleigh map data from OpenStreetMap (Overpass API) and
write a compact scene file to data/raleigh.json.

Usage:  python tools/fetch_osm.py            (uses data/osm_raw.json if present)
        python tools/fetch_osm.py --refresh  (re-download from Overpass)
"""
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "osm_raw.json"
OUT = ROOT / "data" / "raleigh.json"

# South, West, North, East
BBOX = (35.7660, -78.6530, 35.7900, -78.6270)
# Origin: NC State Capitol
LAT0, LON0 = 35.78040, -78.63915
M_PER_DEG_LAT = 110_574.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT0))

QUERY = f"""
[out:json][timeout:90];
(
  way["building"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  relation["building"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["building:part"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["highway"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["leisure"~"park|garden|pitch"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["landuse"~"grass|recreation_ground"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  relation["leisure"="park"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["natural"="water"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  node["natural"="tree"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out geom;
"""

ROAD_WIDTH = {
    "motorway": 18, "trunk": 16, "primary": 14, "secondary": 12, "tertiary": 10,
    "unclassified": 8, "residential": 8, "living_street": 6, "service": 5,
    "primary_link": 8, "secondary_link": 7, "tertiary_link": 6,
    "pedestrian": 6, "footway": 2.5, "cycleway": 2.5, "path": 2, "steps": 2,
}
ROAD_CLASS = {  # 0 = major road, 1 = minor road, 2 = pedestrian
    "motorway": 0, "trunk": 0, "primary": 0, "secondary": 0, "tertiary": 0,
    "primary_link": 0, "secondary_link": 0, "tertiary_link": 0,
    "unclassified": 1, "residential": 1, "living_street": 1, "service": 1,
    "pedestrian": 2, "footway": 2, "cycleway": 2, "path": 2, "steps": 2,
}


MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


# Corrections where OSM lacks or understates heights (m), from public height lists.
OVERRIDES = {
    "w47760005": {"h": 62, "n": "Raleigh Marriott City Center"},
    "w323758992": {"h": 65, "n": "Sheraton Raleigh Hotel"},
    "w1563063472": {"h": 109, "n": "FNB Tower"},
    "w1064097333": {"h": 83},
    "w310168480": {"h": 61},
    "w135692673": {"h": 24},
    "w47759870": {"h": 22},
    "w47663703": {"h": 13},
    "w607928709": {"h": 12},
}

# Landmarks shown in the UI. `id` = OSM element; `style` = extra hand-built detail.
LANDMARKS = [
    {"id": "w268750429", "name": "PNC Plaza", "style": "pnc", "h": 164,
     "info": "Raleigh's tallest building: 538 ft, 32 floors, completed 2008. Its stepped glass crown glows at night."},
    {"id": "w297829070", "name": "Two Hannover Square", "style": "pyramid", "h": 131,
     "info": "431 ft, 29 floors (1991). Known for its peaked roof at the south end of Fayetteville Street."},
    {"id": "w297829069", "name": "Wells Fargo Capitol Center", "style": "stepped", "h": 122,
     "info": "150 Fayetteville St: 400 ft, 30 floors (1990). It faces the Capitol at the north end of Fayetteville Street."},
    {"id": "w1563063472", "name": "FNB Tower", "style": "crown", "h": 109,
     "info": "358 ft, 22 floors (2019); it was planned as Charter Square North. Apartments sit above the offices."},
    {"id": "w47760059", "name": "One Progress Plaza", "style": None, "h": 84,
     "info": "298 ft, 21 floors (1977). Once the headquarters of Progress Energy."},
    {"id": "r4144751", "name": "Red Hat Tower", "style": "redhat", "h": 87,
     "info": "286 ft, 19 floors (2004). Headquarters of the open-source software company Red Hat."},
    {"id": "w47760030", "name": "One City Plaza", "style": None, "h": 88,
     "info": "289 ft, 17 floors (1985), formerly One Bank of America Plaza. (Raleigh's current Bank of America Tower is in North Hills, about 8 km north.)"},
    {"id": "w47760005", "name": "Raleigh Marriott City Center", "style": None, "h": 62,
     "info": "202 ft, 17 floors (2008). The convention hotel facing City Plaza at 500 Fayetteville St."},
    {"id": "w323758992", "name": "Sheraton Raleigh Hotel", "style": None, "h": 65,
     "info": "213 ft, 17 floors (1982), on Salisbury Street."},
    {"id": "w454126369", "name": "Charter Square", "style": None, "h": 65,
     "info": "213 ft, 11 floors (2015), at the south end of Fayetteville Street near the Convention Center."},
    {"id": "w297829073", "name": "SkyHouse Raleigh", "style": None, "h": 80,
     "info": "264 ft, 23-floor apartment tower (2015) on Blount Street."},
    {"id": "w47776449", "name": "Hotel Indigo (the Round Tower)", "style": None, "h": 73,
     "info": "A 20-floor cylindrical hotel from 1969, long known as the Holiday Inn \"round tower\" on Hillsborough St."},
    {"id": "w47663703", "name": "NC State Capitol", "style": "capitol", "h": 13,
     "info": "Greek Revival capitol completed in 1840, with a copper dome. Fayetteville Street runs south from its doors."},
    {"id": "w135692673", "name": "Raleigh Convention Center", "style": None, "h": 24,
     "info": "500,000 sq ft convention center, opened in 2008."},
    {"id": "w47759870", "name": "Martin Marietta Center for the Performing Arts", "style": None, "h": 22,
     "info": "Performing arts complex at the south end of Fayetteville Street, formerly the Progress Energy / Duke Energy Center."},
    {"id": "w607928709", "name": "Raleigh Union Station", "style": None, "h": 12,
     "info": "Amtrak station in the Warehouse District, opened in 2018 in a renovated warehouse."},
]


def point_in(pt, ring):
    x, z = pt
    inside = False
    for i in range(len(ring)):
        x1, z1 = ring[i]
        x2, z2 = ring[i - 1]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            inside = not inside
    return inside


def centroid(r):
    return [sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)]


def fetch():
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    raw = None
    for url in MIRRORS * 2:
        try:
            req = urllib.request.Request(
                url, data=data, headers={"User-Agent": "raleigh-3d-demo/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            print(f"  ok: {url}")
            break
        except Exception as e:  # mirror busy / unreachable: try the next one
            print(f"  {url}: {e}")
    if raw is None:
        sys.exit("All Overpass mirrors failed")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_bytes(raw)
    return json.loads(raw)


def proj(pt):
    x = (pt["lon"] - LON0) * M_PER_DEG_LON
    z = -(pt["lat"] - LAT0) * M_PER_DEG_LAT  # north = -z (three.js convention)
    return [round(x, 1), round(z, 1)]


def parse_len(v):
    if not v:
        return None
    m = re.match(r"\s*([\d.]+)\s*(ft|')?", v)
    if not m:
        return None
    n = float(m.group(1))
    return n * 0.3048 if m.group(2) else n


def ring_area(r):
    a = 0.0
    for i in range(len(r)):
        x1, z1 = r[i]
        x2, z2 = r[(i + 1) % len(r)]
        a += x1 * z2 - x2 * z1
    return a / 2


def clean_ring(coords):
    r = [proj(p) for p in coords]
    if len(r) > 1 and r[0] == r[-1]:
        r = r[:-1]
    return r if len(r) >= 3 else None


def join_outer(members):
    """Stitch relation 'outer' way segments into closed rings."""
    segs = [[(p["lat"], p["lon"]) for p in m["geometry"]]
            for m in members if m.get("role") == "outer" and m.get("geometry")]
    rings = []
    while segs:
        ring = segs.pop(0)
        changed = True
        while ring[0] != ring[-1] and changed:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                elif s[-1] == ring[-1]:
                    ring += s[::-1][1:]
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if ring[0] == ring[-1]:
            rings.append([{"lat": a, "lon": b} for a, b in ring])
    return rings


def height_of(t):
    h = parse_len(t.get("height")) or parse_len(t.get("building:height"))
    if h is None and t.get("building:levels"):
        try:
            h = float(t["building:levels"]) * 3.6 + 2
        except ValueError:
            pass
    if h is None:
        kind = t.get("building", "yes")
        h = {"house": 8, "garage": 4, "shed": 3, "roof": 6, "church": 16,
             "parking": 14, "garages": 4, "carport": 4}.get(kind, 11)
    minh = parse_len(t.get("min_height")) or 0
    if minh == 0 and t.get("building:min_level"):
        try:
            minh = float(t["building:min_level"]) * 3.6
        except ValueError:
            pass
    return round(h, 1), round(minh, 1)


def main():
    if "--refresh" in sys.argv or not RAW.exists():
        print("Downloading from Overpass...")
        osm = fetch()
    else:
        osm = json.loads(RAW.read_text(encoding="utf-8"))

    buildings, parts, roads, parks, water, trees = [], [], [], [], [], []
    for el in osm["elements"]:
        t = el.get("tags", {})
        if el["type"] == "node":
            if t.get("natural") == "tree":
                trees.append(proj(el))
            continue
        if el["type"] == "way":
            rings = [el["geometry"]] if el.get("geometry") else []
        else:
            rings = join_outer(el.get("members", []))

        if "building" in t or "building:part" in t:
            is_part = "building:part" in t and "building" not in t
            if t.get("building") in ("no",) or t.get("building:part") == "no":
                continue
            h, minh = height_of(t)
            for g in rings:
                r = clean_ring(g)
                if not r or abs(ring_area(r)) < 4:
                    continue
                b = {"id": f'{el["type"][0]}{el["id"]}', "p": r, "h": h}
                if minh:
                    b["m"] = minh
                if t.get("name"):
                    b["n"] = t["name"]
                if t.get("building") in ("parking",) or t.get("parking") == "multi-storey":
                    b["k"] = "parking"
                elif t.get("building") in ("house", "detached", "residential", "apartments"):
                    b["k"] = "res"
                if t.get("building:colour"):
                    b["c"] = t["building:colour"]
                (parts if is_part else buildings).append(b)
        elif "highway" in t and el["type"] == "way":
            hw = t["highway"]
            if hw not in ROAD_WIDTH or t.get("area") == "yes":
                continue
            if t.get("tunnel") == "yes":
                continue
            w = ROAD_WIDTH[hw]
            if t.get("lanes"):
                try:
                    w = max(w, int(t["lanes"]) * 3.4)
                except ValueError:
                    pass
            road = {"p": [proj(p) for p in el["geometry"]], "w": w, "c": ROAD_CLASS[hw]}
            if t.get("name"):
                road["n"] = t["name"]
            roads.append(road)
        elif t.get("natural") == "water":
            for g in rings:
                r = clean_ring(g)
                if r:
                    water.append(r)
        else:
            for g in rings:
                r = clean_ring(g)
                if r and abs(ring_area(r)) > 30:
                    parks.append(r)

    for b in buildings + parts:
        o = OVERRIDES.get(b["id"])
        if o:
            b["h"] = o["h"]
            if "n" in o:
                b["n"] = o["n"]

    # OSM often maps an outline plus detailed building:parts (or a taller
    # building inside a podium outline). Drop the outer one when an inner shape
    # at least as tall covers a decent share of it, to avoid z-fighting walls.
    shapes = buildings + parts
    for b in shapes:
        b["_a"] = abs(ring_area(b["p"]))
        b["_c"] = centroid(b["p"])
    drop = set()
    for outer in buildings:
        for inner in shapes:
            if inner is outer or inner["_a"] >= outer["_a"]:
                continue
            if inner["h"] >= outer["h"] - 0.5 and inner["_a"] > 0.15 * outer["_a"] \
                    and point_in(inner["_c"], outer["p"]):
                drop.add(outer["id"])
                break
    buildings = [b for b in buildings if b["id"] not in drop]
    for b in shapes:
        del b["_a"], b["_c"]

    lm_out = []
    by_id = {b["id"]: b for b in buildings + [p for p in parts]}
    raw_by_id = {f'{e["type"][0]}{e["id"]}': e for e in osm["elements"]}
    for l in LANDMARKS:
        src = by_id.get(l["id"])
        ring = src["p"] if src else None
        if ring is None and l["id"] in raw_by_id:  # dropped outline: use raw geometry
            e = raw_by_id[l["id"]]
            g = e.get("geometry") or (join_outer(e.get("members", [])) or [None])[0]
            ring = clean_ring(g) if g else None
        if ring is None:
            print("missing landmark", l["name"])
            continue
        c = centroid(ring)
        lm_out.append({**l, "x": round(c[0], 1), "z": round(c[1], 1), "p": ring})
    print(f"dropped {len(drop)} overlapping outlines")

    out = {
        "origin": [LAT0, LON0],
        "bbox": BBOX,
        "landmarks": lm_out,
        "buildings": buildings,
        "parts": parts,
        "roads": roads,
        "parks": parks,
        "water": water,
        "trees": trees,
    }
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"buildings={len(buildings)} parts={len(parts)} roads={len(roads)} "
          f"parks={len(parks)} water={len(water)} trees={len(trees)} "
          f"size={OUT.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
