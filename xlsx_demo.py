# -*- coding: utf-8 -*-

# 第一步演示：openpyxl 的三个基本动作——创建工作簿、写单元格、保存文件。
import openpyxl

# 创建工作簿：Workbook() 会新建一个 xlsx 工作簿，里面自带一个工作表。
workbook = openpyxl.Workbook()

# 拿到当前工作表并改名。
sheet = workbook.active
sheet.title = "演示"

# 写单元格：row 与 column 都从 1 开始，与 Excel 的行列编号一致。
sheet.cell(row=1, column=1, value="Ticker")
sheet.cell(row=1, column=2, value="Net Exposure")
sheet.cell(row=2, column=1, value="AAPL")
sheet.cell(row=2, column=2, value=15000.0)

# 保存文件：output 目录需已存在。
workbook.save("output/demo.xlsx")
print("已写出 output/demo.xlsx")
