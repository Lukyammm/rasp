# Checklist de segurança antes de lançar

Verbete da central Dominação IA, seção "Publicar sem se queimar" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Três dos quatro posts cobrem o mesmo terreno com sobreposição grande, e a união deles é mais completa que qualquer um sozinho. A tese comum, dita no nó 11: a IA constrói, mas a segurança é de quem orquestra.

*4 fontes · confiança alta*

**Segredos e credenciais**

- Esconder as API keys
- Limpar os secrets do histórico do git
- Conferir as variáveis de ambiente
- Trocar para chave pública no banco

**Acesso e autenticação**

- Proteger as rotas de API com autenticação
- Fazer autenticação no servidor, não no cliente
- Proteger as rotas de admin
- Conferir as permissões de usuário
- Travar o acesso aos registros por usuário
- Ativar RLS nas tabelas
- Conferir as regras do banco

**Dados e senhas**

- Usar hash nas senhas
- Criptografar dados sensíveis
- Salvar os dados do usuário de forma criptografada

**Entrada do usuário**

- Validar as entradas
- Sanitizar a entrada do usuário
- Usar queries parametrizadas
- Proteger contra SQL injection
- Proteger contra XSS
- Escapar conteúdo enviado pelo usuário
- Bloquear mass assignment
- Restringir e tornar seguro o upload de arquivos

**Abuso e custo**

- Aplicar rate limit no login
- Adicionar proteção contra bots
- Definir um teto de gastos (spend cap)

**Transporte e configuração**

- Forçar HTTPS
- Adicionar security headers
- Proteger os cookies de sessão
- Adicionar proteção CSRF
- Revisar a configuração de CORS
- Enxugar as respostas de API
- Desligar o modo debug
- Revisar as configurações de produção
- Rodar scan de dependências

**Automatizar a checagem**

- A skill never-get-hacked, do nó 164, é a primeira coisa do acervo que aplica esta lista sozinha: instalada no agente de código, ela marca SQL injection, XSS, dependência insegura e credencial exposta antes de o código ir para produção
- Continua sendo pedido, não auditoria: nenhum post mostra a skill rodando nem o que ela deixa passar

**Fontes**

- [nó 11](https://www.instagram.com/reel/Dcb6kZHJLFV/) @geraldo.alv3s: Segurança em sistemas feitos com IA: autenticação, criptografia, rate limit e RLS
- [nó 15](https://www.instagram.com/reel/DcZw8Gdxfsn/) @_daniellcruz: 20 itens de segurança para pedir ao Claude antes de lançar um app
- [nó 87](https://www.instagram.com/reel/DcNc-EszHJF/) @yatesvids: 20 verificações de segurança para pedir ao Claude
- [nó 164](https://www.instagram.com/reel/DczvUteRsGJ/) @aj.on.ai: Cinco ferramentas para o que costuma quebrar no projeto com IA

**Observações.** Os nós 15 e 87 são checklists de 20 itens com grande sobreposição; o 87 acrescenta teto de gastos, CORS e modo debug. O nó 11 é o mais curto mas o único que argumenta o porquê. Os três são para "pedir ao Claude": nenhum ensina a implementar, só a cobrar.

**O que não tem aqui.** Nenhum post mostra como verificar se o item foi de fato implementado. A lista é de pedido, não de auditoria.
