# coding: utf-8

import sys
import os
import time
import re
import json
import random
import pprint
import websocket
import threading
import datetime
import traceback
from slackclient import SlackClient
from slackclient import server
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import sqlite3

slack_token = os.environ["SLACK_API_TOKEN"]
sc = SlackClient(slack_token)
nos_memo_id = "C61K9HKDM"
bot_uid = "UCCQ7MNEQ"
responses_json_path = "../responses.json"
responses_db_path = "responses.sqlite3"
karen_text_path = "../Karen_morning.txt"

pat_ns_res = re.compile(r"(nosetting|<@UCCQ7MNEQ>) respond", re.IGNORECASE)
pat_ns_delete = re.compile(r"(nosetting|<@UCCQ7MNEQ>) delete", re.IGNORECASE)
pat_ns_rnd = re.compile(r"(nosetting|<@UCCQ7MNEQ>) randomres", re.IGNORECASE)
pat_ns_rnd_add = re.compile(r"(nosetting|<@UCCQ7MNEQ>) rand add", re.IGNORECASE)
pat_ns_SC = re.compile(r"(nosetting|<@UCCQ7MNEQ>) show channels", re.IGNORECASE)
pat_ns_SR = re.compile(r"(nosetting|<@UCCQ7MNEQ>) show responses", re.IGNORECASE)
pat_ns_help = re.compile(r"(nosetting|<@UCCQ7MNEQ>) help", re.IGNORECASE)
pat_ns_search = re.compile(r"(nosetting|<@UCCQ7MNEQ>) search", re.IGNORECASE)


def post_msg(msg, channel, unfurl=True):
    sc.api_call(
        "chat.postMessage",
        channel=channel,
        text=msg,
        icon_emoji=":mawarunos:",
        unfurl_links=unfurl,
        username="nosponse"
    )


def post_attachment(text, channel):
    sc.api_call(
        "chat.postMessage",
        channel=channel,
        attachments=[{"text": text}],
        icon_emoji=":mawarunos:",
        username="nosponse"
    )

def post_blocks(blocks, channel):
    sc.api_call(
        "chat.postMessage",
        channel=channel,
        blocks=blocks,
        icon_emoji=":mawarunos:",
        username="nosponse"
    )

def make_block_template(triggers, responses):
    blocks = [{
		"type": "section",
		"text": {
			"type": "mrkdwn",
			"text": "*トリガー*"
		}
	}]
    if not len(triggers) == 0:
        trigger_field = [{
                    "type": "mrkdwn",
                    "text": trig,
                } for trig in triggers]
        blocks.append({
            "type": "section",
            "fields": trigger_field
        })
    blocks.append({
		"type": "divider"
	})
    blocks.append({
		"type": "section",
		"text": {
			"type": "mrkdwn",
			"text": "*反応*"
		}
	})
    if not len(responses) == 0:
        responses_field = [{
                    "type": "mrkdwn",
                    "text": resp,
                } for resp in responses]
        blocks.append({
            "type": "section",
            "fields": responses_field
        })
    return blocks


def response_msg(channel, msg):
    post_msg(msg, channel=channel)


def post_rand_msg(channel, lis):
    post_msg(random.choice(lis), channel=channel)


def response(text, channel):
    if text in enable_responses:
        if isinstance(enable_responses[text], str):
            response_msg(channel, enable_responses[text])
        else:
            post_rand_msg(channel, enable_responses[text])


def extract_command(pattern, text):
    return pattern.sub("", text, count=1)

def add_new_responses_to_db(db_path, ress):
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.executemany('insert into response values (?, ?)', ress)

def delete_response_from_db(db_path, msg):
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('delete from response where msg = ?', (msg,))

def search_messages_from_db(db_path, query):
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('''
            select distinct msg from response
            where msg like '%' || ? || '%'
        ''', (query,))
        rows = c.fetchall()
        return [x[0] for x in rows]

def search_responses_from_db(db_path, query):
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('''
            select msg, response from response
            where response like '%' || ? || '%'
        ''', (query,))
        rows = c.fetchall()
        return [x[0] + ' -> ' + x[1] for x in rows]

# やってみるとどうか
# - [x] (nosetting|@nosponse) respondを取り除いてresとmesに分けてるところをextract_commandを使うようにする
# - [x] if not hoge: return で抜けられるなら抜けるようにする
# - [ ] 変数名分かりにくかったらいい感じにする
# - [x] deleteコマンドを追加する
# - [ ] rtm使うのやめてtextだけにする

