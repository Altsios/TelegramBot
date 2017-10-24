import requests
import misc
from time import sleep
import json

# https://api.telegram.org/
# bot457007807:AAGwy_GFW-frl4-5hmJaaA1LycqSO9-Q_XA/
# sendMessage?chat_id=412365892&text=Гаста%20лох

token = misc.token
URL = 'https://api.telegram.org/bot' + token + '/'
global last_update_id
last_update_id = 0  # номер последнего обновления


def get_updates():
    url = URL + 'getupdates'
    r = requests.get(url)  # ответ сервера
    return r.json()

    # отвечать только на новые сообщения
    # получаем id каждого обновления, записать в переменную, сравнить с предыдущим
    # в списке result


def get_message():
    data = get_updates()  # зааписали словарь
    last_object = data['result'][-1]
    current_update_id = last_object['update_id']
    # [result-словарь основной]
    # -получаем последнее сообщение[-1][message-тоже словарь][в message chat]['id'-чат-отправитель]
    # chat_id = data['result'][-1]['message']['chat']['id']
    global last_update_id
    if last_update_id != current_update_id:
        last_update_id = current_update_id
        chat_id = last_object['message']['chat']['id']
        message_text = data['result'][-1]['message']['text']
        message = {'chat_id': chat_id, 'text': message_text}
        return message  # вытаскиваем chat_id и message
    return None  # если новых сообщенйи нет


def send_message(chat_id, text):  # функция отправки сообщения
    url = URL + 'sendmessage?chat_id={}&text={}'.format(chat_id, text)
    requests.get(url)


def main():
    # d = get_updates()
    # with open('updates.json','w') as file:  # записываем в файл
    #     json.dump(d, file, indent=2, ensure_ascii=False)  # сделать запись в файл
    # хотим считывать самые последние данные(кто отослал, с кем переписываемся)
    while True:
        answer = get_message()  # вытаскиваем данные о последнем сообщении
        if answer is not None:
            chat_id = answer['chat_id']
            text = answer['text']  # берем текст из полученного сообщения
            # проверка на определенное слово(на будущее)
            send_message(chat_id, text)
        else:
            continue


# точка входа
if __name__ == '__main__':
    main()
