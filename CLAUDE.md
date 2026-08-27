# CLAUDE.md

このファイルは、本リポジトリで Claude Code が作業する際のルールを定義する。
ユーザーのグローバル `~/.claude/CLAUDE.md` よりも、本ファイルの記述を優先する。

Codex など Claude 以外の実装エージェント向けの要約は `AGENTS.md` にある。
両ファイルのルールは同一であり、片方だけを変更しない。

---

## Project purpose

macOS Voice Memos の録音を、DB とオリジナル音声ファイルから読み取り、
ユーザーが指定した出力先へコピーするツール。

この fork の主成果物は **Python CLI ツール**である。

優先順位:

```text
vmx_core.py
    ↓
export_voice_memos.py
    ↓
tests
```

Tkinter GUI (`voice_memos_exporter.py`) は既存機能として維持する。

`.app` / PyInstaller ビルドは optional。
**`.app` の build 成功を開発完了条件にしない。**

---

## Python-first architecture

```text
Voice Memos DB
      ↓
  vmx_core.py
   ↓       ↓
 CLI       GUI
```

- 共通ロジックは可能な限り `vmx_core.py` に置く。
- CLI と GUI で export 処理を二重実装しない。
- 機能追加・バグ修正も、まず `vmx_core.py` への配置を検討する。

---

## Repository / branch policy

```text
origin    git@github.com:kimipooh/voice-memos-exporter.git
upstream  https://github.com/rudrakabir/voice-memos-exporter.git
```

現在の作業 branch:

```text
fix/export-reliability
```

- `main` を直接編集しない。
- 新しい修正も原則として専用 branch (`feature/*` / `fix/*`) を使う。
- `fix/export-reliability` は現時点では `main` へ merge せず維持する。

---

## Git restrictions（最重要）

### push は実行しない

**Claude は push を実行してはいけない。**

禁止:

```text
git push
git push --force
git push --force-with-lease
git push --tags
git push origin ...
```

push は必ずユーザー本人がターミナルから手動で行う。

Claude は次のような「ユーザーが実行するためのコマンド」を提示してよいが、
自分では実行しない。

```bash
git push origin fix/export-reliability
```

### main へ merge しない

禁止:

```text
git switch main
git merge fix/export-reliability
git rebase main
git push origin main
```

`main` への merge は、ユーザーが明示的に「main へ merge する」と
指示した場合のみ行う。
Claude が「十分完成した」と判断しても、自動的に merge しない。

### commit

ユーザーからその作業で commit まで許可されている場合に限り commit してよい。

通常は、実装・テスト・監査の後に一度状態を報告し、
ユーザーが commit 可否を判断できる状態で止める。

### destructive Git commands

ユーザーの明示許可なしに実行しない。

```text
git reset --hard
git clean -fd
git clean -fdx
git restore .
git checkout -- .
git branch -D
git push --force
git rebase --onto
```

未 commit の変更がある場合は必ず保全する。

### tag / Release / PR / Issue

ユーザーの明示指示なしに実行しない。

```text
git tag
git push --tags
GitHub Release 作成
upstream PR 作成
fork 内 PR 作成
Issue 投稿
```

本文案の作成は可。実際の投稿・作成はユーザーの指示を待つ。

---

## Voice Memos 原本保護

このツールは macOS Voice Memos の DB と録音原本を読み取る。

禁止:

```text
DB への INSERT
DB への UPDATE
DB への DELETE
DB の schema 変更
録音原本の rename
録音原本の delete
録音原本の move
録音原本の modify
```

基本原則は以下のみ。

```text
read database
read source recording
copy to user-selected output
```

SQLite は read-only 接続を維持する。

---

## Full Disk Access

Voice Memos DB へのアクセスには macOS の Full Disk Access が必要になる場合がある。

CLI の場合、Full Disk Access が必要なのは Python を実際に実行するアプリ
(Terminal / iTerm / その他 terminal application) である。

権限関連の処理を変更する場合は、以下を区別して扱う。

- DB missing
- permission error
- schema error

---

## 既知修正を壊さない

以下は回帰させない。

| 項目 | 内容 |
| --- | --- |
| stale Treeview ID | 検索後でも `Item xxxx not found` を発生させない |
| slash title | `Interview / Hanoi` のようなタイトルでも export できる |
| numeric-only title | `123` / `2026` / `001` などでも失敗しない |
| partial failure | 1 件の失敗で全 export を停止しない |
| safe filename | 安全でない path component を適切に処理する |
| read-only SQLite | DB を変更しない |

---

## Testing command

変更後は原則として以下を実行する。

```bash
/usr/bin/python3 -m unittest discover -s tests -t .
```

現在の基準:

```text
49 tests
OK
```

Tkinter が無い環境では GUI テスト 1 件の skip を許容する。
ただし skip 理由を必ず報告する。

CLI についても最低限、以下を確認する。

```bash
python3 export_voice_memos.py --help
```

---

## upstream license

upstream repository には正式な `LICENSE` ファイルが存在しない。
`docs/CONTRIBUTING.md` に MIT への言及があるが、正式ライセンスとは断定しない。

したがって:

```text
LICENSE を新規作成しない
MIT licensed と断定しない
独自ライセンスを設定しない
```

ライセンスに関する記述は慎重に維持する。

---

## README / docs 編集ルール

- 既存構造を維持する。全面書き換えを避ける。
- 変更した実装だけを文書へ反映する。
- 未実装機能を「対応済み」と書かない。
- Apple Silicon / Intel / `.app` build について、未検証事項は未検証と明示する。

以下を変更した場合は整合性を確認する。

```text
README.md
README-ja.md
docs/CHANGELOG.md
docs/
CLAUDE.md
AGENTS.md
```

### Markdown encoding

- 人間が直接読む Markdown (README、CHANGELOG、docs 配下) は既存の文字コードを維持する。
- エージェント / CLI が読む Markdown (`CLAUDE.md`、`AGENTS.md`、`.codex/tasks/` 配下) は
  UTF-8 BOM なしとする。

---

## .claude / .codex

`.claude/` と `.codex/` はローカル開発支援用であり、Git 管理対象にしない。
`.gitignore` に両方が登録されていることを確認する。

```text
tracked:   CLAUDE.md, AGENTS.md
ignored:   .claude/, .codex/
```

tracked な `.claude/` / `.codex/` ファイルが存在した場合は、
勝手に削除せずユーザーへ報告する。

---

## 役割分担

```text
Claude:
- audit
- design
- review
- final verification

Codex:
- implementation
- tests
- narrow code changes
```

- Claude は大量コードの通読・リポジトリ全体レビューを行わない。
- 実装が必要な場合は `.codex/tasks/task-YYYYMMDD-HHMM.md` へ引き継ぎ指示を出力し、
  チャットには要約のみ表示する。
- 小規模作業を Claude が直接変更する場合でも、
  本ファイルの Git 制約と安全ルールは同一に適用される。

### 標準フロー

```text
実装・テスト
↓
レビュー
↓
必要なら commit
↓
ユーザーが確認
↓
ユーザーが手動 push
```

---

## 完了時の報告

作業完了時は以下を報告する。

```bash
git status
git diff --stat
git diff
git diff --check
```

その上で、次の 3 つを**別々に**評価する。

```text
commit 可能か
push 可能か
main merge 可能か
```

評価が「可能」であっても、push や main merge を自動実行しない。
