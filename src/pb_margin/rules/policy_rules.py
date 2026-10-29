# -*- coding: utf-8 -*-
from .base import Rule, RuleResult

class InitialRequirementRule(Rule):
    """Initial Requirement：由 (a) 与 (b) 两部分之和组成。
    (a) 按总市值分层计收保证金：前 10 亿按 12.5% 计收，超出 10 亿的增量部分按 35% 计收。
    (b) 按多空比率加收保证金：Long/Short 比率超出 [0.95, 1.05] 时，加收 20% × |净敞口|。"""
    def apply(self, context):
        gross_market_value = context.gross_market_value
        long_short_ratio = context.long_short_ratio
        net_exposure = context.net_exposure

        part_a = self.params["part_a"]
        part_b = self.params["part_b"]

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

        return RuleResult(section_a, {"part_a": initial_requirement_part_a, "part_b": initial_requirement_part_b})

class SingleCountryRule(Rule):
    """单一国家集中度限额：|净敞口| 超过该国档位阈值（阈值比例 × 总市值）的增量部分，按档位费率计收保证金。"""
    def apply(self, context):
        single_country_requirement = 0
        # 存下每个国家的明细，供报告使用
        country_requirements = {}
        country_threshold_amounts = {}
        for country, nmv in context.country_nmv.items():
            tier = context.country_tiers[country]
            params = self.params[tier]
            threshold_rate = params["threshold_rate_percent"] / 100
            charge_rate = params["charge_rate_percent"] / 100

            threshold_amount = threshold_rate * context.gross_market_value
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

        return RuleResult(single_country_requirement, {"country_requirements": country_requirements, "country_threshold_amounts": country_threshold_amounts})

class AggregateCountryRule(Rule):
    """国家等级对应保证金：按发行人总市值计收——Tier 2 计收 2.5%；Tier 3 按 LCL 与否计收 10%/15%；Tier 4 计收 15%/20%；Tier 1 不计收。"""
    def apply(self, context):
        aggregate_country_requirement = 0
        lcl_market_cap = self.params["lcl_market_cap"]
        for ticker, gmv in context.issuer_gmv.items():
            tier = context.country_tiers[context.securities[ticker]["country"]]
            if tier == "Tier 1":
                continue

            if ticker in context.direct_lcl:
                lcl = context.direct_lcl[ticker]
            else:
                # 通过指数持有的发行人缺少股票价格，持有天数近似为 0，仅按市值判定
                lcl = context.securities[ticker]["market_cap"] > lcl_market_cap

            params = self.params[tier]
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

        return RuleResult(aggregate_country_requirement)

class SectorRule(Rule):
    """行业要求：单一 GICS 行业的 |净敞口| 超过总市值的 15% 时，对增量部分计收 15% 保证金。"""
    def apply(self, context):
        sector_requirement = 0
        # 存下每个行业的明细，供报告使用
        sector_requirements = {}
        threshold_amount = self.params["threshold_rate_percent"] / 100 * context.gross_market_value
        for sector, nmv in context.sector_nmv.items():
            excess = abs(nmv) - threshold_amount
            if excess > 0:
                requirement = excess * self.params["charge_rate_percent"] / 100
            else:
                requirement = 0
            sector_requirements[sector] = requirement
            print(sector, "净敞口 =", nmv, "阈值金额 =", threshold_amount, "要求 =", requirement)
            sector_requirement = sector_requirement + requirement

        print("行业要求合计 =", sector_requirement)
        print()

        return RuleResult(sector_requirement, {"sector_requirements": sector_requirements,
                                               "threshold_amount": threshold_amount})

class PortfolioConditionsRule(Rule):
    """Portfolio Conditions：发行人敞口（占总市值比例）超过对应等级阈值（High 2%/Medium 1.5%/Low 0.8%）时，对增量部分计收 100% 保证金。"""
    def apply(self, context):
        portfolio_conditions_requirement = 0
        # 存下每个发行人的等级与要求明细，供报告使用
        issuer_grades = {}
        port_condition_req = {}
        port_condition_thresholds = {}
        grade_params = self.params["grades"]
        grade_market_caps = self.params["grade_market_caps"]
        charge_rate = self.params["charge_rate_percent"] / 100
        for ticker, net in context.issuer_exposure.items():
            if ticker in context.direct_grade:
                grade = context.direct_grade[ticker]
            else:
                # 通过指数持有的发行人缺少价格数据，持有天数近似为 0，仅按市值判定等级
                market_cap = context.securities[ticker]["market_cap"]
                if market_cap >= grade_market_caps["high"]:
                    grade = "High Grade"
                elif market_cap >= grade_market_caps["medium"]:
                    grade = "Medium Grade"
                else:
                    grade = "Low Grade"

            issuer_grades[ticker] = grade

            threshold_rate = grade_params[grade]["threshold_rate_percent"] / 100

            threshold_amount = threshold_rate * context.gross_market_value
            excess = abs(net) - threshold_amount
            if excess > 0:
                # 计收费率 100%：增量部分全额计收
                requirement = excess * charge_rate
            else:
                requirement = 0
            port_condition_req[ticker] = requirement
            port_condition_thresholds[ticker] = threshold_amount
            print(ticker, grade, "敞口 =", net, "阈值金额 =", threshold_amount, "要求 =", requirement)
            portfolio_conditions_requirement = portfolio_conditions_requirement + requirement

        print("Portfolio Conditions 合计 =", portfolio_conditions_requirement)
        print()

        return RuleResult(portfolio_conditions_requirement, {"issuer_grades": issuer_grades, "port_condition_req": port_condition_req, "port_condition_thresholds": port_condition_thresholds})
