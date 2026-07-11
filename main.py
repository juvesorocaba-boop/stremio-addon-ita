import os
import json
import base64
import requests
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"

with open("database.json", "r", encoding="utf-8") as f:
    DB = json.load(f)

# Mapa de generi TMDB (id -> nome in italiano) - filme e serie tem tabelas diferentes
GENRES_MOVIE = {
    28: "Azione", 12: "Avventura", 16: "Animazione", 35: "Commedia", 80: "Crimine",
    99: "Documentario", 18: "Drama", 10751: "Famiglia", 14: "Fantasy", 36: "Storia",
    27: "Horror", 10402: "Musica", 9648: "Mistero", 10749: "Romantico",
    878: "Fantascienza", 10770: "Film TV", 53: "Thriller", 10752: "Guerra", 37: "Western"
}
GENRES_TV = {
    10759: "Azione & Avventura", 16: "Animazione", 35: "Commedia", 80: "Crimine",
    99: "Documentario", 18: "Drama", 10751: "Famiglia", 10762: "Bambini",
    9648: "Mistero", 10763: "Notizie", 10764: "Reality", 10765: "Fantascienza & Fantasy",
    10766: "Soap", 10767: "Talk", 10768: "Guerra & Politica", 37: "Western"
}

# Lista de grupos/emissoras disponiveis pro filtro de canais (calculada a partir do database.json)
GRUPPI_CANALI = sorted({item.get("gruppo", "Altro") for item in DB.get("canais", [])})

MANIFEST = {
    "id": "it.cinema.italiano",
    "version": "1.1.0",
    "name": "Cinema Italiano",
    "description": "Film, serie TV e canali in diretta, esclusivamente in lingua italiana originale",
    "logo": "https://raw.githubusercontent.com/juvesorocaba-boop/stremio-addon-ita/main/logo.png",
    "types": ["movie", "series", "tv"],
    "resources": ["catalog", "meta", "stream"],
    "idPrefixes": ["tt", "rai_", "canale_"],
    "catalogs": [
        {
            "type": "movie", "id": "cinema_ita_filmes", "name": "Cinema Italiano - Filme",
            "extra": [
                {"name": "search"},
                {"name": "genre", "options": sorted(set(GENRES_MOVIE.values()))}
            ]
        },
        {
            "type": "series", "id": "cinema_ita_series", "name": "Cinema Italiano - Serie",
            "extra": [
                {"name": "search"},
                {"name": "genre", "options": sorted(set(GENRES_TV.values()))}
            ]
        },
        {
            "type": "tv", "id": "cinema_ita_canais", "name": "Cinema Italiano - Canali TV",
            "extra": [
                {"name": "search"},
                {"name": "genre", "options": GRUPPI_CANALI}
            ]
        }
    ],
    # Isso é o que faz a engrenagem de configurações aparecer no Stremio
    "behaviorHints": {
        "configurable": True,
        "configurationRequired": False
    }
}

# Cache simples em memória pra não bater na TMDB toda hora
_tmdb_cache = {}


def parse_config(config_str):
    """Decodifica o config (qualità/provider/token) vindo do segmento da URL, se existir."""
    if not config_str:
        return {}
    try:
        padded = config_str + "=" * (-len(config_str) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode()).decode()
        return json.loads(decoded)
    except Exception:
        return {}


def get_tmdb_meta(imdb_id, tipo):
    """Busca metadata em italiano no TMDB via IMDB ID.
    Retorna None se o conteúdo não for de idioma original italiano
    (filtro anti-erro do escopo original)."""
    cache_key = (imdb_id, tipo)
    if cache_key in _tmdb_cache:
        return _tmdb_cache[cache_key]

    if not TMDB_API_KEY:
        return None

    try:
        find_url = f"{TMDB_BASE}/find/{imdb_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "external_source": "imdb_id",
            "language": "it-IT"
        }
        r = requests.get(find_url, params=params, timeout=8)
        data = r.json()

        results = data.get("movie_results") or data.get("tv_results")
        if not results:
            _tmdb_cache[cache_key] = None
            return None

        item = results[0]
        original_language = item.get("original_language")

        # REGRA MESTRE: só aceita se o idioma original for italiano
        if original_language != "it":
            _tmdb_cache[cache_key] = None
            return None

        titulo = item.get("title") or item.get("name")
        sinopse = item.get("overview") or ""
        poster_path = item.get("poster_path")
        poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""

        genre_ids = item.get("genre_ids", [])
        tabela_generi = GENRES_MOVIE if tipo == "movie" else GENRES_TV
        generi = [tabela_generi[g] for g in genre_ids if g in tabela_generi]

        meta = {"titulo": titulo, "sinopse": sinopse, "poster": poster, "generi": generi}
        _tmdb_cache[cache_key] = meta
        return meta

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Manifest / logo / configure
# ---------------------------------------------------------------------------

