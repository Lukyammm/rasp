"""
Extração dos termos mais frequentes para a nuvem de palavras.
"""
import re
from collections import Counter

_PLACEHOLDER_TEXTS = {"[postagem com mídia / sem texto]", "vídeo tiktok"}

STOPWORDS = {
    # Português - Artigos, pronomes, preposições, conjunções
    'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma',
    'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele',
    'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já',
    'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela', 'entre', 'era',
    'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'quem', 'nas', 'me', 'esse', 'eles',
    'estão', 'você', 'tinha', 'foram', 'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha',
    'têm', 'numa', 'pelos', 'elas', 'havia', 'seja', 'qual', 'será', 'nós', 'tenho', 'lhe',
    'deles', 'essas', 'esses', 'pelas', 'este', 'fosse', 'dele', 'tu', 'te', 'vocês', 'vos',
    'lhes', 'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'nosso', 'nossa', 'nossos', 'nossas',
    'dela', 'delas', 'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles', 'aquelas',
    'isto', 'aquilo', 'estou', 'estamos', 'estive', 'estivemos', 'estiveram', 'estava',
    'estávamos', 'estavam', 'estivera', 'estivéramos', 'esteja', 'estejamos', 'estejam',
    'estivesse', 'estivéssemos', 'estivessem', 'estiver', 'estivermos', 'estiverem', 'hei',
    'havemos', 'hão', 'houve', 'houvemos', 'houveram', 'houvera', 'houvéramos', 'haja',
    'hajamos', 'hajam', 'houvesse', 'houvéssemos', 'houvessem', 'houver', 'houvermos',
    'houverem', 'houverei', 'houverá', 'houveremos', 'houverão', 'houveria', 'houveríamos',
    'houveriam', 'sou', 'somos', 'são', 'éramos', 'eram', 'fui', 'fomos',
    'fora', 'fôramos', 'sejamos', 'sejam', 'fôssemos', 'fossem', 'for',
    'formos', 'forem', 'serei', 'seremos', 'serão', 'seria', 'seríamos', 'seriam',
    'temos', 'tém', 'tínhamos', 'tinham', 'tive', 'tivemos', 'tiveram',
    'tivera', 'tivéramos', 'tenha', 'tenhamos', 'tenham', 'tivesse', 'tivéssemos', 'tivessem',
    'tiver', 'tivermos', 'tiverem', 'terei', 'terá', 'teremos', 'terão', 'teria', 'teríamos',
    'teriam', 'vai', 'vão', 'sobre', 'tudo', 'aqui', 'todos', 'toda', 'todas', 'todo', 'hoje', 'agora',
    'anos', 'ano', 'cada', 'onde', 'quais', 'apenas', 'então', 'entao', 'assim', 'ainda',
    'bem', 'sempre', 'nunca', 'talvez', 'muitos', 'muitas', 'pouco', 'poucos', 'poucas',
    'outra', 'outro', 'outros', 'outras', 'dia', 'dias', 'vez', 'vezes', 'parte', 'forma',
    'modo', 'pode', 'podem', 'fazer', 'feito', 'feita', 'dar', 'dado', 'dada', 'ver',
    'visto', 'vista', 'dizer', 'dito', 'dita', 'saber', 'querer', 'quer', 'estar', 'estao',
    'porque', 'pois', 'aí', 'lá', 'cá', 'rt', 'via', 'pq', 'q', 'tb', 'tbm', 'ai', 'la',
    'gente', 'vida', 'coisa', 'coisas', 'tempo', 'amigo', 'amiga', 'amigos', 'amigas',
    'bom', 'boa', 'bons', 'boas', 'obrigado', 'obrigada', 'valeu', 'legal', 'verdade',
    'foto', 'video', 'vídeo', 'reel', 'reels', 'post', 'imagem', 'comentários', 'comentarios',
    'curtidas', 'seguidores', 'seguir', 'seguindo', 'follow', 'link', 'http', 'https',
    'www', 'com', 'br', 'instagram', 'tiktok', 'twitter', 'youtube', 'facebook', 'perfil',
    'user', 'áudio', 'audio', 'original', 'mil', 'novo', 'nova', 'novos', 'novas',
    'tá', 'ta', 'né', 'ne', 'pra', 'pro', 'vc', 'vcs', 'publicação', 'publicacao',
    'curtidaresponder', 'curtidasresponder', 'semresponder', 'responder', 'respostas',
    'postar', 'comentar', 'curtida', 'salvar', 'compartilhar', 'compartilhe',
    'tradução', 'traducao', 'resposta', 'comentário', 'comentario', 'feed', 'story',
    'stories', 'direto', 'direct', 'enviar', 'mensagem', 'shorts', 'fyp', 'foryou', 'viral',

    # Espanhol - Artigos, pronomes, preposições, verbos e ruídos comuns
    'los', 'las', 'del', 'una', 'uno', 'unos', 'unas', 'con', 'por', 'para', 'sin', 'sobre',
    'tras', 'hasta', 'desde', 'hacia', 'entre', 'contra', 'según', 'segun', 'durante',
    'que', 'qué', 'pero', 'mas', 'más', 'porque', 'pues', 'como', 'cómo', 'cuando', 'cuándo',
    'donde', 'dónde', 'quien', 'quién', 'quienes', 'quiénes', 'cual', 'cuál', 'cuales', 'cuáles',
    'les', 'nos', 'ellos', 'ellas', 'usted', 'ustedes', 'nosotros', 'nosotras', 'vosotros', 'vosotras',
    'mio', 'mía', 'mia', 'míos', 'mios', 'mías', 'mias', 'tuyo', 'tuya', 'tuyos', 'tuyas',
    'suyo', 'suya', 'suyos', 'suyas', 'nuestro', 'nuestra', 'nuestros', 'nuestras',
    'son', 'soy', 'somos', 'era', 'eran', 'fue', 'fueron', 'sido', 'siendo', 'sea', 'sean',
    'estoy', 'está', 'esta', 'están', 'estan', 'estaba', 'estaban', 'estuvo', 'estuvieron',
    'estado', 'estando', 'esté', 'este', 'estén', 'esten', 'estamos',
    'tiene', 'tienen', 'tenía', 'tenia', 'tenían', 'tenian', 'tuvo', 'tuvieron', 'tenido',
    'teniendo', 'tengo', 'tenemos', 'tenga', 'tengan',
    'hay', 'había', 'habia', 'habían', 'habian', 'hubo', 'hubieron', 'habido', 'habiendo',
    'han', 'has', 'hemos', 'haya', 'hayan',
    'hace', 'hacen', 'hacía', 'hacia', 'hacían', 'hacian', 'hizo', 'hicieron', 'hecho', 'haciendo',
    'haga', 'hagan', 'hago', 'hacemos',
    'dice', 'dicen', 'decía', 'decia', 'decían', 'decian', 'dijo', 'dijeron', 'dicho', 'diciendo',
    'diga', 'digan', 'digo', 'decimos',
    'puede', 'pueden', 'podía', 'podia', 'podían', 'podian', 'pudo', 'pudieron', 'podido',
    'puedo', 'podemos', 'pueda', 'puedan',
    'van', 'iba', 'iban', 'ido', 'yendo', 'voy', 'vamos', 'vaya', 'vayan',
    'veo', 've', 'ven', 'veía', 'veia', 'veían', 'veian', 'vio', 'vieron', 'visto', 'viendo',
    'vea', 'vean', 'vemos',
    'dan', 'daba', 'daban', 'dio', 'dieron', 'dado', 'dando', 'doy', 'damos', 'den',
    'sabe', 'saben', 'sabía', 'sabia', 'sabían', 'sabian', 'supo', 'supieron', 'sabido', 'sabiendo',
    'sepa', 'sepan', 'sabemos',
    'quiere', 'quieren', 'quería', 'queria', 'querían', 'querian', 'quiso', 'quisieron',
    'querido', 'queriendo', 'quiero', 'queremos', 'quiera', 'quieran',
    'gusta', 'gustan', 'gustar', 'gustaba',
    'bien', 'mal', 'muy', 'mucho', 'mucha', 'muchos', 'muchas', 'poco', 'poca', 'pocos', 'pocas',
    'tanto', 'tanta', 'tantos', 'tantas', 'tan', 'solo', 'sólo', 'solamente', 'sola', 'solos', 'solas',
    'también', 'tambien', 'tampoco', 'jamás', 'jamas', 'nunca', 'siempre', 'aún', 'aun',
    'todavía', 'todavia', 'hoy', 'ayer', 'mañana', 'manana', 'ahora', 'antes', 'después', 'despues',
    'luego', 'pronto', 'tarde', 'temprano', 'aquí', 'aqui', 'acá', 'aca', 'ahí', 'ahi',
    'allí', 'alli', 'allá', 'alla', 'cerca', 'lejos',
    'todo', 'toda', 'todos', 'todas', 'nada', 'algo', 'alguien', 'nadie',
    'algún', 'algun', 'alguna', 'algunos', 'algunas', 'ningún', 'ningun', 'ninguna',
    'otro', 'otra', 'otros', 'otras', 'mismo', 'misma', 'mismos', 'mismas', 'cada',
    'cualquier', 'cualquiera',
    'día', 'dias', 'gracias', 'favor', 'porfa',
    'hola', 'adios', 'adiós', 'bueno', 'buena', 'buenos', 'buenas',

    # Inglês - Pronomes, verbos auxiliares, preposições e conectivos
    'the', 'and', 'to', 'of', 'in', 'for', 'on', 'with', 'is', 'by', 'at', 'this', 'that', 'from',
    'you', 'are', 'was', 'be', 'it', 'not', 'your', 'have', 'has', 'had', 'having',
    'they', 'them', 'their', 'theirs', 'one', 'two', 'three',
    'what', 'who', 'whom', 'whose', 'which', 'when', 'where', 'why', 'how',
    'all', 'any', 'some', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'such', 'no', 'nor', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    'can', 'will', 'just', 'should', 'now', 'could', 'would', 'may', 'might', 'must',
    'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'under',
    'again', 'further', 'then', 'once', 'here', 'there', 'out', 'off', 'over', 'down',
    'been', 'being', 'were', 'does', 'did', 'doing',
    'like', 'get', 'got', 'getting', 'make', 'made', 'know', 'think', 'see', 'look', 'come', 'came',
    'take', 'took', 'want', 'give', 'good', 'well', 'much', 'many', 'people', 'time',
    'really', 'actually', 'even', 'back', 'way', 'also', 'please', 'thanks', 'thank',
    'dont', 'wont', 'cant', 'didnt', 'isnt', 'arent', 'wasnt', 'werent', 'hasnt', 'havent',
}


def _strip_noise(text: str) -> str:
    t = re.sub(r"https?://\S+|www\.\S+", " ", text)
    t = re.sub(r"@[\w\.]+", " ", t)
    return t


def get_top_words(texts: list, top_n: int = 30) -> list:
    counter = Counter()
    for text in texts:
        if not text or str(text).strip().lower() in _PLACEHOLDER_TEXTS:
            continue
        t_clean = _strip_noise(str(text))
        t_clean = re.sub(r"curtidas?responder|semresponder|responder|respostas|postar", " ", t_clean, flags=re.IGNORECASE)
        t_clean = re.sub(r"\b\d+\s*(?:sem|d|h|min|m)\s*(?:\d+)?\s*(?:curtidas?|likes?)?\b", " ", t_clean, flags=re.IGNORECASE)
        words = re.findall(r"\b[a-zA-ZÀ-ÿ]{3,}\b", t_clean.lower())
        counter.update(w for w in words if w not in STOPWORDS)
    return counter.most_common(top_n)
