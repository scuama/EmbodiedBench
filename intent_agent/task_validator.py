import json
from .llm_client import LLMClient
from .prompt_templates import TASK_VALIDATOR_SYSTEM_PROMPT, TASK_VALIDATOR_USER_PROMPT
from .logger_utils import AgentLogger

class TaskValidator:
    def __init__(self, llm_client: LLMClient, logger: AgentLogger):
        self.llm = llm_client
        self.logger = logger

    def validate_action_feasibility(self, global_intent: dict, solution_space: dict, step: int) -> dict:
        """
        预验证检查拦截器：比较目标意图和解空间，判断是否放行
        """
        user_prompt = TASK_VALIDATOR_USER_PROMPT.format(
            global_intent=json.dumps(global_intent, ensure_ascii=False),
            capabilities=json.dumps(solution_space["capabilities"], ensure_ascii=False),
            visible_objects=json.dumps(solution_space["visible_objects"], ensure_ascii=False),
            memory_objects=json.dumps(solution_space["memory_objects"], ensure_ascii=False)
        )
        
        result_dict = self.llm.generate_json(
            system_prompt=TASK_VALIDATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        if not result_dict:
            result_dict = {"can_execute": False, "reasoning": "LLM Error", "selected_target": None}
            
        # Log the decision
        self.logger.log_module_output(
            module_name="TaskValidator (Module C)",
            step=step,
            output_data=json.dumps(result_dict, indent=2, ensure_ascii=False)
        )
        
        if not result_dict.get("can_execute", False):
            self.logger.info(f"[Step {step}] TaskValidator INTERCEPTED: Intent unachievable with current solution space.")
        else:
            self.logger.info(f"[Step {step}] TaskValidator APPROVED: Moving forward with action.")
            
        return result_dict
