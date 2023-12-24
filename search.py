import time
import os
import sys
import datetime
import subprocess
import argparse
import com
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
from selenium.webdriver.support.select import Select

version = "1.10"    # 23/05/03
appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "./panda.conf"
templ_name = appdir + "./searchtmpl.htm"
result_file = appdir + "./searchres.htm"
result_list = []

SEARCH_NON  = 0    # 見つからない   
SEARCH_NG  = 1     # 貸出中
SEARCH_OK  = 2     # 貸出可
SEARCH_DUP  = 3    # 複数ヒット
SEARCH_MANY  = 4   # ヒット件数多すぎ
state_count = {}
state_count[SEARCH_NON] = 0 
state_count[SEARCH_OK] = 0 

conn_temp = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    r'DBQ=xxxxxx;'
    )
dbfile = ""
dbdata = []    # DBから読み込んだデータ  書名、登録年月、備考(書誌番号)

flg_display = False

def main_proc() :
    global today_date,browser,selenium,dbfile,start_time,driver

    start_time  = time.time()
    today_date = datetime.date.today()
    argument()

    config = com.read_config(conffile)
    browser = config['browser']
    selenium = config['selenium']
    dbfile = config['dbfile']
    if flg_display :
        result = subprocess.run((browser, result_file))
        return

    driver = com.init_selenium(browser,selenium)
    init_search()
    check_exsist()
    parse_template(templ_name,result_file)
    result = subprocess.run((browser, result_file))

def argument() :
    global  flg_display
    parser = argparse.ArgumentParser() 
    parser.add_argument('-d',action='store_true', help="display only") 
    args = parser.parse_args()
    if args.d :
        flg_display = True

def init_search() :
    url = "https://www.lib.city.kobe.jp/winj/opac/search-detail.do"
    driver.get(url)

#   DBの本が図書館にあるかチェックする
def check_exsist() :
    global dbdata
    sql = "SELECT * FROM [main] WHERE [図] is null"
    conn_str = conn_temp.replace("xxxxxx",dbfile)
    dbdata = com.read_database(conn_str,sql)
    #out = open("report.txt",'w',  encoding='utf-8')
    for row in dbdata :
        t = row.split("\t")[0]
        ret = com.search_by_title(t,driver)
        st = ret[0]
        if st == -1 :
            print("ERROR search access")
            sys.exit(1)
        count = ret[1]
        resv = ret[2]
        if st == SEARCH_NON :     # 存在しなければ何もしない
            state_count[SEARCH_NON] +=  1
            continue 
        result_item = {}
        result_item['title'] = t 
        result_item['state'] = st
        if st == SEARCH_NG or st == SEARCH_OK :
            result_item['count'] = count
            result_item['resv'] = resv
            state_count[SEARCH_OK] +=  1   # 貸出中か貸出OKかは区別しない

        result_list.append(result_item)
        # if st == SEARCH_DUP :
        #     msg = "重複"
        # if st == SEARCH_MANY :
        #     msg = "多数"
        # if st == SEARCH_NG or st == SEARCH_OK :
        #     msg = f"★所蔵★ 冊数 {count}  予約数 {resv}"
        #out.write(f'{msg} {t}\n')
    #out.close()
    print(result_list)

def output_result() :
    i = 0 
    for res in result_list :
        i = i+1
        st = res['state'] 
        str_count = ""
        str_resv  = ""
        if st  == SEARCH_DUP :
            mes = "重複"
        if st  == SEARCH_MANY :
            mes = "多数"
        if st  == SEARCH_NG or st  == SEARCH_OK  :
            mes = "所蔵"
            str_count = res['count'] 
            str_resv = res['resv'] 
        out.write(f"<tr><td>{i}</td><td>{res['title'] }</td><td>{mes}</td><td>{str_count}</td><td>{str_resv}</td></tr>")
    pass

def output_state_count(line) :
    all = state_count[SEARCH_OK] + state_count[SEARCH_NON]
    s = f'検索件数 {all}  蔵書あり {state_count[SEARCH_OK]} '
    s = line.replace("%stat%",s)
    out.write(s)

def today(s) :
    d = today_date.strftime("%m/%d %H:%M")
    s = s.replace("%today%",d)
    out.write(s)    

def parse_template(templ_name,result_name) :
    global out 
    f = open(templ_name , 'r', encoding='utf-8')
    out = open(result_name,'w' ,  encoding='utf-8')
    for line in f :
        if "%report_list%" in line :
            output_result()
            continue
        if "%version%" in line :
            s = line.replace("%version%",version)
            out.write(s)
            continue
        if "%today%" in line :
            today(line)
            continue
        if "%stat%" in line :
            output_state_count(line)
            continue
        if "%elapsetime%" in line:
            ela = time.time() - start_time
            ela_min = int(ela / 60)
            ela_sec = int(ela) % 60
            ela_str = f'{ela_min}:{ela_sec:02}'
            s = line.replace("%elapsetime%",ela_str)
            out.write(s)
            continue

        out.write(line)

    f.close()
    out.close()

#----------------------
main_proc()
