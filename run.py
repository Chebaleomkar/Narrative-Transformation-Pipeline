"""
run.py — Narrative Transformation Pipeline (Entry Point)
=========================================================
Reimagines Shakespeare's Hamlet as a Silicon Valley AI startup tragedy.

Usage:
    python run.py                  # Run full pipeline
    python run.py --stage 1        # Run only Stage 1 (World Building)
    python run.py --stage 2        # Run Stages 1-2
    python run.py --stage 3        # Run Stages 1-3
    python run.py --stage 4        # Run full pipeline (same as no flag)

Prerequisites:
    1. pip install -r requirements.txt
    2. Copy .env.example to .env and add your HuggingFace API token
    3. python run.py

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │              STRUCTURED KNOWLEDGE BASE               │
    │   source_material.yaml    transformation_config.yaml │
    └───────────────┬─────────────────────┬───────────────┘
                    │                     │
                    ▼                     ▼
    ┌─────────────────────────────────────────────────────┐
    │              PROMPT ENGINE (Jinja2)                  │
    │   Templates + Data → Rendered Prompts               │
    └───────────────────────────┬─────────────────────────┘
                                │
                                ▼
    ┌─────────────────────────────────────────────────────┐
    │           4-STAGE CHAINED PIPELINE                   │
    │                                                      │
    │  Stage 1: World Building          → world_bible      │
    │       │                                              │
    │       ▼                                              │
    │  Stage 2: Character Profiles      → profiles         │
    │       │                                              │
    │       ▼                                              │
    │  Stage 3: Scene Outline           → outline          │
    │       │                                              │
    │       ▼                                              │
    │  Stage 4: Story Generation        → final_story      │
    │                                                      │
    │  (Each stage feeds its output into the next prompt)  │
    └───────────────────────────┬─────────────────────────┘
                                │
                                ▼
    ┌─────────────────────────────────────────────────────┐
    │              OUTPUT ASSEMBLY                         │
    │   Intermediates + Final Story + Metadata → output/  │
    └─────────────────────────────────────────────────────┘

Open-Source LLM: Uses HuggingFace Inference API with models like
Mixtral-8x7B-Instruct or Meta-Llama-3.1-8B-Instruct.
"""

import argparse
import sys

from pipeline.transformation import TransformationPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Narrative Transformation Pipeline — Reimagine classic stories in new worlds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                    Run the full 4-stage pipeline
  python run.py --stage 2          Run stages 1 and 2 only
  python run.py --model meta-llama/Meta-Llama-3.1-8B-Instruct
        """
    )
    parser.add_argument(
        "--stage", type=int, choices=[1, 2, 3, 4], default=4,
        help="Run pipeline up to this stage (default: 4 = full pipeline)"
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Override model ID (e.g., meta-llama/Meta-Llama-3.1-8B-Instruct)"
    )
    parser.add_argument(
        "--temperature", type=float, default=None,
        help="Override generation temperature (0.0 - 1.0)"
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help="Path to custom source material YAML"
    )
    parser.add_argument(
        "--transform", type=str, default=None,
        help="Path to custom transformation config YAML"
    )

    args = parser.parse_args()

    # Apply model override via environment if specified
    import os
    if args.model:
        os.environ["MODEL_ID"] = args.model
    if args.temperature is not None:
        os.environ["TEMPERATURE"] = str(args.temperature)

    try:
        pipeline = TransformationPipeline(
            source_path=args.source,
            transform_path=args.transform,
        )

        if args.stage >= 1:
            pipeline.stage_1_world_building()
        if args.stage >= 2:
            pipeline.stage_2_character_profiles()
        if args.stage >= 3:
            pipeline.stage_3_scene_outline()
        if args.stage >= 4:
            pipeline.stage_4_story_generation()
            pipeline._assemble_final_output()

        print("\n✅ Done! Check the output/ directory for results.")

    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline Error: {e}")
        raise


if __name__ == "__main__":
    main()
