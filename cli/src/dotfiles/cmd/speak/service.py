"""Text-to-speech backends - this host's capability to talk.

A machine capability, not an application feature: anything on this Mac that needs
a voice calls `dotfiles speak` rather than carrying its own synthesizer. Callers
integrate through the CLI, never by importing this module across repositories.

Backends
    SupertonicVoice  local neural TTS, the default. Lives in `neural.py` because
                     supertonic ships no type hints; imported lazily by `build`.
    SayVoice         macOS `say`. Always available, pre-neural, sounds it.
    SilentVoice      records what would have been said. Dry runs and tests.

`supertonic` is an optional extra so the CLI stays light on a host that never
makes a sound: `uv sync --project cli --extra speech`.
"""

from __future__ import annotations

import contextlib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

# Stock macOS alert sounds, offered as named cues so callers need not know paths.
SOUNDS = {
    "start": "/System/Library/Sounds/Tink.aiff",
    "switch": "/System/Library/Sounds/Pop.aiff",
    "warn": "/System/Library/Sounds/Morse.aiff",
    "done": "/System/Library/Sounds/Glass.aiff",
}

DEFAULT_SAY_VOICE = "Samantha"
DEFAULT_SAY_RATE = 175

# Supertonic ships ten preset styles: five male, five female.
SUPERTONIC_VOICES = ("M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5")
DEFAULT_SUPERTONIC_VOICE = "M1"

# Synthesis runs ~5-6x realtime on this host, so a long paragraph costs a
# noticeable pause before the first sound. Splitting on sentence boundaries and
# rendering the next chunk while the current one plays makes time-to-first-audio
# a function of the FIRST sentence, not the whole message. Below this length the
# seams cost more than they save.
CHUNK_MIN_CHARS = 90
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

ENGINES = ("supertonic", "say", "silent")


class Voice(Protocol):
    """The three things a caller needs from an audio backend."""

    def speak(self, text: str, *, wait: bool = True) -> None: ...
    def chime(self, name: str) -> None: ...
    def stop(self) -> None: ...


class VoiceUnavailableError(RuntimeError):
    """A backend was requested but its dependency or model is missing."""


def _append_or_merge(chunks: list[str], sentence: str, min_chars: int) -> None:
    """Add a sentence, extending the previous chunk while it is still short.

    Keeps a stray "Yes." from becoming its own utterance with a seam either side.
    """
    if chunks and len(chunks[-1]) < min_chars:
        chunks[-1] = f"{chunks[-1]} {sentence}"
    else:
        chunks.append(sentence)


def split_sentences(text: str, *, min_chars: int = CHUNK_MIN_CHARS) -> list[str]:
    """Split into speakable chunks at sentence boundaries.

    Short text comes back as a single chunk - below `min_chars` the seams cost
    more than the earlier first sound buys.
    """
    text = text.strip()
    if len(text) <= min_chars:
        return [text] if text else []

    chunks: list[str] = []
    for sentence in _SENTENCE_END.split(text):
        _append_or_merge(chunks, sentence, min_chars)
    return [c for c in chunks if c]


def _play(path: str | Path) -> subprocess.Popen[bytes]:
    """Fire-and-forget playback. Returns the process so it can be cut short."""
    return subprocess.Popen(
        ["afplay", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


@dataclass
class _ProcessVoice:
    """Shared plumbing for backends that speak by running a subprocess."""

    _proc: subprocess.Popen[bytes] | None = field(default=None, init=False, repr=False)

    def chime(self, name: str) -> None:
        path = SOUNDS.get(name)
        if path and Path(path).exists():
            _play(path)

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                self._proc.wait(timeout=1)
        self._proc = None

    def _run(self, proc: subprocess.Popen[bytes], *, wait: bool) -> None:
        self._proc = proc
        if wait:
            proc.wait()
            self._proc = None


@dataclass
class SayVoice(_ProcessVoice):
    """macOS `say`. The no-dependency fallback, not the default ambition."""

    voice: str = DEFAULT_SAY_VOICE
    rate: int = DEFAULT_SAY_RATE

    def speak(self, text: str, *, wait: bool = True) -> None:
        if not text:
            return
        self.stop()
        self._run(
            subprocess.Popen(
                ["say", "-v", self.voice, "-r", str(self.rate), text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ),
            wait=wait,
        )


@dataclass
class SilentVoice:
    """Records what would have been said. Dry runs and tests."""

    said: list[str] = field(default_factory=list[str])
    chimed: list[str] = field(default_factory=list[str])

    def speak(self, text: str, *, wait: bool = True) -> None:
        if text:
            self.said.append(text)

    def chime(self, name: str) -> None:
        self.chimed.append(name)

    def stop(self) -> None:
        return


def build(engine: str, *, voice: str | None = None, lang: str = "en") -> Voice:
    """Construct a backend by name. The one place engine selection happens."""
    if engine == "silent":
        return SilentVoice()
    if engine == "say":
        return SayVoice(voice=voice) if voice else SayVoice()
    if engine == "supertonic":
        from dotfiles.cmd.speak.neural import SupertonicVoice

        return SupertonicVoice(voice=voice, lang=lang) if voice else SupertonicVoice(lang=lang)
    raise ValueError(f"unknown voice engine {engine!r}; expected one of {', '.join(ENGINES)}")
