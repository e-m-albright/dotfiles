from dotfiles_cli.core.ports import Clock, FileSystem, ProcessRunner


def test_ports_are_runtime_checkable_protocols() -> None:
    # Protocols decorated runtime_checkable support isinstance against duck types.
    class DummyRunner:
        def run(self, command, *, check=False, env=None): ...

    assert isinstance(DummyRunner(), ProcessRunner)
    assert not isinstance(object(), ProcessRunner)
    assert not isinstance(object(), FileSystem)
    assert not isinstance(object(), Clock)
