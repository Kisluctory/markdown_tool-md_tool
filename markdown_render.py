"""iRead V1 — Markdown 文本级渲染核心（纯逻辑，无 GUI 依赖）。

将 Markdown 源码解析为结构化的 block 列表，供 tkinter 渲染层使用。
V1 不处理图片与超链接（原样保留为纯文本）。
"""
import re
import unicodedata


# ---------- 显示宽度工具（用于表格对齐） ----------

def display_width(s: str) -> int:
    """计算字符串的显示宽度：CJK/全角字符计 2，其余计 1。"""
    w = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            w += 2
        else:
            w += 1
    return w


def extract_h1(text: str):
    """提取首个 H1 标题文本；无则返回 None。"""
    for line in text.splitlines():
        m = re.match(r'^\s*#\s+(.+?)\s*$', line)
        if m:
            return m.group(1).strip()
    return None


# ---------- 行内解析 ----------

def parse_inline(s: str):
    """把一段文本解析为 [(text, frozenset_of_styles), ...]。

    支持：**粗体**、*斜体*、~~删除线~~、`行内代码`。
    图片与链接不特殊处理（原样保留为纯文本）。
    """
    segments = []
    i = 0
    n = len(s)
    specials = {'*', '`', '~'}
    while i < n:
        ch = s[i]
        if ch == '`':
            j = s.find('`', i + 1)
            if j != -1:
                segments.append((s[i + 1:j], frozenset({'code'})))
                i = j + 1
                continue
        elif ch == '~' and s.startswith('~~', i):
            j = s.find('~~', i + 2)
            if j != -1:
                for txt, st in parse_inline(s[i + 2:j]):
                    segments.append((txt, st | {'strike'}))
                i = j + 2
                continue
        elif ch == '*' and s.startswith('**', i):
            j = s.find('**', i + 2)
            if j != -1:
                for txt, st in parse_inline(s[i + 2:j]):
                    segments.append((txt, st | {'bold'}))
                i = j + 2
                continue
        elif ch == '*':
            j = s.find('*', i + 1)
            if j != -1:
                for txt, st in parse_inline(s[i + 1:j]):
                    segments.append((txt, st | {'italic'}))
                i = j + 1
                continue
        # 普通文本：吞掉连续的普通字符
        j = i
        while j < n and s[j] not in specials:
            j += 1
        if j == i:
            j = i + 1  # 无法匹配的特殊字符按普通字符处理
        segments.append((s[i:j], frozenset()))
        i = j
    return segments


# ---------- 块级解析 ----------

def _is_hr(line: str) -> bool:
    t = line.strip()
    if not t:
        return False
    if not set(t) <= {'-', '*', '_', ' '}:
        return False
    core = t.replace(' ', '')
    if len(core) < 3:
        return False
    return len(set(core)) == 1


def _is_table_delim(line: str) -> bool:
    t = line.strip()
    if '|' not in t:
        return False
    cells = [c.strip() for c in t.strip('|').split('|')]
    return bool(cells) and all(re.fullmatch(r':?-{1,}:?', c) for c in cells)


def _split_row(line: str):
    t = line.strip()
    if t.startswith('|'):
        t = t[1:]
    if t.endswith('|'):
        t = t[:-1]
    return [c.strip() for c in t.split('|')]


def _alignments(line: str):
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    out = []
    for c in cells:
        if c.startswith(':') and c.endswith(':'):
            out.append('center')
        elif c.endswith(':'):
            out.append('right')
        else:
            out.append('left')
    return out


def _list_marker(line: str):
    """若行以列表标记开头，返回 (indent, ordered, num_or_None, content)，否则 None。"""
    m = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.*)$', line)
    if not m:
        return None
    indent = len(m.group(1))
    marker = m.group(2)
    content = m.group(3)
    ordered = marker[0].isdigit()
    num = int(marker[:-1]) if ordered else None
    return indent, ordered, num, content


def _starts_new_block(line_raw: str, lines, i: int) -> bool:
    ns = line_raw.strip()
    if ns == '':
        return True
    if re.match(r'#{1,6}\s', ns):
        return True
    if ns.startswith('```') or ns.startswith('~~~'):
        return True
    if ns.startswith('>'):
        return True
    if _list_marker(line_raw):
        return True
    if _is_hr(ns):
        return True
    if '|' in ns and i + 1 < len(lines) and _is_table_delim(lines[i + 1]):
        return True
    return False


def _parse_list(lines, start):
    blocks = []
    i = start
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip() == '':
            break
        m = _list_marker(line)
        if not m:
            break
        indent, ordered, num, content = m
        task = None
        tm = re.match(r'^\[([ xX])\]\s+(.*)$', content)
        if tm:
            task = tm.group(1).lower() == 'x'
            content = tm.group(2)
        blocks.append({'type': 'list_item', 'ordered': ordered, 'num': num,
                       'indent': indent, 'task': task, 'inlines': parse_inline(content)})
        i += 1
    return blocks, i


def parse_blocks(text: str):
    """解析 Markdown 为 block 列表。每个 block 是一个 dict。"""
    lines = text.split('\n')
    n = len(lines)
    blocks = []
    i = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped == '':
            i += 1
            continue
        # 围栏代码块
        if stripped.startswith('```') or stripped.startswith('~~~'):
            fence = stripped[:3]
            lang = stripped[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith(fence):
                buf.append(lines[i])
                i += 1
            if i < n:
                i += 1  # 跳过闭合围栏
            blocks.append({'type': 'code', 'lang': lang, 'text': '\n'.join(buf)})
            continue
        # 标题
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            blocks.append({'type': 'heading', 'level': len(m.group(1)),
                           'inlines': parse_inline(m.group(2).strip())})
            i += 1
            continue
        # 分隔线
        if _is_hr(stripped):
            blocks.append({'type': 'hr'})
            i += 1
            continue
        # 表格
        if '|' in stripped and i + 1 < n and _is_table_delim(lines[i + 1]):
            header = _split_row(stripped)
            align = _alignments(lines[i + 1])
            i += 2
            rows = []
            while i < n and lines[i].strip() != '' and '|' in lines[i]:
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append({'type': 'table', 'header': header, 'align': align, 'rows': rows})
            continue
        # 引用块
        if stripped.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append({'type': 'quote', 'inlines': parse_inline(' '.join(buf))})
            continue
        # 列表
        if _list_marker(line):
            list_blocks, i = _parse_list(lines, i)
            blocks.extend(list_blocks)
            continue
        # 段落
        para_parts = [stripped]
        i += 1
        while i < n and not _starts_new_block(lines[i], lines, i):
            nl = lines[i]
            ns = nl.strip()
            sep = '\n' if nl.endswith('  ') else ' '
            para_parts.append(sep)
            para_parts.append(ns)
            i += 1
        blocks.append({'type': 'paragraph', 'inlines': parse_inline(''.join(para_parts))})
    return blocks
