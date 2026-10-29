# -*- coding: utf-8 -*-


# 持仓与证券信息的加载已移入 data_load.py，这里导入并调用。
from data_load import load_positions, load_securities, enrich_positions, decompose_index_futures, load_country_tiers

from metrics import LongShort_portfolio, issuer_exposure, compute_short_issuer_stress, compute_top_5_requirement, compute_long_short_ratio, compute_country_nmv, compute_sector_nmv, compute_issuer_gmv, compute_direct_lcl, compute_direct_grade, compute_issuer_report_metrics, compute_portfolio_structure, compute_structure_shares

# 第 2 阶段修改：规则条款改由规则引擎执行（可插拔规则）。
from rule_config import load_rule_config
from rules.base import MarginContext
from rules.engine import RuleEngine


# 用于把明细表写入 xlsx
import openpyxl

# 报告生成函数：写出 report.tex，再用 pdflatex 编译成 PDF。
from make_report_tex import write_report_tex

positions = load_positions()
print("持仓条数 =", len(positions))

securities = load_securities()
print("证券信息条数 =", len(securities))

# 持仓字段补全已移入 data_load.py：证券信息字段、个券指标、市值与有向市值。
positions = enrich_positions(positions, securities)

# 指数成份拆分已移入 data_load.py，这里调用并接收成份持仓列表。
constituent_positions = decompose_index_futures(positions)

# 发行人敞口聚合已移入 metrics.py，这里调用并接收三类敞口。
issuer_exposure, direct_holding_exposure, index_holding_exposure = issuer_exposure(positions, constituent_positions)

# Short Issuer Stress 已移入 metrics.py，这里调用并接收最大压力损失。
largest_short_stress = compute_short_issuer_stress(issuer_exposure, securities)

# Top 5 要求已移入 metrics.py，这里调用并接收要求值与损失明细。
top_5_requirement, stress_losses = compute_top_5_requirement(issuer_exposure)

# 组合合计已移入 metrics.py，这里调用并接收四个合计值。
long_total, short_total, net_exposure, gross_market_value = LongShort_portfolio(positions)

# Long/Short 比率已移入 metrics.py，这里调用并接收。
long_short_ratio = compute_long_short_ratio(long_total, short_total)

# ---- 第 2 阶段修改：规则条款调用改为"指标 → context → 引擎"三步。----

# 第一步：算好规则需要的全部指标（指标计算仍来自 metrics.py）。
country_tiers = load_country_tiers()
country_nmv = compute_country_nmv(issuer_exposure, securities)
issuer_gmv = compute_issuer_gmv(positions, constituent_positions)
direct_lcl = compute_direct_lcl(positions)
sector_nmv = compute_sector_nmv(issuer_exposure, securities)
direct_grade = compute_direct_grade(positions)

# 第二步：把指标装进 context；规则只从 context 取值，不直接调用指标函数。
context = MarginContext(
    positions=positions,
    securities=securities,
    country_tiers=country_tiers,
    gross_market_value=gross_market_value,
    long_short_ratio=long_short_ratio,
    net_exposure=net_exposure,
    country_nmv=country_nmv,
    sector_nmv=sector_nmv,
    issuer_gmv=issuer_gmv,
    issuer_exposure=issuer_exposure,
    direct_lcl=direct_lcl,
    direct_grade=direct_grade,
)

# 第三步：规则引擎按 YAML 的 rules 列表顺序执行启用的规则。
# 停用某条规则：在 YAML 的 rules 列表里删掉对应行。
rule_config = load_rule_config("configs/jpm_margin_v2024.yaml")
engine = RuleEngine(rule_config)
results = engine.run(context)

# Section A 由五条规则的合计组成：初始要求、单一国家、国家等级、流动性、行业。
section_a = results["initial_requirement"].requirement
section_a = section_a + results["single_country"].requirement
print("Section A 累计 =", section_a)
print()
section_a = section_a + results["aggregate_country"].requirement
print("Section A 累计 =", section_a)
print()
section_a = section_a + results["liquidity"].requirement
print("Section A 累计 =", section_a)
print()
section_a = section_a + results["sector"].requirement
print("Section A 累计 =", section_a)
print()

# Base Margin 取大：Section A、Short Issuer Stress、Top 5 三者取最大值。
base_margin_requirement = max(section_a, largest_short_stress, top_5_requirement)
print("Base Margin Requirement =", base_margin_requirement)
print()

# 报告所需的发行人级指标已移入 metrics.py，这里调用并接收两个字典。
issuer_lcl_flags, issuer_dohs = compute_issuer_report_metrics(positions, issuer_gmv, securities)

