import urllib.request, json

if __name__ == '__main__':
  with urllib.request.urlopen("https://valorant-api.com/v1/weapons?language=ko-KR") as url:
      data = json.load(url)['data']
      with open('./db/weapons_kr.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)