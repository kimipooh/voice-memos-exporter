# Phase 2 — 実機 Voice Memos DB による実測結果

Full Disk Access 付与後、`tools/probe_schema.py` を **read-only（`mode=ro`）** で実行した結果。
Phase 1 監査（`phase1-audit.md`）の未解決事項 U1〜U3 に対する回答。

測定環境: macOS / Python 3.9.6 / SQLite 3.51.0 / 録音 9 件

---

## U1: stable identifier — 解決

`ZCLOUDRECORDING` の実列（抜粋）:

```
Z_PK                    INTEGER   pk=1   非NULL 9/9  distinct 9  → UNIQUE
ZUNIQUEID               VARCHAR          非NULL 9/9  distinct 9  → UNIQUE
ZPATH                   VARCHAR          非NULL 9/9  distinct 9  → UNIQUE
ZENCRYPTEDTITLE         VARCHAR          非NULL 9/9
ZCUSTOMLABEL            VARCHAR          非NULL 9/9
ZCUSTOMLABELFORSORTING  VARCHAR
ZDATE                   TIMESTAMP        NULL 0 件
ZDURATION               FLOAT            NULL 0 件
ZEVICTIONDATE           TIMESTAMP        非NULL 4/9
ZFOLDER, ZFLAGS, ZLOCALDURATION, ZPLAYBACKPOSITION, ... （その他多数）
```

**結論: `Z_PK` を第一の安定識別子として使える。** `ZUNIQUEID` も UNIQUE で、
`Z_PK` が無い schema でのフォールバックとして妥当。

採用した識別子:

```
key = "pk:{Z_PK}"  →  なければ "uid:{ZUNIQUEID}"  →  なければ "path:{ZPATH}"
```

---

## ★ 表示タイトル列の確定（実装の退行を発見）

`ZENCRYPTEDTITLE` と `ZCUSTOMLABEL` は **9 件すべてで値が異なる**。
どちらが「ユーザに見えるタイトル」かを、値そのものを出力せず文字種と長さで判定した:

| 列 | 長さ | 文字種 | 判定 |
|---|---|---|---|
| `ZENCRYPTEDTITLE` | 3, 4, 5, 7, 8, 8, 14, 21, 23 と**可変** | latin / num / space / **CJK / カタカナ** | **ユーザが付けた録音名** |
| `ZCUSTOMLABEL` | 全 9 件が **20 文字固定** | latin / num / punc のみ、CJK なし | 内部ラベル |
| `ZPATH` の stem | 全 9 件が 24 文字固定 | latin / num / punc / space | 生成ファイル名 |

日本語の録音名が `ZENCRYPTEDTITLE` にだけ現れることから、**`ZENCRYPTEDTITLE` が表示名**で確定。
（列名に反して暗号化はされていない。upstream がこの列を使っていたのは正しかった。）

→ Codex 初版が `ZCUSTOMLABEL` を優先していたのは **upstream に対する退行**。
`.codex/tasks/task-20260827-1710.md` の F1 として差し戻し済み。

---

## U3: `ZPATH` の実形式 — 解決

```
サンプル 9 件 / 絶対パス 0 件 / '/' を含むもの 0 件
拡張子: {'.qta': 9}
NULL・空の ZPATH: 0 件
```

- `ZPATH` は **Recordings ディレクトリ直下の相対ファイル名**。サブディレクトリを含まない。
  → `os.path.join(recordings_dir, rel_path)` で正しい。
- **拡張子は `.m4a` ではなく `.qta`。** マジックバイトは `\x00\x00\x00\x14ftypqt  ` で
  **QuickTime コンテナ**。ISO BMFF 系だが `ftypM4A ` ではない。
- `.qta` は **通常ファイルであってディレクトリ（バンドル）ではない**ことを 9 件すべてで確認。
  → `shutil.copyfileobj` で正しくコピーできる。`IsADirectoryError` の懸念はなかった。
- Recordings ディレクトリ内の拡張子分布: `{'.qta': 9, '': 3, '.waveform': 4, '.db': 1, '.db-shm': 1, '.db-wal': 1}`

