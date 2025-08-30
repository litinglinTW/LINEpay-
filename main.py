#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug 30 11:22:34 2025

@author: cglinmacbook
"""
import streamlit as st
import io
import re
import openpyxl
import pandas as pd
from datetime import datetime

def parse_record(cur_date, cur_time, lines, nt_pat, complete_pat, cancel_pat, merchant_pat):
    # 只抓LINE Pay Purchase
    if not any("LINE Pay Purchase" in l for l in lines):
        return None
    text = "\n".join(lines)
    m = nt_pat.search(text)
    amt = int(m.group(1).replace(",", "")) if m else ""
    is_cancel = bool(cancel_pat.search(text))
    is_complete = bool(complete_pat.search(text))
    # 花費資訊
    merchant = ""
    for l in lines:
        merchant_m = merchant_pat.search(l)
        if merchant_m:
            merchant = merchant_m.group(1).strip()
            break
    if is_complete:
        return [cur_date, cur_time, amt, "", merchant]
    elif is_cancel:
        return [cur_date, cur_time, -amt, "", merchant]
    else:
        return [cur_date, cur_time, amt, m.group(1).replace(",", "") if m else "", merchant]

def process_txt(txt_content, start_date, end_date):
    date_pat = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\d{2})/(\d{2})/(\d{4})")
    txn_start_pat = re.compile(r"^(\d{2}:\d{2}[AP]M)[\t ]+LINE錢包[\t ]+")
    nt_pat = re.compile(r"NT\$ ?([0-9,]+)")
    complete_pat = re.compile(r"Payment complete\.")
    cancel_pat = re.compile(r"Payment canceled\.")
    merchant_pat = re.compile(r"Merchant:\s*(.*)")

    records = []
    cur_date = ""
    cur_year = ""
    cur_month = ""
    cur_day = ""
    buf = []
    buf_time = ""
    lines = txt_content.splitlines()
    for line in lines:
        line = line.rstrip('\n').strip()
        # 日期行
        date_m = date_pat.match(line)
        if date_m:
            cur_date = line
            cur_month = int(date_m.group(2))
            cur_day = int(date_m.group(3))
            cur_year = date_m.group(4)
            continue
        # 新一筆消費的開始
        txn_m = txn_start_pat.match(line)
        if txn_m:
            if buf:
                # 檢查日期區間
                try:
                    cur_datetime = datetime(int(cur_year), cur_month, cur_day)
                except Exception:
                    cur_datetime = None
                if cur_datetime and start_date <= cur_datetime <= end_date:
                    rec = parse_record(cur_date, buf_time, buf, nt_pat, complete_pat, cancel_pat, merchant_pat)
                    if rec:
                        records.append(rec)
                buf = []
            buf = [line]
            buf_time = txn_m.group(1)
        elif buf:
            buf.append(line)
    # 處理最後一筆
    if buf:
        try:
            cur_datetime = datetime(int(cur_year), cur_month, cur_day)
        except Exception:
            cur_datetime = None
        if cur_datetime and start_date <= cur_datetime <= end_date:
            rec = parse_record(cur_date, buf_time, buf, nt_pat, complete_pat, cancel_pat, merchant_pat)
            if rec:
                records.append(rec)
    return records

def records_to_excel(records, start_date, end_date):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["日期", "時間", "花費金額", "其他", "花費資訊"])
    for rec in records:
        ws.append(rec)
    # 增加總計行（用excel公式）
    ws.append([])
    last_data_row = ws.max_row
    ws.append(["總計（這個月的總花費）=", "", f'=SUM(C2:C{last_data_row})', "", ""])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

st.title("LINE Pay 聊天室紀錄查詢工具")

uploaded_file = st.file_uploader("請上傳 LINE Pay 聊天室 txt 檔案", type=['txt'])

st.markdown("## 請選擇日期區間")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("開始日期")
with col2:
    end_date = st.date_input("結束日期")

if uploaded_file and start_date and end_date:
    try:
        # st.date_input 回傳 date 物件，需轉為 datetime
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        txt_content = uploaded_file.read().decode("utf-8")
        records = process_txt(txt_content, start_dt, end_dt)
        if not records:
            st.warning("找不到符合條件的消費紀錄，請確認日期區間及txt內容。")
        else:
            df = pd.DataFrame(records, columns=["日期", "時間", "花費金額", "其他", "花費資訊"])
            st.dataframe(df)
            
            # 計算總計
            total = df["花費金額"].sum()
            st.markdown(f"**總計（這個月的總花費）= {total}**")
            
            excel_data = records_to_excel(records, start_dt, end_dt)
            st.download_button(
                label="下載Excel檔案",
                data=excel_data,
                file_name=f"linepay_output_{start_date}_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"格式錯誤或處理失敗：{e}")
else:
    st.info("請先上傳txt檔案並選擇日期區間。")
    
    
    
    
    
    
