#!/usr/bin/env python3
"""Offline tests for the reference library builder. Run: python3 tests/test_refs.py

No network is used: the Crossref fixture is a trimmed real record, so the citation writers and the
verification matcher are tested without spending API calls.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("refs", SKILL_DIR / "scripts" / "refs.py")
refs = importlib.util.module_from_spec(spec)
sys.modules["refs"] = refs
spec.loader.exec_module(refs)

CROSSREF_RECORD = {
    "message": {
        "DOI": "10.1038/nature12373",
        "title": ["Crystal structure of rhodopsin bound to arrestin"],
        "container-title": ["Nature"],
        "publisher": "Springer Science and Business Media LLC",
        "author": [
            {"family": "Kang", "given": "Yanyong"},
            {"family": "Zhou", "given": "X. Edward"},
            {"family": "Gao", "given": "Xiang"},
        ],
        "published-print": {"date-parts": [[2015, 7, 30]]},
        "volume": "523",
        "issue": "7562",
        "page": "561-567",
        "type": "journal-article",
        "URL": "https://doi.org/10.1038/nature12373",
    }
}


class TextUtilsTest(unittest.TestCase):
    def test_normalise_doi_strips_prefixes_and_case(self) -> None:
        for raw in ("https://doi.org/10.1038/Nature12373", "doi:10.1038/nature12373.",
                    "  10.1038/nature12373  "):
            self.assertEqual(refs.normalise_doi(raw), "10.1038/nature12373")

    def test_extract_dois_deduplicates(self) -> None:
        text = ("see 10.1038/nature12373 and https://doi.org/10.1126/science.1225829 "
                "and again 10.1038/nature12373")
        self.assertEqual(
            refs.extract_dois(text),
            ["10.1038/nature12373", "10.1126/science.1225829"],
        )

    def test_slugify_drops_punctuation_and_caps(self) -> None:
        self.assertEqual(
            refs.slugify("Wood-based Moisture Electricity!"), "wood-based-moisture-electricity"
        )

    def test_slugify_cuts_at_a_word_boundary(self) -> None:
        slug = refs.slugify("Wood-based moisture electricity generation device", 20)
        self.assertEqual(slug, "wood-based-moisture")
        self.assertLessEqual(len(slug), 20)

    def test_slugify_falls_back_when_nothing_ascii(self) -> None:
        self.assertEqual(refs.slugify("水伏发电"), "reference")


class MetadataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.meta = refs.parse_crossref(CROSSREF_RECORD)

    def test_parses_core_fields(self) -> None:
        self.assertEqual(self.meta["doi"], "10.1038/nature12373")
        self.assertEqual(self.meta["year"], 2015)
        self.assertEqual(self.meta["volume"], "523")
        self.assertEqual(self.meta["page"], "561-567")
        self.assertEqual(self.meta["container"], "Nature")
        self.assertEqual(len(self.meta["authors"]), 3)

    def test_key_is_stable_and_readable(self) -> None:
        key = refs.key_for(self.meta)
        self.assertTrue(key.startswith("kang-2015-"))
        self.assertEqual(key, refs.key_for(self.meta))
        self.assertNotIn(" ", key)

    def test_first_author_falls_back(self) -> None:
        empty = {"authors": []}
        self.assertEqual(refs.first_author_family(empty), "unknown")


class CitationWriterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.meta = refs.parse_crossref(CROSSREF_RECORD)
        self.key = refs.key_for(self.meta)

    def test_ris_shape(self) -> None:
        ris = refs.to_ris(self.meta)
        self.assertTrue(ris.startswith("TY  - JOUR\n"))
        self.assertIn("AU  - Kang, Yanyong\n", ris)
        self.assertIn("TI  - Crystal structure of rhodopsin bound to arrestin\n", ris)
        self.assertIn("PY  - 2015\n", ris)
        self.assertIn("SP  - 561\n", ris)
        self.assertIn("EP  - 567\n", ris)
        self.assertIn("DO  - 10.1038/nature12373\n", ris)
        self.assertTrue(ris.rstrip().endswith("ER  -"))

    def test_enw_shape(self) -> None:
        enw = refs.to_enw(self.meta)
        self.assertTrue(enw.startswith("%0 Journal Article\n"))
        self.assertIn("%A Kang, Yanyong\n", enw)
        self.assertIn("%J Nature\n", enw)
        self.assertIn("%D 2015\n", enw)
        self.assertIn("%P 561-567\n", enw)
        self.assertIn("%R 10.1038/nature12373\n", enw)

    def test_bibtex_shape(self) -> None:
        bib = refs.to_bibtex(self.meta, self.key)
        self.assertTrue(bib.startswith(f"@article{{{self.key},\n"))
        self.assertIn("author = {Kang, Yanyong and Zhou, X. Edward and Gao, Xiang}", bib)
        self.assertIn("pages = {561--567}", bib)
        self.assertIn("doi = {10.1038/nature12373}", bib)
        self.assertTrue(bib.rstrip().endswith("}"))

    def test_preprint_is_not_written_as_a_journal_article(self) -> None:
        meta = dict(self.meta, type="posted-content")
        self.assertEqual(refs.to_ris(meta).splitlines()[0], "TY  - UNPB")
        self.assertEqual(refs.to_enw(meta).splitlines()[0], "%0 Preprint")

    def test_missing_fields_are_omitted_not_invented(self) -> None:
        sparse = {
            "doi": "10.1000/x", "title": "A short note", "authors": [],
            "type": "journal-article", "year": None, "container": "", "volume": "",
            "issue": "", "page": "", "article_number": "", "url": "https://doi.org/10.1000/x",
            "publisher": "", "subtitle": "",
        }
        ris = refs.to_ris(sparse)
        self.assertNotIn("VL  -", ris)
        self.assertNotIn("PY  -", ris)
        self.assertIn("ER  -", ris)


class MatchTest(unittest.TestCase):
    TITLE = "Crystal structure of rhodopsin bound to arrestin"

    def test_doi_presence_is_enough(self) -> None:
        self.assertTrue(
            refs.matches_reference("Front matter ... doi:10.1038/NATURE12373 ...", 
                                   "10.1038/nature12373", self.TITLE)
        )

    def test_title_words_carry_a_pdf_without_a_doi(self) -> None:
        text = ("Crystal structure of rhodopsin bound to arrestin reveals the "
                "interface between the two proteins.")
        self.assertTrue(refs.matches_reference(text, "10.1038/nature12373", self.TITLE))

    def test_unrelated_pdf_is_rejected(self) -> None:
        text = "Deep learning for weather prediction over the Indian subcontinent"
        self.assertFalse(refs.matches_reference(text, "10.1038/nature12373", self.TITLE))

    def test_empty_text_is_rejected(self) -> None:
        self.assertFalse(refs.matches_reference("", "10.1038/nature12373", self.TITLE))


class IndexTest(unittest.TestCase):
    def test_index_files_are_written(self) -> None:
        import tempfile

        meta = refs.parse_crossref(CROSSREF_RECORD)
        key = refs.key_for(meta)
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            refs.write_citation_files(meta, key, outdir, ["ris", "enw", "bib"])
            refs.write_combined(outdir, [meta], ["ris", "bib"])
            refs.write_index(outdir, [{
                "key": key, "doi": meta["doi"], "year": meta["year"],
                "first_author": "Kang", "title": meta["title"], "journal": "Nature",
                "oa_status": "manual", "pdf": "", "verified": "n/a",
            }])
            for name in ("cite/" + key + ".ris", "cite/" + key + ".enw",
                         "cite/" + key + ".bib", "library.ris", "library.bib",
                         "index.csv", "index.md"):
                self.assertTrue((outdir / name).exists(), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
