"""Inline data/raleigh.json into src/raleigh.html.

Writes:
  index.html          full HTML document for opening locally (double-click works)
  build/artifact.html same page without the document wrapper, for publishing as a claude.ai Artifact
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "src" / "raleigh.html").read_text(encoding="utf-8")
data = (ROOT / "data" / "raleigh.json").read_text(encoding="utf-8").replace("</", "<\\/")
page = src.replace("__CITY_DATA__", data)

local = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
         "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
         "</head>\n<body>\n" + page + "\n</body>\n</html>\n")

for out, text in ((ROOT / "index.html", local), (ROOT / "build" / "artifact.html", page)):
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
