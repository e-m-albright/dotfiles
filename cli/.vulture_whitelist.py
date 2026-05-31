# Referenced dynamically via Protocol structural typing / Typer registration.
from dotfiles_cli.core import ports

_ = ports.ProcessRunner.run
_ = ports.FileSystem.read_text
_ = ports.FileSystem.write_text
_ = ports.FileSystem.exists
_ = ports.FileSystem.mkdir
_ = ports.Clock.now
