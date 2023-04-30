# riot-auth Copyright (c) 2022 Huba Tuba (floxay)
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.
from riot_auth import RiotAuth
import asyncio
import riot_auth
import requests
import json
# need to update for every riot client update
RiotAuth.RIOT_CLIENT_USER_AGENT = "06.08.00.872043 %s (Windows;10;;Professional, x64)"

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
    def __init__(self, region='kr', auth=None):
        self.region = region
        if auth is not None:
          self.username = auth['username']
          self.password = auth['password']
        else:
          raise ValueError
    
    async def fetch_store(self):
        await self.activate()
        store_uri = f'https://pd.{self.region}.a.pvp.net/store/v2/storefront/{self.auth.user_id}'
        header = {
          'X-Riot-Entitlements-JWT': f'{self.auth.entitlements_token}',
          'Authorization': f'Bearer {self.auth.access_token}'
        }
        res = requests.get(store_uri, headers=header)
        return res.json()
    
    async def activate(self):
        auth = riot_auth.RiotAuth()
        await auth.authorize(username=self.username, password=self.password)
        """print(f"Access Token Type: {auth.token_type}\n")
        print(f"Access Token: {auth.access_token}\n")
        print(f"Entitlements Token: {auth.entitlements_token}\n")
        print(f"User ID: {auth.user_id}")"""
        self.auth = auth
        # Reauth using cookies. Returns a bool indicating whether the reauth attempt was successful.
        # asyncio.run(auth.reauthorize())
      

if __name__ == '__main__':
    async def main():
      auth = {'username': '', 'password': ''}
      vf = ValStoreFetcher(auth=auth)
      res = await vf.fetch_store()
      res = res["SkinsPanelLayout"]["SingleItemOffers"]
      for uuid in res:
        print(get_weapon_info(uuid))
    asyncio.run(main())

    

    

    
  

    
