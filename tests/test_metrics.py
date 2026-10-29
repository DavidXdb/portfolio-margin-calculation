# -*- coding: utf-8 -*-
"""metrics.py 中各指标函数的单元测试。"""
import pytest

from pb_margin.metrics import (LongShort_portfolio, compute_long_short_ratio,
                               issuer_exposure, compute_country_nmv, compute_sector_nmv,
                               compute_issuer_gmv, compute_direct_lcl, compute_direct_grade,
                               compute_short_issuer_stress, compute_top_5_requirement,
                               compute_structure_shares)


def test_long_short_portfolio():
    # 多头合计、空头合计、净敞口与总市值
    positions = [
        {"direction": "多头", "signed_market_value": 100},
        {"direction": "空头", "signed_market_value": -40},
        {"direction": "空头", "signed_market_value": -10},
    ]
    long_total, short_total, net_exposure, gross_market_value = LongShort_portfolio(positions)
    assert long_total == 100
    assert short_total == -50
    assert net_exposure == 50
    assert gross_market_value == 150


def test_long_short_ratio():
    # 比率 = 多头合计 ÷ |空头合计|
    assert compute_long_short_ratio(100, -50) == pytest.approx(2.0)


def test_issuer_exposure_aggregation():
    # 直接持仓与指数成份持仓按发行人聚合净敞口；缺失的一侧补 0
    positions = [
        {"ticker": "AAA", "is_index_futures": False, "signed_market_value": 100},
        {"ticker": "BBB", "is_index_futures": False, "signed_market_value": -60},
    ]
    constituents = [
        {"ticker": "AAA", "value": 30, "direction": "多头"},
        {"ticker": "CCC", "value": 20, "direction": "空头"},
    ]
    net, direct, index = issuer_exposure(positions, constituents)
    assert net == {"AAA": 130, "BBB": -60, "CCC": -20}
    assert direct == {"AAA": 100, "BBB": -60, "CCC": 0}
    # 成份持仓敞口存的是有向市值：空头成份为负数
    assert index == {"AAA": 30, "BBB": 0, "CCC": -20}


def test_country_and_sector_nmv():
    exposure = {"AAA": 100, "BBB": -60}
    securities = {"AAA": {"country": "USA", "gics_sector": "Technology"},
                  "BBB": {"country": "China", "gics_sector": "Technology"}}
    assert compute_country_nmv(exposure, securities) == {"USA": 100, "China": -60}
    assert compute_sector_nmv(exposure, securities) == {"Technology": 40}


def test_issuer_gmv():
    # 直接持仓取 |有向市值|，成份持仓取拆分市值
    positions = [{"ticker": "AAA", "is_index_futures": False, "signed_market_value": -100}]
    constituents = [{"ticker": "AAA", "value": 30}]
    assert compute_issuer_gmv(positions, constituents) == {"AAA": 130}


def test_direct_lookup_tables():
    # 查询表只收直接持仓，跳过指数期货
    positions = [
        {"ticker": "AAA", "is_index_futures": False,
         "large_cap_liquid": True, "issuer_grade": "High Grade"},
        {"ticker": "IFX", "is_index_futures": True,
         "large_cap_liquid": False, "issuer_grade": "Low Grade"},
    ]
    assert compute_direct_lcl(positions) == {"AAA": True}
    assert compute_direct_grade(positions) == {"AAA": "High Grade"}


def test_short_issuer_stress_grid():
    # 按市值档位确定压力百分比：5000 万 → 1000%，1.5 亿 → 750%，250 亿 → 100%
    securities = {
        "AAA": {"market_cap": 50_000_000},
        "BBB": {"market_cap": 150_000_000},
        "CCC": {"market_cap": 25_000_000_000},
        "DDD": {"market_cap": 150_000_000},
    }
    exposure = {"AAA": -10_000_000, "BBB": -10_000_000,
                "CCC": -10_000_000, "DDD": 10_000_000}
    largest = compute_short_issuer_stress(exposure, securities)
    # 最大损失来自 AAA：10,000,000 × 1000%
    assert largest == pytest.approx(10_000_000 * 1000 / 100)


def test_top_5_requirement():
    # 六个发行人，取 |净敞口| × 50% 最大的 5 个求和
    exposure = {"A": 10, "B": 20, "C": 30, "D": 40, "E": 50, "F": 60}
    top_5, losses = compute_top_5_requirement(exposure)
    assert top_5 == pytest.approx(30 + 25 + 20 + 15 + 10)
    assert len(losses) == 6


def test_structure_shares():
    # 各小组 GMV 占总市值的百分比，保留两位小数
    shares = compute_structure_shares(
        largest_sector_gmv=300, largest_country_gmv=400,
        tier_gmv={"Tier 1": 500, "Tier 2": 200},
        lcl_gmv=100, liquid_gmv=50, gross_market_value=1000)
    sector_share, country_share, tier1_share, tier2_share, lcl_share, liquid_share = shares
    assert sector_share == 30.0
    assert country_share == 40.0
    assert tier1_share == 50.0
    assert tier2_share == 20.0
    assert lcl_share == 10.0
    assert liquid_share == 5.0
