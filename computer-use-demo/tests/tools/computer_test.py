from unittest.mock import AsyncMock, patch

import pytest

from computer_use_demo.tools.computer import (
    ComputerTool,
    ScalingSource,
    ToolError,
    ToolResult,
)


@pytest.fixture
def computer_tool():
    return ComputerTool()


@pytest.mark.asyncio
async def test_computer_tool_mouse_move(computer_tool):
    with patch("pyautogui.moveTo") as mock_move:
        result = await computer_tool(action="mouse_move", coordinate=[100, 200])
        mock_move.assert_called_once_with(100, 200)
        assert result.output == "Mouse moved"


@pytest.mark.asyncio
async def test_computer_tool_type(computer_tool):
    with (
        patch("pyautogui.write") as mock_write,
        patch.object(
            computer_tool, "screenshot", new_callable=AsyncMock
        ) as mock_screenshot,
    ):
        mock_screenshot.return_value = ToolResult(base64_image="base64_screenshot")
        result = await computer_tool(action="type", text="Hello, World!")
        mock_write.assert_called_once_with("Hello, World!", interval=0.012)
        assert result.output == "Text typed"
        assert result.base64_image == "base64_screenshot"


@pytest.mark.asyncio
async def test_computer_tool_screenshot(computer_tool):
    with patch.object(
        computer_tool, "screenshot", new_callable=AsyncMock
    ) as mock_screenshot:
        mock_screenshot.return_value = ToolResult(base64_image="base64_screenshot")
        result = await computer_tool(action="screenshot")
        mock_screenshot.assert_called_once()
        assert result.base64_image == "base64_screenshot"


@pytest.mark.asyncio
async def test_computer_tool_scaling(computer_tool):
    computer_tool._scaling_enabled = True
    computer_tool.screen_width = 1920
    computer_tool.screen_height = 1080

    # Test scaling from API to computer
    x, y = computer_tool.scale_coordinates(ScalingSource.API, 1366, 768)
    assert x == 1920
    assert y == 1080

    # Test scaling from computer to API
    x, y = computer_tool.scale_coordinates(ScalingSource.COMPUTER, 1920, 1080)
    assert x == 1366
    assert y == 768

    # Test no scaling when disabled
    computer_tool._scaling_enabled = False
    x, y = computer_tool.scale_coordinates(ScalingSource.API, 1366, 768)
    assert x == 1366
    assert y == 768


@pytest.mark.asyncio
async def test_computer_tool_scaling_with_different_aspect_ratio(computer_tool):
    computer_tool._scaling_enabled = True
    computer_tool.screen_width = 1920
    computer_tool.screen_height = 1200  # 16:10 aspect ratio

    # Test scaling from API to computer
    x, y = computer_tool.scale_coordinates(ScalingSource.API, 1280, 800)
    assert x == 1920
    assert y == 1200

    # Test scaling from computer to API
    x, y = computer_tool.scale_coordinates(ScalingSource.COMPUTER, 1920, 1200)
    assert x == 1280
    assert y == 800


@pytest.mark.asyncio
async def test_computer_tool_no_scaling_for_unsupported_resolution(computer_tool):
    computer_tool._scaling_enabled = True
    computer_tool.screen_width = 4096
    computer_tool.screen_height = 2160

    # Test no scaling for unsupported resolution
    x, y = computer_tool.scale_coordinates(ScalingSource.API, 4096, 2160)
    assert x == 4096
    assert y == 2160

    x, y = computer_tool.scale_coordinates(ScalingSource.COMPUTER, 4096, 2160)
    assert x == 4096
    assert y == 2160


@pytest.mark.asyncio
async def test_computer_tool_scaling_out_of_bounds(computer_tool):
    computer_tool._scaling_enabled = True
    computer_tool.screen_width = 1920
    computer_tool.screen_height = 1080

    # Test scaling from API with out of bounds coordinates
    with pytest.raises(ToolError, match="Coordinates .*, .* are out of bounds"):
        x, y = computer_tool.scale_coordinates(ScalingSource.API, 2000, 1500)


@pytest.mark.asyncio
async def test_computer_tool_invalid_action(computer_tool):
    with pytest.raises(ToolError, match="Invalid action: invalid_action"):
        await computer_tool(action="invalid_action")


@pytest.mark.asyncio
async def test_computer_tool_missing_coordinate(computer_tool):
    with pytest.raises(ToolError, match="coordinate is required for mouse_move"):
        await computer_tool(action="mouse_move")


@pytest.mark.asyncio
async def test_computer_tool_missing_text(computer_tool):
    with pytest.raises(ToolError, match="text is required for type"):
        await computer_tool(action="type")


@pytest.mark.asyncio
async def test_computer_tool_click_actions(computer_tool):
    with (
        patch("pyautogui.click") as mock_click,
        patch("pyautogui.rightClick") as mock_right_click,
        patch("pyautogui.middleClick") as mock_middle_click,
    ):
        # Test left click
        result = await computer_tool(action="left_click")
        mock_click.assert_called_once()
        assert result.output == "left_click performed"

        # Test right click
        result = await computer_tool(action="right_click")
        mock_right_click.assert_called_once()
        assert result.output == "right_click performed"

        # Test middle click
        result = await computer_tool(action="middle_click")
        mock_middle_click.assert_called_once()
        assert result.output == "middle_click performed"

        # Test double click
        result = await computer_tool(action="double_click")
        assert (
            mock_click.call_count == 2
        )  # One from left_click and one from double_click
        assert result.output == "double_click performed"


@pytest.mark.asyncio
async def test_computer_tool_drag(computer_tool):
    with (
        patch("pyautogui.mouseDown") as mock_down,
        patch("pyautogui.moveTo") as mock_move,
        patch("pyautogui.mouseUp") as mock_up,
    ):
        result = await computer_tool(action="left_click_drag", coordinate=[100, 200])
        mock_down.assert_called_once()
        mock_move.assert_called_once_with(100, 200)
        mock_up.assert_called_once()
        assert result.output == "Mouse dragged"
