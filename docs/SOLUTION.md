# Solution Documentation

## 1. Approach Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                                  │
│                                                                 │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │  source_material.yaml │    │  transformation_config.yaml  │  │
│  │  ─────────────────── │    │  ──────────────────────────  │  │
│  │  • Title & metadata   │    │  • Target world definition   │  │
│  │  • Themes (abstract)  │    │  • Character mappings        │  │
│  │  • Characters (funcs) │    │  • Motif remappings          │  │
│  │  • Plot beats (funcs) │    │  • Plot beat mappings        │  │
│  │  • Motifs & symbols   │    │  • World internal rules      │  │
│  └──────────┬───────────┘    └──────────────┬───────────────┘  │
│             │                               │                   │
└─────────────┼───────────────────────────────┼───────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PROMPT ENGINE (Jinja2)                           │
│                                                                 │
│  Templates inject structured data into natural language prompts │
│  Each template is a separate, auditable file                    │
│  prompts/01_world_building.txt → 04_story_generation.txt       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              4-STAGE CHAINED PIPELINE                            │
│                                                                 │
│  ┌───────────────────┐                                          │
│  │ Stage 1:          │                                          │
│  │ WORLD BUILDING    │──→ world_bible (setting, rules, culture) │
│  └────────┬──────────┘                                          │
│           │ output feeds ↓                                      │
│  ┌────────▼──────────┐                                          │
│  │ Stage 2:          │                                          │
│  │ CHARACTER PROFILES│──→ detailed profiles in new world        │
│  └────────┬──────────┘                                          │
│           │ outputs feed ↓                                      │
│  ┌────────▼──────────┐                                          │
│  │ Stage 3:          │                                          │
│  │ SCENE OUTLINE     │──→ 5-act scene-by-scene structure        │
│  └────────┬──────────┘                                          │
│           │ all outputs feed ↓                                  │
│  ┌────────▼──────────┐                                          │
│  │ Stage 4:          │                                          │
│  │ STORY GENERATION  │──→ final 2-3 page reimagined narrative   │
│  └───────────────────┘                                          │
│                                                                 │
│  LLM: Groq API (Open-Source Models on LPU Hardware)            │
│  e.g., Llama 4 Maverick 17B, Mixtral, Gemma                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT ASSEMBLY                               │
│                                                                 │
│  output/                                                        │
│  ├── 01_world_bible.md          (intermediate)                  │
│  ├── 02_character_profiles.md   (intermediate)                  │
│  ├── 03_scene_outline.md        (intermediate)                  │
│  ├── 04_final_story.md          (deliverable)                   │
│  ├── final_output.md            (combined document)             │
│  └── run_metadata.json          (reproducibility)               │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Solution Design (End-to-End Explanation)

### Core Insight
Narrative transformation is not a single-prompt problem. Directly asking an LLM to 
"rewrite Hamlet as a tech startup story" produces surface-level results — costume 
changes over Shakespeare, not genuine reimagining. The system needs **decomposition**.

### The Framework
We decompose the problem into three orthogonal concerns:

1. **Source Analysis** (What makes this story THIS story?)
   - We extract abstract narrative components: character *functions* (not identities), 
     thematic *pillars* (not plot events), and symbolic *motifs* (not specific objects).
   - This lives in `source_material.yaml` — human-curated, structured knowledge.

2. **Transformation Rules** (How does each component map to the new world?)
   - Every character, motif, and plot beat has an explicit mapping with a *rationale*.
   - The target world has defined internal rules that constrain the transformation.
   - This lives in `transformation_config.yaml` — the creative design document.

3. **Generation Pipeline** (How do we produce coherent output?)
   - A 4-stage chain where each stage builds on previous outputs.
   - Stage 1 establishes the world → Stage 2 populates it with characters → 
     Stage 3 structures the plot → Stage 4 writes the story.
   - Each stage's prompt includes all relevant prior outputs, ensuring consistency.

### Why This Works
- **Consistency**: Characters introduced in Stage 2 exist in the world built in Stage 1.
- **Coherence**: The scene outline references the actual character profiles, not generic ones.
- **Reproducibility**: Same YAML inputs + same model = comparable outputs.
- **Transparency**: Every intermediate artifact is saved and inspectable.

