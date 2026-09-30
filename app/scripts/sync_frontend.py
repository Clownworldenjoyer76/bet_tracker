from __future__ import annotations

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
DIST = FRONTEND / "dist"

ATTR_RE = re.compile(r'(?i)\b(?:href|src)=["\']([^"\']+)["\']')
INLINE_STYLE_RE = re.compile(r"(?is)<style(?:\s[^>]*)?>")
INLINE_SCRIPT_RE = re.compile(r"(?is)<script(?![^>]*\bsrc\s*=)[^>]*>")


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


def build() -> None:
    for required in (SOURCE, PAGES, ASSETS):
        if not required.exists():
            raise RuntimeError(f"Required source path is missing: {required}")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for page in PAGES.iterdir():
        if page.is_file():
            shutil.copy2(page, DIST / page.name)

    nav = COMPONENTS / "nav.html"
    if nav.exists():
        shutil.copy2(nav, DIST / "nav.html")

    copy_contents(ASSETS, DIST / "assets")
    copy_contents(DATA, DIST / "data")

    if PUBLIC.exists():
        for item in PUBLIC.iterdir():
            if item.is_file():
                shutil.copy2(item, DIST / item.name)


def validate() -> None:
    errors: list[str] = []

    if not (DIST / "index.html").exists():
        errors.append("dist/index.html is missing.")
    if not (DIST / "nav.html").exists():
        errors.append("dist/nav.html is missing.")

    for file in DIST.iterdir():
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if "<html" not in text.lower():
            continue

        if INLINE_STYLE_RE.search(text):
            errors.append(f"{file.name}: inline <style> block found.")
        if INLINE_SCRIPT_RE.search(text):
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
        print(f"BUILD FAILED ({len(errors)} validation error(s))")
        for error in errors:
            print(f" - {error}")
        raise SystemExit(1)

    page_count = sum(1 for p in PAGES.iterdir() if p.is_file())
    asset_count = sum(1 for p in (DIST / "assets").rglob("*") if p.is_file())
    print("BUILD OK")
    print(f"Pages:  {page_count}")
    print(f"Assets: {asset_count}")
    print(f"Output: {DIST}")


if __name__ == "__main__":
    build()
    validate()
