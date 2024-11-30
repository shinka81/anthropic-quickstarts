"""Tests for the WindowsTool class."""

import platform

import pytest

from computer_use_demo.tools.windows import ToolError, WindowsTool


@pytest.fixture
def windows_tool():
    return WindowsTool()


def requires_windows(func):
    """Decorator to skip tests on non-Windows platforms."""
    return pytest.mark.skipif(
        platform.system() != "Windows", reason="Test requires Windows"
    )(func)


@pytest.mark.asyncio
@requires_windows
async def test_windows_tool_restart(windows_tool):
    """Test that restarting the tool creates a new session."""
    result = await windows_tool(restart=True)
    assert result.system == "tool has been restarted."


@pytest.mark.asyncio
@requires_windows
async def test_windows_tool_run_command(windows_tool):
    """Test that running a command works."""
    result = await windows_tool(command="echo test")
    assert "test" in result.output


@pytest.mark.asyncio
async def test_windows_tool_no_command(windows_tool):
    """Test that running without a command raises an error."""
    with pytest.raises(ToolError, match="no command provided"):
        await windows_tool()


@pytest.mark.asyncio
@requires_windows
async def test_windows_tool_session_creation(windows_tool):
    """Test that a session is created when needed."""
    assert windows_tool._session is None
    await windows_tool(command="echo test")
    assert windows_tool._session is not None


@pytest.mark.asyncio
@requires_windows
async def test_windows_tool_session_reuse(windows_tool):
    """Test that the same session is reused."""
    await windows_tool(command="echo test")
    session = windows_tool._session
    await windows_tool(command="echo test2")
    assert windows_tool._session is session


@pytest.mark.asyncio
@requires_windows
async def test_windows_tool_session_error(windows_tool):
    """Test that running a command on a stopped session returns an error."""
    await windows_tool(command="echo test")
    windows_tool._session._process.returncode = 1
    result = await windows_tool(command="echo test")
    assert "tool must be restarted" in result.system


@pytest.mark.asyncio
@requires_windows
async def test_windows_tool_timeout(windows_tool):
    """Test that a long-running command times out."""
    windows_tool._session = None
    with pytest.raises(ToolError, match="timed out"):
        await windows_tool(command="timeout 10")
