from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

app = Flask(__name__)

# 데이터 불러오기 및 전처리
df_30min = pd.read_csv('Results_2006_L2_after GF_Modified.csv', parse_dates=['Timestamp'])
df_daily = pd.read_csv('Daily_Results_2006_L2_after GF_Modified.csv', parse_dates=['Timestamp'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data', methods=['POST'])
def update_data():
    # 사용자 선택 날짜 범위 가져오기
    start_date = pd.to_datetime(request.form['start_date'])
    end_date = pd.to_datetime(request.form['end_date'])

    # 선택한 날짜 범위에 해당하는 데이터 필터링
    filtered_df_30min = df_30min[(df_30min['Timestamp'] >= start_date) & (df_30min['Timestamp'] <= end_date)]
    filtered_df_daily = df_daily[(df_daily['Timestamp'] >= start_date) & (df_daily['Timestamp'] <= end_date)]

    # 그래프 생성
    fig_temp = px.line(filtered_df_30min, x='Timestamp', y=['T_atm', 'T_air', 'T_surf', 'T_soil'], title='Temperature')
    fig_flux = px.line(filtered_df_30min, x='Timestamp', y=['J_H', 'J_LE'], title='Energy Fluxes')
    fig_entropy = px.line(filtered_df_30min, x='Timestamp', y=['J', 'O'], title='Entropy')

    # 그래프를 HTML로 변환
    graph_temp = fig_temp.to_html(full_html=False)
    graph_flux = fig_flux.to_html(full_html=False)
    graph_entropy = fig_entropy.to_html(full_html=False)

    return render_template('data.html', graph_temp=graph_temp, graph_flux=graph_flux, graph_entropy=graph_entropy,
                           data_30min=filtered_df_30min.to_html(index=False),
                           data_daily=filtered_df_daily.to_html(index=False))

if __name__ == '__main__':
    app.run(debug=True)