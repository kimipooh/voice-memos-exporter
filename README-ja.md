# Voice Memos Exporter

[English: README.md](README.md)

これは [rudrakabir/voice-memos-exporter](https://github.com/rudrakabir/voice-memos-exporter)（作者: [rudrakabir](https://github.com/rudrakabir)）のforkです。macOSのボイスメモを一括書き出しできる有用なツールを公開してくださった原作者に感謝します。

このforkでは、利用環境によって一部の録音を書き出せない場合があった点を見直し、現行macOSへの対応やCLI機能を追加しています。現在はGUIアプリとPython CLIの両方からボイスメモを一括書き出せます。

## 主な機能

- 全録音、またはタイトルや日付範囲で絞り込んだ録音を、指定したフォルダへ書き出します。
- GUIで Title / Date / Duration / Local / Status 列の一覧、タイトル検索、Include Recently Deletedを利用できます。
- GUIで Select All / Deselect All、dry-runプレビュー、進捗表示、キャンセルを利用できます。
- 1件が失敗しても処理を続け、Total / Exported / Skipped / Failedを報告します。
- `/` を含むタイトルや数字だけのタイトルにも対応した安全なファイル名を自動生成します。
- ボイスメモのデータベースをread-onlyで読み、原本を変更せず、ネットワーク通信も行いません。

## クイックスタート（GUIアプリ）

GUIアプリは自己完結型で、Python、Homebrew、Tcl/Tkは必要ありません。

1. [GitHub Releases](https://github.com/kimipooh/voice-memos-exporter/releases)ページから `Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip` をダウンロードします。
2. 展開して、`Voice Memos Exporter.app` を `/Applications` へ移動します。
3. アプリを一度開きます。
4. macOSにブロックされた場合は、「システム設定」→「プライバシーとセキュリティ」で「セキュリティ」に移動し、「開く」→「このまま開く」の順にクリックして、ログインパスワードを入力します。このアプリはnotarizeされていないため、Gatekeeperが初回起動をブロックします。詳細は[初回起動がブロックされる](docs/troubleshooting-ja.md#初回起動がブロックされる)を参照してください。
5. アプリをもう一度開きます。
6. フルディスクアクセスを求められたら、「システム設定」→「プライバシーとセキュリティ」→「フルディスクアクセス」を開き、`Voice Memos Exporter.app` を追加してオンにします。これは手順4とは別の権限です。詳細は[フルディスクアクセスが必要](docs/troubleshooting-ja.md#フルディスクアクセスが必要)を参照してください。
7. アプリを完全に終了し、再度開きます。
8. 書き出す録音を選択するか、Select Allを使います。
9. 書き出し先フォルダを選び、**Export Selected** をクリックします。何も書き込まずに確認するには、先に **Dry run** を使います。

## クイックスタート（CLI）

```bash
python3 export_voice_memos.py --help
python3 export_voice_memos.py --list
python3 export_voice_memos.py --all --output ~/Desktop/voice-memos-export
```

例 — 日付範囲を指定して書き出す:

```bash
python3 export_voice_memos.py \
  --all \
  --from 2026-07-01 \
  --to 2026-07-31 \
  --output ~/Desktop/voice-memos-export
```

`--list`、`--all`、`--search` の3つがモードで、少なくとも1つが必要です。すべてのオプションと使用例は [docs/usage-ja.md](docs/usage-ja.md) を参照してください。

## 必要条件

### GUIアプリ

- Apple Silicon（arm64）搭載のmacOS。
- 自己完結型で、Python、Homebrew、Tcl/Tkは不要です。
- `Voice Memos Exporter.app` 自体へのフルディスクアクセス。

### CLI

- ボイスメモのデータが既定の場所にあるmacOS。
- Python 3.9以降。CLIはPython標準ライブラリだけを使います。
- Pythonを実行するターミナルアプリへのフルディスクアクセス。

## 対応環境

| | GUIアプリ | CLI |
|---|---|---|
| macOS | macOS 26.6.2で確認済み。それ以前は未検証 | macOS 26.6.2で確認済み。それ以前は未検証 |
| アーキテクチャ | Apple Silicon（arm64）のみ | Apple Silicon（arm64）で確認済み |
| Intel（x86_64） | 非対応・未検証 | 未検証 |
| Pythonの必要性 | 不要（同梱） | 必要（3.9以降） |
| フルディスクアクセスの許可先 | `Voice Memos Exporter.app` | ターミナルアプリ |

## よくあるトラブル

- **初回起動時にアプリが開かない**（「ゴミ箱に入れる」/「完了」だけが表示される）: アプリがnotarizeされていないため、Gatekeeperがブロックしています。「システム設定」→「プライバシーとセキュリティ」で許可してください。詳細は[初回起動がブロックされる](docs/troubleshooting-ja.md#初回起動がブロックされる)を参照してください。
- **`Voice Memos database not found`**: 通常はボイスメモのデータベースがまだ作成されていないことを示します。Appleのボイスメモアプリを一度開き、このMacに録音があることを確認してください。詳細は[ボイスメモデータベースが見つからない](docs/troubleshooting-ja.md#ボイスメモデータベースが見つからない)を参照してください。

その他の問題は [docs/troubleshooting-ja.md](docs/troubleshooting-ja.md) を参照してください。

## 注意事項と制限

- 既定では「最近削除した項目」を除外します。含める場合は `--include-trash` を指定してください。
- 時刻を省略した `--to` はその日全体を含みます。
- 読み込み処理はAppleの非公開の内部ボイスメモDB schemaに依存するため、将来のmacOS変更で更新が必要になる可能性があります。
- 書き出したファイルはソースの拡張子（一部の録音は `.qta`）を維持し、メディア変換は行いません。
- iCloudだけにある録音はダウンロードされず、ローカルで利用不可として一覧表示・スキップされます。
- アプリはApple Silicon専用です。Intel Macは非対応・未検証です。
- アプリはnotarizeされていません。

## 詳細ドキュメント

| トピック | English | 日本語 |
|---|---|---|
| CLIリファレンス | [usage.md](docs/usage.md) | [usage-ja.md](docs/usage-ja.md) |
| トラブルシューティング | [troubleshooting.md](docs/troubleshooting.md) | [troubleshooting-ja.md](docs/troubleshooting-ja.md) |
| アーキテクチャと設計 | [design.md](docs/design.md) | [design-ja.md](docs/design-ja.md) |
| アプリバンドルのビルド | [gui-packaging.md](docs/gui-packaging.md) | [gui-packaging-ja.md](docs/gui-packaging-ja.md) |
| 変更履歴 | [CHANGELOG.md](docs/CHANGELOG.md) | [CHANGELOG-ja.md](docs/CHANGELOG-ja.md) |
| 貢献方法とテスト | [CONTRIBUTING.md](docs/CONTRIBUTING.md) | [CONTRIBUTING-ja.md](docs/CONTRIBUTING-ja.md) |

[docs/gui-notes.md](docs/gui-notes.md) では、GUIの挙動と手動テストチェックリストを説明しています（英語のみ）。

## 謝辞

Original work © rudrakabir — https://github.com/rudrakabir/voice-memos-exporter

元プロジェクトが役立った場合は、原作者への支援をご検討ください。<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)

## ライセンス

MIT Licenseです。詳細は [LICENSE](LICENSE) を参照してください。

- Original work © 2026 rudrakabir
- Fork modifications © 2026 Kimiya Kitani

帰属の詳細は [NOTICE](NOTICE) を参照してください。
