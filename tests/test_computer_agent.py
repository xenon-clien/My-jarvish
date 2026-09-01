"""Unit & Integration Tests for General Computer-Use AI Agent."""
import pytest
from backend.ai.state_observer import state_observer, ActiveComputerState
from backend.ai.verification_engine import verification_engine, VerificationResult
from backend.core.observability import observability, ObservabilityTrace
from backend.ai.action_planner import action_planner, PlanIntent
from backend.tools.ui_automation import (
    switch_window,
    click_element,
    scroll_screen,
    navigate_back_forward,
)


def test_state_observer_capture():
    """Verify that ComputerStateObserver captures computer state safely."""
    state = state_observer.capture_current_state()
    assert isinstance(state, ActiveComputerState)
    assert state.screen_width > 0
    assert state.screen_height > 0
    assert isinstance(state.running_applications, list)


def test_spatial_coordinate_resolution():
    """Verify spatial coordinate mapping ('upar wala', 'neeche wala', 'left', 'right')."""
    # Base rect: 0, 0, 1000, 1000
    base = (0, 0, 1000, 1000)
    
    top_x, top_y = state_observer.resolve_spatial_coordinates("upar wala", base_rect=base)
    assert top_y < 500  # Top half
    
    bottom_x, bottom_y = state_observer.resolve_spatial_coordinates("neeche wala", base_rect=base)
    assert bottom_y > 500  # Bottom half
    
    left_x, left_y = state_observer.resolve_spatial_coordinates("left side wala", base_rect=base)
    assert left_x < 400  # Left side
    
    right_x, right_y = state_observer.resolve_spatial_coordinates("right side wala", base_rect=base)
    assert right_x > 600  # Right side


def test_verification_engine():
    """Verify ActionVerificationEngine validates outcomes cleanly."""
    res = verification_engine.verify_action(
        action_name="switch_window",
        target="chrome",
    )
    assert isinstance(res, VerificationResult)
    assert res.is_verified is True


def test_observability_trace_formatting():
    """Verify structured observability trace formatting."""
    trace = ObservabilityTrace(
        command="Click the second channel",
        understood_intent="CLICK_ELEMENT",
        current_app="chrome.exe",
        plan_steps=["switch_window", "click_element"],
        selected_tool="click_element",
        target="second channel",
        verification_status="VERIFIED",
        result="SUCCESS",
        execution_time_ms=12.5,
    )
    banner = trace.format_banner()
    assert "OBSERVABILITY TRACE" in banner
    assert "CLICK_ELEMENT" in banner
    assert "chrome.exe" in banner


def test_cross_app_action_planning():
    """Verify ActionPlanner handles cross-application and spatial commands."""
    # 1. History Navigation
    plan_back = action_planner.create_plan("back jao")
    assert plan_back is not None
    assert plan_back.steps[0].tool_call.name == "navigate_back_forward"
    assert plan_back.steps[0].tool_call.arguments["direction"] == "back"

    # 2. Screen Scrolling
    plan_scroll = action_planner.create_plan("neeche scroll karo")
    assert plan_scroll is not None
    assert plan_scroll.steps[0].tool_call.name == "scroll_screen"
    assert plan_scroll.steps[0].tool_call.arguments["direction"] == "down"

    # 3. Window Switching
    plan_switch = action_planner.create_plan("Chrome par switch karo")
    assert plan_switch is not None
    assert plan_switch.steps[0].tool_call.name == "switch_window"

    # 4. Spatial UI Element Clicking
    plan_spatial = action_planner.create_plan("isme jo upar wala hai uspe click karo")
    assert plan_spatial is not None
    assert plan_spatial.steps[0].tool_call.name == "click_element"
    assert "upar wala" in plan_spatial.steps[0].tool_call.arguments["target"]

    # 5. Ambiguous Channel Clarification
    plan_ambig = action_planner.create_plan("click on that random channel")
    assert plan_ambig is not None
    assert plan_ambig.is_direct_chat is True
    assert "ऊपर वाला या नीचे वाला" in plan_ambig.direct_chat_response

    # 6. Direct Episode Queries (e.g. "tarak mehta ep 312", "cid episode 500")
    plan_ep = action_planner.create_plan("tarak mehta ep 312")
    assert plan_ep is not None
    assert plan_ep.intent == PlanIntent.PLAY_VIDEO
    assert "312" in plan_ep.steps[0].tool_call.arguments["query"]
