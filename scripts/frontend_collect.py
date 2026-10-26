"""Collect selected frontend files from source GitHub repositories."""

from pathlib import Path, PurePosixPath
from shutil import copy2
from subprocess import run
from tempfile import TemporaryDirectory


SOURCES = (
    {
        "name": "ufc",
        "url": "https://github.com/Clownworldenjoyer76/ufc.git",
        "branch": "main",
        "paths": (
            "frontend/data/ufc/graded/*.csv",
            "frontend/data/ufc/pred_sb_sel/*.csv",
            "frontend/data/dashboards/ufc.json",
            "frontend/data/pipeline_health/ufc.json",
        ),
    },
)


def main() -> None:
    destination_root = Path(__file__).resolve().parent.parent

    with TemporaryDirectory(prefix="frontend_collect_") as temporary_directory:
        for source in SOURCES:
            source_root = Path(temporary_directory) / source["name"]
            run(
                [
                    "git", "clone", "--quiet", "--depth", "1",
                    "--filter=blob:none", "--sparse", "--branch", source["branch"],
                    source["url"], str(source_root),
                ],
                check=True,
            )
            folders = sorted({str(PurePosixPath(pattern).parent) for pattern in source["paths"]})
            run(["git", "-C", str(source_root), "sparse-checkout", "set", *folders], check=True)

            matches = {}
            for pattern in source["paths"]:
                files = sorted(path for path in source_root.glob(pattern) if path.is_file())
                if not files:
                    raise FileNotFoundError(f"No source files found: {source['name']}:{pattern}")
                matches[pattern] = files

            for pattern, files in matches.items():
                for source_file in files:
                    destination_file = destination_root / source_file.relative_to(source_root)
                    destination_file.parent.mkdir(parents=True, exist_ok=True)
                    copy2(source_file, destination_file)
                print(f"{source['name']}: {pattern} -> {len(files)} file(s) copied")


if __name__ == "__main__":
    main()
