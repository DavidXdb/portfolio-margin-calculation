# -*- coding: utf-8 -*-
"""端到端回归测试：完整运行一次程序，核对关键结果与基线一致。"""
import subprocess
from pathlib import Path

# 项目根目录：tests/ 的上一级
ROOT = Path(__file__).resolve().parent.parent


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
