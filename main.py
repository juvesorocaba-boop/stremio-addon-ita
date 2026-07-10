import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Liberação de CORS para o Stremio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MANIFEST = {
    "id": "org.stremio.italiano.mvp",
    "version": "1.0.0",
    "name": "Italiano Exclusivo MVP",
    "description": "Filmes, séries e TV ao vivo estritamente de produção italiana.",
    "resources": ["catalog", "stream"],
    "types": ["movie", "series", "tv"],
    "idPrefixes": ["tt", "rai_", "canale_"],
    "catalogs": [
        {"type": "movie", "id": "ita_movies", "name": "Filmes Italianos", "extra": [{"name": "search"}]},
        {"type": "series", "id": "ita_series", "name": "Séries Italianas", "extra": [{"name": "search"}]},
        {"type": "tv", "id": "ita_tv", "name": "Canais Italianos"}
    ]
}

def ler_banco():
    with open("database.json", "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/")
def read_root():
    return {"Status": "Servidor do Add-on rodando 100%!"}

@app.get("/manifest.json")
def get_manifest():
    return MANIFEST

# Rota de Catálogo atualizada para suportar buscas normais e por barra de pesquisa
@app.get("/catalog/{type}/{catalog_id}.json")
@app.get("/catalog/{type}/{catalog_id}/search={search_query}.json")
def get_catalog(type: str, catalog_id: str, search_query: str = None):
    dados = ler_banco()
    metas = []
    
    # Normaliza o termo buscado se ele existir
    busca = search_query.lower() if search_query else None
    
    if type == "movie" and catalog_id == "ita_movies":
        for f in dados.get("filmes", []):
            if not busca or busca in f["titulo"].lower():
                metas.append({
                    "id": f["id"],
                    "type": "movie",
                    "name": f["titulo"],
                    "poster": "https://placehold.co/300x450?text=Filme+Ita"
                })
            
    elif type == "series" and catalog_id == "ita_series":
        for s in dados.get("series", []):
            if not busca or busca in s["titulo"].lower():
                metas.append({
                    "id": s["id"],
                    "type": "series",
                    "name": s["titulo"],
                    "poster": "https://placehold.co/300x450?text=Serie+Ita"
                })
            
    elif type == "tv" and catalog_id == "ita_tv":
        for c in dados.get("canais", []):
            if not busca or busca in c["titulo"].lower():
                metas.append({
                    "id": c["id"],
                    "type": "tv",
                    "name": c["titulo"],
                    "poster": "https://placehold.co/300x450?text=TV+Ita"
                })
            
    return {"metas": metas}

# NOVA ROTA: Responsável por mandar os links de reprodução para o player do Stremio
@app.get("/stream/{type}/{id}.json")
def get_stream(type: str, id: str):
    dados = ler_banco()
    streams = []
    
    if type == "movie":
        for f in dados.get("filmes", []):
            if f["id"] == id:
                streams.append({
                    "name": "Italiano MVP",
                    "title": f["titulo"],
                    "url": f["url"]
                })
                
    elif type == "series":
        # O Stremio envia IDs de série no formato ID_IMDB:TEMPORADA:EPISODIO (Ex: tt0118301:1:1)
        partes = id.split(":")
        if len(partes) == 3:
            imdb_id, temporada, episodio = partes[0], partes[1], partes[2]
            for s in dados.get("series", []):
                if s["id"] == imdb_id:
                    # Coleta a URL correspondente à temporada e episódio corretos
                    url_ep = s.get("temporadas", {}).get(temporada, {}).get(episodio)
                    if url_ep:
                        streams.append({
                            "name": "Italiano MVP",
                            "title": f"{s['titulo']} S{temporada}E{episodio}",
                            "url": url_ep
                        })
                        
    elif type == "tv":
        for c in dados.get("canais", []):
            if c["id"] == id:
                streams.append({
                    "name": "Italiano Live TV",
                    "title": c["titulo"],
                    "url": c["url"]
                })
                
    return {"streams": streams}