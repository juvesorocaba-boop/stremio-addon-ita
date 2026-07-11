import requests
from bs4 import BeautifulSoup

def buscar_stream_torrent(nome_filme):
    """
    Função principal que busca em todos os provedores mapeados
    e retorna uma lista consolidada de URLs magnéticas.
    """
    lista_de_urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # Mapeamento dos provedores configurados
    providers = {
        "1337x": {"url": "https://1337x.to/search/{q}/1/", "css": "a[href*='/torrent/']"},
        "TorrentGalaxy": {"url": "https://torrentgalaxy.to/torrents.php?search={q}", "css": "div.tgxtable a[href*='/torrent/']"},
        "Nyaa": {"url": "https://nyaa.si/?f=0&c=0_0&q={q}", "css": "table.torrent-list a[href*='/view/']"},
        "Rutracker": {"url": "https://rutracker.org/forum/tracker.php?nm={q}", "css": "a.tLink"},
        "Rutor": {"url": "http://rutor.info/search/0/0/000/0/{q}", "css": "a[href*='/torrent/']"},
        "MagnetDL": {"url": "https://www.magnetdl.com/{q[0]}/{q}/", "css": "table.download a[href*='magnet:?']"},
        "EzTV": {"url": "https://eztv.re/search/{q}", "css": "a.epinfo"},
        "ThePirateBay": {"url": "https://thepiratebay.party/search/{q}/1/99/0", "css": "a.detLink"},
        "Kickass": {"url": "https://kickass.torrentbay.st/usearch/{q}/", "css": "a.torType"},
        "LimeTorrents": {"url": "https://www.limetorrents.pro/search/all/{q}/", "css": "div.tt-name a[href*='/torrent/']"}
    }

    query_formatted = nome_filme.replace(" ", "+")
    
    for nome, config in providers.items():
        try:
            # Tratamento especial para MagnetDL que exige primeira letra da query
            url = config["url"].replace("{q}", query_formatted)
            
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                elements = soup.select(config["css"])
                
                for el in elements:
                    if el.has_attr('href'):
                        link = el['href']
                        # Garante que estamos pegando links válidos
                        lista_de_urls.append(link)
        except Exception:
            # Segue para o próximo provider caso ocorra erro em um deles
            continue
            
    return list(set(lista_de_urls)) # Remove duplicatas e retorna a lista