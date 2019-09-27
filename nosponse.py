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
from slackclient import SlackClient
from slackclient import server
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

slack_token = os.environ["SLACK_API_TOKEN"]
sc = SlackClient(slack_token)
nos_memo_id = "C61K9HKDM"
bot_uid = "UCCQ7MNEQ"
responses_json_path = "../responses.json"
karen_text_path = "../Karen_morning.txt"

pat_ns_res = re.compile(r"(nosetting|<@UCCQ7MNEQ>) respond", re.IGNORECASE)
pat_ns_delete = re.compile(r"(nosetting|<@UCCQ7MNEQ>) delete", re.IGNORECASE)
pat_ns_rnd = re.compile(r"(nosetting|<@UCCQ7MNEQ>) randomres", re.IGNORECASE)
pat_ns_rnd_add = re.compile(r"(nosetting|<@UCCQ7MNEQ>) rand add", re.IGNORECASE)
pat_ns_SC = re.compile(r"(nosetting|<@UCCQ7MNEQ>) show channels", re.IGNORECASE)
pat_ns_SR = re.compile(r"(nosetting|<@UCCQ7MNEQ>) show responses", re.IGNORECASE)
pat_ns_help = re.compile(r"(nosetting|<@UCCQ7MNEQ>) help", re.IGNORECASE)


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


def response_msg(channel, msg):
    post_msg(msg, channel=channel)


def post_rand_msg(channel, lis):
    post_msg(random.choice(lis), channel=channel)


def response(rtm):
    if rtm["text"] in enable_responses:
        if isinstance(enable_responses[rtm["text"]], str):
            response_msg(rtm["channel"], enable_responses[rtm["text"]])
        else:
            post_rand_msg(rtm["channel"], enable_responses[rtm["text"]])


def extract_command(pattern, text):
    return pattern.sub("", text, count=1)

# やってみるとどうか
# - [ ] (nosetting|@nosponse) respondを取り除いてresとmesに分けてるところをextract_commandを使うようにする
# - [ ] if not hoge: return で抜けられるなら抜けるようにする
# - [ ] 変数名分かりにくかったらいい感じにする
# - [x] deleteコマンドを追加する
# - [ ] rtm使うのやめてtextだけにする

def add_respond(rtm):
    if not pat_ns_res.match(rtm["text"]):
        return
    # (nosetting|@nosponse) respondを取り除いてる
    command = extract_command(pat_ns_res, rtm["text"])
    try:
        res, mes = re.split(r" to ", command, maxsplit=1, flags=re.IGNORECASE)
    except ValueError as e:
        response_msg(rtm["channel"], "Error!")
        return

    res = res.strip()
    mes = mes.strip()
    if mes == "":
        response_msg(rtm["channel"], "Error!")
        return
    enable_responses[mes] = res
    dicjdump(enable_responses, responses_json_path)
    response_msg(rtm["channel"], "Success!")


def delete_response(rtm):
    if not pat_ns_delete_res.match(rtm["text"]):
        return
    command = extract_command(pat_ns_delete, rtm["text"])
    mes = command.strip()
    if mes in enable_responses:
        del enable_responses[mes]
        response_msg(rtm["channel"], "Deleted the response!")
        dicjdump(enable_responses, responses_json_path)
    else:
        response_msg(rtm["channel"], "Error!")
    
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
    response_msg(rtm["channel"], "Error!")
    return
for li in range(len(list)):
    list[li] = list[li].strip()
    if list[li] == "":
        response_msg(rtm["channel"], "Error!")
        return
mes = list.pop(0)
res = list
"""

def add_rand_respond(rtm):
    if not pat_ns_rnd.match(rtm["text"]):
        return
    command = extract_command(pat_ns_rnd, rtm["text"])
    try:
        mes, *res = command.split("\n")
    except ValueError as e:
        response_msg(rtm["channel"], "Error!")
        return
    if len(res) == 0:
        response_msg(rtm["channel"], "Error!")
        return
    enable_responses[mes] = res
    dicjdump(enable_responses, responses_json_path)
    response_msg(rtm["channel"], "Success!")


def modify_rand_respond(rtm):
    if not pat_ns_rnd_add.match(rtm["text"]):
        return
    command = extract_command(pat_ns_rnd_add, rtm["text"])
    mes, *res = command.split("\n")
    try:
        mes, *res = command.split("\n")
    except ValueError as e:
        response_msg(rtm["channel"], "Error!")
        return
    if len(res) == 0:
        response_msg(rtm["channel"], "Error!")
        return
    if mes not in enable_responses:
        response_msg(rtm["channel"], "not exist such response.")
        return
    if isinstance(enable_responses[mes], str):
        enable_responses[mes] = [enable_responses[mes]]
    enable_responses[mes].extend(res)
    dicjdump(enable_responses, responses_json_path)
    response_msg(rtm["channel"], "Success!")


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


def show_details(rtm):
    if pat_ns_SC.match(rtm["text"]):
        ch_link = []
        channels = get_joining_channels()
        for ch in channels.keys():
            ch_link.append("<#" + ch + "|" + channels[ch]+">")
        response_msg(rtm["channel"], pprint.pformat(ch_link, indent=4))
    elif pat_ns_SR.match(rtm["text"]):
        #res = pprint.pformat(enable_responses, indent=4)
        #post_attachment(escape_uid(res), rtm["channel"])
        response_msg(rtm["channel"], "https://inside.kmc.gr.jp/~nos/app/nosponse/")


def show_help(rtm):
    if not pat_ns_help.match(rtm["text"]):
        return
    response_msg(rtm["channel"], "<@UCCQ7MNEQ> がinviteされているチャンネルで有効です。\n"\
    "`(nosetting|<@UCCQ7MNEQ>) respond A to B` : BにAと返す反応を追加します。\n"\
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


def dicjdump(dic, _file):
    with open(_file, "w", encoding="utf-8") as filed:
        json.dump(dic, filed, indent=4, ensure_ascii=False)


def file2list(_file):
    with open(_file, "r", encoding="utf-8") as filed:
        ret = list(filed)
    return ret


def main_process(rtm):
    response(rtm)
    add_respond(rtm)
    delete_response(rtm)
    show_details(rtm)
    show_help(rtm)
    add_rand_respond(rtm)
    modify_rand_respond(rtm)


if __name__ == "__main__":
    enable_responses = j_file2dic(responses_json_path)
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
                print(str(datetime.datetime.now) + ":")
                print(sys.exc_info()[0])
                time.sleep(2)
                if sc.rtm_connect():
                    post_msg(random.choice([":nos: 再接続完了デース！", ":nos: 接続しなおしておきマシタ！"]), nos_memo_id)
                else:
                    print("Connection Failed!")
                    time.sleep(100)
            time.sleep(0.5)
    else:
        print("Connection Failed")
