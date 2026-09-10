#!/usr/bin/env python3
"""
BPAA site image cleanup script.

What it does:
1. Finds every image referenced in your .html/.css files.
2. Renames each to lowercase-hyphenated, no-spaces (e.g. "Malik Headshot.jpeg" -> "malik-headshot.jpg").
3. Compresses/resizes each image so it's web-ready (max width 1200px, target < 200KB).
4. Updates every .html and .css file so src="" / url() paths point to the new filenames.
5. Moves any image folder NOT referenced anywhere (e.g. "BP Charter Member Headshot",
   "BPAA Board of Directors") into an /_archive folder instead of deleting it, so you can
   review before removing for good.

Run this from the ROOT of your cloned bpaa repo.

Setup:
    pip install pillow

Usage:
    python3 bpaa_image_cleanup.py           # does a dry run, shows what it WOULD do
    python3 bpaa_image_cleanup.py --apply   # actually renames, compresses, and rewrites files
"""

import os
import re
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Missing dependency. Run: pip install pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
ROOT = Path.cwd()  # run from repo root

HTML_CSS_EXT = (".html", ".css")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")
MAX_WIDTH = 1200
TARGET_BYTES = 200 * 1024  # 200KB
JPEG_QUALITY_START = 85

APPLY = "--apply" in sys.argv


def slugify(name: str) -> str:
    """lowercase, replace spaces/underscores with hyphens, strip weird chars."""
    stem, ext = os.path.splitext(name)
    ext = ext.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    stem = stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    stem = re.sub(r"-+", "-", stem).strip("-")
    return f"{stem}{ext}"


def find_all_text_files():
    return [p for p in ROOT.rglob("*") if p.suffix in HTML_CSS_EXT and "_archive" not in p.parts]


def find_all_images():
    return [p for p in ROOT.rglob("*") if p.suffix in IMAGE_EXT and "_archive" not in p.parts]


def get_referenced_paths(text_files):
    """Pull every path used in src="" / url() across html/css so we know what's live."""
    referenced = set()
    src_pattern = re.compile(r'src=["\']([^"\']+)["\']')
    url_pattern = re.compile(r'url\(["\']?([^"\')]+)["\']?\)')
    for f in text_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pattern in (src_pattern, url_pattern):
            for match in pattern.findall(content):
                if match.startswith(("http://", "https://", "data:")):
                    continue
                referenced.add(match)
    return referenced


def compress_image(src_path: Path, dest_path: Path):
    """Resize + compress. Overwrites dest_path with a web-ready version."""
    img = Image.open(src_path)

    # Convert to RGB if needed (handles PNG-with-alpha going to JPEG, CMYK, etc.)
    if dest_path.suffix.lower() == ".jpg" and img.mode in ("RGBA", "P", "CMYK"):
        img = img.convert("RGB")

    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.suffix.lower() == ".jpg":
        quality = JPEG_QUALITY_START
        img.save(dest_path, "JPEG", quality=quality, optimize=True)
        while dest_path.stat().st_size > TARGET_BYTES and quality > 40:
            quality -= 10
            img.save(dest_path, "JPEG", quality=quality, optimize=True)
    else:  # png
        img.save(dest_path, "PNG", optimize=True)
        # If a PNG is still huge and has no meaningful transparency, fall back to JPEG-quality PNG compression
        if dest_path.stat().st_size > TARGET_BYTES:
            img.save(dest_path, "PNG", optimize=True, compress_level=9)


def main():
    text_files = find_all_text_files()
    images = find_all_images()
    referenced = get_referenced_paths(text_files)

    print(f"Found {len(text_files)} html/css files")
    print(f"Found {len(images)} image files")
    print(f"Found {len(referenced)} referenced paths in html/css\n")

    rename_map = {}   # old relative path -> new relative path
    unreferenced_dirs = set()

    for img_path in images:
        rel_path = img_path.relative_to(ROOT).as_posix()
        new_name = slugify(img_path.name)
        new_rel_path = (img_path.parent.relative_to(ROOT) / new_name).as_posix()

        is_referenced = any(
            rel_path == ref
            or rel_path.endswith("/" + ref)
            or os.path.basename(ref) == img_path.name  # exact filename match, not substring
            for ref in referenced
        )

        if not is_referenced:
            unreferenced_dirs.add(img_path.parent)
            continue

        if rel_path != new_rel_path:
            rename_map[rel_path] = new_rel_path

    print("=== Images to rename + compress ===")
    for old, new in rename_map.items():
        print(f"  {old}  ->  {new}")

    print("\n=== Unreferenced folders (will be archived, not deleted) ===")
    for d in sorted(unreferenced_dirs):
        print(f"  {d.relative_to(ROOT)}")

    if not APPLY:
        print("\nDry run only. Re-run with --apply to actually make changes.")
        return

    print("\nApplying changes...")

    # 1. Compress + rename images
    for old_rel, new_rel in rename_map.items():
        old_path = ROOT / old_rel
        new_path = ROOT / new_rel
        before = old_path.stat().st_size
        compress_image(old_path, new_path)
        after = new_path.stat().st_size
        if old_path != new_path and old_path.exists():
            old_path.unlink()
        print(f"  {old_rel} ({before//1024}KB) -> {new_rel} ({after//1024}KB)")

    # 2. Update references in html/css
    for f in text_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        original = content
        for old_rel, new_rel in rename_map.items():
            old_name = os.path.basename(old_rel)
            new_name = os.path.basename(new_rel)
            # Replace any occurrence of the old filename (path-agnostic, safest for this repo's mixed path styles)
            content = content.replace(old_name, new_name)
        if content != original:
            f.write_text(content, encoding="utf-8")
            print(f"  Updated references in {f.relative_to(ROOT)}")

    # 3. Archive unreferenced folders
    archive_root = ROOT / "_archive"
    for d in unreferenced_dirs:
        dest = archive_root / d.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(dest))
        print(f"  Archived {d.relative_to(ROOT)} -> {dest.relative_to(ROOT)}")

    print("\nDone. Review changes, then commit:")
    print("  git add -A")
    print('  git commit -m "Compress and rename images, archive unused folders"')
    print("  git push")


if __name__ == "__main__":
    main()