def add_respond(text, channel):
    if not pat_ns_res.match(text):
        return
    # (nosetting|@nosponse) respondを取り除いてる
    command = extract_command(pat_ns_res, text)
    try:
        res, mes = re.split(r" to ", command, maxsplit=1, flags=re.IGNORECASE)
    except ValueError as e:
        response_msg(channel, "Error!")
        return

    res = res.strip()
    mes = mes.strip()
    if mes == "":
        response_msg(channel, "Error!")
        return
    enable_responses[mes] = res
    add_new_responses_to_db(responses_db_path, [(mes, res)])
    response_msg(channel, "Success!")


def delete_response(text, channel):
    if not pat_ns_delete.match(text):
        return
    command = extract_command(pat_ns_delete, text)
    mes = command.strip()
    if mes in enable_responses:
        del enable_responses[mes]
        response_msg(channel, "Deleted the response!")
        delete_response_from_db(responses_db_path, mes)
    else:
        response_msg(channel, "Error!")
    
    
def search_responses(text, channel):
    if not pat_ns_search.match(text):
        return
    command = extract_command(pat_ns_search, text)
    query = command.strip()
    messages = search_messages_from_db(responses_db_path, query)
    responses = search_responses_from_db(responses_db_path, query)
    """
    answers = ['トリガー:'] + messages + [''] + ['反応:'] + responses
    answer_text = '\n'.join(answers)
    answer_text = escape_uid(answer_text)
    response_msg(channel, answer_text)
    """
    blocks = make_block_template(messages, responses)
    answer_blocks = json.dumps(blocks)
    answer_blocks = escape_uid(answer_blocks)
    post_blocks(answer_blocks, channel)

"""
@nosponse randomres A
B
C
D
↓ (extract_command)
A\n (trigger)
B\n
C\n
D (responses)
"""
"""
if len(list) <= 2:
    response_msg(channel, "Error!")
    return
for li in range(len(list)):
    list[li] = list[li].strip()
    if list[li] == "":
        response_msg(channel, "Error!")
        return
mes = list.pop(0)
res = list
"""

def add_rand_respond(text, channel):
    if not pat_ns_rnd.match(text):
        return
    command = extract_command(pat_ns_rnd, text)
    try:
        mes, *res = command.split("\n")
    except ValueError as e:
        response_msg(channel, "Error!")
        return
    if len(res) == 0:
        response_msg(channel, "Error!")
        return
    mes = mes.strip()
    res = [r.strip() for r in res]
    enable_responses[mes] = res
    ress = [(mes, r) for r in res]
    add_new_responses_to_db(responses_db_path, ress)
    response_msg(channel, "Success!")


def modify_rand_respond(text, channel):
    if not pat_ns_rnd_add.match(text):
        return
    command = extract_command(pat_ns_rnd_add, text)
    mes, *res = command.split("\n")
    try:
        mes, *res = command.split("\n")
    except ValueError as e:
        response_msg(channel, "Error!")
        return
    if len(res) == 0:
        response_msg(channel, "Error!")
        return
    mes = mes.strip()
    res = [r.strip() for r in res]
    if mes not in enable_responses:
        response_msg(channel, "not exist such response.")
        return
    if isinstance(enable_responses[mes], str):
        enable_responses[mes] = [enable_responses[mes]]
    enable_responses[mes].extend(res)
    ress = [(mes, r) for r in res]
    add_new_responses_to_db(responses_db_path, ress)
    response_msg(channel, "Success!")


def get_joining_channels():
    res = sc.api_call(
        "users.conversations",
        user=bot_uid
    )
    if not res["ok"]:
        return "get channels Failed"
    channels = {}
    for ch in res["channels"]:
        channels[ch["id"]] = ch["name"]
    return channels


def show_details(text, channel):
    if pat_ns_SC.match(text):
        ch_link = []
        channels = get_joining_channels()
        for ch in channels.keys():
            ch_link.append("<#" + ch + "|" + channels[ch]+">")
        response_msg(channel, pprint.pformat(ch_link, indent=4))
    elif pat_ns_SR.match(text):
        #res = pprint.pformat(enable_responses, indent=4)
        #post_attachment(escape_uid(res), rtm["channel"])
        response_msg(channel, "https://inside.kmc.gr.jp/~nos/app/nosponse/")
    


