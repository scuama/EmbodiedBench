# EB-Manipulation 连续控制臂环境全解析

## 1. 原理与特殊性分析

根据审查 `embench_man` 的源码 `EBManEnv.py` 与运行依赖构建过程，我们发现 `EB-Manipulation` 是三个库中唯一一个依赖**离线物理图形渲染 (PyRep & RLBench)** 和底端 **Continuous Action Spaces (连续控制)** 的平台。

虽然顶层依然接受语言模型的反馈，但是其评估逻辑并非像 Navigation 的“键盘前后左右”，或者 Habitat 的“指定行为ID”。在 Manipulation 中，系统先提供**带 3D 边界框标注 (Bounding Boxes)** 覆盖的可视化图片给模型（包含其长宽高的六边形坐标）。模型通过这些视觉线索，推算输出空间规划阵列，环境收到后负责利用**运动学反解 (Inverse Kinematics)** 操纵一条带有 7 个自由度的真实工业机器手臂。每一次移动如果偏离目标或者撞到物体发生干涉就会在 RLBench 层进行物理惩罚甚至失败退出。
这解释了为什么我们要放弃对它的基线数据进行“粗暴替换”——因为其后端是一个高度复杂的 `.ttm` （V-REP 场景体）+ `.pkl`（动作回放坐标记录），不适合做字符串层的 JSON 涂抹。

## 2. 评测执行与图像日志观测
在解决依赖了它专有的运行环境并修复了传参的 bug 后，我们顺利通过命令仅执行第一关进行了评测：
```bash
conda activate embench_man
xvfb-run -a conda run -n embench_man python -m embodiedbench.main env=eb-man model_name=gpt-4o-mini ++eval_sets="[base]" ++selected_indexes="[0]"
```

本回合 `episode_0` (对应输出第一关 `episode_1`) 的指令为：
**Instruction: Pick up the star and place it into the silver container.** (拾取星星放入银色容器)

**Step 0：出生抓拍 (带有中心点及包围盒注释以输送给大模型进行空间定位算力)**
![man_step_0](./man_step_0.png)

通过 `running/eb_manipulation/` 下截取的模型输出日志可以看到，GPT-4o-mini 不断尝试推断了由 7 维构成 (`[x,y,z,quatx,quaty,quatz,gripper]`) 的操作路径点，尝试抓取星星。这通常极困难。不过由于是仿真，执行 15 步抓动作后，关卡强制停止。

**Step 15：最后时刻的镜头 (机械臂移动到了附近)**
![man_step_15](./man_step_15.png)

## 3. 总体结论

我们已经完全梳理清了三个 EmbodiedBench 环境的能力边界与底层支持。总结如下：
* **EB-Navigation (AI2-THOR)**：最容易二次开发和挂钩修改 JSON 测试集的游乐场；支持随时随地添加替换模型和预制件。
* **EB-Habitat (Facebook Habitat)**：性能怪兽，考验大模型面对成百上千离散字典时的多步规划检索，但对原数据的格式修改不友好，推荐纯做宏观测试。
* **EB-Manipulation (PyRep+RLBench)**：纯机器人学术训练场，包含复杂的正逆运算与力学反馈。极其吃资源，运行需要特定的 X11 Headless（无头配置） 和严格的依赖隔离版本。

## 4. 大模型与环境交互机制详解

### 4.1 动作空间 (Action Space)

EB-Manipulation 是三个环境中唯一使用 **连续动作空间 (Continuous Action Space)** 的环境。实际交互时采用 **7维控制向量**:

```python
action = [
    x, y, z,                    # 末端执行器的位置坐标 (米)
    quat_x, quat_y, quat_z,    # 四元数旋转表示 (姿态)
    gripper                     # 夹爪状态: 0.0=张开, 1.0=闭合
]
```

**特殊机制:** 虽然底层是连续控制，但对外接口支持离散动作标签（如 "grasp", "lift", "place_left"），通过 `get_continous_action_from_discrete()` 函数转换。

### 4.2 模型完整输入

```
┌─────────────────────────────────────────┐
│  多视角图像输入 (5个相机视角)            │
│  ├─ front_rgb (正视图)                  │
│  ├─ left_shoulder_rgb (左肩视角)        │
│  ├─ right_shoulder_rgb (右肩视角)       │
│  ├─ wrist_rgb (腕部视角)                │
│  └─ overhead_rgb (俯视图)               │
├─────────────────────────────────────────┤
│  3D 边界框标注 (Bounding Box)           │
│  ├─ 目标物体的 3D 坐标                  │
│  └─ 包围盒的长宽高 (六边形坐标)         │
├─────────────────────────────────────────┤
│  任务指令                                │
│  "Pick up the star and place it into    │
│   the silver container"                 │
└─────────────────────────────────────────┘
```

**关键特性:**
- 视觉输入包含 5 个不同视角，帮助模型理解 3D 空间关系
- 图像默认分辨率 500x500
- 提供 3D 边界框标注，直接告知目标物体的空间位置

### 4.3 模型输出格式

模型需要输出 **离散动作标签** 或 **连续控制参数**:

**方式1: 离散动作标签**
```json
{
  "action_description": "Move end-effector to grasp position",
  "discrete_action": "grasp",
  "continuous_params": {
    "x": 0.32, "y": 1.14, "z": 0.50,
    "quat_x": 0.0, "quat_y": 1.0, "quat_z": 0.0,
    "gripper": 1.0
  }
}
```

