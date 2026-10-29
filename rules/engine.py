# -*- coding: utf-8 -*-
from rules.base import RuleResult
from rules.bucket_rule import BucketRule
from rules.policy_rules import (InitialRequirementRule, SingleCountryRule,
                                AggregateCountryRule, SectorRule, PortfolioConditionsRule)

# 规则注册表：YAML rules 列表里的名字 → 规则类。
# 新增规则：写一个 Rule 子类，在这里注册一行，再到 YAML 的 rules 列表里启用。
REGISTRY = {
    "initial_requirement": InitialRequirementRule,
    "single_country": SingleCountryRule,
    "aggregate_country": AggregateCountryRule,
    "liquidity": BucketRule,
    "sector": SectorRule,
    "portfolio_conditions": PortfolioConditionsRule,
}

class RuleEngine:
    """规则引擎：按 YAML rules 列表的顺序创建并执行启用的规则。"""
    def __init__(self, rule_config):
        self.rules = []
        for rule_name in rule_config["rules"]:
            rule_class = REGISTRY[rule_name]
            # 每条规则拿到自己的配置小节：rule_config[rule_name]
            self.rules.append(rule_class(rule_name, rule_config[rule_name]))

    def run(self, context):
        """按启用顺序执行全部规则，返回 {规则名: RuleResult}。"""
        # 已注册但未启用的规则先填零结果，停用规则时下游取值不报错。
        results = {rule_name: RuleResult(0) for rule_name in REGISTRY}
        for rule in self.rules:
            results[rule.name] = rule.apply(context)
        return results
