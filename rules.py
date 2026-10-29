# -*- coding: utf-8 -*-

# 规则参数统一放在配置文件里；改费率只改 YAML，不改代码。
from rule_config import load_rule_config

RULE_CONFIG = load_rule_config("configs/jpm_margin_v2024.yaml")

def compute_initial_requirement(gross_market_value, long_short_ratio, net_exposure):
    """Initial Requirement：由 (a) 与 (b) 两部分之和组成。
    (a) 按总市值分层计收保证金：前 10 亿按 12.5% 计收，超出 10 亿的增量部分按 35% 计收。
    (b) 按多空比率加收保证金：Long/Short 比率超出 [0.95, 1.05] 时，加收 20% × |净敞口|。"""
    params = RULE_CONFIG["initial_requirement"]
    part_a = params["part_a"]
    part_b = params["part_b"]

    first_tier_limit = part_a["first_tier_gmv_limit"]
    if gross_market_value <= first_tier_limit:
        # 总市值不超过第一档上限：全部按第一档费率计收
        initial_requirement_part_a = gross_market_value * part_a["first_tier_rate_percent"] / 100
    else:
        # 第一档以内按第一档费率，超出部分按增量费率
        initial_requirement_part_a = first_tier_limit * part_a["first_tier_rate_percent"] / 100
        initial_requirement_part_a = initial_requirement_part_a + (gross_market_value - first_tier_limit) * part_a["excess_rate_percent"] / 100
    print("Section A a) 分层要求 =", initial_requirement_part_a)

    # 比率由 metrics.py 计算后传入，这里打印并用于 (b) 的判断。
    print("Long/Short 比率 =", long_short_ratio)

    # 比率超出配置的上下界区间时，加收费率 × |净敞口|
    if long_short_ratio > part_b["ratio_upper_limit"] or long_short_ratio < part_b["ratio_lower_limit"]:
        initial_requirement_part_b = abs(net_exposure) * part_b["rate_percent"] / 100
    else:
        initial_requirement_part_b = 0

    section_a = initial_requirement_part_a + initial_requirement_part_b

    print("Section A b) 比率要求 =", initial_requirement_part_b)
    print("Initial Requirement =", section_a)
    print()

    return initial_requirement_part_a, initial_requirement_part_b, section_a

def compute_single_country_requirement(country_nmv, country_tiers, gross_market_value):
    """单一国家集中度限额：|净敞口| 超过该国档位阈值（阈值比例 × 总市值）的增量部分，按档位费率计收保证金。"""
    single_country_requirement = 0
    # 存下每个国家的明细，供报告使用
    country_requirements = {}
    country_threshold_amounts = {}
    tier_params = RULE_CONFIG["single_country"]
    for country, nmv in country_nmv.items():
        tier = country_tiers[country]
        params = tier_params[tier]
        threshold_rate = params["threshold_rate_percent"] / 100
        charge_rate = params["charge_rate_percent"] / 100

        threshold_amount = threshold_rate * gross_market_value
        excess = abs(nmv) - threshold_amount
        if excess > 0:
            requirement = excess * charge_rate
        else:
            requirement = 0
        country_requirements[country] = requirement
        country_threshold_amounts[country] = threshold_amount
        print(country, tier, "净敞口 =", nmv, "阈值金额 =", threshold_amount, "要求 =", requirement)
        single_country_requirement = single_country_requirement + requirement

    print("单一国家集中度限额合计 =", single_country_requirement)
    print()

    return single_country_requirement, country_requirements, country_threshold_amounts

def compute_aggregate_country_requirement(issuer_gmv, direct_lcl, securities, country_tiers):
    """国家等级对应保证金：按发行人总市值计收——Tier 2 计收 2.5%；Tier 3 按 LCL 与否计收 10%/15%；Tier 4 计收 15%/20%；Tier 1 不计收。"""
    aggregate_country_requirement = 0
    tier_params = RULE_CONFIG["aggregate_country"]
    lcl_market_cap = tier_params["lcl_market_cap"]
    for ticker, gmv in issuer_gmv.items():
        tier = country_tiers[securities[ticker]["country"]]
        if tier == "Tier 1":
            continue

        if ticker in direct_lcl:
            lcl = direct_lcl[ticker]
        else:
            # 通过指数持有的发行人缺少股票价格，持有天数近似为 0，仅按市值判定
            lcl = securities[ticker]["market_cap"] > lcl_market_cap

        params = tier_params[tier]
        if tier == "Tier 2":
            rate = params["rate_percent"] / 100
        elif lcl:
            rate = params["lcl_rate_percent"] / 100
        else:
            rate = params["non_lcl_rate_percent"] / 100

        requirement = gmv * rate
        print(ticker, tier, "总市值 =", gmv, "要求 =", requirement)
        aggregate_country_requirement = aggregate_country_requirement + requirement

    print("国家等级对应保证金合计 =", aggregate_country_requirement)
    print()

    return aggregate_country_requirement

