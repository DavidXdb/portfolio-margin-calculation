import csv
import openpyxl

def load_positions():
    positions = []
    workbook = openpyxl.load_workbook("examples/portfolio_sample.xlsx")
    sheet = workbook.active
    header = [cell.value for cell in sheet[1]]
    for row in sheet.iter_rows(min_row=2, values_only=True):
        row_dict = dict(zip(header, row))
        # 去掉 Bloomberg 后缀："000001 CH Equity" -> "000001"，"IFBH7 Index" -> "IFBH7"
        row_dict["ticker"] = row_dict["ticker"].split()[0]
        row_dict["price"] = float(row_dict["price"])
        row_dict["quantity"] = int(row_dict["quantity"])
        row_dict["multiplier"] = int(row_dict["multiplier"])
        positions.append(row_dict)
    return positions

def load_securities():
    securities = {}
    with open("data/securities_info.csv", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # 去掉 Bloomberg 后缀；market_cap 含千分位逗号，先去掉再转数字
            row["ticker"] = row["ticker"].split()[0]
            # 跳过数值字段为空的重复行（如 000060 的空行）
            if row["market_cap"].strip() == "" or row["adtv"].strip() == "":
                continue
            row["market_cap"] = float(row["market_cap"].replace(",", ""))
            row["adtv"] = float(row["adtv"])
            securities[row["ticker"]] = row
    return securities

def load_country_tiers():
    """加载国家档位查询字典：{country: tier}。"""
    country_tiers = {}
    with open("data/country_tiers.csv", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            country_tiers[row["country"]] = row["tier"]
    return country_tiers

def enrich_positions(positions, securities):
    
    # 第一部分：证券信息字段与个券指标。
    for position in positions:
        if position["ticker"] in securities:
            ref = securities[position["ticker"]]

            position["country"] = ref["country"]
            position["market_cap"] = ref["market_cap"]
            position["adtv"] = ref["adtv"]
            position["gics_sector"] = ref["gics_sector"]

            # Days of Holdings（持有天数）= 净股数的绝对值 ÷ 日均成交量。
            # 例如：持有 100 股、ADTV 为每天 5000 万股，
            # 全部卖出需要 100 ÷ 50000000 = 0.000002 天。
            days_of_holdings = abs(position["quantity"]) / position["adtv"]
            position["days_of_holdings"] = days_of_holdings

            # 判定 Issuer Grade（发行人等级）。
            market_cap = position["market_cap"]
            if market_cap >= 10_000_000_000 and days_of_holdings < 0.5:
                issuer_grade = "High Grade"
            elif market_cap >= 3_000_000_000 and days_of_holdings < 1:
                issuer_grade = "Medium Grade"
            else:
                issuer_grade = "Low Grade"
            position["issuer_grade"] = issuer_grade

            # 判定是否属于 Large Cap, Liquid Security：
            # 标准：市值大于 100 亿，且持有天数小于 1 天。
            if market_cap > 10_000_000_000 and days_of_holdings < 1:
                large_cap_liquid = True
            else:
                large_cap_liquid = False
            position["large_cap_liquid"] = large_cap_liquid

            print(position["ticker"],
                  "DoH =", days_of_holdings,
                  "Grade =", issuer_grade,
                  "LargeCapLiquid =", large_cap_liquid)
        else:
            # 打印提示：本阶段不会加入指数期货的证券信息。
            print(position["ticker"], "：无证券信息（指数期货，后续按成份拆分处理）")

    print()

    # 第二部分：市值与有向市值。
    for position in positions:

        # 市值 = 当日价格 × 持仓数量 × 标的乘数
        market_value = position["price"] * position["quantity"] * position["multiplier"]

        # 根据头寸方向确定符号：多头 +1，空头 -1
        if position["direction"] == "多头":
            sign = 1
        elif position["direction"] == "空头":
            sign = -1
        else:
            # 方向既不是"多头"也不是"空头"，说明数据有问题。
            raise ValueError("未知的头寸方向：" + position["direction"])

        # 有向市值 = 市值 × 符号
        signed_market_value = market_value * sign

        position["market_value"] = market_value
        position["signed_market_value"] = signed_market_value

        print("市场价值 =", market_value)
        print("有向市值 =", signed_market_value)

    return positions

def decompose_index_futures(positions):
    # 把股指期货持仓按成份权重拆成成份持仓，并返回列表。
    # 读取指数成份文件：每一行是 {index_ticker, ticker, weight}。
    constituents = []
    with open("data/index_constituents.csv", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            row["weight"] = float(row["weight"])
            constituents.append(row)

    # 成份文件里的品种代码集合：{IFB, IFD, FFD}。
    index_tickers = set()
    for constituent in constituents:
        index_tickers.add(constituent["index_ticker"])

    constituent_positions = []
    for position in positions:
        index_ticker = position["ticker"][:3]
        # 标记是否期货持仓：后续计算要跳过期货（期货本身没有证券信息）。
        position["is_index_futures"] = index_ticker in index_tickers
        if not position["is_index_futures"]:
            continue

        # 期货的名义价值 = 价格 × 数量 × 乘数
        index_value = position["price"] * position["quantity"] * position["multiplier"]

        # 该持仓拆分出的成份市值合计。
        split_total = 0
        for constituent in constituents:
            # 只处理属于本品种的成份行。
            if constituent["index_ticker"] != index_ticker:
                continue
            # 成份市值份额 = 名义价值 × 权重；权重是百分数，除以 100 转小数。
            value = index_value * constituent["weight"] / 100
            split_total = split_total + value

            constituent_positions.append({
                "ticker": constituent["ticker"],
                "value": value,
                "direction": position["direction"],
            })

        print(position["ticker"], "名义价值 =", index_value, "成份市值合计 =", round(split_total, 1))

    print("成份持仓总条数 =", len(constituent_positions))
    print()
    return constituent_positions
