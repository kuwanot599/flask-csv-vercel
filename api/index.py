from flask import Flask, jsonify
import csv
import os
from supabase import create_client, Client

app = Flask(__name__)

# 1. 環境変数からSupabaseの接続情報を取得（ローカルやVercelの設定から自動で入ります）
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# CSVファイルのパス
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data.csv')

@app.route('/')
def sync_csv_to_supabase():
    # 環境変数が設定されているかチェック
    if not SUPABASE_URL or not SUPABASE_KEY:
        return jsonify({
            "status": "error",
            "message": "Supabaseの環境変数（SUPABASE_URL, SUPABASE_KEY）が設定されていません。"
        }), 500

    if not os.path.exists(CSV_FILE):
        return jsonify({"status": "error", "message": "CSVファイルが見つかりません。"}), 404

    try:
        # 2. Supabaseクライアントの初期化
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 3. CSVファイルの読み込み
        rows_to_upsert = []
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # SQLのテーブル構造に合わせてデータを整形
                rows_to_upsert.append({
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"]
                })

        # 4. SupabaseへUpsertを実行
        # 重複する主キー(id)があれば上書き、なければ新規追加を自動で行います
        response = supabase.table("users").upsert(rows_to_upsert).execute()

        return jsonify({
            "status": "success",
            "message": f"SupabaseへのUpsertが成功しました！計 {len(rows_to_upsert)} 件のデータを同期しました。",
            "synchronized_data": rows_to_upsert
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500