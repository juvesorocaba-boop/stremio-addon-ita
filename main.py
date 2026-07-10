from flask import Flask, jsonify

app = Flask(__name__)

MANIFEST = {
    "id": "it.cinema.italiano",
    "version": "1.0.0",
    "name": "Cinema Italiano",
    "description": "La collezione definitiva di film, serie e canali TV italiani in streaming.",
    "logo": "https://raw.githubusercontent.com/juvesorocaba-boop/stremio-addon-ita/main/logo.png",
    "types": ["movie", "series", "channel"],
    "catalogs": [
        {
            "type": "movie",
            "id": "film_italiani",
            "name": "Film Italiani"
        },
        {
            "type": "series",
            "id": "serie_italiane",
            "name": "Serie Italiane"
        },
        {
            "type": "channel",
            "id": "canali_tv",
            "name": "Canali TV"
        }
    ],
    "resources": ["catalog", "meta", "stream"]
}

@app.route('/manifest.json')
def addon_manifest():
    return jsonify(MANIFEST)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)