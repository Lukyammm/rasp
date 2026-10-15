import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from database import get_db, ScrapedPost, PostComment
from utils import parse_numeric_metric

db = next(get_db())
posts = db.query(ScrapedPost).filter(ScrapedPost.run_id == 'run_1790012130_164f').all()
comments = db.query(PostComment).filter(PostComment.run_id == 'run_1790012130_164f').all()

total_posts = len(posts)
total_comments = len(comments)

total_likes = sum(parse_numeric_metric(p.likes) for p in posts)
total_views = sum(parse_numeric_metric(p.views) for p in posts)
metric_comments_sum = sum(parse_numeric_metric(p.comments) for p in posts)
total_interactions = total_likes + metric_comments_sum

print(f"Total Posts: {total_posts}")
print(f"Total Comentários Coletados (Banco): {total_comments:,}")
print(f"Total Curtidas (Métrica Posts): {total_likes:,}")
print(f"Total Visualizações (Métrica Posts): {total_views:,}")
print(f"Total Comentários (Métrica Posts): {metric_comments_sum:,}")
print(f"Total Interações (Curtidas + Comentários): {total_interactions:,}")

# Detalhe por rede
from collections import defaultdict
net_p = defaultdict(int)
net_c = defaultdict(int)
net_l = defaultdict(int)
net_v = defaultdict(int)

for p in posts:
    net = p.network.upper()
    if "INSTAGRAM" in net: k = "Instagram"
    elif "TIKTOK" in net: k = "TikTok"
    elif "YOUTUBE" in net: k = "YouTube"
    elif "X" in net or "TWITTER" in net: k = "X"
    else: k = net
    net_p[k] += 1
    net_l[k] += parse_numeric_metric(p.likes)
    net_v[k] += parse_numeric_metric(p.views)

for c in comments:
    net = c.network.lower()
    if "instagram" in net: k = "Instagram"
    elif "tiktok" in net: k = "TikTok"
    elif "youtube" in net: k = "YouTube"
    elif "x" in net or "twitter" in net: k = "X"
    else: k = net
    net_c[k] += 1

print("\n--- POR REDE ---")
for k in ["Instagram", "TikTok", "YouTube", "X"]:
    print(f"{k}: {net_p[k]} posts | {net_c[k]:,} comentários coletados | {net_l[k]:,} likes | {net_v[k]:,} views")

# Buscar comentários sobre governo e elmano
gov_terms = ['elmano', 'governo', 'governador', 'pefoce', 'iml', 'pericia', 'perícia', 'policia', 'polícia', 'segurança pública', 'seguranca publica', 'secretaria de seguranca', 'sspds']
elmano_terms = ['elmano', 'governador']
pefoce_terms = ['pefoce', 'iml', 'pericia', 'perícia']
policia_terms = ['policia', 'polícia', 'delegado', 'delegacia']

gov_comments = []
elmano_comments = []
pefoce_comments = []
policia_comments = []

for c in comments:
    t = (c.text or '').lower()
    if any(k in t for k in gov_terms):
        gov_comments.append(c)
    if any(k in t for k in elmano_terms):
        elmano_comments.append(c)
    if any(k in t for k in pefoce_terms):
        pefoce_comments.append(c)
    if any(k in t for k in policia_terms):
        policia_comments.append(c)

print(f"\nTotal menções a Governo/Elmano/Pefoce/IML/Polícia: {len(gov_comments)} ({len(gov_comments)/total_comments*100:.2f}%)")
print(f" - Menções nominais a Elmano / Governador: {len(elmano_comments)}")
print(f" - Menções a Pefoce / IML / Perícia: {len(pefoce_comments)}")
print(f" - Menções a Polícia / Delegado: {len(policia_comments)}")

gov_comments.sort(key=lambda x: x.likes, reverse=True)
print("\nTop 15 comentários sobre Governo/Autoridades por curtidas:")
for i, gc in enumerate(gov_comments[:15], 1):
    print(f"#{i} [{gc.network.upper()}] {gc.author} ({gc.likes} likes, {gc.replies} replies):")
    print(f"   \"{gc.text}\"")

# Analise tematica geral
clusters = {
    "justica": 0,
    "apoio_mae": 0,
    "especulacao": 0,
    "pesar_fe": 0,
    "institucional": 0
}

for c in comments:
    txt = (c.text or "").lower()
    is_gov = any(k in txt for k in gov_terms)
    
    if any(w in txt for w in ["justiça", "justica", "preso", "prisão", "prisao", "cadeia", "assassino", "monstro", "pagar", "covarde"]):
        clusters["justica"] += 1
    elif any(w in txt for w in ["mãe", "mae", "isorlanda", "força", "forca", "deus conforte", "senhora", "coração", "coracao", "dor"]):
        clusters["apoio_mae"] += 1
    elif is_gov:
        clusters["institucional"] += 1
    elif any(w in txt for w in ["morte", "veneno", "estrangulamento", "namorado", "versão", "versao", "mentira", "laudo", "sangue"]):
        clusters["especulacao"] += 1
    else:
        clusters["pesar_fe"] += 1

tot = sum(clusters.values())
print("\n--- MATRIZ DE PERCEPÇÃO ---")
for k, v in clusters.items():
    print(f"{k}: {v:,} ({v/tot*100:.1f}%)")
