# riot-auth Copyright (c) 2022 Huba Tuba (floxay)
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.
from riot_auth import RiotAuth
import asyncio
import riot_auth
import requests
import json
import urllib

# set riot client version
with urllib.request.urlopen("https://valorant-api.com/v1/version") as url:
  riot_client_build = json.load(url)['data']['riotClientBuild']
  RiotAuth.RIOT_CLIENT_USER_AGENT = f'{riot_client_build} %s (Windows;10;;Professional, x64)'

USERINFO_URL = f'https://auth.riotgames.com/userinfo'

# translate item uuid to name and icons
def get_weapon_info(uuid):
    with open('./db/weapons_kr.json', encoding='utf-8') as f:
      weapons = json.load(f)
    result = None
    for weapon in weapons:
        for single_skin in weapon['skins']:
            # max level video
            video_url = single_skin['levels'][-1]['streamedVideo']
            item = single_skin['levels'][0]
            if item['uuid'] == uuid:
                result = item
                result['streamedVideo'] = video_url
    del result['levelItem']
    del result['assetPath']
    return result

class UserInfo(riot_auth.RiotAuth):
    def __init__(self, **kwargs):
      super().__init__()
      self.entries = ['access_token', 'scope', 'id_token', 'token_type', 'expires_at', 'user_id', 'entitlements_token']
    @property
    def nickname(self):
      header = {
        'Authorization': f'Bearer {self.access_token}'
      }
      res_userinfo = requests.get(USERINFO_URL, headers=header)
      profile = res_userinfo.json()
      nickname = profile['acct']['game_name'] + '#' + profile['acct']['tag_line']
      return nickname
    
    def export_data(self):
      data = dict()
      data['_cookies'] = self._cookie_jar._cookies
      for entry in self.entries:
        data[entry] = getattr(self,entry)
      return data
    
    def import_data(self, data:dict):
      self._cookie_jar._cookies = data['_cookies']
      for entry in self.entries:
        setattr(self, entry, data[entry])
      return
  
class ValStoreFetcher():
    def __init__(self, region='kr'):
        self.region = region

    async def fetch_store(self, auths:dict[str, UserInfo]):
        storefronts = dict()
        for user_id, auth in auths.items():
          store_url = f'https://pd.{self.region}.a.pvp.net/store/v2/storefront/{auth.user_id}'
          header = {
            'X-Riot-Entitlements-JWT': f'{auth.entitlements_token}',
            'Authorization': f'Bearer {auth.access_token}'
          }
          res_store = requests.get(store_url, headers=header)
          nickname = auth.nickname
          storefronts[nickname] = res_store.json()
        return storefronts
        
if __name__ == '__main__':
    async def main():
      user_info_dict = dict()
      vf = ValStoreFetcher()
      cred = ('u', 'p')
      user_info = UserInfo()
      await user_info.authorize(*cred)
      user_info_dict[user_info.user_id] = user_info
      res = await vf.fetch_store(user_info_dict)
      res = res[f'{user_info.nickname}']["SkinsPanelLayout"]["SingleItemOffers"]
      for uuid in res:
        print(get_weapon_info(uuid))
    asyncio.run(main())

    

    

    
  

    
