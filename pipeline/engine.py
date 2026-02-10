"""
Transformation Engine — Universal Narrative Transformer
=========================================================
The core system. Takes ANY source story (text) and ANY
target world (text description), and produces a reimagined
story through a 4-stage LLM chain.

Architecture:
  User Input:
    - source_text: Any story (paragraph, detailed plot, full text)
    - target_world: Any world description ("Cyberpunk Tokyo 2077",
      "AI startup in Silicon Valley", "Ancient Rome", etc.)

  Pipeline:
    Stage 1: ANALYZE  — Extract narrative DNA from source
    Stage 2: TRANSFORM — Map narrative elements to target world
    Stage 3: OUTLINE   — Create scene-by-scene structure
    Stage 4: GENERATE  — Write the final reimagined story

  Each stage's output feeds the next stage's prompt.

  Rate Limit Awareness:
    Groq free tier: 6,000 TPM for Llama 4 Maverick.
    Each stage uses a MINIMAL system prompt to stay under budget.
    65-second cooldown between stages ensures full TPM reset.

Design for Future API:
    engine = TransformationEngine()
    result = engine.transform(source_text, target_world)
    # result contains all intermediates + final story
    # Trivially wrappable in FastAPI / Streamlit / Gradio
"""

import json
import time
from pathlib import Path
from datetime import datetime

from pipeline.llm_client import LLMClient


# Cooldown between stages — must exceed 60s to reset Groq's TPM bucket
STAGE_COOLDOWN_SECONDS = 65

OUTPUT_DIR = Path(__file__).parent.parent / "output"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


