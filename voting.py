import asyncio
import json
import time
import discord
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional
from discord import Role, Member
from discord.ext import commands
from discord.ext.commands import Context, Greedy

# TODO cancel vote
# TODO ezvote

with open("token.txt", 'r') as f:
    TOKEN = f.read().strip()

with open("admins.json", 'r') as f:
    admins = json.load(f)

bot = commands.Bot(command_prefix="¦")

bot.remove_command('help')

votes = {}
polls = {}

emojis = ['0⃣', '1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣', '🔟']


def is_admin(ctx: Context):
    return discord.utils.get(ctx.author.roles, id=admins[str(ctx.guild.id)]) is not None


def is_owner(ctx: Context):
    return ctx.author == ctx.guild.owner


@bot.command()
async def help(ctx: Context):
    await ctx.send("`¦admin @Role` - set admin role which can start votes.\n"
                   "`¦start @Role Question Option1 Option2... timeout` - start vote.")


@bot.command()
@commands.check(is_owner)
async def admin(ctx: Context, role: Role):
    admins[ctx.guild.id] = role.id
    with open("admins.json", 'w') as f:
        json.dump(admins, f)


@dataclass(frozen=True, eq=True)
class Poll:
    author: Member
    role: Role
    question: str
    options: List[str]


@bot.command()
@commands.check(is_admin)
async def start(ctx: Context, role: Role, question, *args):
    msg = await ctx.send("Start vote?")
    poll = Poll(ctx.author, role, question, args)
    polls[poll] = {"results": [], "votes": 0, "msg": msg}
    await msg.add_reaction('👍')
    _, user = await bot.wait_for("reaction_add", check=lambda r, u: r.emoji == "👍" and r.message.id == msg.id and u == poll.author)
    for member in user.voice.channel.members:
        if poll.role in member.roles and member != poll.author:
            await member.send(poll.question)
            options = ""
            for i, option in enumerate(poll.options):
                options += f"{emojis[i]} - {option}\n"
            options += "Please select your option in the reactions and then click the ✅ reaction."
            vote = await member.send(options)

            for num in range(i + 1):
                await vote.add_reaction(f"{emojis[num]}")

            await vote.add_reaction(f"✅")

            votes[vote.id] = poll
            polls[poll]["votes"] += 1
    try:
        await bot.wait_for("reaction_remove", timeout=10, check=lambda r, u: r.emoji == "👍" and r.message.id == msg.id and u == bot.user)
    except asyncio.TimeoutError:
        print("Timeout")
    r = polls[poll]["results"]
    results = Counter({i: 0 for i in range(len(poll.options))})
    for result in r:
        num = emojis.index(result.emoji)
        results[num] += 1

    winner = results.most_common()
    if winner[0][1] == winner[1][1]:
        await poll.author.send(poll.question)
        options = ""
        for i, option in enumerate(poll.options):
            if winner[0][1] != winner[i][1]:
                break
            options += f"{emojis[i]} - {option}\n"
        options += "Please select your option in the reactions and then click the ✅ reaction."

        msg = await poll.author.send(options)

        for num in range(i + 1):
            await msg.add_reaction(f"{emojis[num]}")

        await msg.add_reaction(f"✅")

        while True:
            reaction, _ = await bot.wait_for("reaction_add", check=lambda r, u: r.emoji == "✅" and r.message.id == msg.id and u == poll.author)

            v = []
            for reaction in reaction.message.reactions:
                if reaction.count == 2 and reaction.emoji != "✅":
                    v.append(reaction)
            print(v)
            if len(v) == 1:
                vote = emojis.index(v[0].emoji)
                results[vote] += 1
                break

    winner = results.most_common(1)[0][0]

    result_display = "\n".join([f"{k} - {poll.options[k]}: {v} votes" for k, v in results.items()])
    results = f"The winner is {winner} - {poll.options[winner]}!\nThe results are:\n{result_display}"

    await poll.author.send(results)


@bot.event
async def on_reaction_add(reaction, user):
    print(reaction.emoji)
    if reaction.message.id in votes and reaction.emoji == "✅" and user != bot.user:
        v = []
        for reaction in reaction.message.reactions:
            if reaction.count == 2 and reaction.emoji != "✅":
                v.append(reaction)

        if len(v) == 1:
            time.sleep(2)
            poll = votes[reaction.message.id]
            del votes[reaction.message.id]
            polls[poll]["votes"] -= 1
            polls[poll]["results"].append(v[0])
            if polls[poll]["votes"] == 0:
                await polls[poll]["msg"].remove_reaction("👍", bot.user)
        else:
            await user.send("You can only select one option. Please unreact the tick to try again.")




@bot.event
async def on_ready():
    # load_opus()
    print("Logged in as:")
    print(bot.user.name)
    print(bot.user.id)
    print("-------")


bot.run(TOKEN)
