"""Sessions pane: a touch-first zellij session manager.

Lists live sessions and lets you create, attach/switch, or kill one — each via a
deliberate tap so a misfire on a phone can't yank you somewhere or kill the wrong
session. (Detaching is a zellij keybind, `Ctrl o d`, not a list action.)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from dotfiles.app.context import AppContext
from dotfiles.cmd.session import session_name
from dotfiles.cmd.session.agent_sessions import agents_by_session, live_agents
from dotfiles.cmd.session.models import AgentActivity, Session
from dotfiles.cmd.session.service import exited_sessions, humanize_age, maybe_prune
from dotfiles.cmd.session.zellij import (
    SessionError,
    Zellij,
    handoff_command,
    in_zellij,
)

if TYPE_CHECKING:
    from dotfiles.tui.app import MissionControlApp

_NEW_ROW_ID = "new-session"
_REFRESH_SECONDS = 4.0  # live deck: cheap (one `zellij list-sessions` + a dir scan)


def _elsewhere_line(unmatched: list[AgentActivity], clients: int | None = None) -> str:
    """Top summary: attached-client count + agents running outside any session.

    Matched agents live on their session rows; this line catches the rest — agents
    whose process carries no ZELLIJ_SESSION_NAME, labelled by their working dir.
    """
    prefix = f"[cyan]👤 {clients} attached[/]  ·  " if clients else ""
    if not unmatched:
        return prefix + "[dim]No agents elsewhere[/]"
    parts = [f"[green]{a.agent}[/] {Path(a.cwd).name or a.cwd or '?'}" for a in unmatched]
    return prefix + "[dim]elsewhere:[/]  " + "  ·  ".join(parts)


def _agent_badge(agents: Sequence[AgentActivity]) -> str:
    """Green badge of agent names active in a session, e.g. ``claude`` or ``claude · codex``."""
    return " · ".join(f"[green]{a.agent}[/]" for a in agents)


def live_sessions(sessions: list[Session]) -> list[Session]:
    """Running sessions only, current first then by name (the TUI manages live ones)."""
    return sorted((s for s in sessions if s.running), key=lambda s: (not s.current, s.name))


def _programs_line(programs: Sequence[str], limit: int = 3) -> str:
    """A dim, brand-gold summary of what's running, e.g. ``Claude Code · nvim``.

    Caps the count (with a ``+N`` overflow) and escapes titles so a stray ``[`` in
    a pane title can't be read as console markup.
    """
    shown = [escape(p) for p in programs[:limit]]
    if len(programs) > limit:
        shown.append(f"+{len(programs) - limit}")
    return "   [#cdbf80]" + " · ".join(shown) + "[/]"


def _exited_item(s: Session) -> ListItem:
    """A dimmer, tappable row for a resurrectable (exited) session."""
    age = humanize_age(s.created_age_seconds)
    lines = [
        f"[dim]○  {s.name}[/]",
        f"   [dim]exited · {age} ago · tap to resurrect[/]",
    ]
    return ListItem(Label("\n".join(lines)), id=f"sess-{s.name}", classes="session-row is-exited")


def _session_item(
    s: Session, programs: Sequence[str] = (), agents: Sequence[AgentActivity] = ()
) -> ListItem:
    """A tall, spaced, tappable row for one session (state shown via glyph + accent).

    When zellij tells us what's running in the panes, we lead with that preview
    line; the action hint follows, dimmer, prefixed with any active agents.
    """
    if s.current:
        state_cls, desc = "is-current", "attached here · tap for options"
    else:
        state_cls, desc = "is-running", "running · tap to attach"
    lines = [f"[bold]●  {s.name}[/]"]
    if programs:
        lines.append(_programs_line(programs))
    badge = _agent_badge(agents)
    lines.append(f"   {badge} [dim]· {desc}[/]" if badge else f"   [dim]{desc}[/]")
    return ListItem(
        Label("\n".join(lines)), id=f"sess-{s.name}", classes=f"session-row {state_cls}"
    )


def session_action_buttons(s: Session) -> list[tuple[str, str, str]]:
    """(label, button-id, variant) for the per-session action sheet.

    Button-ids map to actions: ``attach`` (attach/switch), ``kill``, ``resurrect``
    (re-attach an exited session), ``delete`` (drop its serialized state),
    ``cancel``. The session you're attached to offers no destructive action —
    killing it would tear down this very TUI — so it's view-only.
    """
    if s.current:
        return [("[u]C[/u]ancel", "cancel", "primary")]
    if not s.running:  # exited → resurrect or delete its saved state
        return [
            ("[u]R[/u]esurrect", "resurrect", "success"),
            ("[u]D[/u]elete", "delete", "error"),
            ("[u]C[/u]ancel", "cancel", "primary"),
        ]
    return [
        ("[u]A[/u]ttach", "attach", "success"),
        ("[u]K[/u]ill", "kill", "error"),
        ("[u]C[/u]ancel", "cancel", "primary"),
    ]


class SessionsPane(Container):
    """Cross-device zellij session manager: create, attach/switch, kill."""

    BORDER_TITLE = "Sessions"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("n", "new_session", "New"),
        Binding("x", "kill_highlighted", "Kill"),
        Binding("r", "reload", "Reload"),
        # Keyboard-first navigation so the deck is fully drivable on mobile, where
        # tapping/scrolling over Mosh is unreliable: vim j/k move the highlight,
        # and 1-9 jump straight to the n-th live session. (Kill is `x`, freeing k.)
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        *(Binding(str(i), f"attach_index({i})", f"Session {i}", show=False) for i in range(1, 10)),
    ]

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._zellij = Zellij(ctx.runner, home=ctx.home)
        self._sessions: list[Session] = []
        self._exited: list[Session] = []
        # Signatures of the last render, so an unchanged auto-refresh is a no-op
        # (rebuilding the list every tick made it visibly flash).
        self._list_sig: tuple[object, ...] | None = None
        self._agents_sig: str | None = None

    @property
    def _app(self) -> MissionControlApp:
        return cast("MissionControlApp", self.app)  # type: ignore[assignment]

    def compose(self) -> ComposeResult:
        yield Static(id="active-agents")
        yield ListView(id="session-list")

    def on_mount(self) -> None:
        self.action_reload()
        # Focus the list so arrow keys navigate/scroll it straight away (mouse
        # wheel works regardless, now that the ListView is a bounded scroll region).
        self.query_one("#session-list", ListView).focus()
        # Keep the deck live so it reflects sessions created/killed elsewhere.
        self.set_interval(_REFRESH_SECONDS, self.action_reload)

    @work(thread=True, exclusive=True)
    def action_reload(self) -> None:
        # Once-a-day guarded retention sweep, opportunistically on load (the daily
        # guard keeps the 4s auto-refresh from thrashing it).
        maybe_prune(
            self._zellij,
            state_file=self._ctx.state_dir / "session-prune",
            now=datetime.now(),
        )
        try:
            sessions = self._zellij.list_sessions()
        except SessionError:
            sessions = []
        agents = live_agents(self._ctx.runner)
        clients = self._zellij.attached_client_count() if in_zellij() else None
        programs = {s.name: self._zellij.program_titles(s.name) for s in sessions if s.running}
        matched, unmatched = agents_by_session(agents)
        self._app.call_from_thread(
            self._apply_sessions, sessions, unmatched, clients, programs, matched
        )

    async def _apply_sessions(
        self,
        sessions: list[Session],
        unmatched: list[AgentActivity],
        clients: int | None = None,
        programs: dict[str, list[str]] | None = None,
        matched: dict[str, list[AgentActivity]] | None = None,
    ) -> None:
        programs = programs or {}
        matched = matched or {}
        self._sessions = live_sessions(sessions)
        self._exited = exited_sessions(sessions)

        # Only touch the DOM when the rendered content actually changes — an
        # unchanged auto-refresh tick must not flash the list or the elsewhere line.
        elsewhere = _elsewhere_line(unmatched, clients)
        if elsewhere != self._agents_sig:
            self.query_one("#active-agents", Static).update(elsewhere)
            self._agents_sig = elsewhere
        # Exited rows key on name only (their age ticks every second). Matched
        # agents key on NAMES only, not idle minutes — so an agent starting/stopping
        # rebuilds the row, but a ticking minute never flashes the list.
        list_sig = (
            tuple(
                (
                    s.name,
                    s.current,
                    s.running,
                    tuple(programs.get(s.name, ())),
                    tuple(a.agent for a in matched.get(s.name, [])),
                )
                for s in self._sessions
            ),
            tuple(s.name for s in self._exited),
        )
        if list_sig == self._list_sig:
            return
        self._list_sig = list_sig

        view = self.query_one("#session-list", ListView)
        # Preserve the cursor across the rebuild so it doesn't jump rows.
        prev = view.highlighted_child
        prev_id = prev.id if prev is not None else None
        # clear() is deferred — await it so the old fixed-id rows are actually
        # gone before we re-append them (otherwise: DuplicateIds on reload).
        await view.clear()
        self._populate_rows(view, programs, matched)
        if prev_id is not None:
            restored = next((i for i, it in enumerate(view.children) if it.id == prev_id), None)
            if restored is not None:
                view.index = restored

    def _populate_rows(
        self,
        view: ListView,
        programs: dict[str, list[str]],
        matched: dict[str, list[AgentActivity]],
    ) -> None:
        """Rebuild the list rows: the New row, live sessions, then the exited group."""
        # Create is always one tap away, even with zero sessions.
        view.append(ListItem(Label("[b]+  New session[/]"), id=_NEW_ROW_ID, classes="new-row"))
        if not self._sessions and not self._exited:
            view.append(ListItem(Label("[dim]no sessions yet[/]"), disabled=True))
        for s in self._sessions:
            view.append(_session_item(s, programs.get(s.name, ()), matched.get(s.name, [])))
        if self._exited:
            view.append(
                ListItem(Label("[dim]── resurrectable ──[/]"), disabled=True, classes="group-label")
            )
            for s in self._exited:
                view.append(_exited_item(s))

    def session_names(self) -> list[str]:
        return [s.name for s in self._sessions]

    def _managed(self) -> list[Session]:
        """Every row the user can act on: live sessions plus resurrectable ones."""
        return [*self._sessions, *self._exited]

    # ------------------------------------------------------------------ #
    # Interaction
    # ------------------------------------------------------------------ #

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if item_id == _NEW_ROW_ID:
            self.action_new_session()
            return
        if item_id.startswith("sess-"):
            name = item_id.removeprefix("sess-")
            session = next((s for s in self._managed() if s.name == name), None)
            if session is not None:
                self._app.push_screen(
                    _SessionActions(session),
                    lambda action, s=session: self._on_action(s, action),
                )

    def action_new_session(self) -> None:
        self._app.push_screen(_NewSession(), self._on_new_session)

    def action_attach_index(self, n: int) -> None:
        """Jump to the n-th live session (1-9). No-ops when n is past the list."""
        if 1 <= n <= len(self._sessions):
            self._handoff(self._sessions[n - 1].name)

    def action_cursor_down(self) -> None:
        """vim `j`: move the list highlight down (mobile-friendly arrow alternative)."""
        self.query_one("#session-list", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        """vim `k`: move the list highlight up."""
        self.query_one("#session-list", ListView).action_cursor_up()

    def action_kill_highlighted(self) -> None:
        """Kill the highlighted session after one confirm (a keyboard shortcut for
        the row's kill action). No-ops on the New row; refuses the current session,
        since killing it would tear down this very TUI."""
        view = self.query_one("#session-list", ListView)
        item = view.highlighted_child
        item_id = item.id if item is not None else None
        if not item_id or not item_id.startswith("sess-"):
            return
        name = item_id.removeprefix("sess-")
        session = next((s for s in self._sessions if s.name == name), None)
        if session is None:
            return
        if session.current:
            self.notify(
                "Can't kill the session you're attached to.",
                title="Sessions",
                severity="warning",
            )
            return
        self._app.push_screen(
            _ConfirmKill(session),
            lambda ok, s=session: self._on_action(s, "kill") if ok else None,
        )

    def _on_action(self, session: Session, action: str | None) -> None:
        if action in ("attach", "resurrect"):
            self._handoff(session.name)
        elif action == "kill":
            self._zellij.kill_session(session.name)
            self.notify(f"Killed {session.name}", title="Sessions", severity="warning")
            self.action_reload()
        elif action == "delete":
            self._zellij.delete_session(session.name)
            self.notify(f"Deleted {session.name}", title="Sessions", severity="warning")
            self.action_reload()

    def _on_new_session(self, name: str | None) -> None:
        if not name:
            return
        layout = self._zellij.layout_for(name)
        command = self._zellij.attach_command(name, exists=False, layout=layout)
        self._app.request_handoff(command)

    def _handoff(self, name: str) -> None:
        command = handoff_command(name, in_zellij=in_zellij())
        self._app.request_handoff(command)


class _SessionActions(ModalScreen[str | None]):
    """Per-session action sheet: attach/switch or kill. Each option has a hotkey
    (the underlined letter); attach/kill are inert for the current session."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "attach", "Attach"),
        Binding("k", "kill", "Kill"),
        Binding("r", "resurrect", "Resurrect"),
        Binding("d", "delete", "Delete"),
        Binding("c", "cancel", "Cancel"),
        Binding("escape", "cancel", show=False),
    ]

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._s = session

    def compose(self) -> ComposeResult:
        s = self._s
        state = "attached here" if s.current else ("running" if s.running else "exited")
        with Vertical(id="confirm-box"):
            yield Label(f"[b]{s.name}[/]  [dim]· {state}[/]")
            for label, button_id, variant in session_action_buttons(s):
                yield Button(label, variant=variant, id=button_id)  # type: ignore[arg-type]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None if event.button.id == "cancel" else event.button.id)

    def action_attach(self) -> None:
        if self._s.running and not self._s.current:  # only a live, non-current session attaches
            self.dismiss("attach")

    def action_kill(self) -> None:
        if self._s.running and not self._s.current:  # killing current would tear down the TUI
            self.dismiss("kill")

    def action_resurrect(self) -> None:
        if not self._s.running:  # only exited sessions resurrect
            self.dismiss("resurrect")

    def action_delete(self) -> None:
        if not self._s.running:  # delete drops an exited session's saved state
            self.dismiss("delete")

    def action_cancel(self) -> None:
        self.dismiss(None)


class _ConfirmKill(ModalScreen[bool]):
    """One-tap-to-confirm kill sheet for the `k` shortcut; dismisses True to kill."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("k", "kill", "Kill"),
        Binding("c", "cancel", "Cancel"),
        Binding("escape", "cancel", show=False),
    ]

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._s = session

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label(f"Kill [b]{self._s.name}[/]?")
            yield Button("[u]K[/u]ill", variant="error", id="kill")
            yield Button("[u]C[/u]ancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "kill")

    def action_kill(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class _NewSession(ModalScreen[str | None]):
    """Prompt for a new session name; dismisses with the validated name (or None)."""

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label("New session name")
            yield Input(placeholder="e.g. api", id="new-name")
            yield Label("", id="name-error")
            yield Button("Create", variant="success", id="create")
            yield Button("Cancel", variant="primary", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#new-name", Input).focus()

    def _submit(self) -> None:
        name = self.query_one("#new-name", Input).value.strip()
        if session_name.is_valid(name):
            self.dismiss(name)
            return
        if error := session_name.error(name):
            self.query_one("#name-error", Label).update(f"[red]{error}[/]")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "new-name":
            return
        cleaned = session_name.clean(event.value)
        if cleaned == event.value:
            return
        if error := session_name.error(event.value):
            self.query_one("#name-error", Label).update(f"[red]{error}[/]")
        event.input.value = cleaned

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self._submit()
        else:
            self.dismiss(None)
