import os
import tempfile
import unittest

import storage


class TestReadText(unittest.TestCase):
    def test_utf8(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'a.md')
        with open(p, 'w', encoding='utf-8') as f:
            f.write('你好')
        text, enc = storage.read_text(p)
        self.assertEqual(text, '你好')
        self.assertEqual(enc, 'UTF-8')

    def test_gbk(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'a.md')
        with open(p, 'w', encoding='gb18030') as f:
            f.write('中文')
        text, enc = storage.read_text(p)
        self.assertEqual(text, '中文')
        self.assertEqual(enc, 'GB18030')

    def test_too_large(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'big.md')
        with open(p, 'wb') as f:
            f.write(b'0' * (storage.MAX_FILE_SIZE + 1))
        with self.assertRaises(ValueError):
            storage.read_text(p)


class TestBackupStore(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.store = storage.BackupStore(self.d)

    def test_add_and_list(self):
        name = self.store.add('# 你好\n', '/tmp/x.md', '你好')
        self.assertEqual(self.store.list(), [(name, '你好')])
        self.assertEqual(self.store.get_original(name), '/tmp/x.md')

    def test_unique_name(self):
        n1 = self.store.add('a', '/tmp/x.md', '标题')
        n2 = self.store.add('b', '/tmp/y.md', '标题')
        self.assertNotEqual(n1, n2)

    def test_delete(self):
        name = self.store.add('a', '/tmp/x.md', '标题')
        self.store.delete(name)
        self.assertEqual(self.store.list(), [])
        self.assertFalse(os.path.exists(self.store.get_backup_path(name)))


if __name__ == '__main__':
    unittest.main()
