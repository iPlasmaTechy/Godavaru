import asyncio
import datetime
import signal
import sys
import traceback
import discord
import os
import weeb
import pymysql as mysql
from discord.ext import commands
import config
import random
import aiohttp
from cogs.utils.db import get_all_prefixes, get_blacklist
from cogs.utils.tools import get_prefix


class Godavaru(commands.Bot):
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.prefixes = get_all_prefixes()
        super().__init__(command_prefix=get_prefix, case_insensitive=True)
        self.version = config.version
        self.version_info = config.version_description
        self.remove_command('help')
        self.weeb = weeb.Client(token=config.weeb_token, user_agent=f'Godavaru/{self.version}/{config.environment}')
        self.seen_messages = 0
        self.reconnects = 0
        self.executed_commands = 0
        self.db_calls = 0
        self.modlogs = dict()
        self.snipes = dict()
        self.blacklist = get_blacklist(self)
        with open('splashes.txt') as f:
            self.splashes = f.readlines()
        self.game_task = self.loop.create_task(self.change_game())
        if config.environment == 'Production':
            self.post_task = self.loop.create_task(self.post_counts())
        self.webhook = discord.Webhook.partial(int(config.webhook_id), config.webhook_token,
                                               adapter=discord.RequestsWebhookAdapter())
        extensions = [f for f in os.listdir('./cogs') if f.endswith('.py')] + ['events.' + f for f in
                                                                               os.listdir('./cogs/events') if
                                                                               f.endswith('.py')]
        for ext in extensions:
            try:
                self.load_extension('cogs.' + ext[:-3])
            except:
                print(f'Failed to load extension ' + ext)
                print(traceback.format_exc())
                continue

    async def on_message(self, message):
        pass

    async def post_to_haste(self, content):
        async with self.session.post("https://hastepaste.com/api/create", data=f'text={content}&raw=false',
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'}) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                return "Error uploading to hastepaste :("

    # noinspection PyAttributeOutsideInit
    async def on_ready(self):
        startup_message = f"[`{datetime.datetime.now().strftime('%H:%M:%S')}`][`Godavaru`]\n" \
                          + "===============\n" \
                          + 'Logged in as:\n' \
                          + str(self.user) + '\n' \
                          + '===============\n' \
                          + 'Ready for use.\n' \
                          + f'Servers: `{len(self.guilds)}`\n' \
                          + f'Users: `{len(self.users)}`\n' \
                          + '===============\n' \
                          + f'Loaded up `{len(self.commands)}` commands in `{len(self.cogs)}` cogs in `{(datetime.datetime.now() - self.start_time).total_seconds()}` seconds.\n' \
                          + '==============='
        print(startup_message.replace('`', ''))
        self.webhook.send(startup_message)
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()
        self.weeb_types = await self.weeb.get_types()
        self.session = aiohttp.ClientSession()

    async def on_error(self, event, *args, **kwargs):
        if sys.exc_info()[0] == discord.Forbidden:
            return
        self.webhook.send(f':x: **I ran into an error in event `{event}`!**\nTraceback: ```py\n{"".join(traceback.format_exception(*sys.exc_info()))}\n```')

    async def change_game(self):
        await self.wait_until_ready()
        while not self.is_closed():
            pr = random.choice(self.splashes).format(self.version, len(self.guilds))
            await self.change_presence(
                activity=discord.Game(name=config.prefix[0] + "help | " + pr))
            await asyncio.sleep(900)

    async def post_counts(self):
        await self.wait_until_ready()
        while not self.is_closed():
            data = {'server_count': len(self.guilds)}
            dbl_url = f'https://discordbots.org/api/bots/{self.user.id}/stats'
            pw_url = f'https://bots.discord.pw/api/bots/{self.user.id}/stats'
            if config.dbotstoken != '':
                await self.session.post(dbl_url, data=data, headers={'Authorization': config.dbotstoken})
            if config.pw_token != '':
                await self.session.post(pw_url, data=data, headers={'Authorization': config.pw_token})
            await asyncio.sleep(1800)

    async def on_resumed(self):
        self.webhook.send(f"[`{datetime.datetime.now().strftime('%H:%M:%S')}`][`Godavaru`]\n"
                          + "I disconnected from the Discord API and successfully resumed.")
        self.reconnects += 1

    def gracefully_disconnect(self, signal, frame):
        print("Gracefully disconnecting...")
        self.logout()
        sys.exit(0)

    def query_db(self, query, *args, **kwargs):
        self.db_calls += 1
        db = mysql.connect(config.db_ip, config.db_user, config.db_pass, config.db_name, charset='utf8mb4')
        cur = db.cursor()
        cur.execute(query, *args, **kwargs)
        res = cur.fetchall()
        db.commit()
        cur.close()
        db.close()
        return res


bot = Godavaru()
signal.signal(signal.SIGINT, bot.gracefully_disconnect)
signal.signal(signal.SIGTERM, bot.gracefully_disconnect)
'''
app = Flask(__name__)

web_resources = {
    "statuses": {
        "OK": 200,
        "UN_AUTH": 401,
        "NO_AUTH": 403
    },
    "content_type": "application/json"
}


@app.route("/dbl", methods=["POST"])
def get_webhook():
    if request.method == 'POST':
        auth = request.headers.get("authorization")
        if not auth:
            return Response(json.dumps({"msg": "Authorization required"}), status=web_resources["statuses"]["NO_AUTH"],
                            mimetype=web_resources["content_type"])
        if auth != config.dbl_auth:
            return Response(json.dumps({"msg": "Unauthorized"}), status=web_resources["statuses"]["UN_AUTH"],
                            mimetype=web_resources["content_type"])


def start_app():
    app.run(port=1034, host="localhost")


Thread(target=start_app).start()'''
bot.run(config.token)
