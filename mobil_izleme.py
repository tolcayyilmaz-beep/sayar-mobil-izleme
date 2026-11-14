import os
import json
import time
import html
import sqlite3
import tempfile
import requests
import pandas as pd
import streamlit as st
from cryptography.fernet import Fernet

# Sayfa ve Mobil Görünüm Ayarları
st.set_page_config(
    page_title="Sayar Yapı | Sipariş İzleme",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Özel CSS: Streamlit barlarını gizle + İkonlu Üst Bar + Kompakt KPI + Modern Kart ve Tablo Stilleri
st.markdown("""
    <style>
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    footer,
    [data-testid="stStatusWidget"],
    .viewerBadge_container__r5tak,
    .viewerBadge_link__qRIco,
    div[class^="viewerBadge_"] {
        display: none !important;
        visibility: hidden !important;
    }
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    /* Renk Kodlu Kurumsal Başlık Şeridi */
    .header-banner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-left: 5px solid #007acc;
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 10px;
        color: #f8fafc;
        box-shadow: 0 3px 8px rgba(0,0,0,0.2);
        gap: 8px;
    }
    .header-info {
        flex: 1;
        min-width: 0;
    }
    .header-title {
        font-size: 15px;
        font-weight: 700;
        margin: 0;
        color: #ffffff;
        letter-spacing: 0.2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .header-sub {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 2px;
    }
    .header-actions {
        display: flex;
        gap: 6px;
        flex-shrink: 0;
    }
    .icon-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background-color: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.16);
        color: #ffffff !important;
        text-decoration: none !important;
        font-size: 16px;
        cursor: pointer;
    }
    .icon-btn:active {
        background-color: #007acc;
    }
    /* Tıklanabilir Kompakt Yan Yana 3'lü KPI Şeridi */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-bottom: 10px;
    }
    a.kpi-card {
        display: block;
        background-color: #1e1e24;
        border: 1px solid #32323a;
        border-radius: 10px;
        padding: 8px 10px;
        text-align: center;
        text-decoration: none !important;
        transition: transform 0.1s ease, background-color 0.15s ease;
        cursor: pointer;
    }
    a.kpi-card:hover {
        background-color: #272730;
    }
    a.kpi-card:active {
        transform: scale(0.98);
    }
    .kpi-blue { border-top: 3px solid #007acc !important; }
    .kpi-orange { border-top: 3px solid #e67e22 !important; }
    .kpi-green { border-top: 3px solid #2ecc71 !important; }
    .kpi-active {
        background-color: #1e1e24 !important;
        border: 2px solid #ef4444 !important;
        box-shadow: 0 0 8px rgba(239, 68, 68, 0.35);
    }
    .kpi-label {
        font-size: 11px;
        color: #a1a1aa;
        font-weight: 600;
        margin-bottom: 2px;
        white-space: nowrap;
    }
    .kpi-value {
        font-size: 20px;
        font-weight: 800;
        color: #ffffff;
        line-height: 1.2;
    }
    /* Sipariş Kartları (st.expander Özelleştirmesi) */
    div[data-testid="stExpander"] {
        border-radius: 10px !important;
        border: 1px solid rgba(148, 163, 184, 0.28) !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05) !important;
        margin-bottom: 8px !important;
        overflow: hidden;
    }
    div[data-testid="stExpander"] summary {
        padding-top: 10px !important;
        padding-bottom: 10px !important;
        line-height: 1.45 !important;
    }
    div[data-testid="stExpander"] summary p {
        font-size: 13.5px !important;
        margin: 0 !important;
    }
    /* Kart İçi Süreç İlerleme Çubuğu (Stepper) */
    .stepper {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 4px;
        margin: 4px 0 12px 0;
        padding: 6px 8px;
        background: rgba(148, 163, 184, 0.1);
        border-radius: 8px;
        font-size: 11px;
        font-weight: 600;
    }
    .step-item {
        flex: 1;
        text-align: center;
        padding: 4px 2px;
        border-radius: 5px;
        color: #94a3b8;
        background: rgba(148, 163, 184, 0.08);
    }
    .step-done {
        background: #007acc;
        color: #ffffff;
    }
    .step-cancel {
        background: #e74c3c;
        color: #ffffff;
    }
    /* Kart İçi Öne Çıkan Bilgi Kutusu */
    .info-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 6px 12px;
        font-size: 13px;
        margin-bottom: 10px;
    }
    .info-item-label {
        font-size: 11px;
        color: #64748b;
        display: block;
    }
    .info-item-val {
        font-weight: 600;
    }
    /* Hafif ve Hızlı HTML Ürün Tablosu */
    .urun-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 6px;
        font-size: 12.5px;
        border-radius: 8px;
        overflow: hidden;
    }
    .urun-table th {
        background-color: #1e293b;
        color: #f8fafc;
        text-align: left;
        padding: 7px 9px;
        font-weight: 600;
        font-size: 11.5px;
    }
    .urun-table td {
        padding: 7px 9px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.22);
    }
    .urun-table tr:nth-child(even) td {
        background-color: rgba(148, 163, 184, 0.06);
    }
    .urun-miktar {
        font-weight: 700;
        text-align: right;
        white-space: nowrap;
    }
    .badge {
        padding: 3px 8px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        font-size: 11.5px;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# Şifreli Oturum Jetonu (Beni Hatırla) Oluşturma ve Doğrulama
def token_olustur(yetki_tipi, yetki_deger, gun=90):
    secret_key = st.secrets["DB_SECRET_KEY"].encode("utf-8")
    fernet = Fernet(secret_key)
    payload = json.dumps({
        "tip": yetki_tipi,
        "deger": yetki_deger,
        "exp": int(time.time()) + (gun * 86400)
    }).encode("utf-8")
    return fernet.encrypt(payload).decode("utf-8")

def token_dogrula(token_str):
    try:
        secret_key = st.secrets["DB_SECRET_KEY"].encode("utf-8")
        fernet = Fernet(secret_key)
        data = json.loads(fernet.decrypt(token_str.encode("utf-8")).decode("utf-8"))
        if data.get("exp", 0) > int(time.time()):
            return data.get("tip"), data.get("deger")
    except Exception:
        pass
    return None, None

# 1. Rol, Müşteri ve Sipariş Veren Bazlı Şifre + Beni Hatırla Kontrolü
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.yetki_tipi = None
        st.session_state.yetki_deger = None
        st.session_state.active_token = ""

    if st.query_params.get("action") == "logout":
        st.session_state.authenticated = False
        st.session_state.yetki_tipi = None
        st.session_state.yetki_deger = None
        st.session_state.active_token = ""
        st.query_params.clear()
        st.rerun()

    url_token = st.query_params.get("token", "")
    if url_token:
        t_tip, t_deger = token_dogrula(url_token)
        if t_tip:
            st.session_state.authenticated = True
            st.session_state.yetki_tipi = t_tip
            st.session_state.yetki_deger = t_deger
            st.session_state.active_token = url_token
        else:
            st.query_params.clear()

    url_musteri = st.query_params.get("musteri", "")
    url_veren = st.query_params.get("veren", "")

    if not st.session_state.authenticated:
        st.markdown("""
            <div class="header-banner">
                <div class="header-info">
                    <div class="header-title">🏗️ SAYAR YAPI</div>
                    <div class="header-sub">Sipariş Takip ve İzleme Sistemi</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if url_musteri:
            st.caption(f"Müşteri Girişi: **{url_musteri}**")
        elif url_veren:
            st.caption(f"Personel Girişi: **{url_veren}**")

        pin = st.text_input("Erişim Şifresi:", type="password")
        beni_hatirla = st.checkbox("Beni Hatırla", value=True)

        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            basarili_tip = None
            basarili_deger = None

            if pin == st.secrets["APP_PASSWORD"]:
                basarili_tip = "YONETICI"
                basarili_deger = None

            if not basarili_tip and not url_veren:
                musteri_map = st.secrets.get("MUSTERI_SIFRELERI", {})
                for m_adi, m_sifre in musteri_map.items():
                    if pin == str(m_sifre):
                        if not url_musteri or url_musteri.strip().upper() == m_adi.strip().upper():
                            basarili_tip = "MUSTERI"
                            basarili_deger = m_adi
                            break

            if not basarili_tip and not url_musteri:
                veren_map = st.secrets.get("SIPARIS_VEREN_SIFRELERI", {})
                for v_adi, v_sifre in veren_map.items():
                    if pin == str(v_sifre):
                        if not url_veren or url_veren.strip().upper() == v_adi.strip().upper():
                            basarili_tip = "SIPARIS_VEREN"
                            basarili_deger = v_adi
                            break

            if basarili_tip:
                st.session_state.authenticated = True
                st.session_state.yetki_tipi = basarili_tip
                st.session_state.yetki_deger = basarili_deger
                if beni_hatirla:
                    yeni_token = token_olustur(basarili_tip, basarili_deger, gun=90)
                    st.session_state.active_token = yeni_token
                    st.query_params["token"] = yeni_token
                else:
                    st.session_state.active_token = ""
                st.rerun()
            else:
                st.error("Hatalı erişim şifresi!")
        st.stop()

check_password()

# Session State Varsayılanları
if "kpi_mod" not in st.session_state:
    st.session_state.kpi_mod = "SEVK"
if "sayfa_limiti" not in st.session_state:
    st.session_state.sayfa_limiti = 50

if st.query_params.get("action") == "refresh":
    st.cache_data.clear()
    st.session_state.sayfa_limiti = 50
    del st.query_params["action"]
    st.rerun()

if "kpi" in st.query_params:
    secilen_kpi = st.query_params.get("kpi", "").upper()
    if secilen_kpi in ("TUMU", "ONAY", "SEVK"):
        st.session_state.kpi_mod = secilen_kpi
        st.session_state.sayfa_limiti = 50
    del st.query_params["kpi"]
    st.rerun()

yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger
aktif_token = st.session_state.get("active_token") or st.query_params.get("token", "")

# 2. Google Drive'dan Şifreli DB İndirme ve RAM'de Çözme
@st.cache_data(ttl=30)
def verileri_getir():
    file_id = st.secrets["GDRIVE_FILE_ID"]
    secret_key = st.secrets["DB_SECRET_KEY"].encode("utf-8")

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(download_url, timeout=15)
    response.raise_for_status()

    fernet = Fernet(secret_key)
    decrypted_bytes = fernet.decrypt(response.content)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
            tmp_file.write(decrypted_bytes)
            tmp_path = tmp_file.name

        conn = sqlite3.connect(tmp_path)
        df_siparisler = pd.read_sql_query("SELECT * FROM siparisler ORDER BY siparis_no DESC", conn)
        df_kalemler = pd.read_sql_query("SELECT * FROM siparis_kalemleri", conn)
        conn.close()
        return df_siparisler, df_kalemler
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# Renk Kodlu Üst Başlık Şeridi
if yetki_tipi == "MUSTERI":
    baslik_metni = f"🏗️ SAYAR YAPI | {yetki_deger}"
    alt_metin = "Müşteri Sipariş İzleme Paneli"
elif yetki_tipi == "SIPARIS_VEREN":
    baslik_metni = f"🏗️ SAYAR YAPI | {yetki_deger}"
    alt_metin = "Personel Sipariş İzleme Paneli"
else:
    baslik_metni = "🏗️ SAYAR YAPI | Sipariş İzleme"
    alt_metin = "Yönetici Canlı Takip Paneli"

token_param = f"&token={aktif_token}" if aktif_token else ""
refresh_href = f"?action=refresh{token_param}"

st.markdown(f"""
    <div class="header-banner">
        <div class="header-info">
            <div class="header-title">{baslik_metni}</div>
            <div class="header-sub">{alt_metin}</div>
        </div>
        <div class="header-actions">
            <a href="{refresh_href}" target="_self" class="icon-btn" title="Yenile">🔄</a>
            <a href="?action=logout" target="_self" class="icon-btn" title="Çıkış">🚪</a>
        </div>
    </div>
""", unsafe_allow_html=True)

try:
    df_sip, df_kalem = verileri_getir()
except Exception as e:
    st.error(f"Veritabanı okunamadı. Bağlantıyı ve anahtarı kontrol edin.\nDetay: {e}")
    st.stop()

# Yetki Tipine Göre Veriyi Kısıtlama
if yetki_tipi == "MUSTERI":
    df_sip = df_sip[df_sip["musteri"].fillna("").str.strip().str.upper() == yetki_deger.strip().upper()]
elif yetki_tipi == "SIPARIS_VEREN":
    df_sip = df_sip[df_sip["siparis_veren"].fillna("").str.strip().str.upper() == yetki_deger.strip().upper()]

# 3. Tıklanabilir Kompakt Yan Yana 3'lü KPI Şeridi
toplam_siparis = len(df_sip)
onay_bekleyen = len(df_sip[df_sip["operasyon"] == "ONAY BEKLİYOR"])
sevk_bekleyen = len(
    df_sip[
        (df_sip["operasyon"] != "MUHASEBEYE İLETİLDİ") &
        (df_sip["operasyon"] != "İPTAL EDİLDİ") &
        (df_sip["durum"] != "İptal")
    ]
)

kpi_mod = st.session_state.kpi_mod
cls_tumu = "kpi-active" if kpi_mod == "TUMU" else ""
cls_onay = "kpi-active" if kpi_mod == "ONAY" else ""
cls_sevk = "kpi-active" if kpi_mod == "SEVK" else ""

st.markdown(f"""
    <div class="kpi-grid">
        <a href="?kpi=TUMU{token_param}" target="_self" class="kpi-card kpi-blue {cls_tumu}" title="Tüm siparişleri göster">
            <div class="kpi-label">Toplam Sipariş</div>
            <div class="kpi-value">{toplam_siparis}</div>
        </a>
        <a href="?kpi=ONAY{token_param}" target="_self" class="kpi-card kpi-orange {cls_onay}" title="Sadece onay bekleyenleri göster">
            <div class="kpi-label">Onay Bekleyen</div>
            <div class="kpi-value">{onay_bekleyen}</div>
        </a>
        <a href="?kpi=SEVK{token_param}" target="_self" class="kpi-card kpi-green {cls_sevk}" title="Sadece sevk bekleyenleri göster">
            <div class="kpi-label">Sevk Bekleyen</div>
            <div class="kpi-value">{sevk_bekleyen}</div>
        </a>
    </div>
""", unsafe_allow_html=True)

# 4. Hızlı Arama + Tek "Filtrele" Çekmecesi
arama = st.text_input("", placeholder="🔍 Ara (Sipariş No, Firma, Müşteri, Şantiye)...", label_visibility="collapsed")

varsayilan_op = "ONAY BEKLİYOR" if kpi_mod == "ONAY" else "[TÜMÜ]"
varsayilan_gizle = (kpi_mod == "SEVK")

with st.expander("⚙️ Filtrele", expanded=False):
    op_listesi = ["[TÜMÜ]"] + sorted(df_sip["operasyon"].dropna().unique().tolist())
    op_index = op_listesi.index(varsayilan_op) if varsayilan_op in op_listesi else 0

    if yetki_tipi == "MUSTERI":
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            secili_op = st.selectbox("Operasyon", op_listesi, index=op_index)
        with f_col2:
            firma_listesi = ["[TÜMÜ]"] + sorted(df_sip["firma"].dropna().unique().tolist())
            secili_firma = st.selectbox("Tedarikçi Firma", firma_listesi)
        secili_musteri = "[TÜMÜ]"
    else:
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            secili_op = st.selectbox("Operasyon", op_listesi, index=op_index)
        with f_col2:
            firma_listesi = ["[TÜMÜ]"] + sorted(df_sip["firma"].dropna().unique().tolist())
            secili_firma = st.selectbox("Tedarikçi Firma", firma_listesi)
        with f_col3:
            musteri_listesi = ["[TÜMÜ]"] + sorted(df_sip["musteri"].dropna().unique().tolist())
            secili_musteri = st.selectbox("Müşteri", musteri_listesi)

    c_chk1, c_chk2 = st.columns(2)
    with c_chk1:
        gizle_muhasebe = st.checkbox("Muhasebeye İletilenleri Gizle", value=varsayilan_gizle)
    with c_chk2:
        gizle_iptal = st.checkbox("İptal Edilenleri Gizle", value=varsayilan_gizle)

# Filtreleme Uygulama
filtered = df_sip.copy()

if gizle_muhasebe:
    filtered = filtered[filtered["operasyon"] != "MUHASEBEYE İLETİLDİ"]
if gizle_iptal:
    filtered = filtered[(filtered["operasyon"] != "İPTAL EDİLDİ") & (filtered["durum"] != "İptal")]
if secili_op != "[TÜMÜ]":
    filtered = filtered[filtered["operasyon"] == secili_op]
if secili_firma != "[TÜMÜ]":
    filtered = filtered[filtered["firma"] == secili_firma]
if secili_musteri != "[TÜMÜ]":
    filtered = filtered[filtered["musteri"] == secili_musteri]
if arama.strip():
    q = arama.strip().lower()
    mask = (
        filtered["siparis_no"].astype(str).str.contains(q, na=False) |
        filtered["firma"].fillna("").str.lower().str.contains(q) |
        filtered["musteri"].fillna("").str.lower().str.contains(q) |
        filtered["santiye"].fillna("").str.lower().str.contains(q)
    )
    filtered = filtered[mask]

# 5. Ürün Bazlı Hızlı Özet ve Toplam Miktar Hesabı
with st.expander("📦 Ürün Bazlı Toplam Özeti", expanded=False):
    aktif_sip_nolar = filtered["siparis_no"].tolist()
    ozet_kalemler = df_kalem[df_kalem["siparis_no"].isin(aktif_sip_nolar)].copy()

    if not ozet_kalemler.empty:
        ozet_kalemler["urun"] = ozet_kalemler["urun"].fillna("-").str.strip()
        ozet_kalemler["birim"] = ozet_kalemler["birim"].fillna("-").str.strip()
        ozet_kalemler["miktar_str"] = ozet_kalemler["miktar"].fillna("").astype(str).str.strip()

        temiz_sayi = ozet_kalemler["miktar_str"].str.replace(",", ".", regex=False)
        ozet_kalemler["miktar_num"] = pd.to_numeric(temiz_sayi, errors="coerce")

        sayisal_df = ozet_kalemler.dropna(subset=["miktar_num"])
        metin_df = ozet_kalemler[ozet_kalemler["miktar_num"].isna()]

        if not sayisal_df.empty:
            grup_sayisal = (
                sayisal_df.groupby(["urun", "birim"], as_index=False)
                .agg(
                    Siparis_Sayisi=("siparis_no", "nunique"),
                    Toplam_Miktar=("miktar_num", "sum")
                )
                .sort_values(by=["urun", "birim"])
            )
            grup_sayisal["Toplam_Miktar"] = grup_sayisal["Toplam_Miktar"].apply(
                lambda x: f"{int(x):,}".replace(",", ".") if x == int(x) else f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            grup_sayisal.columns = ["Ürün", "Birim", "Sipariş", "Toplam Miktar"]
            st.dataframe(grup_sayisal, use_container_width=True, hide_index=True)

        if not metin_df.empty:
            st.caption("Metin / Özel Miktarlı Kalemler:")
            grup_metin = (
                metin_df.groupby(["urun", "birim", "miktar_str"], as_index=False)
                .agg(Siparis_Sayisi=("siparis_no", "nunique"))
                .sort_values(by=["urun"])
            )
            grup_metin.columns = ["Ürün", "Birim", "Miktar Notu", "Sipariş"]
            st.dataframe(grup_metin, use_container_width=True, hide_index=True)
    else:
        st.caption("Seçili filtrelere ait ürün kalemi bulunmuyor.")

toplam_filtrelenen = len(filtered)
gosterilen_limit = st.session_state.sayfa_limiti
gosterilen_adet = min(toplam_filtrelenen, gosterilen_limit)

st.caption(f"Gösterilen sipariş sayısı: **{gosterilen_adet} / {toplam_filtrelenen}**")

OP_RENK = {
    "İŞLENDİ": "#007acc",
    "ONAY BEKLİYOR": "#e67e22",
    "ONAYLANDI": "#1abc9c",
    "MUHASEBEYE İLETİLDİ": "#2ecc71",
    "İPTAL EDİLDİ": "#e74c3c",
    "KISMİ EVRAK": "#8e44ad"
}

OP_IKON = {
    "İŞLENDİ": "🔵",
    "ONAY BEKLİYOR": "🟠",
    "ONAYLANDI": "🟢",
    "MUHASEBEYE İLETİLDİ": "✅",
    "İPTAL EDİLDİ": "🔴",
    "KISMİ EVRAK": "🟣"
}

def stepper_html(op_upper):
    if op_upper == "İPTAL EDİLDİ":
        return '<div class="stepper"><div class="step-item step-cancel">❌ Sipariş İptal Edildi</div></div>'
    adim = 1
    if op_upper == "ONAYLANDI":
        adim = 2
    elif op_upper in ("İŞLENDİ", "KISMİ EVRAK"):
        adim = 3
    elif op_upper == "MUHASEBEYE İLETİLDİ":
        adim = 4

    c1 = "step-done" if adim >= 1 else ""
    c2 = "step-done" if adim >= 2 else ""
    c3 = "step-done" if adim >= 3 else ""
    c4 = "step-done" if adim >= 4 else ""
    return f"""
        <div class="stepper">
            <div class="step-item {c1}">1. Alındı</div>
            <div class="step-item {c2}">2. Onay</div>
            <div class="step-item {c3}">3. İşlendi</div>
            <div class="step-item {c4}">4. Muhasebe</div>
        </div>
    """

# N+1 Optimizasyonu: Tüm sipariş kalemlerini döngü öncesinde grupla
kalem_gruplari = dict(tuple(df_kalem.groupby("siparis_no"))) if not df_kalem.empty else {}

# 6. Odaklı 2 Satırlı Mobil Sipariş Kartları (Firma, Müşteri, Şantiye ve Sipariş Tarihi Ön Planda)
for _, row in filtered.head(gosterilen_limit).iterrows():
    sip_no = row["siparis_no"]
    op_val = str(row["operasyon"] or "-")
    op_upper = op_val.upper()
    renk = OP_RENK.get(op_upper, "#555555")
    durum_ikon = OP_IKON.get(op_upper, "⚪")

    firma_str = row["firma"] or "-"
    musteri_str = row["musteri"] or "-"
    santiye_str = row["santiye"] or "-"
    tarih_str = row["tarih"] or "-"

    # 2 Satırlı Net Başlık: Üstte Firma & Müşteri, Altta Şantiye & Sipariş Tarihi
    if yetki_tipi == "MUSTERI":
        baslik = (
            f"{durum_ikon} **#{sip_no} | {firma_str}**  \n"
            f"📍 {santiye_str}  •  📅 {tarih_str}  •  *{op_val}*"
        )
    else:
        baslik = (
            f"{durum_ikon} **#{sip_no} | {firma_str} ➔ {musteri_str}**  \n"
            f"📍 {santiye_str}  •  📅 {tarih_str}  •  *{op_val}*"
        )

    with st.expander(baslik):
        st.markdown(
            f"<span class='badge' style='background-color:{renk};'>{html.escape(op_val)}</span> &nbsp; "
            f"**Durum:** {html.escape(str(row['durum'] or '-'))}",
            unsafe_allow_html=True
        )
        st.markdown(stepper_html(op_upper), unsafe_allow_html=True)

        # Öne Çıkan 4 Ana Bilgi + Ek Detaylar
        musteri_blok = "" if yetki_tipi == "MUSTERI" else f"""
            <div><span class="info-item-label">Müşteri</span><span class="info-item-val">{html.escape(str(musteri_str))}</span></div>
            <div><span class="info-item-label">Sipariş Veren</span><span class="info-item-val">{html.escape(str(row['siparis_veren'] or '-'))}</span></div>
        """

        st.markdown(f"""
            <div class="info-grid">
                <div><span class="info-item-label">Tedarikçi Firma</span><span class="info-item-val">{html.escape(str(firma_str))}</span></div>
                <div><span class="info-item-label">Sipariş Tarihi</span><span class="info-item-val">{html.escape(str(tarih_str))}</span></div>
                <div><span class="info-item-label">Şantiye</span><span class="info-item-val">{html.escape(str(santiye_str))}</span></div>
                <div><span class="info-item-label">Sevk Tarihi</span><span class="info-item-val">{html.escape(str(row['sevk_tarihi'] or '-'))}</span></div>
                {musteri_blok}
                <div><span class="info-item-label">Fabrika / Nakliye</span><span class="info-item-val">{html.escape(str(row['fabrika'] or '-'))} / {html.escape(str(row['nakliye'] or '-'))}</span></div>
                <div><span class="info-item-label">Ted. Sip. No</span><span class="info-item-val">{html.escape(str(row['ted_sip_no'] or '-'))}</span></div>
                <div><span class="info-item-label">Yetkili / Tel</span><span class="info-item-val">{html.escape(str(row['yetkili'] or '-'))} {html.escape(str(row['telefon'] or ''))}</span></div>
            </div>
        """, unsafe_allow_html=True)

        if row["notlar"]:
            st.info(f"📝 **Not:** {row['notlar']}")

        # Hafif ve Hızlı HTML Ürün Tablosu (st.dataframe yerine)
        sip_kalem_df = kalem_gruplari.get(sip_no)
        if sip_kalem_df is not None and not sip_kalem_df.empty:
            satirlar_html = ""
            for _, k_row in sip_kalem_df.iterrows():
                u_ad = html.escape(str(k_row["urun"] or "-"))
                u_birim = html.escape(str(k_row["birim"] or "-"))
                u_miktar = html.escape(str(k_row["miktar"] or "-"))
                satirlar_html += f"""
                    <tr>
                        <td>{u_ad}</td>
                        <td>{u_birim}</td>
                        <td class="urun-miktar">{u_miktar}</td>
                    </tr>
                """
            st.markdown(f"""
                <table class="urun-table">
                    <thead>
                        <tr>
                            <th>Ürün</th>
                            <th>Birim</th>
                            <th style="text-align:right;">Miktar</th>
                        </tr>
                    </thead>
                    <tbody>
                        {satirlar_html}
                    </tbody>
                </table>
            """, unsafe_allow_html=True)
        else:
            st.caption("Bu siparişe ait ürün kalemi bulunmuyor.")

# Sayfalama: Daha Fazla Göster Butonu
if toplam_filtrelenen > gosterilen_limit:
    kalan = toplam_filtrelenen - gosterilen_limit
    if st.button(f"⬇️ Daha Fazla Göster ({kalan} kayıt daha var)", use_container_width=True):
        st.session_state.sayfa_limiti += 50
        st.rerun()
