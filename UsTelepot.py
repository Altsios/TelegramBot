# coding: utf-8
import aiohttp
import asyncio
import json
import re
from urllib import parse
from datetime import datetime
import telepot
import telepot.aio
from telepot.namedtuple import ReplyKeyboardMarkup, ReplyKeyboardRemove
from utils import SearchSuggestParser
from constants import GAME_CARD_TEMPLATE, NEWS_CARD_TEMPLATE, LANG, CC



class SteamBot(telepot.aio.Bot, telepot.helper.AnswererMixin):
    def __init__(self, *args, config=None, **kwargs):
        super(SteamBot, self).__init__(*args, **kwargs)
        self._answerer = telepot.aio.helper.Answerer(self)
        self.config = config
        self.cache_time = self.config.get('cache_time', 10)
        self.routes = {
            '/search': self.search_game,
            '/app_': self.game_card_answer,
            '/scr_': self.screenshots_answer,
            '/news_': self.last_news_answer,
            # '/settings': self.settings_answer,
            # '/lang': self.set_lang,
            # '/cc': self.set_cc,
            '/start': self.welcome_answer
        }

    @staticmethod
    def get_command(msg):  # разбиение на команду+параметр
        if 'entities' in msg:  # если это команда, там есть такой ключ
            for entity in msg['entities']:
                if entity['type'] == 'bot_command':  # если тип-команда
                    offset, length = entity['offset'], entity['length']
                    return msg['text'][offset:length], msg['text'][
                                                       offset + length:].strip()  # возвращаем команду и параметр(2 слова) без пробелов
        return None, None

    # разбор команды
    def route(self, chat_id, command, args=None):  # если нет аргументов
        func = None
        for cmd, fnc in self.routes.items():  # смотрим словарь команд
            if command.find(cmd) != -1:  # если нашли команду
                func = fnc  # указываем функцию, соотв команде
                break
        if func:
            print("Есть такая функция!")
            self.loop.create_task(func(chat_id, command, args))  # ставим задачу
            # если /start

    async def welcome_answer(self, chat_id, command, args):
        await self.sendMessage(
            chat_id,
            'Добро пожаловать:)! Нажмите / для просмотра списка команд. Для поиска игры '
            'пошлите сообщение с названием игры'
        )

    # если /search
    async def search_game(self, chat_id, command, args):
        await self.sendChatAction(chat_id, 'typing')  # печатаю вверху
        await self.game_search_answer(args, chat_id)  # только если указали игру

    # Ищем игру(проверено до этого момента)
    async def game_search_answer(self, term, chat_id):  # term-это имя игры
        # информация о пользователе
        #       user_info = await self.get_user(chat_id)
        #        settings = user_info.get('settings')
        msg = self.get_games_message(await self.get_search_results(term))  # settings-настр языка итд
        await self.sendMessage(chat_id, msg, parse_mode='markdown')

    # получаем информацию
    async def get_search_results(self, term):  # settings-настр языка итд
        print("зашли в поиск")
        print("term= " + term)
        # поиск по магазину steam
        search_url = u'https://store.steampowered.com/search/suggest?term={}&f=games&l={}&cc={}'.format(
            parse.quote_plus(term),
            # ЯЗЫК
            'russian',
            # settings.get('lang'),
            # РЕГИОН
            'RU'
            # settings.get('cc')
        )
        print(search_url)
        content = await self.get_content_from_url(search_url, resp_format='text')
        print(content)
        parser = SearchSuggestParser()
        parser.feed(content)
        print(parser.result)
        return parser.result

    # разбираем url в зависимости от типа
    async def get_content_from_url(self, url, resp_format=None):

        async with aiohttp.ClientSession(loop=self.loop) as client:
            async with client.get(url) as resp:
                if resp.status != 200:
                    return
                if resp_format == 'text':
                    result = await resp.text()
                elif resp_format == 'json':
                    result = await resp.json()
                else:
                    result = await resp.content.read()
                return result

    # структура ответа
    @staticmethod
    def get_games_message(entries):
        msg_list = []
        if len(entries) != 0:
            for entry in entries:
                msg = u"{cmd} {name} [steam]({href}) _{price}_".format(
                    name=entry['name'],
                    href=entry['href'],
                    price=entry['price'],
                    cmd=u'/app\_{}'.format(entry['appid'])  # создаем команду /app неявно
                )
                msg_list.append(msg)
            return u'\n'.join(msg_list)
        return u'Nothing found'

    # при нажатии на ссылку app->команда /app
    async def game_card_answer(self, chat_id, command, args):
        appid = command.replace('/app_', '').strip()  # получение appid
        self.loop.create_task(self.sendChatAction(chat_id, 'typing'))  # "отвлекаем"
        app_details = await self.get_appdetails(appid)
        await self.sendMessage(chat_id, self.get_game_card_message(app_details), parse_mode='markdown')

    # смотрим информацию по приложению
    async def get_appdetails(self, appid, settings={}):
        url = u'https://store.steampowered.com/api/appdetails/?appids={}&l={}&cc={}'.format(
            appid,
            # ЯЗЫК
            'russian',
            # settings.get('lang'),
            # РЕГИОН
            'RU'
            # settings.get('cc')
        )
        content = await self.get_content_from_url(url, resp_format='json')
        print(content)# смотрим словарь данных
        return content[appid]['data'] if content else {}  # информации может и не быть(

    # формирвоание красивого ответа
    def get_game_card_message(self, appdetails):
        return GAME_CARD_TEMPLATE.format(
            appid=appdetails['steam_appid'],
            name=appdetails['name'],
            release_date=appdetails['release_date']['date'],
            metacritic=u'\u2b50\ufe0f{} [metacritics]({})'.format(
                appdetails['metacritic']['score'],
                appdetails['metacritic']['url']
            ) if 'metacritic' in appdetails else '',
            platforms=', '.join(
                [x[0] for x in appdetails['platforms'].items() if x[1]]),
            genres=', '.join(
                [x['description'] for x in appdetails['genres']]) if 'genres' in appdetails else '',
            publishers=', '.join(
                appdetails['publishers']) if 'publishers' in appdetails else '',
            price='{} {}'.format(appdetails['price_overview']['final'] / 100.0,
                                 appdetails['price_overview']['currency']) if 'price_overview' in appdetails else '',
            recommendations=appdetails['recommendations']['total'] if 'recommendations' in appdetails else '',
            screenshotscount=len(
                appdetails['screenshots']) if 'screenshots' in appdetails else '0',
            about_the_game=self.clean_html(appdetails['about_the_game'].replace("&quot;","\"").replace("&hellip;","..."))
        )

    @staticmethod
    def clean_html(html):
        return re.sub('<[^<]+?>', '', html)

    #прислать скриншоты
    async def screenshots_answer(self, chat_id, command, args):
        appid = command.replace('/scr_', '').strip()
        self.loop.create_task(self.sendChatAction(chat_id, 'upload_photo')) # встроенная функция telepot
        app_details = await self.get_appdetails(appid)
        for scr in app_details['screenshots']:
            loop.create_task(self.send_photo_from_url(# пишем полный путь к скриншоту,имя скрина шлем чату, отправившему запрос
                scr['path_full'], 'scr-{}.jpg'.format(scr['id']), chat_id))

    #отправка скриншотов
    async def send_photo_from_url(self, url, photo_name, chat_id):
        downloaded_file = await self.get_content_from_url(url)
        await self.sendPhoto(chat_id, photo=(photo_name, downloaded_file))


    async def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        print(msg)
        # await self.create_or_update_user(msg.get('chat'))
        command, args = self.get_command(msg)  # может быть с параметром
        # распознавание не зависит от регистра
        command = command.lower()
        args = args.lower()
        print(command)
        print(args)
        if command:
            self.route(chat_id, command, args)  # разбираем команду
