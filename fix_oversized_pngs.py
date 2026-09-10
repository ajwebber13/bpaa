#!/usr/bin/env python3
"""
Converts the 2 remaining oversized headshot PNGs to compressed JPGs
(steven-jubert.png, spellman-headshot.png) and updates the HTML that
references them.

Run from the repo root:
    python3 fix_oversized_pngs.py
"""

from pathlib import Path
from PIL import Image

ROOT = Path.cwd()
TARGET_BYTES = 200 * 1024

FILES = [
    ROOT / "images" / "steven-jubert.png",
    ROOT / "BP Charter Member Headshot" / "spellman-headshot.png",
]


def convert(png_path: Path):
    if not png_path.exists():
        print(f"  SKIP (not found): {png_path}")
        return None, None
    jpg_path = png_path.with_suffix(".jpg")
    img = Image.open(png_path).convert("RGB")
    quality = 85
    img.save(jpg_path, "JPEG", quality=quality, optimize=True)
    while jpg_path.stat().st_size > TARGET_BYTES and quality > 40:
        quality -= 10
        img.save(jpg_path, "JPEG", quality=quality, optimize=True)
    png_path.unlink()
    print(f"  {png_path.name} ({png_path.stat().st_size if png_path.exists() else 0}) -> "
          f"{jpg_path.name} ({jpg_path.stat().st_size // 1024}KB)")
    return png_path.name, jpg_path.name


def main():
    print("Converting oversized PNGs to JPG...")
    renames = []
    for f in FILES:
        old_name, new_name = convert(f)
        if old_name:
            renames.append((old_name, new_name))

    if not renames:
        print("Nothing to convert.")
        return

    print("\nUpdating HTML references...")
    for html_file in ROOT.rglob("*.html"):
        if "_archive" in html_file.parts:
            continue
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        original = content
        for old_name, new_name in renames:
            content = content.replace(old_name, new_name)
        if content != original:
            html_file.write_text(content, encoding="utf-8")
            print(f"  Updated {html_file.name}")

    print("\nDone. Review, then:")
    print("  git add -A")
    print('  git commit -m "Convert remaining oversized PNGs to JPG"')
    print("  git push")


if __name__ == "__main__":
    main()