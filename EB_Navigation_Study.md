# EB-Navigation 环境研究与魔改记录

本指南详细记录了针对 EmbodiedBench 框架中 `EB-Navigation` 环境的结构剖析与魔改测试流程。

## 1. EB-Navigation 核心机制

`EB-Navigation` 基于 Unity 构建的 AI2-THOR 室内环境，专注于评估视觉导航与寻路能力。
- **环境输入 (Agent 视角)**: 大模型 (VLM) 接收机器人当前的第一人称 RGB 截图，并附带一条明确的房间探索与目标寻找指令 (Instruction)。
- **环境输出 (Agent 动作)**: 大模型必须在 8 向基础离散动作列表中进行选择（如 `0: 向前走`, `4: 向右转 90 度` 等）。它不被允许输出绝对的三维坐标，而是直接下达单一动作 ID。
- **环境反馈**: Python API (`VLMPlanner`) 获取模型动作 ID，立刻转译为空手部操作的 Unity 平台 HTTP 请求，执行后重新宣染新画面作为下一步循环的输入。

## 2. 真实场景切片剖析

以下是我们在 `base.json` （基础考验集）中提取的关于寻找 "Kettle" (水壶) 的一道代表性 Episode：

```json
{
    "scene": "FloorPlan22",
    "targetObjectType": "Kettle",
    "targetObjectIds": "Kettle|-02.62|+00.93|-00.72",
    "instruction": "navigate to the Kettle in the room and be as close as possible to it",
    "agentPose": {
        "position": { "x": -0.2, "y": 0.90, "z": 0.90 },
        "rotation": 270.0,
        "horizon": 0.0
    }
}
```

### 参数深度说明
- **`scene`**: 设定了加载预制房间地图为 `FloorPlan22` 房型。
- **`targetObjectType`**: 明确任务的考核终极目标是寻找 `Kettle` 对象。
- **`instruction`**: 给予语言大模型的最直接文本引导词。这直接注入到了 System Prompt 的任务约束部分。
- **`agentPose`**: 定义机器人在屋内的绝对出生坐标 $(X,Y,Z)$ 以及偏航朝向旋转角。
- **成功判断标准**: 环境不要求拾取(`Pick`)，Agent 只要通过使用离散动作贴近 `targetObjectType` 设定的目标物体，在达到特定物理距离阈值并处于可视判定范围内时，环境即判定该 episode **成功 (Success)**。

## 3. 魔改测试记录 (Custom Config)

我们通过文本直接修改了 JSON，并在隔离的配置文件中进行定制：
- **目标**: 将原始寻找 Kettle 的任务的提示词更替为 `"I am modifying this for testing! Navigate to the Kettle immediately!"`。
- **执行命令**:
  ```bash
  python -m embodiedbench.main env=eb-nav model_name=gpt-4o-mini ++eval_sets="[base_custom]" ++selected_indexes="[0]"
  ```
- **预期结果**: 该评测应当仅执行这 1 题目，调用大模型生成交互步骤动作，并将整个寻找水壶的视觉流程序列保存在记录目录中进行可视化。
\n### 💣 避坑指南：依赖与环境冲突\n\n测试过程中发现，最初教程中建议直接在 `embench` 中运行导航任务是**错误**的。由于 Python 依赖冲突，`EmbodiedBench` 官方为各个子任务配置了不同的虚拟环境：\n- **`EB-Navigation`** 强制需要使用 `ai2thor>=3.3.0`（用于支持修改分辨率和视场角等属性），这记录在其专门的 `environment_eb-nav.yaml` 中。\n- **`EB-ALFRED`** 却需要一个很老的 `ai2thor==2.1.0`。\n\n这意味着我们必须在系统内执行 `conda activate embench_nav` 后再运行 `eb-nav` 测试！并在无显服务器上配合 `xvfb-run -a` 及代理才能成功进行云渲染交互。

## 4. 跑通验证及运行截图结果

经过排雷及提供完整的 API Key 与代理配置下，我们在 **2026-03-08 15:35** 终于成功完成了该魔改设定的评估流程！

