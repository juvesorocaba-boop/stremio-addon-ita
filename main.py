import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "id": "it.cinema.italiano",
        "version": "1.0.0",
        "name": "Cinema Italiano",
        "description": "Filmes e séries italianas",
        "types": ["movie", "series"],
        "resources": ["catalog"],
        "catalogs": []
    })

if __name__ == '__main__':
    # O Render exige que você utilize a porta da variável de ambiente
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)