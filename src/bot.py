import discord
from discord_token import discord_token
from discord.ext import commands
from discord.ext import tasks
import os
import dill
from .valstore import ValStoreFetcher, UserInfo, get_weapon_info, set_riot_client_version
from .translator import Translator

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
        await new_user_info.reauthorize()
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
@tasks.loop(minutes=60)
async def reauthorize_and_save_user_info():
    set_riot_client_version()
    global auths
    drops = list[tuple[str,str]]
    drops = list()
    for discord_id, auth in auths.items():
      for riot_id, user_info in auth.items():
        res = await user_info.reauthorize()
        # reauthorization failed, save user info to drop
        if not res:
          drops.append((discord_id,riot_id))
    
    # drop user info that are not authorized
    for discord_id, riot_id in drops:
      del auths[discord_id][riot_id]
    # db cleanup
    drops = list()
    for discord_id, auth in auths.items():
      if not bool(auth):
        drops.append(discord_id)
    for discord_id in drops:
      del auths[discord_id]

    await set_user_db()
    print('reauthorize and save done')

@bot.event
async def on_ready():
    print(f'Login bot: {bot.user}')
    await get_user_db()
    await bot.change_presence(activity=discord.Game(name="!help | !도움"))
    reauthorize_and_save_user_info.start()

# TODO: update documentation
@bot.command(aliases=translator.get_command_aliases('help'))
async def help(ctx):
    help_text = f'```\n!login id password\n!로그인 id password\n\n!logout id\n!로그아웃 id\n\n!accounts\n!계정목록\n\n!store\n!상점\n```'
    await ctx.channel.send(f'{help_text}')


@bot.command(aliases=translator.get_command_aliases('login'))
async def login(ctx, id, password):
    await ctx.message.delete()
    try:
      user_info = UserInfo()
      await user_info.authorize(id, password)
      await ctx.channel.send(f'{ctx.author} login successful, {user_info.nickname} logged in')
      # save login
      if not (ctx.author.id in auths):
        # create new dict for first time login
        auths[ctx.author.id] = dict()
      auths[ctx.author.id][id] = user_info
    except:
      await ctx.channel.send(f'{ctx.author} login failed, check your id and password')

@bot.command(aliases=translator.get_command_aliases('logout'))
async def logout(ctx, id):
    try:
      del auths[ctx.author.id][id]
      if not bool(auths[ctx.author.id]):
        del auths[ctx.author.id]
      await ctx.channel.send(f'logout successful')
    except:
      await ctx.channel.send(f'logout failed, check your id')

# get user accounts currently logged in
@bot.command(aliases=translator.get_command_aliases('accounts'))
async def accounts(ctx):
    try:
      _auth_dict = auths[ctx.author.id]
      result = list()
      for riot_id, user_info in _auth_dict.items():
        result.append(user_info.nickname)
      await ctx.channel.send(f'accounts: {", ".join(result)}')
    except:
      await ctx.channel.send(f'{ctx.author} no accounts available')

@bot.command(aliases=translator.get_command_aliases('store'))
async def store(ctx):
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
      await ctx.channel.send(f'{ctx.author} no accounts available')

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
    await reauthorize_and_save_user_info()

"""
Test fields
"""
@bot.command()
@commands.is_owner()
async def teststore(ctx):
    try:
      user_info_dict = auths[ctx.author.id]
      storefronts = await fetcher.fetch_store(user_info_dict)
      for nickname, item_uuid in storefronts.items():
        await ctx.channel.send(f'{nickname}')
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
        await ctx.send(embeds=embeds)
    except KeyError:
      await ctx.channel.send(f'{ctx.author} no accounts available')

def run_bot():
    bot.run(discord_token)