
# AI Assistant Response Autograder: LLM-as-Judge Evaluation System

A portfolio project demonstrating autograder design for AI assistant responses, built to explore prompt engineering techniques and LLM-as-Judge reliability.

## Background & Motivation

My background in traditional quality engineering shaped how I initially thought about failures. After spending time reading and experimenting with LLMs, I began to notice a different pattern: instead of obvious crashes or errors, failures are often subtle—confident but wrong answers, plausible hallucinations, or responses that are technically correct yet miss the user’s intent.

This project explores a core question in GenAI evaluation: **How reliable are LLM-based autograders, and how do we validate them?**

I hand-labeled 23 test cases with ground truth scores (the annotation work that underpins any evaluation system), then built and validated multiple autograder approaches to measure their correlation with human judgment.

## Project Overview

This project builds and validates an autograder system that evaluates AI assistant responses across multiple quality dimensions. It demonstrates:

1. **Rubric Design** - Structured evaluation criteria including safety
2. **Prompt Engineering** - Multiple prompting strategies (zero-shot, few-shot, chain-of-thought)
3. **Autograder Validation** - Measuring correlation with human judgment
4. **Bias Detection** - Identifying systematic autograder limitations
5. **Failure Analysis** - Pinpointing where autograders disagree with humans

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
| zero_shot | 0.0406 | 0.38 | +0.067 |
| few_shot | 0.0261 | 0.357 | +0.264 |
| **chain_of_thought** | **0.0116** | **0.348** | +0.261 |

**Best strategy: chain_of_thought** (most consistent AND most accurate)

> **📊 Data Source:** These numbers come from `results/experiment_results_20260117_135429.json` 
> and are calculated by `analyze_results.py`. See [GETTING_STARTED.md](GETTING_STARTED.md) to learn what each metric means.

### What the numbers mean

- **Variance 0.0116**: When asked to score the same response 3 times, chain_of_thought gave nearly identical scores each time (lower = more consistent)
- **MAE 0.348**: On average, Claude's scores were about 0.35 points away from human scores (on a 1-5 scale)
- **Bias +0.261**: Claude tends to rate responses slightly higher than humans do (positive = overrates)

### How these metrics are calculated

**Variance (consistency)**: For each test case, we run 3 trials and calculate how much the scores varied. Then we average across all test cases and dimensions. Lower = more consistent. See `analyze_results.py::analyze_consistency()`.

**MAE (accuracy)**: For each dimension, we compare Claude's average score to the human ground truth score (from `test_cases.py`), take the absolute difference, then average across all test cases. Lower = more accurate. See `analyze_results.py::analyze_ground_truth_correlation()`.

**Bias**: Same as MAE but we keep the sign (positive means Claude scored higher than human). See `analyze_results.py::analyze_ground_truth_correlation()`.

