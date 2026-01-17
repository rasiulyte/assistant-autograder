# Troubleshooting Guide

## Common Issues and Solutions

### Setup Issues

#### ❌ Error: "ANTHROPIC_API_KEY environment variable not set"

**Cause:** The API key isn't configured in your environment.

**Solution:**
```powershell
# Windows PowerShell
$env:ANTHROPIC_API_KEY="your-key-here"

# Mac/Linux
export ANTHROPIC_API_KEY="your-key-here"
```

**Get your key:** https://console.anthropic.com/settings/keys

**Verify it's set:**
```powershell
echo $env:ANTHROPIC_API_KEY
```

---

#### ❌ Error: "ModuleNotFoundError: No module named 'anthropic'"

**Cause:** The Anthropic library isn't installed.

**Solution:**
```powershell
pip install anthropic
```

**Verify installation:**
```python
python -c "import anthropic; print(anthropic.__version__)"
```

---

### Runtime Issues

#### ❌ API calls failing with authentication errors

**Symptoms:**
- "Authentication error" messages
- "Invalid API key" errors

**Solutions:**
1. Check API key is correct (no extra spaces or quotes)
2. Verify key hasn't expired in Anthropic dashboard
3. Check you have credits/billing set up

**Debug:**
```python
# Test API connection directly
import anthropic
client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=100,
    messages=[{"role": "user", "content": "Hi"}]
)
print(message.content[0].text)
```

---

#### ❌ JSON extraction failing (success=False in results)

**Symptoms:**
- Many evaluations show `"success": false` in results JSON
- Console shows "✗ Failed" instead of scores

**Cause:** Claude's response didn't include valid JSON scores.

**Debug:**
1. Open `results/experiment_results_*.json`
2. Find a failed evaluation
3. Look at the `"raw_response"` field
4. Check what Claude actually returned

**Common causes:**
- Prompt is ambiguous
- Claude included reasoning but no JSON
- JSON is malformed (missing quotes, brackets)

**Solutions:**
- Check `prompts.py` templates include clear JSON instructions
- Verify rubric text isn't causing confusion
- Try lowering temperature (more deterministic)

**Example fix in prompts.py:**
```python
# Make JSON requirement more explicit
"""
Respond ONLY with the JSON, no other text. Example format:
```json
{
    "correctness": 5,
    "completeness": 4,
    ...
}
```
Do not include any explanation outside the JSON.
"""
```

---

#### ❌ High variance (>0.1) in consistency analysis

**Symptoms:**
- Variance numbers in analysis report are high
- Same test case gets different scores across trials

**Cause:** Claude is interpreting the rubric inconsistently.

**Solutions:**

1. **Lower temperature** (more deterministic):
```python
# In run_autograder.py
TEMPERATURE = 0.0  # Down from 0.3
```

2. **Clarify rubric** in `rubrics.py`:
- Add more specific examples
- Make scale definitions clearer
- Add edge case guidance

3. **Use chain-of-thought** (forces reasoning):
- Chain-of-thought has lowest variance in our experiments
- Explicit reasoning reduces randomness

**Debug which cases are inconsistent:**
```python
from analyze_results import load_results, analyze_consistency
results = load_results()
consistency = analyze_consistency(results)
print(consistency["zero_shot"]["mean_variance_by_dim"])
# Shows variance per dimension
```

---

### Analysis Issues

#### ❌ Error: "No results files found"

**Cause:** You haven't run the experiment yet.

**Solution:**
```powershell
python run_autograder.py  # This creates results file first
python analyze_results.py # Then analyze it
```

---

#### ❌ MAE seems wrong or too high

**Symptoms:**
- MAE > 1.0 across all strategies
- Results don't match expected behavior

**Debug steps:**

1. **Check ground truth labels** in `test_cases.py`:
```python
from test_cases import get_test_cases
cases = get_test_cases()
for case in cases:
    print(f"{case['id']}: {case['ground_truth']}")
# Are your human scores reasonable?
```

