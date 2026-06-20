import os
import csv
from flask import Flask, render_template
from supabase import create_client, Client

# Vercel環境でtemplatesフォルダを正しく読み込ませるための設定
app = Flask(__name__, template_folder='templates')

# 以前うまくいっていたフォルダ構造（apiの一つ外の階層の data.csv）を正確に指定
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data.csv')

# 💡 Flaskに「ルート関数」だと勘違いされないよう、シンプルに直下で初期化します
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options={"schema": "public"})
else:
    supabase = None


@app.route('/')
def sync_and_show_table():
    if not supabase:
        return "エラー: Supabaseの環境変数（SUPABASE_URL, SUPABASE_KEY）が設定されていません。", 500

    if not os.path.exists(CSV_FILE):
        return f"エラー: CSVファイルが見つかりません。配置パス: {CSV_FILE}", 404

    try:
        # -------------------------------------------------------------------------
        # 1. CSVを読み込んでSupabaseへUpsert（データの同期を実行）
        # -------------------------------------------------------------------------
        rows_to_upsert = []
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 新しいテーブル・CSVに合わせて 'role' を除外し、'id' と 'name' のみに適合
                rows_to_upsert.append({
                    "id": row["id"],
                    "name": row["name"]
                })
        
        if rows_to_upsert:
            # 💡 Flaskのレスポンスに影響を与えないよう、ダミー変数「_」で結果を受け取ります
            _ = supabase.table("users").upsert(rows_to_upsert).execute()

        # -------------------------------------------------------------------------
        # 2. 画面表示用に、Supabaseから最新のデータを全件引っ張ってくる
        # -------------------------------------------------------------------------
        response = supabase.table("users").select("*").order("id", desc=False).execute()
        
        # 戻り値の型（dictかObjectか）の差異を100%吸収する安全な抽出
        if isinstance(response, dict):
            current_users = response.get('data', [])
        else:
            current_users = getattr(response, 'data', [])

        # -------------------------------------------------------------------------
        # 3. HTMLテンプレートにデータを渡してレンダリング
        # -------------------------------------------------------------------------
        # ⭕ 確実に「HTML文字列」だけを返却するため、Flaskが誤認する余地はありません
        return render_template('index.html', users=current_users)

    except Exception as e:
        return f"システムエラーが発生しました: {str(e)}", 500