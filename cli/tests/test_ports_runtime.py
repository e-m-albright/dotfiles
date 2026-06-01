from dotfiles.core.ports import ProcessRunner


def test_ports_are_runtime_checkable_protocols() -> None:
    # runtime_checkable validates method *names* only, not signatures — so these
    # assertions confirm structural subtyping works, not that signatures are correct.
    class DummyRunner:
        def run(self, command, *, check=False, env=None): ...

    assert isinstance(DummyRunner(), ProcessRunner)
    assert not isinstance(object(), ProcessRunner)
