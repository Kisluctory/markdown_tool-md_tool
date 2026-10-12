import os
import tempfile
import unittest


class TestGuiSmoke(unittest.TestCase):
    """验证 GUI 能构建并完成渲染与备份流程（无显示环境时自动跳过）。"""

    def test_render_and_backup(self):
        try:
            import tkinter as tk
            import gui
        except Exception as e:
            self.skipTest(f'tkinter 不可用：{e}')
        try:
            root = tk.Tk()
        except Exception as e:
            self.skipTest(f'无法创建窗口：{e}')
        root.withdraw()
        try:
            d = tempfile.mkdtemp()
            app = gui.App(root, base_dir=d)
            md = ('# 标题\n\n这是**加粗**和`代码`。\n\n'
                  '- 项目一\n- [x] 已完成\n\n'
                  '| A | B |\n| --- | --- |\n| 1 | 2 |\n\n> 引用\n\n---\n')
            app.editor.insert('1.0', md)
            app.render_preview()
            content = app.preview.get('1.0', 'end-1c')
            for c in ['标题', '加粗', '代码', '项目一', '已完成', 'A', 'B', '引用', '─']:
                self.assertIn(c, content)
            name = app.store.add('# 文档\n', '/tmp/doc.md', '文档')
            self.assertEqual(app.store.list()[-1][1], '文档')
            self.assertEqual(app.store.get_original(name), '/tmp/doc.md')
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
