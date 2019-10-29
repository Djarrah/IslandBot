import json
import os
from datetime import datetime, timedelta
from random import randint
import discord
from discord.ext import commands, tasks


# Definitions
TOKEN = os.environ["ACCESS_TOKEN"]
bot = commands.Bot(command_prefix="!")

ROLE_CONVERTER = commands.RoleConverter()
CHANNEL_CONVERTER = commands.TextChannelConverter()
CATEGORY_CONVERTER = commands.CategoryChannelConverter()
MEMBER_CONVERTER = commands.MemberConverter()


# JSON support
def datetime_parser(value):
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = datetime_parser(v)
    elif isinstance(value, list):
        for index, row in enumerate(value):
            value[index] = datetime_parser(row)
    elif isinstance(value, str) and value:
        try:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
        except (ValueError, AttributeError):
            pass
    return value


with open("data.json") as json_file:
    json_data = json.load(json_file, object_hook=datetime_parser)


def json_dump(dest):
    with open(dest, "w") as json_write:
        json.dump(json_data, json_write, indent=4, default=str)


# Checks
def in_channel(channel_name):
    ''' Checks if command is sent from a specific channel '''
    def predicate(ctx):
        return ctx.channel.name == channel_name
    return commands.check(predicate)


def in_channels(channel_list):
    ''' Checks if command is sent from a channel in a list '''
    def predicate(ctx):
        return ctx.channel.name in channel_list
    return commands.check(predicate)


# Events
@bot.event
async def on_ready():
    print(f'{bot.user} connected to discord')
    backup.start()


# Background tasks
@tasks.loop(hours=3.0)
async def backup():
    await bot.wait_until_ready()
    channel = bot.get_channel('''your backup channel id here''')
    await channel.send(file=discord.File("data.json"))
    print("Backup successful at " + str(datetime.now()))


# Commands
@bot.command(aliases=["r"], help="Roll from 1 to 3 d6")
async def roll(ctx, amount: int):
    results = []
    for i in range(amount):
        results.append(str(randint(1, 6)))
    message = f"{ctx.author.mention} Results: " + " ".join(results)
    await ctx.send(message)


@bot.command(
    aliases=["go"],
    help="Travel to a near destination. 5 min User Cooldown"
)
async def walk(ctx, destination=None):
    current_location = ctx.channel.name
    if current_location in json_data["locked locations"]:
        await ctx.message.add_reaction("🔒")
        return
    group = ctx.channel.category.name
    # Checks if current location has special movement rules
    if group == "Private quarters":
        group = "Hotel Eclipse"
        current_location = "bedroom"
    elif group == "Mediterranean Sea" or group == "Outdoors":
        group = current_location
    elif group not in json_data["available destinations"]:
        await ctx.send("You can't move from here")
        return
    # Creates a list of available destinations
    av_dest = []
    for i in json_data["available destinations"][group]:
        if (
            i != current_location and
            i not in json_data["forbidden locations"]
        ):
            av_dest.append(i)

    if destination is None:
        # Writes the list in a message
        if not bool(av_dest):
            message = "There is currently no destination you can reach by foot"
        else:
            message = "Where to?\n" + "\n".join(av_dest)
        await ctx.send(message)
    elif destination not in av_dest:
        await ctx.message.add_reaction("❌")
    else:
        # Checks for cooldown
        try:
            last_move = (
                datetime.now() - json_data["walk cooldown"][ctx.author.id]
            )
        except KeyError:
            last_move = None
        # Moves if not on CD
        if last_move is None or last_move.seconds > 300:
            # Redirects to personal bedroom
            if destination == "bedroom":
                try:
                    destination = json_data["room owners"][ctx.author.id]
                except KeyError:
                    await ctx.send(
                        f"You don't have a bedroom, {ctx.author.mention}"
                    )
                    return

            destination = await CHANNEL_CONVERTER.convert(ctx, destination)
            await destination.set_permissions(ctx.author, read_messages=True)
            await ctx.channel.set_permissions(ctx.author, read_messages=False)
            await ctx.message.delete()
            await ctx.send(f"{ctx.author.name} moved to {destination.name}")
            json_data["walk cooldown"][ctx.author.id] = datetime.now()
            json_dump("data.json")
            print(f"{ctx.author.name} moved to {destination.name}")
        else:
            await ctx.message.add_reaction("🕒")


@bot.command(
    aliases=["car", "taxi"],
    help="Travel to a far place. 1 hour User Cooldown"
)
@in_channels(json_data["bus destinations"])
async def bus(ctx, destination=None):
    if ctx.channel.name in json_data["locked locations"]:
        await ctx.message.add_reaction("🔒")
        return
    # Creates a list ov available destinations
    av_dest = []
    for i in json_data["bus destinations"]:
        if i != ctx.channel.name:
            av_dest.append(i)

    if destination is None:
        # Sends a list of bus destinations
        if not bool(av_dest):
            message = "Long-distance travel is disabled at the moment."
        else:
            message = "List of far destinations:\n" + "\n".join(av_dest)
        await ctx.send(message)
    elif destination in av_dest:
        # Checks for cooldown
        try:
            last_move = (
                datetime.now() - json_data["bus cooldown"][ctx.author.id]
            )
        except KeyError:
            last_move = None
        # Moves if not on CD
        if last_move is None or last_move.seconds > 3600:
            destination = await CHANNEL_CONVERTER.convert(ctx, destination)
            await destination.set_permissions(ctx.author, read_messages=True)
            await ctx.channel.set_permissions(ctx.author, read_messages=False)
            await ctx.message.delete()
            await ctx.send(
                f"{ctx.author.name} took a ride to {destination.name}"
            )
            json_data["bus cooldown"][ctx.author.id] = datetime.now()
            json_dump("data.json")
            print(f"{ctx.author.name} took a ride to {destination.name}")
        else:
            await ctx.message.add_reaction("🕒")
    else:
        await ctx.message.add_reaction("❌")


