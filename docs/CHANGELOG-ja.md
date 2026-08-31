# 変更履歴

[English: CHANGELOG.md](CHANGELOG.md)

Voice Memos Exporterの主な変更をこのファイルに記録します。

形式は [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) に基づき、
このプロジェクトは [Semantic Versioning](https://semver.org/spec/v2.0.0.html) に従います。

## [1.1.0] - 2026-08-31

### 追加

- macOS Tkinter GUIをサポート対象のフロントエンドとして復元し、`vmx_core` 上に再構築してGUIとCLIが単一の書き出しエンジンを共有するようにしました。
- PythonとTcl/Tkを同梱し、利用者側にPython、Homebrew、Tkが不要な自己完結型PyInstaller macOSアプリバンドル（`packaging/voice_memos_exporter.spec`、`packaging/build_app.sh`）を追加しました。
- 各録音の音声がdisk上にあるかを示す `Local` 列と、ActiveとRecently Deletedを区別する `Status` 列を追加しました。
- GUIに「Include Recently Deleted」オプションを追加しました。
- ファイルを書き込まずに件数を報告するGUI dry-run modeを追加しました。
- 進捗表示とcancelに対応したbackground export worker、およびTotal / Exported / Skipped / Failedの集計を追加しました。
- upstreamとforkのattributionを示すAbout dialogを追加し、macOS application menuの明示的な項目として登録しました。
- `CFBundleShortVersionString`、`CFBundleVersion`、`CFBundleIdentifier`、`NSHumanReadableCopyright` のapp metadataを追加しました。
- GUI view-model、selection、formatting、packaging smoke testを追加しました。
- `LICENSE`（MIT）と、license、attribution、versionの整合性を確認する `tests/test_release_metadata.py` を追加しました。

### 変更

- upstreamが公開したMIT Licenseを採用し、upstreamのcopyright行を維持しながらforkのcopyright行を追加しました。それに合わせて `NOTICE`、`README.md`、`README-ja.md`、`docs/design.md`、`docs/design-ja.md`、`docs/CONTRIBUTING.md` を更新しました。
- GUI、packaging spec、build script、ドキュメントから公開・再配布の制限を削除しました。
- フルディスクアクセスの案内で、packaged appでは `Voice Memos Exporter.app` に、scriptとCLIではterminal applicationに許可する違いを明確にしました。
- `TOOL_VERSION`、GUIの `APP_VERSION`、app bundle versionを `1.1.0` に統一し、`APP_VERSION` が `vmx_core.TOOL_VERSION` から導出されるようにしました。
- app bundle identifierを `jp.kitani.voicememosexporter` に変更しました。以前のidentifierに対する既存のローカルなフルディスクアクセス許可は再承認が必要です。
- packaging build helperとGUI notes・packaging文書を公開用の名称へ変更しました。

### ドキュメント

- 初回起動時のGatekeeper承認、フルディスクアクセス、`Voice Memos database not found`、ロックされたデータベース、iCloud-onlyの録音、スキップ・失敗した書き出し、Recently Deletedを扱う `docs/troubleshooting.md` と `docs/troubleshooting-ja.md` を追加しました。
- macOS 15 Sequoia以降では、Control-clickではなく「システム設定」→「プライバシーとセキュリティ」からGatekeeperを上書きする必要があることを記載しました。
- 日本語版 `docs/gui-packaging-ja.md`、`docs/CHANGELOG-ja.md`、`docs/CONTRIBUTING-ja.md` を追加し、すべての日英ペアに相互リンクを付けました。
- `README.md` と `README-ja.md` をentry pointとして簡潔にし、CLIの完全なoption reference、使用例、フルディスクアクセスの詳細を `docs/` に移しました。

## [1.0.0-fork] - 2026-08-27

fork tag `v1.0.0` としてreleaseしました。以下のupstream tag `1.0.0` / `1.0.1` は元プロジェクトの履歴です。

upstreamの `1.0.2` tagはupstream changelogに記録されていません。
以下のGUIまたはapp packagingに言及するentryは、その後のCLI-only方針より前に完了した作業を記録しており、続く削除sectionがその後の削除を記録しています。

### 修正

- `ZEVICTIONDATE` に基づき、Recently Deletedの録音を既定のCLI・GUIの一覧、検索、dry-run、書き出しから除外しました。
- 古くなったTreeview item IDを安定したrecording keyに置き換え、検索・filteringをまたいでGUI selectionを保持しました（upstream Issue #7）。
- `/`、`\`、`:`、control character、空の名前、長すぎるUTF-8 filenameをsanitizeし、`/` を含むtitleの書き出し失敗を修正しました（upstream Issue #2）。
- database値とtitle値を安全にcoerceし、数字だけのtitleで `TypeError` が発生しないようにしました。
- 個別の録音が失敗しても処理を続け、Total / Exported / Skipped / Failedを報告するようにしました。
- 表示したtitleとdateで再queryせず、各録音とともに読み込んだsource pathを使うようにしました。
- 生成された出力先が選択したexport directoryの外へ出ないようにしました。

### 変更

- forkはPython command-line interfaceだけに注力する方針へ変更しました。
- 録音の `ZDATE` から書き出しファイルの `mtime` と `atime` を設定しました。creation timeは明示的に設定・保持しません（upstream Issue #1への部分対応）。
- 認識済みのiCloud placeholderを、失敗ではなく未downloadとして分類し、skipするようにしました。
- GUIのcopy処理をworker threadへ移し、progressとcancelに対応しました。
- PyInstaller specで `target_arch='universal2'` を要求しました。Universal 2 buildは未検証のままです（upstream Issue #4）。

### 追加

- `--from` と `--to` によるinclusive date-range filteringを追加しました。date-onlyでのwhole-day処理、local-time比較、list、search、trash inclusion、dry-run、JSON outputとの組み合わせに対応します。
- `Recording.is_trashed`、CLI option `--include-trash`、list status表示、追加JSON `status` 値を追加しました。
- CLIとGUIで共有するdatabase・export layerとして `vmx_core.py` を追加しました。
- 一覧、JSON output、search、full export、dry-run、database override、timestamp control、documented exit codeに対応した `export_voice_memos.py` を追加しました。
- CLI一覧とGUI window titleにrecording countを追加しました（upstream Issue #3）。
- 安全で一意なdestination生成と、録音ごとのdiagnostic logを追加しました。
- read-only database accessと、WAL処理で必要な場合のtemporary snapshotを追加しました。
- missing、permission-denied、incompatible-schema、locked、corrupt、unknownを区別するdatabase diagnosticsを追加しました。
- database access、filename、destination、export、CLI behavior、GUI selectionの `unittest` regression coverageを追加しました。

### 削除

- Tkinter GUIとGUI-only testを削除しました。
- PyInstaller/macOS app packaging fileと関連image assetを削除しました。
- packaging時のPyInstaller dependencyだけを含んでいた `requirements.txt` を削除しました。CLIはPython standard libraryだけを使います。

### セキュリティ

- Voice Memos databaseをread-onlyで開き、元のdatabaseと録音を変更しないようにしました。
- network communication、telemetry、analytics、data collectionは追加していません。
- diagnostic logは利用者が選んだoutput directory内に保持します。logにはmetadataとpathが含まれますが、音声は含まれません。

### ドキュメント

- `README.md` と `README-ja.md` を短いentry point（機能、必要条件、quick start、主な例、主なoption、注意事項・制限、documentation link）へ整理し、詳細なCLI referenceと内部design noteを新しい `docs/usage.md` / `docs/usage-ja.md` と `docs/design.md` / `docs/design-ja.md` へ移しました。
- `docs/audit/` をGit trackingから外し（ローカルには保持し、`.gitignore` に追加）、`README.md`、`README-ja.md`、`docs/design.md`、`docs/design-ja.md`、`docs/CONTRIBUTING.md` からpublic linkを削除しました。license wordingはこれに依存しない表現へ変更しました。
- `README-ja.md`、`docs/usage-ja.md`、`docs/design-ja.md` のheadingと説明を日本語proseへ統一し、CLI option、code identifier、literal CLI outputは元の形式を維持しました。
- fork modificationとKimiya Kitaniによる新規コードのcopyright noticeを記録する `NOTICE` fileと、`README.md` / `README-ja.md` の短いCopyright sectionを追加しました。

## [1.0.1] - 2024-12-17

### 修正
- 検索機能が結果を正しくrefreshするようにしました
- 書き出したfilenameが元の録音と一致しない問題を修正しました
- file namingの一貫性を改善しました

## [1.0.0] - 2024-12-16

### 追加
- 初回release
- 一括書き出し機能
- 検索機能
- 書き出しprogress tracking
- duplicate file向けのsmart naming
- フルディスクアクセス対応
- privacyを重視したローカル動作
