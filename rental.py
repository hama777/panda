import os
import time
import re
import datetime
import locale
import subprocess
import argparse
import com
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
from datetime import timedelta

# 25/03/16 v1.03 v134よりログイン処理を2回実行しないと最初のユーザデータがとれない
version = "1.03"
appdir = os.path.dirname(os.path.abspath(__file__))
userfile = appdir + "./user.txt"
conffile = appdir + "./panda.conf"
resv_resultfile = appdir + "./resvlist.htm"
resv_templatefile = appdir + "./resvtmpl.htm"
rental_resultfile = appdir + "./rentallist.htm"
rental_templatefile = appdir + "./rentaltmpl.htm"
infofile = appdir + "./info"
histfile = appdir + "./hist"

debug = 0
browser = ""
selenium = ""
driver = ""
user_rental_list = [] # ユーザごとの貸出リスト
rental_list = []      # 全ユーザの貸出リスト
userinfo = []         # ID pass
hist_list = []        # 全ユーザの履歴情報

out = ""
num_output = 0    # output_resv_list の何回目の呼び出しか
today_date = ""
flg_display = False  # ブラウザでの表示のみ

def main_proc():
    global today_date,browser,selenium,userinfo,start_time,driver
    start_time  = time.time()
    locale.setlocale(locale.LC_TIME, '')
    today_date = datetime.date.today()
    argument()
    userinfo = com.read_userinfo(userfile)
    config = com.read_config(conffile)
    browser = config['browser']
    selenium = config['selenium']

    driver = com.init_selenium(browser,selenium)
    proc_rental_list()

def argument() :
    global  flg_display
    parser = argparse.ArgumentParser() 
    parser.add_argument('-d',action='store_true' ,help="display only") 
    args = parser.parse_args()
    if args.d :
        flg_display = True

#################################################
#    貸出リスト
#################################################

def proc_rental_list():
    global rental_list,user_rental_list
    if flg_display :
        result = subprocess.run((browser, rental_resultfile))
        return
    for u in userinfo :
        com.login(u['id'],u['pass'],driver)
        com.login(u['id'],u['pass'],driver)   # v134よりなぜか2回実行しないと最初のユーザデータがとれない
        user_rental_list = []
        access_rental()
        rental_list.append(user_rental_list)
    
    parse_template(rental_templatefile,rental_resultfile)
    result = subprocess.run((browser, rental_resultfile))

def access_rental() :

    rental_url = "https://www.lib.city.kobe.jp/winj/opac/lend-list.do"
    driver.get(rental_url)
    html = driver.page_source
    analize_rental(html)

def analize_rental(html) :
    global user_rental_list

    title_list = []
    re_str = "貸出日:(.*?)返却予定日:(.*?)予約:(.*?)件延長回数:(.*?)件"
    top = BeautifulSoup(html, 'html.parser')
    h4_all = top.find_all('h4', class_='link-image')
    for h4 in h4_all :
        atag = h4.find("a")
        title_list.append(format_title(atag.text))

    attr_list = []
    info_list = []
    extension_list = []     # 貸出延長可かどうか
    div_all = top.find_all('div', class_='column info')
    for div in div_all :
        p_all = div.find_all("p")
        info = p_all[0].text.replace('\n','').replace('--','')
        info_list.append(info)

        p = p_all[1].text
        p = p.replace('\n','').replace('\xa0',' ')
        attr_list.append(p)

    #  貸出延長可かどうかは 貸出延長ボタンがあるかで判断する  
    #  予約数0でも貸出延長可の場合もあるので予約数では判断できない
    div_info = top.find_all('div', class_=['info'])
    #  上記では 'column info' にもヒットするのでこれを取り除く
    filtered_results = [result for result in div_info if result.get("class") == ["info"]]
    for div in filtered_results :
        extension = div.find("a", class_='btn-02')  # 貸出延長ボタン
        flg = True
        if extension == None :
            flg = False
        extension_list.append(flg)

    for title,attr,info,ext in zip(title_list,attr_list,info_list,extension_list) :
        rental_item = {}
        rental_item['title'] = title

        m = re.search(re_str, attr)
        rental_item['rental_date'] = str_to_date(m.group(1))
        rental_item['limit'] = str_to_date(m.group(2))
        rental_item['resv_cnt'] = int(m.group(3))
        rental_item['extension'] = int(m.group(4))
        rental_item['info'] = info
        rental_item['enable_extension'] = ext
        user_rental_list.append(rental_item)

def output_rental_list() :
    global num_output   

    i = 0 
    r_list = rental_list[num_output]
    for r in r_list :
        i = i + 1 
        ext = "<span class=red>延長済み</span>"
        if r['extension'] == 0 :
            ext = ""
        l_date = r['limit'].strftime("%m/%d (%a)")
        if r['limit'] < today_date :     # 期限すぎたら赤字
            l_date = f'<span class=red>{l_date}</span>'
        
        if r['resv_cnt'] == 0 :
            resv = "<span class=blue>なし</span>"
        else :
            resv = r['resv_cnt']
        flg = ""
        if r['enable_extension']  :
            flg = "<span class=blue>可</span>"
        out.write(f"<tr><td align=right>{i}</td><td>{r['title']} {r['info']}</td>"
                  f"<td>{l_date}</td><td align=right>{resv}</td><td align=right>{flg}</td><td>{ext}</td></tr>")

    num_output = num_output + 1

#################################################
#    共通
#################################################

def format_title(t):
    t = t.replace('\n','').replace('\xa0',' ')
    t = t.replace('\u5653',' ')
    t = t.replace('【図書】','').replace('【雑誌】','')
    return(t)

def today(s) :
    d = datetime.datetime.now().strftime("%m/%d %H:%M")
    s = s.replace("%today%",d)
    out.write(s)    

def parse_template(templ_name,result_name) :
    global out 
    f = open(templ_name , 'r', encoding='utf-8')
    out = open(result_name,'w' ,  encoding='utf-8')
    for line in f :
        if "%rental_list%" in line :
            output_rental_list()
            continue
        if "%version%" in line :
            s = line.replace("%version%",version)
            out.write(s)
            continue
        if "%today%" in line :
            today(line)
            continue
        if "%elapsetime%" in line:
            ela = time.time() - start_time
            ela = f'{ela:.2f}'
            s = line.replace("%elapsetime%",ela)
            out.write(s)
            continue

        out.write(line)

    f.close()
    out.close()

#  文字列 を 日付型に変換
def str_to_date(s) :
    s = s.strip()
    date_dt = datetime.datetime.strptime(s, '%Y.%m.%d')
    tdate = datetime.date(date_dt.year, date_dt.month, date_dt.day)
    return(tdate)

#------------------------------------------------------
main_proc()
