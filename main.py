# coding: utf-8

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

slack_token = os.environ["SLACK_API_TOKEN"]
sc = SlackClient(slack_token)

pat_ns_res = re.compile(r"nosetting respond",re.IGNORECASE)
pat_ns_rnd = re.compile(r"nosetting randomres",re.IGNORECASE)
pat_ns_SC = re.compile(r"nosetting show Channels",re.IGNORECASE)
pat_ns_SR = re.compile(r"nosetting show responses",re.IGNORECASE)
pat_ns_AC = re.compile(r"nosetting addThisChannel",re.IGNORECASE)
pat_ns_DC = re.compile(r"nosetting disableThisChannel",re.IGNORECASE)
pat_ns_help = re.compile(r"nosetting help",re.IGNORECASE)
pat_space = re.compile(r"^\s+")
pat_space2 = re.compile(r"\s+$")

def postMsg(msg, channel,unfurl=True):
    sc.api_call(
        "chat.postMessage",
        channel=channel,
        text=msg,
        icon_emoji=":mawarunos:",
        unfurl_links=unfurl,
        username="nosponse"
    )
def responseMsg(rtm, msg):
    postMsg(msg, channel=rtm["channel"])

def postRandMsg(rtm, lis):
    postMsg(random.choice(lis), channel=rtm["channel"])

def response(rtm):
    if rtm["text"] in enableResponses:
        if isinstance(enableResponses[rtm["text"]], str):
            responseMsg(rtm, enableResponses[rtm["text"]])
        else:
            postRandMsg(rtm, enableResponses[rtm["text"]])

def addRespond(rtm):
    if pat_ns_res.match(rtm["text"]):
        string = pat_ns_res.sub("",rtm["text"],count=1)
        list = re.split(r" to ", string ,maxsplit=1, flags=re.IGNORECASE)
        if len(list) != 2:
            responseMsg(rtm,"Error!")
            return
        res = list[0]
        mes = list[1]
        res = pat_space.sub("",res)
        mes = pat_space.sub("",mes)
        res = pat_space2.sub("",res)
        mes = pat_space2.sub("",mes)
        if mes == "":
            responseMsg(rtm,"Error!")
            return
        if res == "":
            if mes in enableResponses:
                del enableResponses[mes]
                responseMsg(rtm,"Deleted the response!")
                dicjdump(enableResponses,"responses.json")
                return
            responseMsg(rtm,"Error!")
            return
        enableResponses[mes] = res
        dicjdump(enableResponses,"responses.json")
        responseMsg(rtm,"Success!")

def addRandrespond(rtm):
    if pat_ns_rnd.match(rtm["text"]):
        string = pat_ns_rnd.sub("",rtm["text"],count=1)
        list = re.split(r"\n", string)
        if len(list) <=2:
            responseMsg(rtm,"Error!")
            return
        for li in range(len(list)):
            list[li] = pat_space.sub("",list[li])
            list[li] = pat_space2.sub("",list[li])
            if list[li] == "":
                responseMsg(rtm,"Error!")
                return
        mes = list.pop(0)
        res = list
        enableResponses[mes] = res
        dicjdump(enableResponses,"responses.json")
        responseMsg(rtm,"Success!")
        
def showDetails(rtm):
    if pat_ns_SC.match(rtm["text"]):
        ch_link = []
        for chs in enableChannels.keys():
            ch_link.append("<#" + chs +"|"+ enableChannels[chs]+">")
        responseMsg(rtm,pprint.pformat(ch_link, indent=4))
    if pat_ns_SR.match(rtm["text"]):
        res = pprint.pformat(enableResponses, indent=4)
        postMsg(escape_uid(res), rtm["channel"], unfurl=False)

def addChannel(rtm, inCh):
    if pat_ns_AC.match(rtm["text"]):
        enableChannels[rtm["channel"]] = get_channel_name(rtm["channel"])
        dicjdump(enableChannels,"enable_channels.json")
        if inCh:
            responseMsg(rtm,"Updated!")
        else:
            responseMsg(rtm,"Success!")

def disChannel(rtm):
    if pat_ns_DC.match(rtm["text"]):
        del enableChannels[rtm["channel"]]
        dicjdump(enableChannels,"enable_channels.json")
        responseMsg(rtm,"Success!")

