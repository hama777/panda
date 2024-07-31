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

version = "0.00"       # 24/07/31

# TODO:  

debug = 0     #  1 ... debug
appdir = os.path.dirname(os.path.abspath(__file__))

datafile = appdir + "/prediction.txt"

ftp_host = ftp_user = ftp_pass = ftp_url =  ""
pixela_url = ""
pixela_token = ""

def main_proc():

    locale.setlocale(locale.LC_TIME, '')
    read_data() 

def read_data():
    global df_past
    df_predict = pd.read_csv(datafile,  sep='\t', header=None, names=['title', 'predict'])
    df_predict = df_predict.sort_values('predict',ascending=True).head(10)
    print(df_predict)


# ----------------------------------------------------------
main_proc()
