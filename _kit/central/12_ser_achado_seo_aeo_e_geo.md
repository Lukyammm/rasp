# Ser achado: SEO, AEO e GEO

Verbete da central Dominação IA, seção "Publicar sem se queimar" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

A tese que atravessa dois posts: site bonito não é site encontrável, e agora são duas audiências distintas: pessoas e modelos. Cada uma exige uma coisa diferente, e a IA que gera o site não pensa em nenhuma das duas.

*4 fontes · confiança alta*

**As três frentes**

- UX faz o visitante comprar
- SEO faz o Google encontrar
- AEO/GEO faz a IA recomendar sua empresa
- Tratar "ser entendido por IA" como requisito próprio, não como consequência do SEO

**O que a IA esquece quando gera o site**

- Sitemap.xml
- Robots.txt
- llms.txt
- Título e meta description por página
- Que o site vai sair da sua máquina e viver no mundo

**robots.txt, sitemap.xml e llms.txt**

- robots.txt fica na raiz e diz aos crawlers o que podem rastrear (Allow e Disallow): deixar tudo liberado, a não ser páginas abertas que você não queira indexadas
- O robots.txt aponta para o sitemap.xml, que também fica na raiz e lista todas as páginas: configurar os dois juntos
- llms.txt é um resumo do site para a IA: as páginas mais importantes, cada uma com uma linha de descrição, para o modelo não ler o HTML inteiro
- É fácil gerar o llms.txt com IA, mas ele ainda é novo e não garante ganho nas respostas
- Exemplos reais para copiar a estrutura: stripe.com/robots.txt e stripe.com/llms.txt

**Prompts e comandos**

Modelo mínimo de robots.txt (nó 105):

```text
User-agent: *
Disallow:

Sitemap: https://www.yourapp.com/sitemap.xml
```

**Fontes**

- [nó 3](https://www.instagram.com/reel/Db6gJljsXaQ/) @mxcdigital.co: 10 tarefas depois de publicar um site (Search Console, llms.txt, sitemap)
- [nó 60](https://www.instagram.com/reel/DbVqzH2J0Ez/) @jeanlucasdso: UX, SEO e AEO/GEO: sites para pessoas e para IAs
- [nó 77](https://www.instagram.com/reel/Dcr2SrUsXMh/) @mxcdigital.co: Por que não fazer um site 100% com IA (SEO, sitemap, llms.txt)
- [nó 105](https://www.instagram.com/reel/Da2ooN2ovZw/) @buildwithnico: robots.txt contra llms.txt: o que cada um faz e qual o app precisa

**Observações.** O nó 77 é conversa publicitária de agência e termina em oferta de serviço, mas o argumento técnico se sustenta sozinho. O nó 60 enuncia a distinção UX/SEO/AEO sem ensinar a implementar. O nó 105 é o único que mostra o conteúdo dos arquivos, com os da Stripe e do Notion na tela.

**O que não tem aqui.** Ainda grande: o llms.txt ganhou estrutura e exemplo real, mas nenhum post mostra outra prática de AEO/GEO além dele, e ninguém mede se a IA passou a recomendar o site. O próprio post sobre llms.txt avisa que ele não garante ganho.
