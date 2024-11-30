"""Tests for platform-specific tool selection."""

from unittest.mock import patch

from computer_use_demo.tools import get_shell_tool
from computer_use_demo.tools.bash import BashTool
from computer_use_demo.tools.windows import WindowsTool


def test_get_shell_tool_windows():
    """Test that WindowsTool is returned on Windows."""
    with patch("platform.system", return_value="Windows"):
        assert get_shell_tool() == WindowsTool


def test_get_shell_tool_linux():
    """Test that BashTool is returned on Linux."""
    with patch("platform.system", return_value="Linux"):
        assert get_shell_tool() == BashTool


def test_get_shell_tool_darwin():
    """Test that BashTool is returned on macOS."""
    with patch("platform.system", return_value="Darwin"):
        assert get_shell_tool() == BashTool
