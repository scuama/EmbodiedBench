import json
import os
from .llm_client import LLMClient
from .prompt_templates import SOLUTION_SPACE_SYSTEM_PROMPT, SOLUTION_SPACE_USER_PROMPT
from .logger_utils import AgentLogger

class SolutionSpaceAnalyzer:
    def __init__(self, llm_client: LLMClient, logger: AgentLogger):
        self.llm = llm_client
        self.logger = logger
        self.memory_objects = {}
        self.current_visible_objects = []
        self.capabilities = []

    def update_capabilities(self, skill_set: list):
        """更新动作能力并提取合法词汇表"""
        self.capabilities = [str(skill) for skill in skill_set]
        self.legal_locations = []
        self.legal_objects = []
        for cap in self.capabilities:
            cap_clean = cap.replace("navigate to the ", "nav_").replace("navigate to ", "nav_")
            if cap_clean.startswith("nav_"):
                loc = cap_clean[4:].strip()
                if loc not in self.legal_locations:
                    self.legal_locations.append(loc)
            else:
                for prefix in ["pick up the ", "open the ", "close the ", "interact with the "]:
                    if cap.startswith(prefix):
                        obj = cap[len(prefix):].strip()
                        if obj not in self.legal_objects:
                            self.legal_objects.append(obj)
                        break

    def update_observation(self, observation_text: str, current_location: str, step: int, img_path: str = None, dual_img_path: str = None):
        """解析环境视觉与文本反馈，提取可视物体"""
        user_prompt = SOLUTION_SPACE_USER_PROMPT.format(
            observation_text=observation_text,
            legal_objects=json.dumps(getattr(self, "legal_objects", []), ensure_ascii=False)
        )
        
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
            self.memory_objects[obj] = current_location
            
        # Log the output
        output_data = {
            "capabilities_count": len(self.capabilities),
            "currently_visible": self.current_visible_objects,
            "memory_objects": self.memory_objects
        }
        
        self.logger.log_module_output(
            module_name="SolutionSpaceAnalyzer (Module B)",
            step=step,
            output_data=json.dumps(output_data, indent=2, ensure_ascii=False),
            img_path=dual_img_path if dual_img_path else img_path
        )

    def get_solution_space_dict(self):
        return {
            "capabilities": self.capabilities,
            "legal_locations": getattr(self, "legal_locations", []),
            "visible_objects": self.current_visible_objects,
            "memory_objects": self.memory_objects
        }
