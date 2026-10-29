# -*- coding: utf-8 -*-
"""rules 包中各规则的单元测试。参数直接在测试里写明，与 YAML 解耦。"""
import pytest

from rules.base import MarginContext
from rules.bucket_rule import BucketRule
from rules.engine import REGISTRY, RuleEngine
from rules.policy_rules import (InitialRequirementRule, SingleCountryRule,
                                AggregateCountryRule, SectorRule,
                                PortfolioConditionsRule)

INITIAL_PARAMS = {
    "part_a": {"first_tier_gmv_limit": 1_000_000_000,
               "first_tier_rate_percent": 12.5,
               "excess_rate_percent": 35},
    "part_b": {"ratio_lower_limit": 0.95,
               "ratio_upper_limit": 1.05,
               "rate_percent": 20},
}

SINGLE_COUNTRY_PARAMS = {
    "Tier 1": {"threshold_rate_percent": 10, "charge_rate_percent": 10},
    "Tier 2": {"threshold_rate_percent": 5, "charge_rate_percent": 10},
}

AGGREGATE_COUNTRY_PARAMS = {
    "Tier 2": {"rate_percent": 2.5},
    "Tier 3": {"lcl_rate_percent": 10, "non_lcl_rate_percent": 15},
    "Tier 4": {"lcl_rate_percent": 15, "non_lcl_rate_percent": 20},
    "lcl_market_cap": 10_000_000_000,
}

LIQUIDITY_PARAMS = {"buckets": [
    {"lower_days": 0.2, "upper_days": 1, "rate_percent": 15},
    {"lower_days": 1, "upper_days": 2, "rate_percent": 35},
    {"lower_days": 2, "upper_days": 3, "rate_percent": 50},
]}

SECTOR_PARAMS = {"threshold_rate_percent": 15, "charge_rate_percent": 15}

PORTFOLIO_CONDITIONS_PARAMS = {
    "grades": {"High Grade": {"threshold_rate_percent": 2},
               "Medium Grade": {"threshold_rate_percent": 1.5},
               "Low Grade": {"threshold_rate_percent": 0.8}},
    "charge_rate_percent": 100,
    "grade_market_caps": {"high": 10_000_000_000, "medium": 3_000_000_000},
}


def make_context(**overrides):
    """组装测试 context：默认值取不影响计算的最小值。"""
    defaults = dict(
        positions=[],
        securities={},
        country_tiers={},
        gross_market_value=100_000_000,
        long_short_ratio=1.0,
        net_exposure=0,
        country_nmv={},
        sector_nmv={},
        issuer_gmv={},
        issuer_exposure={},
        direct_lcl={},
        direct_grade={},
    )
    defaults.update(overrides)
    return MarginContext(**defaults)


def make_position(ticker, days, market_value, is_index_futures=False):
    """组装一条持仓记录（流动性规则测试用）。"""
    return {"ticker": ticker, "days_of_holdings": days,
            "market_value": market_value, "is_index_futures": is_index_futures}


class TestInitialRequirementRule:
    def test_first_tier_charge_only(self):
        # 总市值未超过 10 亿：全部按 12.5% 计收，(b) 为 0
        rule = InitialRequirementRule("initial_requirement", INITIAL_PARAMS)
        result = rule.apply(make_context(gross_market_value=800_000_000))
        assert result.requirement == pytest.approx(800_000_000 * 12.5 / 100)
        assert result.details["part_b"] == 0

    def test_excess_gmv_gets_higher_rate(self):
        # 超过 10 亿的增量部分按 35% 计收
        rule = InitialRequirementRule("initial_requirement", INITIAL_PARAMS)
        result = rule.apply(make_context(gross_market_value=2_000_000_000))
        expected = 1_000_000_000 * 12.5 / 100 + 1_000_000_000 * 35 / 100
        assert result.details["part_a"] == pytest.approx(expected)

    def test_ratio_above_upper_limit(self):
        # 比率 > 1.05：加收 20% × |净敞口|
        rule = InitialRequirementRule("initial_requirement", INITIAL_PARAMS)
        result = rule.apply(make_context(long_short_ratio=1.2,
                                         net_exposure=-50_000_000))
        assert result.details["part_b"] == pytest.approx(50_000_000 * 20 / 100)

    def test_ratio_below_lower_limit(self):
        # 比率 < 0.95：同样加收
        rule = InitialRequirementRule("initial_requirement", INITIAL_PARAMS)
        result = rule.apply(make_context(long_short_ratio=0.9,
                                         net_exposure=30_000_000))
        assert result.details["part_b"] == pytest.approx(30_000_000 * 20 / 100)

    def test_ratio_inside_limits_no_charge(self):
        rule = InitialRequirementRule("initial_requirement", INITIAL_PARAMS)
        result = rule.apply(make_context(long_short_ratio=1.0,
                                         net_exposure=-50_000_000))
        assert result.details["part_b"] == 0


