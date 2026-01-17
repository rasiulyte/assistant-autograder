# Getting Started Guide for Junior Developers

## Welcome! 👋

This guide will help you understand the AI Assistant Autograder project step-by-step. If you're new to LLM evaluation or autograder systems, start here.

## What Does This Project Do?

Think of it like this: Imagine you're a teacher grading student essays. You want to check if another teacher (Claude AI) grades the same essays the same way you do.

**That's what this project does:**
1. **You** (the human) grade 23 AI assistant responses → this is the "ground truth"
2. **Claude** grades the same 23 responses using 3 different strategies
3. We compare Claude's scores to your scores to see how accurate Claude is

## The Big Picture: How Everything Connects

```
┌─────────────────┐
│  test_cases.py  │ ← 23 Q&A pairs with YOUR scores (ground truth)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│run_autograder.py│ ← Runs the experiment (asks Claude to score)
└────────┬────────┘
         │ (uses prompts from prompts.py + rubrics from rubrics.py)
         │
         ↓
┌─────────────────────────────────┐
│ results/experiment_results_*.json│ ← Raw data: All of Claude's scores
└────────┬────────────────────────┘
         │
         ↓
┌──────────────────┐
│analyze_results.py│ ← Calculates statistics & generates report
└────────┬─────────┘
         │
         ↓
┌──────────────────────────────┐
│ results/analysis_report.txt  │ ← Human-readable findings
│ README.md (results tables)   │ ← Summary for GitHub
└──────────────────────────────┘
```

## Step-by-Step: Run Your First Experiment

### Step 1: Install Dependencies
```powershell
pip install anthropic
```

### Step 2: Set Your API Key
```powershell
# Get your key from: https://console.anthropic.com/settings/keys
$env:ANTHROPIC_API_KEY="your-api-key-here"
```

### Step 3: Run the Experiment
```powershell
python run_autograder.py
```

**What happens:**
- Loads 23 test cases from `test_cases.py`
- For each test case:
  - Asks Claude to score it using 3 strategies (zero_shot, few_shot, chain_of_thought)
  - Repeats 3 times per strategy (to measure consistency)
- Total: 23 × 3 × 3 = 207 API calls (~10-15 min, ~$0.03)
- Saves results to `results/experiment_results_YYYYMMDD_HHMMSS.json`

### Step 4: Analyze the Results
```powershell
python analyze_results.py
```

**What happens:**
- Loads the most recent results file
- Calculates:
  - **Variance** (consistency): Do Claude's scores vary across trials?
  - **MAE** (accuracy): How far off is Claude from human scores?
  - **Bias**: Does Claude over-rate or under-rate?
- Saves report to `results/analysis_report.txt`

### Step 5: Read the Results

Open `results/analysis_report.txt` to see:
- Which strategy is most consistent
- Which strategy is most accurate
- Which categories are hardest to evaluate
- Specific cases where Claude disagreed with humans

## Understanding the Data Files

### 1. test_cases.py - The Ground Truth

**Structure of each test case:**
```python
{
    "id": "fact_01",              # Unique identifier
    "category": "factual",         # Type of query
    "query": "What is the capital of France?",
    "response": "The capital of France is Paris.",
    "ground_truth": {             # YOUR scores (the "answer key")
        "correctness": 5,          # 1-5 scale
        "completeness": 5,
        "conciseness": 5,
        "naturalness": 5,
        "safety": 5
    },
    "notes": "Perfect response"   # Why you gave these scores
}
```

**To add a new test case:**
1. Add to the `TEST_CASES` list in `test_cases.py`
2. Score all 5 dimensions (refer to `rubrics.py` for what each score means)
3. Add explanatory notes

### 2. experiment_results_*.json - Claude's Scores

**Structure:**
```json
{
  "metadata": {
    "model": "claude-3-haiku-20240307",
    "num_trials": 3,
    "total_tokens": 138001,
    "estimated_cost_usd": 0.0345
  },
  "evaluations": [
    {
      "test_case_id": "fact_01",
      "query": "What is the capital of France?",
      "response": "The capital of France is Paris.",
      "ground_truth": {            // YOUR scores from test_cases.py
        "correctness": 5,
        ...
      },
      "evaluations": {
        "zero_shot": [
          {
            "success": true,
            "scores": {              // CLAUDE's scores (trial 1)
              "correctness": 5,
              "completeness": 5,
              ...
            },
            "input_tokens": 523,
            "output_tokens": 42
          },
          // ... trial 2 and 3
        ],
        "few_shot": [...],
        "chain_of_thought": [...]
      }
    },
    // ... other test cases
  ]
}
```

### 3. analysis_report.txt - The Findings

**Example section:**
```
## 1. RUN-TO-RUN CONSISTENCY
(Lower variance = more consistent)

### chain_of_thought
  Overall mean variance: 0.012    ← This number appears in README table
    - correctness: 0              ← Perfect consistency
    - completeness: 0.0145
    ...
```

**How to read variance:**
- `0.000` = Perfectly consistent (all 3 trials gave same score)
- `0.012` = Very consistent (scores varied by tiny amount)
- `0.500` = Inconsistent (scores varied significantly)

**How to read MAE (Mean Absolute Error):**
- `0.348` = On average, Claude's score is 0.35 points away from yours
- On a 1-5 scale, this means Claude is usually close but not exact

