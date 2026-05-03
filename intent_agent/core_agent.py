import json
from .llm_client import LLMClient
from .logger_utils import AgentLogger
from .goal_reasoner import GoalReasoner
from .solution_space import SolutionSpaceAnalyzer
from .task_validator import TaskValidator

class IntentReasoningAgent:
    def __init__(self, episode_id=None, model_name="gpt-4o-mini"):
        self.logger = AgentLogger(episode_id)
        self.llm = LLMClient(model_name=model_name)
        
        # Initialize Core Modules
        self.goal_reasoner = GoalReasoner(self.llm, self.logger)
        self.solution_space = SolutionSpaceAnalyzer(self.llm, self.logger)
        self.task_validator = TaskValidator(self.llm, self.logger)
        
        self.global_intent = {}
        self.action_history = []
        self.current_location = "unknown starting location"

    def step(self, instruction: str, observation_text: str, skill_set: list, step_idx: int, img_path: str = None, dual_img_path: str = None) -> dict:
        """
        核心调度循环
        :param instruction: 当前关卡的文本指令
        :param observation_text: 当前视角的文字描述/日志
        :param skill_set: 当前允许的 Action_IDs 列表 (元组或字符串形式)
        :param step_idx: 当前环境的步数
        :param img_path: (新增) 第一人称视觉截图路径，供多模态解析
        :param dual_img_path: (新增) 双视角截图路径，供日志记录
        :return: 决定执行的动作详情字典 (dict)
        """
        self.logger.info(f"\n========== STARTING STEP {step_idx} ==========")
        
        # 1. 目标提取 (仅在第一步执行)
        if step_idx == 0:
            self.global_intent = self.goal_reasoner.extract_intent(instruction)
            
        # 2. 解空间更新
        self.solution_space.update_capabilities(skill_set)
        self.solution_space.update_observation(observation_text, self.current_location, step_idx, img_path=img_path, dual_img_path=dual_img_path)
        current_solution_space = self.solution_space.get_solution_space_dict()
        
        # 3. 验证与决策 (Merged C & D)
        # 提取 visited_locations
        visited_locations = list(set([
            action.replace("navigate to the ", "").replace("navigate to ", "").strip() 
            for action in self.action_history if "nav" in action.lower()
        ]))
        self.logger.info(f"[Visited Locations] {visited_locations}")
        
        validation_result = self.task_validator.validate_action_feasibility(
            global_intent=self.global_intent,
            solution_space=current_solution_space,
            action_history=self.action_history,
            visited_locations=visited_locations,
            current_location=self.current_location,
            step=step_idx
        )
        
        if validation_result.get("communication_to_user"):
            self.logger.info(f"[Communication to User] {validation_result['communication_to_user']}")
        
        # 4. 提取动作并更新状态
        action_id = validation_result.get("action_id", 0)
        
        if action_id is None:
            self.logger.log_module_output(
                module_name="CoreAgent",
                step=step_idx,
                output_data="Agent decided to stop. No action selected (action_id is None)."
            )
            # Default to 0 or some valid format to avoid crashing, or return a special termination signal.
            # Usually we return a stop action. If no stop action is known, return 0 as dummy.
            validation_result["action_id"] = 0
            return validation_result
        
        action_str = skill_set[action_id] if action_id < len(skill_set) else "UNKNOWN"
        self.action_history.append(action_str)
        
        self.logger.info(f"[Step {step_idx}] CoreAgent Final Decision: Action_ID {action_id} -> {action_str}")
        
        # Check if navigate action to update current_location
        if "navigate to" in action_str.lower():
            target_loc = action_str.lower().replace("navigate to the", "").replace("navigate to", "").strip()
            self.current_location = target_loc
            
        return validation_result
