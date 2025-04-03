import json
import os
import io
import base64
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # GUI backend hatalarını önlemek için
import sys
import psutil
import plotly.graph_objects as go
from plotly.offline import plot
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = 'uploads'
RULES_FILE = "rules.json"
MISSING_RULES_FILE = "missing_rules.json"  # Satılmayan ürünler için öneri dosyası
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

KATALOG_DOSYA = "Kategoriler.csv"

#  Ürün kataloğunu oku veya boş set oluştur
if os.path.exists(KATALOG_DOSYA):
    katalog_df = pd.read_csv(KATALOG_DOSYA, encoding="utf-8", sep=";", low_memory=False)
    if "Ürün Tanım" in katalog_df.columns:
        urun_katalogu = set(katalog_df["Ürün Tanım"].astype(str).str.strip())
    else:
        urun_katalogu = set()
else:
    urun_katalogu = set()

def load_rules():
    if not os.path.exists(RULES_FILE):
        with open(RULES_FILE, "w", encoding="utf-8") as file:
            json.dump([], file)
    with open(RULES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_rules(rules):
    with open(RULES_FILE, "w", encoding="utf-8") as file:
        json.dump(rules, file, indent=4, ensure_ascii=False)

def load_missing_rules():
    if not os.path.exists(MISSING_RULES_FILE):
        with open(MISSING_RULES_FILE, "w", encoding="utf-8") as file:
            json.dump([], file)
    with open(MISSING_RULES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_missing_rules(missing_rules):
    with open(MISSING_RULES_FILE, "w", encoding="utf-8") as file:
        json.dump(missing_rules, file, indent=4, ensure_ascii=False)

import pandas as pd




from datetime import datetime

def detect_and_extract_columns(file_path):
    df = pd.read_csv(file_path, encoding="utf-8", sep=";", header=None, low_memory=False)

    start_date = None
    end_date = None

    # İlk 10 satırı satır bazında birleştirip içinde ara
    for i in range(10):
        row_text = " ".join(df.iloc[i].dropna().astype(str)).lower()

        if "başlangıç tarihi" in row_text and start_date is None:
            try:
                tarih_str = row_text.split("başlangıç tarihi:")[1].split()[0] + " " + row_text.split("başlangıç tarihi:")[1].split()[1]
                start_date = datetime.strptime(tarih_str.strip(), "%d.%m.%Y %H:%M:%S")
            except:
                continue

        if "bitiş tarihi" in row_text and end_date is None:
            try:
                tarih_str = row_text.split("bitiş tarihi:")[1].split()[0] + " " + row_text.split("bitiş tarihi:")[1].split()[1]
                end_date = datetime.strptime(tarih_str.strip(), "%d.%m.%Y %H:%M:%S")
            except:
                continue

    # ✅ Rapor Tipi Belirleme
    if start_date and end_date:
        days = (end_date - start_date).days
        if 25 <= days <= 34:
            rapor_tipi = "Aylık"
        elif 76 <= days <= 110:
            rapor_tipi = "3 Aylık"
        elif 160 <= days <= 220:
            rapor_tipi = "6 Aylık"
        elif 340 <= days <= 385:
            rapor_tipi = "Yıllık"
        else:
            rapor_tipi = f"{days} Günlük"
    else:
        rapor_tipi = "Genel"

    print(f"✅ Başlangıç: {start_date} | Bitiş: {end_date} ➜ Rapor Tipi: {rapor_tipi}")

    # 🧩 Son olarak buraya senin tüm veri ayıklama işlemlerin gelmeli:
    # df_cleaned = ...
    # return df_cleaned,_


    # ⬇️ SÜTUNLARI TESPİT ET (eski kodunla aynı)
    malzeme_keywords = ["malzeme grubu", "ürün grubu", "malzeme adı"]
    kategori_keywords = ["kategori"]
    satis_keywords = ["net satış miktarı", "satış miktar", "toplam satış"]
    kdvli_keywords = ["kdv li net satış tutar", "kdv'li net satış tutarı", "kdv dahil satış tutarı"]

    malzeme_sutun = kategori_sutun = satis_sutun = kdvli_sutun = data_start_row = None

    for i in range(50):
        row_values = df.iloc[i].astype(str).str.lower()

        for keyword in malzeme_keywords:
            if any(row_values.str.contains(keyword)):
                malzeme_sutun = row_values[row_values.str.contains(keyword)].index[0]
        for keyword in kategori_keywords:
            if any(row_values.str.contains(keyword)):
                kategori_sutun = row_values[row_values.str.contains(keyword)].index[0]
        for keyword in satis_keywords:
            if any(row_values.str.contains(keyword)):
                satis_sutun = row_values[row_values.str.contains(keyword)].index[0]
        for keyword in kdvli_keywords:
            if any(row_values.str.contains(keyword)):
                kdvli_sutun = row_values[row_values.str.contains(keyword)].index[0]

        if all([malzeme_sutun, kategori_sutun, satis_sutun, kdvli_sutun]):
            data_start_row = i
            break

    if None in [malzeme_sutun, kategori_sutun, satis_sutun, kdvli_sutun, data_start_row]:
        raise ValueError("Gerekli sütunlar bulunamadı!")

    # Temizlenmiş veri çerçevesi
    df_cleaned = df.iloc[data_start_row + 1:, [malzeme_sutun, kategori_sutun, satis_sutun, kdvli_sutun]]
    df_cleaned.columns = ["Malzeme Grubu", "Kategori", "Net Satış Miktarı", "Kdv Li Net Satış Tutar"]
    df_cleaned = df_cleaned[df_cleaned["Malzeme Grubu"] != "Toplam"].dropna()

    for col in ["Net Satış Miktarı", "Kdv Li Net Satış Tutar"]:
        df_cleaned[col] = (
            df_cleaned[col].astype(str)
            .str.replace(r"[^\d,]", "", regex=True)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors="coerce")

    # Filtreleme için ayrı sütun
    df_cleaned["Filtre"] = df_cleaned["Malzeme Grubu"].apply(
        lambda x: (
            "AdaHome" if "adahome" in x.lower() else
            "AdaWall" if "adawall" in x.lower() else
            "AdaPanel" if "adapanel" in x.lower() else
            "Diğer"
        )
        
    )

    return df_cleaned, rapor_tipi



def generate_combined_recommendations(df, satilmayan_urunler):
    rules = load_rules()
    missing_rules = load_missing_rules()
    grouped_df = df.groupby("Malzeme Grubu", as_index=False).sum()

    combined_blocks = []
    brands = ["adahome", "adawall", "adapanel"]

    for brand in brands:
        brand_title = brand.upper()
        icon = "🏠" if brand == "adahome" else "🧱" if brand == "adawall" else "🧩"

        # Genel durum kutusu (satış azsa)
        general_rule = next((r for r in rules if r["keyword"].lower() == brand), None)
        brand_df = grouped_df[grouped_df["Malzeme Grubu"].str.contains(brand, case=False, na=False)]
        total_sales = brand_df["Net Satış Miktarı"].sum()

        block = ""

        if general_rule and total_sales < 1000000:
            block += f"""
            <div class="brand-recommendation">
              <div class="brand-header">{icon} <b>{brand_title} GENEL DURUM RAPORU</b> {icon}</div>
              <div class="sales-info">📉 Toplam Satış: <b>{total_sales:.1f}</b> | </b></div>
              <div class="recommendation-box">💡 <b>ÖNERİLERİMİZ:</b> {general_rule["message"]}</div>
            """

        # Ürün bazlı az satış önerileri
        product_rules = [r for r in rules if r["keyword"].lower().startswith(brand) and r["keyword"].lower() != brand]
        for rule in product_rules:
            match = grouped_df[grouped_df["Malzeme Grubu"].str.contains(rule["keyword"], case=False, na=False)]
            if not match.empty:
                sales = match["Net Satış Miktarı"].sum()
                if sales < rule["threshold"]:
                    block += f"""
                    <div class="normal-message mt-2">
                      <span class="title">🔹 '{rule["keyword"]}' satışı: {sales:.1f} (Hedef: {rule["threshold"]})</span>
                      ➤ {rule["message"]}
                    </div>
                    """

        # Satılmayan ürün önerileri
        for rule in missing_rules:
            if rule["keyword"].lower().startswith(brand):
                if any(rule["keyword"].lower() in u.lower() for u in satilmayan_urunler):
                    block += f"""
                    <div class="normal-message red">
                        <div>
                        <span class="title">❌ <b>'{rule["keyword"]}'</b></span>
                         <span style="color: #d63031; font-weight: bold; margin-left: 10px;">Bu üründen <u>0 adet</u> satmışsınız!</span>
                            </div>
                            <div style="margin-top: 5px;">
                     ➤ {rule["message"]}
                        </div>
                    </div>
                            """


        if block:
            block += "</div>"  # brand-recommendation bitişi
            combined_blocks.append(block)

    if not combined_blocks:
        return """<div class="no-recommendation">✅ Tüm markalarda yeterli satış ve öneri durumu görünmüyor.</div>"""

    return "".join(combined_blocks)


def group_missing_products_by_brand(products):
    grouped = {"AdaHome": [], "AdaWall": [], "AdaPanel": [], "Diğer": []}
    for urun in products:
        urun_lower = urun.lower()
        if "adahome" in urun_lower:
            grouped["AdaHome"].append(urun)
        elif "adawall" in urun_lower:
            grouped["AdaWall"].append(urun)
        elif "adapanel" in urun_lower:
            grouped["AdaPanel"].append(urun)
        else:
            grouped["Diğer"].append(urun)
    return grouped






def generate_missing_recommendations(satilmayan_urunler):
    missing_rules = load_missing_rules()
    recommendations = []

    for rule in missing_rules:
        keyword = rule["keyword"].strip()
        message = rule["message"]

        if any(keyword.lower() in urun.lower() for urun in satilmayan_urunler):
            recommendations.append(f"🔹 <b>'{keyword}'</b> ile ilgili öneri: {message}")

    return "<br>".join(recommendations) if recommendations else "✅ Satılmayan ürünler için özel bir öneri bulunmamaktadır."


def generate_pie_charts(satilan_urunler, satilmayan_urunler, df):
    categories = ["AdaHome", "AdaPanel", "AdaWall"]
    colors = ['#ffcc00', '#66b3ff', '#99ff99']
    chart_buffers = []

    # Grafik 1 - Genel
    fig1, ax1 = plt.subplots()
    ax1.pie([len(satilan_urunler), len(satilmayan_urunler)],
            labels=["Satılan", "Satılmayan"], autopct='%1.1f%%',
            colors=["#ff6347", "#4caf50"], explode=(0, 0.1), shadow=True)
    ax1.set_title("Toplam Ürün Çeşidi Satışı")
    buf1 = io.BytesIO()
    plt.savefig(buf1, format="png", dpi=200)
    buf1.seek(0)
    chart_buffers.append(base64.b64encode(buf1.read()).decode("utf8"))
    plt.close(fig1)

    # Grafik 2 - Satılan Kategori (Doğrulandı)
    fig2, ax2 = plt.subplots()
    df_satilan = df[df["Malzeme Grubu"].isin(satilan_urunler)]
    cat_sales = {
        cat: df_satilan[df_satilan["Malzeme Grubu"].str.contains(fr'\b{cat}\b', na=False, case=False)]["Net Satış Miktarı"].sum()
        for cat in categories
    }
    ax2.pie(cat_sales.values(), labels=cat_sales.keys(), autopct='%1.1f%%', colors=colors)
    ax2.set_title("Satılan Ürünlerin Kategorik Dağılımı")
    buf2 = io.BytesIO()
    plt.savefig(buf2, format="png", dpi=200)
    buf2.seek(0)
    chart_buffers.append(base64.b64encode(buf2.read()).decode("utf8"))
    plt.close(fig2)

    # Grafik 3 - Satılmayan Kategori
    fig3, ax3 = plt.subplots()
    unsold = {cat: sum(1 for u in satilmayan_urunler if cat in u) for cat in categories}
    ax3.pie(unsold.values(), labels=unsold.keys(), autopct='%1.1f%%', colors=colors)
    ax3.set_title("Satılmayan Ürünlerin Kategorik Dağılımı")
    buf3 = io.BytesIO()
    plt.savefig(buf3, format="png", dpi=200)
    buf3.seek(0)
    chart_buffers.append(base64.b64encode(buf3.read()).decode("utf8"))
    plt.close(fig3)

    return chart_buffers


@app.route("/filtered_sold_chart", methods=["POST"])
def filtered_chart():
    if 'data' not in session:
        return ""

    df = pd.DataFrame(session['data'])
    selected = request.json.get("selected_categories", [])
    
    # Seçilen kategorilere göre satışları topla
    data_dict = {}
    for category in selected:
        cat_df = df[df["Malzeme Grubu"].str.contains(category, case=False, na=False)]
        total_sales = cat_df["Net Satış Miktarı"].sum()
        data_dict[category] = total_sales

    if sum(data_dict.values()) == 0:
        data_dict = {"Seçilenlerde Satış Yok": 1}

    fig = go.Figure(data=[go.Pie(
        labels=list(data_dict.keys()),
        values=list(data_dict.values()),
        textinfo='label+percent+value',
        insidetextorientation='auto',
        marker=dict(line=dict(color='#000000', width=1))
    )])

    fig.update_layout(
        margin=dict(t=30, b=30, l=30, r=30),
        height=400,
        title=dict(text="", font=dict(size=20))
    )

    return plot(fig, output_type='div', include_plotlyjs='cdn')





import os
from flask import Response

import threading
from flask import render_template

@app.route("/kapat", methods=["GET"])
def kapat():
    threading.Timer(1.5, lambda: os._exit(0)).start()
    return render_template("kapat.html")




@app.route("/", methods=["GET", "POST"])
def upload_file():
    recommendations_html = None
    missing_recommendations_html = None
    table_data = None
    missing_products_html = None
    pie_chart_url = None
    rapor_tipi = None
    pie_chart_url2 = None
    pie_chart_url3 = None
    uploaded_filename = None
    combined_recommendations = None
    grouped_missing = None  # ✅ Başlangıçta tanımlandı

    if request.method == "POST" and 'file' in request.files:
        file = request.files['file']
        if file:
            uploaded_filename = file.filename
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            try:
                # Eski satır:
# df_cleaned = detect_and_extract_columns(file_path)

# Yeni satır:
                df_cleaned, rapor_tipi = detect_and_extract_columns(file_path)

                session['data'] = df_cleaned.to_dict(orient="records")
                table_data = df_cleaned.to_dict(orient="records")

                satilan_urunler = set(df_cleaned["Malzeme Grubu"].astype(str).str.strip())
                satilmayan_urunler = urun_katalogu - satilan_urunler

                # ✅ Satılmayan ürünleri markalara göre gruplandır
                grouped_missing = group_missing_products_by_brand(satilmayan_urunler)

                combined_recommendations = generate_combined_recommendations(df_cleaned, satilmayan_urunler)

                missing_products_html = "<br>".join(sorted(satilmayan_urunler)) if satilmayan_urunler else "✅ Tüm ürünler satılmış!"

                charts = generate_pie_charts(satilan_urunler, satilmayan_urunler, df_cleaned)
                pie_chart_url, pie_chart_url2, pie_chart_url3 = charts

            except Exception as e:
                return f"Hata oluştu:<br><pre>{str(e)}</pre>"

    return render_template("index.html",
                           table_data=table_data,
                           missing_products=missing_products_html,
                           missing_recommendations=missing_recommendations_html,
                           recommendations=recommendations_html,
                           pie_chart_url=pie_chart_url,
                           rapor_tipi=rapor_tipi,
                           pie_chart_url2=pie_chart_url2,
                           pie_chart_url3=pie_chart_url3,
                           uploaded_filename=uploaded_filename,
                           combined_recommendations=combined_recommendations,
                           grouped_missing_products=grouped_missing)  # ✅ burada eklendi





@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    rules = load_rules()
    missing_rules = load_missing_rules()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            keyword = request.form.get("keyword").strip()
            threshold = int(request.form.get("threshold"))
            message = request.form.get("message")
            rules.append({"keyword": keyword, "threshold": threshold, "message": message})
            save_rules(rules)

        elif action == "delete":
            index = int(request.form.get("index"))
            if 0 <= index < len(rules):
                del rules[index]
                save_rules(rules)

        elif action == "add_missing":
            keyword = request.form.get("missing_keyword").strip()
            message = request.form.get("missing_message")
            missing_rules.append({"keyword": keyword, "message": message})
            save_missing_rules(missing_rules)

        elif action == "delete_missing":
            index = int(request.form.get("missing_index"))
            if 0 <= index < len(missing_rules):
                del missing_rules[index]
                save_missing_rules(missing_rules)

        return redirect(url_for("admin_panel"))

    return render_template("admin.html", rules=rules, missing_rules=missing_rules)

from flask import Flask, request, render_template, session


import threading
import webbrowser

if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=True, use_reloader=False)
