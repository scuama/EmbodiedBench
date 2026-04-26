# EmbodiedBench 快速上手指南

本指南涵盖目前已跑通的 3 个环境：`EB-Habitat`、`EB-Manipulation` 和 `EB-Navigation`，提供最核心的运行与配置说明。

## 1. 启动实验

确保您在系统终端中已激活 `embench` 环境，并配置好所需大模型的 API 密钥（如 OpenAI）。

**通用启动命令格式：**
```bash
# 由于存在不兼容的底层仿真库版本要求，各环境具有独立的 conda 依赖环境！
# Habitat 和 Alfred: conda activate embench
# EB-Navigation: conda activate embench_nav
# EB-Manipulation: conda activate embench_man

# 启动环境评测 (修改 env= 对应的环境名称)
python -m embodiedbench.main env=[环境名称] model_name=[模型名称] ++eval_sets="[base]" ++selected_indexes="[0,1]"
```

**各环境具体运行示例：**
> ⚠️ **避坑指南**：切勿在单一的 `embench` 下运行所有测试！由于 `ai2thor` 引擎版本冲突 (如 2.1.0 与 3.3.5 之争)，请务必激活每个任务专属的 conda 环境。

* **EB-Habitat** (视觉导航与推理):
  `(embench)$ python -m embodiedbench.main env=eb-hab model_name=gpt-4o-mini ++eval_sets="[base]" ++selected_indexes="[0,1]"`
* **EB-Manipulation** (机械臂操作):
  `(embench_man)$ python -m embodiedbench.main env=eb-man model_name=gpt-4o-mini ++eval_sets="[base]" ++selected_indexes="[0,1]"`
* **EB-Navigation** (AI2-THOR 物体寻路):
  `(embench_nav)$ python -m embodiedbench.main env=eb-nav model_name=gpt-4o-mini ++eval_sets="[base]" ++selected_indexes="[0,1]"`

### 启动参数详细说明

在运行上述命令时，您可以通过修改后面追加的 `[参数名]=[值]` 来变更实验流程。以下是核心参数的解释：

* **`env=`** : 必填参数。决定使用哪个底层仿真环境 (`eb-hab`, `eb-man`, `eb-nav`)。不建议使用已废弃的 `eb-alf`。
* **`model_name=`** : 必填参数。设定接入用于充当 agent 大脑的基础模型名称 (如 `gpt-4o-mini`)。
* **`++eval_sets="[集合名]"`** : 指定要测试的数据集划分，通常留 `"[base]"` 即可。
* **`++selected_indexes="[... , ...]"`** : 测试子集抽样。**极为重要！** 用于 Debug 或快速体验。例如 `"[0,1]"` 表示只抓取题库里的第 0 个和第 1 个任务跑。如果不加这参数必将漫长地耗尽整个库。

## 2. 查看结果与可视化

所有评估结果和图片均会保存在项目根目录底下的 `running/` 文件夹内，按 `环境/模型/评估集` 进行归档分类。

* **EB-Habitat**: 图片存放在 `running/eb_habitat/.../base/images/`，含每一步移动和全景视觉。
* **EB-Manipulation**: 存放在 `running/eb_manipulation/.../base/images/`，含前置/侧置多机位摄像头追踪。
* **EB-Navigation**: 存放在 `running/eb_nav/.../base/`，直接记录每一步决策的交互动作拼接图。

---

## 3. 深入环境内核：场景定义、大模型交互与魔改指南

这三个环境引擎大相径庭。在这里，针对每一个环境深挖：**一个任务任务（Episode）究竟是如何定义的、大模型是如何看到并执行交互的、以及如何在无显示器的 Linux 服务器下魔改（二次开发）它**。

---

### 🟢 3.1 EB-Navigation (基于 AI2-THOR - 室内探索拾取)

**🔧 环境原理与交互链路 (I/O) 怎么转化的？**
AI2-THOR 是一款由 Unity 构建的拟真 3D 游戏环境。
- **大模型的输入 (看与听)**：引擎通过 Python API 截取当前机器人的第一人称 RGB 截图，并附上任务指令和候选动作列表喂给大模型。
- **大模型的输出与执行 (想与动)**：大模型**不可输出三维坐标**，而是必须从列表（如 *0: 向前走*, *1: 向左转*, *3: 打开抽屉*）中以 JSON 格式输出推理和唯一的 `action_id`。
  底层 Python 脚本 `VLMPlanner` (`embodiedbench/planner/vlm_planner.py`) 拿到该 ID 后，立刻转为 Unity 的 HTTP API (如发送 `OpenObject` 短句)。Unity 引擎接旨后，内部计算抽屉铰链动画并触发物理碰撞改变。

