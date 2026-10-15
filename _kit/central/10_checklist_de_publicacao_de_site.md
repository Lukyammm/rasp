# Checklist de publicação de site

Verbete da central Dominação IA, seção "Publicar sem se queimar" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Seis posts, três momentos: preparar o domínio, conferir antes de publicar e o que fazer depois que o site está no ar. A união cobre técnica, conteúdo, prova social e dados legais. Um dos posts entrega a conferência como um prompt único para mandar ao modelo.

*6 fontes · confiança alta*

**Ao comprar o domínio**

- Registrar o domínio no seu nome
- Revisar as configurações de segurança do domínio
- Pôr o app num subdomínio (app.seudominio.com) com um registro CNAME e deixar o domínio principal para as páginas de marketing
- Configurar e-mail do próprio domínio
- Criar dois subdomínios de e-mail, um para os e-mails do app (cadastro, cobrança, senha) e outro para marketing (newsletter, campanhas)
- Configurar SPF, DKIM e DMARC nos subdomínios de e-mail

**Antes: técnico**

- Abrir o site num celular de verdade, não só no simulador
- Rodar o PageSpeed no modo celular
- Comprimir todas as imagens
- Servir HTTPS numa URL só, sem duplicar www e não-www
- Usar hospedagem de qualidade
- Conferir que o robots.txt não está bloqueando a produção
- Colocar favicon e imagem de compartilhamento
- Ter página 404 própria
- Remover overflow horizontal e corrigir o mobile

**Antes: conteúdo e conversão**

- Definir a ação principal do site
- Criar uma página por serviço
- Escrever título e descrição próprios em cada página
- Escrever meta descriptions
- Usar foto real da equipe, nada de banco de imagem genérico
- Ter página "sobre" com gente real
- Reunir pelo menos 3 depoimentos reais
- Testar o formulário de contato
- Clicar no link do WhatsApp e em todos os links
- Botão de WhatsApp flutuante
- Revisar textos e contatos

**Antes: legal e dados**

- Publicar política de privacidade e de cookies
- Deixar CNPJ, endereço e contato visíveis no rodapé

**Depois do ar**

- Cadastrar no Google Search Console e enviar o sitemap.xml
- Instalar o Google Analytics e configurar medição de eventos
- Criar o perfil no Google Meu Negócio
- Criar os arquivos llms.txt e robots.txt
- Usar a palavra-chave do negócio
- Acompanhar o tráfego

**Medir depois que subiu**

- O Lighthouse, do nó 164, roda dentro do DevTools do Chrome e devolve nota de performance, acessibilidade e SEO da página, apontando asset pesado e script que trava o carregamento

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| Google Search Console | Cadastrar o site e enviar o sitemap | nó 3, nó 20, nó 75, nó 116 |
| Google Analytics | Acompanhar tráfego e eventos | nó 3, nó 20 |
| Google Meu Negócio | Perfil do negócio | nó 3, nó 75 |
| PageSpeed Insights | Medir velocidade no modo celular | nó 20 |
| Resend | E-mails do app: adicionar os subdomínios e configurar SPF, DKIM e DMARC | nó 116 |

**Prompts e comandos**

Pronto (nó 23):

```text
Remova a rolagem horizontal, encontre links quebrados, adicione o menu mobile, adicione um favicon, corrija os títulos da página, adicione meta descrições, corrija os links do rodapé, adicione uma página 404 personalizada, corrija o ano do copyright, comprima as imagens, corrija botões quebrados, adicione mensagens de sucesso e remova mensagens de erro, remova textos de placeholder, remova a navegação não utilizada, corrija o overflow no mobile, torne o logo clicável, torne o número do WhatsApp clicável, torne o e-mail clicável e deixe todas as páginas otimizadas para o mobile.
```

**Fontes**

- [nó 3](https://www.instagram.com/reel/Db6gJljsXaQ/) @mxcdigital.co: 10 tarefas depois de publicar um site (Search Console, llms.txt, sitemap)
- [nó 20](https://www.instagram.com/reel/DcSZN_WuI__/) @mxcdigital.co: 20 verificações antes de publicar um site
- [nó 23](https://www.instagram.com/reel/Dc6WO6jRTCK/) @gestordeaudiencia: Megaprompt para o Claude arrumar um site
- [nó 75](https://www.instagram.com/reel/DdK_DCYMg2F/) @mxcdigital.co: 20 itens antes de publicar um site de empresa
- [nó 116](https://www.instagram.com/reel/DaSpPVGsu-o/) @buildwithnico: 3 passos depois de comprar o domínio do app: subdomínio, e-mail e sitemap
- [nó 164](https://www.instagram.com/reel/DczvUteRsGJ/) @aj.on.ai: Cinco ferramentas para o que costuma quebrar no projeto com IA

**Observações.** Três dos seis posts são da mesma agência e terminam oferecendo o serviço dela. Isso não invalida o checklist, mas explica a insistência. O nó 75 anuncia 20 itens e a fala lista 19 verificáveis. O nó 116 explica o motivo da divisão: com o app num subdomínio, o time de design mexe na home sem entrar no código; com o e-mail em subdomínios próprios, uma marcação de spam não suja o domínio principal. A legenda diz que o Resend recomenda essa divisão, o que não foi conferido.

**O que não tem aqui.** Nada sobre teste de acessibilidade na prática, sobre performance além do PageSpeed, nem sobre o que fazer quando o site já está no ar e não converte.
