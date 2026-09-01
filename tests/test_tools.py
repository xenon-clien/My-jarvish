"""Unit tests for tool registry, execution, categorization, and system tools."""
import pytest
from pydantic import BaseModel, Field

from backend.core.permissions import PermissionLevel, ToolCategory
from backend.tools.registry import ToolRegistry, tool
from backend.tools.system_tools import (
    get_battery_status,
    get_current_time,
    get_network_status,
    get_storage_status,
    get_system_status,
)


class SampleArgs(BaseModel):
    number: int = Field(..., gt=0)


@pytest.mark.asyncio
async def test_tool_registration_and_execution():
    """Test custom tool registration, categorization, and execution."""
    registry = ToolRegistry()

    @tool(
        name="double_number",
        description="Double a positive integer",
        permission_level=PermissionLevel.LEVEL_0_SAFE,
        category=ToolCategory.SYSTEM,
        args_schema=SampleArgs,
        registry=registry,
    )
    def double_number(number: int):
        return number * 2

    assert registry.get("double_number") is not None

    # Verify OpenAI format schema
    openai_schemas = registry.get_openai_tool_schemas()
    assert len(openai_schemas) == 1
    assert openai_schemas[0]["type"] == "function"
    assert openai_schemas[0]["function"]["name"] == "double_number"

    # Valid call
    result = await registry.execute("double_number", number=5)
    assert result.success is True
    assert result.data == 10

    # Invalid argument validation test
    invalid_result = await registry.execute("double_number", number=-3)
    assert invalid_result.success is False
    assert "Invalid arguments" in (invalid_result.error or "")


@pytest.mark.asyncio
async def test_system_diagnostic_tools():
    """Test built-in system status, battery, storage, and network tools."""
    time_data = get_current_time()
    assert "time" in time_data

    status_data = get_system_status()
    assert "cpu_usage_percent" in status_data

    battery_data = get_battery_status()
    assert "has_battery" in battery_data

    storage_data = get_storage_status()
    assert "drives" in storage_data

    network_data = get_network_status()
    assert "hostname" in network_data
    assert "status" in network_data