## 3. Alternatives Considered

### Alternative A: Fully Prompt-Based (Single Shot)
```
"Rewrite Hamlet as a Silicon Valley AI startup story in 2500 words."
```
**Why rejected**: Produces shallow results. The LLM has to simultaneously handle world-building,
character development, plot structure, and prose style. Quality suffers in all dimensions.
No intermediate artifacts to inspect or iterate on.

### Alternative B: Few-Shot Prompting
Provide 2-3 examples of narrative transformations (e.g., Romeo & Juliet → rival labs),
then ask the model to do the same for Hamlet.

**Why partially adopted**: Few-shot examples don't scale — each transformation is too 
unique for generic examples to help. However, the *motif mapping* approach is inspired 
by few-shot thinking: we provide explicit source → target examples in our transformation 
config, which acts as structured few-shot context.

### Alternative C: RAG with Full Source Text
Feed the entire text of Hamlet through a retrieval system, chunked into scenes.

**Why rejected for this scope**: Hamlet is ~30,000 words. The bottleneck is not *access* 
to the source text (it's public domain, the LLM knows it) — it's *structured analysis* 
of narrative components. Our YAML-based approach is more efficient and more transparent 
than raw retrieval.

### What We Actually Built: Structured Pipeline with Knowledge Integration
- **From Alternative A**: We kept the single coherent output goal
- **From Alternative B**: We adopted structured examples (YAML mappings as implicit few-shot)
- **From Alternative C**: We kept the knowledge integration concept, but curated it manually 
  into YAML rather than using vector retrieval

## 4. Challenges & Mitigations

### Challenge 1: Thematic Coherence Across Stages
**Problem**: When Stage 4 writes the story, does it actually preserve the themes identified 
in the source material?

**Mitigation**: The prompt chain is cumulative — Stage 4 receives the world bible, character 
profiles, AND scene outline. The themes are embedded in every layer, not mentioned once and 
forgotten. The scene outline explicitly marks which motifs appear in each scene.

### Challenge 2: Character Consistency
**Problem**: An LLM might generate different personality details for the same character 
across different parts of a long output.

**Mitigation**: Stage 2 generates definitive character profiles ONCE, and these are 
injected verbatim into all subsequent prompts. The characters are "frozen" after Stage 2.

### Challenge 3: Avoiding Pastiche
**Problem**: The LLM might just paste Shakespeare quotes into tech jargon, creating a 
costume rather than a transformation.

**Mitigation**: We never feed the original Hamlet text to the LLM. The source material 
is abstracted into *functions and themes*, not dialogue or specific events. The LLM 
can't copy what it doesn't see in the prompt.

### Challenge 4: Reproducibility
**Problem**: LLM outputs are stochastic — running the same pipeline twice produces 
different results.

**Mitigation**: We save `run_metadata.json` with model ID, temperature, and timestamp. 
We save all intermediate artifacts. Lower temperature values increase reproducibility. 
The structured inputs (YAML) are deterministic anchors.

## 5. Future Improvements

### Scaling to a Full Product or API
1. **Multi-Source Support**: Create a library of `source_material.yaml` files for 
   different works. The pipeline already supports `--source` and `--transform` flags.

2. **Interactive Transformation Builder**: A web UI where users select a source work,
   choose a target world genre, and the system generates the transformation config 
   automatically (with human review).

3. **Quality Evaluation Loop**: Add a 5th stage that evaluates the generated story 
   against the source themes and scores it for thematic fidelity, character consistency, 
   and narrative coherence. Use this as a feedback signal.

4. **Model Fine-Tuning**: Fine-tune an open-source model on a dataset of high-quality 
   narrative transformations to improve output quality without increasing prompt length.

5. **Parallel Generation**: Run Stages 1 and 2 in parallel (they're semi-independent), 
   then merge for Stage 3. This halves the generation time.

6. **Version Control for Creativity**: Track different transformation configs for the 
   same source material. Compare "Hamlet in Silicon Valley" vs "Hamlet in Space" 
   vs "Hamlet in feudal Japan" — same pipeline, different configs.
