# pyright: basic
"""Supertonic adapter - the imperative shell around the `supertonic` package.

Confined to one file in pyright `basic` mode because supertonic ships no
`py.typed`; in strict mode every call on its TTS object would be an
`Unknown`-type error. The `Voice` port, the chunker, and every other backend
stay strict and fully tested in `service.py`. Upgrade path: drop the mode line
once supertonic publishes type hints, then annotate `_engine`'s return.

supertonic is imported lazily inside `_engine` so a host that never speaks
neurally does not pay the onnxruntime import, and so `dotfiles speak
--engine say` works with the extra uninstalled.
"""

from __future__ import annotations

import importlib
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotfiles.cmd.speak.service import (
    DEFAULT_SUPERTONIC_VOICE,
    VoiceUnavailableError,
    _ProcessVoice,
    play_file,
    split_sentences,
)


@dataclass
class SupertonicVoice(_ProcessVoice):
    """Local neural TTS. Model and voice style load once on first use.

    Inherits process plumbing from `_ProcessVoice`; only synthesis
    and the chunk pipeline are its own.
    """

    voice: str = DEFAULT_SUPERTONIC_VOICE
    lang: str = "en"
    _tts: Any = field(default=None, init=False, repr=False)
    _style: Any = field(default=None, init=False, repr=False)
    _tmp: tempfile.TemporaryDirectory | None = field(default=None, init=False, repr=False)
    _cancel: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)

    def _engine(self):
        if self._tts is None:
            try:
                module = importlib.import_module("supertonic")
            except ImportError as error:  # pragma: no cover - depends on install
                raise VoiceUnavailableError(
                    "supertonic is not installed. Run "
                    "`uv sync --project cli --extra speech`, or use --engine say."
                ) from error
            self._tts = module.TTS(auto_download=True)
            self._style = self._tts.get_voice_style(voice_name=self.voice)
            self._tmp = tempfile.TemporaryDirectory(prefix="dotfiles-speak-")
        return self._tts

    def speak(self, text: str, *, wait: bool = True) -> None:
        if not text:
            return
        self._engine()
        self.stop()
        self._cancel.clear()
        chunks = split_sentences(text)
        if wait:
            self._speak_chunks(chunks)
        else:
            self._thread = threading.Thread(target=self._speak_chunks, args=(chunks,), daemon=True)
            self._thread.start()

    def _speak_chunks(self, chunks: list[str]) -> None:
        """Play each chunk, rendering the next while the current one plays."""
        pending = self._render(chunks[0]) if chunks else None
        for index, _ in enumerate(chunks):
            if pending is None or self._cancel.is_set():
                return
            proc = play_file(pending)
            self._proc = proc
            pending = self._render(chunks[index + 1]) if index + 1 < len(chunks) else None
            proc.wait()
        self._proc = None

    def _render(self, text: str) -> Path:
        """Synthesize one chunk to its own wav file and return the path."""
        wav, _duration = self._tts.synthesize(text=text, lang=self.lang, voice_style=self._style)
        assert self._tmp is not None
        # One file per utterance: overwriting a wav that afplay still holds open
        # truncates the tail of whatever is currently speaking.
        path = Path(self._tmp.name) / f"{abs(hash(text)):x}.wav"
        self._tts.save_audio(wav, str(path))
        return path

    def stop(self) -> None:
        self._cancel.set()
        super().stop()
