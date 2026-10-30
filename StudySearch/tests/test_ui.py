"""通过 Streamlit 官方测试框架执行真实页面逻辑。"""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class InterfaceTests(unittest.TestCase):
    def test_demo_search_preview_and_method_switch(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.metric[0].value, "1")
        at.text_input[0].set_value("什么是矩阵的秩").run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn("第 1 页", at.subheader[0].value)
        at.checkbox[0].check().run()
        self.assertEqual(len(at.exception), 0)
        at.sidebar.radio[1].set_value("关键词覆盖率").run()
        self.assertEqual(len(at.exception), 0)
        at.multiselect[0].set_value([]).run()
        self.assertIn("至少选择", at.info[0].value)
        at.sidebar.radio[0].set_value("上传 PDF").run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn("请上传", at.info[0].value)


if __name__ == "__main__":
    unittest.main()
