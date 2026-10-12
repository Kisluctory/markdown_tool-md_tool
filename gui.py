"""iRead V1 — tkinter 界面（Win11 记事本风格，黑灰简约）。"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import markdown_render as mr
import storage


def _app_base_dir():
    """程序数据目录：PyInstaller 打包后取 exe 同级目录，源码运行取脚本目录。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _app_base_dir()

C = {
    'win': '#1f1f1f',
    'panel': '#252526',
    'editor': '#1e1e1e',
    'fg': '#d4d4d4',
    'muted': '#8a8a8a',
    'accent': '#0078d4',
    'border': '#3c3c3c',
    'btn': '#333333',
    'btn_active': '#404040',
    'sel': '#264f78',
    'head': '#e8e8e8',
    'code_bg': '#2d2d2d',
    'codeblock_bg': '#1a1a1a',
    'quote': '#9cdcfe',
    'bullet': '#c586c0',
    'hr': '#5a5a5a',
}

UI_FONT = 'Segoe UI'
MONO_FONT = 'Consolas'


class App:
    def __init__(self, root, base_dir=None):
        self.root = root
        root.title('iRead')
        root.geometry('1080x680')
        root.minsize(720, 480)
        root.configure(bg=C['win'])

        self.store = storage.BackupStore(base_dir or APP_DIR)
        self.current = None          # {'original','backup_name','title','encoding'}
        self.view = 'edit'           # 'edit' | 'preview'
        self.list_visible = True
        self._names = []             # 列表 index -> backup name

        self._build_ui()
        self.refresh_list()
        self._update_status('就绪 — 点击「打开文件」选择 Markdown 文件')

    # ---------- 构建 ----------

    def _mk_btn(self, parent, text, command, small=False):
        b = tk.Button(parent, text=text, command=command, bg=C['btn'], fg=C['fg'],
                      activebackground=C['btn_active'], activeforeground='#ffffff',
                      relief='flat', bd=0, highlightthickness=0, cursor='hand2',
                      font=(UI_FONT, 9 if small else 10),
                      padx=8 if small else 12, pady=3 if small else 5)
        return b

    def _build_ui(self):
        # 工具栏
        bar = tk.Frame(self.root, bg=C['panel'], height=44)
        bar.pack(side='top', fill='x')
        bar.pack_propagate(False)
        self.list_btn = self._mk_btn(bar, '◀ 列表', self.toggle_list)
        self.list_btn.pack(side='left', padx=(10, 4), pady=7)
        self._mk_btn(bar, '打开文件', self.open_file).pack(side='left', padx=4, pady=7)
        self.view_btn = self._mk_btn(bar, '预览', self.toggle_view)
        self.view_btn.pack(side='left', padx=4, pady=7)
        self._mk_btn(bar, '快速保存', self.save_original).pack(side='right', padx=(4, 10), pady=7)
        self._mk_btn(bar, '保存', self.save_backup).pack(side='right', padx=4, pady=7)

        # 主区域
        self.main = tk.Frame(self.root, bg=C['win'])
        self.main.pack(side='top', fill='both', expand=True)

        # 左侧备份面板
        self.side = tk.Frame(self.main, bg=C['panel'], width=220)
        self.side.pack(side='left', fill='y')
        self.side.pack_propagate(False)

        head = tk.Frame(self.side, bg=C['panel'])
        head.pack(side='top', fill='x', pady=(10, 4))
        tk.Label(head, text='备份列表', bg=C['panel'], fg=C['head'],
                 font=(UI_FONT, 11, 'bold')).pack(side='left', padx=10)
        self._mk_btn(head, '✕', self.toggle_list, small=True).pack(side='right', padx=8)

        self.listbox = tk.Listbox(self.side, bg=C['panel'], fg=C['fg'],
                                  selectbackground=C['sel'], selectforeground='#ffffff',
                                  activestyle='none', bd=0, highlightthickness=0,
                                  font=(UI_FONT, 10))
        self.listbox.pack(side='top', fill='both', expand=True, padx=6, pady=(0, 6))
        self.listbox.bind('<<ListboxSelect>>', self.on_select_backup)
        self._mk_btn(self.side, '删除选中', self.delete_backup).pack(
            side='bottom', fill='x', padx=10, pady=(4, 12))

        # 内容区
        self.content = tk.Frame(self.main, bg=C['editor'])
        self.content.pack(side='left', fill='both', expand=True)

        self.editor = tk.Text(self.content, wrap='word', undo=True, bg=C['editor'],
                              fg=C['fg'], insertbackground='#ffffff',
                              selectbackground=C['sel'], font=(MONO_FONT, 11),
                              bd=0, padx=16, pady=14, highlightthickness=0, relief='flat')
        self.editor.pack(fill='both', expand=True)

        self.preview = tk.Text(self.content, wrap='word', bg=C['editor'], fg=C['fg'],
                               state='disabled', bd=0, padx=16, pady=14,
                               highlightthickness=0, relief='flat', cursor='arrow')
        self._config_preview_tags()

        # 状态栏
        self.status = tk.Label(self.root, text='', bg=C['panel'], fg=C['muted'],
                               anchor='w', padx=12, pady=4, font=(UI_FONT, 9))
        self.status.pack(side='bottom', fill='x')

    def _config_preview_tags(self):
        p = self.preview
        p.tag_configure('h1', font=(UI_FONT, 22, 'bold'), foreground=C['head'], spacing1=14, spacing3=6)
        p.tag_configure('h2', font=(UI_FONT, 18, 'bold'), foreground=C['head'], spacing1=10, spacing3=4)
        p.tag_configure('h3', font=(UI_FONT, 15, 'bold'), foreground=C['head'], spacing1=8, spacing3=4)
        p.tag_configure('h4', font=(UI_FONT, 13, 'bold'), foreground='#dcdcdc', spacing1=6, spacing3=2)
        p.tag_configure('h5', font=(UI_FONT, 12, 'bold'), foreground='#dcdcdc', spacing1=4, spacing3=2)
        p.tag_configure('h6', font=(UI_FONT, 11, 'bold'), foreground='#b0b0b0', spacing1=4, spacing3=2)
        p.tag_configure('quote', foreground=C['quote'])
        p.tag_configure('quote_mark', foreground=C['quote'], font=(MONO_FONT, 10))
        p.tag_configure('hr', foreground=C['hr'], font=(MONO_FONT, 10))
        p.tag_configure('list_bullet', foreground=C['bullet'])
        p.tag_configure('codeblock', font=(MONO_FONT, 10), background=C['codeblock_bg'],
                        foreground='#d4d4d4', spacing1=6, spacing3=6, lmargin1=12, lmargin2=12)
        p.tag_configure('table_head', font=(MONO_FONT, 10, 'bold'), foreground=C['head'])
        p.tag_configure('table_row', font=(MONO_FONT, 10))
        p.tag_configure('table_sep', font=(MONO_FONT, 10), foreground=C['hr'])
        self._inline_tag_cache = {}

    def _inline_tag(self, styles):
        key = ''.join(sorted(styles)) or 'plain'
        if key not in self._inline_tag_cache:
            family = MONO_FONT if 'code' in styles else UI_FONT
            size = 10 if 'code' in styles else 11
            weight = 'bold' if 'bold' in styles else 'normal'
            slant = 'italic' if 'italic' in styles else 'roman'
            opts = {'font': (family, size, weight, slant)}
            if 'code' in styles:
                opts['background'] = C['code_bg']
            if 'strike' in styles:
                opts['overstrike'] = 1
                opts['foreground'] = C['muted']
            self.preview.tag_configure(key, **opts)
            self._inline_tag_cache[key] = key
        return key

    # ---------- 渲染 ----------

    def _insert_inlines(self, segments, base_tags=()):
        for text, styles in segments:
            tags = list(base_tags) + [self._inline_tag(styles)]
            self.preview.insert('end', text, tuple(tags))

    def render_preview(self):
        text = self.editor.get('1.0', 'end-1c')
        blocks = mr.parse_blocks(text)
        p = self.preview
        p.configure(state='normal')
        p.delete('1.0', 'end')
        ordered = {}
        for b in blocks:
            t = b['type']
            if t == 'heading':
                p.insert('end', ''.join(x for x, _ in b['inlines']) + '\n', f"h{b['level']}")
            elif t == 'paragraph':
                self._insert_inlines(b['inlines'])
                p.insert('end', '\n\n')
            elif t == 'code':
                p.insert('end', b['text'] + '\n', 'codeblock')
            elif t == 'hr':
                p.insert('end', '─' * 64 + '\n', 'hr')
            elif t == 'quote':
                p.insert('end', '▎ ', 'quote_mark')
                self._insert_inlines(b['inlines'], ('quote',))
                p.insert('end', '\n\n')
            elif t == 'list_item':
                indent = '  ' * (b['indent'] // 2)
                if b['task'] is not None:
                    bullet = '☑ ' if b['task'] else '☐ '
                elif b['ordered']:
                    key = ('o', b['indent'])
                    ordered[key] = ordered.get(key, 0) + 1
                    bullet = f"{ordered[key]}. "
                else:
                    bullet = '• '
                p.insert('end', indent + bullet, 'list_bullet')
                self._insert_inlines(b['inlines'])
                p.insert('end', '\n')
            elif t == 'table':
                self._render_table(b)
            if t != 'list_item':
                ordered = {}
        p.configure(state='disabled')

    def _render_table(self, b):
        header = b['header']
        rows = b['rows']
        align = b['align']
        ncol = max([len(header)] + [len(r) for r in rows])
        widths = [0] * ncol
        for r in [header] + rows:
            for c in range(ncol):
                val = r[c] if c < len(r) else ''
                w = mr.display_width(val)
                if w > widths[c]:
                    widths[c] = w

        def fmt(cells):
            parts = []
            for c in range(ncol):
                val = cells[c] if c < len(cells) else ''
                a = align[c] if c < len(align) else 'left'
                pad = widths[c] - mr.display_width(val)
                if a == 'right':
                    cell = ' ' * pad + val
                elif a == 'center':
                    left = pad // 2
                    cell = ' ' * left + val + ' ' * (pad - left)
                else:
                    cell = val + ' ' * pad
                parts.append(cell)
            return ' │ '.join(parts)

        p = self.preview
        p.insert('end', fmt(header) + '\n', 'table_head')
        p.insert('end', '─┼─'.join('─' * w for w in widths) + '\n', 'table_sep')
        for r in rows:
            p.insert('end', fmt(r) + '\n', 'table_row')
        p.insert('end', '\n')

    # ---------- 视图切换 ----------

    def _show_edit(self):
        self.preview.pack_forget()
        self.editor.pack(fill='both', expand=True)
        self.view = 'edit'
        self.view_btn.config(text='预览')

    def _show_preview(self):
        self.editor.pack_forget()
        self.render_preview()
        self.preview.pack(fill='both', expand=True)
        self.view = 'preview'
        self.view_btn.config(text='编辑')

    def toggle_view(self):
        if self.view == 'edit':
            self._show_preview()
        else:
            self._show_edit()

    def toggle_list(self):
        if self.list_visible:
            self.side.pack_forget()
            self.list_btn.config(text='▶ 列表')
        else:
            self.side.pack(side='left', fill='y', before=self.content)
            self.list_btn.config(text='◀ 列表')
        self.list_visible = not self.list_visible

    # ---------- 动作 ----------

    def _load_text(self, text):
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', text)
        self._show_edit()

    def open_file(self):
        path = filedialog.askopenfilename(
            title='打开 Markdown 文件',
            filetypes=[('Markdown 文件', '*.md'), ('所有文件', '*.*')])
        if not path:
            return
        try:
            text, enc = storage.read_text(path)
        except ValueError as e:
            messagebox.showerror('无法打开', str(e))
            return
        except OSError as e:
            messagebox.showerror('无法打开', f'读取文件失败：{e}')
            return
        title = mr.extract_h1(text) or os.path.basename(path)
        backup_name = self.store.add(text, path, title)
        self.current = {'original': path, 'backup_name': backup_name,
                        'title': title, 'encoding': enc}
        self._load_text(text)
        self.refresh_list()
        self._update_status(f'已打开 {os.path.basename(path)}（编码 {enc}），已创建备份 {backup_name}')

    def save_backup(self):
        if not self.current or not self.current.get('backup_name'):
            messagebox.showwarning('保存', '请先打开文件')
            return
        text = self.editor.get('1.0', 'end-1c')
        path = self.store.get_backup_path(self.current['backup_name'])
        try:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
        except OSError as e:
            messagebox.showerror('保存失败', f'无法写入备份：{e}')
            return
        self._update_status('已保存到备份（原文件未改动）')

    def save_original(self):
        if not self.current or not self.current.get('original'):
            messagebox.showwarning('覆盖保存', '当前文档没有关联的原文件')
            return
        if not messagebox.askyesno('覆盖保存', '确定用当前内容覆盖原文件？\n' + self.current['original']):
            return
        text = self.editor.get('1.0', 'end-1c')
        try:
            with open(self.current['original'], 'w', encoding='utf-8', newline='') as f:
                f.write(text)
        except OSError as e:
            messagebox.showerror('保存失败', f'无法覆盖原文件：{e}')
            return
        self._update_status('已覆盖原文件')

    def delete_backup(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo('删除', '请先在左侧选择一个备份')
            return
        idx = sel[0]
        name = self._names[idx]
        title = self.store.list()[idx][1]
        if not messagebox.askyesno('删除备份', f'确定删除备份「{title}」？\n（原文件不受影响）'):
            return
        self.store.delete(name)
        if self.current and self.current.get('backup_name') == name:
            self.current['backup_name'] = None
        self.refresh_list()
        self._update_status(f'已删除备份「{title}」')

    def on_select_backup(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        name = self._names[idx]
        path = self.store.get_backup_path(name)
        try:
            text, enc = storage.read_text(path)
        except (ValueError, OSError) as e:
            messagebox.showerror('无法打开备份', str(e))
            return
        title = self.store.list()[idx][1]
        original = self.store.get_original(name)
        self.current = {'original': original, 'backup_name': name,
                        'title': title, 'encoding': enc}
        self._load_text(text)
        self._update_status(f'已打开备份「{title}」' + (f'（原文件 {original}）' if original else ''))

    # ---------- 其他 ----------

    def refresh_list(self):
        self.listbox.delete(0, 'end')
        entries = self.store.list()
        self._names = [e[0] for e in entries]
        for name, title in entries:
            self.listbox.insert('end', title)

    def _update_status(self, msg):
        self.status.config(text=msg)


def run(base_dir=None):
    root = tk.Tk()
    App(root, base_dir=base_dir)
    root.mainloop()
