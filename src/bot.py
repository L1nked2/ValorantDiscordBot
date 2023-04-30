import discord
from discord_token import discord_token
from discord.ext import commands

from .valstore import ValStoreFetcher, get_weapon_info
from .translator import Translator

# discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# user infos
login_info = dict()

# translator
translator = Translator()

@bot.event
async def on_ready():
    print(f'Login bot: {bot.user}')
 
@bot.command()
async def login(ctx, id, password):
    await ctx.message.delete()
    # save login
    if ctx.author.id in login_info:
      login_info[ctx.author.id][id] = password
    else:
      login_info[ctx.author.id] = dict()
      login_info[ctx.author.id][id] = password
    try:
      _auth_dict = {id: password}
      _fetcher = ValStoreFetcher(region="kr", login_info=_auth_dict)
      # only one auth info
      auths = await _fetcher.activate()
      await ctx.channel.send(f'{ctx.author} login successful, {", ".join(auths.keys())} logged in')
    except:
      await ctx.channel.send(f'{ctx.author} login failed, check your id and password')

@bot.command()
async def logout(ctx, id):
    try:
      del login_info[ctx.author.id][id]
      await ctx.channel.send(f'logout successful')
    except:
      await ctx.channel.send(f'logout failed, check your id')


@bot.command(aliases=translator.get_command_aliases('accounts'))
async def accounts(ctx):
    try:
      _auth_dict = login_info[ctx.author.id]
      _fetcher = ValStoreFetcher(region="kr", login_info=_auth_dict)
      auths = await _fetcher.activate()
      
      await ctx.channel.send(f'accounts: {", ".join(auths.keys())}')
    except:
      await ctx.channel.send(f'{ctx.author} no accounts available')

@bot.command(aliases=translator.get_command_aliases('store'))
async def store(ctx):
    _auth_dict = login_info[ctx.author.id]
    _fetcher = ValStoreFetcher(region="kr", login_info=_auth_dict)
    storefronts = await _fetcher.fetch_store()
    result = ''
    for nickname, item_uuid in storefronts.items():
      result += f'{nickname}\n'
      storefront = item_uuid["SkinsPanelLayout"]["SingleItemOffers"]
      for uuid in storefront:
        result += get_weapon_info(uuid)['displayName'] + '\n'
      result += '\n'
    await ctx.channel.send(f'{result}')

@bot.command()
async def echo(ctx, *, msg):
    await ctx.message.delete()
    await ctx.channel.send(f'{msg}')

def run_bot():
    bot.run(discord_token)