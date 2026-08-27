# Phase 1 — Audit Report (voice-memos-exporter)

対象: https://github.com/rudrakabir/voice-memos-exporter
監査時点の upstream HEAD: `0f549f2` (main) / リリース tag: `1.0.2`
監査日: 2026-08-27
**この Phase ではコードを一切変更していない。**

---

## 1. Repository structure

```
voice_memos_exporter.py     15 KB  単一ファイル / 全ロジック
voice_memos_exporter.spec    1 KB  PyInstaller spec
requirements.txt                   pyinstaller==6.3.0 のみ
create_icns.sh / icon.icns / app_icon.png / screenshot.png
README.md
docs/CHANGELOG.md, docs/CONTRIBUTING.md, docs/*.png
Screenshot/
.gitignore
LICENSE                     ★存在しない（後述）
```

- テストコードは**存在しない**（`tests/` なし、CI なし、`.github/` なし）。
- `requirements.txt` は pyinstaller のみ。実行時依存は Python 標準ライブラリ（tkinter/sqlite3/shutil）のみ。

### commit 履歴 (14 commits)

```
0f549f2 Merge pull request #6 from conanm/fix/export-errors-and-select-all
824cfaa Fix export error handling and Select All highlighting, clean up build artifacts
543e906 Merge branch 'main'
1aa795c 1.0.2, fixed full disk acccess stuff        <-- tag 1.0.2 はここ
...
1e08dee init
```

### ★重要: 配布バイナリ 1.0.2 は main とは別物

`git log 1.0.2..main` = `824cfaa` の 1 commit。
つまり **PR #6（per-recording try/except と Select All 修正）は 1.0.2 リリースに入っていない**。
Issue #7 / #2 の報告者が使ったのは tag `1.0.2` のコード、すなわち
`export_selected()` のループに **try/except が無い** 版である。
これが「1 件のエラーで export 全体が中断する」症状の直接的な理由。

---

## 2. Architecture

単一クラス `VoiceMemosExporter`（tkinter GUI）。レイヤ分離なし。

| メソッド | 役割 |
|---|---|
| `__init__` | `db_path` 決め打ち、`selected_items = set()`、`search_var.trace_add('write', filter_recordings)` |
| `load_recordings()` | DB 全件 SELECT → Treeview へ insert |
| `filter_recordings()` | 検索キー入力の**都度** Treeview 全削除 → DB 再 SELECT → 再 insert |
| `on_click` / `toggle_item` | 4列目クリックで `selected_items` に **Treeview item ID** を出し入れ |
| `select_all` / `deselect_all` | 同上 |
| `export_selected()` | `selected_items` の item ID → Treeview から title/date 文字列を取得 → **その文字列で DB を再検索** → ZPATH 取得 → `shutil.copy2` |

問題の本質は **「録音の同一性」を Treeview の内部 item ID と表示文字列で表現している**こと。
永続的な recording identity（`Z_PK` / `ZUNIQUEID` / `ZPATH`）を保持する内部モデルが存在しない。

```
現状:  DB --(表示文字列のみ)--> Treeview --(item ID / 表示文字列)--> DB 再検索 --> copy
あるべき: DB --> Recording model(stable id, path) --> Treeview(表示のみ)
```

---

## 3. Voice Memos DB へのアクセス方法

```python
self.db_path = os.path.expanduser(
    "~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db")
self.recordings_path = os.path.dirname(self.db_path)
conn = sqlite3.connect(self.db_path)          # ★read-write で open している
cursor.execute("SELECT ZPATH, ZENCRYPTEDTITLE, ZDATE, ZDURATION FROM ZCLOUDRECORDING ORDER BY ZDATE DESC")
```

問題点:

- **read-only で開いていない**。`sqlite3.connect(path)` は書き込み可能で open し、WAL の場合は
  `-shm` / `-wal` を作成/更新しうる。Full Disk Access を持つアプリが Apple の DB を
  書き込み可能で掴むのは設計として不適切。→ `file:...?mode=ro&immutable=0` (URI mode) にすべき。
