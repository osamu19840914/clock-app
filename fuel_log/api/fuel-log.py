"""
Vercel Python Serverless Function — GET /api/fuel-log
Notionデータベースから燃費レコードを取得してJSONで返す。
依存ライブラリ: なし（Python標準ライブラリのみ）
環境変数は Vercel ダッシュボードで設定する。
"""

import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

NOTION_TOKEN  = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID   = os.environ.get("NOTION_DATABASE_ID", "")
PROP_DATE     = os.environ.get("PROP_DATE", "日付")
PROP_FUEL     = os.environ.get("PROP_FUEL", "給油量")
PROP_DISTANCE = os.environ.get("PROP_DISTANCE", "走行距離")


# ---------------------------------------------------------------------------
# Notion API
# ---------------------------------------------------------------------------

def _notion_post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def fetch_all_pages() -> list:
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    results, start_cursor = [], None
    while True:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        resp = _notion_post(url, body)
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")
    return results


def _get_number(prop: dict):
    return prop.get("number") if prop.get("type") == "number" else None


def _get_date(prop: dict):
    t = prop.get("type")
    if t == "date" and prop.get("date"):
        return prop["date"]["start"][:10]
    if t == "title":
        items = prop.get("title", [])
        if items:
            text = items[0].get("plain_text", "").strip()
            return text.replace("/", "-") if text else None
    if t == "rich_text":
        items = prop.get("rich_text", [])
        if items:
            text = items[0].get("plain_text", "").strip()
            return text.replace("/", "-") if text else None
    return None


def build_records(pages: list) -> list:
    records = []
    for page in pages:
        props = page.get("properties", {})
        date_val = _get_date(props.get(PROP_DATE, {}))
        fuel_val = _get_number(props.get(PROP_FUEL, {}))
        dist_val = _get_number(props.get(PROP_DISTANCE, {}))
        if not (date_val and fuel_val and dist_val and fuel_val > 0):
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
# Vercel handler（クラス名は必ず "handler"）
# ---------------------------------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if not NOTION_TOKEN:
            self._err(500, "NOTION_TOKEN が設定されていません（Vercelの環境変数を確認）")
            return
        if not DATABASE_ID:
            self._err(500, "NOTION_DATABASE_ID が設定されていません（Vercelの環境変数を確認）")
            return
        try:
            pages = fetch_all_pages()
            records = build_records(pages)
            self._json(200, records)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            self._err(502, f"Notion API エラー {e.code}: {detail}")
        except Exception as e:
            self._err(500, str(e))

    def _json(self, code: int, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _err(self, code: int, msg: str):
        self._json(code, {"error": msg})

    def log_message(self, fmt, *args):
        pass
