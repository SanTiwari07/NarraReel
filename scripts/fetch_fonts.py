"""Download the bundled caption fonts from Google Fonts and write the manifest.

Developer script (needs `pip install fonttools`). It is NOT run by users: the fonts it produces
are committed under narrareel/assets/fonts/. Variable fonts are instanced into static files,
because libass cannot pick weights from variable fonts reliably.

For every family it checks that the licence text is the SIL OFL or Apache-2.0 and copies it
next to the fonts (WHAT_TO_DO.md section 5.9.3, policy rule 7).

Usage: python scripts/fetch_fonts.py [--out narrareel/assets/fonts]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

RAW = "https://raw.githubusercontent.com/google/fonts/main"


@dataclass
class Face:
    style: str  # display style, e.g. "Black"
    weight: int
    remote: str  # file name in the Google Fonts directory
    axes: dict[str, float] | None = None  # set => instance a variable font at these axes
    tags: list[str] = field(default_factory=list)


@dataclass
class Family:
    family: str
    directory: str  # e.g. "ofl/montserrat"
    license_file: str  # OFL.txt or LICENSE.txt
    faces: list[Face]
    scripts: list[str] = field(default_factory=lambda: ["latin"])
    source: str = ""


FAMILIES: list[Family] = [
    Family("Montserrat", "ofl/montserrat", "OFL.txt", [
        Face("Black", 900, "Montserrat[wght].ttf", {"wght": 900}, ["bold", "popular"]),
        Face("ExtraBold", 800, "Montserrat[wght].ttf", {"wght": 800}, ["bold"]),
        Face("Bold", 700, "Montserrat[wght].ttf", {"wght": 700}, ["bold", "clean"]),
    ]),
    Family("Anton", "ofl/anton", "OFL.txt", [
        Face("Regular", 400, "Anton-Regular.ttf", None, ["bold"])]),
    Family("Bebas Neue", "ofl/bebasneue", "OFL.txt", [
        Face("Regular", 400, "BebasNeue-Regular.ttf", None, ["bold"])]),
    Family("Poppins", "ofl/poppins", "OFL.txt", [
        Face("Bold", 700, "Poppins-Bold.ttf", None, ["clean", "bold"]),
        Face("SemiBold", 600, "Poppins-SemiBold.ttf", None, ["clean"]),
    ]),
    Family("Oswald", "ofl/oswald", "OFL.txt", [
        Face("Bold", 700, "Oswald[wght].ttf", {"wght": 700}, ["bold"])]),
    Family("Archivo Black", "ofl/archivoblack", "OFL.txt", [
        Face("Regular", 400, "ArchivoBlack-Regular.ttf", None, ["bold"])]),
    Family("Bangers", "ofl/bangers", "OFL.txt", [
        Face("Regular", 400, "Bangers-Regular.ttf", None, ["fun"])]),
    Family("Luckiest Guy", "apache/luckiestguy", "LICENSE.txt", [
        Face("Regular", 400, "LuckiestGuy-Regular.ttf", None, ["fun"])]),
    Family("Lilita One", "ofl/lilitaone", "OFL.txt", [
        Face("Regular", 400, "LilitaOne-Regular.ttf", None, ["fun", "bold"])]),
    Family("Permanent Marker", "apache/permanentmarker", "LICENSE.txt", [
        Face("Regular", 400, "PermanentMarker-Regular.ttf", None, ["handwritten"])]),
    Family("Caveat Brush", "ofl/caveatbrush", "OFL.txt", [
        Face("Regular", 400, "CaveatBrush-Regular.ttf", None, ["handwritten"])]),
    Family("Inter", "ofl/inter", "OFL.txt", [
        Face("Bold", 700, "Inter[opsz,wght].ttf", {"wght": 700, "opsz": 14}, ["clean"])]),
    Family("Rubik", "ofl/rubik", "OFL.txt", [
        Face("Bold", 700, "Rubik[wght].ttf", {"wght": 700}, ["clean", "fun"])]),
    Family("Kanit", "ofl/kanit", "OFL.txt", [
        Face("Bold", 700, "Kanit-Bold.ttf", None, ["bold"])]),
    Family("Roboto Condensed", "ofl/robotocondensed", "OFL.txt", [
        Face("Bold", 700, "RobotoCondensed[wght].ttf", {"wght": 700}, ["clean", "bold"])]),
    Family("Noto Sans Devanagari", "ofl/notosansdevanagari", "OFL.txt", [
        Face("Bold", 700, "NotoSansDevanagari[wdth,wght].ttf", {"wght": 700, "wdth": 100},
             ["multilingual", "bold"])], scripts=["devanagari", "latin"]),
]  # fmt: skip


def fetch(path: str) -> bytes:
    url = f"{RAW}/{urllib.parse.quote(path, safe='/')}"
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        return resp.read()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def check_license(directory: str, text: str, file: str) -> str:
    low = text.lower()
    if "sil open font license" in low:
        spdx = "OFL-1.1"
        if re.search(r"reserved font name\s+\"", low):
            raise SystemExit(f"{directory}: has a Reserved Font Name - instancing may not be allowed")
    elif "apache license" in low and "version 2.0" in low:
        spdx = "Apache-2.0"
    else:
        raise SystemExit(f"{directory}/{file}: licence is neither OFL nor Apache-2.0 - refusing")
    return spdx


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "narrareel/assets/fonts"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    cache: dict[str, bytes] = {}

    for fam in FAMILIES:
        fam_dir = out / fam.family.replace(" ", "")
        fam_dir.mkdir(exist_ok=True)
        lic_bytes = fetch(f"{fam.directory}/{fam.license_file}")
        spdx = check_license(fam.directory, lic_bytes.decode("utf-8", "replace"), fam.license_file)
        (fam_dir / fam.license_file).write_bytes(lic_bytes)
        for face in fam.faces:
            key = f"{fam.directory}/{face.remote}"
            data = cache.get(key) or fetch(key)
            cache[key] = data
            name = f"{fam.family.replace(' ', '')}-{face.style}.ttf"
            target = fam_dir / name
            src = fam_dir / ".src.ttf"
            src.write_bytes(data)
            font = TTFont(src)
            if face.axes:
                font = instancer.instantiateVariableFont(font, dict(face.axes), updateFontNames=True)
            font.save(target)
            src.unlink()
            names = TTFont(target)["name"]
            manifest.append({
                "id": f"{slug(fam.family)}-{slug(face.style)}",
                "family": fam.family,
                "style": face.style,
                "weight": face.weight,
                "file": f"{fam_dir.name}/{name}",
                "ass_family": names.getDebugName(1),
                "ass_bold": (names.getDebugName(2) or "").lower().startswith("bold"),
                "license": spdx,
                "license_file": f"{fam_dir.name}/{fam.license_file}",
                "source": f"https://fonts.google.com/specimen/{fam.family.replace(' ', '+')}",
                "tags": face.tags,
                "scripts": fam.scripts,
            })
            print(f"{manifest[-1]['id']:32} {spdx:10} {target.stat().st_size // 1024:5d} KB")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total = sum(p.stat().st_size for p in out.rglob("*.ttf")) / 1e6
    print(f"{len(manifest)} fonts, {total:.1f} MB total")


if __name__ == "__main__":
    main()
