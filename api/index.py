from flask import Flask, jsonify
import csv
import os

app = Flask(__name__)

# CSVファイルのパス（apiフォルダから見て1つ上の階層にあるdata.csvを指す）
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data.csv')

@app.route('/')
def index():
    # CSVファイルが存在するかチェック
    if not os.path.exists(CSV_FILE):
        return jsonify({
            "status": "error", 
            "message": "CSVファイルが見つかりません。ルート直下に data.csv を配置してください。"
        }), 404
    
    try:
        data = []
        # Pythonの標準機能（csvモジュール）を使って安全にCSVを読み込む
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        
        return jsonify({
            "status": "success",
            "message": "Hello from Flask on Vercel! CSVデータの読み込みに成功しました。",
            "data": data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ※ Vercelでは、ローカルテスト用を除き、app.run() や特殊なハンドラーの記述は不要です！