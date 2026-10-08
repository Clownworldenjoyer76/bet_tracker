from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
SOURCE = FRONTEND / "src"
PAGES = SOURCE / "pages"
COMPONENTS = SOURCE / "components"
ASSETS = SOURCE / "assets"
DATA = SOURCE / "data"
PUBLIC = SOURCE / "public"
PRODUCTION_DIST = (FRONTEND / "dist").resolve()
LEGACY_MARKER = ".legacy-build-output"

ATTR_RE = re.compile(r'(?i)\b(?:href|src)=["\']([^"\']+)["\']')
INLINE_STYLE_RE = re.compile(r"(?is)<style(?:\s[^>]*)?>")
INLINE_SCRIPT_RE = re.compile(r"(?is)<script(?![^>]*\bsrc\s*=)[^>]*>")
# React-owned pages (deployed from G:\bet_tracker_react) contain exactly one tiny
# inline no-flash style. It is allowed only in files that contain the React root div.
REACT_ROOT_MARKER = '<div id="root">'
REACT_NOFLASH_STYLE_RE = re.compile(r'(?is)<style\s+id="smh-no-flash">[^<]*</style>')


def copy_contents(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _same_or_inside(child: Path, parent: Path) -> bool:
    if child == parent:
        return True
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def check_output_dir(out: Path) -> Path:
    """A legacy rebuild may only target an explicit folder that is not production."""
    out = out.resolve()
    protected = (PRODUCTION_DIST, SOURCE.resolve())
    for p in protected:
        if _same_or_inside(out, p) or _same_or_inside(p, out):
            raise SystemExit(
                f"REFUSED: output folder '{out}' is, contains, or sits inside '{p}'. "
                "The legacy rebuild never targets production dist or the source tree."
            )
    if out.exists() and any(out.iterdir()) and not (out / LEGACY_MARKER).exists():
        raise SystemExit(
            f"REFUSED: '{out}' is not empty and was not created by this script "
            f"(no {LEGACY_MARKER} marker)."
        )
    return out


def build(out: Path) -> None:
    for required in (SOURCE, PAGES, ASSETS):
        if not required.exists():
            raise RuntimeError(f"Required source path is missing: {required}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / LEGACY_MARKER).write_text(
        "Created by sync_frontend.py --rebuild-legacy-to. Not a production directory.\n",
        encoding="ascii",
    )

    for page in PAGES.iterdir():
        if page.is_file():
            shutil.copy2(page, out / page.name)

    nav = COMPONENTS / "nav.html"
    if nav.exists():
        shutil.copy2(nav, out / "nav.html")

    copy_contents(ASSETS, out / "assets")
    copy_contents(DATA, out / "data")

    if PUBLIC.exists():
        for item in PUBLIC.iterdir():
            if item.is_file():
                shutil.copy2(item, out / item.name)


def validate(dist: Path) -> None:
    errors: list[str] = []

    if not dist.is_dir():
        raise SystemExit(f"VALIDATION FAILED: folder not found: {dist}")

    if not (dist / "index.html").exists():
        errors.append("index.html is missing.")
    if not (dist / "nav.html").exists():
        errors.append("nav.html is missing.")

    for file in dist.iterdir():
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if "<html" not in text.lower():
            continue

        check_text = text
        if REACT_ROOT_MARKER in text:
            check_text = REACT_NOFLASH_STYLE_RE.sub("", text)

        if INLINE_STYLE_RE.search(check_text):
            errors.append(f"{file.name}: inline <style> block found.")
        if INLINE_SCRIPT_RE.search(check_text):
            errors.append(f"{file.name}: inline executable <script> found.")

        for match in ATTR_RE.finditer(text):
            url = match.group(1)
            if re.match(r"^(?:#|https?:|mailto:|tel:|javascript:|data:|//)", url):
                continue

            clean = re.split(r"[?#]", url, maxsplit=1)[0]
            if not clean.strip():
                continue

            candidate = file.parent / clean
            if not candidate.exists():
                errors.append(f"{file.name}: missing local reference '{url}'.")

    if errors:
        print(f"VALIDATION FAILED ({len(errors)} error(s)) in {dist}")
        for error in errors:
            print(f" - {error}")
        raise SystemExit(1)

    page_count = sum(1 for p in dist.iterdir() if p.is_file() and p.suffix.lower() == ".html")
    assets_dir = dist / "assets"
    asset_count = sum(1 for p in assets_dir.rglob("*") if p.is_file()) if assets_dir.exists() else 0
    print("VALIDATION OK")
    print(f"HTML pages: {page_count}")
    print(f"Assets:     {asset_count}")
    print(f"Folder:     {dist}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Default: validate the production frontend dist (read-only). "
            "Optional: rebuild the LEGACY frontend from src into an explicit non-production folder."
        )
    )
    parser.add_argument(
        "--rebuild-legacy-to",
        metavar="OUTDIR",
        help="Rebuild the legacy frontend from src into OUTDIR (never production dist), then validate OUTDIR.",
    )
    args = parser.parse_args()

    if args.rebuild_legacy_to:
        out = check_output_dir(Path(args.rebuild_legacy_to))
        build(out)
        validate(out)
    else:
        validate(PRODUCTION_DIST)


if __name__ == "__main__":
    main()
