"""DataShell — REPL loop and main() entry point for nlp4j-data."""
from __future__ import annotations

import shlex
import sys

from .commands import CommandError, build_default_registry
from .context import DataShellContext

_VERSION = "0.1.0"
_BANNER = f"nlp4j-data {_VERSION}\nType 'help' or '?' for available commands.\n"
_PROMPT = ">> "


class DataShell:
    """Interactive REPL that dispatches lines to registered commands.

    Can be driven programmatically (useful for tests)::

        shell = DataShell()
        output = shell.execute("data input.jsonl")
        output = shell.execute("remove xxx")
        output = shell.execute("attrs")
    """

    def __init__(self) -> None:
        self.context = DataShellContext()
        self.registry = build_default_registry()

    def execute(self, line: str) -> str:
        """Parse *line* and execute the matching command.

        Returns the command's output string (may be empty).
        Raises :class:`CommandError` on usage errors.
        Raises :class:`SystemExit` for ``exit`` / ``quit``.
        """
        line = line.strip()
        if not line or line.startswith("#"):
            return ""

        try:
            tokens = shlex.split(line)
        except ValueError as e:
            raise CommandError(f"Parse error: {e}") from e

        cmd_name = tokens[0]
        args = tokens[1:]

        cmd = self.registry.get(cmd_name)
        if cmd is None:
            raise CommandError(
                f"Unknown command: {cmd_name!r}. Type 'help' for available commands."
            )

        result = cmd.execute(self.context, args)
        return result or ""

    def run(self) -> None:
        """Start the interactive REPL loop (reads from stdin)."""
        print(_BANNER)
        while True:
            try:
                line = input(_PROMPT)
            except (EOFError, KeyboardInterrupt):
                print()
                break

            try:
                output = self.execute(line)
                if output:
                    print(output)
            except CommandError as e:
                print(f"ERROR: {e}")
            except SystemExit:
                break
            except Exception as e:
                print(f"ERROR: {e}")


def main() -> None:
    """Entry point for the ``nlp4j-data`` console script."""
    shell = DataShell()
    shell.run()


if __name__ == "__main__":
    main()
