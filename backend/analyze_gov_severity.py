import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from database import get_db, PostComment

db = next(get_db())
comments = db.query(PostComment).filter(PostComment.run_id == 'run_1790012130_164f').all()

gov_terms = ['elmano', 'governo', 'governador', 'pefoce', 'iml', 'pericia', 'perícia', 'policia', 'polícia', 'segurança pública', 'seguranca publica', 'secretaria', 'sspds']
gov_comments = [c for c in comments if any(k in (c.text or '').lower() for k in gov_terms)]

print(f'Total de comentários institucionais: {len(gov_comments)}')

cobranca_elmano = []
acobertamento = []
falhas_procedimento = []

for c in gov_comments:
    t = (c.text or '').lower()
    if any(k in t for k in ['elmano', 'governador']):
        cobranca_elmano.append(c)
    if any(k in t for k in ['comprada', 'abafar', 'acobertar', 'influencia', 'influência', 'cargo', 'politico', 'político', 'corrup', 'propina']):
        acobertamento.append(c)
    if any(k in t for k in ['indigente', 'não avisou', 'nao avisou', 'câmera', 'camera', 'sumir', 'laudo', 'exumação', 'exumacao', 'processado', 'estranho']):
        falhas_procedimento.append(c)

print(f"Cobrança direta a Elmano/Governador: {len(cobranca_elmano)}")
print(f"Suspeitas de Acobertamento / Influência Política / Favorecimento: {len(acobertamento)}")
print(f"Questionamento de Falhas e Procedimentos (IML/Polícia/Câmeras/Laudo): {len(falhas_procedimento)}")

print("\n--- TOP COBRANÇAS A ELMANO/GOVERNADOR ---")
cobranca_elmano.sort(key=lambda x: x.likes or 0, reverse=True)
for c in cobranca_elmano[:10]:
    print(f"[{c.network.upper()}] @{c.author} ({c.likes} likes, {c.replies} replies):")
    print(f"   \"{c.text}\"\n")

print("\n--- TOP SUSPEITAS DE ACOBERTAMENTO / INFLUÊNCIA POLÍTICA ---")
acobertamento.sort(key=lambda x: x.likes or 0, reverse=True)
for c in acobertamento[:10]:
    print(f"[{c.network.upper()}] @{c.author} ({c.likes} likes, {c.replies} replies):")
    print(f"   \"{c.text}\"\n")

print("\n--- TOP FALHAS DE PROCEDIMENTO (IML/POLÍCIA/PERÍCIA) ---")
falhas_procedimento.sort(key=lambda x: x.likes or 0, reverse=True)
for c in falhas_procedimento[:10]:
    print(f"[{c.network.upper()}] @{c.author} ({c.likes} likes, {c.replies} replies):")
    print(f"   \"{c.text}\"\n")
