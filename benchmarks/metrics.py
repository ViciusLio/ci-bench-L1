"""
benchmarks.metrics
~~~~~~~~~~~~~~~~~~~
Metric functions for evaluating RAG retrieval and generation quality.

Usage::

    from benchmarks.metrics import precision_at_k, recall_at_k, mrr, compute_all_metrics
"""
from __future__ import annotations

import math
from typing import Any


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of top-k retrieved items that are relevant.

    Parameters
    ----------
    retrieved : ordered list of retrieved item identifiers (file paths / chunk IDs)
    relevant  : set of items considered relevant for this query
    k         : cutoff rank
    """
    if k <= 0:
        raise ValueError("k must be positive")
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    relevant_set = set(relevant)
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of relevant items found in top-k retrieved items.

    Parameters
    ----------
    retrieved : ordered list of retrieved item identifiers
    relevant  : set of items considered relevant for this query
    k         : cutoff rank
    """
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant:
        return 1.0  # vacuously true: nothing to recall
    relevant_set = set(relevant)
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / len(relevant_set)


def average_precision(retrieved: list[str], relevant: list[str]) -> float:
    """Average precision for a single query (used in MAP computation)."""
    if not relevant:
        return 0.0
    relevant_set = set(relevant)
    hits = 0
    precision_sum = 0.0
    for i, item in enumerate(retrieved, start=1):
        if item in relevant_set:
            hits += 1
            precision_sum += hits / i
    if hits == 0:
        return 0.0
    return precision_sum / len(relevant_set)


def mean_average_precision(
    retrieved_lists: list[list[str]],
    relevant_lists: list[list[str]],
) -> float:
    """Mean Average Precision over multiple queries."""
    if len(retrieved_lists) != len(relevant_lists):
        raise ValueError("retrieved_lists and relevant_lists must have the same length")
    if not retrieved_lists:
        return 0.0
    aps = [average_precision(r, rel) for r, rel in zip(retrieved_lists, relevant_lists)]
    return sum(aps) / len(aps)


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    """Reciprocal rank for a single query (1/rank of first relevant item)."""
    relevant_set = set(relevant)
    for i, item in enumerate(retrieved, start=1):
        if item in relevant_set:
            return 1.0 / i
    return 0.0


def mrr(
    retrieved_lists: list[list[str]],
    relevant_lists: list[list[str]],
) -> float:
    """Mean Reciprocal Rank over multiple queries."""
    if len(retrieved_lists) != len(relevant_lists):
        raise ValueError("retrieved_lists and relevant_lists must have the same length")
    if not retrieved_lists:
        return 0.0
    rrs = [reciprocal_rank(r, rel) for r, rel in zip(retrieved_lists, relevant_lists)]
    return sum(rrs) / len(rrs)


def dcg_at_k(retrieved: list[str], relevance_scores: dict[str, float], k: int) -> float:
    """Discounted Cumulative Gain at k.

    Parameters
    ----------
    retrieved       : ordered list of item identifiers
    relevance_scores: mapping from item id to graded relevance (e.g., 2=primary, 1=secondary, 0=irrelevant)
    k               : cutoff rank
    """
    top_k = retrieved[:k]
    score = 0.0
    for i, item in enumerate(top_k, start=1):
        rel = relevance_scores.get(item, 0.0)
        score += (2 ** rel - 1) / math.log2(i + 1)
    return score


def idcg_at_k(relevance_scores: dict[str, float], k: int) -> float:
    """Ideal DCG at k (all relevant items ranked perfectly)."""
    sorted_rels = sorted(relevance_scores.values(), reverse=True)[:k]
    score = 0.0
    for i, rel in enumerate(sorted_rels, start=1):
        score += (2 ** rel - 1) / math.log2(i + 1)
    return score


def ndcg_at_k(retrieved: list[str], relevance_scores: dict[str, float], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k.

    Returns a value in [0, 1] where 1.0 means perfect ranking.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    ideal = idcg_at_k(relevance_scores, k)
    if ideal == 0:
        return 0.0
    return dcg_at_k(retrieved, relevance_scores, k) / ideal


def file_hit_rate(retrieved_files: list[str], expected_file: str) -> bool:
    """Return True if the expected file appears anywhere in the retrieved list."""
    return expected_file in retrieved_files


def hit_at_k(retrieved: list[str], relevant: list[str], k: int) -> bool:
    """Return True if at least one relevant item appears in top-k."""
    relevant_set = set(relevant)
    return any(item in relevant_set for item in retrieved[:k])


def compute_all_metrics(
    results: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
    k_values: list[int] = None,
) -> dict[str, Any]:
    """Compute all standard metrics for a batch of queries.

    Parameters
    ----------
    results : list of dicts with keys ``id``, ``retrieved`` (list of file/chunk ids),
              optionally ``answer`` (str)
    ground_truth : list of dicts from ground_truth.json with ``id``,
                   ``expected_chunks`` (list of dicts with ``file``)
    k_values : cutoffs to evaluate at; defaults to [1, 3, 5, 10]

    Returns
    -------
    dict with per-k metrics and aggregate scores
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    # Build a lookup from query id to ground truth
    gt_lookup: dict[str, list[str]] = {}
    for entry in ground_truth:
        qid = entry["id"]
        relevant = [c["file"] for c in entry.get("expected_chunks", [])]
        gt_lookup[qid] = relevant

    metrics: dict[str, Any] = {f"P@{k}": [] for k in k_values}
    metrics.update({f"R@{k}": [] for k in k_values})
    metrics.update({f"Hit@{k}": [] for k in k_values})
    rr_list: list[float] = []
    ap_list: list[float] = []

    for result in results:
        qid = result.get("id")
        retrieved = result.get("retrieved", [])
        relevant = gt_lookup.get(qid, [])

        if not relevant:
            continue

        for k in k_values:
            metrics[f"P@{k}"].append(precision_at_k(retrieved, relevant, k))
            metrics[f"R@{k}"].append(recall_at_k(retrieved, relevant, k))
            metrics[f"Hit@{k}"].append(1.0 if hit_at_k(retrieved, relevant, k) else 0.0)

        rr_list.append(reciprocal_rank(retrieved, relevant))
        ap_list.append(average_precision(retrieved, relevant))

    # Aggregate
    aggregated: dict[str, Any] = {}
    for key, values in metrics.items():
        aggregated[key] = round(sum(values) / len(values), 4) if values else 0.0

    aggregated["MRR"] = round(sum(rr_list) / len(rr_list), 4) if rr_list else 0.0
    aggregated["MAP"] = round(sum(ap_list) / len(ap_list), 4) if ap_list else 0.0
    aggregated["num_queries"] = len(results)
    aggregated["num_evaluated"] = len(rr_list)

    return aggregated
