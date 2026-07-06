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
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches
import requests
import base64
import os
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from functools import wraps
import re

def secure_filename_tr(filename):
    # Sadece izin verilen karakterleri bırak (harf, rakam, Türkçe karakterler, boşluk, alt çizgi, nokta, tire)
    filename = re.sub(r"[^A-Za-z0-9ğüşöçıİĞÜŞÖÇ ._-]", "", filename)
    return filename

# PyInstaller için gerekli resource_path fonksiyonu
def resource_path(relative_path):
    """ PyInstaller için kaynak dosyaların yolunu düzenleyen yardımcı fonksiyon """
    try:
        # PyInstaller oluşturduğu _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

SIMPLE_RECOMMENDATIONS_FILE = resource_path("simple_recommendations.json")

def load_simple_recommendations():
    rules = load_rules()
    return [rule for rule in rules if "is_simple" in rule and rule["is_simple"]]

def save_simple_recommendations(recommendations):
    rules = load_rules()
    # Önce mevcut basit önerileri kaldır
    rules = [rule for rule in rules if not ("is_simple" in rule and rule["is_simple"])]
    # Yeni basit önerileri ekle
    for rec in recommendations:
        rec["is_simple"] = True
        if "keyword" not in rec:
            rec["keyword"] = "Genel Öneri"
        rules.append(rec)
    save_rules(rules)

def generate_simple_recommendations():
    recommendations = load_simple_recommendations()
    if not recommendations:
        return "<div class='no-recommendation'>Henüz öneri eklenmemiş.</div>"

    html = """
    <div class="simple-recommendations" style="background-color: #fff; border-radius: 15px; padding: 25px; margin-top: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <div style="text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px;">
            📝 GENEL ÖNERİLER
        </div>
        <hr style="border: none; border-top: 3px dashed #ffc107; margin: 20px 0;">
    """

    for rec in recommendations:
        html += f"""
        <div class='normal-message mt-4' style="font-size: 16px;">
            📌 {rec['message']}
        </div>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">
        """

    html += "</div>"
    return html


app = Flask(__name__)
app.secret_key = "supersecretkey"
app.permanent_session_lifetime = timedelta(minutes=30)  # Oturum 30 dakika sonra sonlanacak

# Template'de kullanılacak fonksiyonları ekle
app.jinja_env.globals.update(generate_simple_recommendations=generate_simple_recommendations)

UPLOAD_FOLDER = resource_path('uploads')
RULES_FILE = resource_path("rules.json")
MISSING_RULES_FILE = resource_path("missing_rules.json")  # Satılmayan ürünler için öneri dosyası
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

KATALOG_DOSYA = resource_path("Kategoriler.csv")

# Kullanıcı adı ve şifre
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '123456')

# UYARI: Gerçek bir uygulamada varsayılan şifre kullanmayın veya çok daha güçlü bir şifre seçin.
#        Ortam değişkenlerini ayarlamak daha güvenli bir yöntemdir.

def login_required(f):
    @wraps(f) # Decorator'ın orijinal fonksiyon bilgilerini korumasını sağlar
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.permanent = True  # Oturumun kalıcı olmasını sağla
            session['logged_in'] = True
            next_url = request.args.get('next')
            return redirect(next_url or url_for('upload_file'))
        else:
            error = 'Geçersiz kullanıcı adı veya şifre!'
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

from datetime import datetime
import pandas as pd

