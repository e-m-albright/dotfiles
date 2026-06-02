# Referenced dynamically via Protocol structural typing / Typer registration.
from dotfiles.adapters import ports
from dotfiles.cmd.session import service as sessions
from dotfiles.testing.fakes import FakeProcessRunner

_ = ports.ProcessRunner.run
_ = sessions.SessionLauncher.pick
_ = sessions.SessionLauncher.attach
_ = ports.HttpClient.get_json
_ = ports.HttpClient.post_json
_ = FakeProcessRunner.inputs
_ = FakeProcessRunner.calls_with_input
