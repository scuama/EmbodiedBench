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
        self.solution_space.update_observation(observation_text, self.current_location, step_idx, img_path=img_path)
        current_solution_space = self.solution_space.get_solution_space_dict()
        
        # 3. 验证与决策 (Merged C & D)
        validation_result = self.task_validator.validate_action_feasibility(
            global_intent=self.global_intent,
            solution_space=current_solution_space,
            action_history=self.action_history[-5:],  # 只传递最近5步历史避免过长
            current_location=self.current_location,
            step=step_idx
        )
        
        # 4. 提取动作并更新状态
        action_id = validation_result.get("action_id", 0)
        
        # 越界保护
        if action_id >= len(current_solution_space["capabilities"]) or action_id < 0:
            action_id = 0
            
        action_str = current_solution_space["capabilities"][action_id]
        
        # 若是导航动作，更新当前所处位置
        if "nav" in action_str.lower():
            loc = action_str.replace("navigate to the ", "").replace("navigate to ", "").strip()
            self.current_location = loc
            
        self.action_history.append(action_str)
        
        self.logger.info(f"[Step {step_idx}] CoreAgent Final Decision: Action_ID {action_id} -> {action_str}")
        
        return action_id
