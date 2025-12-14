#!/usr/bin/env python3
"""Busca vencedores dos Majors 2015 no HLTV e atualiza data/majors-2015.json
"""
import json
import re
import time
from typing import Dict

import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'cstory-hltv-fetcher/1.0 (+https://github.com)'}
BASE = 'https://www.hltv.org'

QUERIES = {
    'Katowice 2015': 'ESL One Katowice 2015',
    'Cologne 2015': 'ESL One Cologne 2015',
    'Cluj-Napoca 2015': 'DreamHack Cluj-Napoca 2015'
}

DATA_IN = 'data/majors-2015.json'
DATA_OUT = 'data/majors-2015-hltv.json'


def search_event(query: str) -> str | None:
    # First try HLTV internal search (may be JS-heavy)
    url = BASE + '/search'
    try:
        r = requests.get(url, params={'query': query}, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/events/'):
                return BASE + href
    except Exception:
        pass

    # Fallback: DuckDuckGo HTML search (no JS) for site:hltv.org
    try:
        ddg = 'https://html.duckduckgo.com/html/'
        q = f"site:hltv.org {query}"
        r2 = requests.post(ddg, data={'q': q}, headers=HEADERS, timeout=10)
        r2.raise_for_status()
        s2 = BeautifulSoup(r2.text, 'lxml')
        for a in s2.find_all('a', href=True):
            href = a['href']
            if 'hltv.org/events/' in href:
                # link may be absolute or relative; ensure absolute
                if href.startswith('http'):
                    return href
                return BASE + href
    except Exception:
        pass

    # Fallback 2: Bing HTML search
    try:
        bing = 'https://www.bing.com/search'
        q2 = f"site:hltv.org/events {query}"
        r3 = requests.get(bing, params={'q': q2}, headers=HEADERS, timeout=10)
        r3.raise_for_status()
        s3 = BeautifulSoup(r3.text, 'lxml')
        for a in s3.find_all('a', href=True):
            href = a['href']
            if 'hltv.org/events/' in href:
                if href.startswith('http'):
                    return href
                return BASE + href
    except Exception:
        pass

    return None


def extract_winner_from_event_html(html: str) -> str | None:
    soup = BeautifulSoup(html, 'lxml')
    # 1) JSON-LD
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            j = json.loads(script.string or '{}')
            if isinstance(j, dict):
                if 'winner' in j:
                    w = j['winner']
                    if isinstance(w, dict) and 'name' in w:
                        return w['name']
                    if isinstance(w, str):
                        return w
        except Exception:
            continue
    txt = html
    # 2) regex: look for 'Winner' label followed by link
    m = re.search(r'Winner[s]?:[^<]{0,80}<a[^>]*>([^<]+)</a>', txt, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 3) look for headings like "Final" and next link text
    for h in soup.find_all(['h2', 'h3', 'h4']):
        if 'final' in h.get_text(strip=True).lower():
            nxt = h.find_next()
            if nxt:
                a = nxt.find('a')
                if a and a.text:
                    return a.text.strip()
    # 4) some pages show winner in a div with class containing 'event-team' or 'team-box'
    for div in soup.find_all(True, class_=re.compile(r'(team|winner|event).*', re.IGNORECASE)):
        a = div.find('a')
        if a and a.text:
            # heuristic: team name likely short
            name = a.text.strip()
            if len(name) < 40:
                return name
    # 5) fallback: try title metadata
    title = soup.find('title')
    if title and '-' in title.text:
        parts = [p.strip() for p in title.text.split('-')]
        # HLTV title often: "Event - Results - HLTV.org"
        # not reliable, skip
    return None


def main():
    out = {}
    try:
        with open(DATA_IN, 'r', encoding='utf-8') as f:
            base = json.load(f)
    except Exception as e:
        print('Erro ao ler', DATA_IN, e)
        return

    for key, query in QUERIES.items():
        print('Buscando HLTV para', key)
        event_url = search_event(query)
        if not event_url:
            print('  não encontrado via busca')
            out[key] = {'hltv_event_url': None, 'hltv_winner': None}
            continue
        print('  event url:', event_url)
        try:
            r = requests.get(event_url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            winner = extract_winner_from_event_html(r.text)
            print('  winner:', winner)
            out[key] = {'hltv_event_url': event_url, 'hltv_winner': winner}
            # merge to base
            if key in base:
                base[key]['hltv_event_url'] = event_url
                base[key]['hltv_winner'] = winner
        except Exception as e:
            print('  erro ao buscar evento', e)
            out[key] = {'hltv_event_url': event_url, 'hltv_winner': None}
        time.sleep(1)

    # save separate file and update main
    with open(DATA_OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with open(DATA_IN, 'w', encoding='utf-8') as f:
        json.dump(base, f, ensure_ascii=False, indent=2)
    print('Atualizado', DATA_IN, 'e salvo', DATA_OUT)

if __name__ == '__main__':
    main()
