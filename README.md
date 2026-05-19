# ci-bench-L1 — pyvalidate

> **Benchmark Level**: L1 · Easy &nbsp;|&nbsp; **~6,000 lines of Python** &nbsp;|&nbsp; **Domain**: Standalone validation library

---

## What is this repo?

`ci-bench-L1` is the **first benchmark repository** of the *Code Intelligence* suite — a collection of three Python codebases purpose-built to evaluate the performance of an **on-premise AI model + RAG (Retrieval-Augmented Generation) pipeline** on real source code.

This repo contains **pyvalidate**, a lightweight data-validation library inspired by Cerberus and Voluptuous. It is a self-contained, dependency-free Python package (~6,000 lines) that covers:

- Validators for strings, numbers, dates, collections, and composite rules
- A declarative `Schema` / `Field` API
- Type coercion and normalization transformers
- A thread-safe LRU `ValidationCache`
- Legacy helper functions that intentionally duplicate newer logic (used to test duplicate-code detection)

The codebase is designed to be **easy to navigate** — a good starting point for calibrating your RAG pipeline before moving to harder benchmarks (L2 and L3).

---

## Why this benchmark suite exists

Modern AI coding assistants rely on RAG to answer questions about a specific codebase. A RAG pipeline typically:

1. **Indexes** the repository (chunked by file, class, or function)
2. **Retrieves** the most relevant chunks for a given query
3. **Augments** the prompt of a local LLM (e.g. Code Llama, Mistral, DeepSeek Coder)
4. **Generates** a grounded answer

The quality of step 2 (retrieval) and step 4 (generation) degrades as the codebase grows in size and complexity. This benchmark suite provides **three codebases of increasing difficulty** plus standardised evaluation ground truth so you can measure exactly where and why your pipeline struggles.

```
ci-bench-L1  (~6k  lines)  → Easy:   single library, flat structure
ci-bench-L2  (~12k lines)  → Medium: layered API, cross-module flow
ci-bench-L3  (~18k lines)  → Hard:   framework, pluggable subsystems
```

---

## Repository structure

```
ci-bench-L1/
├── src/
│   └── pyvalidate/
│       ├── __init__.py              # Public API surface
│       ├── base.py                  # BaseValidator, ValidationResult, ValidationError
│       ├── validators/
│       │   ├── __init__.py
│       │   ├── string_validators.py # EmailValidator, URLValidator, RegexValidator,
│       │   │                        # LengthValidator, PatternValidator, SlugValidator
│       │   ├── numeric_validators.py# IntValidator, FloatValidator, RangeValidator,
│       │   │                        # PositiveValidator, PercentageValidator
│       │   ├── date_validators.py   # DateValidator, AgeValidator, DateRangeValidator,
│       │   │                        # FutureDateValidator, PastDateValidator
│       │   ├── collection_validators.py  # ListValidator, DictValidator, SetValidator,
│       │   │                             # TupleValidator, NonEmptyListValidator
│       │   └── composite_validators.py   # AllValidator, AnyValidator, ChainValidator,
│       │                                 # NotValidator, ConditionalValidator
│       ├── schema/
│       │   ├── field.py             # Field descriptor (validators + metadata)
│       │   ├── schema.py            # Schema, DynamicSchema, SchemaRegistry
│       │   └── errors.py            # SchemaError, FieldError, ErrorCollection
│       ├── transformers/
│       │   ├── converters.py        # to_int, to_float, to_bool, to_date, to_list, …
│       │   └── normalizers.py       # normalize_email, slugify, strip_html,
│       │                            # + legacy helpers (intentional duplication)
│       └── utils/
│           ├── cache.py             # ValidationCache — LRU, thread-safe, TTL
│           └── helpers.py           # is_empty, flatten_errors, deep_merge, safe_cast
├── tests/
│   ├── __init__.py
│   ├── test_string_validators.py
│   ├── test_numeric_validators.py
│   ├── test_date_validators.py
│   ├── test_composite_validators.py
│   ├── test_schema.py
│   ├── test_transformers.py
│   └── test_cache_and_helpers.py
├── benchmarks/
│   ├── ground_truth.json            # 20 Q&A pairs with expected source references
│   ├── code_similarity.json         # 10 semantically similar / duplicate code pairs
│   ├── metrics.py                   # P@K, R@K, F1@K, MRR, MAP, NDCG@K, Hit@K
│   └── eval_harness.py              # CLI runner — sends queries to your RAG API
└── pyproject.toml
```

---

## Key design patterns (relevant for RAG evaluation)

| Pattern | Where | RAG challenge |
|---------|-------|--------------|
| Shared abstract base | `base.py` → all validators | Can the model trace inheritance? |
| Decorator-style chaining | `ChainValidator`, `AllValidator` | Multi-file composition reasoning |
| Legacy duplication | `normalizers.py` vs `helpers.py` | Duplicate-code detection |
| Thread-safe singleton | `ValidationCache` | Concurrency / locking understanding |
| Declarative field binding | `Schema` + `Field` | Cross-file symbol resolution |
| Type coercion pipeline | `converters.py` + validators | Order-of-operations reasoning |

