# AI Assistant Response Autograder: LLM-as-Judge Evaluation System

An experiment testing whether Claude can reliably evaluate AI assistant responses.

## What This Project Does

1. I created 23 example AI assistant conversations and manually scored them (the "ground truth")
2. I asked Claude to score the same conversations using 3 different prompting strategies
3. I ran each evaluation 3 times to test consistency
4. I compared Claude's scores to my human scores to measure accuracy

## Key Question

**Can an LLM (Claude) reliably evaluate AI responses the same way a human would?**

## Results Summary

From 207 API calls (23 test cases × 3 strategies × 3 trials):

| Strategy | Consistency (variance) | Accuracy (MAE) | Bias |
|----------|----------------------|----------------|------|
| zero_shot | 0.041 | 0.380 | +0.067 |
| few_shot | 0.026 | 0.357 | +0.264 |
| **chain_of_thought** | **0.012** | **0.348** | +0.261 |

**Best strategy: chain_of_thought** (most consistent AND most accurate)

> **Note:** These numbers come directly from `results/experiment_results_20260117_135429.json` 
> and are calculated by `analyze_results.py`. Run `python analyze_results.py` to regenerate.

### What the numbers mean

- **Variance 0.012**: When asked to score the same response 3 times, chain_of_thought gave nearly identical scores each time (lower = more consistent)
- **MAE 0.348**: On average, Claude's scores were about 0.35 points away from human scores (on a 1-5 scale)
- **Bias +0.261**: Claude tends to rate responses slightly higher than humans do (positive = overrates)

### How these metrics are calculated

**Variance (consistency)**: For each test case, we run 3 trials and calculate how much the scores varied. Then we average across all test cases and dimensions. See `analyze_results.py::analyze_consistency()`.

**MAE (accuracy)**: For each dimension, we compare Claude's average score to the human ground truth score, take the absolute difference, then average across all test cases. See `analyze_results.py::analyze_ground_truth_correlation()`.

**Bias**: Same as MAE but we keep the sign (positive means Claude scored higher than human). See `analyze_results.py::analyze_ground_truth_correlation()`.

### Performance by Category

| Category | MAE | Test Cases | Notes |
|----------|-----|------------|-------|
| task | 0.600 | 4 | Hardest to evaluate - Claude struggles with task completion |
| subjective | 0.400 | 3 | Opinion questions are challenging |
| weather | 0.400 | 2 | Time-sensitive queries |
| factual | 0.350 | 4 | Clear right/wrong answers |
| math | 0.333 | 3 | Calculation questions |
| safety | 0.300 | 4 | Safety-critical queries |
| edge_case | 0.200 | 3 | Easiest - unusual inputs handled well |

> **Note:** These numbers are calculated in `analyze_results.py::analyze_by_category()`.

### Key Failures Found

Cases where Claude disagreed with human scores by 2+ points:

1. **fact_03** (completeness): Claude rated 5, human rated 1
   - Query: "What is the capital of Australia?"
   - Response: "The capital of Australia is Sydney." (WRONG - it's Canberra)
   - **Problem**: Claude gave high completeness to a factually wrong answer

2. **math_02** (conciseness): Claude rated 5, human rated 2
   - Query: "What's 15% of 80?"
   - Response: Long explanation when "12" would suffice
   - **Problem**: Claude didn't penalize verbosity for simple questions

3. **task_04** (completeness): Claude rated 5, human rated 2
   - Query: "Send a text to John saying I'll be late"
   - Response: "I don't have access to your contacts"
   - **Problem**: Claude thought refusing = complete answer (it's not)

4. **fact_02** (conciseness): Claude rated 4-5, human rated 2
   - Query: "What is the capital of France?"
   - Response: Long paragraph about Paris history
   - **Problem**: Claude didn't penalize over-explanation

> **Note:** Full failure list in `analyze_results.py::identify_failure_cases()`.

## Project Structure

```
assistant-autograder/
├── README.md              # This file - project overview and results
├── test_cases.py          # 23 Q&A pairs with human scores (ground truth)
├── rubrics.py             # What each score (1-5) means for each dimension
├── prompts.py             # 3 prompting strategies (zero-shot, few-shot, CoT)
├── run_autograder.py      # Runs the experiment (calls Claude API)
├── analyze_results.py     # Analyzes results and generates report
└── results/               # Output data (JSON results, analysis report)
```

## How to Run

```bash
# Install dependencies
pip install anthropic

# Set API key (Mac/Linux)
export ANTHROPIC_API_KEY="your-key"

# Set API key (Windows PowerShell)
$env:ANTHROPIC_API_KEY="your-key"

# Run experiment (~10-15 min, ~$0.03)
python run_autograder.py

# Analyze results
python analyze_results.py
```

## The 5 Evaluation Dimensions

| Dimension | What it measures | Example |
|-----------|------------------|---------|
| Correctness | Is the information accurate? | "Paris" for capital of France = 5 |
| Completeness | Does it fully answer the question? | Answering only part of a multi-part question = 3 |
| Conciseness | Is it the right length? | One-word answer to complex question = 2 |
| Naturalness | Does it sound like a helpful assistant? | Robotic response = 2 |
| Safety | Is it appropriate and not harmful? | Giving dangerous instructions = 1 |

## The 3 Prompting Strategies

1. **Zero-shot**: Just give Claude the rubric and ask for scores
   - Simplest approach, tests if Claude can evaluate with instructions alone

2. **Few-shot**: Show Claude 3 example evaluations first
   - Tests if examples help Claude calibrate its scoring

3. **Chain-of-thought**: Ask Claude to explain reasoning before scoring
   - Forces Claude to think through each dimension explicitly

## Conclusions

1. **Chain-of-thought prompting works best** for this task (most consistent and accurate)
2. **Claude is mostly accurate** (MAE ~0.35 on 1-5 scale = within 1 point usually)
3. **Claude has a positive bias** (tends to rate 0.2-0.3 points higher than humans)
4. **Task completion is hardest** to evaluate - Claude struggles to judge if a response truly helped
5. **Edge cases are easiest** - Claude handles unusual inputs well
6. **Conciseness is a blind spot** - Claude doesn't penalize verbose responses enough

## Cost

Total experiment: **$0.03** (207 API calls using Claude Haiku)

- Total tokens: 138,001
- Model: claude-3-haiku-20240307
- Temperature: 0.3

> **Note:** Cost calculated from actual token usage in experiment metadata.

## Reproducing These Results

The numbers in this README come from running the experiment once on January 17, 2026. 
To reproduce:

1. Run `python run_autograder.py` to generate new results
2. Run `python analyze_results.py` to calculate metrics
3. Results may vary slightly due to LLM non-determinism (temperature=0.3)

## Author

Rasa Rasiulytė  
GitHub: [github.com/rasiulyte](https://github.com/rasiulyte)
