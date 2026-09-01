"""Semantic Search Result Matcher & Confidence Scorer for JARVIS AI.

Evaluates and ranks YouTube, Web, and Application search results against user intents
using multi-factor semantic similarity, entity overlap, and confidence scoring.
Prevents opening low-confidence or unrelated videos/results.
"""
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class MatchConfidenceTier:
    VERY_HIGH = "VERY_HIGH"  # >= 0.70 (Safe for direct auto-playback)
    MEDIUM = "MEDIUM"        # 0.45 - 0.69 (Good candidate, ask/confirm if ambiguous)
    LOW = "LOW"              # < 0.45 (Do NOT open blindly; ask for clarification)


class ScoredCandidate(BaseModel):
    """Represents a search result candidate with semantic ranking details."""
    id: str
    title: str
    channel: Optional[str] = ""
    duration_text: Optional[str] = ""
    is_short: bool = False
    confidence_score: float = 0.0
    tier: str = MatchConfidenceTier.LOW
    matched_keywords: List[str] = Field(default_factory=list)


class SemanticMatcher:
    """Intelligent semantic matcher calculating multi-factor relevance scores."""

    @staticmethod
    def extract_core_keywords(query: str) -> List[str]:
        """Extract important nouns, adjectives, and entity keywords from user query."""
        # Clean Hindi/Hinglish filler & command words
        stop_words = {
            "video", "song", "gaana", "chalao", "lagao", "play", "kholo", "open",
            "search", "on", "in", "mein", "pe", "par", "ka", "ki", "ke", "wala",
            "wali", "wale", "karo", "please", "dekho", "dekhao", "dikhao", "sunao",
            "youtube", "chrome", "the", "a", "an", "for", "of", "and", "with", "shivam", "ai", "jarvis"
        }
        words = re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", query.lower())
        return [w for w in words if w not in stop_words and len(w) > 1]

    @classmethod
    def calculate_similarity_score(
        cls,
        user_query: str,
        candidate_title: str,
        candidate_channel: str = "",
        is_short: bool = False,
    ) -> Tuple[float, List[str]]:
        """Calculate a composite relevance score (0.0 to 1.0) and matched keywords."""
        keywords = cls.extract_core_keywords(user_query)
        if not keywords:
            return 0.5, []

        title_lower = candidate_title.lower()
        channel_lower = candidate_channel.lower()
        full_text = f"{title_lower} {channel_lower}"

        matched = [kw for kw in keywords if kw in full_text]
        keyword_overlap = len(matched) / len(keywords)

        # 1. Exact phrase match bonus
        clean_user_phrase = " ".join(keywords)
        phrase_bonus = 0.0
        if clean_user_phrase and clean_user_phrase in title_lower:
            phrase_bonus = 0.35
        elif any(len(kw) > 3 and kw in title_lower for kw in keywords):
            # Check 2-word combinations
            for i in range(len(keywords) - 1):
                pair = f"{keywords[i]} {keywords[i+1]}"
                if pair in title_lower:
                    phrase_bonus = max(phrase_bonus, 0.25)

        # 2. Base score from keyword overlap
        base_score = keyword_overlap * 0.65

        # 3. Channel match bonus
        channel_bonus = 0.0
        if any(kw in channel_lower for kw in keywords):
            channel_bonus = 0.10

        # Composite score
        total_score = min(1.0, base_score + phrase_bonus + channel_bonus)

        # Smart Short vs Full Video Handling:
        wants_short = any(w in user_query.lower() for w in ["short", "shorts", "reel", "reels", "clip"])
        if is_short:
            if wants_short:
                total_score = min(1.0, total_score + 0.25)
            else:
                total_score *= 0.30
        else:
            if wants_short:
                total_score *= 0.60

        return round(total_score, 3), matched

    @classmethod
    def rank_candidates(
        cls,
        user_query: str,
        candidates: List[Dict[str, Any]],
    ) -> List[ScoredCandidate]:
        """Rank and score candidate search results, returning sorted list by confidence."""
        scored_list: List[ScoredCandidate] = []

        for item in candidates:
            if isinstance(item, ScoredCandidate):
                vid = item.id
                title = item.title
                channel = item.channel
                duration = item.duration_text
                is_short = item.is_short
            else:
                vid = item.get("id", "")
                title = item.get("title", "")
                channel = item.get("channel", "")
                duration = item.get("duration", "")
                is_short = item.get("is_short", False)

            score, matched = cls.calculate_similarity_score(
                user_query=user_query,
                candidate_title=title,
                candidate_channel=channel,
                is_short=is_short,
            )

            if score >= 0.70:
                tier = MatchConfidenceTier.VERY_HIGH
            elif score >= 0.45:
                tier = MatchConfidenceTier.MEDIUM
            else:
                tier = MatchConfidenceTier.LOW

            scored_list.append(
                ScoredCandidate(
                    id=vid,
                    title=title,
                    channel=channel,
                    duration_text=duration,
                    is_short=is_short,
                    confidence_score=score,
                    tier=tier,
                    matched_keywords=matched,
                )
            )

        # Sort descending by confidence score
        scored_list.sort(key=lambda x: x.confidence_score, reverse=True)
        return scored_list

    @classmethod
    def select_best_match(
        cls,
        user_query: str,
        candidates: List[Dict[str, Any]],
        confidence_threshold: float = 0.45,
    ) -> Tuple[Optional[ScoredCandidate], Optional[str]]:
        """Select the highest scoring candidate if above threshold, or return clarification advice."""
        ranked = cls.rank_candidates(user_query, candidates)
        if not ranked:
            return None, "No results found for search query."

        top_match = ranked[0]
        if top_match.confidence_score >= confidence_threshold:
            return top_match, None

        # Low confidence: clarify with user
        clean_q = " ".join(cls.extract_core_keywords(user_query))
        clarification = f"Mujhe '{clean_q}' ke liye exact match nahi mila. Kaun sa video chalaun?"
        return None, clarification


# Global singleton
semantic_matcher = SemanticMatcher()
