# Referenced dynamically via Protocol structural typing / Typer registration.
import dotfiles.cmd.session.service as sessions

import dotfiles.adapters.ports as ports
from dotfiles.testing.fakes import FakeProcessRunner

_ = ports.ProcessRunner.run
_ = sessions.SessionLauncher.pick
_ = sessions.SessionLauncher.attach
_ = FakeProcessRunner.inputs
_ = FakeProcessRunner.calls_with_input
