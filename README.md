# 软体生物进化模拟器

这是一个使用 Python、Pymunk、Pygame 构建的**基于遗传算法的软体生物进化模拟器**。项目以三角形软体生物为起点：3 个质点通过 3 根“肌肉弹簧”连接，弹簧根据正弦函数自动伸缩；遗传算法负责优化每根弹簧的振幅、频率和相位参数，使生物尽可能向右移动。

## 已实现功能

- `Pymunk` 物理空间，带重力和高摩擦地面
- `Pygame` 可视化渲染与 `--headless` 高速评估模式
- 三角形软体生物（3 质点 + 3 弹簧）
- 弹簧控制方程：

$$
L(t)=L_{\text{base}} + A \sin(\omega t + \phi)
$$
- 基因编码：每条弹簧对应 `A, ω, φ`，共 9 维浮点染色体
- 适应度函数：10 秒仿真后，质心在 X 方向的位移
- 遗传算法：
  - 随机初始化 50 个体
  - 锦标赛选择
  - SBX 模拟二进制交叉
  - 多项式变异
  - 精英保留
- 默认最多进化 50 代
- 每隔 5 代在**同一个窗口**连续预览当前最优个体 5 秒
- 左上角实时显示 `generation / max fitness / average fitness`
- 保存每代最强基因到 `results/`
- 自动输出 `fitness_curve.png` 收敛曲线
- 支持从 JSON 文件回放冠军个体

## 项目结构

```text
soft-body-creature-evolution-simulator/
├─ results/
├─ src/
│  ├─ config.py          # 仿真与进化配置
│  ├─ creature.py        # 生物结构与肌肉弹簧
│  ├─ ga_engine.py       # 遗传算法核心与适应度评估
│  ├─ io_utils.py        # 结果保存 / 回放 / 曲线绘图
│  ├─ simulation_core.py # 物理空间创建
│  └─ main.py            # 连续可视化 + 进化主循环 + 回放
├─ requirements.txt
└─ README.md
```

## 安装依赖

建议在 Python 3.10+ 环境下运行。

```powershell
# 1. 创建虚拟环境 (可选)
python -m venv .venv

# 2. 激活虚拟环境
# Windows:
.\.venv\Scripts\Activate.ps1
# Mac/Linux:
source .venv/bin/activate

# 3. 安装依赖库
pip install -r requirements.txt


## 运行方式

### 1. 默认启动进化（点击运行即可）

```bash
python src/main.py
```

### 2. 快速测试少量进化代数

```bash
python src/main.py --generations 5 --no-demo
```

### 3. 回放冠军个体

```bash
python src/main.py --replay results/best_genome_overall.json --seconds 8
```

运行进化后会：
- 在终端打印每一代的 `max fitness / avg fitness`
- 每隔 5 代在同一个窗口中播放一次当前最优个体
- 每次播放 5 秒，并实时更新左上角统计信息
- 在 `results/` 中输出每代最优基因 JSON
- 生成 `fitness_history.json`
- 生成 `fitness_curve.png`

## 基因编码

三角形生物包含 3 根弹簧，每根弹簧编码三个参数：
- `A`：振幅比例
- `ω`：频率
- `φ`：相位

因此染色体结构为：

```text
[A1, ω1, φ1, A2, ω2, φ2, A3, ω3, φ3]
```

## 适应度函数说明

每个个体的基因会被解码成 3 根弹簧的振幅、频率和相位，然后在物理引擎中仿真 10 秒。记初始质心横坐标为 \(x_{0})，仿真结束时的质心横坐标为 \(x_{T})，则适应度定义为：

$$
\text{fitness} = x_{T} - x_{0}
$$

也就是说：
- 软体生物在 10 秒内**向右移动越远**，适应度越高
- 如果向左滑动或原地挣扎，适应度会较低，甚至可能为负值

这个定义简单直接，能很好地表达“让软体生物学会向前爬行”的目标。

## 典型输出文件

进化完成后，`results/` 下会出现：
- `best_genome_gen_001.json` 等每代最佳个体
- `best_genome_overall.json` 总冠军个体
- `fitness_history.json` 每代统计历史
- `fitness_curve.png` 收敛曲线图

## 后续可继续扩展

- 让初始形态不止三角形，而是随机 3-5 质点结构
- 引入多个生物同场竞争
- 支持多个不同地形与障碍物
- 增加 batch 实验模式，比较不同 GA 参数配置
- 为回放模式增加“暂停 / 继续 / 快进”控制
