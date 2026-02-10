"""
Prompt Engine — Template Rendering with Jinja2
================================================
Loads prompt templates and fills them with structured data
from the source material and transformation config.

Design Decision:
- We use Jinja2 templates instead of f-strings because:
  1. Templates are version-controlled separately from code
  2. Non-engineers can edit prompts without touching Python
  3. Complex loops and conditionals are cleaner in Jinja2
  4. Templates are auditable artifacts for the submission
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class PromptEngine:
    """Renders prompt templates with structured data."""

    def __init__(self, prompts_dir: str = None):
        template_dir = Path(prompts_dir) if prompts_dir else PROMPTS_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            keep_trailing_newline=True,
        )
        print(f"[PROMPTS] Loaded templates from: {template_dir}")

    def render(self, template_name: str, **kwargs) -> str:
        """
        Render a prompt template with the given context variables.

        Args:
            template_name: Filename of the template (e.g., '01_world_building.txt')
            **kwargs: Variables to inject into the template

        Returns:
            Rendered prompt string
        """
        template = self.env.get_template(template_name)
        rendered = template.render(**kwargs)
        return rendered

    def render_world_building(self, transform_config: dict) -> str:
        """Stage 1: World building prompt."""
        return self.render(
            "01_world_building.txt",
            target_world=transform_config["target_world"],
            character_mappings=transform_config["character_mappings"],
        )

    def render_character_profiles(
        self, source: dict, transform_config: dict, world_bible: str
    ) -> str:
        """Stage 2: Character profiles prompt (chains from Stage 1 output)."""
        return self.render(
            "02_character_profiles.txt",
            source_characters=source["characters"],
            target_world=transform_config["target_world"],
            character_mappings=transform_config["character_mappings"],
            world_bible=world_bible,
        )

    def render_scene_outline(
        self, source: dict, transform_config: dict,
        world_bible: str, character_profiles: str
    ) -> str:
        """Stage 3: Scene outline prompt (chains from Stages 1 & 2)."""
        return self.render(
            "03_scene_outline.txt",
            source_plot_beats=source["plot_beats"],
            plot_beat_mappings=transform_config["plot_beat_mappings"],
            motif_mappings=transform_config["motif_mappings"],
            world_bible=world_bible,
            character_profiles=character_profiles,
        )

    def render_story_generation(
        self, source: dict, transform_config: dict,
        world_bible: str, character_profiles: str, scene_outline: str
    ) -> str:
        """Stage 4: Final story generation (chains from all previous stages)."""
        from pipeline.data_loader import get_themes_summary

        return self.render(
            "04_story_generation.txt",
            source_title=source["title"],
            target_world=transform_config["target_world"],
            themes_summary=get_themes_summary(source),
            motif_mappings=transform_config["motif_mappings"],
            world_bible=world_bible,
            character_profiles=character_profiles,
            scene_outline=scene_outline,
        )
