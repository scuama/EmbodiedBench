import os
import re
from .llm_client import LLMClient
from .logger_utils import AgentLogger
from .prompt_templates import MEMORY_UPDATE_SYSTEM_PROMPT, MEMORY_UPDATE_USER_PROMPT

class MemoryManager:
    def __init__(self, llm_client: LLMClient, logger: AgentLogger, memory_file: str = "persistent_memory.md"):
        self.llm = llm_client
        self.logger = logger
        self.memory_file = os.path.join(os.path.dirname(__file__), memory_file)
        # 确保文件存在
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                f.write("# User Persistent Memory\n\n## Preferences\n- 用户在饥饿时明确表示过喜欢吃香蕉。\n\n## Interaction History\n\n## Current Session Context\n")

    def read_memory(self) -> str:
        with open(self.memory_file, 'r', encoding='utf-8') as f:
            return f.read()

    def write_memory(self, content: str):
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def process_feedback(self, feedback_text: str) -> dict:
        """
        调用大模型解析用户反馈：
        1. 决定是否更新长期偏好
        2. 提取新的 global_intent
        3. 重写持久化 MD 文件
        返回更新后的 global_intent
        """
        current_memory = self.read_memory()
        
        user_prompt = MEMORY_UPDATE_USER_PROMPT.format(
            current_memory=current_memory,
            feedback_text=feedback_text
        )
        
        self.logger.info(f"[MemoryManager] Processing user feedback: {feedback_text}")
        
        result_dict = self.llm.generate_json(
            system_prompt=MEMORY_UPDATE_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        if result_dict:
            new_memory_markdown = result_dict.get("new_memory_markdown", "")
            new_global_intent = result_dict.get("new_global_intent", {})
            if new_memory_markdown:
                self.write_memory(new_memory_markdown)
                self.logger.info("[MemoryManager] Persistent memory updated.")
            return new_global_intent
        else:
            self.logger.error("[MemoryManager] Failed to process feedback.")
            return {}

    def save_session_state(self, scene_id: str, global_intent: dict, visited_locations: list, known_objects: dict, action_history: list, last_agent_message: str):
        """
        将当前探索进度直接拼接到 Markdown 中并覆写保存
        """
        current_memory = self.read_memory()
        
        # 提取 Preferences 和 Interaction History 部分，丢弃旧的 Session Context
        # 使用正则表达式分割
        parts = re.split(r'## Current Session Context', current_memory)
        header_part = parts[0].strip()
        
        session_markdown = f"""
## Current Session Context
- **scene_id**: {scene_id}
- **global_intent**: {global_intent}
- **visited_locations**: {', '.join(visited_locations) if visited_locations else 'None'}
- **known_objects**:
"""
        if known_objects:
            for obj, loc in known_objects.items():
                session_markdown += f"  - {loc}: {obj}\n"
        else:
            session_markdown += "  - None\n"
            
        session_markdown += f"- **action_history**: {', '.join(action_history) if action_history else 'None'}\n"
        if last_agent_message:
            session_markdown += f"- **Last Agent Message**: {last_agent_message}\n"
            
        full_markdown = header_part + "\n\n" + session_markdown.strip() + "\n"
        self.write_memory(full_markdown)
        self.logger.info("[MemoryManager] Session state saved to disk.")

    def load_session_state(self) -> dict:
        """
        从 Markdown 文件中解析恢复 Session 状态
        """
        current_memory = self.read_memory()
        parts = re.split(r'## Current Session Context', current_memory)
        if len(parts) < 2:
            return None
            
        session_part = parts[1]
        
        # 简单正则提取
        scene_id_match = re.search(r'- \*\*scene_id\*\*: (.*)', session_part)
        intent_match = re.search(r'- \*\*global_intent\*\*: (.*)', session_part)
        visited_match = re.search(r'- \*\*visited_locations\*\*: (.*)', session_part)
        
        # 提取 known_objects
        known_objects = {}
        obj_section_match = re.search(r'- \*\*known_objects\*\*:\n((?:  - .*\n?)*)', session_part)
        if obj_section_match:
            lines = obj_section_match.group(1).strip().split('\n')
            for line in lines:
                if ':' in line and 'None' not in line:
                    loc, obj = line.strip().lstrip('- ').split(':', 1)
                    known_objects[obj.strip()] = loc.strip()
                    
        # 提取 action history
        history_match = re.search(r'- \*\*action_history\*\*: (.*)', session_part)

        scene_id = scene_id_match.group(1).strip() if scene_id_match else ""
        try:
            # intent is stored as string representation of dict
            import ast
            global_intent = ast.literal_eval(intent_match.group(1).strip()) if intent_match else {}
        except:
            global_intent = {}
            
        visited_str = visited_match.group(1).strip() if visited_match else ""
        visited_locations = [x.strip() for x in visited_str.split(',')] if visited_str and visited_str != 'None' else []
        
        history_str = history_match.group(1).strip() if history_match else ""
        action_history = [x.strip() for x in history_str.split(',')] if history_str and history_str != 'None' else []

        return {
            "scene_id": scene_id,
            "global_intent": global_intent,
            "visited_locations": visited_locations,
            "known_objects": known_objects,
            "action_history": action_history
        }
