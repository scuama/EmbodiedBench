import json
from .llm_client import LLMClient
from .prompt_templates import TASK_VALIDATOR_SYSTEM_PROMPT, TASK_VALIDATOR_USER_PROMPT
from .logger_utils import AgentLogger

class TaskValidator:
    def __init__(self, llm_client: LLMClient, logger: AgentLogger):
        self.llm = llm_client
        self.logger = logger

    def validate_action_feasibility(self, global_intent: dict, solution_space: dict, action_history: list, visited_locations: list, current_location: str, step: int) -> dict:
        """
        核心决策器：比较目标意图、解空间与历史动作，直接输出下一步最佳 action_id
        """
        user_prompt = TASK_VALIDATOR_USER_PROMPT.format(
            global_intent=json.dumps(global_intent, ensure_ascii=False),
            current_location=current_location,
            legal_locations=json.dumps(solution_space.get("legal_locations", []), ensure_ascii=False),
            visited_locations=json.dumps(visited_locations, ensure_ascii=False),
            unvisited_locations=json.dumps([loc for loc in solution_space.get("legal_locations", []) if loc not in visited_locations], ensure_ascii=False),
            capabilities=json.dumps(list(enumerate(solution_space["capabilities"])), ensure_ascii=False),
            visible_objects=json.dumps(solution_space["visible_objects"], ensure_ascii=False),
            memory_objects=json.dumps(solution_space["memory_objects"], ensure_ascii=False),
            action_history=json.dumps(action_history, ensure_ascii=False)
        )
        
        result_dict = self.llm.generate_json(
            system_prompt=TASK_VALIDATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        if not result_dict:
            result_dict = {"action_id": 0, "reasoning": "LLM Error", "selected_target": None}
            
        # Log the decision
        self.logger.log_module_output(
            module_name="TaskValidator (Module C & D merged)",
            step=step,
            output_data=json.dumps(result_dict, indent=2, ensure_ascii=False)
        )
        
        action_id = result_dict.get("action_id", 0)
        self.logger.info(f"[Step {step}] TaskValidator selected Action ID: {action_id}")
            
        return result_dict
