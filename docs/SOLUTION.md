# Solution Documentation

## 1. Approach Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INPUT                                    │
│                                                                 │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │  Source Story (text)  │    │  Target World (text)         │  │
│  │  ──────────────────── │    │  ──────────────────────────  │  │
│  │  Any story — summary, │    │  Any world — genre, era,    │  │
│  │  plot, full text,     │    │  culture, technology level.  │  │
│  │  history, fiction,    │    │  "Cyberpunk Tokyo 2077"      │  │
│  │  user-written.        │    │  "Medieval India"            │  │
│  └──────────┬───────────┘    └──────────────┬───────────────┘  │
└─────────────┼───────────────────────────────┼───────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              NARRATIVE ONTOLOGY (reference guide)                │
│                                                                 │
│  Gives the LLM structured vocabulary for analysis:              │
│  • Themes (sovereignty, betrayal, loyalty, corruption...)       │
│  • Character Roles (protagonist, antagonist, mentor, pawn...)   │
│  • Plot Functions (inciting_revelation, test_of_truth...)       │
│  • Motif Categories (corruption, performance, surveillance...)  │
│  Used as guide, NOT constraint — LLM can go beyond it           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              4-STAGE CHAINED PIPELINE                            │
│                                                                 │
│  ┌───────────────────┐                                          │
│  │ Stage 1: ANALYZE  │──→ Narrative DNA (themes, characters,    │
│  │ Extract structure  │    plot beats, motifs, soul)             │
│  └────────┬──────────┘                                          │
│           │ output feeds ↓                                      │
│  ┌────────▼──────────┐                                          │
│  │ Stage 2: TRANSFORM│──→ Transformation plan (world bible,     │
│  │ Map to new world   │    character remaps, scene remaps)       │
│  └────────┬──────────┘                                          │
│           │ outputs feed ↓                                      │
│  ┌────────▼──────────┐                                          │
│  │ Stage 3: OUTLINE  │──→ Scene-by-scene structure (5 acts,     │
│  │ Structure scenes   │    12-15 scenes with details)            │
│  └────────┬──────────┘                                          │
│           │ all outputs feed ↓                                  │
│  ┌────────▼──────────┐                                          │
│  │ Stage 4: GENERATE │──→ Final reimagined story (2-3 pages)    │
│  │ Write the story    │                                          │
│  └───────────────────┘                                          │
│                                                                 │
│  LLM: Groq API (Llama 4 Maverick — open-source, ultra-fast)    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT                                        │
│                                                                 │
│  output/                                                        │
│  ├── 01_analyze.md          (narrative DNA)                     │
│  ├── 02_transform.md        (transformation plan)               │
│  ├── 03_outline.md          (scene structure)                   │
│  ├── 04_final_story.md      (reimagined narrative)              │
│  ├── final_output.md        (combined document)                 │
│  └── run_metadata.json      (reproducibility data)              │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Solution Design

### The Core Insight

Narrative transformation is NOT a single-prompt problem. Asking an LLM to 
"rewrite this story in a new world" produces surface-level costume changes.
The magic happens when you **decompose the task** and **chain the stages**.

### Why This Architecture Works

**Stage separation creates quality.** Each stage focuses on ONE task:
- Stage 1 (Analyze) extracts the story's DNA without worrying about the target world
- Stage 2 (Transform) maps elements without worrying about prose quality
- Stage 3 (Outline) structures scenes without worrying about final language
- Stage 4 (Generate) writes with full context from all previous stages

**Chaining creates consistency.** Stage 4 receives the SAME character names that 
Stage 2 defined, the SAME world rules that Stage 2 established, and the SAME scene 
structure that Stage 3 created. No hallucinated inconsistencies.

**The ontology creates shared vocabulary.** Without it, the LLM might use different 
terms in different stages ("the hero" vs "the main character" vs "the protagonist"). 
The ontology anchors the analysis in stable categories while remaining flexible.

### The Universal Design

The system is story-agnostic by design:
- **No per-story YAML schemas** — users provide plain text
- **No per-story code** — the same pipeline handles everything
- **No hardcoded character names** — the LLM discovers them from the source text
- **The engine interface is API-ready**: `engine.transform(source_text, target_world)`

This means:
- Hamlet → Silicon Valley works out of the box
- Shivaji Maharaj → Space Opera works with the same code
- A user's original story → Medieval Japan works with zero changes

## 3. Alternatives Considered

