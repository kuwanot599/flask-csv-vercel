from flask import Flask, render_template, jsonify
import csv
import os
from supabase import create_client, Client

# Vercel環境でtemplatesフォルダを正しく読み込ませるためのパス明示設定
app = Flask(__name__, template_folder='templates')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# 以前うまくいっていたフォルダ構造（apiの一つ外の階層の data.csv）を正確に指定
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data.csv')


@app.route('/')
def sync_and_show_table():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return "エラー: Supabaseの環境変数（SUPABASE_URL, SUPABASE_KEY）が設定されていません。", 500

    if not os.path.exists(CSV_FILE):
        return f"エラー: CSVファイルが見つかりません。配置パス: {CSV_FILE}", 404

    try:
        # Supabaseクライアントの初期化（sb_publishable_... キーの不整合を防ぐためスキーマを明示）
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options={"schema": "public"})

        # 1. CSVを読み込んでSupabaseへUpsert（データの同期を実行）
        rows_to_upsert = []
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 新しいテーブル・CSVに合わせて 'role' を除外し、'id' と 'name' のみに修正
                rows_to_upsert.append({
                    "id": row["id"],
                    "name": row["name"]
                })
        
        if rows_to_upsert:
            supabase.table("users").upsert(rows_to_upsert).execute()

        # 2. 画面表示用に、Supabaseから最新のデータを全件引っ張ってくる
        # 引数を "id" だけにし、desc=False（昇順）の安全な形式
        response = supabase.table("users").select("*").order("id", desc=False).execute()
        current_users = response.data

        # 3. HTMLテンプレートにSupabaseのデータを乗せてブラウザにレンダリング
        return render_template('index.html', users=current_users)

    except Exception as e:
        return f"システムエラーが発生しました: {str(e)}", 500


# 💡 Vercel環境では、余計な wsgi_app の代入や app.run() は不要です。
# 💡 Vercelが上の「app」インスタンスを直接見つけて起動します。