import requests
import os
import sys
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
from ftplib import FTP_TLS

# 25/03/16 v1.24 v134よりログイン処理を2回実行しないと最初のユーザデータがとれない
version = "1.24"     
appdir = os.path.dirname(os.path.abspath(__file__))
userfile = appdir + "./user.txt"
conffile = appdir + "./panda.conf"
resv_resultfile = appdir + "./resvlist.htm"
resv_templatefile = appdir + "./resvtmpl.htm"
rental_resultfile = appdir + "./rentallist.htm"
rental_templatefile = appdir + "./rentaltmpl.htm"
estimatefile = appdir + "./esti.htm"

infofile = appdir + "./info"
histfile = appdir + "./hist"
prediction = appdir + "./prediction.txt"    # 貸出予測日

debug = 0
browser = ""
selenium = ""
driver = ""
user_resv_list = []   # ユーザごとの予約リスト
resv_list = []        # 全ユーザの予約リスト
user_rental_list = [] # ユーザごとの貸出リスト
rental_list = []      # 全ユーザの貸出リスト
userinfo = []         # ID pass
user_book_info_list = []        # 本の情報 所蔵冊数、予約件数
book_info_list = []        # 本の情報 所蔵冊数、予約件数
save_date = ""       # 本の情報を保存した日付
hist_list = []        # 全ユーザの履歴情報

out = ""
num_output = 0    # output_resv_list の何回目の呼び出しか
today_date = ""
flg_display = False  # ブラウザでの表示のみ
flg_rental  = False  # 貸出リストの処理
flg_info = False     # 本の情報(冊数、予約数)を取得する
flg_histo = False    # 履歴情報を出力する
flg_overwrite = False # 履歴ファイルを世代管理せず上書きする
max_gen = 6          # 履歴ファイル世代管理数  0,... 5
estimate_log = ""    # デバッグ

STATUS_OK = 0     # 利用可能
STATUS_DELI = 1   # 配送中
STATUS_NG = 2     # 返却待ち
STATUS_ORDER = 3  # 発注中
STATUS_REQ = 4    # 予約申込
STATUS_OTHER = 5  # 対応中

SEARCH_NON  = 0    # 見つからない   
SEARCH_NG  = 1     # 貸出中
SEARCH_OK  = 2     # 貸出可
SEARCH_DUP  = 3    # 複数ヒット

def main_proc():
    global today_date,browser,selenium,userinfo,start_time,driver,config

    start_time  = time.time()
    locale.setlocale(locale.LC_TIME, '')
    today_date = datetime.date.today()
    argument()
    userinfo = com.read_userinfo(userfile)
    config = com.read_config(conffile)
    browser = config['browser']
    selenium = config['selenium']

    driver = com.init_selenium(browser,selenium)
    proc_reserve_list()

def argument() :
    global  flg_display,flg_rental,flg_info,flg_histo,flg_overwrite
    parser = argparse.ArgumentParser() 
    parser.add_argument('-d',action='store_true' ,help="display only") 
    parser.add_argument('-r',action='store_true', help="rental list") 
    parser.add_argument('-i',action='store_true', help="get book infomation") 
    parser.add_argument('-his',action='store_true', help="output history info ") 
    parser.add_argument('-o',action='store_true', help="history file overwrite ") 
    args = parser.parse_args()
    if args.d :
        flg_display = True
    if args.i :
        flg_info = True
    if args.his :
        flg_histo = True
        flg_info = True      # 書誌番号を得るため
    if args.o :
        flg_overwrite = True

#################################################
#    予約リスト
#################################################
def proc_reserve_list():
    global resv_list,user_resv_list,book_info_list,user_book_info_list,estimate_log,predict
    if flg_display :
        result = subprocess.run((browser, resv_resultfile))
        return
    estimate_log = open(estimatefile,"w",encoding='utf-8')
    estimate_log.write("<table>")
    estimate_log.write("<tr><th>書名</th><th>順位</th><th>基準日付</th><th>基準順位</th>")
    estimate_log.write("<th>予測日</th><th>日/順位</th><th>日数</th><th>差分順位</th></tr>")

    predict  = open(prediction,"w",encoding='utf-8')

    for u in userinfo :
        com.login(u['id'],u['pass'],driver)
        com.login(u['id'],u['pass'],driver)  # v134よりなぜか2回実行しないと最初のユーザデータがとれない
        user_resv_list = []
        user_book_info_list = []
        access_reserve()
        resv_list.append(user_resv_list)
        if flg_info :
            book_info_list.append(user_book_info_list)

    if not flg_info :          #  -i でない時は前回実行結果から情報を取得 
        get_info_from_data()
    if flg_histo :
        output_histo_file()
    read_histo_data()
    parse_template(resv_templatefile,resv_resultfile)
    result = subprocess.run((browser, resv_resultfile))
    estimate_log.write("</table>")
    estimate_log.close()
    predict.close()
    output_info_file()          #  今回の情報を保存
    ftp_upload()

