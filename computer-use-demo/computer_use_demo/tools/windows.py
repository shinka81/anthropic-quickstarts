import asyncio
import os
import subprocess
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolBash20241022Param

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult


class _WindowsSession:
    """A session of a Windows command prompt."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "cmd.exe"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self):
        if self._started:
            return

        self._process = await asyncio.create_subprocess_exec(
            self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

        self._started = True

    def stop(self):
        """Terminate the command prompt."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """Execute a command in the command prompt."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"cmd has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: cmd has not returned in {self._timeout} seconds and must be restarted",
            )

        # we know these are not None because we created the process with PIPEs
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # send command to the process
        full_command = f"{command} & echo {self._sentinel}\n"
        self._process.stdin.write(full_command.encode())
        await self._process.stdin.drain()

        # read output from the process, until the sentinel is found
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)
                    output = self._process.stdout._buffer.decode()  # pyright: ignore[reportAttributeAccessIssue]
                    if self._sentinel in output:
                        # strip the sentinel and break
                        output = output[: output.index(self._sentinel)]
                        break
        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"timed out: cmd has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        if output.endswith("\n"):
            output = output[:-1]

        error = self._process.stderr._buffer.decode()  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # clear the buffers
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


class WindowsTool(BaseAnthropicTool):
    """
    A tool that allows the agent to run Windows commands.
    The tool parameters are defined by Anthropic and are not editable.
    """

    _session: _WindowsSession | None
    name: ClassVar[Literal["bash"]] = "bash"  # Keep as "bash" for compatibility
    api_type: ClassVar[Literal["bash_20241022"]] = "bash_20241022"

    def __init__(self):
        self._session = None
        super().__init__()

    async def __call__(
        self, command: str | None = None, restart: bool = False, **kwargs
    ):
        if not restart and command is None:
            raise ToolError("no command provided.")

        if restart:
            if self._session:
                self._session.stop()
            self._session = _WindowsSession()
            await self._session.start()

            return ToolResult(system="tool has been restarted.")

        if self._session is None:
            self._session = _WindowsSession()
            await self._session.start()

        assert command is not None  # This satisfies the type checker
        return await self._session.run(command)

    def to_params(self) -> BetaToolBash20241022Param:
        """Return the parameters for this tool."""
        return {
            "type": self.api_type,
            "name": self.name,
        }
