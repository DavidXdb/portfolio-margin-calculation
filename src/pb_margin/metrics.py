def LongShort_portfolio(positions):
    """累加多空合计，计算净敞口与总市值，并打印组合合计。"""
    # 两个累加变量，用来存放"多头合计"和"空头合计"。
    # 累加变量的初始值是 0，之后在循环中不断把新数值加进去。
    long_total = 0
    short_total = 0

    for position in positions:
        # 按方向累加：多头加进 long_total，空头加进 short_total。
        if position["direction"] == "多头":
            long_total = long_total + position["signed_market_value"]
        else:
            short_total = short_total + position["signed_market_value"]

    print()
    print("多头合计 =", long_total)
    print("空头合计 =", short_total)

    # 净敞口 = 多头合计 + 空头合计。
    # 因为空头合计本身是负数，两者相加就是"多空相抵"。
    net_exposure = long_total + short_total

    print("净敞口 =", net_exposure)

    # 总市值 = 多头合计的绝对值 + 空头合计的绝对值。
    # abs() 是 Python 内置函数，用来取绝对值。
    # 总市值不冲抵：多空两侧取绝对值相加。
    gross_market_value = abs(long_total) + abs(short_total)

    print("总市值 =", gross_market_value)

    return long_total, short_total, net_exposure, gross_market_value

def compute_long_short_ratio(long_total, short_total):
    """Long/Short 比率 = 多头总市值 ÷ 空头总市值。"""
    # 空头合计存的是带符号的负数，这里用 abs() 转成正数再相除。
    return long_total / abs(short_total)

def issuer_exposure(positions, constituent_positions):
    """按发行人聚合三类敞口：合并净敞口、直接持仓敞口、指数成份持仓敞口。"""
    issuer_exposure = {}
    # 直接持仓敞口：发行人在直接持仓中的有向市值之和。
    direct_holding_exposure = {}
    # 指数成份持仓敞口：发行人在指数成份拆分持仓中的有向市值之和。
    index_holding_exposure = {}

    # 先加直接持仓（股指期货除外，它已由成份持仓代表）。
    for position in positions:
        if position["is_index_futures"]:
            continue
        ticker = position["ticker"]
        if ticker not in issuer_exposure:
            issuer_exposure[ticker] = 0
        issuer_exposure[ticker] = issuer_exposure[ticker] + position["signed_market_value"]

        if ticker not in direct_holding_exposure:
            direct_holding_exposure[ticker] = 0
        direct_holding_exposure[ticker] = direct_holding_exposure[ticker] + position["signed_market_value"]

    # 再加成份持仓（方向与 ES 持仓一致）。
    for constituent_position in constituent_positions:
        ticker = constituent_position["ticker"]
        if constituent_position["direction"] == "多头":
            signed_value = constituent_position["value"]
        else:
            signed_value = -constituent_position["value"]

        if ticker not in issuer_exposure:
            issuer_exposure[ticker] = 0
        issuer_exposure[ticker] = issuer_exposure[ticker] + signed_value

        if ticker not in index_holding_exposure:
            index_holding_exposure[ticker] = 0
        index_holding_exposure[ticker] = index_holding_exposure[ticker] + signed_value

    # 补全键：只在直接或只在成份中出现的 ticker，在另一侧补 0。
    for ticker in issuer_exposure:
        if ticker not in direct_holding_exposure:
            direct_holding_exposure[ticker] = 0
        if ticker not in index_holding_exposure:
            index_holding_exposure[ticker] = 0

    # 打印每个发行人的净敞口，并累加验证。
    total = 0
    for ticker, net in issuer_exposure.items():
        print(ticker, "净敞口 =", net)
        total = total + net

    print("发行人净敞口合计 =", total)
    print()

    return issuer_exposure, direct_holding_exposure, index_holding_exposure

def compute_country_nmv(issuer_exposure, securities):
    """按国家汇总净敞口：{country: 该国发行人净有向市值之和}。"""
    country_nmv = {}
    for ticker, net in issuer_exposure.items():
        country = securities[ticker]["country"]
        if country not in country_nmv:
            country_nmv[country] = 0
        country_nmv[country] = country_nmv[country] + net
    return country_nmv