💡 **For detailed explanations with examples, see [GETTING_STARTED.md](GETTING_STARTED.md#key-metrics-explained)**

### Performance by Category

| Category | MAE | Test Cases | Notes |
|----------|-----|------------|-------|
| task | 0.6 | 4 | Hardest to evaluate - Claude struggles with task completion |
| subjective | 0.4 | 3 | Opinion questions are challenging |
| weather | 0.4 | 2 | Time-sensitive queries |
| factual | 0.35 | 4 | Clear right/wrong answers |
| math | 0.333 | 3 | Calculation questions |
| safety | 0.3 | 4 | Safety-critical queries |
| edge_case | 0.2 | 3 | Easiest - unusual inputs handled well |

> **📊 Data Source:** Categories defined in `test_cases.py` (see "category" field). MAE calculated by `analyze_results.py::analyze_by_category()`. Lower MAE = easier for Claude to evaluate correctly.

#### ⚠️ Unexpected Finding: Why Edge Cases Appear Easy

**The Surprise:** Edge cases showed the lowest error (MAE 0.2), which is counterintuitive. You'd expect edge cases to be *hardest* to evaluate, not easiest.

**Why This Happened:** The 3 edge case responses were designed as objectively good responses to unusual inputs:
- `edge_01`: Thoughtful answer to a philosophical question
- `edge_02`: A clean, funny joke
- `edge_03`: Appropriate refusal to gibberish

All 3 were scored 5/5 in ground truth, giving Claude an easy job—evaluating obvious wins requires no judgment. Claude simply recognized "good response" for each case.

**The Real Issue:** The category tests *unusual input types with unambiguous quality*, not *genuinely difficult edge cases*. True edge cases should involve:
- Responses that are ambiguous (multiple valid interpretations)
- Conflicting dimensions (e.g., safety vs naturalness trade-offs)
- Subtle failures (confident but wrong answers, incomplete reasoning)
- Cases where humans would reasonably disagree

**How to Address This:** Future iterations should add edge cases with ground truth scores spread across 1-5, such as:
- Safety refusals that sacrifice clarity ("I can't help with that" vs "I can't help because this violates policy")
- Technically correct but philosophically evasive responses
- Responses that misunderstand ambiguous queries
- Dimension trade-offs requiring judgment calls

With genuinely ambiguous edge cases, this category's MAE would likely rise to 0.35-0.5, making the results more realistic for evaluating LLM-as-Judge limitations.

### Key Failures Found

Cases where Claude disagreed with human scores by 2+ points:

1. **fact_03** (completeness): Claude rated 5, human rated 1
   - Query: "What is the capital of Australia?"
   - Response: "The capital of Australia is Sydney." (WRONG - it's Canberra)
   - **Problem**: Claude gave high completeness to a factually wrong answer
   - 📍 *See `test_cases.py` line 99 for ground truth scores*

2. **math_02** (conciseness): Claude rated 5, human rated 2
   - Query: "What's 15% of 80?"
   - Response: Long explanation when "12" would suffice
   - **Problem**: Claude didn't penalize verbosity for simple questions
   - 📍 *See `test_cases.py` line 255 for full response text*

3. **task_04** (completeness): Claude rated 5, human rated 2
   - Query: "Send a text to John saying I'll be late"
   - Response: "I don't have access to your contacts"
   - **Problem**: Claude thought refusing = complete answer (it's not)
   - 📍 *See `test_cases.py` line 175 for ground truth reasoning*

4. **fact_02** (conciseness): Claude rated 4-5, human rated 2
   - Query: "What is the capital of France?"
   - Response: Long paragraph about Paris history
   - **Problem**: Claude didn't penalize over-explanation
   - 📍 *See `test_cases.py` line 85 for ground truth notes*

> **📊 Data Source:** Failures identified by `analyze_results.py::identify_failure_cases()` (threshold: 2+ point disagreement). Full list in `results/analysis_report.txt` Section 4.

## Project Structure

```
assistant-autograder/
├── README.md              # This file - project overview and results
├── GETTING_STARTED.md     # Step-by-step guide for junior developers
├── RESULTS_REFERENCE.md   # Quick lookup: where each number comes from
├── test_cases.py          # 23 Q&A pairs with human scores (ground truth)
├── rubrics.py             # What each score (1-5) means for each dimension
├── prompts.py             # 3 prompting strategies (zero-shot, few-shot, CoT)
├── run_autograder.py      # Runs the experiment (calls Claude API)
├── analyze_results.py     # Analyzes results and generates report
└── results/               # Output data (JSON results, analysis report)
```

**Data Flow:**
```
test_cases.py (your scores)
       ↓
run_autograder.py → Claude API → experiment_results_*.json (Claude's scores)
       ↓
analyze_results.py → Compares scores → analysis_report.txt
       ↓
README.md (copy key findings here)
```

💡 **For detailed flow diagrams, see [GETTING_STARTED.md](GETTING_STARTED.md#the-big-picture-how-everything-connects)**

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

**What these scripts do:**
- `run_autograder.py`: Calls Claude API 207 times (23 cases × 3 strategies × 3 trials), saves raw scores to `results/experiment_results_YYYYMMDD_HHMMSS.json`
- `analyze_results.py`: Calculates statistics from the JSON file, generates `results/analysis_report.txt`

**New to the project?** Start with [GETTING_STARTED.md](GETTING_STARTED.md) for a step-by-step guide!

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
2. **Claude is mostly accurate** (MAE ~0.35 on 1-5 scale = typically within 1 point)
3. **Claude has a positive bias** (tends to rate ~0.26 points higher than humans)
4. **Task completion is hardest** to evaluate - Claude struggles to judge if a response truly helped
5. **Edge cases are easiest** - Claude handles unusual inputs well
6. **Conciseness is a blind spot** - Claude doesn't penalize verbose responses enough

## Related Work & Validation

These findings align with published research on LLM-as-Judge evaluation:

- **Chain-of-thought effectiveness**: Wei et al. (2022) and Kojima et al. (2023) demonstrated that explicit reasoning improves LLM performance. This project replicates that finding: CoT variance (0.0116) is 3.5× lower than zero-shot (0.0406).

- **Positive bias in LLM evaluators**: Zheng et al. (2023) in their LLMEval work found that LLMs systematically overrate responses. This project observes similar bias (+0.26 points on a 1-5 scale), consistent with their findings on larger models.

- **Category difficulty variation**: Multi-dimensional evaluation literature shows that subjective and task-based judgments are inherently harder than factual queries. Our results confirm this: task MAE (0.6) vs factual (0.35), reflecting the interpretation overhead required.

- **Model-specific limitations**: The conciseness blind spot reflects a known LLM training bias toward verbose, helpful responses—documented in Constitutional AI research.

These replications suggest the project's evaluation framework and findings are methodologically sound and representative of how LLMs perform as evaluators.

## Cost

Total experiment: **$0.03** (207 API calls using Claude Haiku)

- Total tokens: 138,001
- Model: claude-3-haiku-20240307
- Temperature: 0.3

> **📊 Data Source:** Cost and token counts from `results/experiment_results_20260117_135429.json` metadata. Actual cost was $0.0345, rounded to $0.03 for readability.

## Reproducing These Results

The numbers in this README come from running the experiment once on January 17, 2026. 
To reproduce:

1. Run `python run_autograder.py` to generate new results
2. Run `python analyze_results.py` to calculate metrics
3. Results may vary slightly due to LLM non-determinism (temperature=0.3)

## Author

Rasa Rasiulytė  
GitHub: [github.com/rasiulyte](https://github.com/rasiulyte)

## Documentation

- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Complete walkthrough for junior developers
- **[RESULTS_REFERENCE.md](RESULTS_REFERENCE.md)** - Quick lookup: where each metric comes from
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - AI coding assistant guidance
