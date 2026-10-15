# Como tirar a cara de IA na prática

Verbete da central Dominação IA, seção "Construir com IA sem parecer que foi IA" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Quatro caminhos, do mais barato ao mais estrutural: partir de componentes prontos em vez de deixar a IA inventar a UI; buscar referência real antes de pedir; escanear o resultado atrás de antipadrões; e corrigir o texto, que denuncia tanto quanto o visual. Os quatro partem do mesmo princípio: o que denuncia o site é aceitar a primeira entrega.

*4 fontes · confiança alta*

**Componentes prontos**

- Escolher componentes no 21st.dev, copiar o prompt de cada um e colar no assistente especificando onde aplicar
- Ajustar os elementos depois com a biblioteca, em vez de aceitar o primeiro resultado

**Referência antes do pedido**

- No Pinterest, pesquisar o nicho seguido de "web design" e mandar a IA se basear nessas referências
- Usar Awwwards para referência de interação e scroll, não só de estética
- Buscar referência visual real em vez de descrever o estilo por escrito

**Diagnóstico do resultado**

- Escanear a página com o Impeccable e pedir correções específicas, em vez de mandar refazer tudo
- Antipadrões que a extensão marca: paleta típica de IA, texto de baixo contraste, texto em gradiente e cards aninhados

**O texto também entrega**

- Instalar a skill Humanizer, que reconhece e corrige vícios de linguagem de texto gerado por IA

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| 21st.dev | Biblioteca de componentes e animações com prompt pronto para copiar | nó 9, nó 36 |
| Pinterest | Referência por nicho: pesquisar "<nicho> web design" | nó 36 |
| Awwwards | Referência de interação em sites premiados | nó 36 |
| Impeccable | Extensão que escaneia a página e marca antipadrões de IA | nó 80 |
| Humanizer | Skill que corrige vícios de linguagem de texto de IA | nó 85 |

**Prompts e comandos**

Instalação (nó 85):

```text
npx skills add blader/humanizer --global
```

**Fontes**

- [nó 9](https://www.instagram.com/reel/DcO5WFkM3gn/) @eugustavofelicori: Componentes do 21st.dev no Claude Code para tirar a cara de vibe code
- [nó 36](https://www.instagram.com/reel/Da1VudJRtih/) @eugustavosextaro: 21st.dev, Pinterest e Awwwards para sites sem cara de IA
- [nó 80](https://www.instagram.com/reel/DdKjBN_NyYL/) @liss.json: Extensão Impeccable para encontrar antipadrões de IA em sites
- [nó 85](https://www.instagram.com/reel/DdHoaoWMPOK/) @eugustavofelicori: Skill Humanizer para textos sem cara de IA

**Observações.** Os valores de premiação do Awwwards citados no nó 36 ("15 a 20 mil dólares") são fala do autor, sem verificação.

**O que não tem aqui.** Nenhum post mostra o antes e depois medido: não há evidência de que o site corrigido converta melhor, só de que parece menos genérico.