def compute_sector_nmv(issuer_exposure, securities):
    """按 GICS 行业汇总净敞口：{行业: 该行业发行人净有向市值之和}。"""
    sector_nmv = {}
    for ticker, net in issuer_exposure.items():
        sector = securities[ticker]["gics_sector"]
        if sector not in sector_nmv:
            sector_nmv[sector] = 0
        sector_nmv[sector] = sector_nmv[sector] + net
    return sector_nmv

def compute_issuer_gmv(positions, constituent_positions):
    """发行人总市值归集：直接持仓与成份持仓按 |市值| 相加。"""
    issuer_gmv = {}
    for position in positions:
        if position["is_index_futures"]:
            continue
        ticker = position["ticker"]
        if ticker not in issuer_gmv:
            issuer_gmv[ticker] = 0
        issuer_gmv[ticker] = issuer_gmv[ticker] + abs(position["signed_market_value"])

    for constituent_position in constituent_positions:
        ticker = constituent_position["ticker"]
        if ticker not in issuer_gmv:
            issuer_gmv[ticker] = 0
        issuer_gmv[ticker] = issuer_gmv[ticker] + constituent_position["value"]

    # 验证：归集合计应等于组合总市值
    gmv_total = 0
    for ticker, gmv in issuer_gmv.items():
        gmv_total = gmv_total + gmv
    print("发行人总市值归集合计 =", gmv_total)

    return issuer_gmv

def compute_direct_lcl(positions):
    """有直接持仓的股票所属的发行人的 LCL 标志查询表：{ticker: large_cap_liquid}。"""
    direct_lcl = {}
    for position in positions:
        if position["is_index_futures"]:
            continue
        direct_lcl[position["ticker"]] = position["large_cap_liquid"]
    return direct_lcl

def compute_direct_grade(positions):
    """有直接持仓的股票所属的发行人的等级查询表：{ticker: issuer_grade}。"""
    direct_grade = {}
    for position in positions:
        if position["is_index_futures"]:
            continue
        direct_grade[position["ticker"]] = position["issuer_grade"]
    return direct_grade

def compute_issuer_report_metrics(positions, issuer_gmv, securities):
    """报告所需的发行人级指标：LCL 标志与持有天数。"""
    issuer_lcl_flags = {}
    issuer_dohs = {}
    for position in positions:
        if position["is_index_futures"]:
            continue
        issuer_lcl_flags[position["ticker"]] = position["large_cap_liquid"]
        issuer_dohs[position["ticker"]] = position["days_of_holdings"]

    for ticker in issuer_gmv:
        if ticker not in issuer_lcl_flags:
            # 对于仅通过指数持有的发行人：持有天数doh近似为 0，LCL 仅按市值判定
            market_cap = securities[ticker]["market_cap"]
            issuer_lcl_flags[ticker] = market_cap > 10_000_000_000
            issuer_dohs[ticker] = 0

    return issuer_lcl_flags, issuer_dohs

def compute_portfolio_structure(issuer_gmv, securities, country_tiers, issuer_lcl_flags, issuer_dohs):
    """报告所需的组合结构聚合值：最大行业及其总市值、最大国家及其总市值、档位总市值、LCL 总市值与 DoH < 0.2 总市值。"""
    # 投资组合中的各个行业总市值，并找最大行业
    sector_gmv = {}
    for ticker, gmv in issuer_gmv.items():
        sector = securities[ticker]["gics_sector"]
        if sector not in sector_gmv:
            sector_gmv[sector] = 0
        sector_gmv[sector] = sector_gmv[sector] + gmv

    largest_sector = ""
    largest_sector_gmv = 0
    for sector, gmv in sector_gmv.items():
        if gmv > largest_sector_gmv:
            largest_sector_gmv = gmv
            largest_sector = sector

    # 国家总市值，并找最大国家
    country_gmv = {}
    for ticker, gmv in issuer_gmv.items():
        country = securities[ticker]["country"]
        if country not in country_gmv:
            country_gmv[country] = 0
        country_gmv[country] = country_gmv[country] + gmv

    largest_country = ""
    largest_country_gmv = 0
    for country, gmv in country_gmv.items():
        if gmv > largest_country_gmv:
            largest_country_gmv = gmv
            largest_country = country

    # 按国家档位归集总市值
    tier_gmv = {}
    for country, gmv in country_gmv.items():
        tier = country_tiers[country]
        if tier not in tier_gmv:
            tier_gmv[tier] = 0
        tier_gmv[tier] = tier_gmv[tier] + gmv

    # 属于LCL 的总市值与 DoH < 0.2 的总市值
    lcl_gmv = 0
    liquid_gmv = 0
    for ticker, gmv in issuer_gmv.items():
        if issuer_lcl_flags[ticker]:
            lcl_gmv = lcl_gmv + gmv
        if issuer_dohs[ticker] < 0.2:
            liquid_gmv = liquid_gmv + gmv

    return largest_sector, largest_sector_gmv, largest_country, largest_country_gmv, tier_gmv, lcl_gmv, liquid_gmv