# получение новостей по приложению
    async def last_news_answer(self, chat_id, command, args):
        appid = command.replace('/news_', '').strip()
        self.loop.create_task(self.sendChatAction(chat_id, 'typing'))
        news_items = await self.get_news(appid)
        for item in news_items:
            msg = NEWS_CARD_TEMPLATE.format(
                title=item['title'],
                url=item['url'],
                pub_date=datetime.fromtimestamp(
                    int(item['date'])).strftime("%B %d, %Y"),
                feedlabel=item['feedlabel'],
                contents=self.clean_markdown(self.clean_html(item['contents']).replace("&quot;","\"")
                                             .replace("&hellip;","...")).replace(
                    '\n', '').replace('  ', ''),
                author=item['author']
            )
            loop.create_task(self.sendMessage(
                chat_id, msg, parse_mode='markdown'))

    #как и со скриншотами, вытаскиваем всю информацию с той же страницы
    async def get_news(self, appid, count=3):
        url = u'https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={}&count={}&max_length=300&format=json'.format(
            appid,
            count
        )
        content = await self.get_content_from_url(url, resp_format='json')
        return content['appnews']['newsitems'] if content else {}

    @staticmethod
    def clean_markdown(text):
        return text.replace('_', '\_').replace('*', '\*')

with open('conf/config.json') as f:
    config = json.loads(f.read())

loop = asyncio.get_event_loop()
token = config.pop("telegram_token")
bot = SteamBot(token=token, config=config, loop=loop)
loop.create_task(bot.message_loop())
print('Listening ...')
loop.run_forever()
