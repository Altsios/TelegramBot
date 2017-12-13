import aiohttp
import asyncio
import re
from datetime import datetime
import telepot
import telepot.aio
from Overrparser import Parser
from constants import GAME_TEMPLATE, NEWS_TEMPLATE
import os

class SteamBot(telepot.aio.Bot, telepot.helper.AnswererMixin):
    def __init__(self, *args, **kwargs):
        super(SteamBot, self).__init__(*args, **kwargs)
        self._answerer = telepot.aio.helper.Answerer(self)
        self.commands = {
            '/search': self.search_for_game,
            '/app_': self.app_answer,
            '/scr_': self.screenshots,
            '/news_': self.last_news,
            '/help': self.help,
            '/start': self.welcome_mess
        }

    @staticmethod
    def get_command(msg):  # разбиение на команду+параметр
        if 'entities' in msg:  # если это команда, там есть такой ключ
            for entity in msg['entities']:
                if entity['type'] == 'bot_command':  # если тип-команда
                    offset, length = entity['offset'], entity['length']
                    return msg['text'][offset:length], msg['text'][
                                                       offset + length:].strip() # возвращаем команду и параметр(2 слова) без пробелов
        return None, None

    # разбор команды
    def parse_command(self, chat_id, command, args=None):  # если нет аргументов
        func = None
        for cmd, fnc in self.commands.items():  # смотрим словарь команд
            if command.find(cmd) != -1:  # если нашли команду
                func = fnc  # указываем функцию, соотв команде
                break
        if func:
            self.loop.create_task(func(chat_id, command, args))  # ставим задачу
    # если /start
    async def welcome_mess(self, chat_id, command, args):
        await self.sendMessage(
            chat_id,
            'Добро пожаловать:) Для поиска информации по игре введите, используя /, "search имя_игры" '
            'или просто /search для вывода 5 самых релевантных игр.'
        )

    # если команда help
    async def help(self, chat_id, command, args):
        await  self.sendMessage(chat_id, '1)Введите /start для краткой инструкции\n'
                                         '2)/search покажет 5 самых релевантных результатов по поиску игр\n'
                                         '3)В результатах, полученных по запросу, нажмите на ссылку вида /app_271590, '
                                         'чтобы получить более подробную информацию об игре\n'
                                         '4)Если доступны скриншоты для данной игры, будет дана ссылка вида /scr_271590\n'
                                         '5)Если доступны новости для данной игры, будет дана ссылка /news_271590 на 5 последних новостей')

    # если /search
    async def search_for_game(self, chat_id, command, args):
        await self.sendChatAction(chat_id, 'typing')  # вырисовываем typing
        await self.results(args, chat_id)  # только если указали игру

    # Ищем игру
    async def results(self, term, chat_id):  # term-это имя игры
        msg = self.get_list_of_games(await self.get_Store_results(term))
        await self.sendMessage(chat_id, msg, parse_mode='markdown',disable_web_page_preview=True)

    # получаем информацию
    async def get_Store_results(self, term):
        # поиск по магазину steam
        search_url = u'https://store.steampowered.com/search/suggest?term={}&f=games&l=russian&cc=RU'.format(term)
        content = await self.get_content_from_url(search_url, resp_format='text')
        parser = Parser()
        # скармливаем парсеру содержимое
        parser.feed(content)
        return parser.result

    # разбираем url в зависимости от типа
    async def get_content_from_url(self, url, resp_format=None):
        # идеально подходит для HTTP запросов в ассинхронном приложении
        async with aiohttp.ClientSession(loop=self.loop) as client:
            async with client.get(url) as resp:
                if resp.status != 200: # если ответ норм
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
    def get_list_of_games(entries):
        msg_list = []
        if len(entries) != 0:
            for entry in entries:
                msg = u"{cmd} {name} [steam]({href}) _{price}_ ".format(
                    name=entry['name'],
                    href=entry['href'],
                    price=entry['price'],
                    cmd=u'/app\_{}'.format(entry['appid'])# создаем команду /app неявно
                )
                msg_list.append(msg)
            return u'\n'.join(msg_list)
        return u'Ничего не найдено:('

    # при нажатии на ссылку app->команда /app
    async def app_answer(self, chat_id, command, args):
        appid = command.replace('/app_', '').strip()  # получение appid
        self.loop.create_task(self.sendChatAction(chat_id, 'typing'))  # "отвлекаем"
        app_details = await self.get_appdetails(appid)
        await self.sendMessage(chat_id, self.get_game_beauty_message(app_details), parse_mode='markdown')

    # смотрим информацию по приложению
    async def get_appdetails(self, appid):
        url = u'https://store.steampowered.com/api/appdetails/?appids={}&l=russian&cc=RU'.format(appid)
        content = await self.get_content_from_url(url, resp_format='json')
        return content[appid]['data'] if content else {}  # информации может и не быть(

    # формирвоание красивого ответа
    def get_game_beauty_message(self, appdetails):
        return GAME_TEMPLATE.format(
            appid=appdetails['steam_appid'],
            name=appdetails['name'],
            release_date=appdetails['release_date']['date'],
            metacritic=u'\u2b50\ufe0f{} [metacritics]({})'.format(
                appdetails['metacritic']['score'],
                appdetails['metacritic']['url']
            ) if 'metacritic' in appdetails else '',
            platforms=', '.join(
                [x[0] for x in appdetails['platforms'].items() if x[1]]),# записываем, если поддерживается
            genres=', '.join(
                [x['description'] for x in appdetails['genres']]) if 'genres' in appdetails else '',
            publishers=', '.join(
                appdetails['publishers']) if 'publishers' in appdetails else '',
            price='{} {}'.format(appdetails['price_overview']['final'] / 100.0, # может не быть, если бесплатно
                                 appdetails['price_overview']['currency']) if 'price_overview' in appdetails else '',
            recommendations=appdetails['recommendations']['total'] if 'recommendations' in appdetails else '',
            screenshotscount=len(
                appdetails['screenshots']) if 'screenshots' in appdetails else '0',
            about_the_game=self.clean_html(appdetails['about_the_game'])
        )

    @staticmethod
    def clean_html(html):# re.sub заменяет <любой символ кроме < >. убираем теги
        return re.sub('<[^<]+?>', '', html.replace("&quot;", "\"").replace("&hellip;", "...").replace(
            '\n', '').replace('  ', '').replace('&#xA3;', '£').replace('&#xA0;', '\r\n').replace('&#8217;', '’')
                      .replace('&#8216;', '’').replace('&apos;', '’').replace('&#8212;','–')).replace('&#x2014;','—').\
            replace('&#x2019;','’')


    # прислать скриншоты
    async def screenshots(self, chat_id, command, args):
        appid = command.replace('/scr_', '').strip()
        self.loop.create_task(self.sendChatAction(chat_id, 'upload_photo'))  # встроенная функция telepot
        app_details = await self.get_appdetails(appid)
        for scr in app_details['screenshots']:
            loop.create_task(
                self.send_photo_from_url(  # пишем полный путь к скриншоту,имя скрина шлем чату, отправившему запрос
                    scr['path_full'], chat_id))

    # отправка скриншотов
    async def send_photo_from_url(self, url, chat_id):
        downloaded_file = await self.get_content_from_url(url)
        await self.sendPhoto(chat_id, photo=downloaded_file)

    async def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        command, args = self.get_command(msg)  # может быть с параметром
        if command:
            command = command.lower()
            if args:
                args= args.lower()
            self.parse_command(chat_id, command, args)  # разбираем команду
        # получение новостей по приложению

    async def last_news(self, chat_id, command, args):
        appid = command.replace('/news_', '').strip()
        self.loop.create_task(self.sendChatAction(chat_id, 'typing'))
        news_items = await self.get_news(appid)
        # скармливаем парсеру содержимое
        for item in news_items:
            print(item['contents'])
            msg = NEWS_TEMPLATE.format(
                title=item['title'],
                url=item['url'],
                pub_date=datetime.fromtimestamp(
                    int(item['date'])).strftime("%B %d, %Y"),
                feedlabel=item['feedlabel'],
                contents=self.clean_markdown(self.clean_html(item['contents'])),
                author=item['author']
            )
            loop.create_task(self.sendMessage(
                chat_id, msg, parse_mode='markdown'))

    # здесь уже используем api
    async def get_news(self, appid, count=10):
        url = u'https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={}&count={}&max_length=300&format=json'.format(
            appid,
            count
        )
        content = await self.get_content_from_url(url, resp_format='json')
        print(content)
        return content['appnews']['newsitems'] if content else {}

    @staticmethod
    def clean_markdown(text):
        return text.replace('_', '\_').replace('*', '\*')


loop = asyncio.get_event_loop()
token = os.environ['TOKEN']
bot = SteamBot(token=token, loop=loop)
loop.create_task(bot.message_loop())
print('Listening ...')
loop.run_forever()
