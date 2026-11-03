
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
        "files": (
            ("frontend/data/ufc/graded/*.csv", "frontend/data/ufc/graded"),
            ("frontend/data/ufc/pred_sb_sel/*.csv", "frontend/data/ufc/pred_sb_sel"),
            ("frontend/data/dashboards/ufc.json", "frontend/data/dashboards"),
            ("frontend/data/pipeline_health/ufc.json", "frontend/data/pipeline_health"),
        ),
    },
    {
        "name": "baseball",
        "url": "https://github.com/Clownworldenjoyer76/baseball.git",
        "branch": "main",
        "files": (
            (
                "docs/win/baseball/mlb/05_final_scores/results/graded/MLB_final.csv",
                "frontend/data/mlb/final",
            ),
            ("frontend/data/mlb/*_mlb_games.csv", "frontend/data/mlb/games"),
            ("frontend/data/mlb/*_mlb_picks.csv", "frontend/data/mlb/picks"),
            ("frontend/data/dashboards/baseball.json", "frontend/data/dashboards"),
            ("frontend/data/pipeline_health/mlb.json", "frontend/data/pipeline_health"),
        ),
    },
    {
        "name": "hockey",
        "url": "https://github.com/Clownworldenjoyer76/hockey.git",
        "branch": "main",
        "files": (
            ("frontend/data/nhl_slate.csv", "frontend/data/nhl"),
            ("frontend/data/pipeline_health/nhl.json", "frontend/data/pipeline_health"),
            ("frontend/data/nhl/nhl_final.csv", "frontend/data/nhl"),
            ("frontend/data/dashboards/nhl.json", "frontend/data/dashboards"),
        ),
    },
    {
        "name": "basketball",
        "url": "https://github.com/Clownworldenjoyer76/basketball.git",
        "branch": "main",
        "files": (
            ("frontend/data/dashboards/basketball.json", "frontend/data/dashboards"),
            ("frontend/data/dashboards/nba.json", "frontend/data/dashboards"),
            ("frontend/data/dashboards/ncaam.json", "frontend/data/dashboards"),
            ("frontend/data/dashboards/wnba.json", "frontend/data/dashboards"),
            ("frontend/data/pipeline_health/basketball.json", "frontend/data/pipeline_health"),
            ("frontend/basketball_final.csv", "frontend/data/basketball"),
            ("frontend/basketball_slate.csv", "frontend/data/basketball"),
        ),
    },
    {
        "name": "soccer",
        "url": "https://github.com/Clownworldenjoyer76/soccer.git",
        "branch": "main",
        "files": (
            ("frontend/data/dashboards/soccer.json", "frontend/data/dashboards"),
            ("frontend/data/pipeline_health/soccer.json", "frontend/data/pipeline_health"),
            ("frontend/soccer_final.csv", "frontend/data/soccer"),
            ("frontend/soccer_slate.csv", "frontend/data/soccer"),
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
            folders = sorted({
                str(PurePosixPath(pattern).parent)
                for pattern, _ in source["files"]
            })
            run(
                ["git", "-C", str(source_root), "sparse-checkout", "set", *folders],
                check=True,
            )

            matches = {}
            for pattern, destination_directory in source["files"]:
                files = sorted(path for path in source_root.glob(pattern) if path.is_file())
                if not files:
                    raise FileNotFoundError(
                        f"No source files found: {source['name']}:{pattern}"
                    )
                matches[(pattern, destination_directory)] = files

            for (pattern, destination_directory), files in matches.items():
                for source_file in files:
                    destination_file = destination_root / destination_directory / source_file.name
                    destination_file.parent.mkdir(parents=True, exist_ok=True)
                    copy2(source_file, destination_file)
                print(f"{source['name']}: {pattern} -> {len(files)} file(s) copied")


if __name__ == "__main__":
    main()
