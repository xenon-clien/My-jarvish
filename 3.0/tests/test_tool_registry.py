"""Unit tests for Tool Registry and Standard Tool Contract."""
import pytest
from pydantic import BaseModel, Field
from core.models import PermissionLevel, ToolCategory, ToolExecutionResult
from core.tool_contract import BaseTool
from core.tool_registry import ToolRegistry, default_registry, tool


class MockAddArgs(BaseModel):
    a: int = Field(..., description="First number")
    b: int = Field(..., description="Second number")


def test_tool_registration_and_execution():
    reg = ToolRegistry()

    @tool(
        name="math.add",
        description="Add two numbers together.",
        category=ToolCategory.SYSTEM,
        parameters_schema=MockAddArgs,
        registry=reg,
    )
    def add_numbers(a: int, b: int):
        return {"sum": a + b}

    assert reg.has_tool("math.add")
    t = reg.get("math.add")
    assert t is not None
    assert t.name == "math.add"
    assert t.category == ToolCategory.SYSTEM

    schema = t.get_schema()
    assert "parameters" in schema
    assert "properties" in schema["parameters"]
    assert "a" in schema["parameters"]["properties"]


@pytest.mark.asyncio
async def test_tool_async_execution():
    reg = ToolRegistry()

    @tool(
        name="test.echo",
        description="Echo input text.",
        category=ToolCategory.SYSTEM,
        registry=reg,
    )
    async def echo_tool(message: str):
        return f"Echo: {message}"

    res = await reg.execute("test.echo", message="hello jarvis")
    assert res.success is True
    assert res.data == "Echo: hello jarvis"


@pytest.mark.asyncio
async def test_missing_tool_execution():
    reg = ToolRegistry()
    res = await reg.execute("non_existent_tool")
    assert res.success is False
    assert "not currently installed" in res.error