2. **Check specific failures**:
```python
from analyze_results import load_results, identify_failure_cases
results = load_results()
failures = identify_failure_cases(results)
for f in failures[:5]:
    print(f"{f['test_case_id']}: Claude={f['autograder_score']}, You={f['ground_truth']}")
# Which cases have biggest disagreements?
```

3. **Manually review a case**:
- Pick a high-MAE test case
- Read the query and response in `test_cases.py`
- Read your ground truth scores and notes
- Look at Claude's scores in `results/experiment_results_*.json`
- Do you agree with your original scores? Or Claude's?

**Common causes:**
- Ground truth labels were too harsh/lenient
- Rubric definitions unclear
- Category is inherently difficult (e.g., task completion)

---

#### ❌ Analysis report looks incomplete

**Symptoms:**
- Missing sections
- Empty tables
- "N/A" values everywhere

**Causes:**

1. **Too many failed evaluations:**
   - Check success rate in results JSON
   - Should be >90% successful
   - If low, see "JSON extraction failing" above

2. **Missing ground truth:**
```python
# Verify all test cases have ground truth
from test_cases import get_test_cases
cases = get_test_cases()
for case in cases:
    assert "ground_truth" in case
    assert all(dim in case["ground_truth"] for dim in 
               ["correctness", "completeness", "conciseness", "naturalness", "safety"])
```

3. **Corrupted results file:**
   - Try re-running experiment
   - Check JSON is valid: `python -m json.tool results/experiment_results_*.json`

---

### Data Quality Issues

#### ⚠️ Bias is very high (>±0.5)

**What this means:** Claude systematically rates higher/lower than you.

**Not necessarily a problem if:**
- You're testing if Claude is too lenient (expected positive bias)
- You're debugging a specific bias pattern

**Is it a problem if:**
- You want Claude to match human judgment exactly
- Bias varies wildly between dimensions

**Solutions:**

1. **Calibrate with few-shot examples**:
```python
# In prompts.py, add examples showing your scoring style
# If you're strict on conciseness, show an example with low conciseness score
```

2. **Adjust rubric definitions**:
```python
# In rubrics.py, make scale more explicit
# If Claude gives 5s too easily, make "5" criteria stricter
```

3. **Accept systematic bias**:
- If bias is consistent (e.g., always +0.3), you can subtract it
- What matters more is correlation, not absolute values

---

#### ⚠️ Some categories have very high MAE

**Example:** task queries have MAE=0.600 (from our experiment)

**Is this expected?**
- YES: Some categories are inherently harder
- Task completion is subjective (is refusing a task "complete"?)
- Opinion questions have no ground truth

**Solutions:**

1. **Review test cases in that category:**
```python
from test_cases import get_test_cases
tasks = [c for c in get_test_cases() if c["category"] == "task"]
for task in tasks:
    print(f"{task['id']}: {task['query']}")
    print(f"Your scores: {task['ground_truth']}")
```

2. **Add more specific rubric guidance** for that category
3. **Add more examples** in few-shot prompt for that category
4. **Accept higher MAE** if category is inherently difficult

---

## Validation Checklist

Run this before trusting your results:

### ✅ Data Integrity

```python
# Run this to validate everything
from test_cases import get_test_cases
from rubrics import get_dimensions

cases = get_test_cases()
dims = get_dimensions()

print(f"✓ {len(cases)} test cases loaded")

for case in cases:
    assert "id" in case
    assert "category" in case
    assert "query" in case
    assert "response" in case
    assert "ground_truth" in case
    assert "notes" in case
    
    for dim in dims:
        score = case["ground_truth"][dim]
        assert 1 <= score <= 5, f"{case['id']}.{dim} = {score} (must be 1-5)"

print("✓ All test cases valid")
```

### ✅ Experiment Completeness

