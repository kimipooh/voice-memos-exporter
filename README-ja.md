# Voice Memos Exporter

[English: README.md](README.md)

これは [rudrakabir/voice-memos-exporter](https://github.com/rudrakabir/voice-memos-exporter)（作者: [rudrakabir](https://github.com/rudrakabir)）の開発中のforkです。macOSのボイスメモを一括書き出しできる有用なツールを作った原作者に感謝します。このforkでは、GUIアプリとPython CLIの両方からmacOSのボイスメモを信頼性高く一括書き出しできます。

このforkは、1つの共通書き出しコア上にmacOS GUIアプリとPythonコマンドラインインターフェースの2つのフロントエンドを提供します。どちらもMIT Licenseです。

## 主な機能

- 全録音、またはタイトル・日付で絞り込んだ録音を、指定したフォルダへ書き出します。
- GUIで Title / Date / Duration / Local / Status 列の録音一覧、タイトル検索、「Include Recently Deleted」を利用できます。
- GUIで Select All / Deselect All、dry runによるプレビューを利用できます。
- GUIは書き出し進捗を表示し、キャンセルできます。
- 両方のフロントエンドで最終的な Total / Exported / Skipped / Failed の集計を表示します。
- 1件が失敗しても処理を止めず、Total / Exported / Skipped / Failed を報告します。
- `/` を含むタイトルや数字だけのタイトルなど、元のツールで書き出しが止まっていたケースも含め、安全なファイル名を自動生成します。
- ボイスメモのデータベースをread-onlyで読み、原本を変更しません。
- ネットワーク通信、テレメトリ、データ収集を行いません。

## クイックスタート（GUIアプリ）

GUIアプリは自己完結型です。Python、Homebrew、Tcl/Tkは必要ありません。

1. GitHub Releasesページから `Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip` をダウンロードし、展開します。
2. `Voice Memos Exporter.app` を `/Applications` へ移動します。
3. 一度開きます。macOSがボイスメモデータを読み込めないことを報告します。
4. システム設定 → プライバシーとセキュリティ → フルディスクアクセスを開き、`+` をクリックして `Voice Memos Exporter.app` を追加します。スイッチがオンであることを確認します。
5. アプリを終了し、再度開きます。
6. 書き出す録音を選択するか、Select Allを使います。
7. 書き出し先フォルダを選び、**Export Selected** をクリックします。何も書き込まずにプレビューする場合は、先に **Dry run** を使ってください。

このアプリはnotarizeされていないため、初回起動時にmacOSのシステム設定 → プライバシーとセキュリティから起動を許可する必要があります。

## 必要条件

### GUIアプリ

- Apple Silicon（arm64）搭載のmacOS。
- 自己完結型で、Python、Homebrew、Tcl/Tkは不要です。
- `Voice Memos Exporter.app` 自体へのフルディスクアクセス。

### CLI

- ボイスメモのデータが既定の場所にあるmacOS。
- Python 3.9以降。CLIはPython標準ライブラリだけを使い、サードパーティ依存はありません。
- Pythonを実行するターミナルアプリへのフルディスクアクセス（Full Disk Access）。

### フルディスクアクセス

ボイスメモのデータはmacOSのプライバシー保護機能で保護されています。実際にPythonを起動するターミナルアプリ（Terminal、iTerm、IDEの統合ターミナルなど）に、システム設定 → プライバシーとセキュリティからフルディスクアクセスを許可し、そのアプリを再起動してください。権限が不足している場合、CLIは案内を表示して終了コード1で終了します。

## 対応環境

| | GUIアプリ | CLI |
|---|---|---|
| macOS | macOS 26.6.2で確認済み。それ以前のバージョンは未検証 | macOS 26.6.2で確認済み。それ以前のバージョンは未検証 |
| アーキテクチャ | Apple Silicon（arm64）のみ | Apple Silicon（arm64）で確認済み |
| Intel（x86_64） | 非対応・未検証 | 未検証 |
| Pythonの必要性 | 不要（同梱） | 必要（3.9以降） |
| フルディスクアクセスの許可先 | `Voice Memos Exporter.app` | ターミナルアプリ |

## クイックスタート（CLI）

```bash
python3 export_voice_memos.py --help
python3 export_voice_memos.py --list
python3 export_voice_memos.py --all --output ~/Desktop/voice-memos-export
```

## よく使う例

日付範囲を指定して書き出す:

```bash
python3 export_voice_memos.py \
  --all \
  --from 2026-07-01 \
  --to 2026-07-31 \
  --output ~/Desktop/voice-memos-export
```

「最近削除した項目」も含めて書き出す:

```bash
python3 export_voice_memos.py \
  --all \
  --include-trash \
  --output ~/Desktop/voice-memos-export
```

何も書き込まずに結果だけ確認する:

```bash
python3 export_voice_memos.py --all --dry-run --output ~/Desktop/voice-memos-export
```

## 主なオプション

| オプション | 意味 |
|---|---|
| `--list` | 書き出さずに録音を一覧表示します。 |
| `--all` | 全録音を書き出します。 |
| `--search TEXT` | 大文字小文字を区別しない部分一致でタイトルを絞り込みます。 |
| `--from DATE`, `--to DATE` | 録音日時で絞り込みます（`YYYY-MM-DD[ HH:MM[:SS]]`）。 |
| `--include-trash` | 「最近削除した項目」の録音を含めます。 |
| `--dry-run` | 何も書き込まずに書き出し結果を表示します。 |
| `--json` | `--list` の結果をJSONで出力します。 |
| `--output DIR`, `-o DIR` | 書き出し先ディレクトリです。 |

`--list`、`--all`、`--search` の3つがモードで、少なくとも1つが必要です。オプションの完全な一覧、一覧・書き出し結果の形式、終了コードは [docs/usage-ja.md](docs/usage-ja.md) を参照してください。

## 注意事項と制限

- 既定では「最近削除した項目」を除外します。含める場合は `--include-trash` を指定してください。
- 時刻を省略した `--to` はその日全体を含みます。
- 読み込み処理はAppleの非公開の内部ボイスメモDB schemaに依存するため、将来のmacOS変更で動かなくなる可能性があります。
- 書き出したファイルはソースの拡張子（一部の録音は `.qta`）を維持し、メディア変換は行いません。
- iCloudだけにある録音はダウンロードされず、ローカルで利用不可として一覧・スキップされます。
- アプリはApple Silicon専用です。Intel Macは非対応・未検証です。
- アプリはnotarizeされていません。

## 詳細ドキュメント

- [docs/usage-ja.md](docs/usage-ja.md) — CLIの完全なリファレンスと挙動の詳細
- [docs/design-ja.md](docs/design-ja.md) — アーキテクチャと内部実装ノート
- [docs/gui-notes.md](docs/gui-notes.md) — GUIの挙動と手動テストチェックリスト
- [docs/gui-packaging.md](docs/gui-packaging.md) — アプリバンドルのビルド方法
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — 変更履歴
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — 貢献方法とテストの実行方法

## 謝辞

Original work © rudrakabir — https://github.com/rudrakabir/voice-memos-exporter

元プロジェクトが役立った場合は、原作者への支援をご検討ください。<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)

## ライセンス

MIT License です。詳細は [LICENSE](LICENSE) を参照してください。

- Original work © 2026 rudrakabir
- Fork modifications © 2026 Kimiya Kitani

帰属の詳細は [NOTICE](NOTICE) を参照してください。