### Agent 交互成绩单
评测脚本运行完后产生了一系列最终日志。
- **总步数（num_steps）**: `20` 步
- **成功率（task_success）**: `0.0`
- **执行耗时**: `34.7` 秒
> **结论分析**：VLM (我们使用了 `gpt-4o-mini`) 在房间内转悠和移动了多达 `20` 个动作步骤。由于没有最终有效靠近或者在视口内找到 Kettle 热水壶（也许壶在某个柜子死角里或者模型陷入死胡同），该回合挑战在达到了预设最大步数时由于目标依然未完成所以得分为 `0.0` 失败。但这证明了 **魔改数据流程 + VLM端到端大循环推理 + 无头 3D 物理宣染交互** 的完整通路是100%没问题的了！

### 动作演化图片集 (Visual Steps)
框架将大模型每个步骤收到的实时视觉图像记录到了结果目录下：

**Step 0：出生起点（输入指令为寻找Kettle并带上了我们魔改的前缀文字！）**
![step_0](./step_0.png)

**Step 20：最终截止步的视角（大模型乱转后结束时的最后一眼房间）**
![step_20](./step_20.png)

本报告总结至此。后续所有环境运行只需务必激活特定子环境（如`embench_nav`）并永久化你的 API 变量即万无一失。

## 5. 高阶技巧：场景物品查询、目标替换与动态放置(传送)

根据进阶需求，我们对 AI2-THOR 的开放能力进行了进一步摸索，总结出以下高级魔改方案：

### (1) 如何查看场景中有哪些物品？
你可以通过实例化一个精简版 `ai2thor.controller.Controller`，并利用 `event.metadata['objects']` 直接导出场景内的全部道具。详见我们撰写的 `/mnt/disk1/decom/EmbodiedBench/list_objects.py`。
在 `FloorPlan22` 场景中，我们共导出了 **70** 个对象，包含 Apple（苹果）、Tomato（番茄）、Microwave（微波炉）等等。

### (2) 能否导航到其他的物品上？
完全可以。根据上面导出的完整物体报告，我们可以知道 Apple 的 `objectType` 是 `"Apple"`，`objectId` 是 `"Apple|+00.32|+01.14|+01.51"`，其所在坐标为 `(x: 0.32, y: 1.14, z: 1.50)`。
在前面测试中，我们修改了 `base_custom.json` 的 `targetObjectType` 和 `targetObjectIds`，将我们要寻找的物品从 `Kettle` 变成了 `Apple`。在第二次基准测试中，由于大模型离苹果更近且视线没有被遮挡，我们获得了 **成功率 1.0 (满分)，仅消耗 1 步导航步数** 的完美评测战绩！

### (3) 能否在场景中添加新物品 (Spawning)？
受限于 Unity 预制件和旧版库支持，直接“凭空硬捏”出一个原本不在内存里的全新资源难度比较高。但有一种极其常用和强大的“伪造/生形”方式：
利用 **`SetObjectPoses`** 动作，你可以将在这个屋子里但处于盲区（如某个抽屉里、或者远处角落中）的任意合法存在物品瞬间**传送/重置坐标**到你期望的地方（如主角面前的餐桌上）。

你可以参考我们编写的 `/mnt/disk1/decom/EmbodiedBench/teleport_object.py`，它成功地在控制器初始化阶段，将默认坐标系下的一个远方 `Tomato` 传送重置到了 Agent 就近的高光平台上：`{'x': -0.5, 'y': 0.95, 'z': -1.2}`。在正式测试任务初始化时追加此动作，你就能“仿佛创造了一个新物品”供大模型观察和交互。

## 6. 大模型与环境交互机制详解

### 6.1 动作空间 (Action Space)

EB-Navigation 使用固定的 **8个离散动作**，定义在 `EBNavEnv.py` 中：

```python
DISCRETE_SKILLSET = [
    0: "Move forward by 0.25",      # 前进0.25米
    1: "Move backward by 0.25",     # 后退0.25米
    2: "Move rightward by 0.25",    # 右移0.25米
    3: "Move leftward by 0.25",     # 左移0.25米
    4: "Rotate to the right by 90 degrees",  # 右转90度
    5: "Rotate to the left by 90 degrees",   # 左转90度
    6: "Tilt the camera upward by 30 degrees",  # 抬头30度
    7: "Tilt the camera downward by 30 degrees" # 低头30度
]
```

### 6.2 模型完整输入

大模型在每个时间步接收的完整输入结构如下：

