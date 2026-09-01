"""Universal Human-Language Understanding Engine for JARVIS AI."""
from backend.nlu.models import (
    CandidateInterpretation,
    ExtractedEntities,
    NluDebugTrace,
    SemanticParseResult,
    UniversalIntent,
)
from backend.nlu.normalizer import LanguageNormalizer
from backend.nlu.entities import EntityResolver
from backend.nlu.semantic_engine import SemanticIntentEngine
from backend.nlu.router import UniversalIntentRouter, RoutedToolCall
from backend.nlu.debug import NluDebugLogger

__all__ = [
    "UniversalIntent",
    "ExtractedEntities",
    "CandidateInterpretation",
    "SemanticParseResult",
    "NluDebugTrace",
    "LanguageNormalizer",
    "EntityResolver",
    "SemanticIntentEngine",
    "UniversalIntentRouter",
    "RoutedToolCall",
    "NluDebugLogger",
]
