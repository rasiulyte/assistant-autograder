"""
AUTOGRADER EXPERIMENT RUNNER: Test How Well Claude Can Evaluate AI Responses

PURPOSE:
    This script runs the main experiment. It sends test cases to Claude
    and asks Claude to score them. Then we can compare Claude's scores
    to our human scores (ground truth) to see how accurate Claude is.

WHAT THIS SCRIPT DOES:
    1. Loads all 23 test cases from test_cases.py
    2. For each test case, asks Claude to score it using 3 different prompt strategies
    3. Runs each evaluation 3 times (to measure consistency)
    4. Saves all results to a JSON file for analysis

THE EXPERIMENT:
    - 23 test cases
    - 3 prompt strategies (zero_shot, few_shot, chain_of_thought)
    - 3 trials per strategy (to check if Claude gives same answer each time)
    - Total: 23 × 3 × 3 = 207 API calls

COST:
    Using Claude Haiku, this costs about $0.03-0.05 total.

HOW TO RUN:
    1. Set your API key: export ANTHROPIC_API_KEY="your-key"
    2. Run: python run_autograder.py
    3. Wait 10-15 minutes
    4. Results saved to results/ folder
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

# Try to import the Anthropic library
# If it's not installed, show a helpful error message
try:
    import anthropic
except ImportError:
    print("ERROR: The 'anthropic' library is not installed.")
    print("To install it, run: pip install anthropic")
    exit(1)

from test_cases import get_test_cases
from prompts import get_prompt, get_strategies


# =============================================================================
# CONFIGURATION
# Change these settings to customize the experiment
# =============================================================================

# Which Claude model to use
# claude-3-haiku-20240307 is fast and cheap, good for experiments
MODEL = "claude-3-haiku-20240307"

# Temperature controls randomness (0 = deterministic, 1 = creative)
# We use 0.3 for some variance while still being mostly consistent
TEMPERATURE = 0.3

# How many times to run each evaluation
# Running multiple times lets us measure consistency
NUM_TRIALS = 3

# Where to save results
OUTPUT_DIR = Path("results")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_json_scores(response_text: str) -> dict | None:
    """
    Extract the JSON scores from Claude's response.
    
    WHY THIS IS NEEDED:
        Claude sometimes includes reasoning text before/after the JSON.
        Example response:
            "The response is excellent because... ```json\n{...}```"
        
        We need to extract just the JSON part: {...}
    
    VALIDATION:
        Checks that all 5 dimensions are present:
          - correctness, completeness, conciseness, naturalness, safety
        Checks that each score is a number between 1-5
        
    RETURNS:
        dict: The scores like {"correctness": 5, "completeness": 4, ...}
        None: If we couldn't find or parse valid scores
              (These cases are marked success=False in results)
    
    USED BY:
        - run_single_evaluation() in this file
        - Results saved to experiment_results_*.json
        - Failed extractions excluded from variance calculations
    
    Example:
        response = "The response is good. ```json\n{\"correctness\": 5}```"
        scores = extract_json_scores(response)
        # Returns {"correctness": 5, ...}
    """
    # Use regex to find a JSON object containing "correctness"
    # This handles cases where Claude includes extra text
    json_match = re.search(r'\{[^{}]*"correctness"[^{}]*\}', response_text, re.DOTALL)
    
    if json_match:
        try:
            scores = json.loads(json_match.group())
            
            # Validate that all required dimensions are present and valid
            required_dimensions = ["correctness", "completeness", "conciseness", "naturalness", "safety"]
            for key in required_dimensions:
                if key not in scores:
                    return None  # Missing dimension
                if not isinstance(scores[key], (int, float)):
                    return None  # Score isn't a number
                if scores[key] < 1 or scores[key] > 5:
                    return None  # Score out of range
            
            return scores
            
        except json.JSONDecodeError:
            return None  # Couldn't parse as JSON
    
    return None  # No JSON found


def run_single_evaluation(client, query: str, response: str, strategy: str) -> dict:
    """
    Run a single evaluation: send one test case to Claude and get scores.
    
    Args:
        client: The Anthropic API client
        query: The user's question (from test case)
        response: The AI's response (from test case)
        strategy: Which prompt strategy to use
    
    Returns:
        dict: Results including success status, scores, timing, and token usage
    """
    # Generate the prompt for this strategy
    prompt = get_prompt(strategy, query, response)
    
    start_time = time.time()
    
    try:
        # Call the Claude API
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,  # Max response length
            temperature=TEMPERATURE,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the response text
        response_text = message.content[0].text
        elapsed_time = time.time() - start_time
        
        # Try to extract scores from the response
        scores = extract_json_scores(response_text)
        
        return {
            "success": scores is not None,    # Did we get valid scores?
            "scores": scores,                  # The actual scores (or None)
            "raw_response": response_text,     # Claude's full response (for debugging)
            "elapsed_time": elapsed_time,      # How long the API call took
            "input_tokens": message.usage.input_tokens,   # Tokens in prompt
            "output_tokens": message.usage.output_tokens  # Tokens in response
        }
        
    except Exception as e:
        # If something went wrong, return error info
        return {
            "success": False,
            "scores": None,
            "error": str(e),
            "elapsed_time": time.time() - start_time
        }


# =============================================================================
# MAIN EXPERIMENT FUNCTION
# =============================================================================

def run_experiment():
    """
    Run the full autograder experiment.
    
    This is the main function that:
    1. Loads test cases
    2. Runs evaluations for each test case, strategy, and trial
    3. Saves results to JSON
    """
    # Initialize the API client
    # It automatically uses the ANTHROPIC_API_KEY environment variable
    client = anthropic.Anthropic()
    
    # Load test cases and strategies
    test_cases = get_test_cases()
    strategies = get_strategies()
    
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Initialize results structure
    results = {
        "metadata": {
            "model": MODEL,
            "temperature": TEMPERATURE,
            "num_trials": NUM_TRIALS,
            "num_test_cases": len(test_cases),
            "strategies": strategies,
            "timestamp": datetime.now().isoformat()
        },
        "evaluations": []  # Will hold all evaluation results
    }
    
    # Calculate total number of API calls
    total_calls = len(test_cases) * len(strategies) * NUM_TRIALS
    print(f"Starting experiment: {total_calls} total API calls")
    print(f"  - {len(test_cases)} test cases (from test_cases.py)")
    print(f"  - {len(strategies)} strategies (from prompts.py)")
    print(f"  - {NUM_TRIALS} trials each (for consistency measurement)")
    print(f"")
    print(f"Results will be saved to: results/experiment_results_YYYYMMDD_HHMMSS.json")
    print(f"Run 'python analyze_results.py' after this completes to see metrics.")
    print()
    
    call_count = 0
    
    # Loop through each test case
    for tc in test_cases:
        print(f"Evaluating: {tc['id']} ({tc['category']})")
        
        # Store results for this test case
        case_results = {
            "test_case_id": tc["id"],
            "category": tc["category"],
            "query": tc["query"],
            "response": tc["response"],
            "ground_truth": tc["ground_truth"],  # Human labels for comparison
            "evaluations": {}  # Will hold results for each strategy
        }
        
        # Loop through each prompt strategy
        for strategy in strategies:
            strategy_results = []
            
            # Run multiple trials for consistency measurement
            for trial in range(NUM_TRIALS):
                call_count += 1
                print(f"  [{call_count}/{total_calls}] {strategy} trial {trial + 1}...", end=" ")
                
                # Run the evaluation
                result = run_single_evaluation(
                    client,
                    tc["query"],
                    tc["response"],
                    strategy
                )
                
                # Print result (✓ for success, ✗ for failure)
                # These scores will be saved to results/experiment_results_*.json
                # and compared against ground_truth from test_cases.py
                if result["success"]:
                    print(f"✓ {result['scores']}")
                else:
                    print(f"✗ Failed")
                
                strategy_results.append(result)
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
            
            case_results["evaluations"][strategy] = strategy_results
        
        results["evaluations"].append(case_results)
        print()  # Blank line between test cases
    
    # Calculate summary statistics
    total_tokens = sum(
        eval_result.get("input_tokens", 0) + eval_result.get("output_tokens", 0)
        for case in results["evaluations"]
        for strategy_results in case["evaluations"].values()
        for eval_result in strategy_results
    )
    
    results["metadata"]["total_tokens"] = total_tokens
    
    # -----------------------------------------------------------------
    # COST ESTIMATION
    # -----------------------------------------------------------------
    # WHERE THIS APPEARS IN RESULTS:
    #   - Saved to experiment_results_*.json metadata section
    #   - Displayed in analysis_report.txt "Experiment Configuration"
    #   - Referenced in README.md "Cost" section
    #
    # Claude Haiku pricing (as of 2024):
    #   Input tokens:  $0.25 per million tokens  = $0.00000025 per token
    #   Output tokens: $1.25 per million tokens  = $0.00000125 per token
    #
    # For simplicity, we use an average of ~$0.00000025 per token
    # (our prompts are input-heavy, so this is a reasonable approximation)
    #
    # Actual breakdown for this experiment:
    #   Total tokens: ~138,000 (tracked from each API call)
    #   Estimated cost: 138,000 × $0.00000025 ≈ $0.035
    #
    # This is a ROUGH ESTIMATE. For precise costs, check your Anthropic
    # dashboard after running the experiment.
    # -----------------------------------------------------------------
    results["metadata"]["estimated_cost_usd"] = total_tokens * 0.00000025
    
    # Save results to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = OUTPUT_DIR / f"experiment_results_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"")
    print(f"=" * 60)
    print(f"EXPERIMENT COMPLETE!")
    print(f"=" * 60)
    print(f"Results saved to: {output_file}")
    print(f"Total API calls: {call_count}")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Estimated cost: ${results['metadata']['estimated_cost_usd']:.4f}")
    print(f"")
    print(f"Next step: Run 'python analyze_results.py' to see:")
    print(f"  - Consistency (variance): How much do scores vary across trials?")
    print(f"  - Accuracy (MAE): How close are Claude's scores to human scores?")
    print(f"  - Bias: Does Claude over-rate or under-rate?")
    print(f"  - Failures: Which cases had big disagreements?")
    print(f"")
    print(f"See GETTING_STARTED.md for help understanding the results.")
    print(f"=" * 60)
    
    return results


# =============================================================================
# MAIN: Entry point when running this script directly
# =============================================================================

if __name__ == "__main__":
    # Check that API key is set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print()
        print("To set it:")
        print("  On Mac/Linux: export ANTHROPIC_API_KEY='your-key-here'")
        print("  On Windows:   $env:ANTHROPIC_API_KEY='your-key-here'")
        print()
        print("Get your key from: https://console.anthropic.com/settings/keys")
        exit(1)
    
    # Run the experiment
    run_experiment()
