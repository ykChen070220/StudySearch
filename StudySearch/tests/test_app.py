import unittest
import pymupdf
from app import Chunk, SearchIndex, extract_pdf, highlighted, split_text


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.index = SearchIndex([
            Chunk("a.pdf", "a", 1, "a1", "矩阵的秩是线性无关向量的最大个数。"),
            Chunk("b.pdf", "b", 2, "b2", "过拟合表现为训练效果很好而验证效果较差。")])

    def test_retrieval_and_filter(self):
        for method in ["tfidf", "keyword"]:
            self.assertEqual(self.index.search("矩阵的秩", method)[0]["page"], 1)
            self.assertEqual(self.index.search("矩阵", method, document_ids={"b"}), [])

    def test_empty_and_out_of_vocabulary(self):
        for query in ["", "！？", "的 是", "zzzxxyyqq"]:
            self.assertEqual(self.index.search(query), [])

    def test_html_escaped(self):
        rendered = highlighted('<script>alert(1)</script>矩阵', "矩阵")
        self.assertNotIn("<script>", rendered)
        self.assertIn("<mark>矩阵</mark>", rendered)

    def test_long_text_has_no_gaps(self):
        text = "".join(chr(0x4e00 + i) for i in range(1500))
        parts = split_text(text)
        self.assertTrue(all(len(p) <= 450 for p in parts))
        self.assertEqual(parts[0] + "".join(p[70:] for p in parts[1:]), text)

    def test_pdf_provenance_and_empty_page(self):
        doc = pymupdf.open()
        doc.new_page().insert_text((50, 50), "matrix rank")
        doc.new_page()
        chunks, warnings = extract_pdf("test.pdf", doc.tobytes())
        doc.close()
        self.assertEqual(chunks[0].page, 1)
        self.assertEqual(chunks[0].source, "test.pdf")
        self.assertEqual(len(warnings), 1)

    def test_bad_and_encrypted_pdf(self):
        with self.assertRaises(ValueError):
            extract_pdf("bad.pdf", b"not pdf")
        doc = pymupdf.open()
        doc.new_page()
        data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
        doc.close()
        with self.assertRaisesRegex(ValueError, "加密"):
            extract_pdf("locked.pdf", data)


if __name__ == "__main__":
    unittest.main()
