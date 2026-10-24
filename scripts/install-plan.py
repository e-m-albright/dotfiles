"""Read-only work allowlist rendering without the CLI or third-party packages."""

import sys
import tomllib
from pathlib import Path


def main() -> None:
    with Path(sys.argv[1]).open("rb") as source:
        work = tomllib.load(source)["profile"]["work"]
    for key, label in (
        ("taps", "Homebrew taps"),
        ("formulae", "Homebrew formulae"),
        ("casks", "Homebrew casks"),
        ("npm_packages", "npm global"),
    ):
        values = work[key]
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValueError(f"profile.work.{key} must be a list of strings")
        print(f"Selected {label}: {', '.join(values) or 'none'}")


if __name__ == "__main__":
    main()
