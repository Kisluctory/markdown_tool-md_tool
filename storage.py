"""iRead V1 — 文件读写、编码回退与备份管理（纯逻辑，可测试）。"""
import os
import re
import json
import codecs

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def read_text(path, max_size=MAX_FILE_SIZE):
    """读取文本文件，返回 (text, encoding_name)。

    超限抛 ValueError；读取失败抛 OSError。
    """
    size = os.path.getsize(path)
    if size > max_size:
        raise ValueError(f'文件过大（{size // (1024 * 1024)}MB > 10MB），暂不支持打开')
    with open(path, 'rb') as f:
        data = f.read()
    # BOM 优先
    if data.startswith(codecs.BOM_UTF8):
        return data.decode('utf-8-sig'), 'UTF-8'
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return data.decode('utf-16'), 'UTF-16'
    # 常见编码回退
    for enc, label in (('utf-8', 'UTF-8'), ('gb18030', 'GB18030')):
        try:
            return data.decode(enc), label
        except UnicodeDecodeError:
            continue
    # 兜底（永不失败）
    return data.decode('latin-1'), 'latin-1'


def _sanitize_filename(title: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', '_', title)
    s = re.sub(r'\s+', ' ', s).strip().strip('.')
    return s[:80]


class BackupStore:
    """在程序目录下的 backups/ 目录管理备份，并用 index.json 记录 备份->原文件 映射。"""

    def __init__(self, base_dir):
        self.dir = os.path.join(base_dir, 'backups')
        os.makedirs(self.dir, exist_ok=True)
        self.index_path = os.path.join(self.dir, 'index.json')
        self._index = self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except (OSError, ValueError):
                pass
        return {}

    def _save_index(self):
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    def list(self):
        """返回 [(backup_name, title), ...]，保持索引顺序。"""
        return [(name, e.get('title', name)) for name, e in self._index.items()]

    def add(self, content, original_path, title):
        name = self._unique_name(title)
        with open(os.path.join(self.dir, name), 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        self._index[name] = {'original': original_path, 'title': title}
        self._save_index()
        return name

    def get_backup_path(self, name):
        return os.path.join(self.dir, name)

    def get_original(self, name):
        return self._index.get(name, {}).get('original')

    def delete(self, name):
        p = os.path.join(self.dir, name)
        if os.path.exists(p):
            os.remove(p)
        self._index.pop(name, None)
        self._save_index()

    def _unique_name(self, title):
        base = _sanitize_filename(title) or 'untitled'
        name = base + '.md'
        if name not in self._index and not os.path.exists(os.path.join(self.dir, name)):
            return name
        k = 2
        while (f'{base}_{k}.md' in self._index
               or os.path.exists(os.path.join(self.dir, f'{base}_{k}.md'))):
            k += 1
        return f'{base}_{k}.md'