---

## Installation

```bash
# Clone
git clone https://github.com/ViciusLio/ci-bench-L1.git
cd ci-bench-L1

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# Install library + dev dependencies
pip install -e ".[dev]"
```

`pyproject.toml` dev extras include `pytest`, `pytest-cov`, and `ruff`.

---

## Using the library

```python
from pyvalidate import (
    EmailValidator, URLValidator, IntValidator,
    RangeValidator, Schema, Field,
)

# --- Single validator ---
v = EmailValidator()
result = v.validate("user@example.com")
print(result.is_valid)   # True
print(result.value)      # "user@example.com"

# --- Chained validators ---
from pyvalidate.validators.composite_validators import ChainValidator
chain = ChainValidator(IntValidator(coerce=True), RangeValidator(min_value=1, max_value=100))
r = chain.validate("42")
print(r.is_valid, r.value)   # True, 42

# --- Schema-based validation ---
class UserSchema(Schema):
    email = Field(EmailValidator())
    age   = Field(IntValidator(coerce=True), RangeValidator(min_value=0, max_value=150))
    website = Field(URLValidator(), required=False)

schema = UserSchema()
clean  = schema.validate_strict({"email": "alice@example.com", "age": "28"})
# clean = {"email": "alice@example.com", "age": 28}

errors = schema.validate({"email": "not-an-email", "age": -5})
print(errors)   # {"email": ["invalid email format"], "age": ["value must be >= 0"]}

# --- Validation cache ---
from pyvalidate.utils.cache import ValidationCache
cache = ValidationCache(max_size=256)
cache.set("key", result)
cached = cache.get("key")
```

---

## Running the test suite

```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src/pyvalidate --cov-report=term-missing

# Single module
pytest tests/test_schema.py -v
```

Expected output: **~120 tests**, all passing.

---

## Benchmark — evaluating your RAG pipeline

### Overview

The `benchmarks/` folder contains everything needed to score a RAG system against this codebase.

```
benchmarks/
├── ground_truth.json    # 20 natural-language queries + expected source locations
├── code_similarity.json # 10 pairs of semantically equivalent or duplicate snippets
├── metrics.py           # Pure-Python implementation of all retrieval metrics
└── eval_harness.py      # CLI that calls your RAG API and computes the score
```

### Ground truth format

```json
{
  "queries": [
    {
      "id": "q01",
      "question": "How does EmailValidator check the format of an address?",
      "category": "direct_retrieval",
      "expected_files": ["src/pyvalidate/validators/string_validators.py"],
      "expected_symbols": ["EmailValidator", "_EMAIL_REGEX"],
      "difficulty": "easy"
    },
    {
      "id": "q02",
      "question": "Is email normalization logic duplicated anywhere?",
      "category": "code_similarity",
      "expected_files": [
        "src/pyvalidate/transformers/normalizers.py",
        "src/pyvalidate/utils/helpers.py"
      ],
      "difficulty": "medium"
    }
  ]
}
```

### Query categories

| Category | Count | Description |
|----------|------:|-------------|
| `direct_retrieval` | 8 | Find where a specific class or function is defined |
| `behavioral` | 5 | Explain how a feature works (requires multi-chunk reasoning) |
| `cross_module` | 4 | Trace a concept across multiple files |
| `code_similarity` | 3 | Detect duplicated or equivalent logic |

### RAG API contract

The harness calls your RAG system via HTTP. Your endpoint must accept:

```
POST /query
Content-Type: application/json

{
  "question": "How does EmailValidator check the format?",
  "top_k": 10
}
```

And return:

```json
{
  "answer": "EmailValidator uses a compiled regex pattern ...",
  "sources": [
    {
      "file": "src/pyvalidate/validators/string_validators.py",
      "lines": [12, 45],
      "content": "class EmailValidator(BaseValidator): ..."
    }
  ]
}
```

### Running the evaluation

```bash
# Dry run — validates ground truth format, no RAG needed
python benchmarks/eval_harness.py --dry-run

# Full evaluation against a running RAG server
python benchmarks/eval_harness.py \
    --rag-url http://localhost:8080 \
    --top-k 10 \
    --output results_L1.json

# Specific metric only
python benchmarks/eval_harness.py --rag-url http://localhost:8080 --metric mrr

# Verbose mode (shows per-query detail)
python benchmarks/eval_harness.py --rag-url http://localhost:8080 --verbose
```

### Metrics explained

| Metric | Formula | What it tests |
|--------|---------|--------------|
| **P@K** | `relevant_in_top_k / k` | Precision of retrieved chunks |
| **R@K** | `relevant_in_top_k / total_relevant` | Coverage of relevant chunks |
| **F1@K** | `2·P·R / (P+R)` | Harmonic mean of precision and recall |
| **MRR** | `mean(1 / rank_of_first_relevant)` | How quickly the first correct file appears |
| **MAP** | `mean(AP per query)` | Area under precision-recall curve |
| **NDCG@K** | Normalised DCG | Ranking quality (penalises late relevant results) |
| **Hit@K** | `1 if any relevant in top-k else 0` | Coarse pass/fail per query |

