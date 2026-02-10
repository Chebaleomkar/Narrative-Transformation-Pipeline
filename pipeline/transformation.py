"""
Transformation Pipeline — The Core Orchestrator
=================================================
This is the heart of the system. It chains together
four LLM generation stages, where each stage's output
feeds into the next stage's prompt.

Pipeline Stages:
  1. World Building    → Establishes the target world
  2. Character Profiles → Develops characters in the new world
  3. Scene Outline     → Structures the reimagined plot
  4. Story Generation  → Writes the final narrative

This demonstrates:
  - Prompt chaining (each stage builds on previous outputs)
  - Structured prompt design (templates + data injection)
  - Knowledge integration (YAML data feeds into prompts)
  - Reproducibility (same inputs → deterministic pipeline flow)
"""

import json
from pathlib import Path
from datetime import datetime

from pipeline.llm_client import LLMClient
from pipeline.data_loader import load_source_material, load_transformation_config
from pipeline.prompt_engine import PromptEngine


OUTPUT_DIR = Path(__file__).parent.parent / "output"


class TransformationPipeline:
    """
    End-to-end narrative transformation pipeline.

    Orchestrates the four-stage chain:
    Source Material + Transformation Rules
        → World Bible
        → Character Profiles
        → Scene Outline
        → Final Story
    """

    def __init__(self, source_path: str = None, transform_path: str = None):
        print("=" * 60)
        print("  NARRATIVE TRANSFORMATION PIPELINE")
        print("=" * 60)

        # Load structured data
        self.source = load_source_material(source_path)
        self.transform_config = load_transformation_config(transform_path)

        # Initialize components
        self.llm = LLMClient()
        self.prompts = PromptEngine()

        # Stage outputs (accumulated through the chain)
        self.world_bible = None
        self.character_profiles = None
        self.scene_outline = None
        self.final_story = None

        # Metadata for reproducibility
        self.run_metadata = {
            "timestamp": datetime.now().isoformat(),
            "model": self.llm.model_id,
            "temperature": self.llm.temperature,
            "source": self.source["title"],
            "target_world": self.transform_config["target_world"]["name"],
        }

        OUTPUT_DIR.mkdir(exist_ok=True)

    def stage_1_world_building(self) -> str:
        """Stage 1: Generate the world bible for the target setting."""
        print("\n" + "─" * 50)
        print("STAGE 1: World Building")
        print("─" * 50)

        prompt = self.prompts.render_world_building(self.transform_config)
        print(f"[STAGE 1] Prompt length: {len(prompt)} chars")

        self.world_bible = self.llm.generate(prompt)
        print(f"[STAGE 1] Generated world bible: {len(self.world_bible)} chars")

        self._save_intermediate("01_world_bible.md", self.world_bible)
        return self.world_bible

    def stage_2_character_profiles(self) -> str:
        """Stage 2: Generate detailed character profiles (chains from Stage 1)."""
        if not self.world_bible:
            raise RuntimeError("Stage 1 (World Building) must run before Stage 2")

        print("\n" + "─" * 50)
        print("STAGE 2: Character Profiles")
        print("─" * 50)

        prompt = self.prompts.render_character_profiles(
            self.source, self.transform_config, self.world_bible
        )
        print(f"[STAGE 2] Prompt length: {len(prompt)} chars")

        self.character_profiles = self.llm.generate(prompt)
        print(f"[STAGE 2] Generated profiles: {len(self.character_profiles)} chars")

        self._save_intermediate("02_character_profiles.md", self.character_profiles)
        return self.character_profiles

    def stage_3_scene_outline(self) -> str:
        """Stage 3: Generate scene-by-scene outline (chains from Stages 1 & 2)."""
        if not self.character_profiles:
            raise RuntimeError("Stage 2 (Character Profiles) must run before Stage 3")

        print("\n" + "─" * 50)
        print("STAGE 3: Scene Outline")
        print("─" * 50)

        prompt = self.prompts.render_scene_outline(
            self.source, self.transform_config,
            self.world_bible, self.character_profiles
        )
        print(f"[STAGE 3] Prompt length: {len(prompt)} chars")

        self.scene_outline = self.llm.generate(prompt)
        print(f"[STAGE 3] Generated outline: {len(self.scene_outline)} chars")

        self._save_intermediate("03_scene_outline.md", self.scene_outline)
        return self.scene_outline

    def stage_4_story_generation(self) -> str:
        """Stage 4: Generate the final reimagined story (chains from all)."""
        if not self.scene_outline:
            raise RuntimeError("Stage 3 (Scene Outline) must run before Stage 4")

        print("\n" + "─" * 50)
        print("STAGE 4: Story Generation")
        print("─" * 50)

        prompt = self.prompts.render_story_generation(
            self.source, self.transform_config,
            self.world_bible, self.character_profiles, self.scene_outline
        )
        print(f"[STAGE 4] Prompt length: {len(prompt)} chars")

        # Use longer context for the final story
        self.final_story = self.llm.generate_long(prompt, max_tokens=4096)
        print(f"[STAGE 4] Generated story: {len(self.final_story)} chars")

        self._save_intermediate("04_final_story.md", self.final_story)
        return self.final_story

    def run(self) -> dict:
        """
        Execute the full pipeline end-to-end.

        Returns a dict containing all stage outputs and metadata.
        """
        print("\n🚀 Starting full pipeline run...\n")

        self.stage_1_world_building()
        self.stage_2_character_profiles()
        self.stage_3_scene_outline()
        self.stage_4_story_generation()

        # Assemble final output
        result = self._assemble_final_output()

        print("\n" + "=" * 60)
        print("✅ PIPELINE COMPLETE")
        print(f"   Final story: output/04_final_story.md")
        print(f"   Full output: output/final_output.md")
        print(f"   Run metadata: output/run_metadata.json")
        print("=" * 60)

        return result

    def _assemble_final_output(self) -> dict:
        """Assemble all outputs into a single deliverable document."""
        assembled = f"""# Narrative Transformation: {self.source['title']}
# → {self.transform_config['target_world']['name']}

**Source:** {self.source['title']} by {self.source['author']}
**Target World:** {self.transform_config['target_world']['name']}
**Model:** {self.llm.model_id}
**Generated:** {self.run_metadata['timestamp']}

---

## Intermediate Artifact 1: World Bible

{self.world_bible}

---

## Intermediate Artifact 2: Character Profiles

{self.character_profiles}

---

## Intermediate Artifact 3: Scene Outline

{self.scene_outline}

---

## Final Output: Reimagined Story

{self.final_story}
"""
        self._save_intermediate("final_output.md", assembled)

        # Save run metadata
        metadata_path = OUTPUT_DIR / "run_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.run_metadata, f, indent=2)

        return {
            "world_bible": self.world_bible,
            "character_profiles": self.character_profiles,
            "scene_outline": self.scene_outline,
            "final_story": self.final_story,
            "metadata": self.run_metadata,
        }

    def _save_intermediate(self, filename: str, content: str):
        """Save intermediate stage output to disk."""
        filepath = OUTPUT_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[SAVE] → output/{filename}")