def showhelp(rtm):
    if pat_ns_help.match(rtm["text"]):
        responseMsg(rtm,"`nosetting respond A to B` : BにAと返す反応を追加します。\n"+"`nosetting randomres A \\n B\\n C\\n ...` : Aに対してB,C...をランダムに返す反応を追加します。\n"+"`nosetting addThisChannel` : そのチャンネルでこのbotを有効化します。\n"+"`nosetting disableThisChannel` : そのチャンネルでこのbotを無効化します。\n"+"`nosetting show Channels` : このbotが有効なチャンネルを表示します。\n"+"`nosetting show responses` : 設定されている反応を表示します。")

def get_channel_name(channelid):
    channelname = ""
    ch_list = sc.api_call("channels.list",exclude_archived=True,exclude_members=True)
    if ch_list["ok"]:
        for channel in ch_list["channels"]:
            if channel["id"] == channelid:
                channelname = channel["name"]
                return channelname
        return "not found"

def get_channel_id(channelname):
    channelid = ""
    ch_list = sc.api_call("channels.list",exclude_archived=True,exclude_members=True)
    if ch_list["ok"]:
        for channel in ch_list["channels"]:
            if channel["name"] == channelname:
                channelid = channel["id"]
                return channelid
        return "not found"

def get_user_name(userid):
    username = ""
    u_list = sc.api_call("users.list")
    if u_list["ok"]:
        for user in u_list["members"]:
            if user["id"] == userid:
                username = user["name"]
                return username
        return "not found"

def escape_uid(text):
    res = text.replace("!","！")
    for found in re.findall(r"<@(.*?)>", text):
        res = res.replace(found, get_user_name(found))
    res = res.replace("@","＠")
    return res

def postKaren(Karen_lines):
    postMsg(random.choice(Karen_lines), "C61K9HKDM")

def set_interval(func, delay,sleep_time,*param):
    def body():
        time.sleep(sleep_time)
        while True:
            func(*param)
            time.sleep(delay)
    t = threading.Thread(target=body,daemon=True)
    t.start()

def set_interv_athour(func, delay, at_hour,_param): # 諸事情によりパラメータ一つしか指定できず
    atdt = datetime.datetime.now().replace(hour=at_hour,minute=0,second=0)
    if atdt < datetime.datetime.now():
        atdt = atdt + datetime.timedelta(days=1)
    sleeptime = (atdt - datetime.datetime.now()).seconds
    set_interval(func,delay,sleeptime,_param)

def jfile2dic(_file):
    with open(_file, "r", encoding="utf-8") as filed:
        dic = json.load(filed)
    return dic
def dicjdump(dic,_file):
    with open(_file,"w",encoding="utf-8") as filed:
        json.dump(dic,filed,indent=4)
def file2list(_file):
    with open(_file,"r",encoding="utf-8") as filed:
        _list = list(filed)
    return _list


enableChannels = jfile2dic("enable_channels.json")
enableResponses = jfile2dic("responses.json")
Karen_lines = file2list("Karen_morning.txt")

if sc.rtm_connect():
    for ch in enableChannels.keys():
        enableChannels[ch] = get_channel_name(ch)
    set_interv_athour(postKaren, 86400,8,Karen_lines)
    while True:
        try:
            for rtm in sc.rtm_read():
                if rtm["type"] == "message":
                    if "subtype" not in rtm and "text" in rtm:
                        inCh = rtm["channel"] in enableChannels
                        if inCh:
                            response(rtm)
                            addRespond(rtm)
                            disChannel(rtm)
                            showDetails(rtm)
                            showhelp(rtm)
                            addChannel(rtm, inCh)
                            addRandrespond(rtm)
                        else:
                            addChannel(rtm, inCh)
        except websocket._exceptions.WebSocketConnectionClosedException:
            if sc.rtm_connect():
                postMsg(random.choice([":nos: 再接続完了デース！",":nos: 接続しなおしておきマシタ！"]), "C61K9HKDM")
            else:
                print("Connection Failed!")
                break
        time.sleep(1)
else:
    print("Connection Failed")