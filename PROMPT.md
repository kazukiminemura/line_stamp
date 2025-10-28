以下のプロンプトを使えば、同等のコード一式を生成できます。

```
あなたはPythonエンジニアです。LINEスタンプを自動生成するCLIツールを作りたい。要件は次のとおり。

- プロジェクト構成:
  - `generate_stamps.py`: CLIエントリポイント。`python generate_stamps.py <config>`形式で実行。オプションで `--font`, `--output`, `--set-icon-text`, `--disable-set-icon` を受け取れる。
  - パッケージ `line_stamp_tool`:
    - `config.py`: JSON/YAML設定を読み込む。`GenerationConfig`, `StickerSpec`, `IllustrationSpec` のdataclassを定義。`stickers` 配列、フォント・出力設定、オプションのイラスト仕様を扱う。`load_config`で設定ファイルを読み込み、相対パスは設定ファイルの場所を基準に解決。
    - `generator.py`: Pillowでスタンプ画像を生成。テキスト自動折り返し・サイズ調整・影/ストローク描画。背景色または背景画像に対応。`illustration`が指定されたら外部画像がなくても blob/cat スタイルの簡易キャラクターを描画し、`expression`や色で表情・配色を変えられる。各スタンプについて main(370x320), store(240x240), tab(96x74) を出力し、必要ならセットアイコン(240x240)も生成。
    - `__init__.py`: 上記クラスをエクスポート。
- 依存: Pillow>=10, PyYAML>=6 を `requirements.txt` に記載。
- `examples/sample_config.json`: ユーザーがカスタマイズできるサンプル設定。各スタンプでテキスト・配色・illustration例を記載。
- README: セットアップ手順、設定パラメータ、illustrationオプションの使い方、サンプルJSONを説明。
- CLI実行時は生成ファイルを `config` の `output_dir`（デフォルト `build/stamps`）配下の `main/`,`store/`,`tab/`,`set_icon/` に保存。
- 文字列は日本語対応を想定。デフォルトフォント候補をOSごとに用意し、見つからなければ指定フォントを要求。
- コードはPython 3.10+対応。タイプヒント付きで読みやすく。
```
