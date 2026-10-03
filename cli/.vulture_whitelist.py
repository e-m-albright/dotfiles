# Referenced dynamically via Protocol structural typing / Typer registration.
import dotfiles.ports as ports
from dotfiles.testing.fakes import FakeProcessRunner

_ = ports.ProcessRunner.run
_ = FakeProcessRunner.inputs
_ = FakeProcessRunner.calls_with_input
