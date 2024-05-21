import pandas as pd
from scipy.io import loadmat
import numpy as np
from datetime import datetime, timedelta

def process_daily_data(df):
    # 일 단위로 데이터 집계
    df_daily = df.resample('D', on='Timestamp').agg({
        'PPT': 'sum',
        'T_atm': 'mean',
        'T_air': 'mean',
        'T_surf': 'mean',
        'T_soil': 'mean',
        'detT_soil': 'mean',
        'T_bio': 'mean',
        'detT_bio': 'mean',
        'SWC_01': 'mean',
        'SWC_01_03': 'mean',
        'SWC_03_06': 'mean',
        'RSDN': 'sum',
        'RSUP': 'sum',
        'RLDN': 'sum',
        'RLUP': 'sum',
        'RNET': 'sum',
        'H': 'sum',
        'LE': 'sum',
        'G': 'sum',
        'B': 'sum',
        'J_Rs_net': 'sum',
        'J_Rl_in': 'sum',
        'J_Rl_out': 'sum',
        'J_Rl_net': 'sum',
        'J_H': 'sum',
        'J_LE': 'sum',
        'J_G': 'sum',
        'J_B': 'sum',
        'O_Rs': 'sum',
        'O_Rl': 'sum',
        'J': 'sum',
        'O': 'sum',
        'dS_dt': 'sum',
        'VPD': 'mean'
    })

    # 결과의 단위를 MJ/m2/day로 변환
    columns_to_convert = ['RSDN', 'RSUP', 'RLDN', 'RLUP', 'RNET', 'H', 'LE', 'G', 'B',
                          'J_Rs_net', 'J_Rl_in', 'J_Rl_out', 'J_Rl_net', 'J_H', 'J_LE',
                          'J_G', 'J_B', 'O_Rs', 'O_Rl', 'J', 'O', 'dS_dt']
    df_daily[columns_to_convert] = df_daily[columns_to_convert] * 60 * 30 / 1000000

    # ET (mm/day) 계산
    df_daily['ET'] = df_daily['LE'] / 2.45

    return df_daily

dir_path = 'E:/Matlab/work_on/Entropy'  # 절대 경로 사용
sheet_name = 'L2_after GF'  # 처리할 시트 이름

for year in range(2006, 2018):
    print(f"Processing year: {year}")

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
            data[mapped_name] = pd.to_numeric(df[mapped_name], errors='coerce')
        else:
            data[mapped_name] = pd.Series(dtype=float)  # 열이 없다면 비어있는 시리즈 생성

    # 필요한 변수 데이터 로드 (.mat 파일에서)
    variables_needed = ['LEsc', 'Hsc', 'ea', 'es']
    for var in variables_needed:
        data[var] = mat_data[var].squeeze() if var in mat_data else pd.Series(dtype=float)

    # 공통 차원 확인 및 조정
    common_length = min(len(data['LEsc']), df.shape[0], *(len(data[col]) for col in column_mappings.values()))
    for key in data.keys():
        data[key] = data[key][:common_length]

    # 'replace' 열 처리
    if 'replace' in df.columns:
        replace = pd.to_numeric(df['replace'], errors='coerce').fillna(1).astype(int)
    else:
        replace = pd.Series(np.ones(df.shape[0], dtype=int), index=df.index)  # 'replace' 열이 없으면 모든 값에 대해 보정 적용

    # LE 데이터 보정 계산
    LE_cor = np.where(replace == 0, data['LEsc'], data['LEsc'] * 1.061 + 6.3259)

    # 추가 필요한 계산 변수
    lambda_ = (2501 - 2.37 * data['T_AIR']) * 1000
    T_atm = (data['RLDN'] / (5.67e-8) / 0.85).pow(0.25)
    T_air = data['T_AIR'] + 273.15  # assuming T_AIR is in Celsius and needs conversion to Kelvin
    T_surf = ((data['RLUP'] - (1 - 0.99) * data['RLDN']) / (5.67e-8) / 0.99).pow(0.25)

    # G 계산 (MAT 코드에서는 비어있음)
    G_0_avg = pd.Series(dtype=float)

    # B 계산
    Ta_bio = df[['Ta_1m', 'Ta_3m', 'Ta_10m', 'Ta_15m']].mean(axis=1) + 273.15
    detTa_bio_avg = Ta_bio.diff()
    detTa_bio_avg.iloc[0] = detTa_bio_avg.iloc[1]
    Cveg = 3340
    B_avg = Cveg * detTa_bio_avg * 35.19 / 1800

    # 결과 DataFrame 생성
    results = pd.DataFrame({
        'Timestamp': pd.to_datetime(df['Timestamp']),
        'PPT': data['PPT'],
        'T_atm': T_atm,
        'T_air': T_air,
        'T_surf': T_surf,
        'T_soil': df[['Ts_0.1m(1)', 'Ts_0.1m(2)']].mean(axis=1) + 273.15,
        'detT_soil': df[['Ts_0.1m(1)', 'Ts_0.1m(2)']].mean(axis=1).diff(),
        'T_bio': Ta_bio,
        'detT_bio': detTa_bio_avg,
        'SWC_01': df[['SWC_0.1m(1)', 'SWC_0.1m(2)']].mean(axis=1),
        'SWC_01_03': df[['SWC_0.1_0.3m(1)', 'SWC_0.1_0.3m(2)']].mean(axis=1),
        'SWC_03_06': df[['SWC_0.3_0.6m(1)', 'SWC_0.3_0.6m(2)']].mean(axis=1),
        'RSDN': data['RSDN'],
        'RSUP': data['RSUP'],
        'RLDN': data['RLDN'],
        'RLUP': data['RLUP'],
        'RNET': df['RNET'],
        'H': data['Hsc'],
        'LE': LE_cor,
        'G': G_0_avg,
        'B': B_avg,
        'J_Rs_net': (data['RSDN'] - data['RSUP']) / 5780,
        'J_Rl_in': data['RLDN'] / T_atm,
        'J_Rl_out': -data['RLUP'] / T_surf,
        'J_Rl_net': (data['RLDN'] / T_atm) + (-data['RLUP'] / T_surf),
        'J_H': -data['Hsc'] / T_air,
        'J_LE': -LE_cor / T_air,
        'J_G': pd.Series(dtype=float),  # MAT 코드에서는 비어있음
        'J_B': -B_avg / Ta_bio,
        'O_Rs': (data['RSDN'] - data['RSUP']) * (1 / T_surf - 1 / 5780),
        'O_Rl': data['RLDN'] * (1 / T_surf - 1 / T_atm),
        'J': np.zeros(common_length),  # J 계산 필요
        'O': np.zeros(common_length),  # O 계산 필요
        'dS_dt': np.zeros(common_length),  # 엔트로피 변화율 계산 필요
        'VPD': data['es'] - data['ea']
    })

    # J, O, dS_dt 계산
    results['J'] = results[['J_Rs_net', 'J_Rl_net', 'J_H', 'J_LE', 'J_G', 'J_B']].sum(axis=1)
    results['O'] = results['O_Rs'] + results['O_Rl']
    results['dS_dt'] = results['O'] + results['J']

    # 결과 저장
    results.to_csv(f'{dir_path}/Results_{year}_{sheet_name}_Modified.csv', index=False)
    print(f"File saved for {sheet_name}")

    # 일 단위 데이터 처리
    daily_results = process_daily_data(results)

    # 일 단위 결과 저장
    daily_results.to_csv(f'{dir_path}/Daily_Results_{year}_{sheet_name}_Modified.csv', index=True)
    print(f"Daily file saved for {sheet_name}")