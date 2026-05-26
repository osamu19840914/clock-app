#!/bin/bash
# Mac / Linux 用起動スクリプト
# 初回のみ: chmod +x run.sh を実行してから ./run.sh で起動

cd "$(dirname "$0")"

echo "============================================"
echo " 燃費ログビューア"
echo "============================================"

# .env ファイルの存在チェック
if [ ! -f ".env" ]; then
    echo "[エラー] .env ファイルが見つかりません。"
    echo ".env.example をコピーして .env を作成し、"
    echo "NOTION_TOKEN と NOTION_DATABASE_ID を設定してください。"
    exit 1
fi

# Python3 の存在チェック
if ! command -v python3 &>/dev/null; then
    echo "[エラー] python3 が見つかりません。"
    echo "https://www.python.org/ からインストールしてください。"
    exit 1
fi

echo "サーバーを起動しています..."
echo "ブラウザが自動で開きます。"
echo "終了するには Ctrl+C を押してください。"
echo ""

python3 server.py
