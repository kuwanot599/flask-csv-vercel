from flask import Flask, render_template, jsonify
import csv
import os
from supabase import create_client, Client

# Vercel環境でtemplatesフォルダを正しく読み込ませるためのパス明示設定
app = Flask(__name__, template_folder='templates')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data.csv')

@app.route('/')
def sync_and_show_table():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return "エラー: Supabaseの環境変数が設定されていません。", 500

    if not os.path.exists(CSV_FILE):
        return "エラー: CSVファイルが見つかりません。", 404

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 1. CSVを読み込んでSupabaseへUpsert（データの同期を実行）
        rows_to_upsert = []
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows_to_upsert.append({
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"]
                })
        
        supabase.table("users").upsert(rows_to_upsert).execute()

        # 2. 【ここが進化！】画面表示用に、Supabaseから最新のデータを全件引っ張ってくる
        # id順（昇順）に並び替えて取得します
        response = supabase.table("users").select("*").order("id", ascending=True).execute()
        current_users = response.data

        # 3. HTMLテンプレートにSupabaseのデータを乗せてブラウザにレンダリング
        return render_template('index.html', users=current_users)

    except Exception as e:
        return f"システムエラーが発生しました: {str(e)}", 500