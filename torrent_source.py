import cloudscraper
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# Configuração Central de Provedores
# Cada entrada possui: url base de busca, seletor CSS e se precisa entrar no link (is_indirect)
PROVIDERS = {
    "1337x": {"url": "https://1337x.to/search/{q}/1/", "css": "a[href*='/torrent/']", "is_indirect": True},
    "TorrentGalaxy": {"url": "https://torrentgalaxy.to/torrents.php?search={q}", "css": "a[href^='magnet:?']", "is_indirect": False},
    "Nyaa": {"url": "https://nyaa.si/?f=0&c=0_0&q={q}", "css": "a[href^='magnet:?']", "is_indirect": False},
    "Rutracker": {"url": "https://rutracker.org/forum/tracker.php?nm={q}", "css": "a.magnet-link", "is_indirect": False},
    "Rutor": {"url": "http://rutor.info/search/0/0/100/0/{q}", "css": "a[href^='magnet:?']", "is_indirect": False},
    "MagnetDL": {"url": "https://www.magnetdl.com/{q[0]}/{q}/", "css": "a[href^='magnet:?']", "is_indirect": False},
    "YTS": {"url": "https://yts.mx/browse-movies/{q}/all/all/0/latest", "css": "a.browse-movie-link", "is_indirect": True},
    "EZTV": {"url": "https://eztvx.to/search/{q}", "css": "a[href^='magnet:?']", "is_indirect": False}
}

def get_magnet(scraper, url, css, is_indirect):
    try:
        r = scraper.get(url, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        link = soup.select_one(css)
        if not link: return None
        
        if is_indirect:
            # Segue para a página interna do torrent
            target = "https://1337x.to" + link['href'] if "1337x" in url else "https://yts.mx" + link['href']
            r2 = scraper.get(target, timeout=5)
            magnet = BeautifulSoup(r2.text, 'html.parser').select_one("a[href^='magnet:?']")
            return magnet['href'] if magnet else None
        return link['href']
    except: return None

def buscar_stream_torrent(query):
    query_fmt = query.replace(" ", "+")
    scraper = cloudscraper.create_scraper()
    
    def processar(nome, cfg):
        url = cfg["url"].format(q=query_fmt)
        return get_magnet(scraper, url, cfg["css"], cfg["is_indirect"])

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda p: processar(p[0], p[1]), PROVIDERS.items()))
    
    # Retorna apenas os links válidos encontrados
    return [r for r in results if r]