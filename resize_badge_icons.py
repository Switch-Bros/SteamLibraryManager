#!/usr/bin/env python3
"""
Badge Icon Resizer — Steam Library Manager.

Takes your large source PNGs from GIMP (128x128, 256x256, or 512x512)
and produces optimized 48x48 RGBA PNGs for the badge system.

Why 48x48?
    Qt displays badges at 24px height (scaledToHeight(24)).
    A 48x48 source gives Qt 2 source pixels per display pixel —
    that's the sweet spot for crisp LANCZOS downscaling.
    Anything larger wastes disk space with no visible quality gain at 24px.

Usage:
    1. Put your source PNGs in  source_icons/  (next to src/)
    2. Run:  python resize_badge_icons.py
    3. Done — optimized icons land in  resources/icons/

Expected filenames (any image extension accepted):
    flag_nsfw.png
    flag_humor.png
    flag_epilepsy.png
    flag_animated.png
"""

from pathlib import Path
from typing import Optional

try:
    from PIL import Image
except ImportError:
    print("❌ Pillow nicht installiert. Führe aus:  pip install Pillow")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# 2× Anzeigegröße (24px) → schärfste Interpolation
TARGET_SIZE: int = 48

BADGE_ICONS: list[str] = [
    "flag_nsfw",
    "flag_humor",
    "flag_epilepsy",
    "flag_animated",
]

ACCEPTED_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_project_root() -> Path:
    """Walks up from this script to find the directory containing src/.

    Returns:
        Project root Path, or CWD as fallback.
    """
    candidate: Path = Path(__file__).resolve().parent
    for _ in range(5):
        if (candidate / "src").is_dir():
            return candidate
        candidate = candidate.parent
    return Path.cwd()


def find_source(name: str, search_dirs: list[Path]) -> Optional[Path]:
    """Finds a source image by stem name across multiple directories.

    Args:
        name: Stem to match (e.g. 'flag_nsfw'), case-insensitive.
        search_dirs: Directories to scan.

    Returns:
        First matching Path, or None.
    """
    for d in search_dirs:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.suffix.lower() in ACCEPTED_EXTENSIONS and f.stem.lower() == name.lower():
                return f
    return None


def resize_icon(src: Path, dst: Path) -> tuple[tuple[int, int], float, float]:
    """Resizes src to TARGET_SIZE×TARGET_SIZE and saves as optimised PNG.

    Converts to RGBA first to preserve any transparency channel.

    Args:
        src: Source image path.
        dst: Output path.

    Returns:
        Tuple of (original_size, source_kb, output_kb).
    """
    img: Image.Image = Image.open(src).convert("RGBA")
    original_size: tuple[int, int] = img.size

    # Resampling.LANCZOS = highest quality downscale filter (Pillow 10+)
    resized: Image.Image = img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
    resized.save(dst, format="PNG", optimize=True)

    return (
        original_size,
        src.stat().st_size / 1024,
        dst.stat().st_size / 1024,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: locates sources, resizes, prints a report."""

    root: Path = find_project_root()
    out_dir: Path = root / "resources" / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Suchpfade — vom spezifischen zum allgemeinen
    search: list[Path] = [
        root / "source_icons",  # dedizierter Quell-Ordner  ← hier ablegen
        root,  # Projektroot
        Path.cwd(),  # Arbeitsverzeichnis
    ]

    print("=" * 52)
    print("  Badge Icon Resizer — Steam Library Manager")
    print("=" * 52)
    print(f"  Projekt  : {root}")
    print(f"  Ausgabe  : {out_dir}")
    print(f"  Zielgröße: {TARGET_SIZE}×{TARGET_SIZE} px")
    print("-" * 52)

    processed: int = 0

    for name in BADGE_ICONS:
        src: Optional[Path] = find_source(name, search)

        if src is None:
            print(f"  ⏭️  {name:.<34} nicht gefunden")
            continue

        dst: Path = out_dir / f"{name}.png"
        orig_size, src_kb, dst_kb = resize_icon(src, dst)

        print(
            f"  ✅  {name:.<34} "
            f"{orig_size[0]}×{orig_size[1]} → {TARGET_SIZE}×{TARGET_SIZE}  "
            f"({src_kb:.1f} KB → {dst_kb:.1f} KB)"
        )
        processed += 1

    print("-" * 52)

    if processed:
        print("  🎉 Fertig! Icons in resources/icons/ sind bereit.\n")
    else:
        print("  💡 Keine Quelldateien gefunden.\n")
        print("     Erwartete Dateinamen (beliebige Erweiterung):")
        for n in BADGE_ICONS:
            print(f"       {n}.png")
        print(f"\n     Lege sie in:  {root / 'source_icons'}/\n")

    print("=" * 52)


if __name__ == "__main__":
    main()