**📄 场景数据长什么样？ (真实测验切片剖析)**
AI2-THOR 的所有题目完全是由**纯文本 JSON 字典**定义的。
- **题目文件位置**: `/mnt/disk1/decom/EmbodiedBench/embodiedbench/envs/eb_navigation/datasets/base.json` 等。
- **底层案例切片** (抽取自 `base.json` 的第 0 题):
  ```json
  {
      "scene": "FloorPlan11",
      "targetObjectType": "Bread",
      "instruction": "navigate to the Bread in the room and be as close as possible to it",
      "agentPose": { "position": { "x": -1.5, "y": 0.9, "z": -0.9 }, "rotation": 90.0 }
  }
  ```
  在这里，`"scene": "FloorPlan11"` 直接召唤了 Unity 内置封装好的第 11 套房间模型，机器人将在指定的 `agentPose` 三维坐标出生，它的任务就是听从 `"instruction"` 在三维空间里找到 `"Bread"` (面包)。

**🚀 魔改指南 (本服务器下难度：极易)**
因为它是纯声明式的 JSON，在目前的无图形化命令行环境中操作门槛最低。
- **换房子/换任务**：直接使用文本编辑器 (`vim` / `nano`) 打开上述 JSON，把 `"scene"` 换个数字编号（如 `"FloorPlan22"` 等于瞬移到全新户型），并自由改写 `"instruction"`。
- **在屋里新添物品**：它会在加载房间后依据常识算法在桌面上“自动散货”。只要在类表 `/mnt/disk1/decom/EmbodiedBench/embodiedbench/envs/eb_alfred/gen/constants.py` 的可交互物品集 `OBJECTS` 中注册新物品名字，不用给三维坐标，环境初始化时会自动把它合理地随机撒进房间里。

---

### 🟢 3.2 EB-Habitat (基于 AI Habitat - 视觉导航与放置)

**🔧 环境原理与交互链路 (I/O) 怎么转化的？**
Habitat 是 Facebook 开源的极度注重渲染并发速度的三维物理流体引擎。
- **交互逻辑**：大模型同样是被喂一张 2D RGB 图和提示词，并返回动作 ID（比如编号 1 代表“左转”）。但这里的底层 C++ 引擎不用发 HTTP 请求，而是直接在显存层极度暴力地把装有虚拟摄像头的物理胶囊体旋转角度，实时宣染下一帧。

**📄 场景数据长什么样？ (真实测验切片剖析)**
与 THOR 的文本定义不同，Habitat 所有任务都在生成后被**死锁打包在了二进制档案中**。
- **题目文件位置**: `/mnt/disk1/decom/EmbodiedBench/embodiedbench/envs/eb_habitat/datasets/base.pickle` 等。
- **底层案例剖析**: 您不能直接用文本打开它。这是一个庞大的 Python `pickle` 序列化对象，里面封装了所有的考题。它内部利用键值强行绑定了来自 `data/replica_cad/` 的第三方重重扫描好的真实房间点云模型。参数方向定义于：`/mnt/disk1/decom/EmbodiedBench/embodiedbench/envs/eb_habitat/config/task/dataset_v1.yaml`。

**🚀 魔改指南 (本服务器下难度：中等 - 全靠代码)**
由于 `.pickle` 黑盒特性，普通的编辑器文本修改是行不通的。必须依赖代码：
- **生成脚本介入**：作者预留了数据生成的宏大管道源码——`/mnt/disk1/decom/EmbodiedBench/embodiedbench/envs/eb_habitat/dataset/create_episodes.py` (`RearrangeEpisodeGenerator`)。
- **如何操作**：您不需要显卡界面，但您需要重写这个 Python 脚本，用代码循环组装全新房屋的点云并指定物体，在终端多进程并发运算，最终导出一批专属于您的全新 `.pickle` 去覆盖掉 `datasets/` 目录里的源文件。

---

### 🟢 3.3 EB-Manipulation (基于 CoppeliaSim - 机械臂抓取任务)

