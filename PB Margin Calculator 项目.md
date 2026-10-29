# PB Margin Calculator 项目结构



适合 GitHub 的项目结构目录树

```text
pb-margin-calculator/
├── pyproject.toml
├── README.md
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── configs/
│   ├── jpm_margin_v2024.yaml
│   └── data_sources.yaml
├── scripts/
│   └── update_snapshot.py
├── src/
│   └── pb_margin/
│       ├── __init__.py
│       ├── models.py
│       ├── config.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── provider.py
│       │   ├── csv_provider.py
│       │   ├── yfinance_provider.py
│       │   └── cache.py
│       ├── metrics/
│       │   ├── __init__.py
│       │   ├── position.py
│       │   └── portfolio.py
│       ├── rules/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── bucket_rule.py
│       │   └── engine.py
│       ├── calc/
│       │   ├── __init__.py
│       │   ├── margin.py
│       │   └── futures.py
│       ├── report/
│       │   ├── __init__.py
│       │   └── summary.py
│       └── cli.py
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_rules.py
│   ├── test_metrics.py
│   └── test_margin_regression.py
├── examples/
│   ├── portfolio_sample.csv
│   └── run_demo.ipynb
└── data/
    └── snapshots/
        └── .gitkeep
```

## 模块职责

| 模块 | 路径 | 职责 |
|---|---|---|
| M0 项目骨架 | `pyproject.toml`、`.github/`、`README.md` | 依赖、CI、项目说明、目录容器 |
| M1 基础层 | `src/pb_margin/models.py`、`src/pb_margin/config.py` | 数据模型、配置 schema、YAML 加载与校验 |
| M2 数据层 | `src/pb_margin/data/` | `DataProvider` 接口、CSV / yfinance 实现、快照缓存 |
| M3 指标层 | `src/pb_margin/metrics/` | 个券指标、组合指标计算，纯函数 |
| M4 规则层 | `src/pb_margin/rules/` | `Rule` 抽象、`BucketRule`、规则引擎，配置驱动 |
| M5 计算层 | `src/pb_margin/calc/` | 保证金主流程、期货处理、组合规则分摊 |
| M6 报告展示 | `src/pb_margin/report/`、`src/pb_margin/cli.py`、`examples/` | 结果汇总、CLI、Demo Notebook |
| M7 测试 | `tests/` | 单元测试、回归测试、集成测试 |

## 说明

- `configs/` 中的 YAML 是规则版本化配置，JPM 规则更新时优先改配置，不改代码。
- `data/snapshots/` 存放每日客观数据快照，建议加入 `.gitignore`，用 `.gitkeep` 保留目录结构。
- `scripts/update_snapshot.py` 用于定时拉取全市场数据并落地为 CSV / Parquet。（目前不用做）
- 数据层与计算层解耦，存储格式可从 CSV 平滑替换为 Parquet / DuckDB，上层无感。



**数据、指标、规则、计算四层解耦**，扩展资产类型时只动对应层。



**规则层**的设计建议是：

"可插拔规则"和"配置驱动"把规则从代码里抽出来，写成配置文件（YAML / JSON / TOML）代码只负责"读配置 → 按 metric 取值 → 找到落在哪个 bucket → 累加 add"。规则变了只改 YAML，代码不动。

"可插拔"（pluggable）：每条规则是一个独立的、符合统一接口的模块，可以自由增删、替换、组合，而不影响其他部分。改规则只改 YAML + 加规则类，不动引擎。

加新规则：写一个新 `Rule` 子类，注册进去，不改引擎。

换规则：改 YAML 里的 `rules` 列表。

测规则：每条规则单独单元测试。

版本化：不同 YAML 文件对应不同规则版本，可并存、可对比。

**GitHub 展示友好**：每块是一个清晰的 commit / PR / issue，进度可见。