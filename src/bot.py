import discord
from discord_token import discord_token
from discord.ext import commands

from .valstore import ValStoreFetcher, get_weapon_info

# discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# user infos
login_infos = dict()

@bot.event
async def on_ready():
    print(f'Login bot: {bot.user}')
 
@bot.command()
async def login(ctx, id, password):
    await ctx.channel.send(f'{ctx.author} login')
    _id_pwd_dict = {'username': id, 'password': password}
    login_infos[ctx.author.id] = _id_pwd_dict
    await ctx.message.delete()

@bot.command()
async def store(ctx):
    _auth_dict = login_infos[ctx.author.id]
    _fetcher = ValStoreFetcher(region="kr", auth=_auth_dict)
    item_uuids = await _fetcher.fetch_store()
    item_uuids = item_uuids["SkinsPanelLayout"]["SingleItemOffers"]
    result = ''
    for uuid in item_uuids:
      result += get_weapon_info(uuid)['displayName'] + '\n'
    await ctx.channel.send(f'{result}')

@bot.command()
async def echo(ctx, *, msg):
    await ctx.message.delete()
    await ctx.channel.send(f'{msg}')

def run_bot():
    bot.run(discord_token)