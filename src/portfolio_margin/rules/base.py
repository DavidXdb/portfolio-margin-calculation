# -*- coding: utf-8 -*-
from dataclasses import dataclass

class RuleResult:
    
    def __init__(self, requirement, details=None):
        self.requirement = requirement
        self.details = details if details is not None else {}

@dataclass
class MarginContext:
    """规则计算所需的全部指标值，由 main.py 算好后一次性组装。"""
    positions: list
    securities: dict
    country_tiers: dict
    gross_market_value: float
    long_short_ratio: float
    net_exposure: float
    country_nmv: dict
    sector_nmv: dict
    issuer_gmv: dict
    issuer_exposure: dict
    direct_lcl: dict
    direct_grade: dict

class Rule:
    """每条规则是一个独立的模块，实现 apply 即可接入引擎。"""
    def __init__(self, name, params):
        # name 是 YAML rules 列表里的名字，params 是该规则的配置小节
        self.name = name
        self.params = params

    def apply(self, context):
        """按 context 里的指标，计算本条规则的保证金要求。"""
        raise NotImplementedError
