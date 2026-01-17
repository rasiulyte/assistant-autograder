"""
AI Assistant Autograder Experiment Runner

This script:
1. Runs each test case through the autograder
2. Tests multiple prompt strategies
3. Runs multiple trials to measure consistency
4. Saves results for analysis

Usage:
    python run_autograder.py
    
Estimated API cost: ~$0.50-1.00 (using Claude Haiku)
Estimated time: 10-15 minutes
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    exit(1)

from test_cases import get_test_cases
from prompts import get_prompt, get_strategies

# Configuration
MODEL = "claude-3-haiku-20240307"  # Fast and cheap for experiments
TEMPERATURE = 0.3  # Lower = more consistent, but some variance for testing
NUM_TRIALS = 3  # Number of times to evaluate each case per strategy
OUTPUT_DIR = Path("results")


def extract_json_scores(response_text: str) -> dict | None:
    """
    Extract JSON scores from LLM response.
    Handles responses with reasoning text before/after JSON.
    """
    # Try to find JSON block in response
    json_match = re.search(r'\{[^{}]*"correctness"[^{}]*\}', response_text, re.DOTALL)
    
    if json_match:
        try:
            scores = json.loads(json_match.group())
            # Validate scores are in expected range
            for key in ["correctness", "completeness", "conciseness", "naturalness", "safety"]:
                if key not in scores:
                    return None
                if not isinstance(scores[key], (int, float)) or scores[key] < 1 or scores[key] > 5:
                    return None
            return scores
        except json.JSONDecodeError:
            return None
    return None


def run_single_evaluation(client, query: str, response: str, strategy: str) -> dict:
    """
    Run a single evaluation using the specified strategy.
    
    Returns:
        dict with scores and metadata
    """
    prompt = get_prompt(strategy, query, response)
    
    start_time = time.time()
    
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            temperature=TEMPERATURE,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text
        elapsed_time = time.time() - start_time
        
        scores = extract_json_scores(response_text)
        
        return {
            "success": scores is not None,
            "scores": scores,
            "raw_response": response_text,
            "elapsed_time": elapsed_time,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens
        }
        
    except Exception as e:
        return {
            "success": False,
            "scores": None,
            "error": str(e),
            "elapsed_time": time.time() - start_time
        }


def run_experiment():
    """
    Run the full autograder experiment.
    """
    # Initialize
    client = anthropic.Anthropic()
    test_cases = get_test_cases()
    strategies = get_strategies()
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    results = {
        "metadata": {
            "model": MODEL,
            "temperature": TEMPERATURE,
            "num_trials": NUM_TRIALS,
            "num_test_cases": len(test_cases),
            "strategies": strategies,
            "timestamp": datetime.now().isoformat()
        },
        "evaluations": []
    }
    
    total_calls = len(test_cases) * len(strategies) * NUM_TRIALS
    print(f"Starting experiment: {total_calls} total API calls")
    print(f"  - {len(test_cases)} test cases")
    print(f"  - {len(strategies)} strategies")
    print(f"  - {NUM_TRIALS} trials each")
    print()
    
    call_count = 0
    
    for tc in test_cases:
        print(f"Evaluating: {tc['id']} ({tc['category']})")
        
        case_results = {
            "test_case_id": tc["id"],
            "category": tc["category"],
            "query": tc["query"],
            "response": tc["response"],
            "ground_truth": tc["ground_truth"],
            "evaluations": {}
        }
        
        for strategy in strategies:
            strategy_results = []
            
            for trial in range(NUM_TRIALS):
                call_count += 1
                print(f"  [{call_count}/{total_calls}] {strategy} trial {trial + 1}...", end=" ")
                
                result = run_single_evaluation(
                    client,
                    tc["query"],
                    tc["response"],
                    strategy
                )
                
                if result["success"]:
                    print(f"✓ {result['scores']}")
                else:
                    print(f"✗ Failed")
                
                strategy_results.append(result)
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
            
            case_results["evaluations"][strategy] = strategy_results
        
        results["evaluations"].append(case_results)
        print()
    
    # Calculate summary statistics
    total_tokens = sum(
        eval_result.get("input_tokens", 0) + eval_result.get("output_tokens", 0)
        for case in results["evaluations"]
        for strategy_results in case["evaluations"].values()
        for eval_result in strategy_results
    )
    
    results["metadata"]["total_tokens"] = total_tokens
    results["metadata"]["estimated_cost_usd"] = total_tokens * 0.00000025  # Haiku pricing estimate
    
    # Save results
    output_file = OUTPUT_DIR / f"experiment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    print(f"Total API calls: {call_count}")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Estimated cost: ${results['metadata']['estimated_cost_usd']:.4f}")
    
    return results


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Run: export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)
    
    run_experiment()