@bot.command(help="Use your eyes. 60 seconds Channel Cooldown")
@commands.cooldown(1, 60, commands.BucketType.channel)
async def look(ctx):
    filepath = os.path.join("media", "look", f"{ctx.channel.name}.jpg")
    if os.path.isfile(filepath):
        await ctx.message.delete()
        await ctx.send(file=discord.File(filepath))
    else:
        await ctx.message.add_reaction("❌")


@bot.command(
    aliases=["hide", "unhide", "reveal"],
    help="Hide or reveal a location channel (Default current)"
)
@commands.has_role("Game Master")
async def flip(ctx, location=None):
    await ctx.message.delete()
    if location is None:
        location = ctx.channel.name
    if location in json_data["forbidden locations"]:
        json_data["forbidden locations"].remove(location)
        await ctx.send("Location revealed")
        print(f"{location} was revealed")
    else:
        json_data["forbidden locations"].append(location)
        await ctx.send("Location hidden")
        print(f"{location} was hidden")
    json_dump("data.json")


@bot.command(
    aliases=["yesbus", "nobus"],
    help="Removes a location from the bus list, or adds it."
)
@commands.has_role("Game Master")
async def flipbus(ctx, location=None):
    await ctx.message.delete()
    if location is None:
        location = ctx.channel.name
    if location in json_data["bus destinations"]:
        json_data["bus destinations"].remove(location)
        await ctx.send(f"{location} removed from bus network")
        print(f"{location} removed from bus network")
    else:
        json_data["bus destinations"].append(location)
        await ctx.send(f"{location} added to bus network")
        print(f"{location} added to bus network")
    json_dump("data.json")


@bot.command(
    aliases=["lock", "unlock", "open", "close"],
    help="Lock or unlock player movement from channel"
)
@commands.has_role("Game Master")
async def flipmove(ctx, location=None):
    await ctx.message.delete()
    if location is None:
        location = ctx.channel.name
    if location in json_data["locked locations"]:
        json_data["locked locations"].remove(location)
        await ctx.send("Location opened, it is now possible to move from it")
        print(f"{location} was unlocked")
    else:
        json_data["locked locations"].append(location)
        await ctx.send("Location closed, it is no longer possible to leave it")
        print(f"{location} was locked")
    json_dump("data.json")


@bot.command(
    aliases=["teleport", "tp"],
    help="Forcefully move a player from current location"
)
@commands.has_role("Game Master")
async def move(
    ctx, user: commands.MemberConverter,
    location: commands.TextChannelConverter,
    via="walk"
):
    await location.set_permissions(user, read_messages=True)
    await ctx.channel.set_permissions(user, read_messages=False)
    await ctx.message.delete()
    await ctx.send(f"{user.name} moved to {location.name}")
    print(f"{user.name} was moved to {location.name}")
    if via is "walk":
        json_data["walk cooldown"][user.id] = datetime.now()
    elif via is "bus":
        json_data["bus cooldown"][user.id] = datetime.now()
    else:
        return
    json_dump("data.json")


@bot.command(aliases=["check-in"], help="Create a room for a player")
@commands.has_role("Game Master")
async def spawnroom(ctx, user: commands.MemberConverter):
    if user.id not in json_data["room owners"]:
        await ctx.message.delete()
        rooms = await CATEGORY_CONVERTER.convert(ctx, "Private quarters")
        number = len(json_data["room owners"])+1
        room = await rooms.create_text_channel(f"room-{number}")
        json_data["room owners"][user.id] = room.name
        json_dump("data.json")
        await ctx.send(f"{user.mention}, your room is now ready.")
        print(f"Created room for {user.name}")


@bot.command(help="Temporarly disables the bus, or re-enable it.")
@commands.has_role("Game Master")
async def pausebus(ctx):
    if bool(json_data["bus destinations"]):
        json_data["bus state"] = json_data["bus destinations"]
        json_data["bus destinations"] = []
        json_dump("data.json")
        await ctx.send("Bus disabled")
        print("Bus disabled")
    else:
        json_data["bus destinations"] = json_data["bus state"]
        json_dump("data.json")
        await ctx.send("Bus enabled")
        print("Bus enabled")
    await ctx.message.delete()


@bot.command(help="Say something")
@commands.has_role("Game Master")
async def say(ctx, location: commands.TextChannelConverter, *args):
    message = " ".join(args[:])
    await location.send(message)


@bot.command(aliases=["send"], help="Send a file from the bot folder here")
@commands.has_role("Game Master")
async def sendfile(ctx, filepath):
    await ctx.message.delete()
    filetosend = discord.File(filepath)
    await ctx.send(file=filetosend)


bot.run(TOKEN)