def compute_structure_shares(largest_sector_gmv, largest_country_gmv, tier_gmv, lcl_gmv, liquid_gmv, gross_market_value):
    """报告所需的组合结构份额：各特殊小组的 GMV 占总体的百分比（保留两位小数）。"""
    # 计算每个特殊小组的GMV占总体的比例，round(x, 2) 保留两位小数
    sector_share = round(largest_sector_gmv / gross_market_value * 100, 2)
    country_share = round(largest_country_gmv / gross_market_value * 100, 2)
    tier1_share = round(tier_gmv.get("Tier 1", 0) / gross_market_value * 100, 2)
    tier2_share = round(tier_gmv.get("Tier 2", 0) / gross_market_value * 100, 2)
    lcl_share = round(lcl_gmv / gross_market_value * 100, 2)
    liquid_share = round(liquid_gmv / gross_market_value * 100, 2)

    return sector_share, country_share, tier1_share, tier2_share, lcl_share, liquid_share

def compute_short_issuer_stress(issuer_exposure, securities):
    """Short Issuer Stress：按市值档位对净空头发行人施压，返回最大压力损失。"""
    largest_short_stress = 0

    for ticker, net in issuer_exposure.items():
        if net < 0:
            # 查该发行人的市值（证券信息在加载时已转为数字）
            market_cap = securities[ticker]["market_cap"]

            # 按市值档位确定压力百分比 Y
            if market_cap < 100_000_000:          # 小于 1 亿
                stress = 1000
            elif market_cap < 250_000_000:        # 1 亿（含）到 2.5 亿
                stress = 750
            elif market_cap < 5_000_000_000:      # 2.5 亿（含）到 50 亿
                stress = 500
            elif market_cap < 10_000_000_000:     # 50 亿（含）到 100 亿
                stress = 300
            elif market_cap < 15_000_000_000:     # 100 亿（含）到 150 亿
                stress = 200
            elif market_cap < 20_000_000_000:     # 150 亿（含）到 200 亿
                stress = 150
            else:                                 # 200 亿及以上
                stress = 100

            # 压力损失 = |净空头市值| × Y / 100
            loss = abs(net) * stress / 100

            print(ticker, "净空头市值 =", net, "压力 =", stress, "% 损失 =", loss)

            # 与目前的最大值比较，更大就替换
            if loss > largest_short_stress:
                largest_short_stress = loss

    print("最大 Short Issuer Stress 损失 =", largest_short_stress)
    print()

    return largest_short_stress

def compute_top_5_requirement(issuer_exposure):
    """Top 5 要求：对每个发行人做 ±50% 独立压力测试，取损失最大的 5 个求和。"""
    stress_losses = []
    for ticker, net in issuer_exposure.items():
        loss = abs(net) * 0.5
        # 元组 (损失, ticker)：损失放在前面，便于排序
        stress_losses.append((loss, ticker))

    # sort(reverse=True)：从大到小排序。
    # 元组排序先比第一个元素（损失），损失相同时再比 ticker。
    stress_losses.sort(reverse=True)

    # 切片 [:5] 取前 5 个；不足 5 个时取全部
    top_5_requirement = 0
    for loss, ticker in stress_losses[:5]:
        print(ticker, "压力损失 =", loss)
        top_5_requirement = top_5_requirement + loss

    print("Top 5 要求 =", top_5_requirement)
    print()

    return top_5_requirement, stress_losses
