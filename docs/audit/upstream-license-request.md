# upstream への LICENSE 追加依頼（ドラフト）

実際の投稿用本文は [`upstream-license-issue-draft.md`](upstream-license-issue-draft.md) に分離した。
本ファイルは法的根拠とPR化候補の調査記録として残す。

## 背景

- `rudrakabir/voice-memos-exporter` には `LICENSE` ファイルが存在しない。
  `git log --all --diff-filter=A` で全履歴を確認したが、一度も commit されていない。
- GitHub API `repos/rudrakabir/voice-memos-exporter` の `license` フィールドは `null`。
- 唯一の言及は `docs/CONTRIBUTING.md` の
  「By contributing, you agree that your contributions will be licensed under its MIT License.」
- README にライセンス記載なし。

明示ライセンスが無い公開ソースは既定で全権利留保。GitHub Terms of Service (F.1) が
保証するのは public repository の *fork* と *view* のみで、**改変版の独立配布は保証されない**。

したがって fork 版の Release / バイナリ配布は、LICENSE が明確になるまで行わない。

---

## 送信先

https://github.com/rudrakabir/voice-memos-exporter/issues/new

**※ 未送信。ユーザの承認後に送ること。**

---

## Issue タイトル案

```
Add a LICENSE file (CONTRIBUTING.md references MIT, but no license is declared)
```

## Issue 本文案

```markdown
Hi, and thanks for building this — it solved a real gap in Voice Memos.

I noticed the repository does not contain a `LICENSE` file, and GitHub's
repository metadata reports `"license": null`. The only reference to a
license is in `docs/CONTRIBUTING.md`:

> By contributing, you agree that your contributions will be licensed under its MIT License.

Without a `LICENSE` file in the repository, the code is by default "all rights
reserved", so it isn't clear whether forks may be modified and redistributed —
even though CONTRIBUTING.md implies MIT was intended.

Would you consider adding an explicit `LICENSE` file (MIT, matching
CONTRIBUTING.md)? GitHub can add one for you via
**Add file → Create new file → name it `LICENSE` → Choose a license template**.

That would let people fork, fix and share improvements with confidence.

Context: I'm maintaining a private fork that fixes a few reproducible export
failures (stale Treeview item IDs behind the `"Item ... not found"` error in
#7, unsanitised filenames behind #2, and read-only database access). I'd be
glad to open PRs upstream, but I'm holding off on publishing anything until
the licensing is clear.

Thanks!
```

---

## 補足: PR として upstream に還元できる修正

ライセンスが MIT で明確になった場合、以下は upstream への PR 候補として切り出せる
（fork 独自機能ではなく、素直なバグ修正であるため）。

| 修正 | 対応 Issue | PR 化の容易さ |
|---|---|---|
| 選択状態を安定キーで保持（stale item ID 修正） | #7 | 中（`selected_items` の全廃を伴う） |
| ファイル名サニタイズ | #2 | 高（独立した小さな関数） |
| タイトルの `str()` 強制（int 化対策） | #7 の別要因 | 高（1行） |
| DB を `mode=ro` で open | — | 高 |
| per-recording のエラー分類と Total/Exported/Skipped/Failed 表示 | — | 中 |
| `sqlite3.Error` を FDA 不足に丸めない | — | 中 |
| `.spec` の `target_arch='universal2'` | #4 | 高（ただしビルド環境の説明が要る） |
| `os.utime` で録音日時を復元 | #1（部分） | 高 |

fork 独自に留めるべきもの（upstream の設計方針を大きく変えるため）:

- ワーカースレッド化 + Cancel ボタン
- 診断ログ出力
- `vmx_core.py` へのロジック分離と `tests/` の追加
  （ただし upstream が受け入れるなら PR 価値は高い）
