#!/usr/bin/env python3
"""Busca informações básicas dos Majors de 2015 (Katowice, Cologne, Cluj) na Liquipedia.
Salva resultado em data/majors-2015.json
"""
import json
import time

from typing import List, Dict

try:
    import requests
    from bs4 import BeautifulSoup
except Exception as e:
    raise RuntimeError("Dependências faltando. Rode: pip install requests beautifulsoup4 lxml") from e

OUT = 'data/majors-2015.json'

MAJORS = {
    'Katowice 2015': ['ESL_One_Katowice_2015', 'Intel_Extreme_Masters_Katowice_2015'],
    'Cologne 2015': ['ESL_One_Cologne_2015'],
    'Cluj-Napoca 2015': ['DreamHack_Cluj-Napoca_2015']
}

HEADERS = {
    'User-Agent': 'cstory-data-fetcher/1.0 (+https://github.com)'
}


def try_fetch(url: str) -> requests.Response:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r
    except Exception:
        return None


def fetch_wikitext(page_title: str) -> str | None:
    api = 'https://liquipedia.net/counterstrike/api.php'
    params = {
        'action': 'parse',
        'page': page_title,
        'prop': 'wikitext',
        'format': 'json'
    }
    try:
        r = requests.get(api, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        j = r.json()
        return j.get('parse', {}).get('wikitext', {}).get('*')
    except Exception:
        return None


def extract_redirect_target(wikitext: str) -> str | None:
    import re
    m = re.search(r"#redirect\s*\[\[(.*?)\]\]", wikitext, re.IGNORECASE)
    if m:
        # return the target before any pipe
        return m.group(1).split('|')[0].strip()
    return None


def fetch_and_parse_page(page: str, depth=0):
    """Fetch a page wikitext, follow redirects up to a small depth, and parse common infobox fields."""
    if depth > 4:
        return None
    wikitext = fetch_wikitext(page)
    if not wikitext:
        return None
    redirect = extract_redirect_target(wikitext)
    if redirect and redirect != page.replace('_', ' '):
        target = redirect.replace(' ', '_')
        return fetch_and_parse_page(target, depth + 1)

    # parse key = value pairs from wikitext
    import re
    info = {}
    for m in re.finditer(r"\|\s*([^=\n]+?)\s*=\s*(.+)", wikitext):
        k = m.group(1).strip()
        v = m.group(2).strip()
        info[k] = v

    # normalize keys lowercased
    info_l = {k.lower(): v for k, v in info.items()}

    # helper: clean wiki link or template to plain text
    def clean_wikilink(text: str) -> str:
        # remove templates and brackets
        text = re.sub(r"\{\{[^}]+\}\}", "", text)
        text = re.sub(r"\[\[([^\]|]+)\|?([^\]]+)?\]\]", lambda m: (m.group(2) or m.group(1)), text)
        return text.strip()

    # prize
    prize_raw = None
    for key in ('prizepoolusd', 'prizepool', 'prize_pool', 'prize', 'prizepoolusd'):
        if key in info_l:
            prize_raw = info_l[key]
            break
    prize_usd = None
    if prize_raw:
        # extract digits
        nums = re.sub(r"[^0-9]", "", prize_raw)
        if nums:
            try:
                prize_usd = int(nums)
            except Exception:
                prize_usd = None

    # winner/champion
    winner = None
    for key in ('champion', 'champions', 'winner', 'winners'):
        if key in info_l and info_l[key].strip():
            winner = clean_wikilink(info_l[key])
            break

    # if still not found, try common templates or final link in wikitext
    if not winner:
        m = re.search(r"\{\{(?:winner|champion)[^\}|]*\|?([^}\|]+)\}?\}\]?,?", wikitext, re.IGNORECASE)
        if m:
            winner = clean_wikilink(m.group(1))
        else:
            m2 = re.search(r"winner[^\n]*\[\[([^\]]+)\]\]", wikitext, re.IGNORECASE)
            if m2:
                winner = clean_wikilink(m2.group(1))

    # participants/teams: try explicit fields first
    participants = []
    for key in ('entrants', 'teams', 'participants', 'team_number'):
        if key in info_l and info_l[key].strip():
            raw = info_l[key]
            parts = re.split(r"[,\n]+", raw)
            participants = [clean_wikilink(p) for p in parts if p.strip()]
            break

    # fallback: extract wikilinks present in the wikitext and filter likely team names
    if not participants:
        links = []
        for m in re.finditer(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", wikitext):
            page_name = m.group(1).strip()
            display = (m.group(2) or m.group(1)).strip()
            # filter out namespace and tournament pages
            if ':' in page_name or '/' in page_name:
                continue
            # skip category, file, template
            if page_name.lower().startswith(('file:', 'category:', 'template:')):
                continue
            # heuristic: likely team names have letters and possibly numbers
            if re.search(r"[A-Za-z0-9]", display):
                links.append(clean_wikilink(display))
        # unique while preserving order
        seen = set()
        filtered = []
        for t in links:
            if t and t not in seen:
                seen.add(t)
                filtered.append(t)
        # limit to reasonable number (team_number or 16)
        limit = 16
        participants = filtered[:limit]

    date = info_l.get('sdate') or info_l.get('date') or info_l.get('dates')
    # if winner still unknown, try deeper wikitext heuristics
    if not winner:
        try:
            w = extract_winner_from_wikitext(wikitext)
            if w:
                winner = w
        except Exception:
            pass

    # if still not found, try candidate subpages linked in the wikitext (e.g., pages with 'Final', 'Bracket', 'Playoffs')
    if not winner and depth < 3:
        import re
        candidates = []
        for m in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", wikitext):
            p = m.group(1).strip()
            if any(x in p.lower() for x in ('final', 'bracket', 'playoff', 'playoffs', 'finals')):
                candidates.append(p.replace(' ', '_'))
        # try each candidate
        for cand in candidates:
            try:
                sub = fetch_and_parse_page(cand, depth=depth+1)
                if sub and sub.get('winner'):
                    winner = sub.get('winner')
                    break
            except Exception:
                continue

    return {
        'title': page.replace('_', ' '),
        'wikitext_snippet': wikitext[:1600],
        'winner': winner,
        'teams': participants,
        'date': date,
        'prize_usd': prize_usd,
        'source_page': page,
    }


def extract_winner_from_wikitext(wikitext: str) -> str | None:
    """Tentativa heurística de extrair o vencedor a partir do wikitext.
    Procura por blocos 'Final', templates de resultado e padrões de pontuação entre wikilinks."""
    import re

    # 1) procura por padrão: [[TeamA]] ... score ... [[TeamB]]
    m = re.search(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\][^\n]{0,80}?(\d+)\s*[–-]\s*(\d+)[^\n]{0,80}?\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", wikitext)
    if m:
        team1 = m.group(1).strip()
        s1 = int(m.group(2))
        s2 = int(m.group(3))
        team2 = m.group(4).strip()
        return team1 if s1 > s2 else team2

    # 2) procurar seção 'Final' e extrair primeiros dois wikilinks próximos
    msec = re.search(r"(?i)={2,}\s*Finals?\s*={2,}|(?i)==\s*Finals?\s*==|(?i)'''Final'''", wikitext)
    if msec:
        start = msec.end()
        snippet = wikitext[start:start+800]
        links = re.findall(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", snippet)
        # links returns tuples (page, label)
        teams = []
        for p, lab in links:
            name = (lab or p).strip()
            if ':' in p or '/' in p:
                continue
            if name and len(name) > 1:
                teams.append(name)
        if len(teams) >= 2:
            # try detect score nearby
            mscore = re.search(r"\[\[[^\]]+\]\][^\n]{0,80}?(\d+)\s*[–-]\s*(\d+)[^\n]{0,80}?\[\[[^\]]+\]\]", snippet)
            if mscore:
                s1 = int(mscore.group(1)); s2 = int(mscore.group(2))
                return teams[0] if s1 > s2 else teams[1]
            return teams[0]

    # 3) procurar template Result / Scorebox
    m2 = re.search(r"\{\{Result[^{]*?\[\[([^\]|]+)(?:\|[^\]]+)?\]\][^\d]{0,40}(\d+)[^\d]{0,10}(\d+)[^\]]*?\[\[([^\]|]+)", wikitext, re.IGNORECASE)
    if m2:
        t1 = m2.group(1).strip(); s1 = int(m2.group(2)); s2 = int(m2.group(3)); t2 = m2.group(4).strip()
        return t1 if s1 > s2 else t2

    # 4) fallback: procurar 'champion' ou 'winner' em wikitext já limpo
    m3 = re.search(r"\|\s*(?:champion|champions|winner|winners)\s*=\s*(.+)", wikitext, re.IGNORECASE)
    if m3:
        txt = m3.group(1).strip()
        # extrair primeiro wikilink se houver
        mm = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", txt)
        if mm:
            return (mm.group(2) or mm.group(1)).strip()
        # senão clean text
        return re.sub(r"\{\{[^}]+\}\}", "", txt).split(',')[0].strip()

    return None


def parse_liquipedia(html: str) -> Dict:
    soup = BeautifulSoup(html, 'lxml')
    data = {}
    # title
    title = soup.find('h1', class_='page-header__title') or soup.find('h1')
    if title:
        data['title'] = title.get_text(strip=True)

    info: Dict[str, str] = {}

    # Liquipedia uses 'portable-infobox' (aside) with .pi-data-label / .pi-data-value
    pinfo = soup.find(lambda tag: tag.name in ('aside','div') and tag.get('class') and any('portable-infobox' in c or 'pi-theme' in c for c in tag.get('class')))
    if not pinfo:
        # fallback to table.infobox
        pinfo = soup.find('table', class_='infobox')

    if pinfo:
        # parse portable-infobox style
        for item in pinfo.find_all(class_='pi-data'):
            label_el = item.find(class_='pi-data-label')
            value_el = item.find(class_='pi-data-value')
            if label_el and value_el:
                k = label_el.get_text(separator=' ', strip=True)
                v = value_el.get_text(separator=' ', strip=True)
                info[k] = v

        # also try rows for older infobox table markup
        if not info:
            for tr in pinfo.find_all('tr'):
                th = tr.find('th')
                td = tr.find('td')
                if th and td:
                    k = th.get_text(separator=' ', strip=True)
                    v = td.get_text(separator=' ', strip=True)
                    info[k] = v

    data['infobox'] = info

    # determine winner/champion from common labels
    winner = None
    for key in ['Champions', 'Champion', 'Winner', 'Winners', 'Champion(s)']:
        if key in info:
            winner = info[key]
            break
    data['winner'] = winner

    # participants / teams — try infobox values first
    teams: List[Dict[str, str]] = []
    for key in ['Participants', 'Teams', 'Entrants', 'Participants/Teams']:
        if key in info:
            # split by common separators
            parts = [p.strip() for p in info[key].split('\n') if p.strip()]
            for p in parts:
                teams.append({'name': p})
            break

    # fallback: look for a section with participants/teams and collect links
    if not teams:
        for heading in soup.find_all(['h2','h3','h4']):
            htext = heading.get_text(strip=True).lower()
            if 'participant' in htext or 'teams' in htext or 'participants' in htext:
                nxt = heading.find_next(['ul','table','div'])
                if nxt:
                    for a in nxt.find_all('a'):
                        name = a.get_text(strip=True)
                        href = a.get('href')
                        if name and len(name) > 1 and not name.startswith('#'):
                            teams.append({'name': name, 'href': href})
                break

    data['teams'] = teams
    return data


def main():
    results = {}
    for name, urls in MAJORS.items():
        print('Buscando', name)
        parsed = None
        # try to fetch and parse page (this follows redirects)
        for page in urls:
            print('  tentando page', page)
            parsed = fetch_and_parse_page(page)
            if parsed:
                parsed['source_api'] = 'https://liquipedia.net/counterstrike/api.php?action=parse'
                break
            time.sleep(1)

        # fallback: try HTML scraping of provided urls
        if not parsed:
            for url in ['https://liquipedia.net/counterstrike/' + u for u in urls]:
                print('  tentando HTML', url)
                r = try_fetch(url)
                if r:
                    parsed = parse_liquipedia(r.text)
                    parsed['source_url'] = r.url
                    break
                time.sleep(1)

        if not parsed:
            results[name] = {'error': 'not found', 'tried': urls}
        else:
            results[name] = parsed

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('Salvo em', OUT)


if __name__ == '__main__':
    main()
