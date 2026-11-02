# StreamBGM

配信用のBGM管理デスクトップアプリ（Windows）。

- MP3 / MP4 / WAV / M4A などを登録して音声再生（MP4は音声のみ）
- プレイリストを複数作成
- 1曲・全曲・なしのループ、シャッフル
- シーク、音量、検索、フォルダ一括登録
- `%APPDATA%\StreamBGM\library.json` に設定とファイルパスを保存
- 元のファイルを移動・削除すると再生できなくなります。

## BATやPythonなしで使うEXEの作り方

このZIPは**完成済みEXEではなく、EXEを生成するプロジェクト**です。

1. GitHubで新しいリポジトリを作成（Privateでも可）。
2. ZIPを解凍し、`main.py` と `.github/workflows/build.yml` をフォルダ構造ごとアップロード。
3. GitHubの Actions → Build StreamBGM Windows EXE → Run workflow をクリック。
4. 成功した実行ページの Artifacts → `StreamBGM-EXE` をダウンロード。
5. ダウンロードしたZIPを解凍して `StreamBGM.exe` をダブルクリック。

Windows用のEXEの起動と音声再生は未検証です。Qt Multimediaの再生可否はOSとコーデックに依存します。
配信で流す音源は利用規約・著作権を確認してください。
