#!/usr/bin/env python3
"""apply_translations.py — Praat ソースに翻訳辞書を当てる.

upstream/ (vanilla Praat) に対して translations/*.yaml の対応する原文を
日本語訳に書き換える。書き換えは「U"原文"」リテラル単位で行うので、
コメント中の原文や別文脈での使用には影響しない。

使い方:
    python3 apply_translations.py \\
        --upstream upstream \\
        --translations translations \\
        --files sys/praat_objectMenus.cpp

    # 全ファイル一括 (translations にあるファイル名すべて):
    python3 apply_translations.py --upstream upstream --translations translations

ドライラン:
    python3 apply_translations.py ... --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML が必要です: pip install pyyaml\n")
    sys.exit(2)


def _escape_for_c_literal(s: str) -> str:
    """Python文字列 → C++ U"..." の中に入る形にエスケープ.
    バックスラッシュ・ダブルクォート・改行・タブを処理。
    """
    out: list[str] = []
    for ch in s:
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append('\\"')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\t':
            out.append('\\t')
        elif ord(ch) < 0x20:
            out.append(f'\\x{ord(ch):02x}')
        else:
            out.append(ch)
    return "".join(out)


def _decode_c_literal(escaped: str) -> str:
    """C++ リテラル本体 → Python 文字列にデコード."""
    out: list[str] = []
    i = 0
    while i < len(escaped):
        ch = escaped[i]
        if ch == '\\' and i + 1 < len(escaped):
            nxt = escaped[i + 1]
            if nxt == 'n':
                out.append('\n')
            elif nxt == 't':
                out.append('\t')
            elif nxt == '"':
                out.append('"')
            elif nxt == '\\':
                out.append('\\')
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# U"..." (連結も拾う)
U_LITERAL_RE = re.compile(r'U"((?:[^"\\]|\\.)*)"')


def load_translations(translations_dir: Path) -> dict[str, str]:
    """translations/*.yaml をマージしてフラットな辞書を返す."""
    table: dict[str, str] = {}
    for yml in sorted(translations_dir.glob("*.yaml")):
        data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        for orig, value in data.items():
            if isinstance(value, str):
                ja = value
            elif isinstance(value, dict):
                ja = value.get("ja", "")
            else:
                ja = ""
            if ja and ja != orig:
                table[orig] = ja
    return table


def apply_to_file(
    src_path: Path,
    table: dict[str, str],
    *,
    dry_run: bool = False,
) -> tuple[int, list[str]]:
    """ファイルに翻訳を当てる. (置換数, 当てた原文のリスト)."""
    text = src_path.read_text(encoding="utf-8")

    replaced_count = 0
    applied: list[str] = []

    def repl(m: re.Match[str]) -> str:
        nonlocal replaced_count
        decoded = _decode_c_literal(m.group(1))
        if decoded in table:
            ja = table[decoded]
            replaced_count += 1
            applied.append(decoded)
            return f'U"{_escape_for_c_literal(ja)}"'
        return m.group(0)

    new_text = U_LITERAL_RE.sub(repl, text)

    if not dry_run and new_text != text:
        src_path.write_text(new_text, encoding="utf-8")

    return replaced_count, applied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, help="vanilla Praatソースのルート")
    parser.add_argument("--translations", required=True, help="翻訳辞書ディレクトリ")
    parser.add_argument("--files", nargs="*", help="対象ファイル (相対パス). 省略時は辞書中のfiles情報から決定")
    parser.add_argument("--dry-run", action="store_true", help="書き換えずに件数だけ報告")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    upstream = Path(args.upstream).resolve()
    translations_dir = Path(args.translations).resolve()

    if not upstream.exists():
        sys.stderr.write(f"upstreamディレクトリがありません: {upstream}\n")
        return 1
    if not translations_dir.exists():
        sys.stderr.write(f"翻訳ディレクトリがありません: {translations_dir}\n")
        return 1

    table = load_translations(translations_dir)
    sys.stderr.write(f"翻訳辞書: {len(table)} 件\n")

    # 対象ファイルの決定
    if args.files:
        target_files = [upstream / f for f in args.files]
    else:
        # 辞書から files: フィールドを集めて推定
        target_set: set[str] = set()
        for yml in sorted(translations_dir.glob("*.yaml")):
            data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
            for value in data.values():
                if isinstance(value, dict):
                    files = value.get("files") or []
                    for f in files:
                        target_set.add(f)
        # ファイル名だけが入っている可能性が高いので upstream 内を検索
        target_files = []
        for fname in sorted(target_set):
            matches = list(upstream.rglob(fname))
            if matches:
                target_files.extend(matches)

        if not target_files:
            # 既知の主要ファイルだけでもデフォルトで処理する
            default = upstream / "sys" / "praat_objectMenus.cpp"
            if default.exists():
                target_files = [default]

    if not target_files:
        sys.stderr.write("処理対象のファイルが見つかりません。--files で明示してください。\n")
        return 1

    total = 0
    per_file: dict[Path, int] = {}
    for f in target_files:
        if not f.exists():
            sys.stderr.write(f"  スキップ (見つからない): {f}\n")
            continue
        count, applied = apply_to_file(f, table, dry_run=args.dry_run)
        per_file[f] = count
        total += count
        prefix = "DRY-RUN " if args.dry_run else ""
        sys.stderr.write(f"  {prefix}{f}: {count} 件置換\n")
        if args.verbose and applied:
            for s in applied:
                sys.stderr.write(f"    - {s!r}\n")

    sys.stderr.write(f"\n合計: {total} 件の置換 ({len(per_file)} ファイル)\n")

    # 未使用の翻訳をレポート
    used = set()
    for f in target_files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        for orig, ja in table.items():
            if f'U"{_escape_for_c_literal(ja)}"' in text or f'U"{_escape_for_c_literal(orig)}"' in text:
                used.add(orig)
    unused = set(table.keys()) - used
    if unused:
        sys.stderr.write(f"\n警告: 辞書にあるが使用されなかった翻訳 {len(unused)} 件:\n")
        for s in sorted(unused)[:10]:
            sys.stderr.write(f"  - {s!r}\n")
        if len(unused) > 10:
            sys.stderr.write(f"  ... 他 {len(unused) - 10} 件\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