def _load_text(filepath: Path) -> str:
    """Load a text file as string."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()


def _load_ontology_reference() -> str:
    """
    Load the narrative ontology and produce a condensed
    reference string for LLM context.

    The ontology gives the LLM a shared vocabulary for
    analyzing stories — used ONLY in Stage 1.
    """
    import yaml
    ontology_path = SCHEMAS_DIR / "narrative_ontology.yaml"

    if not ontology_path.exists():
        return ""

    with open(ontology_path, "r", encoding="utf-8") as f:
        onto = yaml.safe_load(f)

    # Build condensed reference — keep it SHORT
    lines = ["NARRATIVE VOCABULARY (reference guide):\n"]

    # Themes — just names
    themes = list(onto.get("themes", {}).keys())
    lines.append(f"THEMES: {', '.join(themes)}")

    # Character roles — just names + brief desc
    lines.append("\nCHARACTER ROLES:")
    for rid, rdata in onto.get("character_roles", {}).items():
        lines.append(f"  {rid}: {rdata['description'][:80]}")

    # Plot functions — just names
    plot_funcs = list(onto.get("plot_functions", {}).keys())
    lines.append(f"\nPLOT FUNCTIONS: {', '.join(plot_funcs)}")

    # Motif categories — just names
    motifs = list(onto.get("motif_categories", {}).keys())
    lines.append(f"\nMOTIF CATEGORIES: {', '.join(motifs)}")

    return "\n".join(lines)


# ── System messages: minimal to stay within TPM ──

SYSTEM_STAGE_1 = """You are a narrative analysis engine. Extract the structural DNA of stories.
Be thorough but concise. Use the provided vocabulary as a guide, not a constraint."""

SYSTEM_STAGE_2 = """You are a narrative transformation architect. Map story elements 
into new worlds. Make characters BELONG, not just wear costumes."""

SYSTEM_STAGE_3 = """You are a story structure architect. Create vivid, detailed scene 
outlines. Each scene should have clear emotional purpose."""

SYSTEM_STAGE_4 = """You are a literary fiction writer. Write with confidence, specificity, 
and emotional truth. The story must work for someone who never read the original."""


class TransformationEngine:
    """
    Universal narrative transformation engine.

    Usage:
        engine = TransformationEngine()
        result = engine.transform(
            source_text="The story of Hamlet...",
            target_world="AI startup in Silicon Valley, 2027"
        )
    """

    def __init__(self):
        self.llm = LLMClient()
        self.ontology_ref = _load_ontology_reference()

        # Load prompt templates
        self.prompts = {}
        for f in sorted(PROMPTS_DIR.glob("*.txt")):
            self.prompts[f.stem] = _load_text(f)

        OUTPUT_DIR.mkdir(exist_ok=True)

        print(f"[ENGINE] Initialized")
        print(f"[ENGINE] Ontology loaded: {len(self.ontology_ref)} chars")
        print(f"[ENGINE] Prompts loaded: {list(self.prompts.keys())}")

    def transform(
        self,
        source_text: str,
        target_world: str,
        callbacks: dict = None,
    ) -> dict:
        """
        Run the full transformation pipeline.

        Args:
            source_text: The source story (any length, any format)
            target_world: Description of the target world
            callbacks: Optional dict of stage_name → callable for progress tracking
                       (future: enables streaming in web UI)

        Returns:
            Dict with all intermediates + final story + metadata
        """
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "model": self.llm.model_id,
            "temperature": self.llm.temperature,
            "source_length": len(source_text),
            "target_world": target_world[:200],
        }

        print("\n" + "=" * 60)
        print("  NARRATIVE TRANSFORMATION ENGINE")
        print("=" * 60)
        print(f"  Source: {len(source_text)} chars")
        print(f"  Target: {target_world[:80]}...")
        print(f"  Cooldown: {STAGE_COOLDOWN_SECONDS}s between stages (6K TPM)")
        print("=" * 60)

        # ── Stage 1: ANALYZE ──
        # Include ontology reference IN the prompt (not system msg)
        # to give the LLM vocabulary for structured analysis.
        stage1_prompt = self.prompts.get("01_analyze", "")
        stage1_prompt = stage1_prompt.replace("{{source_text}}", source_text)
        stage1_prompt = stage1_prompt.replace("{{target_world}}", target_world)
        # Prepend ontology to the user prompt
        stage1_prompt = self.ontology_ref + "\n\n" + stage1_prompt

        analysis = self._call_llm(
            "Stage 1: ANALYZE — Extracting narrative DNA",
            stage1_prompt,
            SYSTEM_STAGE_1,
            "01_analyze",
        )
        if callbacks and "on_analysis" in callbacks:
            callbacks["on_analysis"](analysis)

        self._cooldown()

        # ── Stage 2: TRANSFORM ──
        # Only needs: analysis + target_world (source is already in analysis)
        stage2_prompt = self.prompts.get("02_transform", "")
        stage2_prompt = stage2_prompt.replace("{{analysis}}", analysis)
        stage2_prompt = stage2_prompt.replace("{{target_world}}", target_world)

        transformation = self._call_llm(
            "Stage 2: TRANSFORM — Mapping to target world",
            stage2_prompt,
            SYSTEM_STAGE_2,
            "02_transform",
        )
        if callbacks and "on_transformation" in callbacks:
            callbacks["on_transformation"](transformation)

        self._cooldown()

        # ── Stage 3: OUTLINE ──
        # Only needs: transformation (which contains analysis context)
        # DO NOT pass analysis again — saves tokens
        stage3_prompt = self.prompts.get("03_outline", "")
        stage3_prompt = stage3_prompt.replace("{{analysis}}", "")  # skip to save tokens
        stage3_prompt = stage3_prompt.replace("{{transformation}}", transformation)

        outline = self._call_llm(
            "Stage 3: OUTLINE — Creating scene structure",
            stage3_prompt,
            SYSTEM_STAGE_3,
            "03_outline",
        )
        if callbacks and "on_outline" in callbacks:
            callbacks["on_outline"](outline)

        self._cooldown()

        # ── Stage 4: GENERATE ──
        # Only needs: outline + transformation (compact context)
        # DO NOT pass source_text, analysis, or target_world — all embodied in outline
        stage4_prompt = self.prompts.get("04_generate", "")
        stage4_prompt = stage4_prompt.replace("{{analysis}}", "")  # skip
        stage4_prompt = stage4_prompt.replace("{{transformation}}", "")  # skip
        stage4_prompt = stage4_prompt.replace("{{outline}}", outline)

        story = self._call_llm(
            "Stage 4: GENERATE — Writing the reimagined story",
            stage4_prompt,
            SYSTEM_STAGE_4,
            "04_generate",
            use_long=True,
        )
        if callbacks and "on_story" in callbacks:
            callbacks["on_story"](story)

        # ── Assemble ──
        result = {
            "analysis": analysis,
            "transformation": transformation,
            "outline": outline,
            "story": story,
            "metadata": metadata,
        }

        self._save_outputs(result, source_text, target_world)

        print("\n" + "=" * 60)
        print("  ✅ TRANSFORMATION COMPLETE")
        print(f"  📄 Story: output/04_final_story.md")
        print(f"  📦 Full output: output/final_output.md")
        print("=" * 60)

        return result

    def _call_llm(self, label: str, prompt: str, system_msg: str, prompt_key: str, use_long: bool = False) -> str:
        """
        Call the LLM with a pre-built prompt and save the output.
        Uses minimal system messages to stay within TPM limits.
        """
        print(f"\n{'─' * 50}")
        print(f"  {label}")
        print(f"{'─' * 50}")
        print(f"  Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)")
        print(f"  System: {len(system_msg)} chars (~{len(system_msg)//4} tokens)")

        if use_long:
            result = self.llm.generate_long(prompt, system_message=system_msg)
        else:
            result = self.llm.generate(prompt, system_message=system_msg)

        print(f"  Output: {len(result)} chars (~{len(result)//4} tokens)")

        # Save intermediate
        stage_num = prompt_key[:2]
        stage_name = prompt_key[3:]
        filename = f"{stage_num}_{stage_name}.md"
        self._save_file(filename, result)

        return result

    def _cooldown(self):
        """Wait between stages to let the Groq TPM bucket reset."""
        print(f"\n  ⏸  Cooldown {STAGE_COOLDOWN_SECONDS}s (waiting for TPM reset)...")
        time.sleep(STAGE_COOLDOWN_SECONDS)

    def _save_outputs(self, result: dict, source_text: str, target_world: str):
        """Assemble and save all outputs."""
        # Save final story separately
        self._save_file("04_final_story.md", result["story"])

        # Save combined output
        combined = f"""# Narrative Transformation Output

