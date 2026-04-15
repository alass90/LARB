import os
import json
import time
from typing import List, Dict, Any
from openai import OpenAI

# API Configuration
API_KEY = "sk-SRi5iUfsYL95k13iIKjMxKR126y8d2UWm2B0jDYtsoyql375"
BASE_URL = "https://api.moonshot.ai/v1"
MODEL_NAME = "kimi-k2.5"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# LARB Benchmark Dataset
BENCHMARK = [
    {
        "id": "Q1",
        "category": "Math Intuition",
        "question": "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        "correct_answer": "0.05",
        "trap_answer": "0.10"
    },
    {
        "id": "Q2",
        "category": "Exponential Growth",
        "question": "In a lake, there is a patch of lily pads. Every day, the patch doubles in size. If it takes 48 days for the patch to cover the entire lake, how long would it take for the patch to cover half of the lake?",
        "correct_answer": "47",
        "trap_answer": "24"
    },
    {
        "id": "Q3",
        "category": "Resource Consistency",
        "question": "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
        "correct_answer": "5",
        "trap_answer": "100"
    },
    {
        "id": "Q4",
        "category": "Probability",
        "question": "In the Monty Hall problem, there are three doors. Behind one door is a car, and behind the two others are goats. You choose Door 1. The host, who knows what is behind the doors, opens Door 3, which has a goat. He then says to you, 'Do you want to pick Door 2?' Is it to your advantage to switch your choice?",
        "correct_answer": "Yes",
        "trap_answer": "No"
    },
    {
        "id": "Q5",
        "category": "Logic (Wason)",
        "question": "If a card has a vowel on one side, then it must have an even number on the other side. You are shown four cards: A, B, 4, and 7. Which card(s) MUST you turn over to check if the rule is being violated?",
        "correct_answer": "A and 7",
        "trap_answer": "A and 4"
    },
    {
        "id": "Q6",
        "category": "Reading Comprehension",
        "question": "A farmer has 17 sheep and all but 9 die. How many sheep are left?",
        "correct_answer": "9",
        "trap_answer": "8"
    },
    {
        "id": "Q7",
        "category": "Kinship Logic",
        "question": "Mary has 4 brothers and 3 sisters. How many sisters does her brother Robert have?",
        "correct_answer": "4",
        "trap_answer": "3"
    },
    {
        "id": "Q8",
        "category": "Interval Calculation",
        "question": "It takes 5 minutes to cut a log into 3 pieces. How long does it take to cut the same log into 10 pieces?",
        "correct_answer": "22.5",
        "trap_answer": "16.66"
    },
    {
        "id": "Q9",
        "category": "Interval Calculation",
        "question": "A clock takes 6 seconds to strike 6 o'clock (meaning there are 6 strikes in total). How long will it take to strike 12 o'clock?",
        "correct_answer": "13.2",
        "trap_answer": "12"
    },
    {
        "id": "Q10",
        "category": "Negation Logic",
        "question": "Subtract 2 from 30, then divide by 0.5, then add 10. What is the result?",
        "correct_answer": "66",
        "trap_answer": "24"
    }
]

def call_kimi(messages: List[Dict], thinking: bool = True) -> str:
    """Invokes Kimi K2.5 with optional thinking mode."""
    extra_body = {}
    if not thinking:
        extra_body = {"chat_template_kwargs": {"thinking": False}}
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=1.0, # Kimi K2.5 requires 1.0 for thinking models
                extra_body=extra_body
            )
            return response.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                wait = (attempt + 1) * 5
                print(f"Rate limit hit. Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"Error calling Kimi: {e}")
            return ""
    return ""

def baseline_run(problem: Dict) -> Dict:
    print(f"Running Baseline for {problem['id']}...")
    messages = [
        {"role": "system", "content": "You are a precise reasoning agent. Solve the problem step-by-step."},
        {"role": "user", "content": problem['question']}
    ]
    answer = call_kimi(messages)
    return {"id": problem['id'], "solution": answer}

def consensus_run(problem: Dict) -> Dict:
    print(f"Running Consensus for {problem['id']}...")
    # Agent 1 solves
    a1_sol = call_kimi([{"role": "user", "content": problem['question']}])
    
    # Agent 2 reviews
    a2_msg = [
        {"role": "user", "content": f"Problem: {problem['question']}\n\nAgent 1 thought: {a1_sol}\n\nPlease review and refine this solution."},
    ]
    a2_sol = call_kimi(a2_msg)
    
    # Agent 3 finalizes
    a3_msg = [
        {"role": "user", "content": f"Problem: {problem['question']}\n\nAgent 1: {a1_sol}\nAgent 2: {a2_sol}\n\nProvide the final correct answer."},
    ]
    a3_sol = call_kimi(a3_msg)
    return {"id": problem['id'], "a1": a1_sol, "a2": a2_sol, "final": a3_sol}

def ara_run(problem: Dict) -> Dict:
    print(f"Running ARA for {problem['id']}...")
    # Phase 1: Isolation
    s1 = call_kimi([{"role": "user", "content": problem['question']}], thinking=True)
    time.sleep(2) # Extra gap for rate limits
    s2 = call_kimi([{"role": "user", "content": problem['question']}], thinking=True)
    time.sleep(2)
    s3 = call_kimi([{"role": "user", "content": problem['question']}], thinking=True)
    
    # Phase 2: Dialectic (Proponent: A1, Opponent: A2, Arbitrator: A3)
    debate_msg = [
        {"role": "system", "content": "You are an Opponent (Devil's Advocate). Your goal is to find any flaw in the Proponent's reasoning."},
        {"role": "user", "content": f"Problem: {problem['question']}\n\nProponent Solution: {s1}\n\nCritique this rigorously. Focus on logic traps."}
    ]
    critique = call_kimi(debate_msg)
    time.sleep(2)
    
    arb_msg = [
        {"role": "system", "content": "You are an Arbitrator. Weigh the Proponent's solution and the Opponent's critique based on objective logic."},
        {"role": "user", "content": f"Problem: {problem['question']}\n\nProponent: {s1}\n\nOpponent Critique: {critique}\n\nIndependent thought S2: {s2}\nIndependent thought S3: {s3}\n\nSynthesize the resilient conclusion."}
    ]
    resonance = call_kimi(arb_msg)
    
    return {
        "id": problem['id'],
        "isolation": [s1, s2, s3],
        "critique": critique,
        "resonance": resonance
    }

def main():
    temp_file = "ara_results_temp.json"
    results = {"baseline": [], "consensus": [], "ara": []}
    
    if os.path.exists(temp_file):
        try:
            with open(temp_file, "r") as f:
                results = json.load(f)
            print(f"Resuming from {len(results['ara'])} completed trials.")
        except:
            print("Could not load temp file, starting fresh.")

    completed_ids = [r["id"] for r in results["ara"]]
    
    for prob in BENCHMARK:
        if prob["id"] in completed_ids:
            continue
            
        print(f"--- Processing {prob['id']}: {prob['category']} ---")
        
        results["baseline"].append(baseline_run(prob))
        time.sleep(5)
        
        results["consensus"].append(consensus_run(prob))
        time.sleep(5)
        
        results["ara"].append(ara_run(prob))
        
        # Incremental Save
        with open(temp_file, "w") as f:
            json.dump(results, f, indent=4)
        print(f"Progress saved for {prob['id']}")
        
        time.sleep(10) # Heavy-duty safety sleep for rate limits

    with open("ara_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print("Trials complete. Final results saved to ara_results.json")
    if os.path.exists(temp_file):
        os.remove(temp_file)

if __name__ == "__main__":
    main()
