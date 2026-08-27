# Voice Memos Exporter

[English: README.md](README.md)

これは [rudrakabir/voice-memos-exporter](https://github.com/rudrakabir/voice-memos-exporter)（作者: [rudrakabir](https://github.com/rudrakabir)）の開発中のforkです。macOSのボイスメモを一括書き出しできる有用なツールを作った原作者に感謝します。このforkでは、書き出しの信頼性を改善し、Pythonのコマンドラインツールとして利用できるようにしています。

upstreamのライセンスは現在不明確です。このforkを独立したReleaseやバイナリ配布物として提供していません。詳しくは[ライセンス](#ライセンス)を参照してください。

元プロジェクトが役立った場合は、原作者への支援をご検討ください。<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)

## このforkを作った理由

upstreamコードの監査で、次の再現可能な不具合を特定しました。

- **検索後の `"Item ... not found"`（upstream Issue #7）:** 選択状態をTkinter Treeviewのitem IDで保持していましたが、フィルタ処理が行を削除・再作成するためIDが無効になっていました。Tkは `I%03X` 形式の連番をIDに使います。報告された `I16CD` は、そのセッションで5,837番目に作成された行です。録音件数が多いMacほど発生しやすい問題でした。
- **タイトルに `/` があると書き出しが中断（upstream Issue #2）:** タイトルがサニタイズされず、`os.path.join()` が `/` をディレクトリ区切りとして扱っていました。
- **数字だけのタイトルで書き出しが中断:** Tkinterは `2026` のようなTreeview値を `int` に変換することがあり、その後の `os.path.basename(int)` が `TypeError` を送出していました。

upstreamで配布された1.0.2バイナリは、後に追加された録音単位の `try/except` より前のtag `1.0.2` からビルドされていました。そのため、1件の失敗で書き出し全体が止まりました。

## 変更内容

- 選択状態をデータベース由来の安定した識別子（`Z_PK`、`ZUNIQUEID`、または `ZPATH`）で保持し、検索やフィルタで無効にならないようにしました。
- 表示中のタイトルと日時でデータベースを再検索せず、録音の読み込み時に取得したソースパスを使います。同じタイトル・日時の録音を取り違えません。
- macOSで安全なファイル名を生成します。`/`、`\`、`:` を置換し、制御文字とNULを除去し、前後の空白とドットを取り除きます。空文字、`.`、`..` には代替名を使い、ファイル名本体をUTF-8バイト長で制限します。既存名との重複は `name_1.m4a` のような連番で回避します。
- 出力先が選択したディレクトリ内に収まることを毎回検証します。
- 1件が失敗しても残りを処理し、**Total / Exported / Skipped / Failed** を表示します。
- 1件以上のスキップまたは失敗がある場合、`voice-memos-exporter-YYYYMMDD-HHMMSS.log` という診断ログの作成を試みます。
- SQLiteデータベースをread-onlyで開きます。WAL処理に必要な場合はデータベースとサイドカーファイルを一時スナップショットへコピーし、読み込み後に削除します。
- データベースの問題を「見つからない、権限不足、スキーマ非対応、使用中、破損、不明」に分類します。Full Disk Accessの案内は権限エラーの場合だけ表示します。
- iCloudプレースホルダを**未ダウンロード**として認識し、`File not available locally` でスキップします。このツールはiCloudからのダウンロードを開始しません。
- 書き出し時に録音の `ZDATE` を使い、更新日時（`mtime`）とアクセス日時（`atime`）を明示的に設定します（upstream Issue #1への部分対応）。
- 書き出しとデータベースの共通ロジックを `vmx_core.py` に置き、coreとCLIに回帰テストを追加しました。
- CLIの一覧に録音件数を表示します（upstream Issue #3）。

## 要件と互換性

- ボイスメモのデータが `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/` にあるmacOS。
- Python 3.9以降。CLIはPython標準ライブラリだけを使い、サードパーティの実行時依存はありません。
- ボイスメモデータベースを読むプロセスへのFull Disk Access。

### Pythonソースの互換性

ソースはPython標準ライブラリだけを使い、アーキテクチャ依存コードを含みません。Apple Silicon上のPython 3.9.6でCLI/coreテストを確認しています。Intel Macでのソース実行は未検証です。

## Full Disk Access

ボイスメモのデータはmacOSのTCCで保護されており、Full Disk Accessが必要になる場合があります。Terminal、iTerm、IDEの統合ターミナルを提供するアプリなど、実際にPythonを起動するターミナルアプリへ権限を与えてください。`python3` バイナリ単体を追加するのではありません。

設定項目の名称や場所はmacOSのバージョンによって異なる場合があります。プライバシーとセキュリティの設定で対象のターミナルアプリにFull Disk Accessを許可し、変更を反映するためにそのアプリを再起動してください。

権限があっても、データベースはread-onlyで開きます。CLIが `DbStatus.PERMISSION_DENIED` を検出するとFull Disk Accessの案内を表示し、終了コード1で終了します。データベース不在やスキーマ非対応には別の診断を表示します。

## コマンドライン

CLIはこのforkで唯一サポートするインターフェースです。

```bash
python3 export_voice_memos.py --help
python3 export_voice_memos.py --list
python3 export_voice_memos.py --list --include-trash
python3 export_voice_memos.py --list --search "Project"
python3 export_voice_memos.py --all --output ~/Desktop/voice-memos-export
python3 export_voice_memos.py --search "Project" --output ~/Desktop/VoiceMemos
python3 export_voice_memos.py --all --dry-run --output ~/Desktop/VoiceMemos
```

「最近削除した項目」を含めて書き出す例:

```bash
python3 export_voice_memos.py \
  --all \
  --include-trash \
  --output ~/Desktop/voice-memos-export
```

2026年7月の録音だけを書き出す例:

```bash
python3 export_voice_memos.py \
  --all \
  --from 2026-07-01 \
  --to 2026-07-31 \
  --output ~/Desktop/voice-memos-export
```

`--list`、`--all`、`--search` の少なくとも1つが必要です。`--list --search TEXT` は一致した録音だけを一覧表示します。`--list` がなければ、`--all` または `--search` が書き出しを実行するため、`--output` が必要です。

既定では「最近削除した項目」の録音を一覧、検索、dry-run、書き出しから除外します。含める場合は `--include-trash` を指定します。内部では `ZCLOUDRECORDING.ZEVICTIONDATE` からこの状態を判定します。

| オプション | 意味 |
|---|---|
| `-h`, `--help` | helpを表示して終了します。 |
| `--list` | 書き出さずに録音を一覧表示します。 |
| `--all` | 全録音を書き出します。 |
| `--search TEXT` | Unicode正規化を行い、大文字小文字を区別しない部分一致でタイトルを絞り込みます。 |
| `--from DATE` | `DATE` 以降（指定日時を含む）の録音に絞り込みます。形式は `YYYY-MM-DD`、`YYYY-MM-DD HH:MM`、`YYYY-MM-DD HH:MM:SS` です。 |
| `--to DATE` | 同じ形式の `DATE` 以前（指定日時を含む）の録音に絞り込みます。時刻を省略するとその日全体を含みます。 |
| `--output DIR`, `-o DIR` | 書き出し先ディレクトリです。 |
| `--dry-run` | ソースと出力先を解決して結果を表示しますが、書き出しファイル、ログ、出力ディレクトリを作りません。 |
| `--json` | `--list` の結果を1つのJSON配列として出力します。 |
| `--include-trash` | 「最近削除した項目」の録音を含めます。テキスト一覧には `STATUS` 列を追加します。 |
| `--db PATH` | ボイスメモデータベースのパスを上書きします。 |
| `--no-set-times` | 書き出したファイルの `mtime` と `atime` を設定しません。 |
| `--version` | ツールのバージョンを表示して終了します。 |

日付範囲の片側だけでも指定できます。`--all`、`--search`、`--include-trash`、`--list`、`--dry-run`、`--json` と組み合わせられ、タイトルと日付の条件はANDで適用されます。入力日時はローカル時刻として解釈し、CLIが `ZDATE` から生成して表示する `DATE` 列と同じ基準で比較します。

終了コード:

| code | 意味 |
|---|---|
| `0` | 成功。検索一致が0件の `--list`、またはスキップも失敗もない書き出しを含みます。 |
| `1` | 致命的エラー。引数不正、データベース/出力先エラー、書き出し時の検索一致0件、または中断です。 |
| `2` | 書き出しを完了したものの、1件以上のスキップまたは失敗がありました。 |

### 一覧出力

テキスト出力は次の形式です（以下のタイトルは架空です）。

```text
Total recordings: 3 (matched: 2)
KEY                DATE             DURATION LOCAL   TITLE
pk:101             2026-08-27 10:00     0:42 yes     Project kickoff
pk:102             2026-08-26 15:30  1:02:03 icloud  Project interview
```

`LOCAL` は3つの状態を区別します。

| 値 | 意味 |
|---|---|
| `yes` | 音声ファイルをローカルで利用できます。 |
| `icloud` | iCloudプレースホルダはありますが、録音はローカルに未ダウンロードです。これを `missing` とは呼びません。書き出し時はスキップします。 |
| `missing` | データベース行はありますが、ローカルファイルもiCloudプレースホルダも見つかりません。書き出し時は失敗として扱い、残りを続行します。 |

`--json` を指定すると、stdoutにはJSON配列だけを出力します。0件一致の `--list --json --search TEXT` は `[]` を返し、終了コードは0です。
各録音オブジェクトには追加フィールド `status` が含まれ、値は `active` または `trash` です。
`--include-trash` 指定時のテキスト出力にも同じ値の `STATUS` 列を追加し、既定のテキストレイアウトは変更しません。

### 書き出し結果と診断情報

書き出しは録音ごとに1行を出力し、その後にTotal、Exported、Skipped、Failed件数を表示します。`--dry-run` は結果行に `[dry-run]` を付け、成功見込みを `would export` と表示します。音声、診断ログ、出力ディレクトリなど、書き出しファイルは一切作りません。一覧表示や実際の書き出しと同様、安全なread-only WAL処理のために一時データベーススナップショットを作る場合がありますが、読み込み終了時に削除します。

実際の書き出しでは、1件以上のスキップまたは失敗がある場合だけ、選択した出力先への診断ログ作成を試みます。作成に成功するとパスを表示します。JSON Lines形式の各レコードには、録音識別子、タイトル、ソースパス、出力先パス、結果、例外の型、例外メッセージが含まれます。このためログには私的なタイトルやパスが含まれ得ますが、音声そのものは含まず、外部へ送信しません。

## Architecture

```text
Voice Memos DB / files
        ↓
    vmx_core.py
        ↓
export_voice_memos.py
```

`vmx_core.py` は信頼性の中心で、データベースの診断と読み込み、ソース解決、安全な出力先生成、書き出し、診断ログを担当します。`export_voice_memos.py` がその機能のコマンドラインインターフェースを提供します。

## 書き出したファイルの日時と形式

このツールが明示的に設定するのは、`ZDATE` の録音日時に合わせた更新日時（`mtime`）とアクセス日時（`atime`）だけです。作成日時（`birthtime`）は設定も保持もしません。APFS/HFS+では、設定した `mtime` がコピー直後の作成日時より古い場合、ファイルシステムの副作用としてFinderの「作成日」も同じ値まで下がることがよくあります。`os.utime()` が作成日時を設定しているわけではなく、録音日時がコピー時刻より後の場合には作成日時は後ろへ動きません。録音日時は書き出しログと `--list` でも確認できます。これはupstream Issue #1への部分対応です。

実機のボイスメモデータベースで確認した録音は `.qta` 拡張子で、QuickTimeコンテナ（`ftypqt  `）でした。内容を誤って表示する名前にしないため、exporterはソースの拡張子を維持します。プレーヤーが `.qta` を開けない場合は、書き出し後に別途変換してください。

## プライバシーと安全性

- ネットワーク通信、テレメトリ、分析、データ収集を一切行いません。
- ボイスメモデータベースへ書き込まず、元の録音を名前変更、削除、移動、変更しません。
- データの流れは、データベースを読む、音声ファイルを読む、選択した出力先へコピーする、の3段階です。安全にWALを扱うため一時read-onlyスナップショットを使う場合があり、処理後に削除します。
- 診断ログは選択した出力先だけに書き、タイトルとパスを含みますが音声は含まず、外部へ送信しません。

## 開発とテスト

```bash
python3 -m unittest discover -s tests -t .
```

テストスイートは標準ライブラリの `unittest` を使い、pytestは不要です。

テストはデータベースアクセス、一覧、検索、日付filter、trash処理、dry-run、JSON出力、安全なファイル名、重複名、部分失敗、read-only動作をカバーします。ディスプレイ環境には依存しません。

## 既知の制限

- upstreamのライセンスが未解決のため、このforkにはReleaseもバイナリ配布もありません。
- Intel Macでのソース実行は未検証です。
- readerは、「最近削除した項目」の判定に使う `ZCLOUDRECORDING.ZEVICTIONDATE` など、Appleの非公開の内部ボイスメモDB schemaに依存します。将来のmacOS変更には追随が必要になる場合があります。
- 書き出した録音は `.qta` を含むソースの拡張子を維持し、メディア変換を行いません。
- 作成日時（`birthtime`）は設定も保持もせず、`mtime` と `atime` だけを明示的に設定します。
- iCloudだけにある録音をダウンロードしません。認識できたプレースホルダをスキップするだけです。

## ライセンス

upstream projectには `LICENSE` ファイルがなく、GitHubもlicenseを認識していません。licenseへの言及は `docs/CONTRIBUTING.md` の、contributionが “under its MIT License” でlicenseされるという記述だけですが、repositoryにMIT license本文はありません。

そのため、このコードのライセンスは**不明確**です。このforkは次の方針を取ります。

- 原作者の著作物をlicenseする権限がないため、独自の `LICENSE` ファイルを追加しません。
- 独立したReleaseまたはバイナリ配布物として**公開しません**。
- 個人利用と、修正をupstreamへ還元するための土台となる開発中のforkとして扱います。

upstream作者へ明示的な `LICENSE` の追加を依頼する[Issueドラフト](docs/audit/upstream-license-issue-draft.md)を用意しました。解決するまでは、このforkのビルドを再配布しないでください。

Original work © rudrakabir — https://github.com/rudrakabir/voice-memos-exporter

元プロジェクトが役立った場合は、原作者への支援をご検討ください。<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)