def access_reserve() :
    topurl ="https://www.lib.city.kobe.jp/winj/opac/reserve-list.do"

    for i in range(1,3) :    # 1,2
        if i == 1 :
            url = topurl 
        else :
            url = f'{url}?page={i}'
        driver.get(url)
        html = driver.page_source
        num_book = analize_reserve(html)    
        if flg_info :
            get_info(num_book)

#   対象エントリの件数を返す
def analize_reserve(html) :
    global user_resv_list

    re_resv_date  = "予約日:(.*?)受取館"
    re_status1 = "予約状態：(.*?)順番：(.*?)$"
    re_status2 = "予約状態：(.*?)取置期限日:(.*?)$"
    re_status3 = "予約状態：(.*?)$"

    top = BeautifulSoup(html, 'html.parser')
    div_report_all = top.find_all('div', class_='report')
    for div_report in div_report_all :
        resv_item = {}
        atag = div_report.find("a")
        resv_item['title'] = format_title(atag.text )

        ptag = div_report.find_all("p")
        info = ptag[0].text.replace('\n','').replace('--','')
        resv_item['info'] = info
        resv_date = ptag[1].text.replace('\n','')
        m = re.search(re_resv_date, resv_date)
        resv_date = m.group(1)

        resv_item['resv_date'] = str_to_date(resv_date)
        status = ptag[2].text.replace('\n','')
        status = status.replace(' ','').replace('\xa0',' ')
        m = re.search(re_status1, status)
        if m :
            status = STATUS_NG
            order = m.group(2)
            limit = ""
        else : 
            m = re.search(re_status2, status)
            if  m :
                status = STATUS_OK
                dt = m.group(2)
                if dt == " " :   # 取置期限日 がない場合がある
                    limit = ""
                else :
                    limit = str_to_date(dt)
                order = 0
            else :
                m = re.search(re_status3, status)
                if not m :
                    print(f"ERROR miss match {status}")
                    sys.exit(1)
                if m.group(1) == "発注中" :
                    status = STATUS_ORDER
                elif m.group(1) == "予約申込" :
                    status = STATUS_ORDER
                elif m.group(1) == "対応中" :
                    status = STATUS_OTHER
                else :
                    status = STATUS_DELI
                limit = ""
                order = 0

        resv_item['limit'] = limit
        resv_item['status'] = status
        resv_item['order'] = order
        user_resv_list.append(resv_item)
    return len(div_report_all)

#   本の所蔵冊数、予約数を取得する  n は処理する件数
def get_info(n):
    global user_book_info_list
    url_info_base = "https://www.lib.city.kobe.jp/winj/opac/reserve-detail.do?idx="
    url_detail = "https://www.lib.city.kobe.jp/winj/opac/switch-detail.do?idx=0"

    for i in range(0,n) :
        url_info = url_info_base + str(i)
        driver.get(url_info)
        driver.get(url_detail)
        html = driver.page_source
        ret = com.analize_info(html)
        book_info = {}
        book_info['num'] = ret[1]    # 所蔵冊数
        book_info['resv'] = ret[2]   # 予約数
        book_info['index'] = ret[3]  # 書誌番号
        user_book_info_list.append(book_info)

def output_info_file() :
    output_file_common("info")

def output_histo_file():
    # 最新が1週間以内なら出力しない処理を入れるかも
    if not flg_overwrite :
        histfileGenaration()   # 出力前に世代管理をする
    output_file_common("hist")

def output_file_common(type):
    user = 0 
    for u_resv,u_info in zip(resv_list,book_info_list) :
        if type == "info" :
            fname = f"{infofile}{user}.txt"
        else :
            fname = f"{histfile}{user}_0.txt"
        f = open(fname,"w",encoding='utf-8')
        f.write(today_date.strftime("%y/%m/%d") + "\n")
        for resv,info in zip(u_resv,u_info) :
            f.write(f"{resv['title']}\t{info['num']}\t{info['resv']}\t{resv['order']}\t{info['index']}\n")
        user = user + 1 
        f.close()