def show_help(text, channel):
    if not pat_ns_help.match(text):
        return
    response_msg(channel, "<@UCCQ7MNEQ> がinviteされているチャンネルで有効です。\n"\
    "`(nosetting|<@UCCQ7MNEQ>) respond A to B` : BにAと返す反応を追加します。\n"\
    "`(nosetting|<@UCCQ7MNEQ>) search A` : Aを含むトリガーと反応を検索します。\n"\
    "`(nosetting|<@UCCQ7MNEQ>) delete A` : Aへの反応を削除します。\n"\
    "`(nosetting|<@UCCQ7MNEQ>) randomres A \\n B\\n C\\n ...` : Aに対してB,C...をランダムに返す反応を追加します。\n"\
    "`(nosetting|<@UCCQ7MNEQ>) rand add A \\n D\\n E\\n...` : Aに対してのランダムな反応のパターンを追加します。\n"\
    "`(nosetting|<@UCCQ7MNEQ>) show channels` : このbotが有効なチャンネルを表示します。\n"\
    "`(nosetting|<@UCCQ7MNEQ>) show responses` : 設定されている反応を表示します。")


def get_channel_name(channelid):
    channelname = ""
    ch_list = sc.api_call("channels.list", exclude_archived=True, exclude_members=True)
    if ch_list["ok"]:
        for channel in ch_list["channels"]:
            if channel["id"] == channelid:
                channelname = channel["name"]
                return channelname
    return "not found"


def get_channel_id(channelname):
    channelid = ""
    ch_list = sc.api_call("channels.list", exclude_members=True)
    if ch_list["ok"]:
        for channel in ch_list["channels"]:
            if channel["name"] == channelname:
                channelid = channel["id"]
                return channelid
    return "not found"


def get_user_name(userid, ulist=None):
    username = ""
    if ulist is None:
        u_list = sc.api_call("users.list")
    else:
        u_list = ulist
    if u_list["ok"]:
        for user in u_list["members"]:
            if user["id"] == userid:
                username = user["name"]
                return username
    return "not found"


def escape_uid(text):
    res = text.replace("!", "！")
    ulist = sc.api_call("users.list")
    for found in re.findall(r"<@(.*?)>", text):
        res = res.replace(found, get_user_name(found, ulist=ulist))
    res = res.replace("@", "＠")
    return res


def post_Karen(Karen_lines):
    post_msg(random.choice(Karen_lines), nos_memo_id)


def set_interval(func, delay, sleep_time, *param):
    def body():
        time.sleep(sleep_time)
        while True:
            try:
                func(*param)
            except:
                pass
            time.sleep(delay)
    t = threading.Thread(target=body, daemon=True)
    t.start()


def set_interv_athour(func, delay, at_hour, _param):  # 諸事情によりパラメータ一つしか指定できず
    atdt = datetime.datetime.now().replace(hour=at_hour, minute=0, second=0)
    if atdt < datetime.datetime.now():
        atdt = atdt + datetime.timedelta(days=1)
    sleeptime = (atdt - datetime.datetime.now()).seconds
    set_interval(func, delay, sleeptime, _param)


def j_file2dic(_file):
    with open(_file, "r", encoding="utf-8") as filed:
        dic = json.load(filed)
    return dic


def file2list(_file):
    with open(_file, "r", encoding="utf-8") as filed:
        ret = list(filed)
    return ret


def main_process(rtm):
    text = rtm["text"]
    channel = rtm["channel"]
    response(text, channel)
    add_respond(text, channel)
    delete_response(text, channel)
    show_details(text, channel)
    show_help(text, channel)
    add_rand_respond(text, channel)
    modify_rand_respond(text, channel)
    search_responses(text, channel)


def load_responses(responses_db_path):
    conn = sqlite3.connect(responses_db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('select * from response')
    data = c.fetchall()
    conn.close()
    responses = dict()
    for row in data:
        responses[row['msg']] = responses.get(row['msg'], []) + [row['response']]
    return responses

if __name__ == "__main__":
    enable_responses = load_responses(responses_db_path)
    Karen_lines = file2list(karen_text_path)

    if sc.rtm_connect():
        set_interv_athour(post_Karen, 86400, 8, Karen_lines)
        while True:
            try:
                for rtm in sc.rtm_read():
                    if rtm["type"] == "message":
                        if "subtype" not in rtm and "text" in rtm:
                            main_process(rtm)
            except server.SlackConnectionError:
                if sc.rtm_connect():
                    pass
                else:
                    print("Connection Failed!")
                    time.sleep(100)
            except:
                print(str(datetime.datetime.now()) + ":")
                traceback.print_exc()
                time.sleep(2)
                if sc.rtm_connect():
                    post_msg(random.choice([":nos: 再接続完了デース！", ":nos: 接続しなおしておきマシタ！"]), nos_memo_id)
                else:
                    print("Connection Failed!")
                    time.sleep(100)
            time.sleep(0.5)
    else:
        print("Connection Failed")
