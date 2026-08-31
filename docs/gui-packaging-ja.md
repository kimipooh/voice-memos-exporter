# GUIアプリのpackaging

[English: gui-packaging.md](gui-packaging.md)

この手順の目的は、PyInstallerを使ってmacOS版Voice Memos Exporterのアプリバンドルをbuildすることです。

アプリはApple Silicon（arm64）向けに、Homebrew Python 3.14.7、Tcl/Tk 9.0、PyInstaller 6.22.2でbuildします。PyInstallerはgit-ignoredのpackaging用virtual environment `.venv-package` にインストールします。

## `.app` の構成

アプリバンドルにはPythonとTkが含まれるため、利用者側にPython、Homebrew、Tkは必要ありません。Apple Silicon（arm64）専用であり、Intelとuniversal2には対応していません。メインの実行ファイルは `Contents/MacOS`、metadataは `Contents/Info.plist`、同梱ライブラリは `Contents/Frameworks` にあります。

packaging環境を次のコマンドで作成します。

```bash
/opt/homebrew/bin/python3.14 -m venv .venv-package && .venv-package/bin/python -m pip install pyinstaller
```

アプリをbuildします。

```bash
bash packaging/build_app.sh
```

出力は `dist/Voice Memos Exporter.app` で、bundle identifierは `jp.kitani.voicememosexporter` です。

build後に、全テストの一部としてpackaging smoke testを実行します。

```bash
/usr/bin/python3 -m unittest discover -s tests -t .
```

smoke testは `VMX_APP_SELFTEST=1` でbundleのselftestを実行し、bundle構成、identifier、version、Tcl/Tkライブラリを検証します。また `otool -L` を使い、実行ファイルがHomebrew、外部Python framework、`/usr/bin/python3` に依存していないことを確認します。アプリをbuildしていない場合、bundleのsmoke testはskipされます。

フルディスクアクセスはTerminalなどではなく、`Voice Memos Exporter.app` 自体に許可します。bundle identifierはmacOSがアプリを識別する情報の一部です。再buildでコード署名またはinodeの識別情報が変わると、「システム設定」でフルディスクアクセスの再承認が必要になる場合があります。

bundleはad-hoc署名のみで、Apple Developer ID証明書による署名もnotarizeもされていません。そのためGatekeeperが初回起動をブロックします。詳細は[初回起動がブロックされる](troubleshooting-ja.md#初回起動がブロックされる)を参照してください。

## Release asset

配布用ZIPは次のコマンドで作成します。

```bash
cd dist
ditto -c -k --sequesterRsrc --keepParent \
  "Voice Memos Exporter.app" \
  "Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip"
```

bundleのsymlinkとresource forkを保持するため、`zip` ではなく `ditto` を使います。release ZIPは `dist/Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip` です。
