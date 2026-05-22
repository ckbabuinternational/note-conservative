import json
import requests
import os
import feedparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 設定読み込み
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# dataフォルダ作成
Path('data').mkdir(exist_ok=True)

def save_json(filename, data):
    with open(f'data/{filename}', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'✅ {filename} を保存しました')


def collect_kokkai():
    print('🏛️ 国会議事録を収集中...')
    results = []
    keywords = config['search_keywords']['kokkai']

    for keyword in keywords:
        params = {
            'any': keyword,
            'from': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
            'until': datetime.now().strftime('%Y-%m-%d'),
            'maximumRecords': 10,
            'recordPacking': 'json'
        }
        try:
            res = requests.get(
                'https://kokkai.ndl.go.jp/api/speech',
                params=params,
                timeout=10
            )
            data = res.json()
            records = data.get('speechRecord', [])
            for r in records:
                results.append({
                    'keyword': keyword,
                    'date': r.get('date', ''),
                    'house': r.get('nameOfHouse', ''),
                    'committee': r.get('nameOfMeeting', ''),
                    'speaker': r.get('speaker', ''),
                    'role': r.get('speakerRole', ''),
                    'speech': r.get('speech', '')[:1000],
                    'url': r.get('meetingURL', '')
                })
            print(f'  [{keyword}] {len(records)}件取得')
        except Exception as e:
            print(f'  [{keyword}] エラー: {e}')

    save_json('kokkai.json', {
        'updated': datetime.now().isoformat(),
        'total': len(results),
        'records': results
    })


def collect_estat():
    print('📊 政府統計を収集中...')
    results = []
    keywords = config['search_keywords']['estat']
    api_key = config['estat_api_key']

    if not api_key:
        print('  ⚠️ e-Stat APIキーが未設定です')
        return

    for keyword in keywords:
        params = {
            'appId': api_key,
            'searchWord': keyword,
            'searchKind': '2',
            'lang': 'J',
            'limit': 10
        }
        try:
            res = requests.get(
                'https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList',
                params=params,
                timeout=10
            )
            data = res.json()
            stats = data.get('GET_STATS_LIST', {}) \
                       .get('DATALIST_INF', {}) \
                       .get('TABLE_INF', [])
            if isinstance(stats, dict):
                stats = [stats]
            for s in stats:
                results.append({
                    'keyword': keyword,
                    'id': s.get('@id', ''),
                    'title': s.get('TITLE', {}).get('$', '') if isinstance(s.get('TITLE'), dict) else s.get('TITLE', ''),
                    'org': s.get('GOV_ORG', {}).get('$', '') if isinstance(s.get('GOV_ORG'), dict) else s.get('GOV_ORG', ''),
                    'openDate': s.get('OPEN_DATE', ''),
                    'url': f"https://www.e-stat.go.jp/stat-search/files?tclass={s.get('@id', '')}"
                })
            print(f'  [{keyword}] {len(stats)}件取得')
        except Exception as e:
            print(f'  [{keyword}] エラー: {e}')

    save_json('estat.json', {
        'updated': datetime.now().isoformat(),
        'total': len(results),
        'records': results
    })


def collect_news():
    print('📰 ニュースを収集中...')
    results = []
    keywords = config['search_keywords']['news']
    api_key = config['news_api_key']

    if not api_key:
        print('  ⚠️ News APIキーが未設定です')
        return

    two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S')

    for keyword in keywords:
        params = {
            'q': keyword,
            'language': 'jp',
            'from': two_days_ago,
            'sortBy': 'publishedAt',
            'apiKey': api_key,
            'pageSize': 10
        }
        try:
            res = requests.get(
                'https://newsapi.org/v2/everything',
                params=params,
                timeout=10
            )
            data = res.json()
            articles = data.get('articles', [])
            for a in articles:
                results.append({
                    'keyword': keyword,
                    'title': a.get('title', ''),
                    'source': a.get('source', {}).get('name', ''),
                    'url': a.get('url', ''),
                    'publishedAt': a.get('publishedAt', ''),
                    'description': a.get('description', '')
                })
            print(f'  [{keyword}] {len(articles)}件取得')
        except Exception as e:
            print(f'  [{keyword}] エラー: {e}')

    save_json('news.json', {
        'updated': datetime.now().isoformat(),
        'total': len(results),
        'records': results
    })


def collect_houjin():
    print('🏢 法人番号データを収集中...')
    results = []
    api_key = config['houjin_api_key']

    # 調査対象法人リスト（config.jsonに追加可能）
    target_orgs = config.get('target_organizations', [
        '日本弁護士連合会',
        '全日本教職員組合',
        '移住者と連帯する全国ネットワーク'
    ])

    if not api_key:
        print('  ⚠️ 国税庁APIキーが未設定です（返事待ち）')
        return

    for org in target_orgs:
        params = {
            'id': api_key,
            'name': org,
            'type': '02',
            'output': 'json'
        }
        try:
            res = requests.get(
                'https://api.houjin-bangou.nta.go.jp/4/name',
                params=params,
                timeout=10
            )
            data = res.json()
            corporations = data.get('corporations', [])
            for c in corporations:
                results.append({
                    'name': c.get('name', ''),
                    'corporateNumber': c.get('corporateNumber', ''),
                    'kind': c.get('kind', ''),
                    'prefecture': c.get('prefectureName', ''),
                    'city': c.get('cityName', ''),
                    'address': c.get('streetNumber', ''),
                    'closeDate': c.get('closeDate', ''),
                    'url': f"https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo={c.get('corporateNumber', '')}"
                })
            print(f'  [{org}] {len(corporations)}件取得')
        except Exception as e:
            print(f'  [{org}] エラー: {e}')

    save_json('houjin.json', {
        'updated': datetime.now().isoformat(),
        'total': len(results),
        'records': results
    })


def collect_google_news():
    print('🔍 Google News RSSを収集中...')
    results = []
    keywords = config['search_keywords']['news']

    # 2日前の日時（タイムゾーン対応）
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)

    for keyword in keywords:
        url = (
            f"https://news.google.com/rss/search"
            f"?q={requests.utils.quote(keyword)}"
            f"+when:2d&hl=ja&gl=JP&ceid=JP:ja"
        )
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                # 日付パース
                try:
                    pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pub = datetime.now(timezone.utc)

                # 2日以内のみ取得
                if pub < two_days_ago:
                    continue

                # ソース名を抽出
                source = ''
                if hasattr(entry, 'source'):
                    source = entry.source.get('title', '')
                if not source and ' - ' in entry.title:
                    source = entry.title.rsplit(' - ', 1)[-1]

                # タイトルからソース名を除去
                title = entry.title
                if source and title.endswith(f' - {source}'):
                    title = title[:-(len(source) + 3)]

                results.append({
                    'keyword': keyword,
                    'title': title,
                    'source': source,
                    'url': entry.link,
                    'publishedAt': pub.isoformat(),
                    'description': entry.get('summary', '')
                })
                count += 1

            print(f'  [{keyword}] {count}件取得')

        except Exception as e:
            print(f'  [{keyword}] エラー: {e}')

    save_json('google_news.json', {
        'updated': datetime.now().isoformat(),
        'total': len(results),
        'records': results
    })


def main():
    print('=== データ収集開始 ===')
    collect_kokkai()
    collect_estat()
    collect_news()
    collect_google_news()
    collect_houjin()
    print('=== 全収集完了 ===')

if __name__ == '__main__':
    main()
