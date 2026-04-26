import json
import os
from .llm_client import LLMClient
from .prompt_templates import SOLUTION_SPACE_SYSTEM_PROMPT, SOLUTION_SPACE_USER_PROMPT
from .logger_utils import AgentLogger

class SolutionSpaceAnalyzer:
    def __init__(self, llm_client: LLMClient, logger: AgentLogger):
        self.llm = llm_client
        self.logger = logger
        self.memory_objects = set()
        self.current_visible_objects = []
        self.capabilities = []

    def update_capabilities(self, skill_set: list):
        """更新动作能力"""
        # skill_set usually is a list of tuples like ('nav_to_tvstand', ...)
        self.capabilities = [str(skill) for skill in skill_set]

    def update_observation(self, observation_text: str, step: int, img_path: str = None):
        """解析环境视觉与文本反馈，提取可视物体"""
        user_prompt = SOLUTION_SPACE_USER_PROMPT.format(observation_text=observation_text)
        
        if img_path and os.path.exists(img_path):
            result_dict = self.llm.generate_vision_json(
                system_prompt=SOLUTION_SPACE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                image_path=img_path
            )
        else:
            # Fallback to text only if no image provided
            result_dict = self.llm.generate_json(
                system_prompt=SOLUTION_SPACE_SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
        
        visible = result_dict.get("visible_objects", [])
        self.current_visible_objects = visible
        
        # 将新发现的物品加入全局记忆
        for obj in visible:
            self.memory_objects.add(obj)
            
        # Log the output
        output_data = {
            "capabilities_count": len(self.capabilities),
            "currently_visible": self.current_visible_objects,
            "memory_objects": list(self.memory_objects)
        }
        
        self.logger.log_module_output(
            module_name="SolutionSpaceAnalyzer (Module B)",
            step=step,
            output_data=json.dumps(output_data, indent=2, ensure_ascii=False)
        )

    def get_solution_space_dict(self):
        return {
            "capabilities": self.capabilities,
            "visible_objects": self.current_visible_objects,
            "memory_objects": list(self.memory_objects)
        }
