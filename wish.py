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

version = "1.06"    # 24/08/24
appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "./panda.conf"
wishlistfile = appdir + "./wishlist.htm"
wish_templatefile = appdir + "./wishtmpl.htm"
cachefile = appdir + "./cache.txt"     # 過去の検索した情報ファイル
resv_title_list = []     #  予約中のタイトルリスト  wishlist で予約中のものは色を変えるため
infofile = appdir + "./info"

SEARCH_NON  = 0    # 見つからない   
SEARCH_NG  = 1     # 貸出中
SEARCH_OK  = 2     # 貸出可
SEARCH_DUP  = 3    # 複数ヒット
SEARCH_MANY  = 4   # ヒット件数多すぎ

conn_temp = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    r'DBQ=xxxxxx;'
    )
dbfile = ""
dbdata = []    # DBから読み込んだデータ  書名、登録年月、備考(書誌番号)
cachelist = []  # 過去の検索した情報   title adddate bibid count resv
state_count = {}
state_count[SEARCH_OK] = 0 
state_count[SEARCH_NG] = 0 

flg_display = False
startyymm = 0 

def main_proc() :
    global today_date,browser,selenium,dbfile,start_time,driver

    start_time  = time.time()
    today_date = datetime.date.today()
    argument()
    config = com.read_config(conffile)
    browser = config['browser']
    selenium = config['selenium']
    dbfile = config['dbfile']

    driver = com.init_selenium(browser,selenium)
    init_search()
    wish_list()

def argument() :
    global  flg_display,startyymm
    parser = argparse.ArgumentParser() 
    parser.add_argument('-d',action='store_true', help="display only") 
    parser.add_argument('-t', type=int, default=0,help="check start yymm")
    args = parser.parse_args()
    if args.d :
        flg_display = True
    if args.t :
        startyymm = args.t 

def init_search() :
    url = "https://www.lib.city.kobe.jp/winj/opac/search-detail.do"
    driver.get(url)

def wish_list():
    global dbdata
    if flg_display :
        result = subprocess.run((browser, wishlistfile))
        return

    read_cachefile()
    sql = "SELECT * FROM [main] WHERE [図] = 'Z' order by [登録日];"
    conn_str = conn_temp.replace("xxxxxx",dbfile)
    dbdata = com.read_database(conn_str,sql)
    read_info_file()
    parse_template(wish_templatefile,wishlistfile)
    result = subprocess.run((browser, wishlistfile))

def output_wish_list() :
    biburl = "https://www.lib.city.kobe.jp/winj/opac/switch-detail.do?lang=ja&bibid="
    i = 0 
    bibout = open(cachefile,'w',  encoding='utf-8')
    for row in dbdata :
        i = i + 1 
        dt = row.split("\t")
        title,add,bib = dt  
        title = title.replace('\u203c',' ')
        title = title.replace('\u5653',' ')

        adddate = 0 
        st = -1
        if dt[1] != None :
            adddate = int(add)
        if adddate < startyymm :     # 指定年月より前はキャッシュから情報を得る
            ret = search_cachelist(title)
            if ret == "" :      #  キャッシュにない場合
                count = "--"
                resv = "--"
                bibid = ""
                prev_resv = -1
            else :
                _,_,bibid,count,resv = ret.split("\t")   # title,adddate,bibid,count,resv
                prev_resv = int(resv)
        else :
            if bib != "None" :       # DBに書誌番号が入っている場合は書誌番号で検索する
                ret = com.search_by_bibid(bib,driver)
            else :
                ret = search_by_title_repetition(title)
            st,count,resv,bibid = ret
            prevdata = search_cachelist(title)
            if prevdata != "" :
                prev_resv = int(prevdata.split("\t")[4])
            else :
                prev_resv = -1

        if st == -1 :   # 未定義  指定年月より前の場合
            cell_bg = ""
            msg = ""
        else :
            msg,cell_bg = status_massage(st)

        color_title = title 
        if check_resv_title_list(title) :    # 予約済みのタイトルは色を変える
            color_title = f'<span class=green>{title}</span>'

        titlelnk = color_title
        if bibid != "" :
            titlelnk = f'<a href="{biburl}{bibid}" target="_blank">{color_title}</a>'
        if prev_resv == -1 :
            color_resv = f'{resv}(-)'
        elif  int(resv) > prev_resv :
            color_resv = f'<span class=red>{resv}</span>({prev_resv})'
        else :
            color_resv = f'{resv}({prev_resv})'
        out.write(f"<tr><td align=right>{i}</td><td>{titlelnk}</td><td {cell_bg}>{msg}</td>"
                  f"<td align=right>{count}</td>"
                  f"<td align=right>{color_resv}</td><td align=right>{adddate}</td></tr>\n")
        if bibid != "" :
            bibout.write(f"{title}\t{add}\t{bibid}\t{count}\t{resv}\n")
    bibout.close()        

def read_info_file() :
    global resv_title_list
    for u in range(2)  :  # ユーザ数 2 に決めうち
        f = open(f'{infofile}{u}.txt','r',  encoding='utf-8')
        _ = f.readline()
        for line in f:
            resv_title_list.append(line.split("\t")[0].strip())        

def check_resv_title_list(title) :
    main_title = title.split()[0]
    for t in  resv_title_list :
        if main_title in t :
            return True
    return False 

def search_by_title_repetition(t) :
    for _ in range(4)  :    # エラー時のリトライは2回
        ret = com.search_by_title(t,driver)
        if ret[0] != -1 :   # st 
            return ret  
        time.sleep(30)     # エラーなら30秒まってリトライ
    else :
        print(f"ERROR search access {t}")
        return -1,0,0,0
        #sys.exit(1)

def status_massage(st) :
    global state_count
    cell_bg = ""
    if st == SEARCH_NON :     
        msg = f'<span class=red>未所蔵</span>'
        cell_bg = "style='background: #f7d9d5'"
    if st == SEARCH_DUP :
        msg = f'<span class=red>重複</span>'
        cell_bg = "style='background: #f7d9d5'"
    if st == SEARCH_MANY :
        msg = f'<span class=red>多数</span>'
        cell_bg = "style='background: #f7d9d5'"
    if st == SEARCH_NG  :
        msg = f'<span class=red2>貸出中</span>'
        state_count[SEARCH_NG] =  state_count[SEARCH_NG] + 1 
    if st == SEARCH_OK :
        msg = f'<span class=blue2>在庫</span>'
        state_count[SEARCH_OK] =  state_count[SEARCH_OK] + 1 

    return msg,cell_bg

def read_cachefile():
    global cachelist
    if not os.path.exists(cachefile) :
        return
    f = open(cachefile,'r',  encoding='utf-8')
    for line in f:
        cachelist.append(line)
    f.close()

def search_cachelist(t) :    # タイトルでキャッシュを検索
    for line in cachelist :
        line = line.strip()
        if t == line.split("\t")[0] :
            return line
    return ""

def output_state_count(line) :
    all = state_count[SEARCH_OK] + state_count[SEARCH_NG]
    s = f'全件数 {all}  貸出OK {state_count[SEARCH_OK]} ({state_count[SEARCH_OK]*100/all:.2f}%)'
    s = line.replace("%stat%",s)
    out.write(s)

def parse_template(templ_name,result_name) :
    global out 
    f = open(templ_name , 'r', encoding='utf-8')
    out = open(result_name,'w' ,  encoding='utf-8')
    for line in f :
        if "%wish_list%" in line :
            output_wish_list()
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

def today(s) :
    d = today_date.strftime("%m/%d %H:%M")
    s = s.replace("%today%",d)
    out.write(s)    

#----------------------
main_proc()
