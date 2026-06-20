import os
import csv
from flask import Flask, render_template
from supabase import create_client, Client

# Vercel環境でtemplatesフォルダを正しく読み込ませるためのパス設定
app = Flask(__name__, template_folder='templates')

# 以前うまくいっていたフォルダ構造（apiの一つ外の階層の data.csv）を正確に指定
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data.csv')


def get_supabase_client() -> Client:
    """関数内で初期化することで、Vercel起動時のインポートクラッシュを完全に防ぎます"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("Supabaseの環境変数（SUPABASE_URL, SUPABASE_KEY）が設定されていません。")
        
    return create_client(url, key, options={"schema": "public"})


@app.route('/')
def sync_and_show_table():
    if not os.path.exists(CSV_FILE):
        return f"エラー: CSVファイルが見つかりません。配置パス: {CSV_FILE}", 404

    try:
        # リクエストごとに安全にクライアントを取得
        supabase = get_supabase_client()

        # -------------------------------------------------------------------------
        # 1. CSVを読み込んでSupabaseへUpsert（データの同期を実行）
        # -------------------------------------------------------------------------
        rows_to_upsert = []
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 'role' を除外し、'id' と 'name' のみに適合
                rows_to_upsert.append({
                    "id": row["id"],
                    "name": row["name"]
                })
        
        if rows_to_upsert:
            supabase.table("users").upsert(rows_to_upsert).execute()

        # -------------------------------------------------------------------------
        # 2. 画面表示用に、Supabaseから最新のデータを全件引っ張ってくる
        # -------------------------------------------------------------------------
        response = supabase.table("users").select("*").order("id", desc=False).execute()
        
        # 💡 supabase-pyのバージョン差異によるクラッシュを防ぐ安全なデータ抽出
        if hasattr(response, 'data'):
            current_users = response.data
        elif isinstance(response, dict):
            current_users = response.get('data', [])
        else:
            current_users = getattr(response, 'sliced', [])

        # -------------------------------------------------------------------------
        # 3. HTMLテンプレートにデータを渡してレンダリング
        # -------------------------------------------------------------------------
        return render_template('index.html', users=current_users)

    except Exception as e:
        return f"システムエラーが発生しました: {str(e)}", 500