def detect_and_extract_columns(file_path):
    df = pd.read_csv(file_path, encoding="utf-8", sep=";", header=None, low_memory=False, decimal=",", thousands=".")

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
            ay_ismi_en = start_date.strftime("%B")
            
            ay_cevirisi = {
                "January": "Ocak",
                "February": "Şubat",
                "March": "Mart",
                "April": "Nisan",
                "May": "Mayıs",
                "June": "Haziran",
                "July": "Temmuz",
                "August": "Ağustos",
                "September": "Eylül",
                "October": "Ekim",
                "November": "Kasım",
                "December": "Aralık"
            }
            
            ay_ismi = ay_cevirisi.get(ay_ismi_en, ay_ismi_en)
            rapor_tipi = f"{ay_ismi} Ayı İçin Aylık Satış Analizi"
        elif 76 <= days <= 110:
            rapor_tipi = "3 Aylık Satış Analizi"
        elif 160 <= days <= 220:
            rapor_tipi = "6 Aylık Satış Analizi"
        elif 340 <= days <= 385:
            rapor_tipi = "Yıllık Satış Analizi"
        else:
            rapor_tipi = f"{days} Günlük"
    else:
        rapor_tipi = "Genel"

    # ⬇️ SÜTUNLARI TESPİT ET
    # Önce başlık satırını bul
    header_row = None
    for i in range(50):
        row_text = " ".join(df.iloc[i].dropna().astype(str)).lower()
        if "malzeme grubu" in row_text and "kategori" in row_text:
            header_row = i
            break

    if header_row is None:
        raise ValueError("Başlık satırı bulunamadı!")

    # ⬇️ SÜTUNLARI TESPİT ET
    malzeme_keywords = ["malzeme grubu", "ürün grubu", "malzeme adı"]
    kategori_keywords = ["kategori"]
    kod_keywords = ["ürün kodu","ürün kodları","ürün açıklaması"]
    satis_keywords = ["net satış miktarı", "satış miktar", "toplam satış"]
    kdvli_keywords = ["kdv li net satış tutar", "kdv'li net satış tutarı", "kdv dahil satış tutarı"]

    malzeme_sutun = kategori_sutun = satis_sutun = kdvli_sutun = kod_sutun = data_start_row = None

    for i in range(50):
        row_values = df.iloc[i].astype(str).str.lower()

        for keyword in malzeme_keywords:
            if any(row_values.str.contains(keyword)):
                malzeme_sutun = row_values[row_values.str.contains(keyword)].index[0]
        for keyword in kategori_keywords:
            if any(row_values.str.contains(keyword)):
                kategori_sutun = row_values[row_values.str.contains(keyword)].index[0]
        for keyword in kod_keywords:
            if any(row_values.str.contains(keyword)):
                kod_sutun = row_values[row_values.str.contains(keyword)].index[0]
        for keyword in satis_keywords:
            if any(row_values.str.contains(keyword)):
                satis_sutun = row_values[row_values.str.contains(keyword)].index[0]
        for keyword in kdvli_keywords:
            if any(row_values.str.contains(keyword)):
                kdvli_sutun = row_values[row_values.str.contains(keyword)].index[0]

        if all([malzeme_sutun, kategori_sutun, satis_sutun, kdvli_sutun, kod_sutun]):
            data_start_row = i
            break

    if None in [malzeme_sutun, kategori_sutun, satis_sutun, kdvli_sutun, kod_sutun, data_start_row]:
        raise ValueError("Gerekli sütunlar bulunamadı!")

    # Temizlenmiş veri çerçevesi
    df_cleaned = df.iloc[data_start_row + 1:, [malzeme_sutun, kategori_sutun, satis_sutun, kdvli_sutun, kod_sutun]]
    df_cleaned.columns = ["Malzeme Grubu", "Kategori", "Net Satış Miktarı", "Kdv Li Net Satış Tutar", "Ürün Kodu"]
    df_cleaned = df_cleaned[df_cleaned["Malzeme Grubu"] != "Toplam"].dropna()

    # Sadece sayısal sütunları dönüştür, ürün kodunu hariç tut
    for col in ["Net Satış Miktarı", "Kdv Li Net Satış Tutar"]:
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors="coerce")
    
    # Ürün kodunu string olarak bırak, sadece gereksiz boşlukları temizle
    df_cleaned["Ürün Kodu"] = df_cleaned["Ürün Kodu"].astype(str).str.strip()

    # Filtreleme için ayrı sütun
    df_cleaned["Filtre"] = df_cleaned["Malzeme Grubu"].apply(
        lambda x: (
            "AdaHome" if "adahome" in str(x).lower() else
            "AdaWall" if "adawall" in str(x).lower() else
            "AdaPanel" if "adapanel" in str(x).lower() else
            "Diğer"
        )
    )

    print(df_cleaned.head(10))
    print(df_cleaned[["Kdv Li Net Satış Tutar"]].head(10))
    print(df_cleaned["Kdv Li Net Satış Tutar"].dtype)

    return df_cleaned, rapor_tipi



