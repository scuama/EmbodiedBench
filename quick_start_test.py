import sys
import os
sys.path.append("/mnt/disk1/decom/EmbodiedBench")
from intent_agent import IntentReasoningAgent
from embodiedbench.envs.eb_habitat.EBHabEnv import EBHabEnv
import time

def run_test():
    print("Starting Intent Reasoning Agent Test...")
    # Episode 3 actually has an Orange on the TV stand, and the target is sink.
    env = EBHabEnv(eval_set='base', selected_indexes=[3])
    agent = IntentReasoningAgent(episode_id="test_ep3_quickstart")
    
    obs = env.reset()
    fake_instruction = "I am thirsty, bring me the apple from the TV stand to the sink."
    print(f"Original Instruction (Hidden): {env.episode_language_instruction}")
    print(f"Fake Instruction (Given to Agent): {fake_instruction}")
    
    step_idx = 0
    done = False
    
    skill_set = env.language_skill_set
    observation_text = "You just spawned in the environment."
    
    while not done and step_idx < 15: # limit to 15 steps for test
        # 截取第一人称画面供 Vision 模型识别
        img_path = env.save_image(obs)
        print(f"---> Generated observation image at: {img_path}")
        
        action_id = agent.step(fake_instruction, observation_text, skill_set, step_idx, img_path=img_path)
        
        action_str = skill_set[action_id] if action_id < len(skill_set) else "UNKNOWN"
        print(f"\n---> [Step {step_idx}] Executing: {action_str} (ID: {action_id})")
        
        # Execute in environment
        obs, reward, done, info = env.step(action_id)
        
        # Construct next observation text
        feedback = info.get('env_feedback', '')
        observation_text = f"Feedback: {feedback}."
        print(f"---> Environment Feedback: {feedback}")
        
        step_idx += 1
        time.sleep(1)

    print("\nTest finished. Check the logs in /mnt/disk1/decom/EmbodiedBench/intent_agent/logs/")
    env.close()

if __name__ == "__main__":
    run_test()
