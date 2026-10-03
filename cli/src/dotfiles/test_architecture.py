"""Enforce the dependency boundaries that make the source tree predictable."""

import ast
from importlib.util import resolve_name
from pathlib import Path

PACKAGE = Path(__file__).parent
BACKENDS = {"homebrew", "npm", "go", "special"}


def _modules():
    for path in PACKAGE.rglob("*.py"):
        if path.name.startswith("test_") or "testing" in path.parts or path.name == "conftest.py":
            continue
        parts = path.relative_to(PACKAGE.parent).with_suffix("").parts
        name = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
        yield path, name, ast.parse(path.read_text())


def _imports(module: str, path: Path, tree: ast.Module):
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                target = resolve_name("." * node.level + target, package)
            yield target
            yield from (f"{target}.{alias.name}" for alias in node.names)


def test_canonical_source_homes() -> None:
    assert not (PACKAGE / "cmd").exists()
    assert not (PACKAGE / "adapters" / "ports.py").exists()
    for name in ["ports.py", "app/wiring.py", "features/packages/manifest.py"]:
        assert (PACKAGE / name).is_file()
    for backend in BACKENDS:
        assert (PACKAGE / "features" / "packages" / f"{backend}.py").is_file()


def _edges():
    return {
        (source, target)
        for path, source, tree in _modules()
        for target in _imports(source, path, tree)
    }


def _within(module: str, parent: str) -> bool:
    return module == parent or module.startswith(parent + ".")


def _feature(module: str) -> str | None:
    parts = module.split(".")
    return parts[2] if len(parts) > 2 and parts[1] == "features" else None


def _assembly(module: str) -> bool:
    return any(_within(module, name) for name in ("dotfiles.app.main", "dotfiles.app.wiring"))


def _rendering(module: str) -> bool:
    return (
        any(
            _within(module, name)
            for name in ("dotfiles.console", "dotfiles.banner", "rich", "typer")
        )
        or ".cli" in module
    )


def test_features_do_not_import_application_assembly() -> None:
    assert not {(a, b) for a, b in _edges() if _feature(a) and _assembly(b)}


def test_feature_decisions_depend_on_contracts() -> None:
    assert not {
        (a, b)
        for a, b in _edges()
        if _feature(a)
        and not a.endswith(".cli")
        and (_rendering(b) or _within(b, "dotfiles.adapters"))
    }


def test_adapters_do_not_import_features() -> None:
    assert not {(a, b) for a, b in _edges() if _within(a, "dotfiles.adapters") and _feature(b)}


def test_only_doctor_coordinates_other_features() -> None:
    assert not {
        (a, b)
        for a, b in _edges()
        if _feature(a) not in {None, "doctor"} and _feature(b) not in {None, _feature(a)}
    }


def test_package_backends_do_not_import_their_orchestrator() -> None:
    backends = {f"dotfiles.features.packages.{name}" for name in BACKENDS}
    assert not {
        (a, b)
        for a, b in _edges()
        if a in backends and _within(b, "dotfiles.features.packages.service")
    }


def test_contracts_do_not_construct_concrete_adapters() -> None:
    assert not {
        (a, b)
        for a, b in _edges()
        if a in {"dotfiles.ports", "dotfiles.app.context"}
        and (_within(b, "dotfiles.adapters") or _assembly(b))
    }


def _imported_exports(module: str, tree: ast.Module):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        origin = node.module or ""
        if node.level:
            origin = resolve_name("." * node.level + origin, module)
        for alias in node.names:
            yield alias.asname or alias.name, f"{origin}.{alias.name}"


def _shadowed_modules(path: Path, module: str, tree: ast.Module):
    siblings = {child.stem for child in path.parent.glob("*.py")} - {"__init__"}
    return {
        (module, name, origin)
        for name, origin in _imported_exports(module, tree)
        if name in siblings and origin != f"{module}.{name}"
    }


def test_package_exports_do_not_shadow_sibling_modules() -> None:
    assert not {
        collision
        for path, module, tree in _modules()
        if path.name == "__init__.py"
        for collision in _shadowed_modules(path, module, tree)
    }
