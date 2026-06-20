import os
import csv
from flask import Flask, render_template
from supabase import create_client, Client

# Vercel環境でtemplatesフォルダを正しく読み込ませるための設定
app = Flask(__name__, template_folder='templates')

# 以前うまくいっていたフォルダ構造（apiの一つ外の階層の data.csv）を正確に指定
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data.csv')

# 環境変数の取得
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# グローバル空間での安全な初期化
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
                rows_to_upsert.append({
                    "id": row["id"],
                    "name": row["name"]
                })
        
        if rows_to_upsert:
            # 💡 戻り値オブジェクトをそのまま放置するとFlaskが誤認するため、
            # 💡 明示的に実行のみを行い、結果は変数に代入してスコープを閉じます
            _result = supabase.table("users").upsert(rows_to_upsert).execute()

        # -------------------------------------------------------------------------
        # 2. 画面表示用に、Supabaseから最新のデータを全件引っ張ってくる
        # -------------------------------------------------------------------------
        response = supabase.table("users").select("*").order("id", desc=False).execute()
        
        # 💡 ここが最重要ポイントです 💡
        # responseオブジェクトをそのまま触るのではなく、完全に「純粋なPythonの配列・辞書」へ変換します
        raw_data = []
        if isinstance(response, dict):
            raw_data = response.get('data', [])
        elif hasattr(response, 'data'):
            raw_data = response.data
        else:
            raw_data = getattr(response, 'sliced', [])

        # 💡 万が一、抽出したデータがカスタムオブジェクトだった場合を想定し、
        # 💡 プレーンな辞書のリストにディープコピーして「純粋なデータ」にします
        cleaned_users = []
        for user in raw_data:
            if isinstance(user, dict):
                cleaned_users.append({
                    "id": str(user.get("id", "")),
                    "name": str(user.get("name", ""))
                })
            else:
                cleaned_users.append({
                    "id": str(getattr(user, "id", "")),
                    "name": str(getattr(user, "name", ""))
                })

        # -------------------------------------------------------------------------
        # 3. HTMLテンプレートにデータを渡してレンダリング
        # -------------------------------------------------------------------------
        # ⭕ 完全にクレンジングされた安全な配列（cleaned_users）を渡すことで、
        # ⭕ Flaskが 'headers' 属性を探してクラッシュするバグの発生原因を根絶しました。
        return render_template('index.html', users=cleaned_users)

    except Exception as e:
        return f"システムエラーが発生しました: {str(e)}", 500