import sys
import os
import time
import argparse

sys.path.append("/mnt/disk1/decom/EmbodiedBench")
from intent_agent import IntentReasoningAgent
from embodiedbench.envs.eb_habitat.EBHabEnv import EBHabEnv

def run_interactive_test():
    parser = argparse.ArgumentParser(description="Intent Agent Interactive Test")
    parser.add_argument("--instruction", type=str, help="Initial instruction to start a new session", default="")
    parser.add_argument("--feedback", type=str, help="User feedback to resume an existing session", default="")
    args = parser.parse_args()

    if not args.instruction and not args.feedback:
        print("Please provide either --instruction or --feedback.")
        return

    print("\n" + "="*50)
    print("   Starting Intent Reasoning Agent (Interactive)   ")
    print("="*50)

    # Initialize environment
    env = EBHabEnv(eval_set='base', selected_indexes=[3])
    
    # Initialize Agent with optional feedback
    agent = IntentReasoningAgent(
        episode_id="test_interactive", 
        resume_feedback=args.feedback if args.feedback else None,
        scene_id="FloorPlan22" # Mocking scene ID for persistent memory
    )
    
    obs = env.reset()
    
    if args.instruction:
        print(f"[*] Starting NEW session with instruction: {args.instruction}")
        instruction = args.instruction
        # Clean up existing session memory if it's a new instruction
        memory_content = agent.memory_manager.read_memory()
        if "## Current Session Context" in memory_content:
            parts = memory_content.split("## Current Session Context")
            agent.memory_manager.write_memory(parts[0].strip() + "\n\n## Current Session Context\n")
            print("[*] Cleared previous session memory.")
    else:
        print(f"[*] Resuming session with feedback: {args.feedback}")
        instruction = "RESUMED_SESSION" # Will be ignored by core_agent because global_intent is already loaded

    step_idx = 0
    done = False
    skill_set = env.language_skill_set
    observation_text = "You just spawned in the environment."
    
    while not done and step_idx < 50:
        # Save dual view (optional but good for logs)
        dual_img_path, fpv_img_path = agent.logger.save_obs_dual_view(obs, step_idx)
        print(f"\n---> [Step {step_idx}] Generated observation image at: {dual_img_path}")
        
        # Agent step
        validation_result = agent.step(
            instruction=instruction, 
            observation_text=observation_text, 
            skill_set=skill_set, 
            step_idx=step_idx, 
            img_path=fpv_img_path, 
            dual_img_path=dual_img_path
        )
        
        # Check if agent decided to stop and save session
        if validation_result.get("stop_and_save"):
            print(f"\n[!] Agent Execution Paused.")
            print(f"[!] Agent Message: {validation_result.get('communication_to_user')}")
            print("[!] Session state saved to persistent_memory.md")
            print("[!] Exiting script. Run again with --feedback to resume.\n")
            break
            
        action_id = validation_result.get("action_id", 0)
        action_str = skill_set[action_id] if action_id < len(skill_set) else "UNKNOWN"
        print(f"---> Agent decided to execute: {action_str} (ID: {action_id})")
        
        # Execute action in environment
        obs, reward, done, info = env.step(action_id)
        
        feedback = info.get('env_feedback', '')
        observation_text = f"Feedback: {feedback}."
        print(f"---> Environment Feedback: {feedback}")
        
        step_idx += 1
        time.sleep(1)

    print("\nScript Finished.")
    env.close()

if __name__ == "__main__":
    run_interactive_test()
