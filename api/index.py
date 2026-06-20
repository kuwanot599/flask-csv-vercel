import os
import csv
from flask import Flask, render_template, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# -------------------------------------------------------------------------
# 1. Supabase の接続設定
# -------------------------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabaseの環境変数（SUPABASE_URL, SUPABASE_ANON_KEY）が設定されていません。")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔴 作り直した新しいSupabaseのテーブル名をここに指定してください
TABLE_NAME = "users"

# 初回アクセス時のみUPSERTを実行するためのフラグ
is_first_request = True


# -------------------------------------------------------------------------
# 2. CSVデータをSupabaseへUPSERTする関数
# -------------------------------------------------------------------------
def upsert_csv_data():
    csv_file_path = "data.csv"
    
    if not os.path.exists(csv_file_path):
        print(f"警告: {csv_file_path} が見つかりません。")
        return False

    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]
        
        if rows:
            supabase.table(TABLE_NAME).upsert(rows).execute()
            print(f"成功: {len(rows)} 件のデータを '{TABLE_NAME}' にUPSERTしました。")
            return True
        else:
            print("警告: data.csv が空です。")
            return False
            
    except Exception as e:
        print(f"エラー: CSVのUPSERT中に問題が発生しました: {e}")
        return False


# -------------------------------------------------------------------------
# 3. ルーティング（画面表示）
# -------------------------------------------------------------------------
@app.route("/")
def index():
    global is_first_request
    
    # 🔴 クラッシュを避けるため、アプリ起動時ではなく「最初のアクセス時」に安全に実行
    if is_first_request:
        print("初回アクセスを検知しました。CSVのUPSERT同期を開始します。")
        upsert_csv_data()
        is_first_request = False # 2回目以降のアクセスでは実行しない

    try:
        # Supabaseから最新のデータを全件取得
        response = supabase.table(TABLE_NAME).select("*").execute()
        rows = response.data
    except Exception as e:
        print(f"データベース取得エラー: {e}")
        rows = []

    return render_template("index.html", rows=rows)


# -------------------------------------------------------------------------
# 手動で再同期するためのAPIエンドポイント
# -------------------------------------------------------------------------
@app.route("/api/sync")
def sync_data():
    success = upsert_csv_data()
    if success:
        return jsonify({"status": "success", "message": "CSV data successfully synced to Supabase."})
    else:
        return jsonify({"status": "error", "message": "Failed to sync CSV data."}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)