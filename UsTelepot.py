import os
import telepot
import sys
import time
from telepot.loop import MessageLoop


def handle(msg):  # обработка приходящих сообщений
    content_type, chat_type, chat_id = telepot.glance(msg)  # Вытаскиваем заголовки
    if content_type == 'text':
        bot.sendMessage(chat_id, msg['text'])  # если текст, шлем его обратно(используем словарь)


bot = telepot.Bot(os.environ.get("TOKEN"))  # токен берем из переменной окружения


MessageLoop(bot, handle).run_as_thread()  # получаем сообщения, используя определенного бота+обрабатываем их

while 1:  # бесконечный цикл работы программы
    time.sleep(1)  # присотановка скрипта на 1 с