#   保存データから所蔵冊数、予約数を取得する
def get_info_from_data() :
    global book_info_list,user_book_info_list,save_date
    user = 0 
    for u_resv in resv_list :
        save_info = []
        title_list = []
        user_book_info_list = []
        fname = f"{infofile}{user}.txt"
        if not os.path.exists(fname) :
            print(f'ERROR not found {fname}')
            sys.exit(1)
        f = open(fname,"r",encoding='utf-8')
        save_date = f.readline()
        for line in f:
            dt = line.split("\t")
            title_list.append(dt[0])    # タイトルで検索するためタイトルのみのリスト 
            save_info.append(line)
        f.close()
        for r in u_resv :    # book_info には resv_list と同じ順番で格納する必要がある
            if r['title'] in title_list :
                ix = title_list.index(r['title'])  # タイトルで検索しその情報をbook_infoへ
                dt = save_info[ix]
                book_info = {}
                dt_list = dt.split("\t")
                book_info['num'] = int(dt_list[1])
                book_info['resv'] = int(dt_list[2])
                book_info['order'] = int(dt_list[3])
                book_info['index'] = dt_list[4].replace('\n','')
            else :                                 # タイトルがない場合 (新規)
                book_info = {}
                book_info['num'] = 0
                book_info['resv'] = 0
                book_info['order'] = 0
                book_info['index'] = '0'
            user_book_info_list.append(book_info)
        user = user + 1 
        book_info_list.append(user_book_info_list)

#  最新履歴ファイルを読み hist_list に格納する
def read_histo_data():
    global hist_list,history_date
    for user in range(0,2) :     # とりあえず2ユーザ決めうち
        fname = f"{histfile}{user}_0.txt"
        if not os.path.exists(fname) :
            print(f'ERROR not found {fname}')
            sys.exit(1)

        f = open(fname,"r",encoding='utf-8')
        history_date  = f.readline()
        hist = {}
        for line in f:
            line = line.replace("\n","")
            dt = line.split("\t")
            h_list = [int(dt[1]),int(dt[2]),int(dt[3]),dt[4]]   # 所蔵、予約、順位、書誌番号
            hist[dt[0]] = h_list
        hist_list.append(hist)

def output_resv_list() :
    global num_output   ,estimate_log
    
    i = 0 
    r_list = resv_list[num_output]
    b_list = book_info_list[num_output]
    for r,info in zip(r_list,b_list) :
        i = i + 1 
        title = r['title']
        _,prev_resv,prev_order,_ = get_prev_info(title)
        resv_i = info['resv']
        if not flg_info :     # -i でない時は前回実行結果から順番の情報を取得  -i の時は hist から取得 
            prev_order = info['order']

        if resv_i > prev_resv :
            resv_ele = f"<span class=red>{resv_i}</span>"
        else :
            resv_ele = resv_i
        status = "未定義"
        if r['status'] == STATUS_OK :
            status = "<span class=blue>OK</span>"
        if r['status'] == STATUS_DELI :
            status = "<span class=green>配送中</span>"
        if r['status'] == STATUS_ORDER :
            status = "発注中"
        if r['status'] == STATUS_OTHER :
            status = "対応中"
        if r['status'] == STATUS_NG :
            status = "貸出中"
        if r['status'] == STATUS_REQ :
            status = "申込中"
        r_date = r['resv_date'].strftime("%m/%d (%a)")
        if r['limit'] == "" :
            l_date = ""
        else :
            l_date = r['limit'].strftime("%m/%d (%a)")
        estimeate,dd = calc_available_date(title,int(r['order']))
        estimeatestr = estimeate
        if estimeatestr != "" :
            estimeatestr = estimeate.strftime("%m/%d")
            if estimeate < today_date + timedelta(days=7) :  # 1週間以内なら緑字にする
                estimeatestr = f'<span class=green>{estimeatestr}</span>'
            elif estimeate < today_date + timedelta(days=14) :  # 2週間以内なら青字にする
                estimeatestr = f'<span class=blue>{estimeatestr}</span>'
            elif estimeate > today_date + timedelta(days=365) :  # 1年以上先ならアンダーライン
                estimeatestr = f'<u>{estimeatestr}</u>'
        else :
            dd = 0 
        if r['status'] == STATUS_OK or  r['status'] == STATUS_DELI :
            estimeatestr = ""    # 貸出OK or 配送中なら予測日は不要
        
        od = r['order']
        if int(r['order']) < prev_order:     # 以前より順位が小さい場合は 青文字
            od = f"<span class=blue>{r['order']}</span>"

        out.write(f"<tr><td align=right>{i}</td><td>{title} {r['info']}</td><td>{r_date}</td>"
                  f"<td>{status}</td><td align=right>{info['num']}</td><td align=right>{resv_ele}({prev_resv})</td>"
                  f"<td align=right>{od}({prev_order})</td><td>{estimeatestr}</td>"
                  f"<td align=right>{dd:.2f}</td><td>{l_date}</td></tr>\n")

        predict.write(f'{title}\t{estimeate}\n')
    num_output = num_output + 1

