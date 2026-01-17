"""
RESULTS ANALYSIS: Measure How Well the Autograder Performed

PURPOSE:
    After running the experiment (run_autograder.py), this script analyzes
    the results to answer key questions:
    
    1. CONSISTENCY: Does Claude give the same scores when asked multiple times?
    2. ACCURACY: Does Claude's scores match our human labels?
    3. BIAS: Does Claude systematically over-rate or under-rate?
    4. FAILURES: Which cases did Claude get wrong?

KEY METRICS EXPLAINED:

    VARIANCE (for consistency):
        - Measures how much Claude's scores vary across trials
        - Lower is better (0 = perfectly consistent)
        - Example: If Claude gives [4, 4, 4] across 3 trials, variance = 0
        - Example: If Claude gives [3, 4, 5] across 3 trials, variance = 1
    
    MAE - Mean Absolute Error (for accuracy):
        - Average difference between Claude's scores and human scores
        - Lower is better (0 = perfect agreement)
        - Example: Claude says 5, human says 3 -> error = 2
    
    BIAS (for systematic errors):
        - Positive bias = Claude rates higher than humans (overrates)
        - Negative bias = Claude rates lower than humans (underrates)
        - Example: Bias of +0.5 means Claude averages 0.5 points higher

HOW TO RUN:
    python analyze_results.py
    
    Or specify a specific results file:
    python analyze_results.py results/experiment_results_20260117_120000.json
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
import statistics


def load_results(filepath=None):
    """
    Load experiment results from JSON file.
    
    If no filepath is given, automatically finds the most recent results file.
    """
    results_dir = Path("results")
    
    if filepath:
        with open(filepath) as f:
            return json.load(f)
    
    result_files = list(results_dir.glob("experiment_results_*.json"))
    if not result_files:
        print("ERROR: No results files found.")
        print("Run 'python run_autograder.py' first to generate results.")
        exit(1)
    
    latest = max(result_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading: {latest}")
    
    with open(latest) as f:
        return json.load(f)


def calculate_variance(scores):
    """
    Calculate variance of a list of scores.
    
    Variance measures how spread out the scores are from their mean.
    - Variance of 0 means all scores are identical (perfectly consistent)
    - Higher variance means more variation between trials
    
    Formula: variance = sum((x - mean)^2) / (n - 1)
    
    Example:
        scores = [4, 4, 4] -> variance = 0.0 (all same)
        scores = [3, 4, 5] -> variance = 1.0 (spread out)
        scores = [4, 5, 4] -> variance = 0.33 (slight variation)
    
    Args:
        scores: List of numeric scores from multiple trials
    
    Returns:
        float: The sample variance of the scores
    """
    if len(scores) < 2:
        return 0.0
    return statistics.variance(scores)


def analyze_consistency(results):
    """
    Analyze run-to-run consistency for each prompt strategy.
    
    WHAT THIS MEASURES:
        For each test case, we ran 3 trials with each strategy.
        This function measures how much the scores varied across trials.
        
        Lower variance = more consistent = better
    
    HOW IT WORKS:
        1. For each test case and strategy, collect all scores from 3 trials
        2. Calculate variance for each dimension (correctness, completeness, etc.)
        3. Average the variances across all test cases
        
    EXAMPLE:
        Test case "fact_01" with few_shot strategy:
            Trial 1: correctness=5, completeness=5, ...
            Trial 2: correctness=5, completeness=5, ...
            Trial 3: correctness=5, completeness=5, ...
        Variance for correctness = 0 (all same score)
        
        Test case "edge_03" with zero_shot strategy:
            Trial 1: correctness=5
            Trial 2: correctness=4
            Trial 3: correctness=4
        Variance for correctness = 0.33 (some variation)
    
    Returns:
        dict: For each strategy, the mean variance by dimension and overall
              e.g., {"few_shot": {"overall_mean_variance": 0.026, ...}}
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