**How to read Bias:**
- `+0.261` = Claude scores 0.26 points higher than you on average (overrates)
- `-0.150` = Claude scores 0.15 points lower than you (underrates)

## Common Tasks for Junior Developers

### Task: Test a Single Case Without Running Full Experiment

```python
# In Python console or test file:
from run_autograder import run_single_evaluation
import anthropic

client = anthropic.Anthropic()
result = run_single_evaluation(
    client, 
    "What is 2+2?",           # query
    "The answer is 4.",       # response
    "chain_of_thought"        # strategy
)

print(result["scores"])
# Output: {'correctness': 5, 'completeness': 5, ...}
```

### Task: See What a Prompt Looks Like

```python
from prompts import get_prompt

prompt = get_prompt("few_shot", "What is 2+2?", "The answer is 4.")
print(prompt)
# Shows the full prompt that would be sent to Claude
```

### Task: Validate Test Case Structure Without API Call

```python
from test_cases import get_test_cases
from rubrics import get_dimensions

cases = get_test_cases()
required_dims = get_dimensions()

# Check that all test cases have all required dimensions
for case in cases:
    for dim in required_dims:
        assert dim in case["ground_truth"], f"Missing {dim} in {case['id']}"
        assert 1 <= case["ground_truth"][dim] <= 5, f"Invalid score in {case['id']}"

print("All test cases validated!")
```

### Task: Find Which Test Cases Failed

```python
from analyze_results import load_results, identify_failure_cases

results = load_results()  # Loads most recent results
failures = identify_failure_cases(results)

print(f"Found {len(failures)} failures")
for fail in failures[:5]:  # Show first 5
    print(f"{fail['test_case_id']}: {fail['dimension']}")
    print(f"  Claude: {fail['autograder_score']}, Human: {fail['ground_truth']}")
```

## Understanding the 3 Prompting Strategies

### Zero-Shot (Simplest)
- Give Claude the rubric and ask it to score
- No examples, no special instructions
- **Pros:** Fast, cheap, simple
- **Cons:** Claude has to figure out scoring on its own

### Few-Shot (Learning from Examples)
- Show Claude 3 example evaluations first
- Examples include: perfect response, verbose response, unsafe response
- **Pros:** Examples help Claude understand expectations
- **Cons:** Longer prompt, more expensive

### Chain-of-Thought (Reasoning First)
- Ask Claude to explain its reasoning for each dimension before scoring
- Forces Claude to think through each aspect carefully
- **Pros:** Most accurate and consistent (from our experiment)
- **Cons:** Longest responses, most expensive

## Troubleshooting

### Error: "ANTHROPIC_API_KEY environment variable not set"
**Solution:**
```powershell
$env:ANTHROPIC_API_KEY="your-key-here"
```

### Error: "No results files found"
**Solution:** Run `python run_autograder.py` first to generate results

### Error: JSON extraction failed
**Cause:** Claude's response didn't include valid JSON scores
**Solution:** Check `raw_response` in results JSON to see what Claude actually returned

### Results seem wrong
**Check these:**
1. Are your ground truth scores correct in `test_cases.py`?
2. Did you run enough trials? (default is 3)
3. Is temperature set correctly? (0.3 by default in `run_autograder.py`)

## Key Metrics Explained

### Variance (Consistency)
**Formula:** `variance = Σ(score - mean)² / (n-1)`

**Example:**
- Trial 1: score = 4
- Trial 2: score = 4  
- Trial 3: score = 5
- Mean = 4.33
- Variance = ((4-4.33)² + (4-4.33)² + (5-4.33)²) / 2 = 0.33

**Lower is better!** Variance of 0 means perfect consistency.

### MAE (Mean Absolute Error)
**Formula:** `MAE = Σ|predicted - actual| / n`

**Example:**
- Test case 1: Claude=4, Human=5 → error = |4-5| = 1
- Test case 2: Claude=5, Human=3 → error = |5-3| = 2
- Test case 3: Claude=4, Human=4 → error = |4-4| = 0
- MAE = (1 + 2 + 0) / 3 = 1.0

**Lower is better!** MAE of 0 means perfect accuracy.

### Bias
**Formula:** `Bias = Σ(predicted - actual) / n`

**Same example as MAE but keep the sign:**
- Test case 1: Claude=4, Human=5 → diff = 4-5 = -1
- Test case 2: Claude=5, Human=3 → diff = 5-3 = +2
- Test case 3: Claude=4, Human=4 → diff = 4-4 = 0
- Bias = (-1 + 2 + 0) / 3 = +0.33

**Positive = overrates, Negative = underrates, Zero is ideal!**

## Next Steps

1. **Explore the code:** Read through the files with the comments as your guide
2. **Try modifications:** 
   - Add a new test case
   - Change temperature and see how results differ
   - Add a new prompting strategy
3. **Analyze patterns:** Which dimensions are hardest? Which categories?
4. **Improve the system:** Can you make Claude more accurate?

## Need Help?

- Read the docstrings in each `.py` file - they're extensive!
- Check `README.md` for high-level overview
- Look at `.github/copilot-instructions.md` for AI coding assistant guidance
- Review existing test cases in `test_cases.py` to understand the scoring

Good luck! 🚀
