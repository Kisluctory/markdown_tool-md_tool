import unittest

import markdown_render as mr


class TestExtractH1(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(mr.extract_h1('# 标题\n正文'), '标题')

    def test_none(self):
        self.assertIsNone(mr.extract_h1('正文\n## 二级'))

    def test_leading_ws(self):
        self.assertEqual(mr.extract_h1('   # 你好  '), '你好')


class TestInline(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(mr.parse_inline('abc'), [('abc', frozenset())])

    def test_bold(self):
        self.assertEqual(mr.parse_inline('**b**'), [('b', frozenset({'bold'}))])

    def test_italic(self):
        self.assertEqual(mr.parse_inline('*i*'), [('i', frozenset({'italic'}))])

    def test_strike(self):
        self.assertEqual(mr.parse_inline('~~s~~'), [('s', frozenset({'strike'}))])

    def test_code(self):
        self.assertEqual(mr.parse_inline('`c`'), [('c', frozenset({'code'}))])

    def test_mixed(self):
        self.assertEqual(mr.parse_inline('a **b** c'),
                         [('a ', frozenset()), ('b', frozenset({'bold'})), (' c', frozenset())])


class TestBlocks(unittest.TestCase):
    def types(self, text):
        return [b['type'] for b in mr.parse_blocks(text)]

    def test_heading_and_paragraph(self):
        blocks = mr.parse_blocks('# 一级\n\n正文')
        self.assertEqual(blocks[0]['type'], 'heading')
        self.assertEqual(blocks[0]['level'], 1)
        self.assertEqual(blocks[1]['type'], 'paragraph')

    def test_code_fence(self):
        blocks = mr.parse_blocks('```python\nprint(1)\n```')
        self.assertEqual(blocks[0]['type'], 'code')
        self.assertEqual(blocks[0]['lang'], 'python')
        self.assertEqual(blocks[0]['text'], 'print(1)')

    def test_hr(self):
        self.assertEqual(self.types('---'), ['hr'])

    def test_quote(self):
        self.assertEqual(self.types('> 引用'), ['quote'])

    def test_ulist(self):
        blocks = mr.parse_blocks('- a\n- b')
        self.assertEqual([b['type'] for b in blocks], ['list_item', 'list_item'])
        self.assertFalse(blocks[0]['ordered'])

    def test_olist(self):
        blocks = mr.parse_blocks('1. a\n2. b')
        self.assertTrue(blocks[0]['ordered'])
        self.assertTrue(blocks[1]['ordered'])

    def test_task(self):
        blocks = mr.parse_blocks('- [x] done')
        self.assertTrue(blocks[0]['task'])

    def test_table(self):
        blocks = mr.parse_blocks('| A | B |\n| --- | --- |\n| 1 | 2 |')
        self.assertEqual(blocks[0]['type'], 'table')
        self.assertEqual(blocks[0]['header'], ['A', 'B'])
        self.assertEqual(blocks[0]['rows'], [['1', '2']])


class TestDisplayWidth(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(mr.display_width('abc'), 3)

    def test_cjk(self):
        self.assertEqual(mr.display_width('你好'), 4)


if __name__ == '__main__':
    unittest.main()
