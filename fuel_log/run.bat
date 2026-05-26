@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================
echo  燃費ログビューア
echo ============================================

rem .env ファイルの存在チェック
if not exist ".env" (
    echo [エラー] .env ファイルが見つかりません。
    echo .env.example をコピーして .env を作成し、
    echo NOTION_TOKEN と NOTION_DATABASE_ID を設定してください。
    pause
    exit /b 1
)

rem Python の存在チェック
where python > nul 2>&1
if errorlevel 1 (
    echo [エラー] Python が見つかりません。
    echo https://www.python.org/ からインストールしてください。
    pause
    exit /b 1
)

echo サーバーを起動しています...
echo ブラウザが自動で開きます。
echo 終了するには このウィンドウを閉じるか Ctrl+C を押してください。
echo.

python server.py

pause