- SELECT は 3 箇所（`load_recordings`, `filter_recordings`, `export_selected`）に重複。
- `Z_PK` / `ZUNIQUEID` を **一切取得していない**。
- schema 差異の検査なし（テーブル/カラム欠如で `sqlite3.OperationalError`）。
- `ZDATE`/`ZDURATION` が NULL の場合 `timedelta(seconds=None)` → `TypeError`（`sqlite3.Error` では捕まらず、
  `load_recordings` の 2 番目の `except Exception` に落ちて全件ロード失敗）。

### 本 Mac での実測（Full Disk Access 未付与状態）

```
os.path.exists(db)                -> True         ★存在判定は通る
open/sqlite3 で読む               -> sqlite3.DatabaseError: authorization denied
ls Recordings/                    -> Operation not permitted
```

→ **「DB が存在するか」だけでは権限の有無を判定できない**。実 read を試すまで分からない。
（Phase 1 時点で当環境には FDA を付与していないため、実 schema（`Z_PK`/`ZUNIQUEID` の
有無）の実測は未実施。§14 の未解決事項参照。）

---

## 4. Export 処理フロー（tag 1.0.2 = 配布版）

```
selected_items (Treeview item ID の set) を反復
  └ values = tree.item(item)['values']        ← ★ item が消えていると TclError
      title    = values[0]                    ← ★ Tk が型変換する（後述）
      date_str = values[1]
  └ SELECT ZPATH FROM ZCLOUDRECORDING
      WHERE datetime(ZDATE + 978307200,'unixepoch') = date_str
        AND (ZENCRYPTEDTITLE = title OR ZPATH LIKE '%'||basename(title)||'%')
      → fetchone()                            ← ★ 同一秒/同一タイトルで多重一致し得る
  └ source = recordings_path/ZPATH
  └ if os.path.exists(source):                ← ★ iCloud 未 DL と真の欠損を区別できない
        dest = export_dir + "/" + title + ext ← ★ サニタイズなし
        while exists: name_N を付与
        shutil.copy2(source, dest)            ← ★ birthtime は保持されない
```

tag 1.0.2 では try/except が無いため、**どこか 1 箇所で例外が出るとループごと抜け**、
外側の `except Exception as e: messagebox.showerror("Error", f"...{e}")` に到達する。

