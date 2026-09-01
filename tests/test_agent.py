"""Unit tests for JarvisAgent conversational turns and tool routing."""
import pytest
from backend.ai.agent import AgentState, JarvisAgent
from backend.ai.providers import MockProvider
from backend.core.config import Settings
from backend.core.permissions import PermissionLevel, ToolPermissionPolicy
from backend.tools.registry import ToolRegistry, tool


@pytest.mark.asyncio
async def test_agent_greeting():
    """Test conversational turn without tool calls in Hindi."""
    agent = JarvisAgent()
    response = await agent.process_user_input("Hello Jarvis")
    assert response.state == AgentState.SPEAKING
    assert "Boss" in response.message or len(response.message.strip()) > 0


@pytest.mark.asyncio
async def test_agent_fast_youtube_open(monkeypatch):
    """Test instant 'play youtube karo' zero-latency command."""
    monkeypatch.setattr("subprocess.Popen", lambda cmd, shell=True: None)
    monkeypatch.setattr("webbrowser.open", lambda url, new=0, autoraise=True: None)

    agent = JarvisAgent()
    response = await agent.process_user_input("play youtube karo")
    assert response.state == AgentState.SPEAKING
    assert "Boss" in response.message
    assert len(response.tool_results) >= 1
    assert response.tool_results[0].success is True


@pytest.mark.asyncio
async def test_agent_fast_youtube_click(monkeypatch):
    """Test instant 'aarush laila pe click karo' command."""
    monkeypatch.setattr("subprocess.Popen", lambda cmd, shell=True: None)
    monkeypatch.setattr("webbrowser.open", lambda url, new=0, autoraise=True: None)

    agent = JarvisAgent()
    response = await agent.process_user_input("aarush laila pe click karo")
    assert response.state == AgentState.SPEAKING
    assert "Boss" in response.message
    assert "Aarush Laila" in response.message
    assert len(response.tool_results) >= 1
    assert response.tool_results[0].success is True


@pytest.mark.asyncio
async def test_agent_tool_routing():
    """Test agent routing a request to the get_current_time tool."""
    agent = JarvisAgent()
    response = await agent.process_user_input("time kya hai")
    assert response.state == AgentState.SPEAKING
    assert "samay" in response.message.lower() or "boss" in response.message.lower()
    assert len(response.tool_results) >= 1
    assert response.tool_results[0].success is True


@pytest.mark.asyncio
async def test_agent_confirmation_flow():
    """Test pausing for confirmation when permission policy requires it."""
    # Create custom registry with Level 3 tool
    registry = ToolRegistry()

    @tool(
        name="delete_database",
        description="Destructive action",
        permission_level=PermissionLevel.LEVEL_3_DESTRUCTIVE,
        registry=registry,
    )
    def delete_database():
        return "Deleted"

    # Custom mock provider that calls delete_database
    class DeleteMockProvider(MockProvider):
        async def generate_response(self, messages, tools_schema=None):
            from backend.ai.providers import BaseAIResponse, ToolCall
            return BaseAIResponse(
                content="Deleting...",
                tool_calls=[ToolCall(name="delete_database", arguments={})],
            )

    settings = Settings(AUTO_CONFIRM_LEVEL_3=False)
    policy = ToolPermissionPolicy(settings=settings)
    agent = JarvisAgent(
        settings=settings,
        provider=DeleteMockProvider(settings=settings),
        registry=registry,
        permission_policy=policy,
    )

    # Turn 1: Trigger action -> Should pause for confirmation
    resp1 = await agent.process_user_input("Delete database")
    assert resp1.state == AgentState.AWAITING_CONFIRMATION
    assert agent.pending_action is not None

    # Turn 2: Confirm with "yes" -> Should execute
    resp2 = await agent.process_user_input("yes")
    assert resp2.state == AgentState.SPEAKING
    assert agent.pending_action is None
    assert resp2.tool_results[0].success is True
