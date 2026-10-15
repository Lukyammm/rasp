import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (  # noqa: E402
    BooleanQuery,
    build_report_filename,
    clean_author,
    decode_instagram_date,
    extract_atomic_terms,
    identify_matched_terms,
    parse_numeric_metric,
    parse_social_date,
)


class BooleanQueryTests(unittest.TestCase):
    def test_basic_operators(self):
        q = BooleanQuery("(tecnologia OR inovação) AND mercado NOT política")
        self.assertTrue(q.matches("O mercado de Tecnologia cresce"))
        self.assertTrue(q.matches("inovacao no MERCADO"))
        self.assertFalse(q.matches("tecnologia e mercado na politica"))
        self.assertFalse(q.matches("apenas tecnologia"))

    def test_implicit_and_and_phrases(self):
        q = BooleanQuery('"Ciro Gomes" debate')
        self.assertTrue(q.matches("Debate com Ciro   Gomes hoje"))
        self.assertFalse(q.matches("Ciro fala de Gomes no debate"))
        self.assertFalse(q.matches("Ciro Gomes na TV"))

    def test_prefix_boundary(self):
        q = BooleanQuery("debate")
        self.assertTrue(q.matches("#debates de ontem"))
        self.assertFalse(q.matches("o embate foi duro"))

    def test_minus_exclusion_and_leniency(self):
        self.assertFalse(BooleanQuery("ciro -elmano").matches("ciro e elmano"))
        self.assertTrue(BooleanQuery("(ciro OR elmano").matches("elmano"))
        self.assertTrue(BooleanQuery("ciro AND").matches("ciro"))
        self.assertTrue(BooleanQuery("").matches("qualquer coisa"))

    def test_no_code_execution(self):
        q = BooleanQuery('__import__("os").system("echo hacked")')
        self.assertFalse(q.matches("texto normal"))

    def test_terms_and_x_query(self):
        q = BooleanQuery('("Cid Gomes" OR Elmano) AND debate NOT pesquisa')
        self.assertEqual(q.positive_terms(), ["Cid Gomes", "Elmano", "debate"])
        self.assertEqual(q.negative_terms(), ["pesquisa"])
        self.assertEqual(q.to_x_query(), '("Cid Gomes" OR Elmano) debate -pesquisa')
        self.assertEqual(BooleanQuery("a NOT (b OR c)").to_x_query(), "a -b -c")
        self.assertTrue(q.has_excluded_term("nova Pesquisa divulgada"))

    def test_atomic_terms(self):
        self.assertEqual(extract_atomic_terms('"Luizianne Lins" OR "Cid Gomes"'), ["Luizianne Lins", "Cid Gomes"])
        self.assertEqual(extract_atomic_terms("mercado NOT politica"), ["mercado"])
        self.assertEqual(extract_atomic_terms("ciro, fulano"), ["ciro", "fulano"])
        self.assertEqual(identify_matched_terms(["Cid Gomes", "Elmano"], "Elmano venceu"), "Elmano")
        self.assertEqual(identify_matched_terms(["Cid", "Elmano"], "nada"), "Geral")


class MetricTests(unittest.TestCase):
    def test_values(self):
        cases = {
            "1.500": 1500, "25.000": 25000, "1.234.567": 1234567, "1,5 mil": 1500, "1.5k": 1500,
            "2,3 mi": 2300000, "39K": 39000, "1 bi": 1_000_000_000, "1.234 curtidas": 1234,
            "12 comentários": 12, "N/A": 0, None: 0, "": 0, "3968884816895897016": 0, 17477: 17477,
            "5 minutos": 5, "1,2 mi de visualizações": 1200000, "2.345,6": 2345,
        }
        for raw, expected in cases.items():
            self.assertEqual(parse_numeric_metric(raw), expected, raw)


class DateTests(unittest.TestCase):
    NOW = datetime(2026, 9, 12, 18, 0, 0)

    def check(self, raw, expected):
        self.assertEqual(parse_social_date(raw, now=self.NOW), expected, raw)

    def test_relative(self):
        self.check("há 1 mês", datetime(2026, 8, 13, 18, 0, 0))
        self.check("1 day ago", datetime(2026, 9, 11, 18, 0, 0))
        self.check("3 days ago", datetime(2026, 9, 9, 18, 0, 0))
        self.check("2h", datetime(2026, 9, 12, 16, 0, 0))
        self.check("há 2 anos", datetime(2024, 9, 12, 18, 0, 0))
        self.check("Transmitido há 3 semanas", datetime(2026, 8, 22, 18, 0, 0))
        self.check("15 min", datetime(2026, 9, 12, 17, 45, 0))
        self.check("ontem", datetime(2026, 9, 11, 18, 0, 0))

    def test_absolute(self):
        self.check("2026-08-01", datetime(2026, 8, 1))
        self.check("2026-09-08 19:20:46", datetime(2026, 9, 8, 19, 20, 46))
        self.check("08/09/2026", datetime(2026, 9, 8))
        self.check("8 de set. de 2025", datetime(2025, 9, 8))
        self.check("Sep 8", datetime(2026, 9, 8))
        self.check("9-8", datetime(2026, 9, 8))
        self.assertIsNone(parse_social_date("sem data", now=self.NOW))

    def test_instagram_shortcode(self):
        self.assertTrue(decode_instagram_date("https://www.instagram.com/p/DcUT7aBhW24/").startswith("2026-08"))


class FilenameTests(unittest.TestCase):
    WHEN = datetime(2026, 9, 12, 20, 7)

    def test_names(self):
        self.assertEqual(build_report_filename(['"Debate" AND "Ciro" AND "Elmano"'], "xlsx", self.WHEN),
                         "RASP_Debate-Ciro-Elmano_2026-09-12_20h07.xlsx")
        self.assertEqual(build_report_filename(["Netflix"], "xlsx", self.WHEN, search_type="profile"),
                         "RASP_Perfil_Netflix_2026-09-12_20h07.xlsx")
        self.assertEqual(build_report_filename(["mercado NOT política", "Ceará"], "pdf", self.WHEN, origin="agendamento"),
                         "RASP_Agendado_mercado-Ceara_2026-09-12_20h07.pdf")
        long_name = build_report_filename(["Ciro OR Elmano OR Camilo OR Wagner OR Cid OR Evandro OR Roberto"], "xlsx", self.WHEN)
        self.assertLessEqual(len(long_name.split("_")[1]), 40)
        self.assertEqual(build_report_filename(["???"], "xlsx", self.WHEN), "RASP_Extracao_2026-09-12_20h07.xlsx")


class AuthorTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(clean_author("@Wagner Mendes | @reportermendes | · | Sep 8"), "@reportermendes")
        self.assertEqual(clean_author("opovo"), "@opovo")
        self.assertEqual(clean_author(""), "")


if __name__ == "__main__":
    unittest.main()
