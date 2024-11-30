import platform
from typing import Type

from .base import BaseAnthropicTool, ToolResult
from .bash import BashTool
from .collection import ToolCollection
from .computer import ComputerTool
from .edit import EditTool
from .windows import WindowsTool


def get_shell_tool() -> Type[BaseAnthropicTool]:
    """Get the appropriate shell tool for the current platform."""
    if platform.system() == "Windows":
        return WindowsTool
    return BashTool


__all__ = [
    "BashTool",
    "WindowsTool",
    "BaseAnthropicTool",
    "ComputerTool",
    "EditTool",
    "ToolCollection",
    "ToolResult",
    "get_shell_tool",
]
