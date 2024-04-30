import pandas as pd
from scipy.io import loadmat
import numpy as np
from datetime import datetime, timedelta

# 설정
year = 2006
dir_path = 'E:/Matlab/work_on/Entropy'  # 절대 경로 사용

# 파일 로드: ExcelFile 객체 사용하여 모든 시트에 접근 가능하게 설정
xlsx = pd.ExcelFile(f'{dir_path}/{year}/GDK_FNL_{year}_GF.xls')

# .mat 파일 로드
mat_data = loadmat(f'{dir_path}/{year}/GDK_{year}_L2.mat')

# 열 이름 매핑 설정
column_mappings = {
    'Timestamp': 'Timestamp',
    'RSDN': 'RSDN',
    'RSUP': 'RSUP',
    'RLDN': 'RLDN',
    'RLUP': 'RLUP',
    'T_AIR': 'T_AIR',
    'PPT': 'PPT'
}

# 시트별 처리
for sheet_name in xlsx.sheet_names:
    print(f"Processing sheet: {sheet_name}")
    df = pd.read_excel(xlsx, sheet_name=sheet_name, header=0)  # 첫 행을 헤더로 사용
    units = df.iloc[0]  # 단위 행 추출
    df = df[1:]  # 단위 행 제거
    df.columns = units.index  # 열 이름을 단위로 설정
    df.rename(columns=column_mappings, inplace=True)  # 열 이름 매핑 적용

    # 데이터 업데이트
    data = {}
    for column, mapped_name in column_mappings.items():
        if mapped_name in df.columns:
            data[mapped_name] = pd.to_numeric(df[mapped_name], errors='coerce').values
        else:
            data[mapped_name] = np.zeros(df.shape[0])  # 열이 없다면 0으로 채워진 배열 생성

    # 필요한 변수 데이터 로드 (.mat 파일에서)
    variables_needed = ['LEsc', 'H', 'ea', 'es']
    for var in variables_needed:
        data[var] = mat_data[var].squeeze() if var in mat_data else np.zeros(df.shape[0])

    # 공통 차원 확인 및 조정
    common_length = min(len(data['LEsc']), df.shape[0], *(len(data[col]) for col in column_mappings.values()))
    for key in data.keys():
        data[key] = data[key][:common_length]

    # 'replace' 열 처리
    if 'replace' in df.columns:
        replace = pd.to_numeric(df['replace'], errors='coerce').fillna(1).astype(int).values
    else:
        replace = np.ones(df.shape[0], dtype=int)  # 'replace' 열이 없으면 모든 값에 대해 보정 적용

    # LE 데이터 보정 계산
    LE_cor = np.where(replace == 0, data['LEsc'], data['LEsc'] * 1.061 + 6.3259)

    # 추가 필요한 계산 변수
    lambda_ = 2501 - 2.37 * data['T_AIR']
    T_atm = (data['RLDN'] / (5.67e-8) / 0.85)**0.25
    T_air = data['T_AIR'] + 273.15  # assuming T_AIR is in Celsius and needs conversion to Kelvin
    T_surf = (data['RLUP'] / (5.67e-8) / 0.98)**0.25

    # 결과 DataFrame 생성
    results = pd.DataFrame({
        'Timestamp': pd.to_datetime(df['Timestamp']),
        'PPT': data['PPT'],
        'T_atm': T_atm,
        'T_air': T_air,
        'T_surf': T_surf,
        'T_soil': df[['Ts_0.1m(1)', 'Ts_0.1m(2)']].mean(axis=1),
        'T_bio': df[['Ta_1m', 'Ta_3m', 'Ta_10m', 'Ta_15m']].mean(axis=1),
        'SWC_01': df[['SWC_0.1m(1)', 'SWC_0.1m(2)']].mean(axis=1),
        'SWC_01_03': df[['SWC_0.1_0.3m(1)', 'SWC_0.1_0.3m(2)']].mean(axis=1),
        'SWC_03_06': df[['SWC_0.3_0.6m(1)', 'SWC_0.3_0.6m(2)']].mean(axis=1),
        'RSDN': data['RSDN'],
        'RSUP': data['RSUP'],
        'RLDN': data['RLDN'],
        'RLUP': data['RLUP'],
        'RNET': df['RNET'],
        'H': data['H'],
        'LE': LE_cor,
        'ET': LE_cor / 2.44,
        'G': df[['G_0.1m(1)', 'G_0.1m(2)']].mean(axis=1),
        'B': df[['Ta_1m', 'Ta_3m', 'Ta_10m', 'Ta_15m']].mean(axis=1) * 0.1,
        'J_Rs_net': (data['RSDN'] - data['RSUP']) / 5780,
        'J_Rl_in': data['RLDN'] / T_atm,
        'J_Rl_out': -data['RLUP'] / T_surf,
        'J_Rl_net': (data['RLDN'] / T_atm) + (-data['RLUP'] / T_surf),
        'J_H': -data['H'] / T_air,
        'J_LE': -LE_cor / T_air,
        'J_G': -df[['G_0.1m(1)', 'G_0.1m(2)']].mean(axis=1) / df[['Ts_0.1m(1)', 'Ts_0.1m(2)']].mean(axis=1),
        'J_B': -df[['Ta_1m', 'Ta_3m', 'Ta_10m', 'Ta_15m']].mean(axis=1) * 0.1 / df[['Ta_1m', 'Ta_3m', 'Ta_10m', 'Ta_15m']].mean(axis=1),
        #0 되는거 방지하기 위해
        #'J_G': -df[['G_0.1m(1)', 'G_0.1m(2)']].mean(axis=1) / df[['Ts_0.1m(1)', 'Ts_0.1m(2)']].mean(axis=1),
        #'J_B': -df[['Ta_1m', 'Ta_3m', 'Ta_10m', 'Ta_15m']].mean(axis=1) * 0.1 / df[['Ta_1m', 'Ta_3m', 'Ta_10m', 'Ta_15m']].mean(axis=1),
        'O_Rs': (data['RSDN'] - data['RSUP']) * (1 / T_surf - 1 / 5780),
        'O_Rl': data['RLDN'] * (1 / T_surf - 1 / T_atm),
        'J': np.zeros(common_length),  # J 계산 필요
        'O': np.zeros(common_length),  # O 계산 필요
        'dS_dt': np.zeros(common_length),  # 엔트로피 변화율 계산 필요
        'VPD': data['es'] - data['ea']
    })

    # 결과 저장
    results.to_excel(f'{dir_path}/Results_{year}_{sheet_name}_Modified.xlsx', index=False)
    print(f"File saved for {sheet_name}")