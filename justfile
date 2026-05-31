# dotfiles dev tasks. Run `just` for the list.

default:
    @just --list

# Run the whole static-check + test gate for the Python CLI.
check: fmt-check lint types deadcode complexity test

fmt:
    cd cli && uv run ruff format .

fmt-check:
    cd cli && uv run ruff format --check .

lint:
    cd cli && uv run ruff check .

types:
    cd cli && uv run pyright

deadcode:
    cd cli && uv run vulture src tests .vulture_whitelist.py --min-confidence 80

complexity:
    cd cli && uv run complexipy src -mx 10

test:
    cd cli && uv run pytest --cov=dotfiles_cli --cov-report=term-missing --cov-fail-under=85

audit:
    cd cli && uv run pip-audit