# 组合结构聚合已移入 metrics.py，这里调用并接收七个聚合值。
largest_sector, largest_sector_gmv, largest_country, largest_country_gmv, tier_gmv, lcl_gmv, liquid_gmv = compute_portfolio_structure(issuer_gmv, securities, country_tiers, issuer_lcl_flags, issuer_dohs)
# 组合结构份额已移入 metrics.py，这里调用并接收六个份额值。
sector_share, country_share, tier1_share, tier2_share, lcl_share, liquid_share = compute_structure_shares(largest_sector_gmv, largest_country_gmv, tier_gmv, lcl_gmv, liquid_gmv, gross_market_value)

# 总保证金 = Base Margin + Portfolio Conditions
portfolio_conditions_requirement = results["portfolio_conditions"].requirement
total_margin_requirement = base_margin_requirement + portfolio_conditions_requirement

# 控制台报告打印已移入 console_report.py；main.py 只生成 PDF 报告，不再打印终端报告。

# 第 2 阶段修改：以下变量改从规则引擎结果中取出，供 xlsx 明细与 PDF 报告使用。
initial_requirement_part_a = results["initial_requirement"].details["part_a"]
initial_requirement_part_b = results["initial_requirement"].details["part_b"]
issuer_grades = results["portfolio_conditions"].details["issuer_grades"]
port_condition_req = results["portfolio_conditions"].details["port_condition_req"]
port_condition_thresholds = results["portfolio_conditions"].details["port_condition_thresholds"]
country_requirements = results["single_country"].details["country_requirements"]
country_threshold_amounts = results["single_country"].details["country_threshold_amounts"]
single_country_requirement = results["single_country"].requirement
aggregate_country_requirement = results["aggregate_country"].requirement
liquidity_requirement = results["liquidity"].requirement
sector_requirements = results["sector"].details["sector_requirements"]
sector_requirement = results["sector"].requirement


# openpyxl 的三个基本动作——创建工作簿、写单元格、保存文件。
# Security-Level Metrics 明细写入 xlsx：表头 8 列，11 个发行人各一行。
# 创建工作簿：Workbook() 会新建一个 xlsx 工作簿，里面自带一个工作表。

security_workbook = openpyxl.Workbook()
security_sheet = security_workbook.active
security_sheet.title = "Security-Level Metrics"

# 写单元格：row 与 column 都从 1 开始，与 Excel 的行列编号一致。
# 表头：与报告 III 的列顺序一致。
security_sheet.cell(row=1, column=1, value="Ticker")
security_sheet.cell(row=1, column=2, value="Market Cap")
security_sheet.cell(row=1, column=3, value="ADTV")
security_sheet.cell(row=1, column=4, value="DoH")
security_sheet.cell(row=1, column=5, value="Grade")
security_sheet.cell(row=1, column=6, value="LCL")
security_sheet.cell(row=1, column=7, value="Country")
security_sheet.cell(row=1, column=8, value="Sector")

# 逐发行人写一行：数据行从第 2 行开始（第 1 行是表头）。
row_number = 2
for ticker in issuer_gmv:
    info = securities[ticker]
    security_sheet.cell(row=row_number, column=1, value=ticker)
    security_sheet.cell(row=row_number, column=2, value=info["market_cap"])
    security_sheet.cell(row=row_number, column=3, value=info["adtv"])
    security_sheet.cell(row=row_number, column=4, value=issuer_dohs[ticker])
    security_sheet.cell(row=row_number, column=5, value=issuer_grades[ticker])
    security_sheet.cell(row=row_number, column=6, value=issuer_lcl_flags[ticker])
    security_sheet.cell(row=row_number, column=7, value=info["country"])
    security_sheet.cell(row=row_number, column=8, value=info["gics_sector"])

    # 数字格式：市值与 ADTV 用千分位加两位小数，DoH 保持 9 位小数。
    security_sheet.cell(row=row_number, column=2).number_format = "#,##0.00"
    security_sheet.cell(row=row_number, column=3).number_format = "#,##0.00"
    security_sheet.cell(row=row_number, column=4).number_format = "0.000000000"
    row_number = row_number + 1

# 保存移到第 27 步(3)：等第二个表也写完后保存一次。

# Issuer Exposures 明细写入同一工作簿的第二个工作表。
# create_sheet 在现有工作簿里新增工作表；Workbook() 才是新建文件。
exposure_sheet = security_workbook.create_sheet("Issuer Exposures")

# 表头：与报告 IV 的列顺序一致。
exposure_sheet.cell(row=1, column=1, value="Ticker")
exposure_sheet.cell(row=1, column=2, value="Direct MV")
exposure_sheet.cell(row=1, column=3, value="Constituent MV")
exposure_sheet.cell(row=1, column=4, value="Net Exposure")
exposure_sheet.cell(row=1, column=5, value="GMV")

