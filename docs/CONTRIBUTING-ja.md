# Voice Memos Exporterへのコントリビューション

[English: CONTRIBUTING.md](CONTRIBUTING.md)

Voice Memos Exporterへの協力を歓迎します。次のようなコントリビューションを、分かりやすく透明な手順で受け付けます。

- バグの報告
- コードの現状に関する議論
- 修正の提出
- 新機能の提案
- メンテナーとしての参加

## 開発プロセス

コードのhosting、Issueと機能要望の管理、pull requestの受付にはGitHubを使います。

1. リポジトリをforkし、`main` から作業branchを作成します。
2. テストすべきコードを追加した場合は、テストも追加します。
3. APIを変更した場合は、ドキュメントを更新します。
4. テストsuiteが通ることを確認します。
5. コードがlintを通ることを確認します。
6. pull requestを作成します。

## 開発環境

- リポジトリをcloneします。
- 通常の開発では、`python3 -m venv venv` と `source venv/bin/activate` でvirtual environmentを作成して有効化します。
- 開発にはmacOSが必要です。
- CLIはPython 3.9以降に対応します。
- GUI・packaging検証にはPython 3.14.7とTcl/Tk 9.0を使います。
- packagingではvirtual environment `.venv-package` を使います。`/opt/homebrew/bin/python3.14 -m venv .venv-package` で作成し、[gui-packaging-ja.md](gui-packaging-ja.md) の手順でPyInstallerをインストールします。

## テストの実行

リポジトリのテストsuiteは次のコマンドで実行します。

```bash
/usr/bin/python3 -m unittest discover -s tests -t .
```

変更を通すためにテストを弱めたりskipしたりしないでください。

## CLIの確認

```bash
python3 export_voice_memos.py --help
python3 export_voice_memos.py --version
```

## GUIテスト

一部のGUIテストにはTkが必要です。macOS WindowServerへ接続できない環境では実行できません。interfaceを手動確認するときは、`python3 voice_memos_exporter.py` でGUIをソースから起動します。

## Packagingテスト

`dist/Voice Memos Exporter.app` をbuildしていない場合、packaging smoke testはskipされます。build後は同じテストsuiteコマンドで実行され、bundleのselftest、構成、metadata、同梱Tcl/Tk、外部依存を検証します。

## ビルド

次のコマンドでアプリをbuildします。

```bash
bash packaging/build_app.sh
```

packaging環境、検証、release ZIP作成コマンドは [gui-packaging-ja.md](gui-packaging-ja.md) を参照してください。

## 手動テスト

次の項目は実際のVoice Memos DBが必要で、完全には自動化できません。一覧表示、export、dry run、Recently Deleted、cancel、`/` を含むtitle、数字だけのtitle、iCloud-onlyの録音、元のデータベースが変更されないこと、Gatekeeperの承認、フルディスクアクセスを確認します。

詳細は[GUI手動テストチェックリスト](gui-notes.md#manual-test-checklist)を参照してください。

## コントリビューションの方針

- DB・exportロジックの正本は `vmx_core.py` です。
- GUI側に別のexport engineを作らないでください。
- Voice Memosの元のデータベースや録音を変更しないでください。
- CLIをregressionさせず、テストを弱めないでください。
- upstream attributionとMIT Licenseを維持してください。
- `README.md` と `README-ja.md`、docsの日英ペアを同期してください。

## ライセンス

このプロジェクトにはMIT Licenseが適用されます。詳細は [LICENSE](../LICENSE) を参照してください。
upstreamプロジェクト `rudrakabir/voice-memos-exporter` も同じMIT Licenseを公開しています。コントリビューションにもMIT Licenseが適用されることに同意するものとします。