def generate_combined_recommendations(df_cleaned):
    import pandas as pd
    import os

    def get_unit_from_keyword(keyword):
        keyword = keyword.lower()
        if any(kw in keyword for kw in ["kumaş", "perde", "poster", "katalog"]):
            return "metre"
        elif any(kw in keyword for kw in ["puf", "mobilya", "yastık", "şezlong"]):
            return "adet"
        elif "tutkal" in keyword:
            return "adet"
        elif any(kw in keyword for kw in ["adawall 16.5 m2'lik rulo", "adawall 10.6 m2'lik rulo", "duvar kağıdı", "adawall duvar kağıdı"]):
            return "rulo"
        else:
            return ""

    rules = load_rules()
    ANA_TABLO_PATH = "ana_tablo.csv"

    if not os.path.exists(ANA_TABLO_PATH):
        return "<div class='no-recommendation'>❗ ana_tablo.csv bulunamadı.</div>"

    ana_tablo_df = pd.read_csv(ANA_TABLO_PATH, encoding="utf-8", sep=";")
    ana_tablo_df["Malzeme Grubu"] = ana_tablo_df["Malzeme Grubu"].astype(str).str.strip()
    ana_tablo_df["Kategori"] = ana_tablo_df["Kategori"].astype(str).str.strip()
    df_cleaned["Malzeme Grubu"] = df_cleaned["Malzeme Grubu"].astype(str).str.strip()
    df_cleaned["Kategori"] = df_cleaned["Kategori"].astype(str).str.strip()

    ana_tablo_df["key"] = ana_tablo_df["Malzeme Grubu"] + "||" + ana_tablo_df["Kategori"]
    df_cleaned["key"] = df_cleaned["Malzeme Grubu"] + "||" + df_cleaned["Kategori"]

    merged = ana_tablo_df.merge(
        df_cleaned[["key", "Net Satış Miktarı"]],
        on="key",
        how="left",
        suffixes=("", "_Gercek")
    )
    merged["Net Satış Miktarı"] = merged["Net Satış Miktarı_Gercek"].fillna(0)
    merged = merged.drop(columns=["Net Satış Miktarı_Gercek", "key"])

    combined_blocks = []
    brands = ["adahome", "adawall", "adapanel"]

    for brand in brands:
        block = ""
        brand_df = merged[merged["Malzeme Grubu"].str.lower().str.contains(brand)]
        icon = "🏠" if brand == "adahome" else "🧱" if brand == "adawall" else "🧹"
        brand_title = brand.upper()

        general_rule = next((r for r in rules if r["keyword"].lower() == brand and isinstance(r["threshold"], (int, float))), None)
        total_sales = brand_df["Net Satış Miktarı"].sum()

        # Logo yolu
        if brand_title == "ADAHOME":
            logo_path = "/static/images/adahome-logo.png"
        elif brand_title == "ADAWALL":
            logo_path = "/static/images/adawall-logo.png"
        elif brand_title == "ADAPANEL":
            logo_path = "/static/images/adapanel-logo.png"
        else:
            logo_path = None

        block += f"""
        <div class="brand-recommendation" style="background-color: #fff; border-radius: 15px; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <div style='text-align: center; margin-bottom: 10px;'>
                <img src='{logo_path}' alt='{brand_title} Logo' style='height: 50px; width: auto;'>
            </div>
            <div style="text-align: center; font-size: 24px; font-weight: bold; margin-top: 5px;">
                {brand_title} GENEL DURUM RAPORU
            </div>
            <hr style="border: none; border-top: 3px dashed yellow; margin: 20px 0;">
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">
                <span style='font-size: 18px;'>💡</span> ÖNERİLERİMİZ:
            </div>
        """

        product_rules = [r for r in rules if r["keyword"].lower().startswith(brand) and r["keyword"].lower() != brand]
        has_recommendation = False

        for rule in product_rules:
            keyword = rule["keyword"].lower()
            filtered = pd.DataFrame()

            # Özel filtreleme kurallarını uygula
            if rule.get("filters"):
                filters = rule["filters"]
                if filters.get("malzeme_grubu"):
                    filtered = merged[merged["Malzeme Grubu"].str.lower().str.contains(filters["malzeme_grubu"], regex=True)]
                else:
                    filtered = brand_df[brand_df["Malzeme Grubu"].str.lower().str.contains(keyword)]

                if filters.get("kategori"):
                    filtered = filtered[filtered["Kategori"].str.lower() == filters["kategori"].lower()]
            else:
                filtered = brand_df[brand_df["Malzeme Grubu"].str.lower().str.contains(keyword)]

            # threshold dict ise (ör: Adapanel) aynı mantık devam
            if isinstance(rule["threshold"], dict):
                paket_sum = brand_df[brand_df["Malzeme Grubu"].str.lower().str.contains("paket")]["Net Satış Miktarı"].sum()
                ozel_sum = brand_df[brand_df["Malzeme Grubu"].str.lower().str.contains("özel")]["Net Satış Miktarı"].sum()
                paket_th = rule["threshold"].get("Paket", 0)
                ozel_th = rule["threshold"].get("Özel Üretim", 0)
                if (paket_sum < paket_th) and (ozel_sum < ozel_th):
                    has_recommendation = True
                    block += f"""
                    <div class='normal-message mt-2'>
                        🔹 <b>{rule['keyword']} Satışınız</b>: <b>Paket: {paket_sum:.1f}, Özel Üretim: {ozel_sum:.1f}</b> (Hedefler: Paket {paket_th}, Özel Üretim {ozel_th})<br>
                        ➔ {rule['message']}
                    </div>
                    """
                continue
            if not filtered.empty:
                product_sales = filtered["Net Satış Miktarı"].sum()
                birim = get_unit_from_keyword(keyword)
                hedef_birim = " Rulo" if "duvar kağıdı" in keyword else (f" {birim}" if birim else "")
                if product_sales < rule["threshold"]:
                    has_recommendation = True
                    filters_text = ""
                    block += f"""
                    <div class='normal-message mt-2'>
                        🔹 <b>{rule['keyword']} Satışınız</b>: <b>{product_sales:.1f} {birim}</b> (Hedef: {rule['threshold']}{hedef_birim})<br>
                        ➔ {rule['message']}
                        {filters_text}
                    </div>
                    """

        if not has_recommendation:
            block += """
            <div style="background-color: #f8f9fa; border-left: 4px solid #ccc; padding: 15px; border-radius: 8px; margin-bottom: 10px; color: #555; font-style: italic;">
                ✅ Bu kategoriye ait önerilecek özel bir durum bulunmamaktadır. Başarılarınızın devamını dileriz....
            </div>
            """

        block += "</div>"
        combined_blocks.append(block)

    if not combined_blocks:
        return "<div class='no-recommendation'>✅ Tüm markalarda yeterli satış ve öneri durumu görünmüyor.</div>"

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




