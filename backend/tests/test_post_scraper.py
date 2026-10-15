import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.post_scraper import detect_network_from_url, extract_instagram_single_post, extract_tiktok_single_post, extract_youtube_single_post


class FakePage:
    def __init__(self, evaluate_return=None):
        self.evaluate_return = evaluate_return
        self.url = ""

    def goto(self, url, **kwargs):
        self.url = url

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, script, *args):
        if callable(self.evaluate_return):
            return self.evaluate_return(script, *args)
        return self.evaluate_return


class PostScraperTests(unittest.TestCase):
    def test_detect_network(self):
        self.assertEqual(detect_network_from_url("https://www.instagram.com/p/DF123/"), "instagram")
        self.assertEqual(detect_network_from_url("https://instagram.com/reel/XYZ/"), "instagram")
        self.assertEqual(detect_network_from_url("https://www.tiktok.com/@user/video/12345"), "tiktok")
        self.assertEqual(detect_network_from_url("https://x.com/user/status/987654321"), "x")
        self.assertEqual(detect_network_from_url("https://twitter.com/user/status/987654321"), "x")
        self.assertEqual(detect_network_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "youtube")
        self.assertEqual(detect_network_from_url("https://youtu.be/dQw4w9WgXcQ"), "youtube")
        self.assertEqual(detect_network_from_url("https://www.facebook.com/watch/?v=123"), "facebook")
        self.assertIsNone(detect_network_from_url("https://google.com"))

    def test_extract_instagram_mock(self):
        page = FakePage(evaluate_return={
            "ogTitle": "Instagram post by @lukyam",
            "ogDesc": "1.200 curtidas, 45 comentários - @lukyam no Instagram: 'Legenda incrível'",
            "author": "lukyam",
            "text": "Legenda incrível"
        })
        res = extract_instagram_single_post(page, "https://www.instagram.com/p/DF12345abc/")
        self.assertEqual(res["Rede"], "Instagram")
        self.assertEqual(res["Autor"], "@lukyam")
        self.assertEqual(res["Texto"], "Legenda incrível")
        self.assertEqual(res["Curtidas"], 1200)
        self.assertEqual(res["Comentarios"], 45)

    def test_extract_tiktok_mock(self):
        page = FakePage(evaluate_return={
            "found": True,
            "id": "12345",
            "author": "lukyam_oficial",
            "text": "Vídeo no TikTok",
            "likes": 5000,
            "comments": 250,
            "views": 80000,
            "shares": 120,
            "createTime": 1700000000
        })
        res = extract_tiktok_single_post(page, "https://www.tiktok.com/@lukyam_oficial/video/12345")
        self.assertEqual(res["Rede"], "TikTok")
        self.assertEqual(res["Autor"], "@lukyam_oficial")
        self.assertEqual(res["Curtidas"], 5000)
        self.assertEqual(res["Views"], 80000)

    def test_extract_youtube_mock(self):
        page = FakePage(evaluate_return={
            "title": "Vídeo Incrível de BI",
            "author": "EBM Quintto",
            "views": 15000,
            "desc": "Descrição do vídeo",
            "likes": "1,5 mil",
            "dateVal": "2026-09-10"
        })
        res = extract_youtube_single_post(page, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(res["Rede"], "YouTube")
        self.assertEqual(res["Autor"], "@EBM_Quintto")
        self.assertEqual(res["Texto"], "Vídeo Incrível de BI")
        self.assertEqual(res["Curtidas"], 1500)
        self.assertEqual(res["Views"], 15000)


if __name__ == "__main__":
    unittest.main()