PROVIDER_TAG = {
    "realdebrid": "RD",
    "alldebrid": "AD",
    "torbox": "TB",
}


@app.route('/manifest.json')
@app.route('/<config_str>/manifest.json')
def manifest(config_str=None):
    cfg = parse_config(config_str)
    provider = cfg.get("provider")
    tag = PROVIDER_TAG.get(provider)

    if not tag:
        return jsonify(MANIFEST)

    m = dict(MANIFEST)
    m["name"] = f'{MANIFEST["name"]} | {tag}'
    return jsonify(m)


@app.route('/logo.png')
def logo():
    return send_from_directory('.', 'logo.png')


@app.route("/configure")
@app.route("/<config_str>/configure")
def configure(config_str=None):
    return render_template("configure.html")


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@app.route('/catalog/<tipo>/<cat_id>.json')
@app.route('/catalog/<tipo>/<cat_id>/<extra>.json')
@app.route('/<config_str>/catalog/<tipo>/<cat_id>.json')
@app.route('/<config_str>/catalog/<tipo>/<cat_id>/<extra>.json')
def catalog(tipo, cat_id, extra=None, config_str=None):
    search_query = None
    genre_filter = None
    if extra:
        # o Stremio manda os parametros extra separados por '&' dentro do segmento
        for par in extra.split("&"):
            if par.startswith("search="):
                search_query = par.replace("search=", "").strip().lower()
            elif par.startswith("genre="):
                genre_filter = requests.utils.unquote(par.replace("genre=", "").strip())

    metas = []

    if tipo == "movie":
        for item in DB.get("filmes", []):
            tmdb = get_tmdb_meta(item["id"], "movie")
            if not tmdb:
                continue  # não é italiano de verdade, ignora
            if search_query and search_query not in tmdb["titulo"].lower():
                continue
            if genre_filter and genre_filter not in tmdb["generi"]:
                continue
            metas.append({
                "id": item["id"],
                "type": "movie",
                "name": tmdb["titulo"],
                "poster": tmdb["poster"],
                "description": tmdb["sinopse"],
                "genres": tmdb["generi"]
            })

    elif tipo == "series":
        for item in DB.get("series", []):
            tmdb = get_tmdb_meta(item["id"], "series")
            if not tmdb:
                continue
            if search_query and search_query not in tmdb["titulo"].lower():
                continue
            if genre_filter and genre_filter not in tmdb["generi"]:
                continue
            metas.append({
                "id": item["id"],
                "type": "series",
                "name": tmdb["titulo"],
                "poster": tmdb["poster"],
                "description": tmdb["sinopse"],
                "genres": tmdb["generi"]
            })

    elif tipo == "tv":
        for item in DB.get("canais", []):
            if search_query and search_query not in item["titulo"].lower():
                continue
            if genre_filter and item.get("gruppo", "Altro") != genre_filter:
                continue
            metas.append({
                "id": item["id"],
                "type": "tv",
                "name": item["titulo"],
                "poster": item.get("poster", ""),
                "genres": [item.get("gruppo", "Altro")]
            })

    return jsonify({"metas": metas})


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

