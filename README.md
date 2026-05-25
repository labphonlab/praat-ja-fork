# 非公式 Praat 日本語化版 (フォーク)

> ⚠️ **本リポジトリは Praat の非公式日本語化フォークです / UNOFFICIAL FORK**
>
> Paul Boersma・David Weenink（アムステルダム大学）および公式 Praat プロジェクトとは
> **無関係** であり、公式の承認・推奨を受けたものではありません。
>
> This is an **UNOFFICIAL** Japanese localization fork of Praat. Not affiliated
> with, endorsed by, or sponsored by the official Praat project.

---

## 設計方針

Praat 本体は GitHub から submodule として **無改変** で取得し、ビルド前に
翻訳辞書 (YAML) を sed 的に当てる**「翻訳パッチ方式」**を採用しています。
これにより:

- 本リポジトリの差分は「辞書 + 適用スクリプト」のみ → 軽量
- upstream の月次更新に追従しやすい
- 翻訳の追加・修正は YAML 編集だけ
- 非エンジニアでも翻訳に参加可能

```
praat-ja-fork/
├── upstream/                     ← praat/praat を submodule で取得 (vanilla)
├── translations/
│   ├── menus.yaml                ← 翻訳辞書 (現在: ~125件)
│   ├── dialogs.yaml              ← 今後追加
│   ├── editor_menus.yaml         ← 今後追加
│   └── errors.yaml               ← 今後追加
├── scripts/
│   ├── apply_translations.py     ← ビルド前に upstream に翻訳を当てる
│   └── extract_strings.py        ← 新版から未翻訳文字列を抽出
├── patches/                      ← 翻訳では済まない構造的変更 (将来用)
├── docs/                         ← (将来) 配布サイト
├── LICENSE                       ← GPL v3
├── COPYING.GPL                   ← GPL v3 全文
├── MODIFICATIONS.md              ← GPL §5(a) 改変内容の記録
└── .github/workflows/build.yml   ← 3プラットフォーム CI
```

## 翻訳カバレッジ (現状)

| 領域 | 対象ファイル | 翻訳済み | カバレッジ |
|---|---|---|---|
| Objects ウィンドウのメインメニュー | `sys/praat_objectMenus.cpp` | 125 / ~187 | PoC 完了 |
| Sound 系メニュー | `fon/praat_Sound.cpp` | 0 | 未着手 |
| dwtools | `dwtools/praat_David_init.cpp` | 0 | 未着手 |
| Editor メニュー | `sys/Editor.cpp`, `foned/*` | 0 | 未着手 |
| エラーメッセージ | `melder/*` | 0 | 未着手 |

ロードマップは [`INVESTIGATION.md`](../praat_ja/INVESTIGATION.md) 参照。

## ローカル開発

```bash
# 初回クローン (submodule込み)
git clone --recursive https://github.com/labphonlab/praat-ja-fork.git
cd praat-ja-fork

# 翻訳辞書を upstream に適用
pip install pyyaml
python3 scripts/apply_translations.py \
    --upstream upstream \
    --translations translations

# ビルド (Linux 例)
cd upstream
cp makefiles/makefile.defs.linux.pulse makefile.defs
make -j$(nproc) PRAAT_ARCH=x64v3 PRAAT_COMPILER=gcc
./praat
```

新しい翻訳項目を追加する:

```bash
# upstream から未翻訳文字列を抽出
python3 scripts/extract_strings.py upstream/sys/Editor.cpp \
    --existing translations/menus.yaml \
    > new_strings.yaml

# new_strings.yaml の "ja:" を埋めて translations/editor_menus.yaml にマージ
```

## ライセンス

- **本リポジトリの内容 (辞書・スクリプト・ワークフロー)**: 翻訳辞書は派生物のため
  **GPL v3** で配布
- **Praat 本体**: 上流の通り **GPL v3+** (Boersma & Weenink)
- 詳細: [`LICENSE`](./LICENSE), [`COPYING.GPL`](./COPYING.GPL)
- 改変内容の記録: [`MODIFICATIONS.md`](./MODIFICATIONS.md)

## 公式 Praat との関係

本フォークは独立した派生プロジェクトです。バグや機能要望は本リポジトリの
[Issues](https://github.com/labphonlab/praat-ja-fork/issues) へお願いします。
**公式 Praat (<https://github.com/praat/praat>) には絶対に投稿しないでください。**

## 関連プロジェクト

- **`labphonlab/praat_ja`**: 別アプローチの日本語フロントエンド (ランチャー方式)。
  Praat本体には手を加えず、PySide6 の日本語UI から公式 Praat を呼び出す方式。
