import discord
from discord_token import discord_token
from discord.ext import commands
from discord.ext import tasks
import os
import dill
from .valstore import ValStoreFetcher, UserInfo, get_weapon_info
from .translator import Translator

# discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

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

async def set_user_db():
    global auths
    data = list()
    for discord_id, auth in auths.items():
      for riot_id, user_info in auth.items():
        data.append([discord_id, riot_id, user_info.export_data()])
    with open(db_path, 'wb') as f:
      dill.dump(data, f)

# reauthorize and save user info every hour
@tasks.loop(hours=1)
async def reauthorize_and_save_user_info():
    global auths
    for discord_id, auth in auths.items():
      for riot_id, user_info in auth.items():
        await user_info.reauthorize()
    await set_user_db()

@bot.event
async def on_ready():
    print(f'Login bot: {bot.user}')
    await get_user_db()
    reauthorize_and_save_user_info.start()

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
      result = ''
      for nickname, item_uuid in storefronts.items():
        result += f'{nickname}\n'
        storefront = item_uuid["SkinsPanelLayout"]["SingleItemOffers"]
        for uuid in storefront:
          result += get_weapon_info(uuid)['displayName'] + '\n'
        result += '\n'
      await ctx.channel.send(f'{result}')
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

def run_bot():
    bot.run(discord_token)