@app.route('/meta/<tipo>/<meta_id>.json')
@app.route('/<config_str>/meta/<tipo>/<meta_id>.json')
def meta(tipo, meta_id, config_str=None):
    if tipo == "movie":
        for item in DB.get("filmes", []):
            if item["id"] == meta_id:
                tmdb = get_tmdb_meta(item["id"], "movie")
                if not tmdb:
                    return jsonify({"meta": {}}), 404
                return jsonify({"meta": {
                    "id": item["id"], "type": "movie",
                    "name": tmdb["titulo"], "poster": tmdb["poster"],
                    "description": tmdb["sinopse"], "genres": tmdb["generi"]
                }})

    elif tipo == "series":
        for item in DB.get("series", []):
            if item["id"] == meta_id:
                tmdb = get_tmdb_meta(item["id"], "series")
                if not tmdb:
                    return jsonify({"meta": {}}), 404
                videos = []
                for temporada, episodios in item.get("temporadas", {}).items():
                    for episodio in episodios:
                        videos.append({
                            "id": f"{item['id']}:{temporada}:{episodio}",
                            "title": f"S{int(temporada):02d}E{int(episodio):02d}",
                            "season": int(temporada),
                            "episode": int(episodio)
                        })
                return jsonify({"meta": {
                    "id": item["id"], "type": "series",
                    "name": tmdb["titulo"], "poster": tmdb["poster"],
                    "description": tmdb["sinopse"], "genres": tmdb["generi"],
                    "videos": videos
                }})

    elif tipo == "tv":
        for item in DB.get("canais", []):
            if item["id"] == meta_id:
                return jsonify({"meta": {
                    "id": item["id"], "type": "tv", "name": item["titulo"],
                    "genres": [item.get("gruppo", "Altro")]
                }})

    return jsonify({"meta": {}}), 404


# ---------------------------------------------------------------------------
# Stream
# ---------------------------------------------------------------------------

_size_cache = {}


def format_size(num_bytes):
    """Converte bytes pra string tipo '602.96 MB' ou '1.46 GB'."""
    if num_bytes is None:
        return None
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.2f} {unit}"
        size /= 1024


def get_file_size(url):
    """Pega o tamanho do arquivo via HEAD request, com cache em memória."""
    if url in _size_cache:
        return _size_cache[url]
    size_str = None
    try:
        r = requests.head(url, timeout=6, allow_redirects=True)
        length = r.headers.get("Content-Length")
        if length:
            size_str = format_size(int(length))
    except Exception:
        size_str = None
    _size_cache[url] = size_str
    return size_str


def build_stream(nome_conteudo, url, extra_linha=None):
    """Monta o objeto stream no padrão dos outros addons: name = tag curta,
    title = nome do conteúdo + tamanho (+ linha extra opcional, tipo qualidade)."""
    tamanho = get_file_size(url)
    linhas = [nome_conteudo]
    detalhe = []
    if tamanho:
        detalhe.append(f"💾 {tamanho}")
    if extra_linha:
        detalhe.append(extra_linha)
    if detalhe:
        linhas.append(" | ".join(detalhe))

    return {
        "name": "Cinema Italiano",
        "title": "\n".join(linhas),
        "url": url
    }


@app.route('/stream/<tipo>/<stream_id>.json')
@app.route('/<config_str>/stream/<tipo>/<stream_id>.json')
def stream(tipo, stream_id, config_str=None):
    cfg = parse_config(config_str)
    # cfg pode ter: cfg.get("qualities") -> lista, ex ["1080p", "720p"]
    # cfg.get("provider"), cfg.get("token") -> reservados pra uso futuro

    streams = []

    if tipo == "movie":
        for item in DB.get("filmes", []):
            if item["id"] == stream_id:
                streams.append(build_stream(item["titulo"], item["url"]))

    elif tipo == "series":
        parts = stream_id.split(":")
        base_id = parts[0]
        for item in DB.get("series", []):
            if item["id"] == base_id and len(parts) == 3:
                temporada, episodio = parts[1], parts[2]
                url = item.get("temporadas", {}).get(temporada, {}).get(episodio)
                if url:
                    nome = f"{item['titulo']} S{int(temporada):02d}E{int(episodio):02d}"
                    streams.append(build_stream(nome, url))

    elif tipo == "tv":
        for item in DB.get("canais", []):
            if item["id"] == stream_id:
                streams.append(build_stream(item["titulo"], item["url"], "🔴 Diretta"))

    return jsonify({"streams": streams})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)