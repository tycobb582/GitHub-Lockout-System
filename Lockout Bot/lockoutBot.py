import discord
from discord import app_commands, Message, TextChannel
from discord.ext import commands
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv


workingDirectory = os.getcwd()
workingDirectory.replace("\\\\", "\\")
dotenv_path = os.path.join(workingDirectory, ".env")
load_dotenv(dotenv_path=dotenv_path)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_ID = os.environ.get("BOT_ID")
SHEET_ID = os.environ.get("SHEET_ID")
SHEETS_API_KEY = os.environ.get("SHEETS_API_KEY")
GUILD_ID = os.environ.get("GUILD_ID")
BOT_GUILD = discord.Object(GUILD_ID)
# IDs for the channel that the bot posts in and the channel the webhook posts in
BOT_CHANNEL = os.environ.get("BOT_CHANNEL")
WEBHOOK_CHANNEL = os.environ.get("WEBHOOK_CHANNEL")

sheets = build('sheets', 'v4', developerKey=SHEETS_API_KEY).spreadsheets()


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.messages = True
bot = commands.Bot(command_prefix='/', intents=intents)
botChannel: TextChannel = None
maintainedMessage: Message = None


def scanSheet():
    global timeSinceLastScan
    result = sheets.values().get(spreadsheetId=SHEET_ID, range="Sheet1").execute()
    values = result.get('values', [])
    checkedOut = []
    for i in range(1, len(values)):
        data = values[i]
        if data[1] == "Yes":
            lockoutInfo = (data[0], data[2])
            lockoutInfo = " : ".join(lockoutInfo)
            checkedOut.append(lockoutInfo)
    return checkedOut


def constructLockoutPost(checkoutList):
    output = ""
    if not checkoutList:
        output = "```No files checked out.```"
    else:
        output = "```" + "\n".join(checkoutList) + "```"
    return output



@bot.event
async def on_ready():
    global botChannel, maintainedMessage
    print(f"Logged on as {bot.user}!")
    botChannel = await bot.fetch_channel(BOT_CHANNEL)
    channelMessages = [message async for message in botChannel.history(limit=100)]
    checkoutList = scanSheet()
    output = constructLockoutPost(checkoutList)
    if len(channelMessages) >= 1:
        maintainedMessage = channelMessages[len(channelMessages) - 1]
        print("Found bot message already posted.")
    if not maintainedMessage:
        print("Creating bot message.")
        maintainedMessage = await botChannel.send(content=output)
    else:
        maintainedMessage = await maintainedMessage.edit(content=output)


@bot.event
async def on_message(message: Message):
    global botChannel, maintainedMessage
    if message.channel.id == WEBHOOK_CHANNEL:   # Monitor the webhook channel
        if message.content.find("NOTIFY RESCAN") > -1:
            print("Received rescan notification from webhook.")
            checkoutList = scanSheet()
            output = constructLockoutPost(checkoutList)
            maintainedMessage = await maintainedMessage.edit(content=output)


@bot.hybrid_command(name="sync", description="Syncs all slash commands. Can only be called by admins.", guild=BOT_GUILD)
@commands.has_permissions(administrator=True)
async def sync(ctx: commands.Context):
    bot.tree.clear_commands(guild=BOT_GUILD)
    synced = await bot.tree.sync()
    reply = await ctx.send(f"Synced {len(synced)} commands.")
    await reply.delete(delay=2)


@bot.hybrid_command(name="list-locked-by-user", description="Lists all the files currently checked out by the given user.", guild=BOT_GUILD)
@app_commands.describe(user="The Discord username of the person who's locked files you want to see.")
async def listByUser(ctx: commands.Context, user: discord.Member):
    # Look for checked out files, then the info
    username = user.display_name
    result = sheets.values().get(spreadsheetId=SHEET_ID, range="Sheet1").execute()
    values = result.get('values', [])
    checkedOut = []
    for i in range(1, len(values)):
        data = values[i]
        if data[1] == "Yes" and data[2] == username:
            checkedOut.append(data[0])
            print(data[0])
    output = f"Files checked out by {username}:\n```" + " \n".join(checkedOut) + "```"
    if not checkedOut:
        reply = await ctx.send(f"No files locked out by {username}.")
        await reply.delete(delay=60)
        return
    reply = await ctx.send(output)
    await reply.delete(delay=60)


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