**Generated:** {result['metadata']['timestamp']}
**Model:** {result['metadata']['model']}
**Source Length:** {result['metadata']['source_length']} chars
**Target World:** {result['metadata']['target_world']}

---

## Stage 1: Narrative Analysis

{result['analysis']}

---

## Stage 2: Transformation Plan

{result['transformation']}

---

## Stage 3: Scene Outline

{result['outline']}

---

## Stage 4: Final Reimagined Story

{result['story']}
"""
        self._save_file("final_output.md", combined)

        # Save metadata
        meta_path = OUTPUT_DIR / "run_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(result["metadata"], f, indent=2)
        print(f"  [SAVE] → output/run_metadata.json")

    def _save_file(self, filename: str, content: str):
        """Save a file to the output directory."""
        filepath = OUTPUT_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [SAVE] → output/{filename}")


    # ─────────────────────────────────────────────
    # VALIDATION (for future FastAPI integration)
    # ─────────────────────────────────────────────

    @staticmethod
    def validate_input(source_text: str, target_world: str) -> dict:
        """
        Validate user inputs before running the pipeline.
        Returns {"valid": True/False, "errors": [...]}

        Designed for FastAPI: POST /validate
        """
        errors = []

        if not source_text or len(source_text.strip()) < 20:
            errors.append({
                "field": "source_text",
                "message": "Source story must be at least 20 characters. "
                           "Provide a story summary, plot description, or full text."
            })

        if not target_world or len(target_world.strip()) < 5:
            errors.append({
                "field": "target_world",
                "message": "Target world must be at least 5 characters. "
                           "Examples: 'Cyberpunk Tokyo 2077', 'Medieval India', 'Space Opera'"
            })

        if len(source_text) > 50000:
            errors.append({
                "field": "source_text",
                "message": "Source text exceeds 50,000 characters. Please provide a shorter version or summary."
            })

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