def compute_liquidity_requirement(positions):
    """流动性要求：按持有天数分档，对"超过档位下限天数"的市值部分计收保证金。
    分档与费率见配置文件 liquidity.buckets。
    各档独立判断：持有 2.5 天时三档同时计收。成份持仓本步暂不处理。"""
    liquidity_requirement = 0
    for position in positions:
        if position["is_index_futures"]:
            continue

        days_of_holdings = position["days_of_holdings"]
        market_value = position["market_value"]

        charge = 0
        # 各档独立判断：持有天数超过档位下限的部分，按该档费率计收。
        for bucket in RULE_CONFIG["liquidity"]["buckets"]:
            lower_days = bucket["lower_days"]
            upper_days = bucket["upper_days"]
            if days_of_holdings > lower_days:
                excess_days = min(days_of_holdings, upper_days) - lower_days
                charged_value = market_value * excess_days / days_of_holdings
                charge = charge + charged_value * bucket["rate_percent"] / 100

        # 费用写回持仓字典：positions 是同一个列表对象，main.py 里同样可见。
        position["liquidity_charge"] = charge
        print(position["ticker"], "DoH =", days_of_holdings, "流动性要求 =", charge)
        liquidity_requirement = liquidity_requirement + charge

    print("流动性要求合计 =", liquidity_requirement)
    print()

    return liquidity_requirement

def compute_sector_requirement(sector_nmv, gross_market_value):
    """行业要求：单一 GICS 行业的 |净敞口| 超过总市值的 15% 时，对增量部分计收 15% 保证金。"""
    sector_requirement = 0
    # 存下每个行业的明细，供报告使用
    sector_requirements = {}
    params = RULE_CONFIG["sector"]
    threshold_amount = params["threshold_rate_percent"] / 100 * gross_market_value
    for sector, nmv in sector_nmv.items():
        excess = abs(nmv) - threshold_amount
        if excess > 0:
            requirement = excess * params["charge_rate_percent"] / 100
        else:
            requirement = 0
        sector_requirements[sector] = requirement
        print(sector, "净敞口 =", nmv, "阈值金额 =", threshold_amount, "要求 =", requirement)
        sector_requirement = sector_requirement + requirement

    print("行业要求合计 =", sector_requirement)
    print()

    return sector_requirement, sector_requirements

def compute_base_margin(section_a, largest_short_stress, top_5_requirement):
    """Base Margin Requirement：Section A、Short Issuer Stress、Top 5 三个比较项取最大。"""
    # max() 是内置函数，返回多个数值中最大的一个。
    base_margin_requirement = max(section_a, largest_short_stress, top_5_requirement)

    print("Base Margin Requirement =", base_margin_requirement)
    print()

    return base_margin_requirement

def compute_portfolio_conditions(issuer_exposure, direct_grade, securities, gross_market_value):
    """Portfolio Conditions：发行人敞口（占总市值比例）超过对应等级阈值（High 2%/Medium 1.5%/Low 0.8%）时，对增量部分计收 100% 保证金。"""
    # 存下每个发行人的等级与要求明细，供报告使用
    portfolio_conditions_requirement = 0
    issuer_grades = {}
    port_condition_req = {}
    params = RULE_CONFIG["portfolio_conditions"]
    grade_params = params["grades"]
    grade_market_caps = params["grade_market_caps"]
    charge_rate = params["charge_rate_percent"] / 100
    for ticker, net in issuer_exposure.items():
        if ticker in direct_grade:
            grade = direct_grade[ticker]
        else:
            # 通过指数持有的发行人缺少价格数据，持有天数近似为 0，仅按市值判定等级
            market_cap = securities[ticker]["market_cap"]
            if market_cap >= grade_market_caps["high"]:
                grade = "High Grade"
            elif market_cap >= grade_market_caps["medium"]:
                grade = "Medium Grade"
            else:
                grade = "Low Grade"

        issuer_grades[ticker] = grade

        threshold_rate = grade_params[grade]["threshold_rate_percent"] / 100

        threshold_amount = threshold_rate * gross_market_value
        excess = abs(net) - threshold_amount
        if excess > 0:
            # 计收费率 100%：增量部分全额计收
            requirement = excess * charge_rate
        else:
            requirement = 0
        port_condition_req[ticker] = requirement
        print(ticker, grade, "敞口 =", net, "阈值金额 =", threshold_amount, "要求 =", requirement)
        portfolio_conditions_requirement = portfolio_conditions_requirement + requirement

    print("Portfolio Conditions 合计 =", portfolio_conditions_requirement)
    print()

    return portfolio_conditions_requirement, issuer_grades, port_condition_req
