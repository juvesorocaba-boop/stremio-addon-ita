import os
import json
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import base64
import json
from flask import render_template

def parse_config(config_str):
    """Decodifica il config (qualità/provider/token) dal segmento URL, se presente."""
    if not config_str:
        return {}
    try:
        padded = config_str + "=" * (-len(config_str) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode()).decode()
        return json.loads(decoded)
    except Exception:
        return {}

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"

with open("database.json", "r", encoding="utf-8") as f:
    DB = json.load(f)

MANIFEST = {
    "id": "it.cinema.italiano",
    "version": "1.0.0",
    "name": "Cinema Italiano",
    "description": "Film, serie TV e canali in diretta, esclusivamente in lingua italiana originale",
    "logo": "https://raw.githubusercontent.com/juvesorocaba-boop/stremio-addon-ita/main/logo.png",
    "types": ["movie", "series", "tv"],
    "resources": ["catalog", "meta", "stream"],
    "idPrefixes": ["tt", "rai_", "canale_"],
    "catalogs": [
        {"type": "movie", "id": "cinema_ita_filmes", "name": "Film Italiani",
         "extra": [{"name": "search"}]},
        {"type": "series", "id": "cinema_ita_series", "name": "Serie TV Italiane",
         "extra": [{"name": "search"}]},
        {"type": "tv", "id": "cinema_ita_canais", "name": "TV Italiana in Diretta"}
    ]
}

# Cache simples em memória pra não bater na TMDB toda hora
_tmdb_cache = {}


def get_tmdb_meta(imdb_id, tipo):
    """Busca metadata em italiano no TMDB via IMDB ID.
    Retorna None se o conteúdo não for de idioma original italiano
    (filtro anti-erro do escopo original)."""
    if imdb_id in _tmdb_cache:
        return _tmdb_cache[imdb_id]

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
            _tmdb_cache[imdb_id] = None
            return None

        item = results[0]
        original_language = item.get("original_language")

        # REGRA MESTRE: só aceita se o idioma original for italiano
        if original_language != "it":
            _tmdb_cache[imdb_id] = None
            return None

        titulo = item.get("title") or item.get("name")
        sinopse = item.get("overview") or ""
        poster_path = item.get("poster_path")
        poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""

        meta = {"titulo": titulo, "sinopse": sinopse, "poster": poster}
        _tmdb_cache[imdb_id] = meta
        return meta

    except Exception:
        return None


@app.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)


@app.route('/logo.png')
def logo():
    return send_from_directory('.', 'logo.png')


@app.route('/catalog/<tipo>/<cat_id>.json')
@app.route('/catalog/<tipo>/<cat_id>/<extra>.json')
def catalog(tipo, cat_id, extra=None):
    search_query = None
    if extra and extra.startswith("search="):
        search_query = extra.replace("search=", "").strip().lower()
        
        
@app.route("/configure")
@app.route("/<config_str>/configure")
def configure(config_str=None):
    return render_template("configure.html")

    metas = []

    if tipo == "movie":
        for item in DB.get("filmes", []):
            tmdb = get_tmdb_meta(item["id"], "movie")
            if not tmdb:
                continue  # não é italiano de verdade, ignora
            if search_query and search_query not in tmdb["titulo"].lower():
                continue
            metas.append({
                "id": item["id"],
                "type": "movie",
                "name": tmdb["titulo"],
                "poster": tmdb["poster"],
                "description": tmdb["sinopse"]
            })

    elif tipo == "series":
        for item in DB.get("series", []):
            tmdb = get_tmdb_meta(item["id"], "series")
            if not tmdb:
                continue
            if search_query and search_query not in tmdb["titulo"].lower():
                continue
            metas.append({
                "id": item["id"],
                "type": "series",
                "name": tmdb["titulo"],
                "poster": tmdb["poster"],
                "description": tmdb["sinopse"]
            })

    elif tipo == "tv":
        for item in DB.get("canais", []):
            if search_query and search_query not in item["titulo"].lower():
                continue
            metas.append({
                "id": item["id"],
                "type": "tv",
                "name": item["titulo"],
                "poster": item.get("poster", "")
            })

    return jsonify({"metas": metas})


@app.route('/meta/<tipo>/<meta_id>.json')
def meta(tipo, meta_id):
    if tipo == "movie":
        for item in DB.get("filmes", []):
            if item["id"] == meta_id:
                tmdb = get_tmdb_meta(item["id"], "movie")
                if not tmdb:
                    return jsonify({"meta": {}}), 404
                return jsonify({"meta": {
                    "id": item["id"], "type": "movie",
                    "name": tmdb["titulo"], "poster": tmdb["poster"],
                    "description": tmdb["sinopse"]
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
                    "description": tmdb["sinopse"], "videos": videos
                }})

    elif tipo == "tv":
        for item in DB.get("canais", []):
            if item["id"] == meta_id:
                return jsonify({"meta": {
                    "id": item["id"], "type": "tv", "name": item["titulo"]
                }})

    return jsonify({"meta": {}}), 404


@app.route('/stream/<tipo>/<stream_id>.json')
def stream(tipo, stream_id):
    streams = []

    if tipo == "movie":
        for item in DB.get("filmes", []):
            if item["id"] == stream_id:
                streams.append({"title": "Server", "url": item["url"]})

    elif tipo == "series":
        parts = stream_id.split(":")
        base_id = parts[0]
        for item in DB.get("series", []):
            if item["id"] == base_id and len(parts) == 3:
                temporada, episodio = parts[1], parts[2]
                url = item.get("temporadas", {}).get(temporada, {}).get(episodio)
                if url:
                    streams.append({"title": "Server", "url": url})

    elif tipo == "tv":
        for item in DB.get("canais", []):
            if item["id"] == stream_id:
                streams.append({"title": "Diretta", "url": item["url"]})

    return jsonify({"streams": streams})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)