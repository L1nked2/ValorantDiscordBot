import urllib.request, json, os

def update_weapons(lang='ko-KR'):
  with urllib.request.urlopen("https://valorant-api.com/v1/weapons?language=ko-KR") as url:
      data = json.load(url)['data']
      path = os.path.join('.','db','weapons_kr.json')
      with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

if __name__ == '__main__':
  update_weapons()
  
  