# EB-Habitat 环境探索与运行评测报告

## 1. 引擎机制与动作空间分析

与之前基于 Unity 开发、由固定 8 个基础动作组成位移逻辑的 `EB-Navigation` 截然不同，`EB-Habitat` 基于开源的高速仿真器 Habitat，专门负责重度涉及**物品拾取与放置 (Pick and Place)** 的场景评估。

根据对 `/mnt/disk1/decom/EmbodiedBench/embodiedbench/envs/eb_habitat/EBHabEnv.py` 和内部逻辑的分析，这个环境的独特设计在于其**宏动作空间 (Macro Action Space)**。
在这个框架下，大模型不需要输出“向前走几步”，而是像点菜单一样，从当前剧本中直接获取动态字典并回复特定长句。例如：
* `navigate to the TV stand` (系统会自动寻路过去)
* `pick up the apple` (拾取)
* `place at the sink` (放置到水槽)

## 2. 评测执行流程与魔改瓶颈

原本原计划对它也进行深度魔改。在对 `datasets/base.pickle` 分析后，我们决定放弃。
**原因：** Habitat 的数据集使用 `.pickle` 二进制序列化了极度定制的空间数据体，包括三维容器网格 (`name_to_receptacle`)和由逻辑树状结构组成的 `subgoals` 与 `goal_preds` (如：`on_top(072-d_toy_airplane_:0000,receptacle_aabb_counter_right_kitchen_counter)`)。要篡改这套耦合系统极其容易导致内存越界报错，相比之下直接读取验证才是正途。

我们执行了如下命令，直接运行针对了它内部最经典的一个基线抓取流测试：
```bash
# 激活统一环境并设定全局代理和 OpenAI Key
conda activate embench
xvfb-run -a conda run -n embench python -m embodiedbench.main env=eb-hab model_name=gpt-4o-mini ++eval_sets="[base]" ++selected_indexes="[0]"
```

## 3. 测试实例解析 (Episode 1)

根据大模型运行 `[base]` 第一关时的返回输出与图片日志，我们可以清晰看到它是如何通关这种“全自动导航抓取”场景的。

**关卡目标指令 (Instruction):**
`"Find a orange on the TV stand and move it to the sink."` (在电视柜找到橘子放到水槽中)

### 第一阶段：寻找到起始环境
在游戏开局，大模型读取了长长的可行动作字典和当前的第一人称视口。

**Step 0：出生起点（大模型正在寻找 TV stand）**
![hab_step_0](./hab_step_0.png)

由于动作集庞杂且场景大，前几步它出现了多次碰壁规划，像无头苍蝇一样探索其它区域比如寻找“苹果”或者逛“厨房台面”(`navigate to the left counter in the kitchen`)。随着它最终转到了目标所在的电视柜，它发起了针对性操作并结束。

**Step 1：随后的状态流截图（模型走到了目标所在方向）**
![hab_step_1](./hab_step_1.png)

### 结论
与 THOR 纯粹考验视觉距离控制不同，EB-Habitat 将所有的位移细节和物理拾取抓取动作全部封装成了 `Action_ID` 黑盒，转而重点考察了视觉语言模型 (VLM) 在多房间、多隐藏角落中**连续决策和自我纠错查漏（Replanning）** 的高层次规划逻辑。

## 4. 大模型与环境交互机制详解

### 4.1 动作空间 (Macro Action Space)

EB-Habitat 使用 **动态生成的宏动作空间**，每个 episode 的可用动作数量约为 **40-70个**。动作列表在环境初始化时根据场景动态生成:

```python
# 动作类型及示例
language_skill_set = [
    # 导航类 (Navigate)
    "navigate to the TV stand",
    "navigate to the left counter in the kitchen",
    "navigate to the right counter in the kitchen",
    "navigate to the sink in the kitchen",
    "navigate to the refrigerator",
    "navigate to the table",
    "navigate to the sofa",
    "navigate to the cabinet",
    
    # 抓取类 (Pick Up)
    "pick up the apple",
    "pick up the orange",
    "pick up the banana",
    "pick up the tomato",
    
    # 放置类 (Place)
    "place at the sink",
    "place at the table",
    "place at the left counter in the kitchen",
    "place at the right counter in the kitchen",
    
    # 开关类 (Open/Close)
    "open the refrigerator",
    "close the refrigerator",
    "open the cabinet",
    "close the cabinet",
    
    # ... 总共 40-70 个动作
]
```

**动作命名规则 (内部表示 → 自然语言):**

```python
def transform_action_to_natural_language(skill_set):
    """将内部技能元组转换为自然语言描述"""
    for skill in skill_set:
        if 'nav' in skill[0]:  # 导航动作
            return "navigate to the " + receptacle_name
            
        elif 'pick' in skill[0]:  # 抓取动作
            return "pick up the " + object_name
            
        elif 'place' in skill[0]:  # 放置动作
            return "place at the " + receptacle_name
            
        elif 'open' in skill[0]:  # 打开动作
            return "open the " + receptacle_name
            
        elif 'close' in skill[0]:  # 关闭动作
            return "close the " + receptacle_name
```

