"""
Data Loader — YAML Source Material & Transformation Config
===========================================================
Loads and validates the structured data files that feed
the transformation pipeline.

This module is the "knowledge integration" component:
it takes curated, structured knowledge about the source
narrative and transformation rules, and makes them
available to the prompt templates.
"""

import yaml
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"


def load_source_material(path: str = None) -> dict:
    """Load the source narrative metadata."""
    filepath = Path(path) if path else DATA_DIR / "source_material.yaml"
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Validate essential fields
    required = ["title", "themes", "characters", "plot_beats", "motifs"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Source material missing required fields: {missing}")

    print(f"[DATA] Loaded source: {data['title']}")
    print(f"       {len(data['characters'])} characters, {len(data['plot_beats'])} plot beats")
    return data


def load_transformation_config(path: str = None) -> dict:
    """Load the transformation rules and target world definition."""
    filepath = Path(path) if path else DATA_DIR / "transformation_config.yaml"
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    required = ["target_world", "character_mappings", "motif_mappings", "plot_beat_mappings"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Transformation config missing required fields: {missing}")

    print(f"[DATA] Loaded transformation: → {data['target_world']['name']}")
    print(f"       {len(data['character_mappings'])} character mappings, "
          f"{len(data['plot_beat_mappings'])} plot beat mappings")
    return data


def get_themes_summary(source: dict) -> str:
    """Create a comma-separated summary of theme descriptions."""
    return ", ".join(t["description"] for t in source["themes"])
