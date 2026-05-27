#!/usr/bin/env python3
"""extract_strings.py — Praat C++ ソースから翻訳対象の U"..." 文字列を抽出する.

praat_addMenuCommand / Editor_addCommand / FORM などのマクロ呼び出しに含まれる
ユーザー可視文字列を抜き出し、YAML 翻訳辞書のテンプレートとして書き出す。

使い方:
    python3 extract_strings.py upstream/sys/praat_objectMenus.cpp > new_strings.yaml
    python3 extract_strings.py upstream/sys/praat_objectMenus.cpp \\
        --existing translations/menus.yaml > diff.yaml

抽出ルール (簡易版):
- 行頭〜マクロ名(空白)?(の後の最初の U"..." 群
- ターゲットマクロ: praat_addMenuCommand, praat_addAction, Editor_addCommand,
  FORM, FORM_READ, FORM_SAVE, TEXTFIELD, BOOLEAN, RADIO, OPTION, LABEL,
  REAL, REAL_DEFAULT_UNDEFINED, INTEGER, POSITIVE, NATURAL, CHOICE,
  OPTIONMENU, WORD, SENTENCE, COMMENT, MUTABLE_LABEL, HEADING

各マクロでどの位置の引数が「UI表示文字列」かは個別に判定する。
コマンド識別子・ヘルプページ参照・空文字 ("") は除外。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML が必要です: pip install pyyaml\n")
    sys.exit(2)


# マクロ名 → 「UI 表示文字列」の引数位置 (0-indexed)
# 値が複数あるのは複数の引数を抽出することを意味する。
MACRO_UI_ARG_POSITIONS: dict[str, tuple[int, ...]] = {
    "praat_addMenuCommand": (1, 2),       # window-id (skip), menu name, label
    "praat_addFixedButtonCommand": (1,),  # window, label, ...
    "praat_addAction1": (1,),             # class, label
    "praat_addAction2": (2,),
    "praat_addAction3": (3,),
    "praat_addAction4": (4,),
    "Editor_addCommand": (1, 2),          # editor, menu name, label
    "Editor_addMenu": (0,),               # menu name (e.g. U"File")
    "GuiMenu_createInWindow": (1,),       # window, title, ...
    "GuiButton_createShown": (5,),        # parent, left,right,top,bottom, label
    "FORM": (1,),                         # name, dialog title, help page
    "FORM_READ": (1,),
    "FORM_SAVE": (1,),
    "TEXTFIELD": (1,),                    # var, label, default, ...
    "WORD": (1,),
    "SENTENCE": (1,),
    "REAL": (1,),
    "REAL_DEFAULT_UNDEFINED": (1,),
    "POSITIVE": (1,),
    "INTEGER": (1,),
    "NATURAL": (1,),
    "BOOLEAN": (1,),
    "RADIO": (1,),
    "OPTIONMENU": (1,),
    "OPTION": (0,),                       # OPTION(U"label")
    "CHOICE": (1,),
    "LABEL": (0,),                        # LABEL(U"text")
    "COMMENT": (0,),
    "MUTABLE_LABEL": (1,),
    "HEADING": (0,),
}


# U"..." リテラル (Cの隣接連結も拾う)
U_LITERAL_RE = re.compile(r'U"((?:[^"\\]|\\.)*)"(?:\s*U"((?:[^"\\]|\\.)*)")*')


def _strip_comments(src: str) -> str:
    """ // と /* ... */ コメントを潰す (粗いが十分)."""
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
    src = re.sub(r'//[^\n]*', '', src)
    return src


def _scan_args(text: str, start: int) -> tuple[list[str], int]:
    """text[start] が '(' の直後を指すとき、対応する ')' までを引数リストとして返す.
    戻り値: (引数文字列のリスト, 閉じ括弧位置+1).
    引数は U"..." リテラルのみを取り出した結果。それ以外はそのまま文字列で保持。
    """
    depth = 1
    i = start
    cur = []
    args: list[str] = []
    while i < len(text):
        c = text[i]
        if c == '"':
            # 文字列リテラルを読み飛ばす（U" や "" 連結も含む）
            end = i + 1
            while end < len(text):
                if text[end] == '\\':
                    end += 2
                    continue
                if text[end] == '"':
                    end += 1
                    break
                end += 1
            cur.append(text[i:end])
            i = end
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                args.append("".join(cur).strip())
                return args, i + 1
        elif c == ',' and depth == 1:
            args.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    return args, i