**注意: 拡張子を `.m4a` に書き換えてはいけない。** 中身は QuickTime であり、改名は誤表示を招く。
エクスポート後のファイルが一部のプレイヤーで開けない可能性は README に注記する（Phase 5）。

---

## U2: iCloud 未ダウンロード録音 — 部分的に解決

```
present on disk        : 9
.icloud placeholder    : 0
absent, no placeholder : 0

ZEVICTIONDATE 非NULL   : 4 / 9
```

- この Mac には未ダウンロード録音が **存在しなかった**ため、
  `.icloud` プレースホルダ方式の実地検証はできていない。**未確認のまま残る。**
- **`ZEVICTIONDATE` が非NULL でも実ファイルはローカルに存在した（4/9）。**
  → `ZEVICTIONDATE` を「ローカル未取得」の判定に使ってはいけない。
  実装が `os.path.exists` + `.icloud` プレースホルダで判定しているのは妥当。
- 実装は「ファイルが無い」かつ「`.icloud` プレースホルダも無い」場合を
  `MISSING`（failed）、プレースホルダがある場合を `NOT_DOWNLOADED`（skipped）に分類する。
  プレースホルダが使われない実装形態だった場合、未ダウンロード録音は `MISSING`（failed）に
  落ちるが、**export 全体は止まらない**ので実害は「分類が粗い」ことに留まる。

---

## WAL と read-only アクセスの実測

実機 DB は `journal_mode = wal`、`-wal` / `-shm` が常駐していた。
合成 DB で `mode=ro` の挙動を検証した結果:

| ケース | 結果 | 評価 |
|---|---|---|
| A. `-shm` あり・ディレクトリ書込可 | `DbStatus.OK` | 通常状態。問題なし |
| B. `-shm` **なし**・ディレクトリ書込可 | `DbStatus.OK`。ただし **SQLite が `-shm` を新規作成する** | ★制約違反。Voice Memos コンテナ内に書き込みが発生 |
| C. hot WAL・ディレクトリ**書込不可** | `unable to open database file` → **`PERMISSION_DENIED` に誤分類** | ★本タスクが排除したかった誤分類そのもの |

`mode=ro` は「DB 本体を書き換えない」ことは保証するが、
**WAL データベースでは `-shm` の作成/更新までは防げない。**

→ `.codex/tasks/task-20260827-1710.md` の F3 として、
`-shm` が無い場合や `mode=ro` が失敗した場合に
**DB / `-wal` / `-shm` を一時ディレクトリへコピーしてコピー側を開く**フォールバックを指示済み。
`immutable=1` は hot WAL があると不整合なデータを返すため採用しない。

---

## 「同僚の Mac だけ失敗する」仮説の裏付け

この Mac のデータ特性:

```
録音件数                          : 9
タイトルに '/' を含むもの          : 0
数字のみのタイトル                 : 0
NULL タイトル                     : 0
最長タイトル長                     : 23
同一秒・同一タイトルの重複グループ  : 0
秒のみ重複するグループ             : 0
ZDATE / ZDURATION が NULL         : 0
ローカルに無い録音                 : 0
```

**Phase 1 で特定した失敗要因が 1 つも成立しない。**
すなわちこの Mac では upstream 1.0.2 でも成功する。

- 録音 9 件では Treeview の item ID 連番が `I16CD`（= 5837 個目）に到達し得ない。
- `/` を含むタイトルも、数字のみのタイトルも無い。

→ Phase 1 の結論「環境差ではなくデータ差」が実測で裏付けられた。
失敗した Mac には、録音件数が多いか、`/` を含むタイトルか、数字のみのタイトルか、
iCloud 未ダウンロード録音のいずれかが存在したと考えられる。

---

## プライバシー上の注意

`tools/probe_schema.py` および本文書は、
録音タイトル・音声内容・絶対パスを一切出力していない。
文字数・文字種・件数の集計のみを記録している。
DB は `mode=ro` でのみ open し、SELECT / PRAGMA 以外を発行していない。
