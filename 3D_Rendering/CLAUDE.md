# Downtown Raleigh 3D

An interactive 3D model of downtown Raleigh, NC, built with Three.js, that runs in any browser. It shows buildings and streets from OpenStreetMap, labeled landmarks with hand-built details, camera flights and tours, and a time-of-day slider that runs from day to night.

Published privately at https://claude.ai/artifact/NMqugzwQiT4utCvXx5KfaE. To update it, republish `build/artifact.html` so the URL stays the same.

## Layout

| Path | What it is |
|---|---|
| `src/raleigh.html` | **The source.** All CSS, UI markup and the Three.js module script. Edit this file. |
| `tools/fetch_osm.py` | Downloads OSM data with Overpass and writes `data/raleigh.json`. It also holds the height corrections (`OVERRIDES`) and the landmark list (`LANDMARKS`: name, info text, style). |
| `tools/build.py` | Inlines `data/raleigh.json` into the source and writes both outputs below. |
| `tools/serve.mjs` | A small Node static server for local preview (port 8137). |
| `data/osm_raw.json` | Cached raw Overpass response. It's reused unless you pass `--refresh`. |
| `data/raleigh.json` | Compact scene data: buildings, parts, roads, parks, trees and landmarks. |
| `index.html` | **Generated.** A full HTML document for local use (double-click to open). |
| `build/artifact.html` | **Generated.** The same page without `<!doctype>`/`<html>`/`<head>`/`<body>`, because the Artifact publisher adds its own wrapper. |

Never hand-edit `index.html` or `build/artifact.html`. Edit `src/raleigh.html` and rebuild.

## Commands

```bash
python tools/fetch_osm.py            # rebuild data/raleigh.json from the cached raw OSM data
python tools/fetch_osm.py --refresh  # re-download from Overpass (tries several mirrors)
python tools/build.py                # write index.html and build/artifact.html
node tools/serve.mjs                 # preview at http://localhost:8137
```

`.claude/launch.json` defines the `raleigh` preview config using the Node server. Don't use `python -m http.server` here: in this environment it cuts the 1.3 MB page off at about 56 KB.

## Data conventions

- Coordinates are in meters from the NC State Capitol (35.78040, -78.63915). **+x = east, +z = south** (north is -z), and y is up.
- The bounding box is about 2.6 × 2.8 km (`BBOX` in `fetch_osm.py`).
- Building ids are OSM ids with a type prefix: `w` for a way, `r` for a relation. Fields: `p` = ring, `h` = height, `m` = min height, `n` = name, `k` = kind (`parking`/`res`).
- OSM often maps a building outline plus detailed `building:part`s. The fetch script drops an outer outline when an inner shape at least as tall covers more than 15% of it, which prevents z-fighting.
- Landmark `h` is the real height and is shown in the UI as `hReal`. At runtime, `buildLandmarkDetails()` raises `l.h` for crowns, domes and signs so labels sit above them.

## Rendering notes (`src/raleigh.html`)

- Three.js **0.160.0** is loaded through an import map from cdn.jsdelivr.net. That's the only external script host. Fonts come from Google Fonts. The Artifact page blocks other hosts, so don't add any.
- All buildings are **one merged mesh**. Windows are drawn procedurally in a patched `MeshStandardMaterial` (`onBeforeCompile`), with no textures. Per-vertex attributes:
  - `aWall`: wall coordinates in meters (along the wall, height).
  - `aColor`: base color.
  - `aInfo`: isWall, seed, style, top. Style values: 0 = no windows, 1 = punched windows, 2 = curtain wall, 3 = parking deck.
- Roads use one ribbon mesh with markings drawn in the shader, from the `aRoad` attribute (distance along the road, offset across it, road class, half width).
- **GLSL gotcha:** `half` is a reserved word in GLSL ES 3.0. Using it as a variable name stops a shader from compiling and the mesh silently disappears.
- Flat layers (paved area, parks, roads) use `polygonOffset`, `depthWrite: false` and `renderOrder` to stack correctly over the ground.
- Time of day: `setTime(t)` computes the late-October sun position for Raleigh (declination -13°, solar noon about 1:00 PM). It drives the Sky shader, the sun or moon light, fog, exposure, `U.night` (window lights), streetlight glow, stars, the night sky dome and the crown glow materials.
- The environment map is regenerated from the sky with PMREM, debounced while the slider moves (`queueEnv`).
- Startup waits on `setTimeout`, not `requestAnimationFrame`, because browsers pause rAF in background tabs. A full build takes about 0.8 s. Per-step timings are stored in `canvas.dataset.timing`, and `canvas.dataset.ready` is set once the scene is ready.
- Label collisions: tags are placed in priority order (selected first, then tallest). Any tag that overlaps one already placed is hidden.

## UI / design

- Tokens live on `:root`, with dark variants under `prefers-color-scheme` and `[data-theme]`. The accent is oak green and `--glow` is sodium-lamp amber.
- Fonts: Big Shoulders Display for headings, IBM Plex Sans for body text, IBM Plex Mono for data.
- Phones (≤720px): the panel becomes a bottom sheet, the landmark list sits behind the "Landmarks" button, and the starting camera is farther back on portrait screens.
- Keep the OpenStreetMap attribution visible. The data's ODbL license requires it.

## Facts worth keeping straight

- There's no Bank of America Tower downtown; the one in Raleigh is in North Hills. Downtown's One City Plaza was formerly One Bank of America Plaza.
- FNB Tower (109 m) was planned as Charter Square North. OSM had it under that name at 11 m, so its height is set in `OVERRIDES`.
- The Eastern (115 m, 2022) isn't named in OSM yet, so it's missing from the model.

## Testing a change

1. `python tools/build.py`, then preview with the `raleigh` launch config.
2. Check the console for `THREE.WebGLProgram` shader errors.
3. Set `#time` to about 20.5 to check night lighting.
4. Click a landmark to check the fly-to and the info card.
5. Check at 375px width.
6. Republish `build/artifact.html` to the same artifact.
