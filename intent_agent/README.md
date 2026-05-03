# Intent Agent 意图推理具身智能大脑

这是一个基于多模态大模型（Vision LLMs）设计的具身智能高阶推理引擎。
与传统的“死板执行指令”的 Agent 不同，Intent Agent 具备**目标深度推理 (5 Whys)** 与**主动寻路替代方案 (Replanning/Exploration)** 的能力。当环境发生变动或目标丢失时，它能像人类一样推理出用户的“核心意图”（如：渴了想找水），并寻找替代解（如：没有苹果，可以拿橘子）。

## 🧩 核心架构与模块说明

目前系统采用了 **单体综合调度 + 职能切片** 的架构，主要包含以下几个子模块：

- **`core_agent.py`** (中央调度器)：
  主入口。负责协调各个子模块，维护 Action History，并向外部（例如 Habitat 仿真环境）暴露唯一的 `step()` 调用接口。

- **`goal_reasoner.py`** (模块 A：目标推理引擎)：
  **仅在 Episode 第一步调用**。负责分析用户的原始自然语言指令，采用结构化的“5 Whys”逻辑链，深入挖掘用户的深层诉求（Deep Intent），并输出能够满足该诉求的物体物理属性（例如：多汁、解渴）。

- **`solution_space.py`** (模块 B：解空间与多模态感知器)：
  负责 Agent 的“眼”和“记忆”。在每个 Step 接收物理引擎的文字反馈以及**第一人称图像 (img_path)**，调用视觉模型（如 `gpt-5.4-mini`）提取当前视野中的可见物体。同时维护一个 `object -> current_location` 的全局记忆地图。

- **`task_validator.py`** (模块 C&D：任务验证与动作决策)：
  核心决策大脑。在每个 Step 读取 **全局意图**、**解空间记忆** 以及 **历史动作**，判断当前视线范围内或记忆中是否有符合意图的目标/替代品。如果没有，它会主动进入“探索模式 (Exploration)”去寻路；如果有，则下达拾取等动作指令，最终直接输出下一步的 `action_id`。

- **支撑组件**：
  - `llm_client.py`: 封装了统一的纯文本及多模态 Vision API 调用，支持动态切换模型（默认 `gpt-5.4-mini`，高维推理切 `gpt-4o`）。
  - `prompt_templates.py`: 集中管理所有模块的 System & User Prompt，严格约束输出为规范的 JSON 结构。
  - `logger_utils.py`: 为每个 Episode 自动生成结构化的排错日志（存放在 `logs/` 目录下），便于审查思维链。

---

## 🚀 快速上手 (使用方法)

Intent Agent 已经被设计为“即插即用”的模块，它与底层的仿真引擎（如 Habitat, AI2-THOR 等）实现了完全的接口解耦。

您可以参考下方伪代码，将其挂载到任何具身环境的主循环中：

```python
from intent_agent import IntentReasoningAgent

# 1. 实例化 Agent
agent = IntentReasoningAgent(episode_id="test_episode_01")

# 2. 从环境中获取初始状态和指令
obs = env.reset()
instruction = env.get_instruction()   # 例如："I am thirsty, bring me the apple."
skill_set = env.get_action_space()    # 当前环境支持的 Action 列表

step_idx = 0
done = False

# 3. 开启仿真主循环
while not done:
    # (可选) 截取第一人称画面供多模态模型识别视野
    img_path = env.save_current_frame_to_disk() 
    
    # 纯净的文字 Feedback（上一步操作的物理反馈）
    feedback_text = env.get_feedback()

    # 4. 调用 Intent Agent 核心 step 方法，直接获取大模型决策出的 action_id
    action_id = agent.step(
        instruction=instruction,
        observation_text=feedback_text,
        skill_set=skill_set,
        step_idx=step_idx,
        img_path=img_path   # 传入视觉信号
    )
    
    # 5. 在底层环境中执行动作
    obs, reward, done, info = env.step(action_id)
    
    step_idx += 1
```

> **调试提示**：在实际挂载测试时，建议使用 `tail -f intent_agent/logs/<episode_name>.log` 实时监控大模型的 5 Whys 推理链与拦截决策，以便于后续调优 Prompt 解决“逻辑幻觉”和“死循环”问题。
