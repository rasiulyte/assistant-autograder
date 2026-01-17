"""
Autograder Results Analysis

This script analyzes the experiment results to measure:
1. Run-to-run consistency (variance within same strategy)
2. Prompt strategy comparison (which strategy is most reliable?)
3. Correlation with human ground truth
4. Bias detection (systematic over/under-rating)
5. Category-specific patterns

Usage:
    python analyze_results.py
    
    Or specify a results file:
    python analyze_results.py results/experiment_results_20240115_120000.json
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
import statistics

# Try to import optional dependencies
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("Note: numpy not installed. Using basic statistics.")


def load_results(filepath: str = None) -> dict:
    """Load the most recent results file or specified file."""
    results_dir = Path("results")
    
    if filepath:
        with open(filepath) as f:
            return json.load(f)
    
    # Find most recent results file
    result_files = list(results_dir.glob("experiment_results_*.json"))
    if not result_files:
        print("No results files found. Run 'python run_autograder.py' first.")
        exit(1)
    
    latest = max(result_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading: {latest}")
    
    with open(latest) as f:
        return json.load(f)


def calculate_variance(scores: list[int | float]) -> float:
    """Calculate variance of scores."""
    if len(scores) < 2:
        return 0.0
    return statistics.variance(scores)


def calculate_std(scores: list[int | float]) -> float:
    """Calculate standard deviation of scores."""
    if len(scores) < 2:
        return 0.0
    return statistics.stdev(scores)


def analyze_consistency(results: dict) -> dict:
    """
    Analyze run-to-run consistency for each strategy.
    
    Returns variance/std metrics showing how consistent each strategy is
    when running the same evaluation multiple times.
    """
    dimensions = ["correctness", "completeness", "conciseness", "naturalness", "safety"]
    strategies = results["metadata"]["strategies"]
    
    consistency = {strategy: {dim: [] for dim in dimensions} for strategy in strategies}
    
    for case in results["evaluations"]:
        for strategy in strategies:
            evals = case["evaluations"].get(strategy, [])
            successful_evals = [e for e in evals if e["success"] and e["scores"]]
            
            if len(successful_evals) >= 2:
                for dim in dimensions:
                    scores = [e["scores"][dim] for e in successful_evals]
                    variance = calculate_variance(scores)
                    consistency[strategy][dim].append(variance)
    
    # Aggregate
    summary = {}
    for strategy in strategies:
        summary[strategy] = {
            "mean_variance_by_dim": {},
            "overall_mean_variance": 0.0
        }
        all_variances = []
        for dim in dimensions:
            variances = consistency[strategy][dim]
            if variances:
                mean_var = statistics.mean(variances)
                summary[strategy]["mean_variance_by_dim"][dim] = round(mean_var, 4)
                all_variances.extend(variances)
        
        if all_variances:
            summary[strategy]["overall_mean_variance"] = round(statistics.mean(all_variances), 4)
    
    return summary


def analyze_ground_truth_correlation(results: dict) -> dict:
    """
    Compare autograder scores to human ground truth labels.
    
    Calculates:
    - Mean absolute error (MAE)
    - Bias (systematic over/under rating)
    - Exact match rate
    """
    dimensions = ["correctness", "completeness", "conciseness", "naturalness", "safety"]
    strategies = results["metadata"]["strategies"]
    
    analysis = {strategy: {dim: {"errors": [], "diffs": []} for dim in dimensions} for strategy in strategies}
    
    for case in results["evaluations"]:
        ground_truth = case["ground_truth"]
        
        for strategy in strategies:
            evals = case["evaluations"].get(strategy, [])
            successful_evals = [e for e in evals if e["success"] and e["scores"]]
            
            if successful_evals:
                # Average scores across trials
                for dim in dimensions:
                    scores = [e["scores"][dim] for e in successful_evals]
                    avg_score = statistics.mean(scores)
                    gt_score = ground_truth[dim]
                    
                    error = abs(avg_score - gt_score)
                    diff = avg_score - gt_score  # Positive = overrating
                    
                    analysis[strategy][dim]["errors"].append(error)
                    analysis[strategy][dim]["diffs"].append(diff)
    
    # Summarize
    summary = {}
    for strategy in strategies:
        summary[strategy] = {
            "mae_by_dim": {},
            "bias_by_dim": {},  # Positive = tends to overrate
            "overall_mae": 0.0,
            "overall_bias": 0.0
        }
        
        all_errors = []
        all_diffs = []
        
        for dim in dimensions:
            errors = analysis[strategy][dim]["errors"]
            diffs = analysis[strategy][dim]["diffs"]
            
            if errors:
                summary[strategy]["mae_by_dim"][dim] = round(statistics.mean(errors), 3)
                summary[strategy]["bias_by_dim"][dim] = round(statistics.mean(diffs), 3)
                all_errors.extend(errors)
                all_diffs.extend(diffs)
        
        if all_errors:
            summary[strategy]["overall_mae"] = round(statistics.mean(all_errors), 3)
            summary[strategy]["overall_bias"] = round(statistics.mean(all_diffs), 3)
    
    return summary


def analyze_by_category(results: dict) -> dict:
    """
    Analyze performance broken down by query category.
    
    Identifies if certain query types are harder to evaluate.
    """
    dimensions = ["correctness", "completeness", "conciseness", "naturalness", "safety"]
    
    # Group by category
    category_errors = defaultdict(lambda: defaultdict(list))
    
    for case in results["evaluations"]:
        category = case["category"]
        ground_truth = case["ground_truth"]
        
        # Use first strategy's first successful eval as representative
        for strategy, evals in case["evaluations"].items():
            successful = [e for e in evals if e["success"] and e["scores"]]
            if successful:
                scores = successful[0]["scores"]
                for dim in dimensions:
                    error = abs(scores[dim] - ground_truth[dim])
                    category_errors[category][dim].append(error)
                break  # Only count once per case
    
    # Summarize
    summary = {}
    for category, dim_errors in category_errors.items():
        summary[category] = {}
        all_errors = []
        for dim, errors in dim_errors.items():
            if errors:
                summary[category][dim] = round(statistics.mean(errors), 3)
                all_errors.extend(errors)
        if all_errors:
            summary[category]["overall_mae"] = round(statistics.mean(all_errors), 3)
    
    return summary


def identify_failure_cases(results: dict) -> list:
    """
    Find cases where autograder significantly disagrees with ground truth.
    
    These are candidates for rubric refinement or edge case handling.
    """
    failures = []
    
    for case in results["evaluations"]:
        ground_truth = case["ground_truth"]
        
        for strategy, evals in case["evaluations"].items():
            successful = [e for e in evals if e["success"] and e["scores"]]
            if successful:
                scores = successful[0]["scores"]
                
                for dim, score in scores.items():
                    gt_score = ground_truth[dim]
                    error = abs(score - gt_score)
                    
                    if error >= 2:  # Off by 2+ points
                        failures.append({
                            "test_case_id": case["test_case_id"],
                            "category": case["category"],
                            "dimension": dim,
                            "autograder_score": score,
                            "ground_truth": gt_score,
                            "error": error,
                            "strategy": strategy,
                            "query": case["query"][:50] + "..." if len(case["query"]) > 50 else case["query"],
                            "response": case["response"][:50] + "..." if len(case["response"]) > 50 else case["response"]
                        })
    
    return sorted(failures, key=lambda x: x["error"], reverse=True)


def generate_report(results: dict) -> str:
    """Generate a formatted analysis report."""
    
    consistency = analyze_consistency(results)
    correlation = analyze_ground_truth_correlation(results)
    by_category = analyze_by_category(results)
    failures = identify_failure_cases(results)
    
    report = []
    report.append("=" * 70)
    report.append("SIRI AUTOGRADER ANALYSIS REPORT")
    report.append("=" * 70)
    report.append("")
    
    # Metadata
    meta = results["metadata"]
    report.append("## Experiment Configuration")
    report.append(f"Model: {meta['model']}")
    report.append(f"Temperature: {meta['temperature']}")
    report.append(f"Test cases: {meta['num_test_cases']}")
    report.append(f"Trials per strategy: {meta['num_trials']}")
    report.append(f"Strategies tested: {', '.join(meta['strategies'])}")
    report.append(f"Total tokens: {meta.get('total_tokens', 'N/A'):,}")
    report.append(f"Estimated cost: ${meta.get('estimated_cost_usd', 0):.4f}")
    report.append("")
    
    # Consistency Analysis
    report.append("-" * 70)
    report.append("## 1. RUN-TO-RUN CONSISTENCY")
    report.append("(Lower variance = more consistent)")
    report.append("")
    
    for strategy, data in consistency.items():
        report.append(f"### {strategy}")
        report.append(f"  Overall mean variance: {data['overall_mean_variance']}")
        for dim, var in data['mean_variance_by_dim'].items():
            report.append(f"    - {dim}: {var}")
        report.append("")
    
    # Best consistency
    best_strategy = min(consistency.keys(), key=lambda s: consistency[s]['overall_mean_variance'])
    report.append(f"**Most consistent strategy: {best_strategy}**")
    report.append("")
    
    # Correlation with Ground Truth
    report.append("-" * 70)
    report.append("## 2. CORRELATION WITH HUMAN LABELS")
    report.append("(Lower MAE = closer to human judgment)")
    report.append("")
    
    for strategy, data in correlation.items():
        report.append(f"### {strategy}")
        report.append(f"  Overall MAE: {data['overall_mae']}")
        report.append(f"  Overall Bias: {data['overall_bias']:+.3f} (positive = overrates)")
        report.append("  By dimension:")
        for dim in ["correctness", "completeness", "conciseness", "naturalness", "safety"]:
            mae = data['mae_by_dim'].get(dim, "N/A")
            bias = data['bias_by_dim'].get(dim, 0)
            report.append(f"    - {dim}: MAE={mae}, Bias={bias:+.3f}")
        report.append("")
    
    # Best accuracy
    best_accuracy = min(correlation.keys(), key=lambda s: correlation[s]['overall_mae'])
    report.append(f"**Most accurate strategy: {best_accuracy}**")
    report.append("")
    
    # Category Analysis
    report.append("-" * 70)
    report.append("## 3. PERFORMANCE BY CATEGORY")
    report.append("(Which query types are hardest to evaluate?)")
    report.append("")
    
    sorted_categories = sorted(by_category.items(), key=lambda x: x[1].get('overall_mae', 0), reverse=True)
    for category, data in sorted_categories:
        report.append(f"### {category}")
        report.append(f"  Overall MAE: {data.get('overall_mae', 'N/A')}")
        report.append("")
    
    # Failure Cases
    report.append("-" * 70)
    report.append("## 4. SIGNIFICANT DISAGREEMENTS WITH HUMAN LABELS")
    report.append("(Cases where autograder was off by 2+ points)")
    report.append("")
    
    if failures:
        for i, fail in enumerate(failures[:10]):  # Top 10
            report.append(f"### Failure {i+1}")
            report.append(f"  Test case: {fail['test_case_id']} ({fail['category']})")
            report.append(f"  Dimension: {fail['dimension']}")
            report.append(f"  Autograder: {fail['autograder_score']}, Ground truth: {fail['ground_truth']}")
            report.append(f"  Query: {fail['query']}")
            report.append(f"  Response: {fail['response']}")
            report.append("")
    else:
        report.append("No significant disagreements found.")
        report.append("")
    
    # Key Findings
    report.append("-" * 70)
    report.append("## 5. KEY FINDINGS")
    report.append("")
    
    # Determine key findings
    findings = []
    
    # Consistency finding
    worst_consistency = max(consistency.keys(), key=lambda s: consistency[s]['overall_mean_variance'])
    findings.append(f"- {best_strategy} is the most consistent strategy (lowest run-to-run variance)")
    
    # Accuracy finding
    findings.append(f"- {best_accuracy} is most accurate vs human labels (MAE={correlation[best_accuracy]['overall_mae']})")
    
    # Bias finding
    for strategy, data in correlation.items():
        bias = data['overall_bias']
        if abs(bias) > 0.3:
            direction = "overrates" if bias > 0 else "underrates"
            findings.append(f"- {strategy} tends to {direction} responses (bias={bias:+.3f})")
    
    # Category finding
    if sorted_categories:
        hardest = sorted_categories[0][0]
        easiest = sorted_categories[-1][0]
        findings.append(f"- Hardest category to evaluate: {hardest}")
        findings.append(f"- Easiest category to evaluate: {easiest}")
    
    for finding in findings:
        report.append(finding)
    
    report.append("")
    report.append("=" * 70)
    report.append("END OF REPORT")
    report.append("=" * 70)
    
    return "\n".join(report)


def main():
    # Load results
    filepath = sys.argv[1] if len(sys.argv) > 1 else None
    results = load_results(filepath)
    
    # Generate and print report
    report = generate_report(results)
    print(report)
    
    # Save report
    report_path = Path("results") / "analysis_report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