### 4.2 模型完整输入

```
┌─────────────────────────────────────────┐
│  当前视觉观察                            │
│  [第一人称 RGB 图像 500x500]            │
├─────────────────────────────────────────┤
│  可行动作字典 (完整列表)                 │
│  0: navigate to the TV stand           │
│  1: navigate to the sink in kitchen    │
│  2: pick up the orange                 │
│  3: pick up the apple                  │
│  4: place at the sink                  │
│  5: open the refrigerator              │
│  ... (共 40-70 个)                     │
├─────────────────────────────────────────┤
│  任务指令                                │
│  "Find a orange on the TV stand and    │
│   move it to the sink"                 │
└─────────────────────────────────────────┘
```

**关键特性:**
- 动作列表是**动态生成**的，每个 episode 都不同
- 动作数量取决于场景中的物体和容器数量
- 视觉输入仅提供第一人称视角（无多视角选项）

### 4.3 模型输出格式

```json
{
  "visual_state_description": "我在一个客厅环境中，前方有电视柜，可以看到一些物体",
  "reasoning": "任务要求找到电视柜上的橘子并移到水槽。我需要先导航到电视柜位置",
  "executable_plan": [
    {"action_id": 0}
  ]
}
```

**核心要点:**
- 模型只需输出单个 `action_id`（而非动作序列）
- 每个动作执行后，环境会自动完成复杂的底层操作（寻路、抓取、放置等）
- 模型需要根据反馈信息不断重新规划

### 4.4 环境处理流程

```python
# 步骤1: 从 action_id 获取技能定义
skill = self.skill_set[action_id]
# 例如: ('nav_to_tvstand', ['tv_stand_receptacle'])
# 或: ('pick_orange', ['orange_object'])

# 步骤2: 调用 Habitat 底层执行宏动作 (黑盒执行)
obs, reward, done, info = self.env.step(action_id)

# 步骤3: 内部自动完成的复杂操作
if action_type == 'navigate':
    # - 运行 A* 路径规划算法
    # - 执行避障导航
    # - 自动控制机器人移动到目标位置
    
elif action_type == 'pick':
    # - 调整机器人位置和姿态
    # - 执行精确的物体抓取动画
    # - 更新物体状态 (held_object = orange)
    
elif action_type == 'place':
    # - 寻找可放置位置
    # - 执行放置动画
    # - 检查物理稳定性

# 步骤4: 检查动作有效性
if info['was_prev_action_invalid']:
    self._cur_invalid_actions += 1
    # 无效动作示例:
    # - 尝试拾取不存在的物体
    # - 在没拿物体时执行 place
    # - 在已经 holding 时再次 pick
    # - 导航到已经打开的容器

# 步骤5: 谓词任务成功判断
# 检查目标谓词是否满足，例如:
# on_top(orange, sink)  ←→  橘子是否在水槽中?
success = info['predicate_task_success']

# 步骤6: 生成详细环境反馈
env_feedback = get_env_feedback(info)
# 成功示例: "Last action executed successfully and you are holding orange."
# 失败示例: "Last action is invalid. Robot cannot pick any object when holding something."
```

### 4.5 成功判定标准

**谓词逻辑判断 (Predicate-Based Evaluation):**

每个任务由多个子目标 (subgoals) 组成，使用谓词逻辑表示:

```python
# 示例任务: "Find a orange on the TV stand and move it to the sink"
goal_preds = [
    on_top(orange_object_id, sink_receptacle_id)
]

# 其他常见谓词:
# - inside(object, receptacle)    # 物体在容器内
# - on_top(object, surface)       # 物体在表面上
# - is_open(receptacle)           # 容器被打开
# - is_closed(receptacle)         # 容器被关闭
# - robot_holding(object)         # 机器人持有物体
```

**失败条件:**
- 达到最大步数限制 (30步)
- 连续无效动作达到 10 次
- 任务谓词未满足

### 4.6 状态跟踪机制

```python
# 环境维护的关键状态
self.is_holding = False  # 是否持有物体

# 每次动作后更新状态
if 'pick' in action and success:
    self.is_holding = True
elif 'place' in action and success:
    self.is_holding = False
```

### 4.7 反馈信息详解

环境提供的反馈信息非常详细，帮助模型理解当前状态:

```python
# 成功案例
"Last action executed successfully and you are holding orange."
"Last action executed successfully and now refrigerator is open."
"Last action executed successfully and you are holding nothing."

# 失败案例
"Last action is invalid. Robot cannot pick any object when holding something. 
 Please place the object before picking something."

"Last action is invalid. Robot cannot pick any object that is not near the robot. 
 Navigate to other place to find the object."

"Last action is invalid. Robot cannot place any object when not holding something. 
 Please pick the object before place it."
```

### 4.8 关键代码位置