#  タイトルで検索し過去の 所蔵冊数、予約数、順位、書誌番号 を取得する  引数ｔ はタイトル
def get_prev_info(t) :
    hist = hist_list[num_output]
    if t in hist :
        dt = hist[t]
        return dt
    else :
        return [0,0,0,0]

#  履歴ファイルの世代管理
def histfileGenaration():
    for user in range(2) :    # 2ユーザきめうち
        if not os.path.exists(f'{histfile}{user}_0.txt') : 
            continue   # 最新世代がない場合はなにもしない
        for i in range(max_gen-1,-1,-1) :   # max_gen-1 (=3) から 0 まで
            fname = f'{histfile}{user}_{i}.txt'
            #print(f'user ={user} i={i} f={f}')
            if not os.path.exists(fname)  :
                continue
            if i == (max_gen -1 ):  # i == 3
                os.remove(fname)    #  最終世代なら消すだけ
            else :             #  最終世代でないなら1つ世代を進める
                newfile = f'{histfile}{user}_{i+1}.txt'
                os.rename(fname, newfile) 

#  貸出予定日を計算する   引数 t はタイトル order は現在の順位
#  返却値  貸出予定日(date型),1順位進むのにかかる日数(float型)   計算不可の場合は ””,"" を返す   
def calc_available_date(t,order) :
    base_date,base_order = search_hist_data(t)
    estimate_log.write(f'<tr><td>{t}</td><td align=right>{order}</td><td>{base_date}</td><td align=right>{base_order}</td>\n')

    if base_order == -1 or base_order == 0 :  # 履歴がない または 0 (入荷中)
        estimate_log.write(f'<td> </td><td> </td><td> </td><td> </td></tr>\n')
        return "",""
    diff_days = today_date - base_date
    diff_days = diff_days.days 
    diff_order =  base_order - order
    if diff_order <= 0 :
        estimate_log.write(f'<td> </td><td> </td><td> </td><td> </td></tr>\n')
        return "",""
    dd =  diff_days / diff_order   #  1順位進むのにかかる日数
    estimate = today_date + timedelta(days=int(dd * order)) 
    estimate_log.write(f'<td>{estimate}</td><td align=right>{dd:.2f}</td><td align=right>{diff_days}</td>'
                       f'<td align=right>{diff_order}</td></tr>\n')
    return estimate,dd


#  履歴ファイルをタイトルで検索し、最古の日付と順位を返す
#  見つからなければ save_order に -1 を返す
def search_hist_data(t) :
    save_date = ""
    save_order = -1
    for i in range(0,max_gen) :   # 最新から過去にさかのぼる  0 から 3
        hist = f'{histfile}{num_output}_{i}.txt'
        if not os.path.exists(hist) : 
            break     # ファイルが存在しなければ検索終了
        f = open(hist,"r",encoding='utf-8')
        found = 0 
        hist_date = f.readline()
        hist_date = hist_date.strip()
        date_dt = datetime.datetime.strptime(hist_date, '%y/%m/%d')
        hist_date = datetime.date(date_dt.year, date_dt.month, date_dt.day)
        for line in f:
            line = line.replace("\n","")
            dt = line.split("\t")
            if t == dt[0] :    #  タイトルが一致
                save_date = hist_date
                save_order = int(dt[3])
                found = 1
                break          # このファイルの散策は終了
        if found == 0 :    # ファイルの最後までタイトルが見つからなかったら検索終了
            break

    return save_date,save_order


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

def ftp_upload() : 
    if debug == 1 :
        return 
    with FTP_TLS(host=config['ftp_host'], user=config['ftp_user'], passwd=config['ftp_pass']) as ftp:
        ftp.storbinary('STOR {}'.format(config['ftp_url']), open(resv_resultfile, 'rb'))

def parse_template(templ_name,result_name) :
    global out 
    f = open(templ_name , 'r', encoding='utf-8')
    out = open(result_name,'w' ,  encoding='utf-8')
    for line in f :
        if "%resv_list%" in line :
            output_resv_list()
            continue
        if "%version%" in line :
            s = line.replace("%version%",version)
            out.write(s)
            continue
        if "%today%" in line :
            today(line)
            continue
        if "%historydate%" in line:
            s = line.replace("%historydate%",history_date)
            out.write(s)
            continue
        if "%elapsetime%" in line:
            ela = time.time() - start_time
            ela = f'{ela:.2f}'
            s = line.replace("%elapsetime%",ela)
            out.write(s)
            continue
        if "%resv_title%" in line:
            d = datetime.datetime.now().strftime("%y/%m/%d")
            s = line.replace("%resv_title%",f"予約リスト{d}")
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
