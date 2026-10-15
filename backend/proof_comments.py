import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from database import get_db, PostComment

db = next(get_db())
comments = db.query(PostComment).filter(PostComment.run_id == 'run_1790012130_164f').all()

search_terms = ['sara', 'cosap', 'penitenciária', 'penitenciaria', 'cargo', 'oab', 'indigente', 'abafar', 'elmano', 'influência', 'influencia']

found = []
for c in comments:
    txt = (c.text or '').lower()
    matches = [t for t in search_terms if t in txt]
    if len(matches) >= 2 or 'sara' in txt or 'cosap' in txt or 'penitenciaria' in txt or 'penitenciária' in txt:
        found.append(c)

print(f"Total de comentários encontrados com essas afirmações: {len(found)}")
found.sort(key=lambda x: x.likes or 0, reverse=True)

for i, c in enumerate(found[:15], 1):
    print(f"--- EVIDÊNCIA REAL #{i} ---")
    print(f"ID no Banco: {c.id} | Rede: {c.network.upper()} | Autor: {c.author} | Curtidas: {c.likes:,} | Respostas: {c.replies}")
    print(f"Texto Exato: \"{c.text}\"\n")