def generate_pie_charts(satilan_urunler, satilmayan_urunler, df):
    import matplotlib.pyplot as plt
    import base64
    import io
    import matplotlib.patches as mpatches
    from adjustText import adjust_text

    df.columns = df.columns.str.strip()
    categories = ["AdaHome", "AdaPanel", "Adawall"]
    colors = ['#ffcc00', '#66b3ff', '#99ff99']
    chart_buffers = []

    # --- GRAFİK 1: Satılan vs Satılmayan ürün adedi ---
    fig1, ax1 = plt.subplots(figsize=(3, 3))
    wedges, texts, autotexts = ax1.pie(
        [len(satilan_urunler), len(satilmayan_urunler)],
        labels=["Satılan", "Satılmayan"],
        autopct='%1.1f%%',
        colors=["#4CAF50", "#FF6347"],
        explode=(0.1, 0),
        shadow=True,
        startangle=90,
        textprops={'fontsize': 8, 'fontweight': 'bold', 'ha': 'center'},
        labeldistance=1.2
    )
    
    ax1.set_title("Toplam Ürün Çeşidi Satışı", fontsize=14, fontweight='bold', pad=20)

    fig1.tight_layout()
    buf1 = io.BytesIO()
    plt.savefig(buf1, format="png", dpi=200, bbox_inches='tight')
    buf1.seek(0)
    chart_buffers.append(base64.b64encode(buf1.read()).decode("utf8"))
    plt.close(fig1)

    # --- GRAFİK 2: KDV'li satış tutarı yüzdesi ---
    fig2, ax2 = plt.subplots(figsize=(4, 4), dpi=250)
    df_satilan = df[df["Malzeme Grubu"].isin(satilan_urunler)]

    try:
        tutar_column = "Kdv Li Net Satış Tutar (TL)"
        df[tutar_column] = df[tutar_column].astype(float)
    except KeyError:
        tutar_column = "Kdv Li Net Satış Tutar"
        df[tutar_column] = df[tutar_column].astype(float)

    # Regex desenlerini değiştirdik
    sales_by_category = {
        cat: df_satilan[df_satilan["Malzeme Grubu"].str.contains(cat.lower(), case=False)][tutar_column].sum()
        for cat in categories
    }

    values = list(sales_by_category.values())
    labels = list(sales_by_category.keys())

    # Eğer hiç satış yoksa veya tüm değerler sıfırsa
    if sum(values) == 0:
        wedges, texts = ax2.pie(
            [1],
            labels=["Satış Yok"],
            colors=["#e0e0e0"],
            startangle=90,
            textprops={'fontsize': 12, 'fontweight': 'bold'}
        )
        ax2.set_title("KDV'li Net Satış Tutarına Göre Dağılım\n(Henüz Satış Yok)", fontsize=14, fontweight='bold')
    else:
        total_sales = sum(values)
        percentages = [round((value / total_sales) * 100, 1) for value in values]

        wedges, texts = ax2.pie(
            values,
            labels=None,
            startangle=90,
            colors=colors,
            pctdistance=0.75,
            labeldistance=1.4,
            textprops={'fontsize': 8, 'fontweight': 'bold', 'ha': 'center'},
            wedgeprops={'width': 0.3}
        )

        ax2.set_title("KDV'li Net Satış Tutarına Göre Dağılım", fontsize=14, fontweight='bold')

        legend_labels = [
            f"{cat}: ₺{sales_by_category[cat]:,.0f} ({percentages[i]}%)" for i, cat in enumerate(categories)
        ]
        legend_patches = [
            mpatches.Patch(color=colors[i], label=legend_labels[i]) for i in range(len(categories))
        ]

        ax2.legend(
            handles=legend_patches,
            loc='lower center',
            bbox_to_anchor=(0.5, -0.25),
            fontsize=10,
            frameon=False
        )

    fig2.tight_layout()
    buf2 = io.BytesIO()
    plt.savefig(buf2, format="png", dpi=200, bbox_inches='tight')
    buf2.seek(0)
    chart_buffers.append(base64.b64encode(buf2.read()).decode("utf8"))
    plt.close(fig2)
    return chart_buffers










