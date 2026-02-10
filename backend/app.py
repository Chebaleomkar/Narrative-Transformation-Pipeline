"""
FastAPI Backend — Narrative Transformation Engine
===================================================
Provides streaming API endpoints for the transformation pipeline.
Uses Server-Sent Events (SSE) so the client sees real-time progress
through each stage of the pipeline.

Endpoints:
    POST /api/transform  — Stream the 4-stage transformation (SSE)
    POST /api/validate   — Validate inputs before transforming
    GET  /api/examples   — Get example stories and worlds
    GET  /api/health     — Health check
"""

import json
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# ── Add project root to path for pipeline imports ──
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.llm_client import LLMClient

# ── Dirs ──
PROMPTS_DIR = PROJECT_ROOT / "prompts"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
OUTPUT_DIR = PROJECT_ROOT / "output"

# ── Rate limit config ──
# Groq free tier: 6,000 TPM for Llama 4 Maverick
# 65s cooldown ensures full TPM bucket reset between stages
STAGE_COOLDOWN = 65
COOLDOWN_TICK_INTERVAL = 5  # seconds between progress updates


# ── Minimal system prompts (to save tokens) ──
SYSTEM_PROMPTS = {
    1: "You are a narrative analysis engine. Extract the structural DNA of stories. Be thorough but concise.",
    2: "You are a narrative transformation architect. Map story elements into new worlds. Make characters BELONG, not just wear costumes.",
    3: "You are a story structure architect. Create vivid, detailed scene outlines with clear emotional purpose.",
    4: "You are a literary fiction writer. Write with confidence, specificity, and emotional truth.",
}

STAGE_INFO = {
    1: {"name": "ANALYZE", "message": "Extracting narrative DNA...", "desc": "Identifying themes, characters, plot beats, motifs, and the soul of the story"},
    2: {"name": "TRANSFORM", "message": "Mapping to target world...", "desc": "Creating world bible, character mappings, plot remappings, and motif translations"},
    3: {"name": "OUTLINE", "message": "Creating scene structure...", "desc": "Building a 5-act, scene-by-scene outline with emotional beats"},
    4: {"name": "GENERATE", "message": "Writing the reimagined story...", "desc": "Crafting the final narrative with dialogue, motifs, and earned endings"},
}


# ── Helpers ──

def load_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_ontology_ref() -> str:
    """Load condensed narrative ontology for Stage 1 context."""
    import yaml
    path = SCHEMAS_DIR / "narrative_ontology.yaml"
    if not path.exists():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        onto = yaml.safe_load(f)

    lines = ["NARRATIVE VOCABULARY (reference guide):\n"]
    themes = list(onto.get("themes", {}).keys())
    lines.append(f"THEMES: {', '.join(themes)}")

    lines.append("\nCHARACTER ROLES:")
    for rid, rdata in onto.get("character_roles", {}).items():
        lines.append(f"  {rid}: {rdata['description'][:80]}")

    plot_funcs = list(onto.get("plot_functions", {}).keys())
    lines.append(f"\nPLOT FUNCTIONS: {', '.join(plot_funcs)}")

    motifs = list(onto.get("motif_categories", {}).keys())
    lines.append(f"\nMOTIF CATEGORIES: {', '.join(motifs)}")

    return "\n".join(lines)


# ── App ──

