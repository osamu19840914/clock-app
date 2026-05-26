"""
燃費ログビューア — ローカルサーバー
Notion APIをサーバー側で叩いてCORSを回避し、ブラウザにデータを提供する。
依存ライブラリ: なし（Python 3.6+ 標準ライブラリのみ）
"""

import json
import os
import urllib.request
import urllib.error
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ---------------------------------------------------------------------------
# .env 読み込み（python-dotenv 不要）
# ---------------------------------------------------------------------------

def _load_env(path: str = ".env") -> None:
    env_path = Path(__file__).parent / path
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

_load_env()

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

NOTION_TOKEN   = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID    = os.environ.get("NOTION_DATABASE_ID", "")
PROP_DATE      = os.environ.get("PROP_DATE", "日付")
PROP_FUEL      = os.environ.get("PROP_FUEL", "給油量")
PROP_DISTANCE  = os.environ.get("PROP_DISTANCE", "走行距離")
PORT           = int(os.environ.get("PORT", "8080"))

SCRIPT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Notion API
# ---------------------------------------------------------------------------

def _notion_request(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_all_pages() -> list:
    """ページネーションを考慮して全レコードを取得する。"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    results = []
    start_cursor = None

    while True:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        resp = _notion_request(url, body)
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")

    return results


def _get_number(prop: dict) -> float | None:
    return prop.get("number") if prop.get("type") == "number" else None


def _get_date(prop: dict) -> str | None:
    t = prop.get("type")
    # Date型
    if t == "date" and prop.get("date"):
        return prop["date"]["start"][:10]
    # タイトル型（日付をテキストで入力しているケース）
    if t == "title":
        titles = prop.get("title", [])
        if titles:
            text = titles[0].get("plain_text", "").strip()
            # YYYY/MM/DD → YYYY-MM-DD に正規化
            return text.replace("/", "-") if text else None
    # リッチテキスト型
    if t == "rich_text":
        blocks = prop.get("rich_text", [])
        if blocks:
            text = blocks[0].get("plain_text", "").strip()
            return text.replace("/", "-") if text else None
    return None


def build_records(pages: list) -> list:
    """Notionページリストから燃費レコードを生成して日付昇順で返す。"""
    records = []
    for page in pages:
        props = page.get("properties", {})

        date_val = _get_date(props.get(PROP_DATE, {}))
        fuel_val = _get_number(props.get(PROP_FUEL, {}))
        dist_val = _get_number(props.get(PROP_DISTANCE, {}))

        if date_val is None or fuel_val is None or dist_val is None:
            continue
        if fuel_val <= 0:
            continue

        records.append({
            "date":     date_val,
            "fuel":     round(fuel_val, 2),
            "distance": round(dist_val, 2),
            "kmpl":     round(dist_val / fuel_val, 2),
        })

    records.sort(key=lambda r: r["date"])
    return records

# ---------------------------------------------------------------------------
# HTTPハンドラ
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
        elif path == "/api/fuel-log":
            self._serve_api()
        elif path == "/api/debug":
            self._serve_debug()
        else:
            self.send_error(404, "Not Found")

    def _serve_file(self, filename: str, content_type: str) -> None:
        filepath = SCRIPT_DIR / filename
        if not filepath.exists():
            self.send_error(404, f"{filename} not found")
            return
        content = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_api(self) -> None:
        if not NOTION_TOKEN:
            self._json_error(500, ".env に NOTION_TOKEN が設定されていません")
            return
        if not DATABASE_ID:
            self._json_error(500, ".env に NOTION_DATABASE_ID が設定されていません")
            return
        try:
            pages = fetch_all_pages()
            records = build_records(pages)
            body = json.dumps(records, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            self._json_error(502, f"Notion API エラー {e.code}: {detail}")
        except Exception as e:
            self._json_error(500, str(e))

    def _serve_debug(self) -> None:
        """Notionから返ってくるプロパティ名と型を確認するためのデバッグ用エンドポイント。"""
        try:
            pages = fetch_all_pages()
            if not pages:
                info = {"total_pages": 0, "message": "データが0件です。インテグレーションのデータベース接続を確認してください。"}
            else:
                first_props = pages[0].get("properties", {})
                prop_info = {
                    name: {"type": prop.get("type"), "raw": prop}
                    for name, prop in first_props.items()
                }
                info = {
                    "total_pages": len(pages),
                    "env_settings": {
                        "PROP_DATE": PROP_DATE,
                        "PROP_FUEL": PROP_FUEL,
                        "PROP_DISTANCE": PROP_DISTANCE,
                    },
                    "notion_properties": prop_info,
                    "hint": "notion_properties のキー名を .env の PROP_* に設定してください",
                }
            body = json.dumps(info, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self._json_error(500, str(e))

    def _json_error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # 標準ログを抑制
        pass

# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

def _open_browser(url: str) -> None:
    """サーバー起動後にブラウザを開く。"""
    import time
    time.sleep(0.8)
    webbrowser.open(url)


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    print(f"燃費ログサーバーを起動: {url}")
    print("終了するには Ctrl+C を押してください\n")

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    server = HTTPServer(("", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました。")
