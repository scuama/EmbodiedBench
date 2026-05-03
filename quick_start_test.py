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
    
    print("\n" + "="*41)
    print("   启动 Intent Reasoning Agent 测试场景   ")
    print("="*41)
    print(f"场景: Episode 3 (解渴替代意图验证)")
    print(f"指令: {fake_instruction}\n")
    
    # 获取 Ground Truth
    try:
        import pickle
        with open('embodiedbench/envs/eb_habitat/datasets/base.pickle', 'rb') as f:
            dataset = pickle.load(f)
            ep_info = dataset['all_eps'][3]['sampled_entities']
            
            
            all_scene_objects = list(set([s.replace('pick up the ', '') for s in env.language_skill_set if s.startswith('pick up the ')]))
            gt_info = {
                "episode_index": 3,
                "target_object": ep_info.get("target_object_name", "unknown"),
                "spawn_location (receptacle)": ep_info.get("source_receptacle_name", "unknown"),
                "destination (receptacle)": ep_info.get("target_receptacle_name", "unknown"),
                "all_scene_objects": sorted(all_scene_objects)
            }
            agent.logger.log_ground_truth(gt_info)
    except Exception as e:
        agent.logger.log_ground_truth({"error": f"Could not load GT from dataset: {e}"})

    step_idx = 0
    done = False
    
    skill_set = env.language_skill_set
    observation_text = "You just spawned in the environment."
    
    while not done and step_idx < 50: # limit to 50 steps for test
        # 截取画面供 Vision 模型识别 (分离第一人称和双视角)
        dual_img_path, fpv_img_path = agent.logger.save_obs_dual_view(obs, step_idx)
        print(f"---> Generated observation image at: {dual_img_path}")
        
        validation_result = agent.step(fake_instruction, observation_text, skill_set, step_idx, img_path=fpv_img_path, dual_img_path=dual_img_path)
        action_id = validation_result.get("action_id", 0)
        
        action_str = skill_set[action_id] if action_id < len(skill_set) else "UNKNOWN"
        print(f"\n---> [Step {step_idx}] Executing: {action_str} (ID: {action_id})")
        
        # Stop early if the agent has communicated with the user (e.g. found an alternative)
        if validation_result.get("communication_to_user"):
            print(f"\n[Agent Finished] {validation_result['communication_to_user']}")
            done = True
            break
            
        # 真正执行动作
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
