# riot-auth Copyright (c) 2022 Huba Tuba (floxay)
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.
from riot_auth import RiotAuth
import asyncio
import riot_auth
import requests
import json
# need to update for every riot client update
RiotAuth.RIOT_CLIENT_USER_AGENT = "06.08.00.872043 %s (Windows;10;;Professional, x64)"

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

class ValStoreFetcher():
    def __init__(self, region='kr', login_info:dict=None):
        self.region = region
        if login_info is None:
          raise ValueError
        self.login_info = login_info
        self.auths = dict()

    async def fetch_store(self):
        await self.activate()
        storefronts = dict()
        for nickname, auth in self.auths.items():
          store_url = f'https://pd.{self.region}.a.pvp.net/store/v2/storefront/{auth.user_id}'
          header = {
            'X-Riot-Entitlements-JWT': f'{auth.entitlements_token}',
            'Authorization': f'Bearer {auth.access_token}'
          }
          res_store = requests.get(store_url, headers=header)
          storefronts[nickname] = res_store.json()
        return storefronts
    
    async def activate(self):
        for id, password in self.login_info.items():
          auth = riot_auth.RiotAuth()
          await auth.authorize(username=id, password=password)
          header = {
            'Authorization': f'Bearer {auth.access_token}'
          }
          res_userinfo = requests.get(USERINFO_URL, headers=header)
          profile = res_userinfo.json()
          nickname = profile['acct']['game_name'] + '#' + profile['acct']['tag_line']
          self.auths[nickname] = auth
        return self.auths
        # Reauth using cookies. Returns a bool indicating whether the reauth attempt was successful.
        # asyncio.run(auth.reauthorize())
      

if __name__ == '__main__':
    async def main():
      auth = {'u': 'p'}
      vf = ValStoreFetcher(login_info=auth)
      res = await vf.fetch_store()
      res = res['fullname']["SkinsPanelLayout"]["SingleItemOffers"]
      for uuid in res:
        print(get_weapon_info(uuid))
    asyncio.run(main())

    

    

    
  

    