from flask import send_file

from flask import send_file, session

import os





from flask import send_file




from flask import send_file










import os

@app.route("/kapat")
def kapat():
    session.clear()
    return redirect(url_for("login"))


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


import threading
from flask import render_template





@app.route("/", methods=["GET", "POST"])
@login_required
def upload_file():
    recommendations_html = None
    missing_recommendations_html = None
    table_data = None
    missing_products_html = None
    pie_chart_url = None
    rapor_tipi = None
    pie_chart_url2 = None
    
    uploaded_filename = None
    combined_recommendations = None
    grouped_missing = None
    ciro = 0

    # Uploads klasörünün mevcut durumunu logla
    print("\n=== Uploads Klasörü Durumu ===")
    if os.path.exists(UPLOAD_FOLDER):
        files = os.listdir(UPLOAD_FOLDER)
        if files:
            print("Mevcut Dosyalar:")
            for file in files:
                file_path = os.path.join(UPLOAD_FOLDER, file)
                file_size = os.path.getsize(file_path) / 1024  # KB cinsinden
                print(f"- {file} ({file_size:.2f} KB)")
        else:
            print("Klasör boş")
    else:
        print("Uploads klasörü henüz oluşturulmamış")
    print("=============================\n")

    if request.method == "POST" and 'file' in request.files:
        file = request.files['file']
        if file:
            # Uploads klasörünü kontrol et ve oluştur
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            
            # Önceki tüm dosyaları sil
            for filename in os.listdir(UPLOAD_FOLDER):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        print(f'Eski dosya silindi: {filename}')
                except Exception as e:
                    print(f'Dosya silinirken hata oluştu: {e}')

            # Yeni dosyayı kaydet
            uploaded_filename = secure_filename_tr(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, uploaded_filename)
            file.save(file_path)
            print(f'Yeni dosya kaydedildi: {uploaded_filename}')

            # Excel dosyası ise CSV'ye dönüştür
            if uploaded_filename.lower().endswith(('.xlsx', '.xls')):
                try:
                    # Excel dosyasını oku
                    df = pd.read_excel(file_path)
                    # CSV dosya adını oluştur
                    csv_filename = os.path.splitext(uploaded_filename)[0] + '.csv'
                    csv_path = os.path.join(UPLOAD_FOLDER, csv_filename)
                    # CSV olarak kaydet
                    df.to_csv(csv_path, sep=';', index=False, encoding='utf-8')
                    # Orijinal Excel dosyasını sil
                    os.remove(file_path)
                    # CSV dosyasını kullan
                    file_path = csv_path
                    uploaded_filename = csv_filename
                    print(f'Excel dosyası CSV\'ye dönüştürüldü: {csv_filename}')
                except Exception as e:
                    return f"Excel dosyası dönüştürülürken hata oluştu:<br><pre>{str(e)}</pre>"

            # Yükleme sonrası klasör durumunu logla
            print("\n=== Yükleme Sonrası Uploads Klasörü Durumu ===")
            files = os.listdir(UPLOAD_FOLDER)
            if files:
                print("Mevcut Dosyalar:")
                for file in files:
                    file_path = os.path.join(UPLOAD_FOLDER, file)
                    file_size = os.path.getsize(file_path) / 1024  # KB cinsinden
                    print(f"- {file} ({file_size:.2f} KB)")
            else:
                print("Klasör boş")
            print("===========================================\n")

            try:
                df_cleaned, rapor_tipi = detect_and_extract_columns(file_path)
                session['data'] = df_cleaned.to_dict(orient="records")
                table_data = df_cleaned.to_dict(orient="records")

                # ✅ Satılan ürünler
                satilan_urunler = set(df_cleaned["Malzeme Grubu"].astype(str).str.strip())

                # ✅ Katalogtan eksikleri tespit et (sadece görüntü için)
                satilmayan_urunler = urun_katalogu - satilan_urunler
                grouped_missing = group_missing_products_by_brand(satilmayan_urunler)

                # ✅ Yeni öneri sistemi
                combined_recommendations = generate_combined_recommendations(df_cleaned)

                # ✅ Toplam Ciro Hesabı
                ciro = df_cleaned["Kdv Li Net Satış Tutar"].sum()

                # Sadece görsel gösterim için
                missing_products_html = "<br>".join(sorted(satilmayan_urunler)) if satilmayan_urunler else "✅ Tüm ürünler satılmış!"

                charts = generate_pie_charts(satilan_urunler, satilmayan_urunler, df_cleaned)
                pie_chart_url, pie_chart_url2 = charts

            except Exception as e:
                return f"Hata oluştu:<br><pre>{str(e)}</pre>"

    return render_template("index.html",
                           table_data=table_data,
                           missing_products=missing_products_html,
                           missing_recommendations=missing_recommendations_html,
                           recommendations=recommendations_html,
                           pie_chart_url=pie_chart_url,
                           rapor_tipi=rapor_tipi,
                           ciro=ciro,
                           pie_chart_url2=pie_chart_url2,
                           uploaded_filename=uploaded_filename,
                           combined_recommendations=combined_recommendations,
                           grouped_missing_products=grouped_missing)







