"""
run.py — Universal Narrative Transformation Engine
====================================================
Takes ANY story and reimagines it in ANY target world.

Usage:
    # Interactive mode
    python run.py

    # From files
    python run.py --source examples/hamlet.txt --world "Cyberpunk Tokyo, 2077"

    # Both from files
    python run.py --source examples/hamlet.txt --world examples/silicon_valley_2027.txt

    # Inline text
    python run.py --source "Romeo and Juliet by Shakespeare" --world "Rival AI research labs"

    # With options
    python run.py --source examples/shivaji_maharaj.txt --world "Space Opera" --temperature 0.9

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │  USER INPUT                                                  │
    │  ┌──────────────────────┐  ┌─────────────────────────────┐  │
    │  │  Source Story (text)  │  │  Target World (text)        │  │
    │  │  - Any story          │  │  - Any world description    │  │
    │  │  - Any length         │  │  - Genre, era, culture      │  │
    │  │  - Any format         │  │  - As detailed as you want  │  │
    │  └──────────┬───────────┘  └──────────────┬──────────────┘  │
    └─────────────┼──────────────────────────────┼────────────────┘
                  │                              │
                  ▼                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  TRANSFORMATION ENGINE (4-Stage LLM Chain)                   │
    │                                                              │
    │  ┌──────────┐    ┌───────────┐    ┌────────┐    ┌────────┐  │
    │  │ ANALYZE  │───→│ TRANSFORM │───→│OUTLINE │───→│GENERATE│  │
    │  │ Extract  │    │ Map to    │    │ Scene  │    │ Write  │  │
    │  │ DNA      │    │ new world │    │ by     │    │ final  │  │
    │  │          │    │           │    │ scene  │    │ story  │  │
    │  └──────────┘    └───────────┘    └────────┘    └────────┘  │
    │                                                              │
    │  + Narrative Ontology (vocabulary guide for the LLM)         │
    │  + Groq API (Llama 4 Maverick — open-source LLM)            │
    └──────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  OUTPUT                                                      │
    │  output/01_analyze.md     — Narrative DNA extraction         │
    │  output/02_transform.md   — Transformation plan              │
    │  output/03_outline.md     — Scene-by-scene structure         │
    │  output/04_final_story.md — The reimagined story             │
    │  output/final_output.md   — Combined document                │
    │  output/run_metadata.json — Reproducibility metadata         │
    └─────────────────────────────────────────────────────────────┘
"""

import argparse
import sys
import os
from pathlib import Path


def load_input(value: str) -> str:
    """
    Load input from a file path or use as inline text.
    If the value is a path to an existing file, read it.
    Otherwise, treat it as inline text.
    """
    path = Path(value)
    if path.exists() and path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return value.strip()


def interactive_mode() -> tuple:
    """Collect source story and target world interactively."""
    print("\n" + "=" * 60)
    print("  NARRATIVE TRANSFORMATION ENGINE")
    print("  Transform any story into any world")
    print("=" * 60)

    print("\n📖 SOURCE STORY")
    print("  Enter your story (summary, plot description, or full text).")
    print("  Or provide a file path (e.g., examples/hamlet.txt)")
    print("  Type 'END' on a new line when done.\n")

    lines = []
    while True:
        line = input("  > ")
        if line.strip().upper() == "END":
            break
        lines.append(line)

    source_text = "\n".join(lines).strip()

    # Check if it's a file path
    if len(lines) == 1:
        source_text = load_input(source_text)

    print(f"\n  ✓ Source loaded: {len(source_text)} chars")

    print("\n🌍 TARGET WORLD")
    print("  Describe the world you want to reimagine the story in.")
    print("  Examples: 'Cyberpunk Tokyo 2077', 'Medieval India',")
    print("            'Silicon Valley AI startup', 'Space Opera'")
    print("  Type 'END' on a new line when done.\n")

    lines = []
    while True:
        line = input("  > ")
        if line.strip().upper() == "END":
            break
        lines.append(line)

    target_world = "\n".join(lines).strip()

    if len(lines) == 1:
        target_world = load_input(target_world)

    print(f"\n  ✓ World loaded: {len(target_world)} chars")

    return source_text, target_world


def main():
    parser = argparse.ArgumentParser(
        description="Universal Narrative Transformation Engine — Any story → Any world",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                                              Interactive mode
  python run.py --source examples/hamlet.txt --world "Space Opera"
  python run.py --source "Romeo and Juliet" --world "Rival AI labs in 2030"
  python run.py --source examples/shivaji_maharaj.txt --world examples/silicon_valley_2027.txt
        """
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help="Source story: file path or inline text"
    )
    parser.add_argument(
        "--world", type=str, default=None,
        help="Target world: file path or inline text description"
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Override LLM model ID"
    )
    parser.add_argument(
        "--temperature", type=float, default=None,
        help="Override generation temperature (0.0 - 1.0)"
    )

    args = parser.parse_args()

    # Apply overrides
    if args.model:
        os.environ["MODEL_ID"] = args.model
    if args.temperature is not None:
        os.environ["TEMPERATURE"] = str(args.temperature)

    # Get inputs
    if args.source and args.world:
        source_text = load_input(args.source)
        target_world = load_input(args.world)
    elif args.source or args.world:
        print("Error: Both --source and --world are required in CLI mode.")
        print("       Or run without arguments for interactive mode.")
        sys.exit(1)
    else:
        source_text, target_world = interactive_mode()

    # Import engine (after env overrides are set)
    from pipeline.engine import TransformationEngine

    # Validate
    validation = TransformationEngine.validate_input(source_text, target_world)
    if not validation["valid"]:
        print("\n❌ Input validation failed:")
        for err in validation["errors"]:
            print(f"   [{err['field']}] {err['message']}")
        sys.exit(1)

    # Run
    try:
        engine = TransformationEngine()
        result = engine.transform(source_text, target_world)
        print(f"\n✅ Done! Check the output/ directory.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
