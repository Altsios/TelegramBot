GAME_TEMPLATE = """
*{name} ({release_date})* [steam](https://store.steampowered.com/app/{appid}/)
{metacritic}
*platforms:* _{platforms}_
*genres:* _{genres}_
*publisher:* _{publishers}_
*recommendations:* _{recommendations}_
*price:* _{price}_
_get {screenshotscount} screenshots:_ /scr\_{appid}
_get last news:_ /news\_{appid}
{about_the_game}
"""

NEWS_TEMPLATE = """
*{title}* [read on site]({url})
_{pub_date}_
_{feedlabel}_
{contents}
_{author}_
"""