import os
import csv
from flask import Flask, render_template, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# テーブル名は小文字の「users」で固定
TABLE_NAME = "users"


# -------------------------------------------------------------------------
# 安全にSupabaseクライアントを生成する関数（インポートエラー対策版）
# -------------------------------------------------------------------------
def get_supabase_client() -> Client:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabaseの環境変数（SUPABASE_URL, SUPABASE_ANON_KEY）が設定されていません。")
    
    # 💡 外部クラスをインポートせず、プレーンな辞書型でオプションを指定して
    # パス不正（PGRST125）とインポートエラー（500）を同時に回避します
    safe_options = {"schema": "public"}
    
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=safe_options)


# -------------------------------------------------------------------------
# 1. ルーティング（画面表示：データ取得のみ）
# -------------------------------------------------------------------------
@app.route("/")
def index():
    try:
        supabase = get_supabase_client()
        response = supabase.table(TABLE_NAME).select("*").execute()
        rows = response.data
    except Exception as e:
        # VercelのLogsにエラー詳細を出すため、printではなく標準エラー出力等に反映
        print(f"データベース取得エラー詳細: {str(e)}")
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