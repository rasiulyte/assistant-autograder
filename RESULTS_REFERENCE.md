# Quick Reference: Understanding Results

## 📊 Where Each Number Comes From

### Main Results Table (README.md)

| What You See | Where It Comes From | How It's Calculated |
|-------------|-------------------|-------------------|
| **Variance 0.012** | `analyze_results.py::analyze_consistency()` | Average variance across 3 trials per test case |
| **MAE 0.348** | `analyze_results.py::analyze_ground_truth_correlation()` | \|Claude score - Human score\| averaged across all cases |
| **Bias +0.261** | `analyze_results.py::analyze_ground_truth_correlation()` | (Claude score - Human score) averaged (keeps sign) |

### Category Performance Table

| What You See | Where It Comes From | What It Means |
|-------------|-------------------|--------------|
| **task MAE 0.600** | `analyze_results.py::analyze_by_category()` | Claude struggles most with task queries |
| **edge_case MAE 0.200** | `analyze_results.py::analyze_by_category()` | Claude handles edge cases well |

### Key Failures Section

| What You See | Where It Comes From | Threshold |
|-------------|-------------------|-----------|
| **fact_03 failure** | `analyze_results.py::identify_failure_cases()` | Disagreement ≥ 2 points |
| **Ground truth scores** | `test_cases.py` ground_truth field | Human-labeled scores (1-5) |
| **Claude scores** | `results/experiment_results_*.json` | API response scores |

## 🔍 Tracing a Result Through the System

### Example: "chain_of_thought variance = 0.012"

**Step 1:** Run experiment
```
python run_autograder.py
→ Calls Claude 207 times
→ Saves to results/experiment_results_20260117_135429.json
```

**Step 2:** Look in JSON file
```json
{
  "evaluations": [
    {
      "test_case_id": "fact_01",
      "evaluations": {
        "chain_of_thought": [
          {"scores": {"correctness": 5, ...}},  // Trial 1
          {"scores": {"correctness": 5, ...}},  // Trial 2
          {"scores": {"correctness": 5, ...}}   // Trial 3
        ]
      }
    }
  ]
}
```

**Step 3:** Calculate variance
```python
# In analyze_results.py::analyze_consistency()
scores = [5, 5, 5]  # correctness scores from 3 trials
variance = statistics.variance(scores)  # = 0.0
# Repeat for all dimensions and test cases, then average
```

**Step 4:** See in report
```
results/analysis_report.txt:
  ### chain_of_thought
    Overall mean variance: 0.012
      - correctness: 0
      ...
```

**Step 5:** Appears in README
```
README.md table:
| chain_of_thought | 0.012 | ... |
```

## 📁 File Relationships

```
Ground Truth (Human Scores)
├── test_cases.py
│   └── "ground_truth": {"correctness": 5, ...}
│
Experiment (Claude Scores)  
├── run_autograder.py
│   └── Calls Claude API
│       └── results/experiment_results_*.json
│           └── "scores": {"correctness": 5, ...}
│
Analysis (Compare Them)
├── analyze_results.py
│   ├── analyze_consistency() → variance
│   ├── analyze_ground_truth_correlation() → MAE & bias
│   ├── analyze_by_category() → category performance
│   └── identify_failure_cases() → significant disagreements
│       └── results/analysis_report.txt
│           └── All metrics formatted
│
Documentation
└── README.md ← Copy/paste from analysis_report.txt
```

## 🎯 Common Questions

### Q: Where does "MAE 0.348" come from?

**A:** 
1. For each test case, Claude scores it 3 times (3 trials)
2. Average Claude's 3 scores: e.g., [4, 4, 5] → 4.33
3. Compare to human score from `test_cases.py`: e.g., 3
4. Calculate error: |4.33 - 3| = 1.33
5. Repeat for all test cases and dimensions
6. Average all errors: 0.348

**Code:** `analyze_results.py` lines 169-254

### Q: What does "fact_03 completeness: Claude 5, Human 1" mean?

**A:**
- **Human score (1):** From `test_cases.py` line 99 → Response is wrong, can't be complete
- **Claude score (5):** From experiment results JSON → Claude thought it fully answered
- **Error:** |5 - 1| = 4 points → Listed as failure (≥2 point threshold)

**See:** 
- Human reasoning: `test_cases.py` line 105 "notes" field
- Failure detection: `analyze_results.py::identify_failure_cases()` line 297+

### Q: How do I know if my experiment worked correctly?

**Check these:**

1. **Results file exists:** `results/experiment_results_YYYYMMDD_HHMMSS.json`
2. **Total API calls:** Should be 207 (23 cases × 3 strategies × 3 trials)
3. **Success rate:** Most evaluations should have `"success": true`
4. **Token count:** Should be ~138,000 tokens
5. **Analysis runs:** `python analyze_results.py` should complete without errors

### Q: What's the difference between variance and MAE?

**Variance (consistency):**
- Measures: Do Claude's 3 trials give similar scores?
- Example: [5, 5, 5] → variance = 0 (perfectly consistent)
- Example: [3, 4, 5] → variance = 1.0 (inconsistent)

**MAE (accuracy):**
- Measures: How close is Claude to human judgment?
- Example: Claude avg=4.5, Human=5 → MAE = 0.5 (very accurate)
- Example: Claude avg=5, Human=1 → MAE = 4.0 (very inaccurate)

**Both matter!** You want low variance (consistent) AND low MAE (accurate).

## 🛠️ Debugging Results

### If variances are high (>0.1):

**Possible causes:**
- Temperature too high (default is 0.3, try 0.0 for more determinism)
- Prompt ambiguity (Claude interprets rubric differently each time)
- Edge cases where rubric is unclear

**Check:** `results/experiment_results_*.json` → Look at the 3 trial scores for high-variance cases

### If MAE is high (>1.0):

**Possible causes:**
- Ground truth labels might need review
- Claude doesn't understand the rubric
- Category is inherently hard to evaluate

**Check:** `results/analysis_report.txt` Section 4 → See which specific cases failed

### If bias is high (>±0.5):

**Possible causes:**
- Claude is too lenient (+bias) or too harsh (-bias)
- Prompt strategy needs tuning
- Rubric definitions misaligned with Claude's interpretation

**Check:** `analyze_results.py::analyze_ground_truth_correlation()` → See bias by dimension

## 📖 Further Reading

- **Full walkthrough:** [GETTING_STARTED.md](GETTING_STARTED.md)
- **AI agent guidance:** [.github/copilot-instructions.md](.github/copilot-instructions.md)
- **Project overview:** [README.md](README.md)
- **Code documentation:** Read docstrings in each `.py` file
