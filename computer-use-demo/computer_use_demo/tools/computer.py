import asyncio
import base64
import os
import platform
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal, Sequence, TypedDict
from uuid import uuid4

from anthropic.types.beta import BetaToolComputerUse20241022Param

from .base import BaseAnthropicTool, ToolError, ToolResult

# Use appropriate temp directory
OUTPUT_DIR = tempfile.gettempdir() if platform.system() == "Windows" else "/tmp/outputs"

TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50

Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "screenshot",
    "cursor_position",
]


class Resolution(TypedDict):
    width: int
    height: int


MAX_SCALING_TARGETS: dict[str, Resolution] = {
    "XGA": Resolution(width=1024, height=768),  # 4:3
    "WXGA": Resolution(width=1280, height=800),  # 16:10
    "FWXGA": Resolution(width=1366, height=768),  # ~16:9
}


class ScalingSource(StrEnum):
    COMPUTER = "computer"
    API = "api"


class ComputerToolOptions(TypedDict):
    display_height_px: int
    display_width_px: int
    display_number: int | None


def chunks(s: str, chunk_size: int) -> list[str]:
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


class ComputerTool(BaseAnthropicTool):
    """A tool that allows the agent to control the computer."""

    name: ClassVar[Literal["computer"]] = "computer"
    api_type: ClassVar[Literal["computer_20241022"]] = "computer_20241022"
    screen_width: int
    screen_height: int
    display_num: int | None = None
    _screenshot_delay = 2.0
    _scaling_enabled = True

    @property
    def options(self) -> ComputerToolOptions:
        width, height = self.scale_coordinates(
            ScalingSource.COMPUTER, self.screen_width, self.screen_height
        )
        return {
            "display_width_px": width,
            "display_height_px": height,
            "display_number": self.display_num,
        }

    def __init__(self):
        """Initialize the computer tool."""
        try:
            os.environ.setdefault("DISPLAY", ":1")
            import pyautogui

            size = pyautogui.size()
            self.screen_width = size.width
            self.screen_height = size.height
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        except ImportError:
            self.screen_width = 1920  # Default fallback
            self.screen_height = 1080  # Default fallback

        super().__init__()

    def scale_coordinates(
        self, source: ScalingSource, x: int, y: int
    ) -> tuple[int, int]:
        """Scale coordinates to a target maximum resolution."""
        if not self._scaling_enabled:
            return x, y

        ratio = self.screen_width / self.screen_height
        target_dimension = None
        for dimension in MAX_SCALING_TARGETS.values():
            if abs(dimension["width"] / dimension["height"] - ratio) < 0.02:
                target_dimension = dimension
                break

        if target_dimension is None:
            # No matching aspect ratio found, return original coordinates
            return x, y

        if source == ScalingSource.API:
            # For unsupported resolutions, raise error
            if x > 1920 or y > 1200:
                raise ToolError(f"Coordinates {x}, {y} are out of bounds")

            # For 16:9 aspect ratio
            if abs(ratio - 16.0 / 9.0) < 0.02:
                if x > 1366 or y > 768:  # FWXGA resolution
                    raise ToolError(f"Coordinates {x}, {y} are out of bounds")
                scale_x = self.screen_width / 1366
                scale_y = self.screen_height / 768
                return int(x * scale_x), int(y * scale_y)

            # For 16:10 aspect ratio
            elif abs(ratio - 16.0 / 10.0) < 0.02:
                if x > 1280 or y > 800:  # WXGA resolution
                    raise ToolError(f"Coordinates {x}, {y} are out of bounds")
                scale_x = self.screen_width / 1280
                scale_y = self.screen_height / 800
                return int(x * scale_x), int(y * scale_y)

            # For other aspect ratios
            else:
                if x > target_dimension["width"] or y > target_dimension["height"]:
                    raise ToolError(f"Coordinates {x}, {y} are out of bounds")
                scale_x = self.screen_width / target_dimension["width"]
                scale_y = self.screen_height / target_dimension["height"]
                return int(x * scale_x), int(y * scale_y)
        else:
            # Scale from actual screen coordinates to API coordinates
            # For unsupported resolutions, raise error
            if self.screen_width > 1920 or self.screen_height > 1200:
                raise ToolError(f"Coordinates {x}, {y} are out of bounds")

            # For 16:9 aspect ratio
            if abs(ratio - 16.0 / 9.0) < 0.02:
                scale_x = 1366 / self.screen_width
                scale_y = 768 / self.screen_height
                return int(x * scale_x), int(y * scale_y)

            # For 16:10 aspect ratio
            elif abs(ratio - 16.0 / 10.0) < 0.02:
                scale_x = 1280 / self.screen_width
                scale_y = 800 / self.screen_height
                return int(x * scale_x), int(y * scale_y)

            # For other aspect ratios
            else:
                scale_x = target_dimension["width"] / self.screen_width
                scale_y = target_dimension["height"] / self.screen_height
                return int(x * scale_x), int(y * scale_y)

    async def screenshot(self) -> ToolResult:
        """Take a screenshot of the current screen and return the base64 encoded image."""
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"screenshot_{uuid4().hex}.png"

        try:
            import pyautogui

            screenshot = pyautogui.screenshot()
            screenshot.save(str(path))

            if self._scaling_enabled:
                from PIL import Image

                img = Image.open(path)
                x, y = self.scale_coordinates(
                    ScalingSource.COMPUTER,
                    int(self.screen_width),
                    int(self.screen_height),
                )
                img = img.resize((x, y), Image.Resampling.LANCZOS)
                img.save(path)

            if path.exists():
                return ToolResult(
                    base64_image=base64.b64encode(path.read_bytes()).decode()
                )
            else:
                raise ToolError("Screenshot file not found")
        except ImportError:
            return ToolResult(error="pyautogui is not installed")
        except Exception as e:
            raise ToolError(f"Failed to take screenshot: {str(e)}") from e

    async def __call__(
        self,
        *,
        action: Action,
        text: str | None = None,
        coordinate: Sequence[int] | None = None,
        **kwargs,
    ) -> ToolResult:
        """Execute the tool with the given arguments."""
        try:
            import pyautogui

            if action in ("mouse_move", "left_click_drag"):
                if coordinate is None:
                    raise ToolError(f"coordinate is required for {action}")
                if text is not None:
                    raise ToolError(f"text is not accepted for {action}")
                if not isinstance(coordinate, (tuple, list)) or len(coordinate) != 2:
                    raise ToolError(f"{coordinate} must be a sequence of length 2")
                if not all(isinstance(i, int) and i >= 0 for i in coordinate):
                    raise ToolError(
                        f"{coordinate} must be a sequence of non-negative ints"
                    )

                x, y = coordinate[0], coordinate[1]

                if action == "mouse_move":
                    pyautogui.moveTo(x, y)
                    return ToolResult(output="Mouse moved")
                elif action == "left_click_drag":
                    pyautogui.mouseDown()
                    pyautogui.moveTo(x, y)
                    pyautogui.mouseUp()
                    return ToolResult(output="Mouse dragged")

            if action in ("key", "type"):
                if text is None:
                    raise ToolError(f"text is required for {action}")
                if coordinate is not None:
                    raise ToolError(f"coordinate is not accepted for {action}")
                if not isinstance(text, str):
                    raise ToolError(output=f"{text} must be a string")

                if action == "key":
                    pyautogui.press(text)
                    return ToolResult(output="Key pressed")
                elif action == "type":
                    for chunk in chunks(text, TYPING_GROUP_SIZE):
                        pyautogui.write(chunk, interval=TYPING_DELAY_MS / 1000)
                    await asyncio.sleep(self._screenshot_delay)
                    screenshot_result = await self.screenshot()
                    return ToolResult(
                        output="Text typed",
                        base64_image=screenshot_result.base64_image,
                    )

            if action in (
                "left_click",
                "right_click",
                "double_click",
                "middle_click",
                "screenshot",
                "cursor_position",
            ):
                if text is not None:
                    raise ToolError(f"text is not accepted for {action}")
                if coordinate is not None:
                    raise ToolError(f"coordinate is not accepted for {action}")

                if action == "screenshot":
                    return await self.screenshot()
                elif action == "cursor_position":
                    pos = pyautogui.position()
                    x, y = self.scale_coordinates(
                        ScalingSource.COMPUTER, int(pos.x), int(pos.y)
                    )
                    return ToolResult(output=f"X={x},Y={y}")
                else:
                    click_funcs = {
                        "left_click": pyautogui.click,
                        "right_click": pyautogui.rightClick,
                        "middle_click": pyautogui.middleClick,
                        "double_click": lambda: pyautogui.click(clicks=2),
                    }
                    click_funcs[action]()
                    return ToolResult(output=f"{action} performed")

            raise ToolError(f"Invalid action: {action}")
        except ImportError:
            return ToolResult(error="pyautogui is not installed")

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {"name": self.name, "type": self.api_type, **self.options}
