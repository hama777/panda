import time
import os
import sys
import datetime
import requests
import com

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
from selenium.webdriver.support.select import Select

version = "1.03"    # 23/04/28
appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "./panda.conf"
magfile = appdir + "./mag.conf"   # チェックする雑誌名 
prevfile = appdir + "./mag.txt"
logfile = appdir + "./mag.log"
maglist = []       # チェックする雑誌名 リスト
prevdata = {}
token = ""
logf = ""

def main_proc() :
    global today_date,browser,selenium,token,logf,driver

    logf = open(logfile,'a',encoding='utf-8')
    logf.write("\n=== start %s === \n" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    today_date = datetime.date.today()
    config = com.read_config(conffile)
    browser = config['browser']
    selenium = config['selenium']
    token = config['linetoken']

    read_maglist()
    read_prevdata()
    driver = com.init_selenium(browser,selenium)
    init_search()
    check_magazine()

    logf.write("\n=== end %s === \n" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    logf.close()

def init_search() :
    url = "https://www.lib.city.kobe.jp/winj/opac/search-detail.do"
    driver.get(url)

#   
def check_magazine() :
    
    f = open(prevfile,'w',  encoding='utf-8')
    for t in maglist :
        new_magname = search_by_magagine(t)
        if t in prevdata :   # 雑誌の過去データがあれば
            prev_magname = prevdata[t]
            if new_magname != prev_magname :
                report(f'★New {new_magname}')
                logf.write(f"\n=== report {new_magname} === \n" )

        f.write(f'{t}\t{new_magname}\n')
    f.close()

def report(mes) :
    line_notify_token = token
    line_notify_api = 'https://notify-api.line.me/api/notify'
    payload = {'message': mes}
    headers = {'Authorization': 'Bearer ' + line_notify_token}  
    line_notify = requests.post(line_notify_api, data=payload, headers=headers)

def read_prevdata() :
    global prevdata
    if not os.path.isfile(prevfile) :
        return
    f = open(prevfile,'r',  encoding='utf-8')
    for line in f:
        line = line.strip()
        magname,prevname = line.split("\t")
        prevdata[ magname ] = prevname
    f.close()

def read_maglist() :
    f = open(magfile,'r',  encoding='utf-8')
    for line in f:
        maglist.append(line.strip())        
    f.close()


#  指定した雑誌の最新号のタイトルを返す
def search_by_magagine(title) :
    title = title.replace(":"," ")    # : があるとヒットしない
    url = "https://www.lib.city.kobe.jp/winj/opac/search-detail.do"
    driver.get(url)
    word = driver.find_element(By.NAME,"txt_word1")
    word.send_keys(title)
    catph = driver.find_element(By.ID,"chk_catph0")   #  図書 のチェックボックスをはずす
    catph.click() 
    btn = driver.find_element(By.NAME,"submit_btn_searchDetailSelAr")
    btn.click()
    html = driver.page_source
    #com.debug_out("magck.htm",html)
    ret = analize_magagine_info(html)
    return ret

def analize_magagine_info(html) :
    top = BeautifulSoup(html, 'html.parser')
    atag_all = top.find_all('a')   #  最初のタイトルを取得
    for atag in atag_all :
        a_title = atag.find('span', class_='title')   #  最初のタイトルを取得
        if a_title is None :
            continue
        title = a_title.text
        break
    title = title.strip().replace("\n","")
    return title

#----------------------
main_proc()
