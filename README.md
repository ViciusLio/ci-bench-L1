# ci-bench-L1 — pyvalidate

**Difficulty**: Level 1 · Easy  
**Lines of Python**: ~5,500  
**Domain**: Standalone data validation library  
**Purpose**: Benchmark scenario for Code Intelligence RAG evaluation

---

## About this repo

`pyvalidate` is a lightweight Python validation library modelled after Cerberus / Voluptuous.
It is intentionally designed as a **RAG benchmark target**:

- Multiple validator classes with shared patterns (regex compilation, error handling)
- Legacy helper functions that duplicate newer normaliser logic (test for duplicate detection)
- A declarative `Schema` / `Field` API (test for cross-module understanding)
- A thread-safe `ValidationCache` (test for caching pattern retrieval)

---

## Structure

```
src/pyvalidate/
├── base.py                  # BaseValidator, ValidationResult, ValidationError
├── validators/
│   ├── string_validators.py # EmailValidator, URLValidator, RegexValidator, …
│   ├── numeric_validators.py# IntValidator, FloatValidator, RangeValidator, …
│   ├── date_validators.py   # DateValidator, AgeValidator, DateRangeValidator, …
│   ├── collection_validators.py
│   └── composite_validators.py  # AllValidator, AnyValidator, ChainValidator, …
├── schema/
│   ├── field.py             # Field descriptor
│   ├── schema.py            # Schema, DynamicSchema
│   └── errors.py            # SchemaError, FieldError, ErrorCollection
├── transformers/
│   ├── converters.py        # to_int, to_float, to_bool, to_date, …
│   └── normalizers.py       # normalize_email, slugify, + legacy helpers
└── utils/
    ├── cache.py             # ValidationCache (LRU, thread-safe)
    └── helpers.py           # is_empty, flatten_errors, deep_merge, …
```

---

## Benchmark

```
benchmarks/
├── ground_truth.json    # 20 Q&A queries with expected file/symbol references
├── code_similarity.json # 10 semantically similar code pairs
├── metrics.py           # P@K, R@K, MRR, MAP, NDCG@K
└── eval_harness.py      # CLI evaluation script
```

### Running the benchmark

```bash
# Dry run (no RAG system needed)
python benchmarks/eval_harness.py --dry-run

# Against a live RAG system
python benchmarks/eval_harness.py --rag-url http://localhost:8000 --top-k 10

# Custom ground truth
python benchmarks/eval_harness.py --ground-truth benchmarks/ground_truth.json
```

Expected RAG API:
```
POST /query
{"question": "...", "top_k": 10}

Response:
{"answer": "...", "sources": [{"file": "src/...", "lines": [10, 25], "content": "..."}]}
```

### Metrics

| Metric | Description |
|--------|-------------|
| P@K    | Precision at K — fraction of top-K results that are relevant |
| R@K    | Recall at K — fraction of relevant items found in top-K |
| MRR    | Mean Reciprocal Rank — how high the first relevant result ranks |
| MAP    | Mean Average Precision — area under precision-recall curve |
| Hit@K  | At least one relevant file in top-K |

---

## Quick start

```python
from pyvalidate import EmailValidator, Schema, Field, IntValidator, RangeValidator

# Single validator
v = EmailValidator()
result = v.validate("user@example.com")
print(result.is_valid)   # True
print(result.value)      # "user@example.com"

# Schema
class UserSchema(Schema):
    email = Field(EmailValidator())
    age   = Field(IntValidator(coerce=True), RangeValidator(min_value=0, max_value=150))

schema = UserSchema()
clean = schema.validate_strict({"email": "a@b.com", "age": "25"})
# clean = {"email": "a@b.com", "age": 25}
```

---

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
