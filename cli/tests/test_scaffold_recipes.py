"""Tests for core/scaffold/recipes.py and core/scaffold/tool_registry.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dotfiles.core.scaffold.recipes import (
    DEFAULT_APP_TYPES,
    VALID_RECIPES,
    get_recipe_rules,
    is_known_app_type,
)
from dotfiles.core.scaffold.tool_registry import (
    ToolTarget,
    load_registry,
    tools_for_filter,
)

# ---------------------------------------------------------------------------
# recipes.py
# ---------------------------------------------------------------------------


class TestGetRecipeRules:
    def test_typescript_svelte_includes_lang_stack_framework(self) -> None:
        rules = get_recipe_rules("typescript", "svelte")
        assert "languages/typescript.mdc" in rules
        assert "tooling/stack-typescript.mdc" in rules
        assert "tooling/services.mdc" in rules
        assert "frameworks/sveltekit.mdc" in rules

    def test_typescript_astro_uses_astro_framework(self) -> None:
        rules = get_recipe_rules("typescript", "astro")
        assert "frameworks/astro.mdc" in rules
        assert "frameworks/sveltekit.mdc" not in rules

    def test_python_fastapi_includes_framework(self) -> None:
        rules = get_recipe_rules("python", "fastapi")
        assert "languages/python.mdc" in rules
        assert "frameworks/fastapi.mdc" in rules
        assert "process/shell-automation.mdc" in rules

    def test_python_cli_no_framework_rule(self) -> None:
        rules = get_recipe_rules("python", "cli")
        assert "languages/python.mdc" in rules
        # python/cli explicitly has no framework rule
        assert not any(r.startswith("frameworks/") for r in rules)

    def test_golang_chi_includes_framework(self) -> None:
        rules = get_recipe_rules("golang", "chi")
        assert "languages/golang.mdc" in rules
        assert "frameworks/chi.mdc" in rules

    def test_rust_axum_includes_framework(self) -> None:
        rules = get_recipe_rules("rust", "axum")
        assert "languages/rust.mdc" in rules
        assert "frameworks/axum.mdc" in rules

    def test_rust_tauri_uses_tauri_framework(self) -> None:
        rules = get_recipe_rules("rust", "tauri")
        assert "frameworks/tauri.mdc" in rules
        assert "frameworks/axum.mdc" not in rules

    def test_unknown_recipe_returns_empty(self) -> None:
        assert get_recipe_rules("elixir", "phoenix") == []

    def test_recipe_rules_are_ordered_base_then_framework(self) -> None:
        """Framework rule is always appended after base rules."""
        rules = get_recipe_rules("typescript", "svelte")
        framework_idx = rules.index("frameworks/sveltekit.mdc")
        lang_idx = rules.index("languages/typescript.mdc")
        assert lang_idx < framework_idx


class TestIsKnownAppType:
    @pytest.mark.parametrize(
        ("recipe", "app_type"),
        [
            ("typescript", "svelte"),
            ("typescript", "astro"),
            ("python", "fastapi"),
            ("python", "cli"),
            ("golang", "chi"),
            ("rust", "axum"),
            ("rust", "tauri"),
        ],
    )
    def test_known_combos(self, recipe: str, app_type: str) -> None:
        assert is_known_app_type(recipe, app_type) is True

    @pytest.mark.parametrize(
        ("recipe", "app_type"),
        [
            ("typescript", "vue"),
            ("python", "django"),
            ("golang", "gin"),
            ("rust", "rocket"),
            ("elixir", "phoenix"),
        ],
    )
    def test_unknown_combos(self, recipe: str, app_type: str) -> None:
        assert is_known_app_type(recipe, app_type) is False


class TestDefaultAppTypes:
    def test_all_valid_recipes_have_defaults(self) -> None:
        for recipe in VALID_RECIPES:
            assert recipe in DEFAULT_APP_TYPES

    def test_defaults_are_known_app_types(self) -> None:
        for recipe, app_type in DEFAULT_APP_TYPES.items():
            assert is_known_app_type(recipe, app_type), (
                f"{recipe}/{app_type} is a default but not a known app type"
            )


# ---------------------------------------------------------------------------
# tool_registry.py
# ---------------------------------------------------------------------------


def _write_registry(tmp_path: Path, data: dict) -> Path:
    """Write a fake tool-targets.json and return the fake dotfiles_dir."""
    dotfiles_dir = tmp_path / "dotfiles"
    registry_path = dotfiles_dir / "agents" / "shared"
    registry_path.mkdir(parents=True)
    (registry_path / "tool-targets.json").write_text(json.dumps(data))
    return dotfiles_dir


class TestLoadRegistry:
    def test_loads_cursor_entry(self, tmp_path: Path) -> None:
        dotfiles_dir = _write_registry(
            tmp_path,
            {
                "tools": {
                    "cursor": {
                        "rulesDir": ".cursor/rules",
                        "suffix": ".mdc",
                        "strategy": "symlink",
                        "symlinkPrefix": "../../",
                        "rootFile": None,
                        "agentsMdAware": False,
                    }
                }
            },
        )
        registry = load_registry(dotfiles_dir)
        assert "cursor" in registry
        tool = registry["cursor"]
        assert tool.rules_dir == ".cursor/rules"
        assert tool.suffix == ".mdc"
        assert tool.symlink_prefix == "../../"
        assert tool.root_file is None

    def test_loads_real_registry(self) -> None:
        """Smoke-test against the live agents/shared/tool-targets.json."""
        real_dotfiles = Path(__file__).parent.parent.parent
        registry = load_registry(real_dotfiles)
        assert "cursor" in registry
        assert "codex" in registry

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        registry = load_registry(tmp_path)
        assert registry == {}

    def test_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        dotfiles_dir = tmp_path / "dotfiles"
        path = dotfiles_dir / "agents" / "shared"
        path.mkdir(parents=True)
        (path / "tool-targets.json").write_text("NOT JSON {{{")
        assert load_registry(dotfiles_dir) == {}

    def test_rootfile_entries_loaded(self, tmp_path: Path) -> None:
        dotfiles_dir = _write_registry(
            tmp_path,
            {
                "tools": {
                    "codex": {
                        "rulesDir": None,
                        "suffix": None,
                        "strategy": "symlink",
                        "symlinkPrefix": None,
                        "rootFile": "CODEX.md",
                    }
                }
            },
        )
        registry = load_registry(dotfiles_dir)
        assert registry["codex"].root_file == "CODEX.md"


def _make_tool(
    *,
    rules_dir: str | None = None,
    suffix: str | None = None,
    strategy: str | None = None,
    symlink_prefix: str | None = None,
    root_file: str | None = None,
) -> ToolTarget:
    return ToolTarget.model_validate(
        {
            "rulesDir": rules_dir,
            "suffix": suffix,
            "strategy": strategy,
            "symlinkPrefix": symlink_prefix,
            "rootFile": root_file,
        }
    )


def _make_registry_dict() -> dict[str, ToolTarget]:
    return {
        "cursor": _make_tool(
            rules_dir=".cursor/rules",
            suffix=".mdc",
            strategy="symlink",
            symlink_prefix="../../",
        ),
        "copilot": _make_tool(
            rules_dir=".github/instructions",
            suffix=".instructions.md",
            strategy="symlink",
            symlink_prefix="../../",
        ),
        "codex": _make_tool(
            strategy="symlink",
            root_file="CODEX.md",
        ),
        "jules": _make_tool(
            strategy=None,
        ),
    }


class TestToolsForFilter:
    def test_all_returns_symlink_tools_only(self) -> None:
        registry = _make_registry_dict()
        result = tools_for_filter(registry, "all")
        assert set(result.keys()) == {"cursor", "copilot", "codex"}
        assert "jules" not in result  # strategy=None

    def test_cursor_filter_returns_only_cursor(self) -> None:
        registry = _make_registry_dict()
        result = tools_for_filter(registry, "cursor")
        assert set(result.keys()) == {"cursor"}

    def test_comma_list_filter(self) -> None:
        registry = _make_registry_dict()
        result = tools_for_filter(registry, "cursor,copilot")
        assert set(result.keys()) == {"cursor", "copilot"}

    def test_unknown_name_silently_excluded(self) -> None:
        registry = _make_registry_dict()
        result = tools_for_filter(registry, "cursor,unknown_tool")
        assert set(result.keys()) == {"cursor"}

    def test_non_symlink_excluded_by_strategy(self) -> None:
        """Jules has strategy=None so it's excluded from symlink filter."""
        registry = _make_registry_dict()
        result = tools_for_filter(registry, "all")
        assert "jules" not in result

    def test_empty_filter_returns_empty(self) -> None:
        registry = _make_registry_dict()
        result = tools_for_filter(registry, "")
        assert result == {}
