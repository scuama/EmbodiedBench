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

    def step(self, instruction: str, observation_text: str, skill_set: list, step_idx: int, img_path: str = None) -> int:
        """
        核心调度循环
        :param instruction: 当前关卡的文本指令
        :param observation_text: 当前视角的文字描述/日志
        :param skill_set: 当前允许的 Action_IDs 列表 (元组或字符串形式)
        :param step_idx: 当前环境的步数
        :param img_path: (新增) 第一人称视觉截图路径，供多模态解析
        :return: 决定执行的 action_id (整数)
        """
        self.logger.info(f"\n========== STARTING STEP {step_idx} ==========")
        
        # 1. 目标提取 (仅在第一步执行)
        if step_idx == 0:
            self.global_intent = self.goal_reasoner.extract_intent(instruction)
            
        # 2. 解空间更新
        self.solution_space.update_capabilities(skill_set)
        self.solution_space.update_observation(observation_text, step_idx, img_path=img_path)
        current_solution_space = self.solution_space.get_solution_space_dict()
        
        # 3. 验证与拦截
        validation_result = self.task_validator.validate_action_feasibility(
            global_intent=self.global_intent,
            solution_space=current_solution_space,
            step=step_idx
        )
        
        # 4. 决策输出
        can_execute = validation_result.get("can_execute", False)
        selected_target = validation_result.get("selected_target", None)
        
        action_id = self._decide_action(current_solution_space["capabilities"], can_execute, selected_target, step_idx)
        
        self.logger.info(f"[Step {step_idx}] CoreAgent Final Decision: Action_ID {action_id} -> {current_solution_space['capabilities'][action_id] if action_id < len(current_solution_space['capabilities']) else 'UNKNOWN'}")
        
        return action_id

    def _decide_action(self, capabilities: list, can_execute: bool, selected_target: str, step: int) -> int:
        """
        根据验证器的结果和 Capabilities 选择最终的 Action ID。
        如果被拦截 (can_execute=False)，则强制选择“探索/导航”相关的动作。
        如果放行，则优先选择与 selected_target 相关的动作（如 Pick / Place）。
        这里使用大模型作为动态路由器。
        """
        system_prompt = "You are an action router. Select the BEST action_id (index) from the capabilities list."
        user_prompt = f"""
        Capabilities (Index: Action Name):
        {json.dumps(list(enumerate(capabilities)), ensure_ascii=False)}
        
        Can Execute Target Task? {can_execute}
        Selected Target Object (if any): {selected_target}
        
        Rules:
        1. If Can Execute is True, find the action_id that interacts with or navigates to the Selected Target Object.
        2. If Can Execute is False, we are in EXPLORATION mode. Pick a 'navigate' action to a new receptacle/area to expand our solution space. DO NOT pick 'pick' or 'place' or 'open'/'close' blindly.
        3. Output a raw JSON exactly like: {{"action_id": <int>}}
        """
        
        result_dict = self.llm.generate_json(system_prompt, user_prompt)
        
        try:
            action_id = int(result_dict.get("action_id", 0))
            if action_id >= len(capabilities) or action_id < 0:
                action_id = 0 # Fallback
        except Exception:
            action_id = 0
            
        self.logger.log_module_output(
            module_name="Core Decision Maker (Module D)",
            step=step,
            output_data=json.dumps({"input_can_execute": can_execute, "selected_target": selected_target, "output_action_id": action_id}, indent=2)
        )
        
        return action_id