class TestSingleCountryRule:
    def test_excess_over_threshold_is_charged(self):
        # Tier 1：阈值 10% × GMV，超出的增量按 10% 计收
        rule = SingleCountryRule("single_country", SINGLE_COUNTRY_PARAMS)
        context = make_context(country_nmv={"USA": 30_000_000},
                               country_tiers={"USA": "Tier 1"})
        result = rule.apply(context)
        assert result.requirement == pytest.approx(20_000_000 * 10 / 100)
        assert result.details["country_requirements"]["USA"] == pytest.approx(2_000_000)

    def test_below_threshold_no_charge(self):
        rule = SingleCountryRule("single_country", SINGLE_COUNTRY_PARAMS)
        context = make_context(country_nmv={"USA": 8_000_000},
                               country_tiers={"USA": "Tier 1"})
        assert rule.apply(context).requirement == 0

    def test_tier2_threshold_and_rate(self):
        # Tier 2：阈值 5% × GMV，费率 10%
        rule = SingleCountryRule("single_country", SINGLE_COUNTRY_PARAMS)
        context = make_context(country_nmv={"Hong Kong": 20_000_000},
                               country_tiers={"Hong Kong": "Tier 2"})
        assert rule.apply(context).requirement == pytest.approx(15_000_000 * 10 / 100)


class TestAggregateCountryRule:
    def test_tier1_not_charged(self):
        rule = AggregateCountryRule("aggregate_country", AGGREGATE_COUNTRY_PARAMS)
        context = make_context(
            issuer_gmv={"AAA": 10_000_000},
            securities={"AAA": {"country": "USA", "market_cap": 20_000_000_000}},
            country_tiers={"USA": "Tier 1"},
        )
        assert rule.apply(context).requirement == 0

    def test_tier2_flat_rate(self):
        # Tier 2：按总市值全额计收 2.5%
        rule = AggregateCountryRule("aggregate_country", AGGREGATE_COUNTRY_PARAMS)
        context = make_context(
            issuer_gmv={"AAA": 10_000_000},
            securities={"AAA": {"country": "Hong Kong", "market_cap": 5_000_000_000}},
            country_tiers={"Hong Kong": "Tier 2"},
        )
        assert rule.apply(context).requirement == pytest.approx(10_000_000 * 2.5 / 100)

    def test_tier3_lcl_vs_non_lcl(self):
        # Tier 3：LCL 计收 10%，非 LCL 计收 15%
        rule = AggregateCountryRule("aggregate_country", AGGREGATE_COUNTRY_PARAMS)
        context = make_context(
            issuer_gmv={"AAA": 10_000_000, "BBB": 10_000_000},
            securities={"AAA": {"country": "India", "market_cap": 5_000_000_000},
                        "BBB": {"country": "India", "market_cap": 5_000_000_000}},
            country_tiers={"India": "Tier 3"},
            direct_lcl={"AAA": True, "BBB": False},
        )
        result = rule.apply(context)
        expected = 10_000_000 * 10 / 100 + 10_000_000 * 15 / 100
        assert result.requirement == pytest.approx(expected)

    def test_tier3_fallback_by_market_cap(self):
        # 无 direct_lcl 的发行人（仅指数持有）按市值判定：超 100 亿为 LCL
        rule = AggregateCountryRule("aggregate_country", AGGREGATE_COUNTRY_PARAMS)
        context = make_context(
            issuer_gmv={"AAA": 10_000_000},
            securities={"AAA": {"country": "India", "market_cap": 20_000_000_000}},
            country_tiers={"India": "Tier 3"},
        )
        assert rule.apply(context).requirement == pytest.approx(10_000_000 * 10 / 100)


