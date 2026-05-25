#!/usr/bin/env bash
# migrate-fork-to-new-repo.sh
#
# praat_open リポジトリの praat_ja_fork/ 配下を、新リポジトリ
# labphonlab/praat-ja-fork のルートとしてプッシュする移行ヘルパー。
#
# 前提:
#   - GitHub 上で空の labphonlab/praat-ja-fork リポジトリを作成済みであること
#
# 使い方:
#   cd <praat_open repo>
#   bash praat_ja_fork/scripts/migrate-fork-to-new-repo.sh \
#       /tmp/praat-ja-fork-staging \
#       https://github.com/labphonlab/praat-ja-fork.git

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "使い方: $0 <staging directory> [<remote URL>]" >&2
    exit 1
fi

STAGING_DIR="$1"
REMOTE_URL="${2:-}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC="$REPO_ROOT/praat_ja_fork"

if [ ! -d "$SRC" ]; then
    echo "エラー: $SRC が見つかりません" >&2
    exit 1
fi

if [ -e "$STAGING_DIR" ]; then
    echo "エラー: $STAGING_DIR は既に存在します" >&2
    exit 1
fi

echo "==> ステージング: $STAGING_DIR"
mkdir -p "$STAGING_DIR"
cp -a "$SRC"/. "$STAGING_DIR"/

cd "$STAGING_DIR"

echo "==> git init"
git init -b main

echo "==> upstream を submodule として追加"
# .gitmodules は既にコピーされているが、実体は submodule add で追加
git submodule add -b master https://github.com/praat/praat.git upstream

git add -A
git commit -m "Initial commit — Unofficial Japanese localization fork of Praat

非公式 Praat 日本語化版 (Praat JA Fork - Unofficial)

This is a translation-patch fork: upstream Praat is included as a
submodule and translation YAML files are applied at build time.
Currently translates the Objects window main menu (~125 unique strings,
~187 occurrences in sys/praat_objectMenus.cpp).

Not affiliated with the official Praat project.
Inherits GPL v3 from upstream.
"

if [ -n "$REMOTE_URL" ]; then
    git remote add origin "$REMOTE_URL"
    echo ""
    echo "==> 次のコマンドで push:"
    echo "    cd $STAGING_DIR"
    echo "    git push -u origin main"
fi

echo ""
echo "==> 完了。次の手順:"
echo "  1) GitHub 上で空の labphonlab/praat-ja-fork リポジトリを作成"
echo "  2) $STAGING_DIR から main を push"
echo "  3) Settings → Actions → General で Workflow permissions を 'Read and write' に"
echo "  4) 初回 push or workflow_dispatch で build.yml が起動 → 3プラットフォームのビルド"
