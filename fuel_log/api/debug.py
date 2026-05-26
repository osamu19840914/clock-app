"""
Vercel Python Serverless Function — GET /api/debug
Notionから返るプロパティ名と型を確認するためのデバッグ用エンドポイント。
本番運用が安定したら削除しても構わない。
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


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
            resp = _notion_post(url, {"page_size": 1})
            pages = resp.get("results", [])
            total_pages = resp.get("next_cursor") and "100+" or str(len(pages))

            if not pages:
                info = {"total_pages": 0, "message": "データが0件です。インテグレーションのデータベース接続を確認してください。"}
            else:
                first_props = pages[0].get("properties", {})
                prop_info = {
                    name: {"type": prop.get("type")}
                    for name, prop in first_props.items()
                }
                info = {
                    "env_settings": {
                        "PROP_DATE":     PROP_DATE,
                        "PROP_FUEL":     PROP_FUEL,
                        "PROP_DISTANCE": PROP_DISTANCE,
                    },
                    "notion_properties": prop_info,
                    "hint": "notion_properties のキー名を環境変数 PROP_* に設定してください",
                }
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            info = {"error": f"Notion API エラー {e.code}: {detail}"}
        except Exception as e:
            info = {"error": str(e)}

        body = json.dumps(info, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass
