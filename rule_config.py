# -*- coding: utf-8 -*-
import yaml

def load_rule_config(path):
    """读取 YAML 规则配置文件，返回配置字典。"""
    with open(path, encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config
