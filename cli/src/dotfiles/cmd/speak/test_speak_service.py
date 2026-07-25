"""Voice backends: engine selection and sentence chunking.

Nothing here makes a sound, and nothing loads a model - the suite must pass on a
host without the optional `speech` extra installed.
"""

from __future__ import annotations

import pytest

from dotfiles.cmd.speak import neural
from dotfiles.cmd.speak.neural import SupertonicVoice
from dotfiles.cmd.speak.service import (
    DEFAULT_SAY_VOICE,
    DEFAULT_SUPERTONIC_VOICE,
    ENGINES,
    SUPERTONIC_VOICES,
    SayVoice,
    SilentVoice,
    build,
    split_sentences,
)


def test_build_returns_the_named_backend() -> None:
    assert isinstance(build("silent"), SilentVoice)
    assert isinstance(build("say"), SayVoice)
    assert isinstance(build("supertonic"), SupertonicVoice)


def test_build_passes_voice_and_language_through() -> None:
    neural = build("supertonic", voice="F2", lang="es")
    assert isinstance(neural, SupertonicVoice)
    assert (neural.voice, neural.lang) == ("F2", "es")


def test_build_uses_each_backends_default_voice() -> None:
    said, neural = build("say"), build("supertonic")
    assert isinstance(said, SayVoice)
    assert said.voice == DEFAULT_SAY_VOICE
    assert isinstance(neural, SupertonicVoice)
    assert neural.voice == DEFAULT_SUPERTONIC_VOICE


def test_build_rejects_an_unknown_engine() -> None:
    with pytest.raises(ValueError, match="unknown voice engine"):
        build("elevenlabs")


def test_every_advertised_engine_builds() -> None:
    assert all(build(engine) is not None for engine in ENGINES)


def test_the_preset_roster_is_five_male_and_five_female() -> None:
    assert len(SUPERTONIC_VOICES) == 10
    assert sum(v.startswith("M") for v in SUPERTONIC_VOICES) == 5
    assert sum(v.startswith("F") for v in SUPERTONIC_VOICES) == 5
    assert DEFAULT_SUPERTONIC_VOICE in SUPERTONIC_VOICES


def test_silent_backend_records_speech_and_chimes() -> None:
    voice = SilentVoice()
    voice.speak("hello")
    voice.speak("")  # empty text is not speech
    voice.chime("start")
    assert voice.said == ["hello"]
    assert voice.chimed == ["start"]


# --- chunking -------------------------------------------------------------


def test_short_text_is_not_chunked() -> None:
    assert split_sentences("Pigeon, right side.") == ["Pigeon, right side."]


def test_empty_text_yields_no_chunks() -> None:
    assert split_sentences("   ") == []


def test_long_text_splits_on_sentence_boundaries_without_losing_words() -> None:
    text = (
        "From all fours, slide the right knee toward the right wrist. "
        "Extend the left leg straight back behind you. "
        "Square the hips forward and let the chest come down over the front shin."
    )
    chunks = split_sentences(text)
    assert len(chunks) > 1
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")


def test_short_fragments_merge_forward() -> None:
    text = "Yes. No. " + "Now hold the position and breathe slowly through the nose. " * 2
    chunks = split_sentences(text)
    assert chunks[0] != "Yes."


def test_chunks_render_and_play_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each chunk is rendered exactly once, in spoken order, with lookahead."""
    played: list[str] = []

    class _Proc:
        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            assert timeout is None or timeout > 0
            return 0

        def terminate(self) -> None:
            return None

    class _FakeTTS:
        def __init__(self) -> None:
            self.synthesized: list[str] = []

        def get_voice_style(self, voice_name: str) -> str:
            return f"style:{voice_name}"

        def synthesize(self, text: str, lang: str, voice_style: str):
            # Assert rather than ignore: every chunk must carry the session's
            # language and the style resolved from the chosen preset.
            assert lang == "en"
            assert voice_style == "style:M3"
            self.synthesized.append(text)
            return ([0.0], 1.0)

        def save_audio(self, wav, path: str) -> None:
            return None

    import tempfile

    # neural.py binds `_play` at import, so patch it there, not on service.
    monkeypatch.setattr(neural, "_play", lambda path: (played.append(str(path)), _Proc())[1])
    fake = _FakeTTS()
    backend = SupertonicVoice(voice="M3")
    backend._tts = fake
    backend._style = fake.get_voice_style("M3")
    backend._tmp = tempfile.TemporaryDirectory(prefix="dotfiles-speak-test-")

    text = (
        "First sentence goes here and it is reasonably long. "
        "Second sentence follows it and is also reasonably long. "
        "Third sentence closes things out with enough words to matter."
    )
    backend.speak(text, wait=True)
    assert fake.synthesized == split_sentences(text)
    assert len(played) == len(fake.synthesized) > 1
