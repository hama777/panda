#!/usr/bin/python
# -*- coding: utf-8 -*-

from ast import If
import os
import csv
import datetime
import pandas as pd
import locale
from ftplib import FTP_TLS
from datetime import date,timedelta
import math

version = "0.01"       # 24/08/02

# TODO:  

debug = 0     #  1 ... debug
appdir = os.path.dirname(os.path.abspath(__file__))

datafile = appdir + "/prediction.txt"
templatefile = appdir + "/predict_templ.htm"
resultfile = appdir + "/predict.htm"
df_predict = ""
ftp_host = ftp_user = ftp_pass = ftp_url =  ""
pixela_url = ""
pixela_token = ""

def main_proc():

    locale.setlocale(locale.LC_TIME, '')
    read_data() 
    parse_template()

def read_data():
    global df_predict

    df_predict = pd.read_csv(datafile,  sep='\t', header=None, names=['title', 'predict'])
    df_predict = df_predict.sort_values('predict',ascending=True).head(20)

def predict_timeline() :
    d_today = datetime.date.today()
    t_yy = d_today.year
    t_mm = d_today.month -1 
    t_dd = d_today.day
    limit_date = d_today + datetime.timedelta(days=60)
    for index , row in df_predict.iterrows() :    
        title = row['title']
        predict = row['predict']   # str type
        pdate = datetime.datetime.strptime(predict, "%Y-%m-%d")
        pdate = pdate.date()     # datetime => date
        pdate_label = pdate.strftime("%m/%d")
        if pdate <= d_today :
            continue
        if pdate > limit_date :    # 最大2ヶ月まで
            break 
        yy = pdate.year
        mm = pdate.month -1   # javascript の月は 0 はじまり
        dd = pdate.day
        out.write(f"['{title}','{pdate_label}',new Date({t_yy},{t_mm},{t_dd}), new Date({yy},{mm},{dd})],\n")

def today(s):
    today_datetime = datetime.datetime.today()
    d = today_datetime.strftime("%m/%d %H:%M")
    s = s.replace("%today%",d)
    out.write(s)

def parse_template() :
    global out 
    f = open(templatefile , 'r', encoding='utf-8')
    out = open(resultfile,'w' ,  encoding='utf-8')
    for line in f :
        if "%predict_timeline%" in line :
            predict_timeline()
            continue
        if "%version%" in line :
            s = line.replace("%version%",version)
            out.write(s)
            continue
        if "%today%" in line :
            today(line)
            continue
        out.write(line)

    f.close()
    out.close()

# ----------------------------------------------------------
main_proc()
