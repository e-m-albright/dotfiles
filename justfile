# dotfiles dev tasks. Run `just` for the list.

set working-directory := 'cli'

default:
    @just --list

# Run the whole static-check + test gate for the Python CLI.
check: fmt-check lint types deadcode complexity test

# Fast static checks only (no tests) — used on pre-commit.
lint-fast: fmt-check lint types deadcode complexity

fmt:
    uv run ruff format .

fmt-check:
    uv run ruff format --check .

lint:
    uv run ruff check .

types:
    uv run pyright

deadcode:
    uv run vulture src tests .vulture_whitelist.py --min-confidence 80

complexity:
    uv run complexipy src -mx 10

test:
    uv run pytest --cov=dotfiles_cli --cov-report=term-missing --cov-fail-under=85

audit:
    uv run pip-audit
