
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

