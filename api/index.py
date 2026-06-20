import os
import csv
from flask import Flask, render_template, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# 🔴 作り直した新しいSupabaseのテーブル名
TABLE_NAME = "my_new_table"


# -------------------------------------------------------------------------
# 💡 安全にSupabaseクライアントを生成する関数
# グローバル空間ではなく、関数内で呼び出すことで初期化クラッシュを防ぎます
# -------------------------------------------------------------------------
def get_supabase_client() -> Client:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabaseの環境変数（SUPABASE_URL, SUPABASE_ANON_KEY）が設定されていません。")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------------------------------------------------------
# 1. ルーティング（画面表示：データ取得のみ）
# -------------------------------------------------------------------------
@app.route("/")
def index():
    try:
        # 関数内で安全にクライアントを初期化
        supabase = get_supabase_client()
        
        # Supabaseから最新のデータを全件取得
        response = supabase.table(TABLE_NAME).select("*").execute()
        rows = response.data
    except Exception as e:
        print(f"データベース取得エラー: {e}")
        rows = []

    return render_template("index.html", rows=rows)


# -------------------------------------------------------------------------
# 2. CSVデータをSupabaseへUPSERTする専用API（手動同期用 URLの末尾に /api/sync）
# -------------------------------------------------------------------------
@app.route("/api/sync")
def sync_data():
    csv_file_path = "data.csv"
    
    if not os.path.exists(csv_file_path):
        return jsonify({"status": "error", "message": f"{csv_file_path} が見つかりません。"}), 404

    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]
        
        if rows:
            # 関数内で安全にクライアントを初期化
            supabase = get_supabase_client()
            
            # UPSERT実行
            supabase.table(TABLE_NAME).upsert(rows).execute()
            return jsonify({"status": "success", "message": f"{len(rows)} 件のデータをUPSERTしました。"})
        else:
            return jsonify({"status": "warning", "message": "data.csv が空です。"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)