```
┌─────────────────────────────────────────┐
│  System Prompt (任务规则说明)            │
│  ├─ 可用动作列表 (0-7)                  │
│  └─ N-shot 示例 (可选)                  │
├─────────────────────────────────────────┤
│  当前任务指令                            │
│  "navigate to the Kettle in the room"  │
├─────────────────────────────────────────┤
│  历史交互记录 (如有)                     │
│  Step 0, action 4, 右转90度, 成功       │
│  Step 1, action 0, 前进, 失败(撞墙)     │
├─────────────────────────────────────────┤
│  当前视觉观察                            │
│  [第一人称RGB图像 500x500像素]          │
└─────────────────────────────────────────┘
```

**关键特性:**
- 视觉输入: 第一人称视角的 RGB 图像，默认分辨率 500x500
- 可选多视角: `multiview=True` 时额外提供俯视图
- 可选多步历史: `multistep=True` 时提供最近3步的图像序列

### 6.3 模型输出格式

模型必须输出符合规范的 **JSON 格式**:

```json
{
  "visual_state_description": "我看到了一个厨房场景，前方有柜台...",
  "reasoning_and_reflection": "目标水壶应该在厨房区域，之前向右转没有看到，现在需要向左转探索",
  "language_plan": "1. 向左转90度  2. 向前走寻找水壶",
  "executable_plan": [
    {"action_id": 5},
    {"action_id": 0}
  ]
}
```

**字段说明:**
- `visual_state_description`: 对当前视觉场景的描述
- `reasoning_and_reflection`: 推理与反思（分析为何之前失败）
- `language_plan`: 自然语言形式的行动计划
- `executable_plan`: 可执行的动作ID序列（核心字段）

### 6.4 环境处理流程

当模型输出 JSON 后，环境执行以下流程：

```python
# 步骤1: 解析JSON提取动作ID
action_id = json_output['executable_plan'][0]['action_id']  # 例如: 5

# 步骤2: 映射为AI2-THOR底层指令
def discrete_action_mapper(action_index):
    if action_index == 0:
        env.step(action="MoveAhead", moveMagnitude=0.25)
    elif action_index == 4:
        env.step(action="RotateRight", degrees=90)
    elif action_index == 5:
        env.step(action="RotateLeft", degrees=90)
    # ... 其他动作映射

# 步骤3: Unity引擎重新渲染画面
new_frame = env.last_event.frame  # 获取渲染后的新视角

# 步骤4: 计算距离并判断成功
agent_position = env.last_event.metadata["agent"]["position"]
target_position = episode_data["target_position"]
distance = sqrt(
    (agent_x - target_x)² + (agent_z - target_z)²
)
success = (distance <= 1.0米)  # 成功阈值为1米

# 步骤5: 生成环境反馈文本
if action_success:
    feedback = f"Last action {action_name} executed successfully."
else:
    feedback = f"Last action {action_name} is invalid. {error_message}"

# 步骤6: 返回新的观察和反馈
return obs, reward, done, info
```

### 6.5 成功判定标准

- **距离阈值**: Agent 与目标物体的水平距离 ≤ 1.0 米
- **最大步数限制**: 20步
- **判定时机**: 每一步执行后都会检查距离

```python
# 核心代码位置: EBNavEnv.py:218-234
def measure_success(self):
    agent_position = self.env.last_event.metadata["agent"]["position"]
    target_position = self.episode_data["target_position"]
    
    dist = math.sqrt(
        (agent_position["x"] - target_position["x"])**2 +
        (agent_position["z"] - target_position["z"])**2
    )
    success = (dist <= SUCCESS_THRESHOLD)  # SUCCESS_THRESHOLD = 1
    return float(success), dist
```

### 6.6 关键代码位置

如需魔改，请关注以下文件:

| 功能模块 | 文件位置 | 关键行号 |
|---------|---------|---------|
| 动作空间定义 | `EBNavEnv.py` | 22-34 |
| Prompt 构造 | `nav_planner.py` | 92-136 |
| JSON 解析 | `vlm_planner.py` | 153-179 |
| 动作映射 | `EBNavEnv.py` | 179-217 |
| 成功判断 | `EBNavEnv.py` | 218-234 |
| 主循环 | `EBNavEnv.py` | 238-304 |
