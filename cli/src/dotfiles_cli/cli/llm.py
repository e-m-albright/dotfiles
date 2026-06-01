"""`dotfiles llm` commands: list, bench, estimate, compare LM Studio models."""

import typer
from rich.markup import escape

from dotfiles_cli.cli.context import AppContext
from dotfiles_cli.console import console
from dotfiles_cli.core.llm import LMStudioService
from dotfiles_cli.core.models import BenchResult

llm_app = typer.Typer(help="Evaluate local LM Studio models (list|bench|estimate|compare).")


def _ctx(ctx: typer.Context) -> AppContext:
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)
    return app_ctx


def _service(app_ctx: AppContext) -> LMStudioService:
    return LMStudioService(
        runner=app_ctx.runner,
        http=app_ctx.http,
        settings=app_ctx.llm_settings,
    )


def _render_bench(result: BenchResult) -> None:
    """Render a BenchResult in the llm-bench.sh format."""
    console.print()
    console.print("  Throughput")
    console.print(f"    Token gen (tg):       {result.tg_tps:6.2f} tok/s   \\[{result.tier}]")
    console.print(
        f"    Prompt eval (pp):     {result.pp_tps:6.2f} tok/s"
        f"   ({result.pp_tokens} tokens / {result.pp_wall:.2f}s)"
    )
    console.print(f"    TTFT (warm):          {result.ttft:6.3f}s")
    console.print()
    console.print("  Reasoning-mode check")
    console.print(f"    Reasoning tokens:     {result.reasoning_tokens}")
    console.print(f"    Visible content len:  {result.content_len} chars")
    if result.reasoning_tokens > 0:
        budget = 3 + result.reasoning_tokens // 100
        console.print(f"    -> THINKING MODEL — budget {budget}x max_tokens for visible output")


@llm_app.command(name="list")
def list_models(ctx: typer.Context) -> None:
    """List loaded LM Studio models (lms ps)."""
    app_ctx = _ctx(ctx)
    try:
        output = _service(app_ctx).list_loaded()
    except RuntimeError as exc:
        console.print(f"[red]Error:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc
    console.print(output, end="", markup=False)


@llm_app.command()
def bench(
    ctx: typer.Context,
    model: str = typer.Argument(None, help="Model ID to bench (default: currently loaded)."),
) -> None:
    """Benchmark a model: throughput, TTFT, and reasoning-mode check."""
    app_ctx = _ctx(ctx)
    try:
        result = _service(app_ctx).bench(model)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc
    _render_bench(result)


@llm_app.command()
def estimate(
    ctx: typer.Context,
    model: str = typer.Argument(..., help="Model ID to estimate."),
    ctx_size: int = typer.Argument(262144, help="Context window size (default 262144)."),
) -> None:
    """Estimate memory footprint for a model at a given context size."""
    app_ctx = _ctx(ctx)
    try:
        output = _service(app_ctx).estimate(model, ctx_size)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc
    console.print(output, markup=False)
    console.print()
    console.print("  Working set ceiling on M4 Pro 48GB: ~40 GB")


@llm_app.command()
def compare(
    ctx: typer.Context,
    model_a: str = typer.Argument(..., help="First model ID."),
    model_b: str = typer.Argument(..., help="Second model ID."),
) -> None:
    """Head-to-head benchmark: bench MODEL_A then MODEL_B."""
    app_ctx = _ctx(ctx)
    svc = _service(app_ctx)

    console.print(f"[blue]Head-to-head: {escape(model_a)} vs {escape(model_b)}[/]")

    try:
        result_a = svc.bench(model_a)
    except RuntimeError as exc:
        console.print(f"[red]Error benchmarking {escape(model_a)}:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc
    _render_bench(result_a)

    console.print()

    try:
        result_b = svc.bench(model_b)
    except RuntimeError as exc:
        console.print(f"[red]Error benchmarking {escape(model_b)}:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc
    _render_bench(result_b)

    console.print()
    console.print("[dim]Per the local-llm-stack.md heuristic:[/]")
    console.print("[dim]  > 40 tok/s = interactive-grade; > 100 = autocomplete-grade[/]")
