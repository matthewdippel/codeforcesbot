import discord
import asyncio
import concurrent.futures
from discord.ext import commands
import json
import requests
import logging
import pickle

BOT_PREFIX = ('?', '!')
CF_USER_API_BASE = "http://codeforces.com/api/user.rating?handle="
DEFAULT_APP_DATA_FOLDER = "/var/lib/cfbot/"
DEFAULT_USER_FILE = DEFAULT_APP_DATA_FOLDER + "users.pik"

class CodeForcesBot:
    """
    Class for Discord bot for retrieving codeforces ratings and tracking users
    """
    def __init__(self, channel_name, bot_token):
        self.channel_name = channel_name
        self.bot_token = bot_token
        self.discord_client = commands.Bot(command_prefix=BOT_PREFIX)
        self.users = set()
        self.read_users()
        self.setup()

    def read_users(self):
        """
        Read users from saved file for persistance between runs
        """
        import os
        directory = os.path.dirname(DEFAULT_USER_FILE)
        if not os.path.exists(directory):
            os.makedirs(directory)
        logger = logging.getLogger(__name__)
        if os.path.isfile(DEFAULT_USER_FILE):
            with open(DEFAULT_USER_FILE, 'rb') as fin:
                self.users = pickle.load(fin)
            logger.info("Loaded users from %s" % DEFAULT_USER_FILE)
        else:
            logger.info("No user file found, starting with empty user set")

    def update_users_file(self):
        """
        Overwrite the users file with the current users set
        """
        with open(DEFAULT_USER_FILE, 'wb') as fout:
            pickle.dump(self.users, fout)
        logger = logging.getLogger(__name__)
        logger.info("Resaved users to %s" % DEFAULT_USER_FILE)

    def handle_api_response(self, response, user):
        """
        handle the codeforces api response
        partitions responses into three times:
         - a rated user. gets the most recent rating
         - an unrated user. 
         - a nonexistent user
        """
        if response.status_code == 200:
            content = json.loads(response.content.decode('utf-8'))
            if content['status'] == "OK":
                if len(content['result']) > 0:
                    return ('rated', content['result'][-1]['newRating'], user)
                else:
                    return ('unrated', None, user)
        return ('bad_user', None, user)

    async def get_user_rating(self, user):
        """
        Get the most recent Codeforces rating for the user via the Codeforces API
        """
        request_url = CF_USER_API_BASE + user
        response = requests.get(request_url)
        return self.handle_api_response(response, user)

    async def get_user_rating_batch(self, users):
        """
        get the most recent Codeforces ratings for a set of users
        Performs asyncio to do multiple API requests in parallel
        """
        async_ratings = [self.get_user_rating(user) for user in self.users]
        ratings = []
        for async_rating in async_ratings:
            rating = await async_rating
            ratings.append(rating)
        print(ratings)
        return ratings

    def rankings_leaderboard(self, ratings):
        """
        Create a pretty Discord formatted leaderboard
        from a collection of user ratings
        """
        logger = logging.getLogger(__name__)
        d = []
        for status, rank, user in ratings:
            if status != 'bad_user':
                if status == 'unrated':
                    rank = 0
                d.append((rank, user))
                
        d = sorted(d)[::-1]
        d = [r for r in map(lambda t: (str(t[0]), str(t[1])), d)]
        max_len_user = max([len(t[1]) for t in d])

        header = "__**User ratings leaderboard**__\n"
        column_user = "User%s" % ("  " * max(0, max_len_user - 4))
        user_column_width =  len(column_user)
        column_rating = "Rating"
        column_header = column_user + "   " + column_rating
        
        leaderboard_str = "%s\n`%s`\n`%s`" % (header, column_header, '='*len(column_header))

        for rank, user in d:
            table_string = "%s%s   %s%s" % (user, 
                                            " "*max(0, user_column_width - len(user)), 
                                            rank,
                                            " "*max(0, len(column_rating) - len(rank)), )
            logger.debug((user, len(table_string)))
            leaderboard_str += "\n`%s`" % table_string
        logger.debug(leaderboard_str)
        return leaderboard_str



    def setup(self):
        """
        Setup for the discord bot
        defines async routines and commands, and tags them with the command decorator
        to register them with the bot
        """
        @self.discord_client.event
        @asyncio.coroutine
        def on_ready():
            print("Bot Online!")
            print("Name: {}".format(self.discord_client.user.name))
            print("ID: {}".format(self.discord_client.user.id))

        
        """
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
                response = none
                if request_status == 'rated':
                    response = "user %s's rating: %d" % (user, rating)
                elif request_status == 'unrated':
                    response = "user %s is unrated. do some contests!" % user
                elif request_status == 'bad_user':
                    response = "user %s does not exist" % user
                else:
                    response = "bad response from server. is codeforces down?"

                yield from self.discord_client.send_message(message.channel, response)
        """

        @commands.command()
        async def rating(user : str):
            """
            Command to display the rating of a Codeforces user
            """
            print(user)
            api_response = await self.get_user_rating(user)
            request_status, rating = api_response[0], api_response[1]

            response = None
            if request_status == 'rated':
                response = "user %s's rating: %d" % (user, rating)
            elif request_status == 'unrated':
                response = "user %s is unrated. do some contests!" % user
            elif request_status == 'bad_user':
                response = "user %s does not exist" % user
            else:
                response = "bad response from server. is codeforces down?"
            print(response)
            await self.discord_client.say(response)
        self.discord_client.add_command(rating)

        
        @commands.command()
        async def follow(user : str):
            """
            Command to follow a Codeforces user
            """
            print(user)
            api_response = await self.get_user_rating(user)
            request_status, rating = api_response[0], api_response[1]
            response = None
            if request_status != 'bad_user':
                self.users.add(user)
                response = "Now tracking %s" % user
                self.update_users_file()
            else:
                response = "user %s does not exist" % user
            print(response)
            await self.discord_client.say(response)
        self.discord_client.add_command(follow)

        @commands.command()
        async def all_ratings():
            """
            Command to display ratings of all followed Codeforces users,
            sorted by rating
            """
            rankings = await self.get_user_rating_batch(self.users)
            print(rankings)
            msg = self.rankings_leaderboard(rankings)
            print(msg)
            await self.discord_client.say(msg)
        self.discord_client.add_command(all_ratings)


    def run(self):
        self.discord_client.run(self.bot_token)
	
