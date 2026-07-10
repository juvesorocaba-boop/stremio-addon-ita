import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Carrega o banco de dados uma vez ao iniciar
with open("database.json", "r", encoding="utf-8") as f:
    DB = json.load(f)

MANIFEST = {
    "id": "it.cinema.italiano",
    "version": "1.0.0",
    "name": "Cinema Italiano",
    "description": "Film, serie TV e canali in diretta, esclusivamente in lingua italiana originale",
    "logo": "https://stremio-addon-ita.onrender.com/logo.png",
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
@app.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)


@app.route('/catalog/<type>/<id>.json')
def catalog(type, id):
    metas = []

    if type == "movie":
        for item in DB.get("filmes", []):
            metas.append({
                "id": item["id"],
                "type": "movie",
                "name": item["titulo"],
                "poster": item.get("poster", "")
            })

    elif type == "series":
        for item in DB.get("series", []):
            metas.append({
                "id": item["id"],
                "type": "series",
                "name": item["titulo"],
                "poster": item.get("poster", "")
            })

    elif type == "tv":
        for item in DB.get("canais", []):
            metas.append({
                "id": item["id"],
                "type": "tv",
                "name": item["titulo"],
                "poster": item.get("poster", "")
            })

    return jsonify({"metas": metas})


@app.route('/meta/<type>/<id>.json')
def meta(type, id):
    if type == "movie":
        for item in DB.get("filmes", []):
            if item["id"] == id:
                return jsonify({"meta": {
                    "id": item["id"], "type": "movie", "name": item["titulo"]
                }})

    elif type == "series":
        for item in DB.get("series", []):
            if item["id"] == id:
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
                    "id": item["id"], "type": "series", "name": item["titulo"],
                    "videos": videos
                }})

    elif type == "tv":
        for item in DB.get("canais", []):
            if item["id"] == id:
                return jsonify({"meta": {
                    "id": item["id"], "type": "tv", "name": item["titulo"]
                }})

    return jsonify({"meta": {}}), 404


@app.route('/stream/<type>/<id>.json')
def stream(type, id):
    streams = []

    if type == "movie":
        for item in DB.get("filmes", []):
            if item["id"] == id:
                streams.append({"title": "Servidor 1", "url": item["url"]})

    elif type == "series":
        # id vem como tt0118301:1:1
        parts = id.split(":")
        base_id = parts[0]
        for item in DB.get("series", []):
            if item["id"] == base_id and len(parts) == 3:
                temporada, episodio = parts[1], parts[2]
                url = item.get("temporadas", {}).get(temporada, {}).get(episodio)
                if url:
                    streams.append({"title": "Servidor 1", "url": url})

    elif type == "tv":
        for item in DB.get("canais", []):
            if item["id"] == id:
                streams.append({"title": "Ao Vivo", "url": item["url"]})

    return jsonify({"streams": streams})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)