def _extract_u_strings(arg_text: str) -> list[str]:
    """引数テキストから連結された U"..." を解凍して文字列内容のリストを返す."""
    out: list[str] = []
    pos = 0
    while True:
        idx = arg_text.find('U"', pos)
        if idx < 0:
            break
        # 連結された U"..." U"..." を結合
        parts: list[str] = []
        j = idx
        while j < len(arg_text):
            if arg_text[j:j + 2] != 'U"':
                # スキップして空白だけなら次の連結を許容
                k = j
                while k < len(arg_text) and arg_text[k] in " \t\n\r":
                    k += 1
                if k < len(arg_text) and arg_text[k:k + 2] == 'U"':
                    j = k
                    continue
                break
            # 文字列本体を読む
            end = j + 2
            buf: list[str] = []
            while end < len(arg_text):
                ch = arg_text[end]
                if ch == '\\' and end + 1 < len(arg_text):
                    nxt = arg_text[end + 1]
                    if nxt == 'n':
                        buf.append('\n')
                    elif nxt == 't':
                        buf.append('\t')
                    elif nxt == '"':
                        buf.append('"')
                    elif nxt == '\\':
                        buf.append('\\')
                    else:
                        buf.append(nxt)
                    end += 2
                    continue
                if ch == '"':
                    end += 1
                    break
                buf.append(ch)
                end += 1
            parts.append("".join(buf))
            j = end
        out.append("".join(parts))
        pos = j
    return out


def extract_from_file(path: Path) -> dict[str, dict]:
    """ファイルから {原文: {sources: [<file:line>], macro: <name>}} を返す."""
    text_orig = path.read_text(encoding="utf-8")
    text = _strip_comments(text_orig)
    # 行番号は原文ベース。コメント除去で行ずれが起きるので簡易計算は諦め、
    # 抜けた行は近似（このスクリプトの用途には十分）.

    results: dict[str, dict] = {}

    # マクロ呼び出し: macro_name (
    macro_re = re.compile(
        r'\b(' + '|'.join(re.escape(m) for m in MACRO_UI_ARG_POSITIONS) + r')\s*\('
    )

    for m in macro_re.finditer(text):
        macro = m.group(1)
        positions = MACRO_UI_ARG_POSITIONS[macro]
        args, _end = _scan_args(text, m.end())
        for pos in positions:
            if pos >= len(args):
                continue
            strings = _extract_u_strings(args[pos])
            for s in strings:
                if not s:
                    continue
                # 識別子っぽいもの（空白を含まず、全部小文字スネークかキャメル）はスキップ
                if not _looks_like_ui_text(s):
                    continue
                entry = results.setdefault(s, {"macros": set(), "files": set()})
                entry["macros"].add(macro)
                entry["files"].add(path.name)

    # set を list に変換
    for k, v in results.items():
        v["macros"] = sorted(v["macros"])
        v["files"] = sorted(v["files"])
    return results


def _looks_like_ui_text(s: str) -> bool:
    """文字列がUI表示テキストっぽいか判定する.
    識別子 (snake_case / CamelCase 単体) は除外、空白や記号があれば採用。
    """
    if not s:
        return False
    if len(s) == 1:
        # 単一文字 (キーボードショートカット等) は除外
        return False
    # 全部小文字スネークケース・キャメルケースで空白なし → 識別子の可能性
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', s):
        # ただし "Save", "Open" のような単一英単語は UI テキストの可能性あり
        # 短く単純な英単語は UI として扱う
        if s[0].isupper() and len(s) <= 20:
            return True
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="抽出対象のC++ソースファイル")
    parser.add_argument("--existing", help="既存YAML辞書 (差分のみ出力)")
    parser.add_argument("--output", "-o", help="出力先 (省略時は stdout)")
    args = parser.parse_args()

    src_path = Path(args.source)
    if not src_path.exists():
        sys.stderr.write(f"ファイルがありません: {src_path}\n")
        return 1

    extracted = extract_from_file(src_path)

    existing: dict = {}
    if args.existing:
        ex_path = Path(args.existing)
        if ex_path.exists():
            existing = yaml.safe_load(ex_path.read_text(encoding="utf-8")) or {}

    out_data = {}
    for original, meta in sorted(extracted.items()):
        if existing.get(original):
            continue  # 翻訳済みはスキップ
        out_data[original] = {
            "ja": "",
            "macros": meta["macros"],
            "files": meta["files"],
        }

    text = yaml.safe_dump(
        out_data,
        allow_unicode=True,
        sort_keys=True,
        default_flow_style=False,
    )

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        sys.stderr.write(f"抽出 {len(out_data)} 件 → {args.output}\n")
    else:
        sys.stdout.write(text)
        sys.stderr.write(f"抽出 {len(out_data)} 件\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