**🔧 环境原理与交互链路 (I/O) 怎么转化的？**
这涉及操作桌面极度精细的重型机械臂（如搭载夹爪的 UR5 / Franka）。
- **交互逻辑**：这也是体现框架自动魔法。当大模型看见桌上有红色方块，并按照要求在 JSON 中输出 “抓取红方块” 对应的那个 `action_id` 时，它无需计算这 6 个关节该各自旋转多少度！底层 `CoppeliaSim (V-REP)` 的正逆运动学(IK)控制引擎会在其内部自动查探该方块的绝对坐标，并规划一条最平滑的接近与钳下落轨迹去完成所有的物理脏活。

**📄 场景数据长什么样？ (真实测验切片剖析)**
惊人的是，这个环境里**根本没有配置文件代码！所有的桌子和物品都是真实的 3D 渲染截面！**
- **题目位置**: 每一道题就是一个超级庞大的三维系统夹缩，比如第一道题藏于：
  `/mnt/disk1/decom/EmbodiedBench/embodiedbench/envs/eb_manipulation/data/base/eval/pick_cube_shape/variation0/episodes/episode0/`
- **底层案例剖析**: 点开这道题的最终目录，纯粹只有三样死物：
  1. `task_base.ttm` (场景网格：整个桌子此刻的物理空间 3D 存档大面模型)
  2. `waypoint_sets.ttm` (专家轨迹：包含机械臂拿满分的标准高玩运动示范，用于算分)
  3. `configs.pkl` (题头字典：包含 `"instruction"` 诸如“抓起方块”此类的文字描述题干)。

**🚀 环境魔改指南 (本无显服务器下难度：地狱 - 极易炸膛)**
在这个没有桌面图标纯打代码的 Linux 终端服务器中，给桌上加一个干扰苹果**极其危险**！
- 如果仅用代码：您必须去 `EBManEnv.py` 中写 PyRep 高级 `spawn` 的加载语句，像瞎子一样凭空蒙出 `[0.2, 0.45, z_height]` 的 XYZ 坐标。且不说没画面很难对齐网格坐标中心，只要坐标偏了 1 厘米塞进了桌子的内部，一启动测试刚体穿模弹射，引擎当场崩溃。
- **脱机化正统工业操作（强烈推荐）**：
  不要在无显服务器上硬写代码！将服务器里要题目的那个原始 `task_base.ttm` 文件传输下载回您个人的本地笔记本电脑上。在本地安装免费版 **CoppeliaSim (V-REP)**。用本地 3D 软件和鼠标，可视化地把你带的手办或者模型文件（如 `.obj/json`）拖动摆在桌子上不穿插的安全位置，点左上角“保存”。再用 `scp` 把这个精装修的新 `.ttm` 覆盖回 Linux 服务器内。从此测试，机器人面对的就是那间新的桌子。

---

## 4. 大模型的“真题试卷”与“操作面板”：Prompt 与 Action 深度解密

您一定很好奇我们到底对大模型说了怎样的咒语？而且那些所谓的“可选操作 ID”究竟有哪些？不同环境的提示词和动作面板结构**天差地别**，源代码存在于 `embodiedbench/evaluator/config/system_prompts.py` 中。

以下是三个环境喂给 GPT 的核心灵魂框架：

### 📝 试卷 1：EB-Navigation 的提示词与宏动作 (静态字典)
大模型收到的是一份**规则固定的 8 向盘操作指令**：
```markdown
## You are a robot operating in a home...
## The available action id (0 ~ 7) and action names are:
action id 0: Move forward by 0.25, 
action id 1: Move backward by 0.25, 
action id 2: Move rightward by 0.25, 
action id 3: Move leftward by 0.25,
action id 4: Rotate to the right by 90 degrees.,
action id 5: Rotate to the left by 90 degrees.,
action id 6: Tilt the camera upward by 30 degrees.,
action id 7: Tilt the camera downward by 30 degrees.

*** Strategy ***
1. Locate the Target Object Type: Clearly describe...
2. Navigate by Using Move forward and Move right/left as main strategy...
(紧接着附带环境生成的当前帧照片 Base64 代码...)
```
**解析**：Navigation 每一步都在考方向盘定点操作，没有提供拿取物品的选项，走近目标即算作过关。

