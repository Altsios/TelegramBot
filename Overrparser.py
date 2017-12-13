from html.parser import HTMLParser


# перегрузка html парсера
class Parser(HTMLParser):
    def __init__(self):
        super(Parser, self).__init__()
        self.result = []

    # этот метод вызывается каждый раз, когда парсер встречает в тексте открывающий html-тэг
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'): # href=ссылка на профиль игры
            self.result.append({})
            self.result[-1]['appid'] = attrs.get('data-ds-appid')# составляем словарь
            self.result[-1]['href'] = attrs['href']
        elif tag == 'div' and attrs.get('class') == 'match_name':
            self.result[-1]['name'] = u''
        elif tag == 'div' and attrs.get('class') == 'match_price':
            self.result[-1]['price'] = u''

    def handle_data(self, data):
        if len(self.result) == 0:
            return
        if self.result[-1].get('name') == u'':# теперь заполняем данные >данные<
            self.result[-1]['name'] = data
        elif self.result[-1].get('price') == u'':
            self.result[-1]['price'] = data
