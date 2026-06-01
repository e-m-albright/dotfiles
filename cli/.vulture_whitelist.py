# Referenced dynamically via Protocol structural typing / Typer registration.
from tests.fakes import FakeProcessRunner

from dotfiles.core import ports, sessions

_ = ports.ProcessRunner.run
_ = sessions.SessionLauncher.pick
_ = sessions.SessionLauncher.attach
_ = ports.HttpClient.get_json
_ = ports.HttpClient.post_json
_ = FakeProcessRunner.inputs
_ = FakeProcessRunner.calls_with_input
