import os
import csv
from flask import Flask, render_template, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# -------------------------------------------------------------------------
# 1. Supabase の接続設定
# Vercelの環境変数（Environment Variables）から認証情報を取得します
# -------------------------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabaseの環境変数（SUPABASE_URL, SUPABASE_ANON_KEY）が設定されていません。")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔴 作り直した新しいSupabaseのテーブル名をここに指定してください
TABLE_NAME = "users"


# -------------------------------------------------------------------------
# 2. CSVデータをSupabaseへUPSERTする関数
# -------------------------------------------------------------------------
def upsert_csv_data():
    csv_file_path = "data.csv"
    
    # リポジトリ直下に data.csv が存在するか確認
    if not os.path.exists(csv_file_path):
        print(f"警告: {csv_file_path} が見つかりません。UPSERT処理をスキップします。")
        return False

    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # CSVのヘッダー行をキーとした辞書のリストを作成
            rows = [row for row in reader]
        
        if rows:
            # SupabaseにUPSERT（重複データは更新、新規データは挿入）
            # ※CSVのヘッダー名と、Supabaseの列名が一致している必要があります
            supabase.table(TABLE_NAME).upsert(rows).execute()
            print(f"成功: {len(rows)} 件のデータを '{TABLE_NAME}' テーブルにUPSERTしました。")
            return True
        else:
            print("警告: data.csv が空です。")
            return False
            
    except Exception as e:
        print(f"エラー: CSVのUPSERT中に問題が発生しました: {e}")
        return False


# -------------------------------------------------------------------------
# 3. Vercel起動時（または初回アクセス時）に自動でCSVを同期
# -------------------------------------------------------------------------
# アプリケーション起動時にCSVの内容を自動でSupabaseへ反映させます
with app.app_context():
    upsert_csv_data()


# -------------------------------------------------------------------------
# 4. ルーティング（画面表示）
# -------------------------------------------------------------------------
@app.route("/")
def index():
    try:
        # Supabaseから最新のデータを全件取得
        # （並び順を固定したい場合は .order('id') などを末尾に追記してください）
        response = supabase.table(TABLE_NAME).select("*").execute()
        rows = response.data
    except Exception as e:
        print(f"データベース取得エラー: {e}")
        rows = []

    # templates/index.html に取得したレコード一覧を渡してレンダリング
    return render_template("index.html", rows=rows)


# -------------------------------------------------------------------------
# （参考）手動で再同期するためのAPIエンドポイント
# -------------------------------------------------------------------------
@app.route("/api/sync")
def sync_data():
    success = upsert_csv_data()
    if success:
        return jsonify({"status": "success", "message": "CSV data successfully synced to Supabase."})
    else:
        return jsonify({"status": "error", "message": "Failed to sync CSV data."}), 500


# Vercel環境以外（ローカル開発環境など）で直接実行された場合の起動処理
if __name__ == "__main__":
    app.run(debug=True, port=5000)