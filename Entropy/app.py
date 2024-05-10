import os
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)
@app.route('/')
def index():
    # 현재 디렉토리에 있는 CSV 파일 리스트 가져오기
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    return render_template('index.html', csv_files=csv_files)
@app.route('/plot', methods=['POST'])
def plot():
    # 선택한 CSV 파일들 가져오기
    selected_files = request.form.getlist('csv_files')
    plot_data_list = []

    for file in selected_files:
        df = pd.read_csv(file)
        plot_data = {
            'filename': file,
            'data': df.to_dict(orient='list')
        }
        plot_data_list.append(plot_data)

    return render_template('plot.html', plot_data_list=plot_data_list)
if __name__ == '__main__':
    app.run(debug=True)