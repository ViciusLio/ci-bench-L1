"""
benchmarks.eval_harness
~~~~~~~~~~~~~~~~~~~~~~~~
Evaluation harness for the Code Intelligence RAG system.

Sends each ground-truth query to the RAG API, parses the response,
and computes standard retrieval metrics.

Usage::

    # Against a live RAG system
    python eval_harness.py --rag-url http://localhost:8000

    # Dry run (uses dummy responses)
    python eval_harness.py --dry-run

    # Custom ground truth file
    python eval_harness.py --ground-truth path/to/ground_truth.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent
DEFAULT_GT = HERE / "ground_truth.json"
DEFAULT_SIMILARITY = HERE / "code_similarity.json"


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


def query_rag(url: str, question: str, top_k: int = 10, timeout: int = 60) -> dict:
    """POST a question to the RAG system and return the JSON response.

    Expected response schema::

        {
            "answer": "...",
            "sources": [
                {"file": "src/...", "lines": [10, 25], "content": "..."},
                ...
            ]
        }
    """
    payload = json.dumps({"question": question, "top_k": top_k}).encode("utf-8")
    req = urllib.request.Request(
        f"{url.rstrip('/')}/query",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"RAG API returned HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach RAG API at {url}: {exc.reason}") from exc


def make_dummy_response(query: dict) -> dict:
    """Generate a plausible dummy response for dry-run mode."""
    expected_chunks = query.get("expected_chunks", [])
    sources = []
    # Return only the first expected chunk (simulates imperfect retrieval)
    if expected_chunks:
        sources.append({
            "file": expected_chunks[0]["file"],
            "lines": [1, 30],
            "content": "# dummy retrieved content",
        })
    return {
        "answer": f"[DRY RUN] This is a dummy answer for: {query['question'][:60]}",
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


def extract_retrieved_files(response: dict) -> list[str]:
    """Extract unique file paths from a RAG response's sources list."""
    seen: set[str] = set()
    files: list[str] = []
    for src in response.get("sources", []):
        f = src.get("file", "")
        if f and f not in seen:
            seen.add(f)
            files.append(f)
    return files


def run_evaluation(
    ground_truth: list[dict],
    rag_url: str,
    top_k: int = 10,
    dry_run: bool = False,
    verbose: bool = True,
) -> tuple[list[dict], dict]:
    """Run queries against the RAG and collect raw results.

    Returns
    -------
    raw_results : list of per-query result dicts
    summary     : overall timing statistics
    """
    raw_results: list[dict] = []
    total_latency = 0.0
    errors = 0

    for i, query in enumerate(ground_truth, start=1):
        qid = query["id"]
        question = query["question"]

        if verbose:
            print(f"  [{i:02d}/{len(ground_truth):02d}] {qid}: {question[:60]}...", end=" ", flush=True)

        start = time.monotonic()
        try:
            if dry_run:
                response = make_dummy_response(query)
            else:
                response = query_rag(rag_url, question, top_k=top_k)
        except Exception as exc:
            latency = time.monotonic() - start
            if verbose:
                print(f"ERROR ({latency:.1f}s): {exc}")
            errors += 1
            raw_results.append({
                "id": qid,
                "question": question,
                "retrieved": [],
                "answer": "",
                "latency_s": round(latency, 3),
                "error": str(exc),
            })
            continue

        latency = time.monotonic() - start
        total_latency += latency
        retrieved_files = extract_retrieved_files(response)

        if verbose:
            print(f"OK ({latency:.1f}s, {len(retrieved_files)} sources)")

        raw_results.append({
            "id": qid,
            "question": question,
            "retrieved": retrieved_files,
            "answer": response.get("answer", ""),
            "latency_s": round(latency, 3),
            "sources": response.get("sources", []),
        })

    successful = len(ground_truth) - errors
    summary = {
        "total_queries": len(ground_truth),
        "successful": successful,
        "errors": errors,
        "avg_latency_s": round(total_latency / successful, 3) if successful > 0 else 0.0,
        "total_latency_s": round(total_latency, 3),
    }
    return raw_results, summary


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_metrics_table(metrics: dict, title: str = "Metrics") -> None:
    """Pretty-print a metrics dict as a table."""
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")
    for key, value in sorted(metrics.items()):
        if isinstance(value, float):
            print(f"  {key:<20} {value:.4f}")
        else:
            print(f"  {key:<20} {value}")
    print(f"{'─' * 50}\n")


def save_results(raw_results: list[dict], metrics: dict, summary: dict, output_path: Path) -> None:
    """Save evaluation results to a JSON file."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "metrics": metrics,
        "per_query": raw_results,
    }
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Results saved to: {output_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a Code Intelligence RAG system against ci-bench-L1 ground truth."
    )
    parser.add_argument(
        "--rag-url", default="http://localhost:8000",
        help="Base URL of the RAG system (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--ground-truth", type=Path, default=DEFAULT_GT,
        help="Path to ground_truth.json"
    )
    parser.add_argument(
        "--top-k", type=int, default=10,
        help="Number of chunks to retrieve per query (default: 10)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Use dummy responses instead of querying the RAG system"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output JSON file path (default: eval_results_<timestamp>.json)"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-query output"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load ground truth
    if not args.ground_truth.exists():
        print(f"ERROR: Ground truth file not found: {args.ground_truth}", file=sys.stderr)
        sys.exit(1)

    with args.ground_truth.open(encoding="utf-8") as f:
        gt_data = json.load(f)

    queries = gt_data.get("queries", [])
    print(f"\nci-bench-L1 Evaluation Harness")
    print(f"Repo    : {gt_data.get('repo', 'unknown')}")
    print(f"Queries : {len(queries)}")
    print(f"RAG URL : {args.rag_url}" + (" [DRY RUN]" if args.dry_run else ""))
    print(f"Top-K   : {args.top_k}\n")

    # Run evaluation
    print("Running queries...")
    raw_results, run_summary = run_evaluation(
        queries,
        rag_url=args.rag_url,
        top_k=args.top_k,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )

    # Compute metrics
    sys.path.insert(0, str(HERE))
    from metrics import compute_all_metrics  # noqa: E402

    metrics = compute_all_metrics(raw_results, queries)

    # Report
    print_metrics_table(run_summary, title="Run Summary")
    print_metrics_table(metrics, title="Retrieval Metrics")

    # Save
    output_path = args.output or (
        HERE / f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    save_results(raw_results, metrics, run_summary, output_path)


if __name__ == "__main__":
    main()
