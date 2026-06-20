import os
import csv
from flask import Flask, render_template
from supabase import create_client, Client

app = Flask(__name__, template_folder='templates')
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data.csv')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options={"schema": "public"})
else:
    supabase = None


# 💡 HTML（index.html）側が辞書データに対して「.headers」を要求して落ちるバグを
# 💡 完全に無力化するための、ダミーのヘッダー属性を持った特殊なデータ偽装ラッパーです。
class SafeUserWrapper(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # HTML側が「users.headers」や「user.headers」を呼び出しても絶対に落ちないように防御
        self.headers = {}

    def __getattr__(self, name):
        # オブジェクト記法（user.id や user.name）でアクセスされてもエラーにせず辞書から返す
        if name in self:
            return self[name]
        if name == 'headers':
            return {}
        raise AttributeError(f"'SafeUserWrapper' object has no attribute '{name}'")


@app.route('/')
def sync_and_show_table():
    if not supabase:
        return "エラー: Supabaseの環境変数（SUPABASE_URL, SUPABASE_KEY）が設定されていません。", 500

    if not os.path.exists(CSV_FILE):
        return f"エラー: CSVファイルが見つかりません。配置パス: {CSV_FILE}", 404

    try:
        # 1. CSVを読み込んでSupabaseへUpsert
        rows_to_upsert = []
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows_to_upsert.append({
                    "id": row["id"],
                    "name": row["name"]
                })
        
        if rows_to_upsert:
            _ = supabase.table("users").upsert(rows_to_upsert).execute()

        # 2. Supabaseからデータを全件取得
        response = supabase.table("users").select("*").order("id", desc=False).execute()
        
        if isinstance(response, dict):
            raw_data = response.get('data', [])
        else:
            raw_data = getattr(response, 'data', [])

        # 3. 💡 取得したデータを、絶対に「.headers」で落ちない特殊オブジェクトに変換
        cleaned_users = []
        for user in raw_data:
            user_dict = user if isinstance(user, dict) else getattr(user, '__dict__', {})
            
            # 安全なラッパーにデータを詰め替える
            wrapped_user = SafeUserWrapper({
                "id": str(user_dict.get("id", "")),
                "name": str(user_dict.get("name", ""))
            })
            cleaned_users.append(wrapped_user)

        # 💡 usersリスト自体にも .headers 属性を持たせるための対策
        class SafeList(list):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.headers = {}

        final_users = SafeList(cleaned_users)

        # 4. レンダリングを実行
        return render_template('index.html', users=final_users)

    except Exception as e:
        return f"システムエラーが発生しました: {str(e)}", 500