main (PR #6 後) では per-item `except Exception: failed.append(title)` が入ったが、
**例外情報を完全に握りつぶす**ため診断不能。

---

## 5. GitHub Issues とコードの対応

| Issue | 症状 | コード上の原因（確定） | 確度 |
|---|---|---|---|
| #7 | `"Item 16CD not found"` | stale Treeview item ID → `tree.item()` が `TclError` | **実測で確定** (§6-A) |
| #2 | タイトルに `/` で export が中断 | `os.path.join(export_dir, f"{title}{ext}")` にサニタイズ無し → `FileNotFoundError` | **実測で確定** (§6-B) |
| #4 | Intel Mac で起動しない | `.spec` の `target_arch=None` → ビルドホスト(arm64)専用バイナリ | **コード上で確定** (§10) |
| #1 | export 後の作成日が export 日時 | `shutil.copy2` は mtime/atime は複製するが **birthtime は複製しない** | **確定** (§12) |
| #3 | ファイル件数表示が欲しい | 機能要望（バグではない） | — |
| PR #5 | datetime metadata 付与（未マージ） | Issue #1 対応案 | — |

---

## 6. 再現可能な bug（実測ログ）

### A. Issue #7 = stale Treeview item ID（**根本原因確定**）

`selected_items` は Treeview の内部 item ID を保持する。
一方 `filter_recordings()` は検索欄への **1 打鍵ごとに**

```python
self.tree.delete(*self.tree.get_children())   # 旧 item ID を無効化
... self.tree.insert(...)                     # 新しい item ID を採番
```

を実行する。`selected_items` は一切更新されないため、旧 ID が残留する。
その後 `export_selected()` が `self.tree.item(item)` を呼ぶと `TclError` になる。

実測（`python3` + tkinter、当環境）:

```
first ids:    ['I001', 'I002', 'I003']
after reload: ['I004', 'I005', 'I006']
tree.item('I001') -> TclError: Item I001 not found
挿入 5836 件目の item ID -> 'I16CC'
```

- Tk の item ID は `I%03X`（16進連番）。→ Issue #7 の `16CD` は **`I16CD`** であり、
  「セッション中に 5837 個目に生成された Treeview 行」を指す。
  報告者の先頭 `I` の欠落は転記漏れと解釈できる。
- 録音 N 件 × 検索リロード回数だけ連番が進むので、
  **録音件数が多い Mac ほど到達しやすい**（= 「あるMacでは成功、別のMacで失敗」の説明になる）。
- tag 1.0.2 には per-item try/except が無いため、この `TclError` が
  外側 handler まで飛び **`An error occurred during export: Item I16CD not found`** と表示される。
  Issue #7 の文言と完全に一致する。

#### 付随バグ: `checked_items` の型不一致（ユーザ指摘どおり）

```python
checked_items = {item for item in self.tree.get_children()
                 if self.tree.item(item)['values'][3] == '☑'}   # ← Treeview item ID の集合
...
check_mark = '☑' if path in checked_items else '☐'               # ← 比較対象は ZPATH 文字列
```

`path`（例 `'20240910 160000.m4a'`）が item ID 集合（`{'I004', ...}`）に含まれることは
**構造上あり得ない**。したがって:

- 検索するとチェックマークは**必ず全部消える**（見た目上は選択解除されたように見える）。
- しかし `selected_items` にはチェックが残ったままなので、
  **ユーザには見えない選択が export 対象として残る**。
- さらにその ID は既に削除済み → `TclError`。

つまり「選択が消えたように見えるのに export でエラーになる」という Issue #7 の体験と整合する。

### B. Issue #2 = ファイル名サニタイズ欠如（**根本原因確定**）

`dest_path = os.path.join(export_dir, f"{title}{ext}")` を実測:

```
FAIL 'Interview / Hanoi'  -> FileNotFoundError: .../export/Interview / Hanoi.m4a
OK   '../escaped'         -> export_dir の外に書き込まれた（inside_export=False）★traversal
OK   ''                   -> '.m4a'（不可視ファイル）
OK   '  spaced  '         -> '  spaced  .m4a'（前後空白がそのまま）
OK   '.'                  -> '..m4a'
FAIL 'x'*300              -> OSError [Errno 63] File name too long
（絶対パス風タイトル）    -> os.path.join(export_dir, '/tmp/pwned.m4a') == '/tmp/pwned.m4a' ★脱出
```

- `/` は macOS の POSIX 層ではディレクトリ区切り。Voice Memos の UI 上は `/` を含む
  タイトルを許すため、DB には `/` を含む `ZENCRYPTEDTITLE` が入り得る。
- tag 1.0.2 では `FileNotFoundError` がループを抜けて export 全体を中断 → Issue #2 の「cancel the export」。

### C. ★新発見: 数字のみのタイトルで `TypeError`（Issue #7 のもう 1 つの原因候補）

Tkinter の Treeview は値を Tcl オブジェクト経由で返すため、**型が保存されない**。実測:

```
'New Recording 1' -> str
'20240910'        -> int        ★ os.path.basename(int) -> TypeError
'007'             -> int (7)    ★ 値も壊れる（ゼロ埋めが消える）
'1.5'             -> str
'会議 メモ'        -> str
```

`export_selected()` は `os.path.basename(title)` を呼ぶので、
**タイトルが数字のみの録音が 1 件でも選択されていると `TypeError` が発生**する。
tag 1.0.2 ではここで export 全体が中断する。
（Voice Memos は日付ベースの既定名や、ユーザが `20240910` のように改名した録音で普通に起こり得る。）

さらに `ZENCRYPTEDTITLE = 20240910`（整数）は SQLite の型親和性により
TEXT 列 `'20240910'` と一致しないため、仮に例外を免れても検索が失敗する。

---

## 7. 潜在 bug（未報告だが実コードで説明できるもの）

| # | 箇所 | 内容 |
|---|---|---|
| P1 | `export_selected` | `fetchone()`：同一秒・同一タイトルの録音が複数あると**同じ 1 件を重複 export**し、他方は取りこぼす |
| P2 | `export_selected` | `ZPATH LIKE '%'||basename(title)||'%'`：title 内の `%` `_` が LIKE ワイルドカードとして解釈される |
| P3 | `export_selected` | `ZENCRYPTEDTITLE IS NULL` の録音では `= ?` が常に偽。`LIKE` 側頼みで、basename に `/` があると崩れる |
| P4 | `load_recordings` / `filter_recordings` | `ZDATE`/`ZDURATION` が NULL → `timedelta(seconds=None)` で `TypeError` → **一覧ロード全体が失敗** |
| P5 | `filter_recordings` | `self.tree.item(item)['values'][3]` — values が 4 要素未満だと `IndexError` |
| P6 | 全体 | 表示日時は Apple epoch を **UTC のまま** 表示している（`datetime(2001,1,1)+timedelta`）。ローカル時刻ではない。DB 再検索側 (`unixepoch`) も UTC なので現状は整合するが、表示としては誤り |
| P7 | `export_selected` | `shutil.copy2` を **Tk メインスレッド**で実行。`progress_window.update()` のみで、数百〜数千件では UI が実質フリーズ。cancel 不可 |
| P8 | `export_selected` | 重複名解決の `while os.path.exists()` は O(n²)。同名多数で低速。TOCTOU あり |
| P9 | `load_recordings` | `except sqlite3.Error:` を**すべて FDA 不足**として `show_permissions_dialog()`。schema 差異・DB 破損・locked も同じ扱い |
| P10 | `load_recordings` | DB ファイル不在（Voice Memos 未使用の Mac）は `sqlite3.connect` が空 DB を**新規作成**しうる → その後 `no such table` |
| P11 | `filter_recordings` | 打鍵ごとに全件 SELECT + 全件 insert。数千件では入力が重くなる |
| P12 | `export_selected` | `os.path.exists(source)` のみ。iCloud 未ダウンロードと真の欠損を区別しない |
| P13 | 全体 | 一覧は `if path:` で `ZPATH` が NULL/空の行を**黙って除外**。ユーザには件数の食い違いが見えない |

### ★「同僚の Mac だけ途中で止まる」を説明できる要因（優先順）

1. **stale item ID (`TclError`)** — 録音件数 × 検索操作回数に依存。件数の多い Mac ほど発生。
2. **タイトルに `/`** — その録音が 1 件でもあれば中断。
3. **数字のみタイトル (`TypeError`)** — 同上。
4. **iCloud 未ダウンロード録音** — iPhone 同期分が多い Mac で `os.path.exists` が偽 →
   1.0.2 では `failed` にも入らず**黙って 0 件扱い**（tag 1.0.2 は else 節すら無い）。
5. **`ZDATE`/`ZDURATION` NULL** — 一覧ロード段階で全滅。
6. Voice Memos 起動中の WAL / lock。

いずれも「同じアプリなのに Mac ごとにデータ内容が違う」ことに起因する。**環境差ではなくデータ差**。

---

## 8. Security / Privacy

現状の実挙動:

| 項目 | 現状 | 評価 |
|---|---|---|
| ネットワーク送信 | なし（`socket`/`urllib`/`requests` 不使用） | OK |
| telemetry | なし | OK |
| 原本の rename/delete/move | なし（`shutil.copy2` のみ） | OK |
| DB への write | **SQL の write は無いが、`sqlite3.connect()` を read-write モードで開いている** | 要修正 |
| 外部プロセス起動 | `subprocess.run(['open', 'x-apple.systempreferences:...'])` のみ | OK |
| 書き込み先の制御 | **なし。タイトル由来のパストラバーサルで export_dir 外へ書ける** | 要修正 |
| ログ | なし（`print` のみ） | 診断不能 |

FDA を要求するアプリとしての主要リスクは 2 点:
**(a) DB を書き込み可能で開いている**、**(b) 出力先ディレクトリを逸脱し得る**。

---

## 9. License（★要判断・ブロッカー）

- **リポジトリに `LICENSE` ファイルが存在しない。**
  `git log --all --diff-filter=A` で全履歴を確認したが、`LICENSE`/`COPYING` は**一度も commit されていない**。
- GitHub API `repos/rudrakabir/voice-memos-exporter` の `license` フィールドは **`null`**。
- 唯一の言及は `docs/CONTRIBUTING.md` の
  「By contributing, you agree that your contributions will be licensed under **its MIT License**.」
  のみ。README にライセンス記載なし。

**結論: ライセンスは不明確。**
米国/日本の著作権法上、明示的ライセンスの無い公開ソースは既定で「全権利留保」であり、
GitHub の ToS が保証するのは *fork* と *view* のみ（GitHub Terms F.1: public repo の fork 権）。
改変版の**再配布**は ToS では保証されない。

→ 指示 §16 に従い、**「fork 版を公開可能」とは判断しない。**
推奨アクション（いずれかが取れるまで公開しない）:

1. upstream に Issue/PR を立てて `LICENSE`（MIT）の追加を依頼する。
   CONTRIBUTING.md に MIT の記載があるため、応じてもらえる可能性は高い。
2. それまでは fork を **GitHub 上の fork（private / public fork のまま）** に留め、
   独立配布物（Release、バイナリ）を作らない。
3. どうしても公開が必要なら、著作者へ直接許諾を取る。

（GitHub 上で fork ボタンを押して派生を持つこと自体は ToS 上問題ない。
問題になるのは「独立リリース／再配布」。）

---

## 10. Build compatibility（Issue #4）

`voice_memos_exporter.spec`:

```python
exe = EXE(..., target_arch=None, codesign_identity=None, entitlements_file=None, upx=True, ...)
app = BUNDLE(..., info_plist={'LSMinimumSystemVersion': '10.12', ...})
```

- `target_arch=None` → PyInstaller は**ビルドホストのアーキテクチャのみ**で生成する。
  作者が Apple Silicon でビルドしたため arm64-only バイナリになった。→ Issue #4 の直接原因。
  **Python コード自体は Intel でも動作する**（標準ライブラリのみ、arch 依存なし）。
- 対策候補:
  - `target_arch='universal2'` — ただし **universal2 な Python** が必要
    （python.org の macOS universal2 installer。Homebrew python は単一 arch なので不可）。
  - もしくは arm64 / x86_64 を別々にビルドして `lipo -create` で結合。
  - もしくは Release に arm64 版と x86_64 版の 2 つの zip を出す（最も簡単で確実）。
- `LSMinimumSystemVersion: '10.12'` は README の「macOS 10.15 or newer」と**不整合**。
  また `Group Containers/group.com.apple.VoiceMemos.shared` は macOS 12 (Monterey) で
  Voice Memos が Mac に来て以降の構造なので、10.12 という宣言は実態と合わない。
- `upx=True` は macOS では未署名バイナリを壊しやすく、Gatekeeper 問題の原因になり得る。
- `codesign_identity=None` → ad-hoc 署名。Gatekeeper 警告と、
  **FDA の TCC 登録がアプリ更新のたびに外れる**原因になる。

---

## 11. その他の不整合

- `docs/CONTRIBUTING.md` の「Run the application: `python src/main.py`」は**実在しないパス**
  （実際は `python3 voice_memos_exporter.py`）。
- `docs/CHANGELOG.md` は 1.0.1 で止まっており、1.0.2 の記載がない。
- `.spec` の version は `1.0.3` だが、リリース済みの最新は `1.0.2`。
- `requirements.txt` に改行が無い（`pyinstaller==6.3.0` で EOF）。

---

## 12. Issue #1（日付）の技術的整理

- `shutil.copy2` が複製するのは `st_atime` / `st_mtime` / permission / flags。
  macOS の **`st_birthtime`（Finder の「作成日」）は複製されない** → 新規作成時刻 = export 時刻。
- 元 `.m4a` の `st_mtime` 自体も、iCloud からダウンロードされたファイルでは
  ダウンロード時刻になっている場合がある。→ `ZDATE` を正とすべき。
- 安全に近づける手段:
  - `os.utime(dest, (zdate, zdate))` で atime/mtime を録音日時に設定（副作用なし、安全）。
  - birthtime は Python 標準では設定不可。`SetFile -d`（Xcode CLT 依存）や
    `subprocess` での `touch` は環境依存。→ **必須にしない**。
- 優先度: 低（指示どおり、export 安定化の後）。

---

## 13. iCloud 未ダウンロード録音の識別方針（要検証）

現状 `os.path.exists(source_path)` のみ。設計案:

1. `ZPATH` の実ファイルが存在 → 通常 export。
2. 存在しない場合、同ディレクトリに `.<basename>.icloud` プレースホルダがあるか確認
   （iCloud Drive 方式のエビクション）。
3. 併せて `ZEVICTIONDATE` 等、evict 状態を示すカラムが `ZCLOUDRECORDING` にあるか実 DB で確認する。
4. いずれかに該当 → `File not available locally (iCloud)` として **skipped** に分類。
   該当しない → `Source file missing` として **failed**。
5. **アプリから iCloud ダウンロードは行わない**（指示 §8）。

→ 実 DB / 実ディレクトリの確認には Full Disk Access が必要（§14）。

---

## 14. 未解決 / 要確認事項

| # | 内容 | 影響 |
|---|---|---|
| U1 | 当環境に FDA 未付与のため、**実 `ZCLOUDRECORDING` の schema 未確認**（`Z_PK` / `ZUNIQUEID` / `ZEVICTIONDATE` の有無） | stable identifier の第一候補を実測で確定できない。→ 実行時 `PRAGMA table_info` で動的判定する設計で回避可能だが、実測で裏を取りたい |
| U2 | iCloud 未 DL 録音の実際の表れ方（ファイル欠損 / `.icloud` プレースホルダ / DB フラグ） | §13 の分類ロジック |
| U3 | 実データでの `ZPATH` 形式（相対パスか、サブディレクトリを含むか） | `os.path.join` の妥当性 |
| U4 | ライセンス（§9） | fork 版の公開可否 |
| U5 | 数千件環境での実測（当環境では未取得） | §14 大量データ対応の設計判断 |

U1〜U3 は、ターミナルに Full Disk Access を付与すれば **read-only** で確認できる。

---

## 15. Git 状態（Phase 1 終了時点）

- 作業ディレクトリ `voice-memo-exporter-fork/` は **git リポジトリではない**（`.claude/` のみ存在した）。
- 監査のため upstream を `upstream-clone/` に clone した（読み取り専用の参照用）。
- **commit は行っていない。**
- 注意: 当作業ディレクトリは Google Drive 同期配下で、sandbox が `.git/config` への
  書き込みを拒否する。git 操作はサンドボックス無効化が必要。

---

## 次アクション（要ユーザ判断）

1. **ライセンス**（§9 / U4）— fork 版の公開可否。
2. **Full Disk Access**（U1〜U3）— 実 schema 確認のためターミナルへ付与するか。
3. **リポジトリ配置** — fork をこの作業ディレクトリ直下に置くか、サブディレクトリのままか。
4. **実装の担当** — グローバル CLAUDE.md の方針どおり Codex CLI へ委任するか。