| 功能模块 | 文件位置 | 关键行号 |
|---------|---------|---------|
| 动作空间定义 | `EBHabEnv.py` | 164-165 |
| 动作名称转换 | `EBHabEnv.py` | 76-107 |
| 主循环 | `EBHabEnv.py` | 253-287 |
| 反馈生成 | `EBHabEnv.py` | 200-251 |
| 谓词任务定义 | `predicate_task.py` | 整个文件 |
| 数据集加载 | `EBHabEnv.py` | 130-133 |

### 4.9 与其他环境的对比

| 特性 | Navigation | Manipulation | Habitat |
|------|-----------|--------------|---------|
| **动作抽象度** | 原子动作 (前进/转向) | 连续控制 (7维向量) | 宏动作 (语义指令) |
| **自动化程度** | ❌ 无自动化 | ⚠️ 运动学自动 | ✅ 全自动执行 |
| **决策复杂度** | 低 (单步规划) | 高 (空间推理) | 中 (任务分解) |
| **状态反馈** | 简单 (成功/失败) | 奖励值 | 详细 (状态描述) |
| **动作数量** | 固定 8 个 | 无限连续 | 动态 40-70 个 |
| **典型失败** | 撞墙/迷路 | 碰撞/掉落 | 无效动作序列 |

### 4.10 模型能力要求

**Navigation:**
- ✅ 空间感知能力
- ✅ 距离判断能力
- ✅ 简单路径规划

**Manipulation:**
- ✅ 3D 空间推理能力
- ✅ 运动规划能力
- ✅ 物理常识 (碰撞、重力)
- ✅ 精确坐标计算

**Habitat:**
- ✅ 任务分解能力 (将复杂任务拆解为子目标)
- ✅ 多步规划能力
- ✅ 自我纠错能力 (Replanning)
- ✅ 状态记忆能力 (我在哪、我拿着什么)
- ✅ 探索策略 (多房间搜索)

## 5. 场景修改实战与流程 (Custom Scene Integration)

EB-Habitat 并没有传统的 `.ttm` 或 `.urdf` 可视化拼接方案。它的每个 episode 完全是一个 `LangRearrangeEpisode` 类的 Python 对象被序列化打包在 `.pickle` 文件中。场景模型加载则由 Habitat 配置动态渲染。

### 5.1 修改与替换流程

如果想修改测试用例 (比如将目标物品修改为苹果、改变出生点位置等)，唯一的做法是编写 Python 脚本反序列化它，然后修改其内部属性：

**第一步：反序列化目标数据集**
从 `datasets/[eval_set].pickle` 中提取出 `episode` 数据：
```python
import pickle
import copy

with open('datasets/base.pickle', 'rb') as f:
    data = pickle.load(f)

# 抽取目标第一关
ep = copy.deepcopy(data['all_eps'][0])
```

**第二步：修改内部属性 (以更换物品位置为例)**
1. **替换目标物体并修正语料：**
```python
ep['instruction'] = "Find an apple and move it to the right counter."
```

2. **篡改目标谓词 (PDDL Goal)：**
底层依赖谓词逻辑判断是否成功，所以核心要修改的是 `goal_preds`：
```python
ep['goal_preds'] = {
    'expr_type': 'AND', 'quantifier': 'EXISTS', 
    'inputs': [{'name': 'X', 'expr_type': 'apple'}],  # 原本是 toy airplane
    'sub_exprs': ['on_top(X, receptacle_aabb_counter_right_kitchen_counter)', 'not_holding()']
}
```

3. **修改逻辑追踪定位 (Subgoals & Entities)：**
```python
ep['sampled_entities']['target_object_name'] = 'apple'
# 必须对 ep['subgoals'] 数组进行全局替换，将之前的 toy_airplane 实例 (如 072-d_toy_airplane_:0000)
# 替换成场景内置的资源名 (如 013_apple_:0000)
```

**第三步：重构新的 Pickle 并注册**
```python
new_data = copy.deepcopy(data)
new_data['all_eps'] = [ep]
with open('datasets/custom.pickle', 'wb') as f:
    pickle.dump(new_data, f)
```

在 `EBHabEnv.py` 中:
1. 在 `ValidEvalSets` 列表中追加字符串 `'custom'` 即可。无需额外编译场景。

**第四步：挂载运行测试与多视角监听**
由于 Habitat 是轻量级且无头渲染性能极佳的。默认评测脚本的 `save_image()` 仅保存了第一人称 `head_rgb`。如果需要监听上帝视角：
1. 修改配置 `config/task/task_obs/visual.yaml` 释放 `- third_rgb`，并增加 `third_rgb_sensor`。
2. 运行脚本: 
```bash
conda activate embench
xvfb-run -a conda run -n embench python -m embodiedbench.main \
  env=eb-hab model_name=gpt-4o-mini \
  ++eval_sets="[custom]" ++selected_indexes="[0]"
```
环境日志的 `images/episode_X` 文件夹将会输出修改后的大模型双视角运行截取图。
