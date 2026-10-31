# -*- coding: utf-8 -*-
"""配置文件与规则注册表的一致性测试。"""
from pathlib import Path

from portfolio_margin.rule_config import load_rule_config
from portfolio_margin.rules.engine import REGISTRY

# 项目根目录：tests/ 的上一级
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "ms_margin_v2024.yaml"


def test_config_loads():
    config = load_rule_config(CONFIG_PATH)
    assert config["version"] == "ms_margin_v2024"
    assert isinstance(config["rules"], list)


def test_rules_list_matches_registry():
    # 默认配置应启用注册表里的全部规则
    config = load_rule_config(CONFIG_PATH)
    assert sorted(config["rules"]) == sorted(REGISTRY)


def test_enabled_rules_have_params():
    # rules 列表里的每条规则都要有对应的参数小节
    config = load_rule_config(CONFIG_PATH)
    for rule_name in config["rules"]:
        assert rule_name in config, "缺少参数小节：" + rule_name
        assert isinstance(config[rule_name], dict)


def test_no_duplicate_rules():
    config = load_rule_config(CONFIG_PATH)
    rules = config["rules"]
    assert len(set(rules)) == len(rules)
