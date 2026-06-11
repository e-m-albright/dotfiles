from dotfiles.adapters.ports import ProcessRunner


def test_process_runner_protocol_guards_its_method_set() -> None:
    # `@runtime_checkable` isinstance validates method *names* only — not
    # signatures or return types. So this guards exactly one thing, honestly: the
    # protocol's required method set. That's still worth a test — it fails loudly
    # if `run` is renamed on the protocol but not its implementers (or vice versa).
    # Signature/return conformance is covered by the real adapter tests + pyright.
    class Conforms:
        def run(self, command, *, check=False, env=None): ...

    class MissingRun:
        def execute(self, command): ...  # right idea, wrong method name

    assert isinstance(Conforms(), ProcessRunner)
    assert not isinstance(MissingRun(), ProcessRunner)  # missing `run` → not a runner
    assert not isinstance(object(), ProcessRunner)
