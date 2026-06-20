import os
import csv
from flask import Flask, render_template, jsonify
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions  # 💡 オプション設定をインポート

app = Flask(__name__)

TABLE_NAME = "users"


# -------------------------------------------------------------------------
# 安全にSupabaseクライアントを生成する関数
# -------------------------------------------------------------------------
def get_supabase_client() -> Client:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabaseの環境変数（SUPABASE_URL, SUPABASE_ANON_KEY）が設定されていません。")
    
    # 💡 sb_publishable_... のキーで PGRST125 エラー（パス不正）になるのを防ぐため、
    # スキーマを 'public' に固定したクライアントオプションを明示的に渡します
    options = ClientOptions(schema="public")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=options)


# -------------------------------------------------------------------------
# 1. ルーティング（画面表示：データ取得のみ）
# -------------------------------------------------------------------------
@app.route("/")
def index():
    try:
        supabase = get_supabase_client()
        
        # クライアント生成時にオプションを渡しているため、そのままシンプルに呼び出せます
        response = supabase.table(TABLE_NAME).select("*").execute()
        rows = response.data
    except Exception as e:
        print(f"データベース取得エラー: {e}")
        rows = []

    return render_template("index.html", rows=rows)


# -------------------------------------------------------------------------
# 2. CSVデータをSupabaseへUPSERTする専用API（末尾 /api/sync）
# -------------------------------------------------------------------------
@app.route("/api/sync")
def sync_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(current_dir, "data.csv")
    
    if not os.path.exists(csv_file_path):
        return jsonify({"status": "error", "message": f"{csv_file_path} が見つかりません。"}), 404

    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]
        
        if rows:
            supabase = get_supabase_client()
            
            # UPSERTを実行
            supabase.table(TABLE_NAME).upsert(rows).execute()
            return jsonify({"status": "success", "message": f"{len(rows)} 件のデータをUPSERTしました。"})
        else:
            return jsonify({"status": "warning", "message": "data.csv が空です。"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)