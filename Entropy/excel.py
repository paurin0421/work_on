import pandas as pd

# 파일 경로
excel_path = './2006/GDK_FNL_2006_GF.xls'

# 엑셀 파일 로드
df = pd.read_excel(excel_path)

# 열 이름 출력
print("Column names:", df.columns.tolist())
