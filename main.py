from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Isso libera o acesso para o Stremio

MANIFEST = {
    "id": "it.cinema.italiano",
    "version": "1.0.0",
    "name": "Cinema Italiano",
    "description": "La collezione di film, serie e canali TV italiani.",
    "logo": "https://raw.githubusercontent.com/juvesorocaba-boop/stremio-addon-ita/main/logo.png",
    "types": ["movie", "series"],
    "resources": ["catalog"] # Deixamos apenas catalog por enquanto para não dar erro
}

@app.route('/manifest.json')
def addon_manifest():
    return jsonify(MANIFEST)

# Rota básica de catálogo para o Stremio não reclamar
@app.route('/catalog/movie/film_italiani.json')
def catalog():
    return jsonify({"metas": []})

if __name__ == '__main__':
    app.run()