### 📝 试卷 2：EB-Habitat 的提示词与宏动作 (动态字典)
与 THOR 的定死 8 个动作不同，Habitat 的试卷是**按每一关房间里的物体动态生成选项的**：
```markdown
## You are a robot operating in a home...
## Action Descriptions and Validity Rules
- Pick: Parameterized by the name of the object to pick...
- Place: Parameterized by the name of the receptacle to place...

## The available action id (0 ~ N) and action names are:
action id 0: navigate to the sofa,
action id 1: navigate to the tv stand,
action id 2: pick up the cushion,
action id 3: open the cabinet_1...
(跟随照片喂给大模型)
```
**解析**：Habitat 的宏动作极其高级。只需选 `action id 0` 大模型就会瞬间在屋子里找到沙发走过去，不必自己算朝前走几步。大模型就是个点菜单的食客，底层 C++ 包办了一切微观路径算法。

### 📝 试卷 3：EB-Manipulation 的硬核提示词 (纯七维坐标，无字典)
在这里，大模型的输入输出被定义成了**极其硬核的第七轴空间坐标组**！根本没有什么“action id 1 = 向上抬”的选项！
```markdown
## You are a Franka Panda robot with a parallel gripper...
** Output Action Space **
- Each output action is represented as a 7D discrete gripper action in the following format: [X, Y, Z, Roll, Pitch, Yaw, Gripper state].
- X, Y, Z are the 3D discrete position of the gripper in the environment...
- ...
(跟随机械臂视角拍设的一堆前后双机位照片)
```
**解析**：在机械臂抓取任务中，大模型必须输出如 `[30, 15, 20, 0, 90, 0, 1]` 的七位数组矩阵，前三维控制抓手的空间位姿，后三维控制偏航角，最后一位控制开合紧抓。这就是传说中的空间具身理解指令！

---

## [NEW] 进阶魔改指南：EB-Navigation 中深挖 AI2-THOR 场景互动

如果您希望突破单纯的 JSON 任务修饰，主动在 3D 渲染场景里“兴风作浪”（如获取场景隐藏道具、更改默认目标甚至凭空转移生成物品），您可以在 `embench_nav` 环境下，通过绕开框架直接调用底层的 `ai2thor.controller.Controller` API 来做到。

### 1. 如何查看本场景中到底存放了哪些 3D 物品？
如果想穷举一个房间（如 `FloorPlan22`）内部包含的所有物品资产，您可以自己开一个空控制器，并在初始化后直接打印 `metadata` 中的全部清单。我们在项目根目录下放置了一个 `list_objects.py` 作为示例。
它会调用下属接口返回大约 70 种带独特 ID 的预加载对象，包括了 Apple、Tomato、Microwave 等等，同时包含了每件物品当前的空间三维坐标 `(x, y, z)` 和种类名称 `objectType`。

### 2. 怎样不找“指定物体”，换一个对象作为导航目标？
这非常简单！一旦您通过上面的脚本抓取出了该场景下其它物品的合法专属 `objectId`（例如：`"Apple|+00.32|+01.14|+01.51"`），您只需重写对应的任务 JSON（比如我们在 `datasets` 目录下自己建立的 `base_custom.json`）。
将原本的 `targetObjectType` 和 `targetObjectIds` 完全抹去换成您的 Apple 的值和类型。大模型就能在同样的房间场景里收到您下达给它的新命令并自动寻路！

### 3. 是否能像造物主一样在场景中“无中生有”动态添加新物品？
直接依赖代码纯靠参数“硬捏”出一个原本内存和地图库里并未缓存进来的新 Unity 预制件难度极高（这部分功能在近几年老版本接口上也被逐渐废弃）。**但是，我们可以使用传送“伪造”！**
AI2-THOR 的开放 API 包含一个神通广大的 `SetObjectPoses` 功能。我们可以在游戏开始的初始化钩子处（具体实现在源码 `reset` 后或者另起脚本中），利用该动作锁定目标视野外（比如墙角、抽屉深处）存在的一个番茄，强行把它瞬间传送到面前餐桌的高光坐标系上！
```python
# 假设你在房间找到了一个遥远的 'Tomato_0f198569'
action_params = {
    "action": "SetObjectPoses",
    "objectPoses": [{
        "objectName": "Tomato_0f198569",
        "position": {"x": -0.5, "y": 0.95, "z": -1.2}, # 将坐标直接设定到餐桌桌面上 
        "rotation": {"x": 0, "y": 0, "z": 0}
    }]
}
controller.step(action_params)
# 房间里这个远方的番茄就这么活生生被吸到了您的面前！您可以借此变相创建物品让模型研究。
```
有关详细的 `teleport_object.py` 脚本代码与端到端高阶测试的日志，欢迎查阅文档最后附赠的 `EB_Navigation_Study.md` 研究报告合集！
