import os
import logging
from datetime import datetime

class AgentLogger:
    def __init__(self, episode_id=None):
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.episode_id = episode_id if episode_id else run_timestamp
        self.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 强制在文件名后缀加上时间戳，确保每次运行都是新文件
        if episode_id:
            filename = f"episode_{self.episode_id}_{run_timestamp}.log"
        else:
            filename = f"episode_{self.episode_id}.log"
            
        self.log_file = os.path.join(self.log_dir, filename)
        
        # Configure logging
        # 使用 filename 作为 logger 的名字，防止在同一进程中多次实例化导致 Handler 冲突或重复追加
        self.logger = logging.getLogger(f"IntentAgent_{filename}")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(self.log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Avoid duplicate logs if instantiated multiple times
        if not self.logger.handlers:
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def log_module_output(self, module_name: str, step: int, output_data: str):
        """记录特定模块在特定步骤的核心输出"""
        separator = "-" * 40
        log_message = f"\n{separator}\n[Step: {step}] [Module: {module_name}]\n{output_data}\n{separator}"
        self.logger.info(log_message)

    def info(self, msg: str):
        self.logger.info(msg)
        
    def error(self, msg: str):
        self.logger.error(msg)