1. Check total API calls: Should be 23 × 3 × 3 = 207
2. Check success rate: Should be >90%
3. Check token count: Should be ~130k-150k
4. Check all strategies ran: zero_shot, few_shot, chain_of_thought

### ✅ Analysis Outputs

1. `results/experiment_results_*.json` exists and is valid JSON
2. `results/analysis_report.txt` has all sections (1-5)
3. No "N/A" in key metrics (variance, MAE, bias)
4. Failures section shows specific test_case_ids

---

## Getting Help

### Self-Diagnosis

1. **Read the error message carefully**
   - Often tells you exactly what's wrong
   - Note the file and line number

2. **Check the docstrings**
   - Every function has detailed documentation
   - Explains what it does, inputs, outputs

3. **Look at examples**
   - `GETTING_STARTED.md` has working examples
   - `test_cases.py` shows proper data structure

4. **Enable debug output**:
```python
# In run_autograder.py, print raw responses
result = run_single_evaluation(...)
if not result["success"]:
    print("Raw response:", result.get("raw_response", "N/A"))
```

### When to Re-run vs Debug

**Re-run the experiment if:**
- You changed test cases
- You modified prompts or rubrics
- You want to test different temperature
- Random LLM variation might be the issue

**Debug the code if:**
- Getting Python errors
- JSON parsing fails consistently
- Results file is corrupted
- Analysis script crashes

### Understanding "Normal" Results

From our experiment, these are typical:

**Good:**
- Variance: 0.01-0.05 (very consistent)
- MAE: 0.3-0.4 (reasonably accurate)
- Bias: ±0.3 (slight systematic difference)
- Success rate: >95%

**Needs attention:**
- Variance: >0.1 (too much variation)
- MAE: >1.0 (significantly inaccurate)
- Bias: >±0.5 (large systematic error)
- Success rate: <80% (many failures)

---

## Advanced Debugging

### Trace a Specific Test Case

```python
# Find everything related to one test case
import json
from pathlib import Path

# Load results
with open("results/experiment_results_20260117_135429.json") as f:
    results = json.load(f)

# Find specific case
test_id = "fact_03"  # The one you're debugging
case = next(c for c in results["evaluations"] if c["test_case_id"] == test_id)

print(f"Query: {case['query']}")
print(f"Response: {case['response']}")
print(f"Your scores: {case['ground_truth']}")
print(f"")

# Check each strategy
for strategy, evals in case["evaluations"].items():
    print(f"{strategy}:")
    for i, e in enumerate(evals, 1):
        if e["success"]:
            print(f"  Trial {i}: {e['scores']}")
        else:
            print(f"  Trial {i}: FAILED")
            print(f"    Raw: {e.get('raw_response', 'N/A')[:100]}...")
```

### Compare Strategies

```python
# Which strategy performs best?
from analyze_results import load_results, analyze_ground_truth_correlation

results = load_results()
correlation = analyze_ground_truth_correlation(results)

for strategy, data in sorted(correlation.items(), key=lambda x: x[1]["overall_mae"]):
    print(f"{strategy:20} MAE={data['overall_mae']:.3f}  Bias={data['overall_bias']:+.3f}")
```

### Find Patterns in Failures

```python
from analyze_results import load_results, identify_failure_cases
from collections import Counter

results = load_results()
failures = identify_failure_cases(results)

# Which dimensions fail most?
dim_counts = Counter(f["dimension"] for f in failures)
print("Failures by dimension:", dim_counts)

# Which categories fail most?
cat_counts = Counter(f["category"] for f in failures)
print("Failures by category:", cat_counts)

# Which strategies fail most?
strat_counts = Counter(f["strategy"] for f in failures)
print("Failures by strategy:", strat_counts)
```

---

For more help, see:
- [GETTING_STARTED.md](GETTING_STARTED.md) - Basic usage
- [RESULTS_REFERENCE.md](RESULTS_REFERENCE.md) - Understanding numbers
- Code comments and docstrings - Detailed explanations