def analyze_ground_truth_correlation(results):
    """
    Compare autograder scores to human ground truth labels.
    
    WHAT THIS MEASURES:
        - MAE (Mean Absolute Error): How far off is Claude's score on average?
        - Bias: Does Claude systematically over-rate or under-rate?
    
    HOW MAE IS CALCULATED:
        1. For each test case, average Claude's scores across 3 trials
        2. Compare to human ground truth: error = |claude_score - human_score|
        3. Average all errors across test cases and dimensions
        
        Example:
            Human rated correctness as 3
            Claude's 3 trials: [4, 4, 5] -> average = 4.33
            Error = |4.33 - 3| = 1.33
    
    HOW BIAS IS CALCULATED:
        Same as MAE but keep the sign:
            Bias = claude_score - human_score
        
        Positive bias = Claude rates higher than human (overrates)
        Negative bias = Claude rates lower than human (underrates)
        
        Example:
            Human: 3, Claude average: 4.33
            Bias = 4.33 - 3 = +1.33 (Claude overrated)
    
    WHY BOTH METRICS MATTER:
        - MAE tells you how accurate Claude is overall
        - Bias tells you if there's a systematic pattern
        
        You could have low MAE but high bias if Claude consistently
        over-rates by a small amount (e.g., always +0.3).
    
    Returns:
        dict: For each strategy, MAE and bias by dimension and overall
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
                for dim in dimensions:
                    scores = [e["scores"][dim] for e in successful_evals]
                    avg_score = statistics.mean(scores)
                    gt_score = ground_truth[dim]
                    
                    error = abs(avg_score - gt_score)
                    diff = avg_score - gt_score
                    
                    analysis[strategy][dim]["errors"].append(error)
                    analysis[strategy][dim]["diffs"].append(diff)
    
    summary = {}
    for strategy in strategies:
        summary[strategy] = {
            "mae_by_dim": {},
            "bias_by_dim": {},
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


def analyze_by_category(results):
    """
    Analyze performance broken down by query category.
    
    PURPOSE:
        Different types of queries may be easier or harder to evaluate.
        This function shows which categories Claude struggles with most.
    
    CATEGORIES IN THIS EXPERIMENT:
        - factual: Questions with clear right/wrong answers (e.g., "capital of France")
        - task: Commands to do something (e.g., "set a timer")
        - subjective: Opinion questions (e.g., "best restaurant nearby")
        - math: Calculation questions (e.g., "15% of 80")
        - weather: Time-sensitive queries (e.g., "will it rain tomorrow")
        - safety: Sensitive topics requiring careful handling
        - edge_case: Unusual inputs (e.g., gibberish, jokes)
    
    HOW IT WORKS:
        1. Group test cases by category
        2. For each category, calculate MAE across all dimensions
        3. Sort by MAE to see hardest vs easiest categories
    
    Returns:
        dict: MAE by dimension and overall for each category
    """
    dimensions = ["correctness", "completeness", "conciseness", "naturalness", "safety"]
    
    category_errors = defaultdict(lambda: defaultdict(list))
    
    for case in results["evaluations"]:
        category = case["category"]
        ground_truth = case["ground_truth"]
        
        for strategy, evals in case["evaluations"].items():
            successful = [e for e in evals if e["success"] and e["scores"]]
            if successful:
                scores = successful[0]["scores"]
                for dim in dimensions:
                    error = abs(scores[dim] - ground_truth[dim])
                    category_errors[category][dim].append(error)
                break
    
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


def identify_failure_cases(results):
    """
    Find cases where autograder disagreed with human by 2+ points.
    
    PURPOSE:
        Small disagreements (±1 point) are expected - even humans disagree.
        But disagreements of 2+ points indicate systematic problems.
        
        These "failure cases" help us understand:
        - What types of responses Claude misjudges
        - Which dimensions are most problematic
        - How to improve the autograder
    
    THRESHOLD:
        We use 2+ points as the threshold because:
        - On a 1-5 scale, 2 points is a significant difference
        - 1-point differences could be reasonable disagreement
        - 2+ points suggests Claude fundamentally misunderstood something
    
    EXAMPLE FAILURE:
        Query: "What is the capital of Australia?"
        Response: "The capital is Sydney." (WRONG - it's Canberra)
        
        Human scored completeness: 1 (can't be complete if wrong)
        Claude scored completeness: 5 (thought it answered the question)
        
        Error: |5 - 1| = 4 points -> FAILURE
    
    Returns:
        list: Failure cases sorted by error magnitude (worst first)
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
                    
                    if error >= 2:
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


def generate_report(results):
    """Generate a formatted analysis report."""
    
    consistency = analyze_consistency(results)
    correlation = analyze_ground_truth_correlation(results)
    by_category = analyze_by_category(results)
    failures = identify_failure_cases(results)
    
    report = []
    
    report.append("=" * 70)
    report.append("AI ASSISTANT AUTOGRADER ANALYSIS REPORT")
    report.append("=" * 70)
    report.append("")
    
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
    
    best_strategy = min(consistency.keys(), key=lambda s: consistency[s]['overall_mean_variance'])
    report.append(f"**Most consistent strategy: {best_strategy}**")
    report.append("")
    
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
    
    best_accuracy = min(correlation.keys(), key=lambda s: correlation[s]['overall_mae'])
    report.append(f"**Most accurate strategy: {best_accuracy}**")
    report.append("")
    
    report.append("-" * 70)
    report.append("## 3. PERFORMANCE BY CATEGORY")
    report.append("(Which query types are hardest to evaluate?)")
    report.append("")
    
    sorted_categories = sorted(by_category.items(), key=lambda x: x[1].get('overall_mae', 0), reverse=True)
    for category, data in sorted_categories:
        report.append(f"### {category}")
        report.append(f"  Overall MAE: {data.get('overall_mae', 'N/A')}")
        report.append("")
    
    report.append("-" * 70)
    report.append("## 4. SIGNIFICANT DISAGREEMENTS WITH HUMAN LABELS")
    report.append("(Cases where autograder was off by 2+ points)")
    report.append("")
    
    if failures:
        for i, fail in enumerate(failures[:10]):
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
    
    report.append("-" * 70)
    report.append("## 5. KEY FINDINGS SUMMARY")
    report.append("")
    
    findings = []
    findings.append(f"- {best_strategy} is the most consistent strategy (lowest variance)")
    findings.append(f"- {best_accuracy} is most accurate vs human labels (MAE={correlation[best_accuracy]['overall_mae']})")
    
    for strategy, data in correlation.items():
        bias = data['overall_bias']
        if abs(bias) > 0.1:
            direction = "overrates" if bias > 0 else "underrates"
            findings.append(f"- {strategy} tends to {direction} responses (bias={bias:+.3f})")
    
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
    filepath = sys.argv[1] if len(sys.argv) > 1 else None
    results = load_results(filepath)
    
    report = generate_report(results)
    print(report)
    
    report_path = Path("results") / "analysis_report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
