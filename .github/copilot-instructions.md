# AI Assistant Autograder - Copilot Instructions

## Project Overview

This is an **LLM-as-Judge evaluation system** that tests whether Claude can reliably evaluate AI assistant responses the same way a human would. The experiment measures consistency, accuracy, and bias across 3 prompting strategies (zero-shot, few-shot, chain-of-thought).

**Core experiment loop**: 23 human-labeled test cases → 3 prompt strategies → 3 trials each → 207 total API calls → statistical analysis comparing Claude's scores vs human ground truth.

## Architecture & Data Flow

```
test_cases.py (ground truth labels)
     ↓
run_autograder.py (experiment runner)
     ↓ (calls Anthropic API 207 times)
prompts.py (3 strategies) + rubrics.py (scoring criteria)
     ↓
results/experiment_results_*.json (raw scores)
     ↓
analyze_results.py (statistical analysis)
     ↓
results/analysis_report.txt (findings)
```

**Key files**:
- [test_cases.py](test_cases.py): 23 query-response pairs with human scores (1-5) across 5 dimensions
- [rubrics.py](rubrics.py): Detailed scoring criteria (what each score 1-5 means for each dimension)
- [prompts.py](prompts.py): 3 prompt templates (zero_shot, few_shot, chain_of_thought)
- [run_autograder.py](run_autograder.py): Main experiment runner - loops through all combinations
- [analyze_results.py](analyze_results.py): Calculates variance (consistency), MAE (accuracy), bias

## Critical Developer Workflows

**Run full experiment** (~10-15 min, $0.03):
```powershell
$env:ANTHROPIC_API_KEY="your-key"
python run_autograder.py
python analyze_results.py
```

**Test with single case** (for prompt development):
```python
from run_autograder import run_single_evaluation
import anthropic
client = anthropic.Anthropic()
result = run_single_evaluation(client, "What is 2+2?", "4", "chain_of_thought")
```

**Quick test without API** (validate data structures):
```python
from test_cases import get_test_cases
from prompts import get_prompt
cases = get_test_cases()
prompt = get_prompt("zero_shot", cases[0]["query"], cases[0]["response"])
```

## Project-Specific Conventions

### 1. Five-Dimension Scoring System
Every response evaluated on **correctness, completeness, conciseness, naturalness, safety** (1-5 scale). These are ALWAYS used together - never score on subset. See [rubrics.py](rubrics.py) for full definitions.

### 2. Ground Truth Structure
```python
"ground_truth": {
    "correctness": 5,    # Required
    "completeness": 5,   # Required
    "conciseness": 5,    # Required
    "naturalness": 5,    # Required
    "safety": 5          # Required
}
```
Every test case MUST include all 5 dimensions + `notes` field explaining rationale.

### 3. Results File Naming
Pattern: `results/experiment_results_YYYYMMDD_HHMMSS.json`. [analyze_results.py](analyze_results.py) auto-loads most recent by modification time if no path specified.

### 4. JSON Extraction Pattern
Claude's responses may include reasoning text. Extract scores using regex: `r'\{[^{}]*"correctness"[^{}]*\}'` (see [run_autograder.py#L96-L121](run_autograder.py#L96-L121)). Validate all 5 dimensions present and in range [1,5].

### 5. Variance as Consistency Metric
Use `statistics.variance()` with 3-trial runs to measure consistency (0 = perfectly consistent). Average variances across dimensions and test cases for overall metric. See [analyze_results.py#L101-L165](analyze_results.py#L101-L165).

## Key Integration Points

**Anthropic API**: `claude-3-haiku-20240307` at temperature=0.3. Uses `anthropic.Anthropic()` client (auto-reads `ANTHROPIC_API_KEY` env var). Max tokens=1024 for responses.

**Token tracking**: Every API call records `input_tokens` and `output_tokens` from `message.usage`. Cost estimation: `total_tokens × $0.00000025` (rough average for Haiku pricing).

**Error handling**: If JSON extraction fails (`extract_json_scores()` returns `None`), mark `success: False` but continue experiment. Failed trials excluded from variance calculations but tracked in metadata.

## Common Patterns

### Adding New Test Cases
1. Add to [test_cases.py](test_cases.py) `TEST_CASES` list
2. Include: `id`, `category`, `query`, `response`, `ground_truth` (all 5 dims), `notes`
3. Follow naming: `{category}_{number}` (e.g., `"fact_04"`, `"math_03"`)
4. Update `DATASET STATISTICS` comment with new counts

### Adding New Prompt Strategies
1. Define prompt template in [prompts.py](prompts.py) with `{query}`, `{response}`, `{rubric}` placeholders
2. Add to `STRATEGIES` dict (key = strategy name)
3. Register in `get_strategies()` return list
4. Template MUST instruct response in exact JSON format (see existing patterns)

### Analyzing Specific Dimensions
```python
# Filter results by dimension
for case in results["evaluations"]:
    for strategy, evals in case["evaluations"].items():
        conciseness_scores = [e["scores"]["conciseness"] for e in evals if e["success"]]
```

### Identifying Failure Cases
Threshold: MAE ≥ 2.0 on any dimension = failure. See [analyze_results.py#L297-L343](analyze_results.py#L297-L343) for implementation. Failures often reveal bias patterns (e.g., Claude doesn't penalize verbosity enough).

## README Numbers Are Live
All metrics in [README.md](README.md) (variance, MAE, bias, cost) come from `results/experiment_results_20260117_135429.json`. When regenerating results, update README tables by re-running [analyze_results.py](analyze_results.py) and copying output.

## Testing Philosophy
This project uses **real API calls** as tests (no mocks). Test changes by running small experiments (e.g., 1 test case × 1 strategy × 3 trials = 3 API calls ≈ $0.001). Use `NUM_TRIALS = 1` in [run_autograder.py](run_autograder.py) for faster iteration during development.
