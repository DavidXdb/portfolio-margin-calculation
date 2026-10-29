# -*- coding: utf-8 -*-
from rules.base import Rule, RuleResult

class BucketRule(Rule):
    """流动性要求：按持有天数分档，对"超过档位下限天数"的市值部分计收保证金。
    分档与费率见配置文件 liquidity.buckets。各档独立判断：持有 2.5 天时三档同时计收。
    成份持仓本步暂不处理。"""
    def apply(self, context):
        liquidity_requirement = 0
        for position in context.positions:
            if position["is_index_futures"]:
                continue

            days_of_holdings = position["days_of_holdings"]
            market_value = position["market_value"]

            charge = 0
            # 各档独立判断：持有天数超过档位下限的部分，按该档费率计收。
            for bucket in self.params["buckets"]:
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

        return RuleResult(liquidity_requirement)
