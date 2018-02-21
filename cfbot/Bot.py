import discord
import asyncio
from discord.ext import commands
import json
import requests


BOT_PREFIX = ('?', '!')
CF_USER_API_BASE = "http://codeforces.com/api/user.rating?handle="


class CodeForcesBot:
    def __init__(self, channel_name, bot_token):
        self.channel_name = channel_name
        self.bot_token = bot_token
        self.discord_client = commands.Bot(command_prefix=BOT_PREFIX)
        self.setup()

    def get_user_rating(self, user):
        """
        Get the most recent Codeforces rating for the user via the Codeforces API
        """
        request_url = CF_USER_API_BASE + user
        response = requests.get(request_url)
        if response.status_code == 200:
            content = json.loads(response.content.decode('utf-8'))
            if content['status'] == "OK":
                if len(content['result']) > 0:
                    return ('rated', content['result'][-1]['newRating'])
                else:
                    return ('unrated', None)
        return ('bad_user', None)
        print(response.status_code)

    def setup(self):
        @self.discord_client.event
        @asyncio.coroutine
        def on_ready():
            print("Bot Online!")
            print("Name: {}".format(self.discord_client.user.name))
            print("ID: {}".format(self.discord_client.user.id))

        

        @self.discord_client.event
        @asyncio.coroutine
        def on_message(message):
            if message.author.bot or str(message.channel) != self.channel_name:
                return
            if message.content is None:
                return
            print("Message: " + str(message.content))

            if message.content.startswith(BOT_PREFIX):
                user = str(message.content).split()[1]
                request_status, rating = self.get_user_rating(user)
                response = None
                if request_status == 'rated':
                    response = "User %s's rating: %d" % (user, rating)
                elif request_status == 'unrated':
                    response = "User %s is unrated. Do some contests!" % user
                elif request_status == 'bad_user':
                    response = "User %s does not exist" % user
                else:
                    response = "Bad response from server. Is Codeforces down?"

                yield from self.discord_client.send_message(message.channel, response)

    def run(self):
        self.discord_client.run(self.bot_token)
	
