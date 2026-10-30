# Downtown Raleigh 3D

An interactive 3D model of downtown Raleigh, North Carolina, that runs in any modern browser. It's built with [Three.js](https://threejs.org/) on [OpenStreetMap](https://www.openstreetmap.org/) data.

- **About 3,700 buildings** and **7,000 road segments** cover an area of roughly 2.6 × 2.8 km centered on the NC State Capitol.
- **16 labeled landmarks** have hand-built details (crowns, domes, signs). Click one to fly to it and read about it.
- **Guided tour**: the camera flies from landmark to landmark.
- **Time of day**: a slider (or the play button) moves the sun across a late-October day. At night, windows, streetlights, stars and building crowns light up.
- **Works on phones**: on narrow screens the controls become a bottom sheet.

The whole app is one self-contained HTML file with the map data inlined. The only things it loads at runtime are Three.js from cdn.jsdelivr.net and the fonts from Google Fonts.

## Quick start

You need **Python 3** (standard library only, no packages to install) and **Node.js** for the preview server.

```bash
python tools/build.py     # builds index.html from the source and data
node tools/serve.mjs      # serves it at http://localhost:8137
```

Open <http://localhost:8137> in your browser. You can pass a different port to the server: `node tools/serve.mjs 9000`.

You can also skip the server and double-click `index.html`. You still need an internet connection, because Three.js and the fonts load from CDNs.

> Don't use `python -m http.server` to preview the app. In this environment it cuts the 1.3 MB page off partway through.

## Using the app

| Control | What it does |
|---|---|
| Left-drag / one finger | Orbit the camera |
| Right-drag / two fingers | Pan |
| Scroll / pinch | Zoom |
| Click a landmark (map or list) | Fly to it and open its info card |
| **Time of day** slider | Set the hour; the ▶ button plays through a day |
| **Start tour** | Visit each landmark in turn (click again to stop) |
| **Reset view** | Return to the starting camera |
| **Labels** | Show or hide landmark labels |

## Project layout

```
src/raleigh.html     The source: CSS, UI markup and the Three.js module. Edit this.
tools/fetch_osm.py   Turns OSM data into data/raleigh.json; holds height fixes and the landmark list
tools/build.py       Inlines the data into the source and writes the outputs below
tools/serve.mjs      Small static server for local preview (default port 8137)
data/osm_raw.json    Cached raw Overpass API response
data/raleigh.json    Compact scene data (buildings, parts, roads, parks, trees, landmarks)
index.html           GENERATED: full page for local use
build/artifact.html  GENERATED: same page without the <html>/<head>/<body> wrapper, for publishing
```

Never edit `index.html` or `build/artifact.html` by hand. Change `src/raleigh.html` (or the data) and rebuild.

## Development workflow

### Changing the app

1. Edit `src/raleigh.html`.
2. Run `python tools/build.py`.
3. Reload the page in the browser (the server reads files from disk on each request, so you don't need to restart it).

### Changing the data

The building heights, height fixes and landmark list (name, height, description, style) live in `tools/fetch_osm.py`.

```bash
python tools/fetch_osm.py             # regenerate data/raleigh.json from the cached raw data
python tools/fetch_osm.py --refresh   # download fresh data from Overpass (tries several mirrors)
python tools/build.py                 # then rebuild the page
```

To find a building's OSM id for a new landmark or height fix, click the building on [openstreetmap.org](https://www.openstreetmap.org/). Ways use the prefix `w` and relations use `r`, for example `w268750429`.

### Checking a change

1. Open the browser console and look for `THREE.WebGLProgram` errors. A shader that fails to compile makes its mesh silently disappear.
2. Set the time to about 8:30 PM to check the night lighting.
3. Click a landmark to check the fly-to and the info card.
4. Check the layout at a phone width (375px) with your browser's device toolbar.

## How it works

- **Coordinates** are in meters from the NC State Capitol (35.78040°N, 78.63915°W): +x is east, +z is south, y is up.
- **Buildings** are a single merged mesh. Windows are drawn procedurally in a patched `MeshStandardMaterial` shader, so the app uses no textures. Each building gets a window style (punched windows, curtain wall, parking deck or none) and a random seed.
- **Roads** are one ribbon mesh. Lane markings are drawn in the shader from the distance along the road and the offset across it.
- **Lighting**: `setTime()` works out the sun's position for Raleigh in late October. It drives the sky shader, the sun or moon light, fog, exposure, window and street lights, and the stars. The environment map is regenerated from the sky as the time changes.
- **OSM cleanup**: when OSM has a building outline and also detailed `building:part`s, the fetch script drops the outline so the shapes don't overlap and flicker.

See [CLAUDE.md](CLAUDE.md) for more detailed implementation notes and known gotchas.

## Data and license

Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the Open Database License (ODbL). The app shows this attribution on screen, and the license requires that it stay visible.

A few heights are corrected by hand where the OSM data is incomplete or out of date (for example, FNB Tower). The Eastern (2022) isn't named in OSM yet, so it isn't in the model.