# 逐发行人写一行，四个数值列用千分位加两位小数格式。
row_number = 2
for ticker in issuer_gmv:
    exposure_sheet.cell(row=row_number, column=1, value=ticker)
    exposure_sheet.cell(row=row_number, column=2, value=direct_holding_exposure[ticker])
    exposure_sheet.cell(row=row_number, column=3, value=index_holding_exposure[ticker])
    exposure_sheet.cell(row=row_number, column=4, value=issuer_exposure[ticker])
    exposure_sheet.cell(row=row_number, column=5, value=issuer_gmv[ticker])

    exposure_sheet.cell(row=row_number, column=2).number_format = "#,##0.00"
    exposure_sheet.cell(row=row_number, column=3).number_format = "#,##0.00"
    exposure_sheet.cell(row=row_number, column=4).number_format = "#,##0.00"
    exposure_sheet.cell(row=row_number, column=5).number_format = "#,##0.00"
    row_number = row_number + 1

# 循环结束后 row_number 停在下一个空行，正好写 Total 合计行。
exposure_sheet.cell(row=row_number, column=1, value="Total")
exposure_sheet.cell(row=row_number, column=2, value=sum(direct_holding_exposure.values()))
exposure_sheet.cell(row=row_number, column=3, value=sum(index_holding_exposure.values()))
exposure_sheet.cell(row=row_number, column=4, value=sum(issuer_exposure.values()))
exposure_sheet.cell(row=row_number, column=5, value=sum(issuer_gmv.values()))
exposure_sheet.cell(row=row_number, column=2).number_format = "#,##0.00"
exposure_sheet.cell(row=row_number, column=3).number_format = "#,##0.00"
exposure_sheet.cell(row=row_number, column=4).number_format = "#,##0.00"
exposure_sheet.cell(row=row_number, column=5).number_format = "#,##0.00"

# 保存移到第 27 步(4)：等第三个表也写完后保存一次。


# Portfolio Conditions 明细写入第三个工作表：只写要求大于 0 的发行人，与报告 V.4 一致。
portfolio_sheet = security_workbook.create_sheet("Portfolio Conditions")

# 表头：与报告 V.4 的打印字段一致。
portfolio_sheet.cell(row=1, column=1, value="Ticker")
portfolio_sheet.cell(row=1, column=2, value="Grade")
portfolio_sheet.cell(row=1, column=3, value="Exposure")
portfolio_sheet.cell(row=1, column=4, value="Threshold")
portfolio_sheet.cell(row=1, column=5, value="Requirement")

# 逐发行人写一行：要求小于等于 0 的跳过，与报告 V.4 的筛选一致。
row_number = 2
for ticker, net in issuer_exposure.items():
    if port_condition_req[ticker] <= 0:
        continue

    grade = issuer_grades[ticker]
    # 第 2 阶段修改：阈值金额改从规则引擎结果中取出。
    pc_threshold_amount = port_condition_thresholds[ticker]

    portfolio_sheet.cell(row=row_number, column=1, value=ticker)
    portfolio_sheet.cell(row=row_number, column=2, value=grade)
    portfolio_sheet.cell(row=row_number, column=3, value=net)
    portfolio_sheet.cell(row=row_number, column=4, value=pc_threshold_amount)
    portfolio_sheet.cell(row=row_number, column=5, value=port_condition_req[ticker])

    portfolio_sheet.cell(row=row_number, column=3).number_format = "#,##0.00"
    portfolio_sheet.cell(row=row_number, column=4).number_format = "#,##0.00"
    portfolio_sheet.cell(row=row_number, column=5).number_format = "#,##0.00"
    row_number = row_number + 1

# 三张表都写完后保存一次。
security_workbook.save("output/issuer_details.xlsx")
print("已写出 output/issuer_details.xlsx")

# 调用报告生成函数并传入组合数据，生成 report.tex。
write_report_tex(positions, long_total, short_total, net_exposure, gross_market_value, long_short_ratio, largest_sector, sector_share, largest_country, country_share, tier1_share, tier2_share, lcl_share, liquid_share, initial_requirement_part_a, initial_requirement_part_b, country_nmv, country_threshold_amounts, country_requirements, single_country_requirement, aggregate_country_requirement, liquidity_requirement, sector_nmv, sector_requirements, sector_requirement, section_a, issuer_exposure, largest_short_stress, stress_losses, top_5_requirement, base_margin_requirement, portfolio_conditions_requirement, total_margin_requirement)