@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin_panel():
    try:
        rules = load_rules()
        simple_recommendations = load_simple_recommendations()
    except Exception as e:
        print(f"Error loading rules: {str(e)}")
        rules = []
        simple_recommendations = []

    if request.method == "POST":
        try:
            action = request.form.get("action")

            if action == "add":
                keyword = request.form.get("keyword", "").strip()
                threshold = request.form.get("threshold", "0").strip()
                message = request.form.get("message", "").strip()
                malzeme_grubu = request.form.get("malzeme_grubu", "").strip()
                kategori = request.form.get("kategori", "").strip()

                # Filtreleri oluştur
                filters = None
                if malzeme_grubu or kategori:
                    filters = {
                        "malzeme_grubu": malzeme_grubu if malzeme_grubu else None,
                        "kategori": kategori if kategori else None
                    }

                # Threshold'u sayıya çevir
                try:
                    threshold = int(threshold)
                except ValueError:
                    threshold = 0

                rules.append({
                    "keyword": keyword,
                    "threshold": threshold,
                    "message": message,
                    "filters": filters
                })
                save_rules(rules)

            elif action == "delete":
                try:
                    index = int(request.form.get("index", "0"))
                    if 0 <= index < len(rules):
                        rules.pop(index)
                        save_rules(rules)
                except (ValueError, IndexError):
                    pass

            elif action == "add_simple":
                message = request.form.get("simple_message", "").strip()
                if message:
                    simple_recommendations.append({
                        "message": message
                    })
                    save_simple_recommendations(simple_recommendations)

            elif action == "delete_simple":
                try:
                    index = int(request.form.get("simple_index", "0"))
                    if 0 <= index < len(simple_recommendations):
                        simple_recommendations.pop(index)
                        save_simple_recommendations(simple_recommendations)
                except (ValueError, IndexError):
                    pass

            return redirect("/admin")

        except Exception as e:
            print(f"Error processing form: {str(e)}")
            return redirect("/admin")

    return render_template("admin.html", rules=rules, simple_recommendations=simple_recommendations)

