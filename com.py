import sys
import time
import datetime
import pyodbc
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
from datetime import timedelta

#  1.04  23/04/14

SEARCH_NON  = 0    # 見つからない   
SEARCH_NG  = 1     # 貸出中
SEARCH_OK  = 2     # 貸出可
SEARCH_DUP  = 3    # 複数ヒット
SEARCH_MANY  = 4   # ヒット件数多すぎ

def login(userid,passwd,drv) :
    login_url = 'https://www.lib.city.kobe.jp/winj/opac/login.do'
    drv.get(login_url)
    time.sleep(2)
    #cookies = driver.get_cookies()
    drv.get(login_url)    # 2回やらないと セッションタイムアウト になる

    html = drv.page_source
    username = drv.find_element(By.NAME,"txt_usercd")
    username.send_keys(userid)
    passwd_ele = drv.find_element(By.NAME,"txt_password")
    passwd_ele.send_keys(passwd)
    next_btn = drv.find_element(By.NAME,"submit_btn_login")
    next_btn.click()


#  文字列 を 日付型に変換
def str_to_date(s) :
    s = s.strip()
    date_dt = datetime.datetime.strptime(s, '%Y.%m.%d')
    tdate = datetime.date(date_dt.year, date_dt.month, date_dt.day)
    return(tdate)

def init_selenium(browser,selenium):
    options = Options()
    options.binary_location = browser
    options.add_argument('--headless')
    chrome_service = fs.Service(executable_path=selenium) 
    drv = webdriver.Chrome(options=options,service=chrome_service)
    return drv

def read_userinfo(userfile) : 

    uinfo = []
    f = open(userfile,'r', encoding='utf-8')
    while True:
        s = f.readline().strip()
        if s == '' :
            break 
        user = {}
        user['id'],user['pass'] = s.split('\t')
        uinfo.append(user)
    f.close()
    return uinfo

def read_config(conffile) : 
    config = {}
    conf = open(conffile,'r', encoding='utf-8')
    config['browser'] = conf.readline().strip()
    config['selenium'] = conf.readline().strip()
    config['dbfile'] = conf.readline().strip()
    config['linetoken'] = conf.readline().strip()
    conf.close()
    return config

def search_by_title(title,driver) :
    title = title.replace(":"," ")    # : があるとヒットしない
    url = "https://www.lib.city.kobe.jp/winj/opac/search-detail.do"
    driver.get(url)
    word = driver.find_element(By.NAME,"txt_word1")
    word.send_keys(title)
    btn = driver.find_element(By.NAME,"submit_btn_searchDetailSelAr")
    btn.click()
    html = driver.page_source
    ret = analize_info(html)
    return ret

def search_by_bibid(bibid,driver) :
    url = f"https://www.lib.city.kobe.jp/winj/opac/switch-detail.do?lang=ja&bibid={bibid}"
    driver.get(url)
    html = driver.page_source
    ret = analize_info(html)
    return ret    

def analize_info(html) :
    # 返却値は4個   本の状態、所蔵冊数、予約件数、書誌番号
    top = BeautifulSoup(html, 'html.parser')
    st = ""
    if "該当するリストが存在しません" in top.text :
        return SEARCH_NON,0,0,""
    if "ヒット件数が多すぎます" in top.text :
        return SEARCH_MANY,0,0,""
    h3_all = top.find('h3',class_='nav-hdg')
    if h3_all is not None :
        return SEARCH_DUP,0,0,""
    span_tag = top.find('span',class_='icon-lent')
    if span_tag is not None :
        st = SEARCH_NG
    span_tag = top.find('span',class_='icon-others')  # 貸出不可
    if span_tag is not None :
        st = SEARCH_NG
    span_tag = top.find('span',class_='icon-borrow')
    if span_tag is not None :
        st = SEARCH_OK

    em_all = top.find_all('em', class_='em-02')
    bibid  = ""    #  雑誌の場合は書誌番号がないため "" を返す
    table = top.find('table',class_='tbl-04')
    if table == None :  #  アクセスエラー
        print(f'ERROR table tag')
        debug_out("tagerr.htm",html)
        #sys.exit(1)
        return -1,0,0,""
    tr_all = table.find_all('tr')
    for tr in tr_all :
        th = tr.find('th')
        if th.text == '書誌番号' :
            td = tr.find('td')
            bibid = td.text
    if st == "" :
        print("ERROR st is None")
        debug_out("sterr.htm",html)
        sys.exit(1)
    return st,int(em_all[0].text),int(em_all[1].text),bibid

def read_database(conn_str,sql):
    data = [] 
    #conn_str = conn_temp.replace("xxxxxx",dbfile)
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    rows = cursor.execute(sql).fetchall()
    i = 0 
    for r in rows :
        data.append(f'{r[1]}\t{r[9]}\t{r[10]}')   # 書名、登録年月、備考(書誌番号)
    return data 

def debug_out(filename,html) :
    out = open(filename,'w',  encoding='utf-8')
    out.write(html)
    out.close()

