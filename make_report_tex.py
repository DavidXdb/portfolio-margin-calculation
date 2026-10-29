# -*- coding: utf-8 -*-

# 报告生成脚本：运行后生成 report.tex，再用 pdflatex 编译成 PDF。

def write_report_tex(positions, long_total, short_total, net_exposure, gross_market_value, long_short_ratio, largest_sector, sector_share, largest_country, country_share, tier1_share, tier2_share, lcl_share, liquid_share, initial_requirement_part_a, initial_requirement_part_b, country_nmv, country_threshold_amounts, country_requirements, single_country_requirement, aggregate_country_requirement, liquidity_requirement, sector_nmv, sector_requirements, sector_requirement, section_a, issuer_exposure, largest_short_stress, stress_losses, top_5_requirement, base_margin_requirement, portfolio_conditions_requirement, total_margin_requirement):
    """接收组合数据，生成 LaTeX 报告文本并写出 report.tex。"""

    # 用列表逐行存放报告内容，最后一次性写入文件。
    report_lines = []

    # 文档头：文档类、字体编码、标题、正文环境开始。
    report_lines.append(r"\documentclass{article}")
    # T1 字体编码：让 < 与 > 能直接书写（默认编码会把它们渲染成其他符号）。
    report_lines.append(r"\usepackage[T1]{fontenc}")

    # geometry 宏包：用 margin 参数统一设置页边距（默认页边距较宽，正文区域偏小）。
    report_lines.append(r"\usepackage[margin=2cm]{geometry}")

    # booktabs 宏包：提供 \addlinespace，用于在表格行之间插入竖直间距。
    report_lines.append(r"\usepackage{booktabs}")

    report_lines.append("")
    report_lines.append(r"\title{PB Margin Report}")
    report_lines.append(r"\author{PB Margin Calculator}")
    report_lines.append(r"\date{\today}")
    report_lines.append("")
    report_lines.append(r"\begin{document}")
    report_lines.append(r"\maketitle")
    report_lines.append("")

    # Counterparty 与 I、II 两节。
    report_lines.append(f"Counterparty: {positions[0]['counterparty']}")
    report_lines.append("")

    report_lines.append(r"\section*{I. Portfolio Overview}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")

    # 表格行包含 \\（LaTeX 换行符）：必须用 r 字符串——普通字符串里 \\ 只等于一个反斜杠。
    # f-string 与 r 可以合并成 rf-string；{值:,.2f} 给数字加千分位逗号并保留两位小数。
    report_lines.append(rf"Number of Positions: & {len(positions):,.2f} \\")
    report_lines.append(rf"Long Market Value: & {long_total:,.2f} \\")
    report_lines.append(rf"Short Market Value: & {short_total:,.2f} \\")
    report_lines.append(rf"Net Market Value (NMV): & {net_exposure:,.2f} \\")
    report_lines.append(rf"Gross Market Value (GMV): & {gross_market_value:,.2f} \\")
    report_lines.append(rf"Long/Short Ratio: & {long_short_ratio:,.2f} \\")

    report_lines.append(r"\end{tabular}")
    report_lines.append("")

    report_lines.append(r"\section*{II. Position Structure}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    # 行业英文名可能含 &，而 & 在 LaTeX 表格里是列分隔符，需要先转义。
    report_lines.append(rf"Largest Sector: & {largest_sector.replace('&', r'\&')} \\")
    report_lines.append(rf"Largest Sector GMV Share: & {sector_share:,.2f} \% \\")
    report_lines.append(rf"Largest Country: & {largest_country} \\")
    report_lines.append(rf"Largest Country GMV Share: & {country_share:,.2f} \% \\")
    report_lines.append(rf"Tier 1 GMV Share: & {tier1_share:,.2f} \% \\")
    report_lines.append(rf"Tier 2 GMV Share: & {tier2_share:,.2f} \% \\")
    report_lines.append(rf"Large Cap Liquid security share (GMV): & {lcl_share:,.2f} \% \\")
    report_lines.append(rf"days of holding < 0.2 security share (GMV): & {liquid_share:,.2f} \% \\")
    report_lines.append(r"\end{tabular}")

    report_lines.append("")
    report_lines.append(r"\bigskip")

    report_lines.append(r"\noindent\textit{\small The list of Tier 1/Tier 2 countries could be found in the Morgan Stanley Margin Rule.}")

    report_lines.append("")

    # III、IV 两节：逐行明细已写入 xlsx，这里只保留标题与指引。
    report_lines.append(r"\section*{III. Security-Level Metrics}")

    report_lines.append(r"See issuer\_details.xlsx.")
    report_lines.append("")
    report_lines.append(r"\section*{IV. Issuer Exposures}")
    report_lines.append(r"See issuer\_details.xlsx.")

    report_lines.append("")

    # V 节：保证金计算明细。
    report_lines.append(r"\section*{V. Margin Calculation}")
    report_lines.append("")

    report_lines.append(r"\subsection*{1. Section A}")

    # 第二轮修订：标签改名；千分位分隔符；内容与注释之间用 \medskip 留空；d) 只报告持有天数大于 0.2 的持仓。
    # 第三轮修正：每条规则行之后加空行（结束段落），否则 \medskip 会把下一标题并进同一段落；e) 规则行从中分行。
    report_lines.append(r"\textbf{a) Excess GMV charge}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    report_lines.append(rf"Portfolio GMV: & {gross_market_value:,.2f} \\")
    report_lines.append(rf"Margin requirement: & {initial_requirement_part_a:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    # 说明句随真实数据变化：GMV 未超 10 亿整体按 12.5%，超出部分按 35%。
    if gross_market_value <= 1_000_000_000:
        report_lines.append(r"\noindent\textit{\small GMV less than \$1,000,000,000 -> 12.5\% charge on full GMV}")
    else:
        report_lines.append(r"\noindent\textit{\small first 1,000,000,000 at 12.5\% + excess at 35\%}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    report_lines.append(r"\textbf{b) Long/Short Ratio}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    report_lines.append(rf"Long/Short Ratio: & {long_short_ratio:,.2f} \\")
    report_lines.append(rf"Margin requirement: & {initial_requirement_part_b:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    # 说明句随真实数据变化：比率在 [0.95, 1.05] 内不计费，区间外按 |NMV| 的 20%。
    if long_short_ratio > 1.05 or long_short_ratio < 0.95:
        report_lines.append(r"\noindent\textit{\small Ratio outside [0.95, 1.05] -> 20\% on |NMV|}")
    else:
        report_lines.append(r"\noindent\textit{\small Ratio within [0.95, 1.05] -> 0}")
    report_lines.append("")
    report_lines.append(r"\bigskip")

    # c) Country Additional
    report_lines.append(r"\textbf{c) Country Additional}")
    report_lines.append("")

    # 新增次级小标题
    report_lines.append(r"\textit{Margin Requirement for sub-portfolio in a single country}")
    report_lines.append("")

    report_lines.append(r"\begin{tabular}{l r}")
    # 每个国家输出三行（净敞口、阈值、要求），国家之间用 \addlinespace 留间距。
    for country, nmv in country_nmv.items():
        report_lines.append(rf"Portfolio NMV ({country}): & {nmv:,.2f} \\")
        report_lines.append(rf"Portfolio GMV threshold ({country}): & {country_threshold_amounts[country]:,.2f} \\")
        report_lines.append(rf"Margin requirement ({country}): & {country_requirements[country]:,.2f} \\")
        report_lines.append(r"\addlinespace")
    report_lines.append(rf"Margin requirement (Aggregate country condition): & {aggregate_country_requirement:,.2f} \\")
    report_lines.append(r"\addlinespace")
    # 合计 = 单一国家要求 + 国家等级对应保证金
    country_additional_total = single_country_requirement + aggregate_country_requirement
    report_lines.append(rf"Total Margin requirement: & {country_additional_total:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")

    # 替换原 Single-country 注释为 Aggregate country condition 说明
    report_lines.append(r"\noindent\textit{\small Aggregate country condition: The GMV attributable to Tier 2 countries will receive a 2.5\% requirement; Tier 1 not charged.}")
    report_lines.append("")
    report_lines.append(r"\bigskip")

    # d) Liquidity Additional
    report_lines.append(r"\textbf{d) Liquidity Additional}")
    report_lines.append("")
    # 收集持有天数超过 0.2 的持仓（股指期货除外，它不是个股）。
    illiquid_positions = []
    for position in positions:
        if position["is_index_futures"]:
            continue
        if position["days_of_holdings"] > 0.2:
            illiquid_positions.append(position)

    # 没有超过 0.2 的持仓：只输出一句话；否则逐个列出持仓的持有天数与费用。
    if len(illiquid_positions) == 0:
        report_lines.append("All securities in the portfolio are less than 0.2 days of holding.")
        report_lines.append("")
        report_lines.append(r"\begin{tabular}{l r}")
        report_lines.append(rf"Total Margin requirement: & {liquidity_requirement:,.2f} \\")
        report_lines.append(r"\end{tabular}")
    else:
        report_lines.append(r"\begin{tabular}{l r}")
        for position in illiquid_positions:
            report_lines.append(rf"{position['ticker']} Days of Holding: & {position['days_of_holdings']:.9f} \\")
            report_lines.append(rf"{position['ticker']} liquidity charge: & {position['liquidity_charge']:,.2f} \\")
        report_lines.append(r"\addlinespace")
        report_lines.append(rf"Total Margin requirement: & {liquidity_requirement:,.2f} \\")
        report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    report_lines.append(r"\noindent\textit{\small Days of holding beyond 0.2 charged 15\% (up to 1 day), beyond 1 charged 35\% (up to 2), beyond 2 charged 50\% (up to 3); bands apply independently}")
    report_lines.append("")
    report_lines.append(r"\bigskip")

    # e) Sector Additional
    report_lines.append(r"\textbf{e) Sector Additional}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    # 阈值与控制台一致：GMV 的 15%。
    sector_threshold = 15 / 100 * gross_market_value
    report_lines.append(rf"Sector GMV threshold: & {sector_threshold:,.2f} \\")
    report_lines.append(r"\addlinespace")
    # 每个行业输出两行（净敞口、要求）；行业名已是英文，直接使用。
    for sector, nmv in sector_nmv.items():
        sector_en = sector.replace("&", r"\&")
        report_lines.append(rf"{sector_en} Sector NMV: & {nmv:,.2f} \\")
        report_lines.append(rf"{sector_en} Sector Margin: & {sector_requirements[sector]:,.2f} \\")
    report_lines.append(r"\addlinespace")
    report_lines.append(rf"Total Margin requirement: & {sector_requirement:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    report_lines.append(r"\noindent\textit{\small Single GICS sector |NMV| above 15\% of GMV charged 15\% on excess}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    report_lines.append(r"\textbf{Section A Total}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    report_lines.append(rf"Margin requirement: & {section_a:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")

    report_lines.append(r"\subsection*{2. Short Issuer Stress}")

    # 统计净空头发行人数量（净敞口为负）。
    net_short_count = 0
    for ticker, net in issuer_exposure.items():
        if net < 0:
            net_short_count = net_short_count + 1

    # 没有净空头发行人：只输出一句话；否则逐个列出净敞口。
    if net_short_count == 0:
        report_lines.append("No net-short issuers")
        report_lines.append("")
    else:
        report_lines.append(r"\begin{tabular}{l r}")
        for ticker, net in issuer_exposure.items():
            if net < 0:
                report_lines.append(rf"{ticker} net exposure: & {net:,.2f} \\")
        report_lines.append(r"\end{tabular}")
        report_lines.append("")

    # 合计表格两个分支共用：if/else 之后的行，无论走哪个分支都会执行。
    report_lines.append(r"\begin{tabular}{l r}")
    report_lines.append(rf"Margin requirement: & {largest_short_stress:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")

    # 3. Top 5 Requirement
    report_lines.append(r"\subsection*{3. Top 5 Requirement}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    # stress_losses 已按损失从大到小排序，取前 5 个逐一输出；round 去掉乘法产生的浮点尾差。
    for loss, ticker in stress_losses[:5]:
        report_lines.append(rf"{ticker} stress loss: & {loss:,.2f} \\")
    report_lines.append(r"\addlinespace")
    report_lines.append(rf"Total margin requirement: & {top_5_requirement:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    report_lines.append(r"\noindent\textit{\small Each issuer stressed by |exposure| x 50\%; margin requirement = sum of the 5 largest losses}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    report_lines.append(r"\textbf{Base Margin Requirement}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    report_lines.append(rf"Margin requirement: & {base_margin_requirement:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    report_lines.append(r"\noindent\textit{\small Base margin = max of Section A, Short Issuer Stress, Top 5}")
    report_lines.append("")
    report_lines.append(r"\bigskip")

    # 4. Portfolio Conditions
    report_lines.append(r"\subsection*{4. Portfolio Conditions}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    report_lines.append(rf"Margin requirement: & {portfolio_conditions_requirement:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")
    report_lines.append(r"\bigskip")

    # 替换 Portfolio Conditions 注释
    report_lines.append(r"\noindent\textit{\small The absolute value of the Issuer Exposure of different grade Issuer should be less than different threshold \% of GMV. Excess will be charged 100\% margin. (Threshold \% of GMV: High Grade 2\%, Medium 1.5\%, Low 0.8\%. Definitions of High/Medium/Low Grade Issuer could be found the in the MS Margin Rule)}")
    report_lines.append("")
    report_lines.append(r"\bigskip")
    report_lines.append(r"Per-issuer detail: see issuer\_details.xlsx.")
    report_lines.append("")


    # VI、VII 两节与文档结尾。
    report_lines.append(r"\section*{VI. Total Margin Requirement}")
    report_lines.append("")
    report_lines.append(r"\begin{tabular}{l r}")
    report_lines.append(rf"Base Margin: & {base_margin_requirement:,.2f} \\")
    report_lines.append(rf"Portfolio Conditions: & {portfolio_conditions_requirement:,.2f} \\")
    report_lines.append(rf"Total Margin Requirement: & {total_margin_requirement:,.2f} \\")
    report_lines.append(r"\end{tabular}")
    report_lines.append("")

    report_lines.append(r"\section*{VII. Assumptions}")
    report_lines.append("")
    report_lines.append(r"- Sample portfolio data is fictional")

    report_lines.append(r"- Index futures positions decomposed into their index constituents")
    report_lines.append(r"- Constituent-only issuers: DoH approximated as 0 (no price data)")

    report_lines.append("")
    report_lines.append(r"\end{document}")

    # 列表转整篇文本："\n".join 把各行用换行符连起来，再写入文件。
    report_text = "\n".join(report_lines)
    with open("report.tex", "w", encoding="utf-8") as file:
        file.write(report_text)

    print("已写出 report.tex")