app = FastAPI(
    title="Narrative Transformation Engine",
    description="Transform any story into any world using LLM-powered narrative analysis",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──

class TransformRequest(BaseModel):
    source_text: str
    target_world: str


# ── Endpoints ──

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0"}


@app.post("/api/validate")
async def validate(req: TransformRequest):
    """Validate inputs before running the pipeline."""
    errors = []

    if not req.source_text or len(req.source_text.strip()) < 20:
        errors.append({
            "field": "source_text",
            "message": "Source story must be at least 20 characters."
        })

    if not req.target_world or len(req.target_world.strip()) < 5:
        errors.append({
            "field": "target_world",
            "message": "Target world must be at least 5 characters."
        })

    if len(req.source_text) > 50000:
        errors.append({
            "field": "source_text",
            "message": "Source text exceeds 50,000 characters."
        })

    return {"valid": len(errors) == 0, "errors": errors}


@app.get("/api/examples")
async def get_examples():
    """Return example stories and worlds for the UI."""
    examples = {"stories": {}, "worlds": {}}

    if EXAMPLES_DIR.exists():
        for f in sorted(EXAMPLES_DIR.glob("*.txt")):
            content = load_text(f)
            name = f.stem.replace("_", " ").title()

            # Categorize: files with "world" or specific world names go to worlds
            if any(w in f.stem.lower() for w in ["world", "silicon", "cyberpunk", "medieval", "space"]):
                examples["worlds"][name] = content
            else:
                examples["stories"][name] = content

    return examples


@app.post("/api/transform")
async def transform(req: TransformRequest):
    """
    Stream the 4-stage transformation pipeline via SSE.

    Events sent to client:
        stage_start     — A stage is beginning
        stage_complete  — A stage finished (includes full output)
        cooldown_start  — Rate limit cooldown beginning
        cooldown_tick   — Cooldown progress update (every 5s)
        complete        — Pipeline finished successfully
        error           — An error occurred
    """

    async def event_stream():
        try:
            # Initialize
            llm = LLMClient()
            ontology_ref = load_ontology_ref()
            prompts = {}
            for f in sorted(PROMPTS_DIR.glob("*.txt")):
                prompts[f.stem] = load_text(f)

            yield {"data": json.dumps({
                "type": "init",
                "message": "Engine initialized",
                "model": llm.model_id,
                "source_length": len(req.source_text),
                "target_world": req.target_world[:100],
            })}

            # Context accumulator — stores each stage's output
            context = {}
            stages_output = {}

            for stage_num in range(1, 5):
                info = STAGE_INFO[stage_num]
                sys_msg = SYSTEM_PROMPTS[stage_num]

                # ── Send stage_start ──
                yield {"data": json.dumps({
                    "type": "stage_start",
                    "stage": stage_num,
                    "name": info["name"],
                    "message": info["message"],
                    "description": info["desc"],
                })}

                # ── Build prompt ──
                prompt = _build_prompt(stage_num, prompts, req, context, ontology_ref)

                # ── Call LLM (blocking → run in thread) ──
                is_long = (stage_num == 4)
                if is_long:
                    result = await asyncio.to_thread(
                        llm.generate_long, prompt, sys_msg
                    )
                else:
                    result = await asyncio.to_thread(
                        llm.generate, prompt, sys_msg
                    )

                # Store result
                stage_key = {1: "analysis", 2: "transformation", 3: "outline", 4: "story"}
                context[stage_key[stage_num]] = result
                stages_output[stage_num] = result

                # ── Send stage_complete ──
                yield {"data": json.dumps({
                    "type": "stage_complete",
                    "stage": stage_num,
                    "name": info["name"],
                    "content": result,
                    "tokens": len(result),
                })}

                # ── Cooldown (except after last stage) ──
                if stage_num < 4:
                    yield {"data": json.dumps({
                        "type": "cooldown_start",
                        "stage": stage_num,
                        "seconds": STAGE_COOLDOWN,
                        "message": f"Waiting {STAGE_COOLDOWN}s for API rate limit reset...",
                    })}

                    elapsed = 0
                    while elapsed < STAGE_COOLDOWN:
                        await asyncio.sleep(COOLDOWN_TICK_INTERVAL)
                        elapsed += COOLDOWN_TICK_INTERVAL
                        remaining = max(0, STAGE_COOLDOWN - elapsed)
                        yield {"data": json.dumps({
                            "type": "cooldown_tick",
                            "seconds_remaining": remaining,
                            "progress": elapsed / STAGE_COOLDOWN,
                        })}

            # ── Save outputs ──
            OUTPUT_DIR.mkdir(exist_ok=True)
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "model": llm.model_id,
                "temperature": llm.temperature,
                "source_length": len(req.source_text),
                "target_world": req.target_world[:200],
            }

            _save_outputs(stages_output, metadata)

            # ── Send complete ──
            yield {"data": json.dumps({
                "type": "complete",
                "message": "Transformation complete!",
                "metadata": metadata,
            })}

        except Exception as e:
            yield {"data": json.dumps({
                "type": "error",
                "message": str(e),
            })}

    return EventSourceResponse(event_stream())


# ── Internal helpers ──

def _build_prompt(stage_num: int, prompts: dict, req: TransformRequest,
                  context: dict, ontology_ref: str) -> str:
    """
    Build the prompt for a given stage, injecting only the context it needs.
    Token-optimized: later stages skip redundant context.
    """
    prompt_keys = {1: "01_analyze", 2: "02_transform", 3: "03_outline", 4: "04_generate"}
    prompt = prompts.get(prompt_keys[stage_num], "")

    if stage_num == 1:
        # Stage 1: source + world + ontology
        prompt = prompt.replace("{{source_text}}", req.source_text)
        prompt = prompt.replace("{{target_world}}", req.target_world)
        prompt = ontology_ref + "\n\n" + prompt

    elif stage_num == 2:
        # Stage 2: analysis + world (no ontology needed)
        prompt = prompt.replace("{{analysis}}", context.get("analysis", ""))
        prompt = prompt.replace("{{target_world}}", req.target_world)

    elif stage_num == 3:
        # Stage 3: transformation only (analysis skipped to save tokens)
        prompt = prompt.replace("{{transformation}}", context.get("transformation", ""))
        prompt = prompt.replace("{{analysis}}", "")

    elif stage_num == 4:
        # Stage 4: outline only (everything else already embedded)
        prompt = prompt.replace("{{outline}}", context.get("outline", ""))
        prompt = prompt.replace("{{analysis}}", "")
        prompt = prompt.replace("{{transformation}}", "")

    return prompt


def _save_outputs(stages_output: dict, metadata: dict):
    """Save all pipeline outputs to the output/ directory."""
    stage_files = {1: "01_analyze.md", 2: "02_transform.md", 3: "03_outline.md", 4: "04_generate.md"}

    for num, filename in stage_files.items():
        content = stages_output.get(num, "")
        if content:
            with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as f:
                f.write(content)

    # Final story
    story = stages_output.get(4, "")
    with open(OUTPUT_DIR / "04_final_story.md", "w", encoding="utf-8") as f:
        f.write(story)

    # Combined
    combined = f"""# Narrative Transformation Output

**Generated:** {metadata['timestamp']}
**Model:** {metadata['model']}
**Source Length:** {metadata['source_length']} chars
**Target World:** {metadata['target_world']}

---

## Stage 1: Narrative Analysis

{stages_output.get(1, '')}

---

## Stage 2: Transformation Plan

{stages_output.get(2, '')}

---

## Stage 3: Scene Outline

{stages_output.get(3, '')}

---

## Stage 4: Final Reimagined Story

{stages_output.get(4, '')}
"""
    with open(OUTPUT_DIR / "final_output.md", "w", encoding="utf-8") as f:
        f.write(combined)

    with open(OUTPUT_DIR / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


# ── Run ──

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
