"""
Scoring configuration data structures for the tuning system.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel
import json
import os


class FieldWeights(BaseModel):
    """Field-specific weights for FTS5 scoring."""
    quote_text: float = 1.0
    quote_keywords: float = 0.8
    book_keywords: float = 0.7
    themes: float = 0.6
    summary: float = 0.5
    book_title: float = 3.0
    book_authors: float = 2.5
    type: float = 0.4
    publisher: float = 0.3
    journal: float = 0.3


class ScoringConfig(BaseModel):
    """Global scoring configuration."""
    bm25_weight: float = 1.0
    phrase_bonus: float = 2.0
    field_weights: FieldWeights = FieldWeights()


class LocalOverrides(BaseModel):
    """Local overrides (deprecated)."""
    pass


class TuningProfile(BaseModel):
    """Complete tuning profile including config and overrides."""
    name: str
    description: str = ""
    config: ScoringConfig
    overrides: LocalOverrides = LocalOverrides()


class ScoringBreakdown(BaseModel):
    """Detailed score breakdown for debugging."""
    quote_id: int
    bm25_raw: float
    bm25_normalized: float
    field_score: float
    field_matches: Optional[Dict[str, float]] = {}
    phrase_bonus: float
    final_score: float


class TuningManager:
    """Manages tuning profiles and scoring configuration."""

    def __init__(self, profiles_dir: str = "tuning_profiles"):
        self.profiles_dir = profiles_dir
        self.current_config = ScoringConfig()
        self.current_overrides = LocalOverrides()
        self.current_profile_name = "default"

        # Ensure profiles directory exists
        os.makedirs(profiles_dir, exist_ok=True)

        # Load default profile if it exists
        self.load_default_profile()

    def load_default_profile(self):
        """Load the default profile on startup."""
        default_path = os.path.join(self.profiles_dir, "default.json")
        if os.path.exists(default_path):
            self.load_profile("default")
        else:
            # Create default profile
            default_profile = TuningProfile(
                name="default",
                description="Default scoring configuration",
                config=ScoringConfig(),
                overrides=LocalOverrides()
            )
            self.save_profile(default_profile)

    def get_current_config(self) -> ScoringConfig:
        """Get current scoring configuration."""
        return self.current_config

    def get_current_overrides(self) -> LocalOverrides:
        """Get current local overrides."""
        return self.current_overrides

    def update_config(self, config: ScoringConfig):
        """Update current scoring configuration."""
        self.current_config = config

    def update_overrides(self, overrides: LocalOverrides):
        """Update current local overrides."""
        self.current_overrides = overrides

    def save_profile(self, profile: TuningProfile):
        """Save a tuning profile to disk."""
        file_path = os.path.join(self.profiles_dir, f"{profile.name}.json")
        with open(file_path, 'w') as f:
            json.dump(profile.dict(), f, indent=2)

    def load_profile(self, name: str) -> bool:
        """Load a tuning profile from disk."""
        file_path = os.path.join(self.profiles_dir, f"{name}.json")
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            profile = TuningProfile(**data)
            self.current_config = profile.config
            self.current_overrides = profile.overrides
            self.current_profile_name = name
            return True
        except Exception:
            return False

    def list_profiles(self) -> list[str]:
        """List available profiles."""
        if not os.path.exists(self.profiles_dir):
            return []

        profiles = []
        for file in os.listdir(self.profiles_dir):
            if file.endswith('.json'):
                profiles.append(file[:-5])  # Remove .json extension
        return sorted(profiles)

    def get_profile_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get profile information without loading it."""
        file_path = os.path.join(self.profiles_dir, f"{name}.json")
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return {
                "name": data.get("name", name),
                "description": data.get("description", ""),
                "active": name == self.current_profile_name
            }
        except Exception:
            return None


# Global tuning manager instance
tuning_manager = TuningManager()