### Expected baseline scores (L1 — easy)

A well-tuned RAG pipeline should achieve approximately:

| Metric | Target |
|--------|--------|
| Hit@5  | ≥ 0.85 |
| MRR    | ≥ 0.70 |
| MAP    | ≥ 0.65 |
| NDCG@10| ≥ 0.68 |

Scores significantly below these targets indicate issues with chunk size, embedding model choice, or retrieval strategy. Use L1 to tune before running L2/L3.

---

## Recommended RAG setup for local evaluation

```
Embedding model : nomic-embed-text / bge-m3 / text-embedding-3-small (OpenAI-compatible)
LLM             : Code Llama 13B / DeepSeek Coder 6.7B / Mistral 7B Instruct
Vector store    : Chroma / Qdrant / FAISS (local)
Chunk strategy  : Function-level splitting (recommended) or 512-token sliding window
Chunk overlap   : 64–128 tokens
```

---

## RAG Quick Start — query this repo with a local LLM

You can make this codebase directly queryable using the companion tools in the
[CodeIntelligence](https://github.com/ViciusLio/CodeIntelligence) project.

### 1. Generate the chunks (one-off)

```bash
git clone https://github.com/ViciusLio/CodeIntelligence
cd CodeIntelligence

# Parse ci-bench-L1 into semantic RAG chunks (stdlib only, no dependencies)
# Includes function/class chunks + cross-reference usage index
python parse_repo.py ../ci-bench-L1 --output ci_bench_L1_chunks.jsonl
# -> writes ~600 chunks (overview + file + function + class + usages)
```

### 2a. Query with Claude API (cloud)

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-...

python ask_repo.py ci_bench_L1_chunks.jsonl "How does EmailValidator check an address?"
```

### 2b. Query with a local LLM (Ollama — no API key needed)

```bash
# Install Ollama from https://ollama.com, then:
ollama pull qwen2.5-coder:7b   # ~4.5 GB, best code model for the size
ollama serve                    # keep this terminal open

python ask_repo_local.py ci_bench_L1_chunks.jsonl \
    "Is email normalisation logic duplicated anywhere?" \
    --model qwen2.5-coder:7b
```

### 3. Upgrade to semantic retrieval (recommended)

TF-IDF is fast but misses synonyms and semantic matches. Embed once with
`nomic-embed-text` (free, runs locally) to unlock cosine-similarity retrieval:

```bash
ollama pull nomic-embed-text

# Embed all chunks (~1-2 min for L1)
python embed_chunks.py ci_bench_L1_chunks.jsonl
# -> writes ci_bench_L1_chunks_embedded.jsonl

# Query with semantic retrieval
python ask_repo_local.py ci_bench_L1_chunks_embedded.jsonl \
    "Where is email normalisation logic?" \
    --embed --model qwen2.5-coder:7b

# Add cross-encoder re-ranking for even better precision
pip install sentence-transformers
python ask_repo_local.py ci_bench_L1_chunks_embedded.jsonl \
    "Where is email normalisation logic?" \
    --embed --rerank --model qwen2.5-coder:7b
```

Re-run embedding only when source files change (skips unchanged files):

```bash
python embed_chunks.py ci_bench_L1_chunks.jsonl --incremental
```

### 4. Launch the chat server (optional)

Serves a built-in chat UI + OpenAI / Ollama / Anthropic compatible endpoints:

```bash
python rag_server.py ci_bench_L1_chunks_embedded.jsonl \
    --embed --rerank --model qwen2.5-coder:7b

# Open http://localhost:8080 in your browser for the chat UI
# Or query via API:
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:7b","messages":[{"role":"user","content":"How does EmailValidator work?"}]}'
```

For a persistent vector store (survives server restarts):

```bash
pip install chromadb
python rag_server.py ci_bench_L1_chunks_embedded.jsonl \
    --embed --rerank --chroma --model qwen2.5-coder:7b
```

### How it works

```
parse_repo.py  ->  repo_chunks.jsonl
  (AST parser,       |
   stdlib only)      v
                 embed_chunks.py  ->  repo_chunks_embedded.jsonl
                   (Ollama,              |
                    incremental)         v
                                    ask_repo_local.py   (CLI, Ollama)
                                    ask_repo.py         (CLI, Claude API)
                                    rag_server.py       (HTTP server + chat UI)
```

The JSONL is model-agnostic — generate once, query with any LLM.
TF-IDF retrieval reduces token usage by ~95–99% vs. passing the full codebase;
semantic embeddings + re-ranking further improve retrieval quality on harder queries.

---

## Relation to the full benchmark suite

```
ci-bench-L1 (this repo) — L1 Easy   — ~6k lines  — single library
ci-bench-L2             — L2 Medium — ~12k lines — FastAPI REST service
ci-bench-L3             — L3 Hard   — ~18k lines — pipeflow pipeline framework
```

Run all three in sequence to build a **difficulty curve** for your pipeline. A system that scores well on L1 but degrades on L3 highlights specific weaknesses (e.g. cross-file reasoning, large-context retrieval, or symbol disambiguation).

---

## License

MIT — free to use for benchmarking, research, and commercial evaluation.