from flask import Flask, request, render_template, session


import threading
import webbrowser

if __name__ == "__main__":
    import threading
    import webbrowser
    import socket
    import os
    from contextlib import closing
    
    # Kullanılabilir port bulma fonksiyonu
    def find_free_port():
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]
    
    # Sistem tepsisine ikon ekleme (Windows için)
    try:
        import pystray
        from PIL import Image
        from pystray import MenuItem as item
        
        def setup(icon):
            icon.visible = True

        def open_browser(icon):
            webbrowser.open(f"http://127.0.0.1:{port}/login")

        def exit_action(icon):
            icon.stop()
            os._exit(0)
            
        # Uygulamayı başlat
        port = find_free_port()
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}/login")).start()
        
        # Sistem tepsisi için ikon ayarla
        try:
            image = Image.open(resource_path("static/favicon.ico"))
            menu = (item('Uygulamayı Aç', open_browser), item('Çıkış', exit_action))
            icon = pystray.Icon("Analiz", image, "Analiz Uygulaması", menu)
            threading.Thread(target=lambda: icon.run()).start()
        except Exception as e:
            print(f"Sistem tepsisi ikonu oluşturulamadı: {e}")
            
        # Flask uygulamasını başlat
        app.run(debug=False, port=port, use_reloader=False)
    except ImportError:
        # pystray bulunamazsa standart başlatma
        port = 5000
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}/login")).start()
        app.run(debug=False, port=port, use_reloader=False)

@app.route("/simple_recommendations", methods=["GET", "POST"])
@login_required
def simple_recommendations_panel():
    try:
        recommendations = load_simple_recommendations()
    except Exception as e:
        print(f"Error loading recommendations: {str(e)}")
        recommendations = []

    if request.method == "POST":
        try:
            action = request.form.get("action")

            if action == "add":
                message = request.form.get("message", "").strip()
                if message:
                    recommendations.append({
                        "message": message
                    })
                    save_simple_recommendations(recommendations)

            elif action == "delete":
                try:
                    index = int(request.form.get("index", "0"))
                    if 0 <= index < len(recommendations):
                        recommendations.pop(index)
                        save_simple_recommendations(recommendations)
                except (ValueError, IndexError):
                    pass

            return redirect("/simple_recommendations")

        except Exception as e:
            print(f"Error processing form: {str(e)}")
            return redirect("/simple_recommendations")

    return render_template("simple_recommendations.html", recommendations=recommendations)