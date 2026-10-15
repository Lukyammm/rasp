import unittest
from scrapers.common import ScrapeContext


class TestStrictMatching(unittest.TestCase):
    def test_quoted_phrase_rejects_fuzzy_matches(self):
        ctx = ScrapeContext(network="tiktok", keyword='"EBM Quintto"', limit=10)
        
        # Casos que NÃO devem entrar (os que estavam poluindo)
        self.assertFalse(ctx.add_post(
            key="1",
            author="@basequintefox",
            text="#resultat #quinte #pmu",
            link="https://www.tiktok.com/@basequintefox/video/1",
            date=None,
        ))
        
        self.assertFalse(ctx.add_post(
            key="2",
            author="@quint.pronos",
            text="#maroc #france",
            link="https://www.tiktok.com/@quint.pronos/video/2",
            date=None,
        ))

        self.assertFalse(ctx.add_post(
            key="3",
            author="@egb.quintino",
            text="Rua Nerval de Gouveia, 03 Quintino",
            link="https://www.tiktok.com/@egb.quintino/video/3",
            date=None,
        ))

        self.assertFalse(ctx.add_post(
            key="4",
            author="@anya_nguyen",
            text="Hoje é dia de comemorar a quinta",
            link="https://www.tiktok.com/@anya_nguyen/video/4",
            date=None,
        ))

        # Casos que DEVEM entrar
        self.assertTrue(ctx.add_post(
            key="5",
            author="@joao_silva",
            text="Muito orgulho de fazer parte da EBM Quintto!",
            link="https://www.tiktok.com/@joao_silva/video/5",
            date=None,
        ))

        self.assertTrue(ctx.add_post(
            key="6",
            author="@ebmquintto",
            text="Confira os bastidores do nosso novo projeto na EBM Quintto.",
            link="https://www.tiktok.com/@ebmquintto/video/6",
            date=None,
        ))

        # Total coletado deve ser exatamente 2
        self.assertEqual(len(ctx.results), 2)

    def test_render_variant_quote_phrases(self):
        ctx = ScrapeContext(network="tiktok", keyword='"EBM Quintto"', limit=10)
        variants = ctx.search_variants()
        rendered_with_quotes = [ctx.render_variant(v, quote_phrases=True) for v in variants]
        self.assertEqual(rendered_with_quotes, ['"EBM Quintto"'])

    def test_quoted_name_strict_boundaries(self):
        ctx = ScrapeContext(network="tiktok", keyword='"Lukyam"', limit=10)

        # Deve rejeitar posts completamente sem relação (como os que o algoritmo do TikTok sugeria)
        self.assertFalse(ctx.add_post(
            key="101",
            author="@katara._.water._.atla",
            text="#avatar KKKKKKK #avatarthelastairbender #fyy",
            link="https://www.tiktok.com/@katara/video/101",
            date=None,
        ))
        self.assertFalse(ctx.add_post(
            key="102",
            author="@previasmidia7",
            text="MC Luuky representa uma geração de artistas...",
            link="https://www.tiktok.com/@previasmidia7/video/102",
            date=None,
        ))
        self.assertFalse(ctx.add_post(
            key="103",
            author="@lukaim",
            text="qual o seu tipo de risada? #lukaim",
            link="https://www.tiktok.com/@lukaim/video/103",
            date=None,
        ))

        # Deve aceitar arrobas derivadas, numéricas e menções diretas a Lukyam
        self.assertTrue(ctx.add_post(
            key="104",
            author="@lukyam72",
            text="Novo conteúdo saindo!",
            link="https://www.tiktok.com/@lukyam72/video/104",
            date=None,
        ))
        self.assertTrue(ctx.add_post(
            key="105",
            author="@lukyam272",
            text="Show de dublagem!",
            link="https://www.tiktok.com/@lukyam272/video/105",
            date=None,
        ))
        self.assertTrue(ctx.add_post(
            key="106",
            author="@lukyam.madeira",
            text="A única estrela vermelha que amo. #ovisitanteespacial",
            link="https://www.tiktok.com/@lukyam.madeira/video/106",
            date=None,
        ))
        self.assertTrue(ctx.add_post(
            key="107",
            author="@leitor_fiel",
            text="Terminei de ler o livro do Lukyam, sensacional!",
            link="https://www.tiktok.com/@leitor_fiel/video/107",
            date=None,
        ))

        self.assertEqual(len(ctx.results), 4)

    def test_single_quoted_words_are_sent_without_quotes(self):
        # '"Ciro"' com aspas literais zerava a busca do Instagram
        ctx = ScrapeContext(network="instagram", keyword='"Debate" AND "Ciro" AND "Elmano"', limit=10)
        rendered = [ctx.render_variant(v, quote_phrases=True) for v in ctx.search_variants()]
        self.assertEqual(rendered, ["Debate Ciro Elmano"])
        mixed = ScrapeContext(network="instagram", keyword='"Ciro Gomes" AND debate', limit=10)
        self.assertEqual([mixed.render_variant(v, quote_phrases=True) for v in mixed.search_variants()],
                         ['"Ciro Gomes" debate'])

    def test_rejected_post_is_reevaluated_with_more_text(self):
        ctx = ScrapeContext(network="x", keyword="debate AND ciro", limit=10)
        # 1ª leitura (DOM) sem o tweet citado: não bate com a busca
        self.assertFalse(ctx.add_post(key="1", author="@a", text="assistindo o debate", link="l", date=None))
        self.assertFalse(ctx.add_post(key="1", author="@a", text="assistindo o debate", link="l", date=None))
        # 2ª leitura (GraphQL) inclui o tweet citado: agora entra
        self.assertTrue(ctx.add_post(key="1", author="@a", text="assistindo o debate", link="l", date=None,
                                     match_text="assistindo o debate Ciro falou"))
        # e não entra duas vezes
        self.assertFalse(ctx.add_post(key="1", author="@a", text="assistindo o debate", link="l", date=None,
                                      match_text="assistindo o debate Ciro falou"))
        self.assertEqual(len(ctx.results), 1)


class TestNetworkLock(unittest.TestCase):
    def test_waits_for_other_extraction_and_gives_up_on_cancel(self):
        import threading
        from scrapers.browser import network_lock

        cancel = threading.Event()
        with network_lock("youtube") as first:
            self.assertTrue(first)
            cancel.set()
            with network_lock("youtube", cancel) as second:
                self.assertFalse(second)  # rede ocupada e extração cancelada: desiste sem erro
        with network_lock("youtube") as again:
            self.assertTrue(again)  # liberada ao sair


if __name__ == "__main__":
    unittest.main()