class TestBucketRule:
    def test_one_bucket(self):
        # 持有 0.5 天：只有第一档，计收 (0.5-0.2)/0.5 的市值 × 15%
        rule = BucketRule("liquidity", LIQUIDITY_PARAMS)
        context = make_context(positions=[make_position("AAA", 0.5, 1_000_000)])
        result = rule.apply(context)
        charged = 1_000_000 * (0.5 - 0.2) / 0.5 * 15 / 100
        assert result.requirement == pytest.approx(charged)

    def test_three_buckets(self):
        # 持有 2.5 天：三档同时计收
        rule = BucketRule("liquidity", LIQUIDITY_PARAMS)
        context = make_context(positions=[make_position("AAA", 2.5, 1_000_000)])
        result = rule.apply(context)
        expected = (1_000_000 * 0.8 / 2.5 * 15 / 100
                    + 1_000_000 * 1 / 2.5 * 35 / 100
                    + 1_000_000 * 0.5 / 2.5 * 50 / 100)
        assert result.requirement == pytest.approx(expected)

    def test_below_first_bucket_no_charge(self):
        rule = BucketRule("liquidity", LIQUIDITY_PARAMS)
        context = make_context(positions=[make_position("AAA", 0.1, 1_000_000)])
        assert rule.apply(context).requirement == 0

    def test_index_futures_skipped(self):
        rule = BucketRule("liquidity", LIQUIDITY_PARAMS)
        context = make_context(positions=[make_position("IFX", 2.5, 1_000_000, True)])
        assert rule.apply(context).requirement == 0


class TestSectorRule:
    def test_excess_over_threshold_is_charged(self):
        # 阈值 15% × GMV，增量按 15% 计收
        rule = SectorRule("sector", SECTOR_PARAMS)
        context = make_context(sector_nmv={"Technology": 20_000_000})
        result = rule.apply(context)
        assert result.requirement == pytest.approx(5_000_000 * 15 / 100)

    def test_below_threshold_no_charge(self):
        rule = SectorRule("sector", SECTOR_PARAMS)
        context = make_context(sector_nmv={"Technology": 10_000_000})
        assert rule.apply(context).requirement == 0


class TestRuleEngine:
    def test_disabled_rules_get_zero_results(self):
        # 只启用一条规则：其余已注册规则仍出现在结果里，但要求为 0
        rule_config = {
            "rules": ["initial_requirement"],
            "initial_requirement": INITIAL_PARAMS,
        }
        engine = RuleEngine(rule_config)
        results = engine.run(make_context(gross_market_value=800_000_000))
        assert len(results) == len(REGISTRY)
        assert results["sector"].requirement == 0
        assert results["initial_requirement"].requirement == pytest.approx(800_000_000 * 12.5 / 100)


class TestPortfolioConditionsRule:
    def test_high_grade_excess_charged_at_100_percent(self):
        # High Grade 阈值 2% × GMV；增量部分按 100% 计收
        rule = PortfolioConditionsRule("portfolio_conditions", PORTFOLIO_CONDITIONS_PARAMS)
        context = make_context(issuer_exposure={"AAA": 5_000_000},
                               direct_grade={"AAA": "High Grade"})
        result = rule.apply(context)
        assert result.requirement == pytest.approx(3_000_000)
        assert result.details["issuer_grades"]["AAA"] == "High Grade"

    def test_fallback_grade_by_market_cap(self):
        # 无 direct_grade（仅指数持有）：50 亿市值 → Medium Grade，阈值 1.5%
        rule = PortfolioConditionsRule("portfolio_conditions", PORTFOLIO_CONDITIONS_PARAMS)
        context = make_context(issuer_exposure={"AAA": 2_000_000},
                               securities={"AAA": {"market_cap": 5_000_000_000}})
        result = rule.apply(context)
        assert result.requirement == pytest.approx(500_000)

    def test_below_threshold_no_charge(self):
        rule = PortfolioConditionsRule("portfolio_conditions", PORTFOLIO_CONDITIONS_PARAMS)
        context = make_context(issuer_exposure={"AAA": 1_000_000},
                               direct_grade={"AAA": "High Grade"})
        assert rule.apply(context).requirement == 0
