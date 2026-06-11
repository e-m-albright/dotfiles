"""Render the harness manifest for `dotfiles agent instructions` as a tree.

One picture: the five-layer harness model as a header, then a tree of everything an
agent is fed (in context now) and everything it can reach (on demand) — with the
engineering map + symptom→rite routing folded in (subsuming `agent catechism`) and
the vendors that skip a surface flagged inline.
"""

from __future__ import annotations

from rich.markup import escape
from rich.tree import Tree

from dotfiles.cmd.agent.instructions import ContextItem, InstructionsManifest, LoadMode
from dotfiles.cmd.agent.render.overview import GOLD
from dotfiles.console import console


def _fmt_tokens(tokens: int) -> str:
    """A compact token gauge: ~12.3k / ~840."""
    return f"~{tokens / 1000:.1f}k" if tokens >= 1000 else f"~{tokens}"


def _item_label(item: ContextItem) -> str:
    """One source as a tree line: name · count · tokens · note · the vendors that skip it."""
    parts = [f"[{GOLD}]{escape(item.name)}[/]"]
    if item.count:
        parts.append(f"[dim]({item.count})[/]")
    if item.est_tokens:
        parts.append(f"[dim]{_fmt_tokens(item.est_tokens)}[/]")
    parts.append(f"[dim]{escape(item.note)}[/]")
    if item.vendor_gaps:
        parts.append(f"[red]✗ {escape(' · '.join(item.vendor_gaps))}[/]")
    return "  ".join(parts)


def _graft_doctrine(node: Tree, manifest: InstructionsManifest) -> None:
    """Hang the engineering map + symptom→rite routing off *node* (the subsumed catechism)."""
    ids = " · ".join(f"{col.name} {col.ids}" for col in manifest.columns)
    map_node = node.add(f"[{GOLD}]doctrine — the engineering map[/]  [dim]ENGINEERING.md[/]")
    map_node.add(f"[dim]{escape(ids)}[/]")
    for layer in manifest.doctrine:
        map_node.add(f"[bold]{escape(layer.name)}[/]  [dim]{escape(layer.role)}[/]")
    routing = node.add(f"[{GOLD}]routing — symptom → rite[/]  [dim]front door: code-health[/]")
    for entry in manifest.routing:
        routing.add(
            f"[dim]{escape(entry.symptom)}[/] → [bold]{escape(entry.rite)}[/]  "
            f"[dim]{escape(entry.tier)}[/]"
        )


def _add_items(branch: Tree, manifest: InstructionsManifest, mode: LoadMode) -> None:
    for item in manifest.items_for(mode):
        node = branch.add(_item_label(item))
        if item.name == "reference docs":
            _graft_doctrine(node, manifest)


def render_instructions(manifest: InstructionsManifest) -> None:
    """Print the harness manifest as a tree: provided / reachable / active / tools."""
    default_tok = manifest.tokens_for(LoadMode.default)
    reachable_tok = manifest.tokens_for(LoadMode.reachable)

    console.print("[bold]the harness[/]  [dim]· five layers we engineer around the model[/]")
    for layer in manifest.layers:
        console.print(f"  [{GOLD}]{escape(layer.name)}[/]  [dim]{escape(layer.pieces)}[/]")
    console.print()

    tree = Tree("[bold]context[/]  [dim]· what an agent is fed, and what it can reach[/]")
    provided = tree.add(
        f"[{GOLD}]① in context every session[/]  "
        f"[dim]{_fmt_tokens(default_tok)} tok — the budget you always pay[/]"
    )
    _add_items(provided, manifest, LoadMode.default)
    reachable = tree.add(
        f"[{GOLD}]② reachable on demand[/]  "
        f"[dim]0 until pulled · {_fmt_tokens(reachable_tok)} corpus[/]"
    )
    _add_items(reachable, manifest, LoadMode.reachable)
    active = tree.add(f"[{GOLD}]③ active harness[/]  [dim]behavior-shaping config, not context[/]")
    _add_items(active, manifest, LoadMode.harness)
    tools = tree.add(f"[{GOLD}]④ tools[/]  [dim]the agent's surface · ✎ = mutating (gated)[/]")
    for tool in manifest.tools:
        mark = "[red]✎[/]" if tool.mutating else "[dim]·[/]"
        detail = f"{escape(tool.kind)} · {escape(tool.note)}"
        tools.add(f"{mark} [{GOLD}]{escape(tool.name)}[/]  [dim]{detail}[/]")
    console.print(tree)

    console.print(
        f"\n[dim]Budget every session: [/][bold]{_fmt_tokens(default_tok)} tok[/]"
        f"[dim] · ✗ = vendors that skip a surface · repo sources only (excludes the system "
        f"prompt, MEMORY.md auto-memory, and vendor-injected skills)[/]"
    )


def manifest_json(manifest: InstructionsManifest) -> dict[str, object]:
    """Structured manifest for `--json`, with the per-mode token totals folded in."""
    return {
        "items": [item.model_dump(mode="json") for item in manifest.items],
        "columns": [col.model_dump(mode="json") for col in manifest.columns],
        "tools": [tool.model_dump(mode="json") for tool in manifest.tools],
        "layers": [layer.model_dump(mode="json") for layer in manifest.layers],
        "doctrine": [layer.model_dump(mode="json") for layer in manifest.doctrine],
        "routing": [entry.model_dump(mode="json") for entry in manifest.routing],
        "totals": {
            "default_tokens": manifest.tokens_for(LoadMode.default),
            "reachable_tokens": manifest.tokens_for(LoadMode.reachable),
        },
    }