**方式2: 连续参数直接输出**
```json
{
  "executable_plan": [
    {
      "action_id": 0,
      "x": 0.32, "y": 1.14, "z": 0.50,
      "quat_x": 0.0, "quat_y": 1.0, "quat_z": 0.0,
      "gripper": 1.0
    }
  ]
}
```

### 4.4 环境处理流程

```python
# 步骤1: 动作转换 (离散 → 连续)
action_continuous = get_continous_action_from_discrete(discrete_action)

# 步骤2: 调用 PyRep 物理引擎
obs, reward, terminate = self.task.step(action_continuous)

# 步骤3: 运动学逆解 (Inverse Kinematics)
# → 根据 (x, y, z, quat) 计算机械臂 7 个关节的角度
# → 驱动仿真器中的虚拟机器人运动

# 步骤4: 物理碰撞检测
if collision_detected or out_of_workspace:
    reward = -1
    terminate = False
    raise ConfigurationPathError

# 步骤5: 任务特定成功判断 (以堆叠任务为例)
if task_type == 'stack_cubes_color':
    if terminate and action[-1] == 1.0:  # 夹爪闭合
        # 检查是否正确堆叠
        action[2] += 0.03  # 微调高度
        obs, reward, terminate = self.task.step(action)
        if reward == 1.0:
            logger.info("堆叠成功!")
            reward = 1.0
            terminate = True
        else:
            reward = 0.0
            terminate = False

# 步骤6: 生成环境反馈
env_feedback = f"You are currently performing the task intended to {instruction}. "
env_feedback += f"At this moment, you have completed {step} steps. "
if action_success:
    env_feedback += f"Last action is valid. "
else:
    env_feedback += f"Last action is invalid. {error}"
env_feedback += f"The current reward obtained is {reward}."
```

### 4.5 成功判定标准

**堆叠任务 (stack_cubes_color):**
- 物体A必须放置在物体B的正上方
- 物体不能掉落
- 夹爪必须正确释放

**抓取任务 (pick_cube_shape):**
- 成功抓取目标物体
- 物体不能掉落

**放置任务 (place_into_shape_sorter_color):**
- 物体正确放入容器中
- 位置准确

**擦拭任务 (wipe_table_direction):**
- 沿指定方向擦拭桌面
- 覆盖率达到要求

**最大步数限制:** 15步

### 4.6 关键代码位置

| 功能模块 | 文件位置 | 关键行号 |
|---------|---------|---------|
| 动作空间定义 | `EBManEnv.py` | 76-77 |
| 连续动作转换 | `eb_man_utils.py` | `get_continous_action_from_discrete()` |
| 任务加载 | `EBManEnv.py` | 159-165 |
| 动作执行 | `EBManEnv.py` | 167-218 |
| 成功判断 | `EBManEnv.py` | 174-193 |
| 反馈生成 | `EBManEnv.py` | 237-252 |

### 4.7 与其他环境的差异

| 维度 | Navigation | Manipulation | Habitat |
|------|-----------|--------------|---------|
| **控制类型** | 离散 (8个) | 连续 (7维) | 离散宏动作 (~70个) |
| **自动化程度** | ❌ 全手动 | ⚠️ 半自动 (逆运动学自动) | ✅ 高度自动 |
| **技能要求** | 空间感知 | 运动规划 + 力学理解 | 任务分解 |
| **难度** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **可解释性** | 高 | 低 (黑盒运动学) | 中 |

## 5. 场景修改实战与流程 (Custom Scene Integration)

EB-Manipulation 的核心场景是由 CoppeliaSim 构建的。所以如果需要向评测集中加入自定义的场景并运行大模型，不能通过修改代码或 JSON，必须通过操纵底层模型文件实现。

### 5.1 修改与替换流程

如果要针对某个关卡 (如 `pick_cube_shape` 的 `variation0`) 修改物品位置或新增模型，需要执行以下完整流程：

**第一步：客户端模型修改 (Mac / Windows)**
1. 下载原本的 `task_base.ttm` (位于 `data/base/eval/[task_name]/[variation]/episodes/episode0/`)。
2. 安装并打开 **CoppeliaSim V4.1.0** (这是非常关键的版本限制，因为更高版本 V4.6+ 保存的格式在服务器服务端无头模拟器中无法读取)。
3. 在可视化图形界面中移动物品坐标，调整模型后将其另存为 `modified.ttm`。

**第二步：服务器端环境构建**
在服务器端的场景路径 (如 `data/custom/eval/[task_name]/[variation]/episodes/episode0/`) 构建新数据：
1. 将 `modified.ttm` 重命名为 `task_base.ttm` 放入目录下。
2. 完整的一局游戏还需要 `waypoint_sets.ttm` 和 `configs.pkl`。如果只是修改模型位置，可以直接从旧的 `base` 目录将这两个文件拷贝过来。

**第三步：注册自定义评测集**
在 `/mnt/disk1/decom/EmbodiedBench/embodiedbench/envs/eb_manipulation/EBManEnv.py` 中:
1. 在 `ValidEvalSets` 列表中追加字符串 `'custom'`。
2. 在 `EVAL_SETS` 字典中追加 `'custom': EVAL_SETS['base']` 或者指定专属的评测用例映射。

**第四步：挂载运行测试**
```bash
conda activate embench_man
xvfb-run -a conda run -n embench_man python -m embodiedbench.main \
  env=eb-man model_name=gpt-4o-mini \
  ++eval_sets="[custom]" ++selected_indexes="[0]"
```
系统将会启动含有修改过物品的 3D 环境进行评测。
