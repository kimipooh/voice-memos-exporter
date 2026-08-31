# トラブルシューティング

[English: troubleshooting.md](troubleshooting.md)

Voice Memos Exporterの症状と対処方法です。CLIリファレンスは
[usage-ja.md](usage-ja.md)、アプリのビルド方法は [gui-packaging-ja.md](gui-packaging-ja.md) を参照してください。

## 初回起動がブロックされる

**症状:** アプリをダブルクリックすると「ゴミ箱に入れる」/「完了」だけを選べる警告が表示され、アプリが起動しません。

このアプリはApple Developer ID証明書で署名されておらず、notarizeもされていないため、Gatekeeperが初回起動をブロックします。ad-hoc署名のみですが、故障ではありません。

macOS 15 Sequoia以降では、Controlキーを押しながらクリック→「開く」でGatekeeperを上書きできなくなりました。Appleは [Updates to runtime protection in macOS Sequoia](https://developer.apple.com/news/?id=saqachfa) で次のように案内しています。

> In macOS Sequoia, users will no longer be able to Control-click to override
> Gatekeeper when opening software that isn't signed correctly or notarized.
> They'll need to visit System Settings > Privacy & Security to review security
> information for software before allowing it to run.

Appleの記載どおり、次の順で操作します。

1. Macでアップルメニュー ＞「システム設定」と選択し、サイドバーで「プライバシーとセキュリティ」
   をクリックします。（下にスクロールする必要がある場合があります。）
2. 「セキュリティ」に移動して、「開く」をクリックします。
3. 「このまま開く」をクリックします。
   - *このボタンは、アプリを開こうとした後、約1時間の間使用できます。*
4. ログインパスワードを入力して、「OK」をクリックします。

承認後はセキュリティ設定の例外として保存され、以後は通常どおりダブルクリックで開けます。Appleの[「開発元が不明なMacアプリを開く」](https://support.apple.com/ja-jp/guide/mac-help/mh40616/mac)も参照してください。

## フルディスクアクセスが必要

**症状:** アプリは起動しますが、ボイスメモのデータベースや録音を読み取れません。

Gatekeeperはアプリの**起動を許可するか**を決めます。フルディスクアクセスはボイスメモのデータベースと録音の**読み取りを許可するか**を決めます。どちらも「システム設定」→「プライバシーとセキュリティ」にあるため混同しやすいものの、別々の権限であり、両方が必要です。

1. アップルメニュー→「システム設定」→「プライバシーとセキュリティ」→「フルディスクアクセス」と進みます。
2. `Voice Memos Exporter.app` を追加してオンにします。
3. アプリを完全に終了し、再度開きます。

CLIまたはソースからGUIを実行する場合は、`.app` ではなく、Pythonを起動する**ターミナルアプリ**（Terminal、iTerm、IDEの統合ターミナル）にフルディスクアクセスを許可し、そのターミナルを再起動します。アクセス権がない場合、CLIは案内を表示して終了コード1で終了します。

アプリを再buildするとコード署名の識別情報が変わり、macOSからフルディスクアクセスの再承認を求められる場合があります。

## ボイスメモデータベースが見つからない

このメッセージは、必ずしもアプリの故障を意味しません。ボイスメモをこのMacで一度も使っていない場合など、データベースがまだ作成されていないときによく表示されます。

- Appleのボイスメモアプリを一度開きます。
- このMacに録音が1件以上あることを確認します。
- 録音がiPhoneにある場合、iCloud経由でこのMacへ同期されていることを確認します。
- ボイスメモを終了し、Voice Memos Exporterを再度起動します。
- データベースを既定以外の場所に置いている場合、CLIでは `--db PATH` を指定できます。

## ボイスメモデータベースがロックされているか開けない

Appleのボイスメモアプリを終了して再試行します。これはフルディスクアクセス不足とは別のエラーです。ロックはファイルに到達できたものの使用中だったことを示し、権限不足ではpermission errorが報告されます。このツールはmissing、permission-denied、incompatible-schema、locked、corruptの状態を区別します。

データベースはread-onlyで開き、WAL処理のために一時的な読み取りsnapshotを使う場合があります。元のデータベースへ書き込むことはありません。

## 録音がiCloudにしかない

録音が一覧にあっても、音声がこのMacにない場合があります。その場合、`Local` 列は `iCloud` と表示されます。このような録音は失敗ではなくスキップとして報告され、このツールがダウンロードすることはありません。

ボイスメモを開き、録音を再生またはダウンロードしてmacOSにローカル取得させた後、再度書き出します。

## 一部の録音がスキップまたは失敗した

`Local` 列（`Yes` / `iCloud` / `Missing`）、`Status` 列、書き出し先フォルダへの書き込み権限を確認します。

1件以上の録音がスキップまたは失敗すると、JSON Lines形式の診断ログが出力先ディレクトリに書き込まれ、そのパスが表示されます。ログには録音識別子、タイトル、ソースと出力先のパス、結果、例外の型とメッセージが記録されます。音声は含まれず、外部へ送信されません。1件の失敗で残りの書き出しが止まることはありません。

## 最近削除した項目の録音

「最近削除した項目」の録音は既定で除外されます。GUIでは **Include Recently Deleted** を有効にし、CLIでは `--include-trash` を指定します。該当する行の `Status` 列には `Recently Deleted` と表示されます。

録音が残っているかは、Appleの「最近削除した項目」の保持期間に依存します。ボイスメモによる削除後は、このツールでは復元できません。

## Appleのドキュメント

- [「開発元が不明なMacアプリを開く」](https://support.apple.com/ja-jp/guide/mac-help/mh40616/mac)
- [Updates to runtime protection in macOS Sequoia](https://developer.apple.com/news/?id=saqachfa)
