import discord
from discord_token import discord_token
from discord.ext import commands
from discord.ext import tasks
import os
import dill
from .valstore import ValStoreFetcher, UserInfo, get_weapon_info, set_riot_client_version
from .translator import Translator
from db_updator import update_weapons

# discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# auth dictionary, {discord_id: {riot_id: UserInfo}}
# saved on every hour
auths:dict[str, dict[str, UserInfo]]
auths = dict()
db_path = os.path.join('.', 'db', 'auths.pickle')

# translator
translator = Translator()

# valstore fetcher
fetcher = ValStoreFetcher()

# DB setter and getter
async def get_user_db():
    global auths
    # set initial pickle file
    if not os.path.isfile(db_path):
      await set_user_db()
    # get auth dictionary from pickle file
    with open(db_path, 'rb') as f:
      data = dill.load(f)
      for info in data:
        discord_id = info[0]
        riot_id = info[1]
        user_data = info[2]
        if not discord_id in auths:
           auths[discord_id] = dict()
        auths[discord_id][riot_id] = UserInfo()
        new_user_info = auths[discord_id][riot_id]
        new_user_info.import_data(user_data)
        #await new_user_info.reauthorize()
    print(f'user db loaded successfully')

async def set_user_db():
    global auths
    data = list()
    for discord_id, auth in auths.items():
      for riot_id, user_info in auth.items():
        data.append([discord_id, riot_id, user_info.export_data()])
    with open(db_path, 'wb') as f:
      dill.dump(data, f)

# reauthorize and save user info every hour
# also, delete empty discord_id entries to cleanup user info db
@tasks.loop(minutes=60)
async def save_user_info():
    set_riot_client_version()
    
    await set_user_db()
    print('reauthorize and save done')

@tasks.loop(hours=72)
async def update_weapon_db():
    update_weapons()
    print('Weapon DB updeated successfully')

@bot.event
async def on_ready():
    print(f'Login bot: {bot.user}')
    await get_user_db()
    await bot.change_presence(activity=discord.Game(name="!help | !도움"))
    save_user_info.start()
    update_weapon_db.start()

# TODO: update documentation
@bot.command(aliases=translator.get_command_aliases('help'))
async def help(ctx):
    help_text = f'```로그인\n!login id password\n!로그인 id password\n\n로그아웃\n!logout id\n!로그아웃 id\n\n연결된 계정목록 확인\n!accounts\n!계정목록\n\n상점 확인\n!store\n!상점\n!ㅅㅈ\n```'
    await ctx.channel.send(f'{help_text}')


@bot.command(aliases=translator.get_command_aliases('login'))
async def login(ctx, id, password):
    await ctx.message.delete()
    try:
      user_info = UserInfo()
      await user_info.authorize(id, password)
      await ctx.channel.send(f'{ctx.author} 에 {user_info.nickname} 계정이 연결되었습니다.')
      # save login
      if not (ctx.author.id in auths):
        # create new dict for first time login
        auths[ctx.author.id] = dict()
      auths[ctx.author.id][id] = user_info
    except:
      await ctx.channel.send(f'{ctx.author} 님, 로그인이 실패했습니다. 다시 시도해주세요.')

@bot.command(aliases=translator.get_command_aliases('logout'))
async def logout(ctx, id):
    await ctx.message.delete()
    try:
      del auths[ctx.author.id][id]
      if not bool(auths[ctx.author.id]):
        del auths[ctx.author.id]
      await ctx.channel.send(f'로그아웃이 완료되었습니다.')
    except:
      await ctx.channel.send(f'로그아웃이 실패했습니다. 아이디를 확인해주세요.')

# get user accounts currently logged in
@bot.command(aliases=translator.get_command_aliases('accounts'))
async def accounts(ctx):
    try:
      _auth_dict = auths[ctx.author.id]
      result = list()
      for riot_id, user_info in _auth_dict.items():
        result.append(user_info.nickname)
      await ctx.channel.send(f'계정 목록: {", ".join(result)}')
    except:
      await ctx.channel.send(f'{ctx.author} 에 연결된 계정이 없습니다. 로그인을 먼저 해주세요.')

@bot.command(aliases=translator.get_command_aliases('store'))
async def store(ctx):
    # try reauthorize existing user info
    drops:list[tuple[str,str]]
    drops = list()
    discord_id = ctx.author.id
    user_info:UserInfo
    for riot_id, user_info in auths[discord_id].items():
      res = await user_info.reauthorize()
      # reauthorization failed, save user info to drop
      if not res:
        drops.append((discord_id,riot_id))
    # drop user info that are not authorized
    for discord_id, riot_id in drops:
      del auths[discord_id][riot_id]
    # db cleanup
    if not bool(auths[discord_id]):
      del auths[discord_id]
    
    # fetch storefront information
    try:
      user_info_dict = auths[ctx.author.id]
      storefronts = await fetcher.fetch_store(user_info_dict)
      nicknames = list()
      for nickname, item_uuid in storefronts.items():
        header = f'{nickname}'
        nicknames.append(f'{nickname}')
        storefront = item_uuid["SkinsPanelLayout"]["SingleItemOffers"]
        costs = list()
        for offers in item_uuid["SkinsPanelLayout"]["SingleItemStoreOffers"]:
          cost_dict = offers['Cost']
          cost = str(list(cost_dict.values())[0]) + ' VP'
          costs.append(cost)
        embeds = list()
        for uuid, cost in zip(storefront, costs):
          weapon_info = get_weapon_info(uuid)
          embed=discord.Embed(title=weapon_info['displayName'], url=weapon_info['streamedVideo'], description=cost, color=0x40e243)
          embed.set_thumbnail(url=weapon_info['displayIcon'])
          embeds.append(embed)
        await ctx.send(content=header, embeds=embeds)
      print(f'{nicknames} visited store')
    except KeyError:
      await ctx.channel.send(f'{ctx.author} 에 연결된 계정이 없습니다. 로그인을 먼저 해주세요')

@bot.command()
@commands.is_owner()
async def echo(ctx, *, msg):
    await ctx.message.delete()
    await ctx.channel.send(f'{msg}')

@bot.command()
@commands.is_owner()
async def force_save(ctx):
    await set_user_db()

@bot.command()
@commands.is_owner()
async def force_update(ctx):
    await save_user_info()

"""
Test fields
"""
@bot.command()
@commands.is_owner()
async def teststore(ctx):
    try:
      user_info_dict = auths[ctx.author.id]
      storefronts = await fetcher.fetch_store(user_info_dict)
      nicknames = list()
      for nickname, item_uuid in storefronts.items():
        print(item_uuid)
      print(f'{nicknames} visited store')
    except KeyError:
      await ctx.channel.send(f'{ctx.author} no accounts available')

def run_bot():
    bot.run(discord_token)