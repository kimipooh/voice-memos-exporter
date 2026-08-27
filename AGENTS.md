# AGENTS.md

Codex その他の実装エージェント向けの作業ルール。
Claude Code 向けの詳細版は `CLAUDE.md` にある。両者のルールは同一。

---

## Project purpose

macOS Voice Memos の DB と録音原本を読み取り、
ユーザー指定の出力先へコピーするツール。

この fork の主成果物は **Python CLI ツール**。

```text
vmx_core.py          共通ロジック（最優先）
export_voice_memos.py  CLI
tests/                 テスト
```

このforkはPython CLI専用であり、GUIとmacOS app buildは保守しない。

---

## Python-first architecture

```text
Voice Memos DB
      ↓
  vmx_core.py
      ↓
export_voice_memos.py
```

- 共通ロジックは `vmx_core.py` に置く。
- 現行インターフェースはCLIだけとする。

---

## Repository / branch policy

```text
origin    git@github.com:kimipooh/voice-memos-exporter.git
upstream  https://github.com/rudrakabir/voice-memos-exporter.git
```

作業 branch:

```text
fix/export-reliability
```

- `main` を直接編集しない。
- 新規修正も `feature/*` / `fix/*` の専用 branch で行う。

---

## Git restrictions

### No push

**push を実行してはいけない。**

```text
git push
git push --force
git push --force-with-lease
git push --tags
git push origin ...
```

push はユーザー本人が手動で行う。
実行用コマンドの提示は可、実行は不可。

### No main merge

```text
git switch main
git merge fix/export-reliability
git rebase main
git push origin main
```

ユーザーが明示的に指示した場合のみ `main` へ merge する。
「十分完成した」という自己判断で merge しない。

### No tag / Release / PR without explicit approval

```text
git tag
git push --tags
GitHub Release 作成
upstream PR 作成
fork 内 PR 作成
Issue 投稿
```

本文案の作成は可。投稿・作成はユーザーの指示を待つ。

### commit

その作業で commit まで許可されている場合のみ commit する。
通常は実装・テスト後に状態を報告し、ユーザーの判断を待つ。

### destructive commands（明示許可が必要）

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

未 commit の変更は必ず保全する。

---

## Safety rules（Voice Memos 原本保護）

禁止:

```text
DB への INSERT / UPDATE / DELETE / schema 変更
録音原本の rename / delete / move / modify
```

許可されるのは以下のみ。

```text
read database
read source recording
copy to user-selected output
```

SQLite は read-only 接続を維持する。

Full Disk Access が必要な場合がある。CLI では Python を実行する
terminal application 側に権限が必要。
権限関連の変更時は DB missing / permission error / schema error を区別する。

---

## 既知修正を壊さない

- slash title: `Interview / Hanoi` でも export 可能
- numeric-only title: `123` / `2026` / `001` でも失敗しない
- partial failure: 1 件の失敗で全 export を停止しない
- safe filename: 安全でない path component を適切に処理する
- read-only SQLite: DB を変更しない

---

## Testing command

```bash
/usr/bin/python3 -m unittest discover -s tests -t .
```

基準:

```text
CLI/core tests
OK
```

CLI は最低限以下を確認する。

```bash
python3 export_voice_memos.py --help
```

---

## upstream license

upstream に正式な `LICENSE` ファイルは存在しない。

```text
LICENSE を新規作成しない
MIT licensed と断定しない
独自ライセンスを設定しない
```

upstreamのライセンス状態が明確になるか、ユーザーが明示的に決定するまでこの方針を維持する。
`NOTICE` にある fork 追加・変更部分の著作権表示は、この方針を変更するものではない。

---

## README / docs

- 既存構造を維持し、全面書き換えを避ける。
- 変更した実装だけを文書へ反映する。
- 未実装機能を「対応済み」と書かない。
- GUIやapp buildを現行機能として説明しない。
- `README.md` / `README-ja.md` / `docs/CHANGELOG.md` の整合性を確認する。
- `AGENTS.md` / `CLAUDE.md` / `.codex/tasks/` 配下は UTF-8 BOM なしで保存する。

---

## .claude / .codex are local-only

`.claude/` と `.codex/` はローカル開発支援用。Git 管理対象にしない。

```text
tracked:   CLAUDE.md, AGENTS.md
ignored:   .claude/, .codex/
```

tracked な `.claude/` / `.codex/` ファイルを見つけた場合は、
削除せずユーザーへ報告する。

---

## 作業完了時の報告

```bash
git status
git diff --stat
git diff
git diff --check
```

`commit 可能` / `push 可能` / `main merge 可能` を別々に評価して報告する。
評価が「可能」でも、push と main merge は自動実行しない。

標準フロー:

```text
実装・テスト → レビュー → 必要なら commit → ユーザー確認 → ユーザーが手動 push
```