### Alternative A: Fully Prompt-Based (Single Shot)
```
"Rewrite Hamlet as a Silicon Valley story in 2500 words."
```
**Why rejected**: Produces costume changes, not genuine transformation. The LLM 
has to simultaneously handle analysis, mapping, structuring, AND writing. Quality 
suffers in ALL dimensions.

### Alternative B: Rigid Schema per Story (Over-engineering)
Hand-curate YAML files for every source story with fixed character slots, 
motif mappings, and plot beat structures.

**Why rejected**: Doesn't scale. Adding a new story requires schema work, not 
just text input. The system becomes a YAML editor, not a transformation engine.
The LLM is better at extracting narrative structure than human YAML curation.

### Alternative C: Few-Shot Prompting
Show 2-3 examples of transformations, then ask for a new one.

**Why partially adopted**: We adopted the PRINCIPLE (show the LLM what structure 
looks like) but not the METHOD (examples are too story-specific). Instead, we 
provide the ontology as a structural vocabulary — a meta-level few-shot guide.

### Alternative D: RAG with Full Source Text
Chunk the entire original text and retrieve relevant passages.

**Why rejected for this scope**: For well-known works, the LLM already knows the 
source. For user-written stories, the user provides a summary. RAG adds complexity 
without clear benefit for this use case. However, RAG could be valuable at scale 
(e.g., transforming a 300-page novel) as a future enhancement.

### What We Built: LLM-Driven Universal Pipeline
- **From A**: We kept the single coherent output goal
- **From B**: We kept the ontology concept (vocabulary, not schema)
- **From C**: We adopted meta-level structural guidance
- **From D**: We kept knowledge integration as a future option

## 4. Challenges & Mitigations

### Challenge 1: Thematic Coherence Across Stages
**Problem**: Stage 4 might forget themes identified in Stage 1.

**Mitigation**: Cumulative prompting — Stage 4 receives ALL previous outputs. 
The ontology provides stable vocabulary. The "Soul of the Story" extraction in 
Stage 1 creates an anchor that persists through all stages.

### Challenge 2: Universal Applicability
**Problem**: Will the same prompts work for Hamlet AND Shivaji Maharaj AND a 
user-written sci-fi story?

**Mitigation**: Prompts are task-oriented, not content-oriented. "Extract 
narrative DNA" works for any story. "Map to target world" works for any world. 
The ontology provides structural categories but doesn't force specific ones.

### Challenge 3: Rate Limits
**Problem**: Groq's free tier has per-minute token limits. A 4-stage pipeline 
with large prompts can exceed them.

**Mitigation**: Automatic retry with exponential backoff. 3 retries at 30/60/90 
second intervals. Intermediate outputs are saved, so a crash at Stage 4 doesn't 
lose Stages 1-3.

### Challenge 4: Avoiding Pastiche
**Problem**: The LLM might produce "Shakespeare in tech jargon" instead of a 
genuine reimagining.

**Mitigation**: Stage 1 extracts ABSTRACT narrative functions (not dialogue or 
specific events). The LLM never receives the original text for Stage 4 — only 
the structured analysis and transformation plan. It can't copy what it doesn't see.

### Challenge 5: Reproducibility
**Problem**: LLM outputs are non-deterministic.

**Mitigation**: All intermediate outputs are saved. Run metadata (model, 
temperature, timestamp) is recorded. Lower temperature increases reproducibility.

## 5. Future Improvements

### Immediate (Low Effort, High Impact)
1. **Streaming**: Add streaming to Stage 4 for progressive story display
2. **Stage caching**: If source text is identical, skip Stage 1 on re-runs
3. **Model selection per stage**: Use a fast model for analysis, a creative model for generation

### Medium-Term (Product Features)
4. **Web UI**: Streamlit/Gradio frontend — the engine already has a clean API:
   ```python
   @app.post("/transform")
   async def transform(req: TransformRequest):
       engine = TransformationEngine()
       return engine.transform(req.source, req.world)
   ```
5. **Multi-world comparison**: Same source → 3 different worlds, side by side
6. **Quality evaluation**: Stage 5 that scores the output for thematic fidelity, 
   character consistency, and narrative coherence

### Long-Term (Scaling)
7. **RAG for long sources**: Chunk and retrieve from 300-page novels
8. **Fine-tuning**: Train on high-quality narrative transformations
9. **User feedback loop**: Rate generated stories, use ratings to improve prompts
10. **Multi-language**: Transform stories into different languages, not just worlds
