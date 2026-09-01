"""JARVIS Universal App Skills Package.

Exposes Universal Action Engine, App Skill Registry, Capability Scanner,
Context State Manager, and Verification Engine.
"""
from backend.skills.models import (
    AppCapabilityMap,
    AppActionDefinition,
    AppFeatureMatrixEntry,
    AppContextState,
    ActionResult,
    CapabilityStatus,
    FallbackTier,
)
from backend.skills.actions import action_engine, UniversalActionEngine
from backend.skills.context import state_manager, relative_resolver, AppStateManager, RelativeCommandResolver
from backend.skills.scanner import capability_scanner, AppCapabilityScanner
from backend.skills.generator import skill_generator, AppSkillGenerator
from backend.skills.registry import skill_registry, AppSkillRegistry
from backend.skills.verifier import action_verifier, ActionVerifier

__all__ = [
    "AppCapabilityMap",
    "AppActionDefinition",
    "AppFeatureMatrixEntry",
    "AppContextState",
    "ActionResult",
    "CapabilityStatus",
    "FallbackTier",
    "action_engine",
    "UniversalActionEngine",
    "state_manager",
    "relative_resolver",
    "AppStateManager",
    "RelativeCommandResolver",
    "capability_scanner",
    "AppCapabilityScanner",
    "skill_generator",
    "AppSkillGenerator",
    "skill_registry",
    "AppSkillRegistry",
    "action_verifier",
    "ActionVerifier",
]
