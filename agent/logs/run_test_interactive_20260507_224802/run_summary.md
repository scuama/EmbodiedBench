# Intent Reasoning Agent Run Summary
**Episode ID:** test_interactive  
**Timestamp:** 20260507_224802  

---

### Step 0

![Observation](visuals/step_00_obs_dual.png)

- **手持物品 (Held Object)**: `None`
- **可选动作数量**: `15` 个
- **已探索地点**: `{}`
- **记忆物品**: `['ball']`
- **Ranker 决策 (Top-2)**:
- **最终执行**: `Action 8 -> navigate to the TV stand`

---

### Step 1

![Observation](visuals/step_01_obs_dual.png)

- **手持物品 (Held Object)**: `None`
- **可选动作数量**: `14` 个
- **已探索地点**: `{'tv stand': 'fully_explored'}`
- **记忆物品**: `['ball']`
- **Ranker 决策 (Top-2)**:
- **最终执行**: `Action 13 -> navigate to the refrigerator`

---

### Step 2

![Observation](visuals/step_02_obs_dual.png)

- **手持物品 (Held Object)**: `None`
- **可选动作数量**: `1` 个
- **已探索地点**: `{'tv stand': 'fully_explored', 'refrigerator': 'visited_closed'}`
- **记忆物品**: `['ball']`
- **Ranker 决策 (Top-2)**:
- **最终执行**: `Action 60 -> open the refrigerator`

---

### Step 3

![Observation](visuals/step_03_obs_dual.png)

- **手持物品 (Held Object)**: `None`
- **可选动作数量**: `1` 个
- **已探索地点**: `{'tv stand': 'fully_explored', 'refrigerator': 'fully_explored'}`
- **记忆物品**: `['ball']`
- **Ranker 决策 (Top-2)**:
- **最终执行**: `Action 61 -> close the refrigerator`

---

### Step 4

![Observation](visuals/step_04_obs_dual.png)

- **手持物品 (Held Object)**: `None`
- **可选动作数量**: `14` 个
- **已探索地点**: `{'tv stand': 'fully_explored', 'refrigerator': 'fully_explored'}`
- **记忆物品**: `['ball']`
- **Ranker 决策 (Top-2)**:
- **最终执行**: `Action 6 -> navigate to the table 1`

---

### Step 5

![Observation](visuals/step_05_obs_dual.png)

- **手持物品 (Held Object)**: `None`
- **可选动作数量**: `3` 个
- **已探索地点**: `{'tv stand': 'fully_explored', 'refrigerator': 'fully_explored', 'table 1': 'fully_explored'}`
- **记忆物品**: `['ball', 'strawberry', 'lego']`
- **Ranker 决策 (Top-2)**:
- **最终执行**: `Action 38 -> pick up the strawberry`

---

