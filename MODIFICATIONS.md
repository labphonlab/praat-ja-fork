# 改変内容の記録 (GPL v3 §5(a))

本ドキュメントは GNU General Public License v3 §5(a) の要件に基づき、
upstream の Praat に対して本フォークが加えた変更を明示するものです。

## upstream

- リポジトリ: <https://github.com/praat/praat>
- 著作者: Paul Boersma, David Weenink (University of Amsterdam)
- ライセンス: GNU General Public License v3 or later

## 本フォークによる改変

本フォークは upstream の Praat ソースを **直接修正しません**。代わりに、
ビルド前に翻訳辞書を機械的に当てる方式 (`scripts/apply_translations.py`) を
採用しています。

### 翻訳パッチで書き換える対象

- C++ ソース中の `U"..."` 文字列リテラルのうち、`translations/*.yaml` に
  原文と翻訳が対になって登録されているもの

### 翻訳対象ファイル (現時点)

| upstream のパス | 内容 |
|---|---|
| `sys/praat_objectMenus.cpp` | Objects ウィンドウのメインメニュー (~187箇所) |

### 翻訳されない部分

- マニュアル本文 (`*/manual_*.cpp`)
- スクリプト言語のキーワード
- API 識別子・コマンド名
- 内部メッセージ・デバッグログ

### 識別 (本フォークと公式の区別)

- バイナリ名: `Praat-ja` (公式は `Praat`)
- 配布サイト: <https://github.com/labphonlab/praat-ja-fork> (公式: <https://praat.org>)
- 本フォークのウィンドウタイトル / About ダイアログには「非公式」表記を入れる
  (将来追加予定)

## 翻訳辞書のライセンス

`translations/*.yaml` の内容は派生物として **GPL v3** で配布されます。

## 改変履歴

### 2026-05-25
- 初版 PoC: `sys/praat_objectMenus.cpp` の Objects ウィンドウメニューを翻訳
  (~125 ユニーク文字列、~187 出現箇所)
