"""`dotfiles speak` - this host's voice. Text in, sound out.

The process contract other repositories depend on:

    dotfiles speak "hello"                 # text as an argument
    echo "hello" | dotfiles speak -        # or on stdin
    dotfiles speak "hola" --lang es
    dotfiles speak "hi" --engine say       # no neural dependency
    dotfiles speak --voices                # audition all ten presets

Exit codes: 0 spoke, 1 backend unavailable, 2 bad argument. Keep this surface
stable - `notes` and the agent voice loop call it as a subprocess.
"""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from dotfiles.cmd.speak.service import (
    DEFAULT_SUPERTONIC_VOICE,
    ENGINES,
    SUPERTONIC_VOICES,
    VoiceUnavailableError,
    build,
)
from dotfiles.console import console, print_status

AUDITION_LINE = (
    "This is the voice your machine will use. "
    "It reads a full sentence so you can judge the rhythm, not just the timbre."
)


def _read_text(text: str | None) -> str:
    """Argument text, or stdin when the argument is `-` or absent in a pipe."""
    if text == "-" or (text is None and not sys.stdin.isatty()):
        return sys.stdin.read().strip()
    return (text or "").strip()


def speak_command(
    text: Annotated[
        str | None, typer.Argument(help="Text to speak. Use '-' to read stdin.")
    ] = None,
    engine: Annotated[
        str, typer.Option("--engine", help="supertonic (neural, local) | say (macOS) | silent.")
    ] = "supertonic",
    voice: Annotated[
        str | None, typer.Option("--voice", help="Preset M1-M5 / F1-F5, or a macOS voice name.")
    ] = None,
    lang: Annotated[
        str, typer.Option("--lang", help="Language code, e.g. en, es. Supertonic covers 31.")
    ] = "en",
    voices: Annotated[
        bool, typer.Option("--voices", help="Audition every preset instead of speaking.")
    ] = False,
    follow: Annotated[
        bool,
        typer.Option(
            "--follow",
            help="Stay resident: speak each line of stdin, print 'ok' after each. "
            "Loads the model once - use this for a session of many utterances.",
        ),
    ] = False,
) -> None:
    """Speak text aloud with local neural text-to-speech."""
    if voices:
        _audition(lang)
        raise typer.Exit(0)
    if follow:
        _follow(engine, voice, lang)
        raise typer.Exit(0)

    body = _read_text(text)
    if not body:
        print_status(console, "error", "nothing to speak", "pass text, or pipe it in")
        raise typer.Exit(2)
    if engine not in ENGINES:
        print_status(
            console, "error", f"unknown engine {engine!r}", f"expected: {', '.join(ENGINES)}"
        )
        raise typer.Exit(2)

    try:
        build(engine, voice=voice, lang=lang).speak(body, wait=True)
    except (ValueError, VoiceUnavailableError) as error:
        print_status(console, "error", str(error))
        raise typer.Exit(1) from error


def _follow(engine: str, voice: str | None, lang: str) -> None:
    """Resident line-oriented mode - the session protocol.

    One line of stdin in, one utterance out, `ok` on stdout when it finishes.
    A blank line is a no-op that still acks, so a caller can use it as a ping.
    The model loads once for the whole session instead of once per utterance,
    which is the difference between a usable coach and a three-second stutter
    before every cue. Exits cleanly on EOF.
    """
    try:
        backend = build(engine, voice=voice, lang=lang)
    except (ValueError, VoiceUnavailableError) as error:
        print_status(console, "error", str(error))
        raise typer.Exit(1) from error

    for line in sys.stdin:
        body = line.strip()
        if body:
            backend.speak(body, wait=True)
        sys.stdout.write("ok\n")
        sys.stdout.flush()


def _audition(lang: str) -> None:
    """Speak the same line through every Supertonic preset, in order."""
    console.print(f"Auditioning {len(SUPERTONIC_VOICES)} voices - M is male, F is female")
    console.print("[dim]First run downloads the model; later runs are instant.[/dim]")
    try:
        for name in SUPERTONIC_VOICES:
            marker = " (current default)" if name == DEFAULT_SUPERTONIC_VOICE else ""
            console.print(f"  [bold]{name}[/bold]{marker}")
            build("supertonic", voice=name, lang=lang).speak(AUDITION_LINE, wait=True)
    except VoiceUnavailableError as error:
        print_status(console, "error", str(error))
        raise typer.Exit(1) from error
    console.print("\n[dim]Use one with: dotfiles speak '...' --voice <NAME>[/dim]")
    return None
