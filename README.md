# Portfolio Margin Calculation

根据主经纪商（Prime Brokerage）保证金规则（Margin Rule）计算基金投资组合所需保证金（Margin Requirement）的工具。

## 项目背景

对冲基金通过券商进行融资融券交易时，券商会依据自身保证金政策（Margin Policy）要求基金为投资组合提供保证金。本项目按照一份真实的主经纪商保证金政策实现计算：

- **Section A 初始要求**：总市值（GMV）前 10 亿按 12.5% 计收、超出部分按 35% 计收；Long/Short 比率偏离 [0.95, 1.05] 时按 20% × |净敞口| 加收；
- **单一国家要求**：某国净敞口超过该国档位阈值（阈值比例 × 总市值）时，对增量按档位费率计收；
- **国家等级要求**：按发行人所属国家等级（Tier 1–4）对总市值计收；Tier 3/4 区分 LCL 与非 LCL；
- **流动性要求**：按持有天数（Days of Holdings）分档（0.2–1、1–2、2–3 天）计收；
- **行业要求**：单一 GICS 行业净敞口超过总市值 15% 时，对增量计收 15%；
- **组合条件（Portfolio Conditions）**：发行人敞口超过对应等级阈值（High 2% / Medium 1.5% / Low 0.8%）时，对增量按 100% 计收；
- **Base Margin**：Section A、Short Issuer Stress、Top 5 三者取大；总保证金 = Base Margin + Portfolio Conditions。

股指期货持仓会按指数成份权重拆分为成份股持仓，再参与全部计算。

## 快速开始

要求：Python 3.10 及以上。在项目根目录下执行：

```bash
# 以开发模式安装（代码改动即时生效），dev 同时安装测试依赖
pip install -e ".[dev]"

# 运行计算：生成 report.tex 与 output/issuer_details.xlsx
python3 main.py

# 运行测试
python3 -m pytest
```

`report.tex` 可用 `pdflatex report.tex` 编译为 PDF 报告；个券与发行人级明细见 `output/issuer_details.xlsx`。

## 配置驱动与可插拔规则

全部规则参数集中在 `configs/ms_margin_v2024.yaml`，程序代码本身不含规则条款：

- **调整费率或阈值**：只改 YAML；
- **停用一条规则**：在 YAML 的 `rules` 列表中删除对应行；
- **新增一条规则**：写一个 `Rule` 子类 → 在 `rules/engine.py` 的 `REGISTRY` 中注册 → 在 YAML 中启用；
- **切换规则版本**：复制一份 YAML 修改后，用环境变量 `PB_RULE_CONFIG` 指定，例如 `PB_RULE_CONFIG=configs/新配置.yaml python3 main.py`。

## 项目结构

```
├── main.py                     # 入口脚本
├── pyproject.toml              # 项目元数据、依赖与测试配置
├── configs/                    # 规则配置（YAML）
├── data/                       # 证券信息、国家档位、指数成份
├── examples/                   # 示例组合（xlsx）
├── src/portfolio_margin/       # 源代码包
│   ├── data_load.py            # 数据加载与预处理（含指数成份拆分）
│   ├── metrics.py              # 指标计算（敞口、压力测试、组合结构）
│   ├── rule_config.py          # YAML 配置加载
│   ├── make_report_tex.py      # LaTeX 报告生成
│   └── rules/                  # 规则引擎（可插拔规则）
├── tests/                      # pytest 测试
└── .github/workflows/ci.yml    # GitHub Actions 持续集成（每次推送自动跑测试）
```

## 测试

42 个用例，覆盖四个层面：

- 规则单元测试：每条规则独立验证，参数写在测试里、与 YAML 解耦；
- 指标单元测试：敞口聚合、压力测试、组合结构；
- 配置一致性测试：启用的规则都有对应参数、无重复；
- 端到端回归测试：完整运行一次程序，核对结果与基线一致；并逐条停用规则验证程序不报错。

## 数据文件

- `data/securities_info.csv`：证券信息，列：ticker、country、market_cap、adtv、gics_sector；
- `data/country_tiers.csv`：国家档位，列：country、tier；
- `data/index_constituents.csv`：股指期货对应的成份股与权重，列：index_ticker、ticker、weight；
- `examples/portfolio_sample.xlsx`：组合持仓样例。
