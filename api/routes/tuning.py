"""
Tuning endpoints for The Library API.
Provides configuration management and score debugging.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os

from api.models.scoring_config import (
    ScoringConfig, LocalOverrides, TuningProfile, ScoringBreakdown,
    tuning_manager
)
from api.services.scorer import scorer

router = APIRouter()


class TuningSearchRequest(BaseModel):
    query: str
    config: ScoringConfig
    overrides: LocalOverrides
    limit: int = 10


class TuningSearchResult(BaseModel):
    quote_id: int
    quote_text: str
    page: Optional[int]
    book_title: str
    book_authors: Optional[str]
    score_breakdown: ScoringBreakdown


class TuningSearchResponse(BaseModel):
    results: List[TuningSearchResult]
    total: int
    query: str
    config_used: ScoringConfig


@router.get("/config")
async def get_current_config():
    """Get current scoring configuration and overrides."""
    return {
        "config": tuning_manager.get_current_config(),
        "overrides": tuning_manager.get_current_overrides(),
        "profile": tuning_manager.current_profile_name
    }


@router.post("/config")
async def update_config(config: ScoringConfig):
    """Update current scoring configuration."""
    tuning_manager.update_config(config)
    return {"status": "updated", "config": config}


@router.post("/overrides")
async def update_overrides(overrides: LocalOverrides):
    """Update local overrides."""
    tuning_manager.update_overrides(overrides)
    return {"status": "updated", "overrides": overrides}


@router.get("/profiles")
async def list_profiles():
    """List available tuning profiles."""
    profiles = tuning_manager.list_profiles()
    profile_info = []

    for name in profiles:
        info = tuning_manager.get_profile_info(name)
        if info:
            profile_info.append(info)

    return {"profiles": profile_info}


@router.post("/profiles")
async def save_profile(profile: TuningProfile):
    """Save a new tuning profile."""
    try:
        tuning_manager.save_profile(profile)
        return {"status": "saved", "profile": profile.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {str(e)}")


@router.post("/profiles/{name}/activate")
async def activate_profile(name: str):
    """Activate a tuning profile."""
    if tuning_manager.load_profile(name):
        return {
            "status": "activated",
            "profile": name,
            "config": tuning_manager.get_current_config(),
            "overrides": tuning_manager.get_current_overrides()
        }
    else:
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")


@router.post("/search")
async def tuning_search(request: TuningSearchRequest):
    """Search with custom configuration and return detailed score breakdown."""
    if not request.query.strip():
        return TuningSearchResponse(
            results=[],
            total=0,
            query=request.query,
            config_used=request.config
        )

    # Temporarily update scorer configuration
    original_config = tuning_manager.get_current_config()
    original_overrides = tuning_manager.get_current_overrides()

    try:
        # Apply temporary configuration
        tuning_manager.update_config(request.config)
        tuning_manager.update_overrides(request.overrides)

        # Update scorer with new configuration
        scorer.update_config(request.config, request.overrides)

        # Perform search with detailed scoring
        results = scorer.search_with_breakdown(
            db_path="index/library.db",
            fts_query=request.query,
            exact_phrase=request.query if '"' in request.query else None,
            limit=request.limit
        )

        # Format results for tuning UI
        tuning_results = []
        for result in results.get("results", []):
            for quote in result.get("top_quotes", []):
                tuning_results.append(TuningSearchResult(
                    quote_id=quote["id"],
                    quote_text=quote["quote_text"],
                    page=quote.get("page"),
                    book_title=result["book"]["title"],
                    book_authors=result["book"].get("authors"),
                    score_breakdown=quote.get("score_breakdown", ScoringBreakdown(
                        quote_id=quote["id"],
                        bm25_raw=0.0,
                        bm25_normalized=0.0,
                        phrase_bonus=0.0,
                        book_boost=0.0,
                        quote_boost=0.0,
                        local_boost=0.0,
                        final_score=quote.get("score", 0.0)
                    ))
                ))

        return TuningSearchResponse(
            results=tuning_results[:request.limit],
            total=len(tuning_results),
            query=request.query,
            config_used=request.config
        )

    finally:
        # Restore original configuration
        tuning_manager.update_config(original_config)
        tuning_manager.update_overrides(original_overrides)
        scorer.update_config(original_config, original_overrides)


@router.post("/overrides/book/{book_id}")
async def set_book_boost(book_id: int, boost: float):
    """Set boost for a specific book."""
    current_overrides = tuning_manager.get_current_overrides()
    current_overrides.book_boosts[book_id] = boost
    tuning_manager.update_overrides(current_overrides)
    return {"status": "updated", "book_id": book_id, "boost": boost}


@router.delete("/overrides/book/{book_id}")
async def remove_book_boost(book_id: int):
    """Remove boost for a specific book."""
    current_overrides = tuning_manager.get_current_overrides()
    if book_id in current_overrides.book_boosts:
        del current_overrides.book_boosts[book_id]
        tuning_manager.update_overrides(current_overrides)
        return {"status": "removed", "book_id": book_id}
    else:
        raise HTTPException(status_code=404, detail=f"No boost set for book {book_id}")


@router.post("/overrides/quote/{quote_id}")
async def set_quote_boost(quote_id: int, boost: float):
    """Set boost for a specific quote."""
    current_overrides = tuning_manager.get_current_overrides()
    current_overrides.quote_boosts[quote_id] = boost
    tuning_manager.update_overrides(current_overrides)
    return {"status": "updated", "quote_id": quote_id, "boost": boost}


@router.delete("/overrides/quote/{quote_id}")
async def remove_quote_boost(quote_id: int):
    """Remove boost for a specific quote."""
    current_overrides = tuning_manager.get_current_overrides()
    if quote_id in current_overrides.quote_boosts:
        del current_overrides.quote_boosts[quote_id]
        tuning_manager.update_overrides(current_overrides)
        return {"status": "removed", "quote_id": quote_id}
    else:
        raise HTTPException(status_code=404, detail=f"No boost set for quote {quote_id}")


@router.get("/overrides/summary")
async def get_overrides_summary():
    """Get summary of current local overrides."""
    overrides = tuning_manager.get_current_overrides()
    return {
        "book_boosts_count": len(overrides.book_boosts),
        "quote_boosts_count": len(overrides.quote_boosts),
        "book_boosts": overrides.book_boosts,
        "quote_boosts": overrides.quote_boosts
    }