# -*- coding: utf-8 -*-
"""端到端回归测试：完整运行一次程序，核对关键结果与基线一致。"""
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from rule_config import load_rule_config

# 项目根目录：tests/ 的上一级
ROOT = Path(__file__).resolve().parent.parent

ALL_RULES = ["initial_requirement", "single_country", "aggregate_country",
             "liquidity", "sector", "portfolio_conditions"]


def test_full_run_matches_baseline():
    # 与命令行 python3 main.py 完全相同的完整运行
    result = subprocess.run(["python3", "main.py"], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0

    # 报告文件刚被本次运行重新生成
    tex = (ROOT / "report.tex").read_text(encoding="utf-8")

    # 基线数值：2026-10-29 重构前版本（commit 01bc437）的验证结果
    assert "Base Margin: & 34,138,688.42 \\\\" in tex
    assert "Total Margin Requirement: & 34,138,688.42 \\\\" in tex

    # 控制台关键数值与基线一致
    assert "Top 5 要求 = 2167313.5116" in result.stdout
    assert "最大 Short Issuer Stress 损失 = 928356.6600000001" in result.stdout
    assert "Portfolio Conditions 合计 = 0" in result.stdout


@pytest.mark.parametrize("rule_name", ALL_RULES)
def test_program_runs_with_rule_disabled(rule_name, tmp_path):
    # 复制配置并删掉一条规则，写到临时文件
    config = load_rule_config(ROOT / "configs" / "jpm_margin_v2024.yaml")
    config["rules"] = [r for r in config["rules"] if r != rule_name]
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, sort_keys=False)

    # 通过环境变量让程序使用这份临时配置，其余与正常完整运行相同
    env = {**os.environ, "PB_RULE_CONFIG": str(config_path)}
    result = subprocess.run(["python3", "main.py"], cwd=ROOT,
                            capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "Traceback" not in result.stderr
    assert (ROOT / "report.tex").exists()
