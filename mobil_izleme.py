import os

# Railway ortam değişkeninden secrets.toml dosyasını otomatik oluştur
if os.environ.get("STREAMLIT_SECRETS"):
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMLIT_SECRETS"])

import json
import time
import html
import sqlite3
import tempfile
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet

# Sayfa ve Mobil Görünüm Ayarları
st.set_page_config(
    page_title="Sayar Yapı | Sipariş İzleme",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Özel CSS: Kurumsal Çelik & Beton (Sıkılaştırılmış Kompakt Aydınlık Tema)
st.markdown("""
<style>
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="manage-app-button"],
footer,
.stAppDeployButton,
.viewerBadge_container__r5tak,
.viewerBadge_link__qRIco,
div[class*="viewerBadge"],
div[class*="StatusWidget"],
div[class*="profileContainer"],
div[class*="profilePreview"],
a[href*="streamlit.io/cloud"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
/* Sayfa Zemini: Taş Grisi */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
}
.block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 1.5rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
}
/* Streamlit blokları arasındaki genel dikey boşluğu daralt */
[data-testid="stVerticalBlock"] {
    gap: 0.45rem !important;
}
/* Kurumsal Başlık Şeridi: Arduvaz Lacivert + İnşaat Turuncusu Vurgu */
.header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-left: 5px solid #f97316;
    border-radius: 10px;
    padding: 9px 12px;
    margin-bottom: 4px;
    color: #f8fafc;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.14);
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
    color: #cbd5e1;
    margin-top: 2px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
}
/* Canlılık İndikatörü ve Zaman Damgası (Öneri 5) */
.live-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    padding: 1px 7px;
    border-radius: 999px;
    font-size: 10px;
    color: #e2e8f0;
    font-weight: 500;
}
.live-dot {
    width: 6px;
    height: 6px;
    background-color: #22c55e;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
    animation: pulse-green 2s infinite;
}
@keyframes pulse-green {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 5px rgba(34, 197, 94, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
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
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.18);
    color: #ffffff !important;
    text-decoration: none !important;
    font-size: 16px;
    cursor: pointer;
}
.icon-btn:active {
    background-color: #f97316;
}
/* Tıklanabilir Beyaz KPI Kartları */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 8px;
    margin-bottom: 8px;
}
a.kpi-card {
    display: block;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 9px;
    padding: 7px 8px;
    text-align: center;
    text-decoration: none !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    transition: transform 0.1s ease, box-shadow 0.15s ease;
    cursor: pointer;
}
a.kpi-card:hover {
    background-color: #f8fafc;
}
a.kpi-card:active {
    transform: scale(0.98);
}
.kpi-blue { border-top: 3px solid #0284c7 !important; }
.kpi-orange { border-top: 3px solid #f97316 !important; }
.kpi-green { border-top: 3px solid #16a34a !important; }
.kpi-active {
    background-color: #ffffff !important;
    border: 2px solid #ef4444 !important;
    box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2);
}
.kpi-label {
    font-size: 11px;
    color: #475569;
    font-weight: 600;
    margin-bottom: 1px;
    white-space: nowrap;
}
.kpi-value {
    font-size: 19px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
}
/* Arama + Popover Satırının Mobilde Yan Yana Kalması */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 6px !important;
    margin-top: 8px !important;
}
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:first-child {
    flex: 1 1 auto !important;
    min-width: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:last-child {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 54px !important;
}
/* Arama Kutusu Beyaz Zemin */
div[data-testid="stTextInput"] input {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
    color: #0f172a !important;
    height: 38px !important;
    padding-top: 6px !important;
    padding-bottom: 6px !important;
}
/* Popover Buton Tasarımı */
div[data-testid="stPopover"] > button {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
    color: #0f172a !important;
    height: 38px !important;
    padding: 0 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
}
div[data-testid="stPopover"] > button:hover {
    border-color: #f97316 !important;
    background-color: #fff7ed !important;
}
/* Aktif Filtre Etiketleri / Chips (Öneri 3) */
.chip-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 2px;
    margin-bottom: 4px;
    align-items: center;
}
a.filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background-color: #e2e8f0;
    color: #1e293b !important;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 600;
    text-decoration: none !important;
    transition: background-color 0.15s ease, border-color 0.15s ease;
}
a.filter-chip:hover {
    background-color: #fed7aa;
    border-color: #f97316;
    color: #9a3412 !important;
}
a.filter-chip-clear {
    background-color: #fee2e2;
    border-color: #fecaca;
    color: #b91c1c !important;
}
a.filter-chip-clear:hover {
    background-color: #fecaca;
}
/* Sipariş Kartları ve Sol Kenar Durum Şeridi (Öneri 2) */
div[data-testid="stExpander"] {
    background-color: #ffffff !important;
    border-radius: 9px !important;
    border: 1px solid #cbd5e1 !important;
    border-left: 4px solid #0284c7 !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
    margin-bottom: 3px !important;
    overflow: hidden;
}
/* Expander içindeki metin/ikon rengine göre sol kenar şeridini otomatik renklendir */
div[data-testid="stExpander"]:has(summary p:contains("🟠")),
div[data-testid="stExpander"]:has(.status-flag-orange) {
    border-left: 4px solid #f97316 !important;
}
div[data-testid="stExpander"]:has(.status-flag-green) {
    border-left: 4px solid #16a34a !important;
}
div[data-testid="stExpander"]:has(.status-flag-red) {
    border-left: 4px solid #ef4444 !important;
}
div[data-testid="stExpander"]:has(.status-flag-blue) {
    border-left: 4px solid #0284c7 !important;
}
div[data-testid="stExpander"] summary {
    display: flex !important;
    align-items: center !important;
    background-color: #ffffff !important;
    padding-top: 6px !important;
    padding-bottom: 6px !important;
    padding-left: 10px !important;
    padding-right: 10px !important;
    line-height: 1.3 !important;
}
div[data-testid="stExpander"] summary:hover {
    background-color: #f8fafc !important;
}
div[data-testid="stExpander"] summary p {
    font-size: 13px !important;
    color: #0f172a !important;
    margin: 0 !important;
    line-height: 1.32 !important;
}
.info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px 10px;
    font-size: 12.5px;
    margin-top: 6px;
    margin-bottom: 8px;
    padding: 8px;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
.info-item-label {
    font-size: 10.5px;
    color: #64748b;
    display: block;
}
.info-item-val {
    font-weight: 600;
    color: #0f172a;
}
.urun-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 4px;
    font-size: 12.5px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}
.urun-table th {
    background-color: #1e293b;
    color: #f8fafc;
    text-align: left;
    padding: 6px 8px;
    font-weight: 600;
    font-size: 11.5px;
}
.urun-table td {
    padding: 6px 8px;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
}
.urun-table tr:nth-child(even) td {
    background-color: #f8fafc;
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
/* Empty State & Sayfalama Stilleri */
.empty-state-box {
    background-color: #ffffff;
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    padding: 28px 16px;
    text-align: center;
    margin-top: 8px;
    margin-bottom: 10px;
}
.empty-state-icon {
    font-size: 32px;
    margin-bottom: 6px;
}
.empty-state-title {
    font-size: 14.5px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 4px;
}
.empty-state-desc {
    font-size: 12.5px;
    color: #64748b;
}
.pagination-box {
    margin-top: 12px;
    margin-bottom: 6px;
    text-align: center;
}
.pagination-text {
    font-size: 11.5px;
    color: #64748b;
    margin-bottom: 5px;
    font-weight: 500;
}
.progress-track {
    width: 100%;
    max-width: 240px;
    height: 5px;
    background-color: #e2e8f0;
    border-radius: 999px;
    margin: 0 auto 8px auto;
    overflow: hidden;
}
.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #0f172a 0%, #f97316 100%);
    border-radius: 999px;
    transition: width 0.25s ease;
}
</style>
""", unsafe_allow_html=True)

def md_temizle(metin):
    """Expander başlığında Markdown karakterlerinin biçim bozmasını önler."""
    return str(metin or "-").replace("*", "").replace("_", " ").replace("`", "").strip()

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
            st.query_params.pop("token", None)

    url_musteri = st.query_params.get("musteri", "")
    url_veren = st.query_params.get("veren", "")

    if not st.session_state.authenticated:
        st.markdown('<div class="header-banner"><div class="header-info"><div class="header-title">🏗️ SAYAR YAPI</div><div class="header-sub">Sipariş Takip ve İzleme Sistemi</div></div></div>', unsafe_allow_html=True)

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
if "arama_metni" not in st.session_state:
    st.session_state.arama_metni = ""

def filtreleri_sifirla():
    st.session_state.kpi_mod = "TUMU"
    st.session_state.arama_metni = ""
    st.session_state.f_op = "[TÜMÜ]"
    st.session_state.f_firma = "[TÜMÜ]"
    st.session_state.f_musteri = "[TÜMÜ]"
    st.session_state.f_gizle_muh = False
    st.session_state.f_gizle_ipt = False
    st.session_state.sayfa_limiti = 50

# URL Üzerinden Tekil Filtre Kaldırma (Öneri 3 - Chip Kapatma)
if "drop_filter" in st.query_params:
    df_hedef = st.query_params.get("drop_filter", "")
    if df_hedef == "op":
        st.session_state.f_op = "[TÜMÜ]"
        if st.session_state.kpi_mod == "ONAY":
            st.session_state.kpi_mod = "TUMU"
    elif df_hedef == "firma":
        st.session_state.f_firma = "[TÜMÜ]"
    elif df_hedef == "musteri":
        st.session_state.f_musteri = "[TÜMÜ]"
    elif df_hedef == "gizle_muh":
        st.session_state.f_gizle_muh = False
        if st.session_state.kpi_mod == "SEVK":
            st.session_state.kpi_mod = "TUMU"
    elif df_hedef == "gizle_ipt":
        st.session_state.f_gizle_ipt = False
        if st.session_state.kpi_mod == "SEVK":
            st.session_state.kpi_mod = "TUMU"
    elif df_hedef == "arama":
        st.session_state.arama_metni = ""
    elif df_hedef == "all":
        filtreleri_sifirla()
    st.session_state.sayfa_limiti = 50
    st.query_params.pop("drop_filter", None)
    st.rerun()

if st.query_params.get("action") == "refresh":
    st.cache_data.clear()
    st.session_state.sayfa_limiti = 50
    st.query_params.pop("action", None)
    st.rerun()

if "kpi" in st.query_params:
    secilen_kpi = st.query_params.get("kpi", "").upper()
    if secilen_kpi in ("TUMU", "ONAY", "SEVK"):
        if st.session_state.kpi_mod == secilen_kpi and secilen_kpi != "SEVK":
            st.session_state.kpi_mod = "SEVK"
        else:
            st.session_state.kpi_mod = secilen_kpi
        st.session_state.f_op = "ONAY BEKLİYOR" if st.session_state.kpi_mod == "ONAY" else "[TÜMÜ]"
        st.session_state.f_gizle_muh = (st.session_state.kpi_mod == "SEVK")
        st.session_state.f_gizle_ipt = (st.session_state.kpi_mod == "SEVK")
        st.session_state.sayfa_limiti = 50
    st.query_params.pop("kpi", None)
    st.rerun()

yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger
aktif_token = st.session_state.get("active_token") or st.query_params.get("token", "")
token_param = f"&token={aktif_token}" if aktif_token else ""

# 2. Google Drive'dan Şifreli DB İndirme ve RAM'de Çözme
@st.cache_data(ttl=30)
def verileri_getir():
    file_id = st.secrets["GDRIVE_FILE_ID"]
    secret_key = st.secrets["DB_SECRET_KEY"].encode("utf-8")

    download_url = f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
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

        # Türkiye saati (UTC+3) ile verinin çekildiği anı damgala
        tr_saati = datetime.now(timezone(timedelta(hours=3))).strftime("%H:%M")
        return df_siparisler, df_kalemler, tr_saati
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

try:
    df_sip, df_kalem, son_guncelleme = verileri_getir()
except Exception as e:
    st.error(f"Veritabanı okunamadı. Bağlantıyı ve anahtarı kontrol edin.\nDetay: {e}")
    st.stop()

# Renk Kodlu Üst Başlık Şeridi + Canlılık İndikatörü (Öneri 5)
if yetki_tipi == "MUSTERI":
    baslik_metni = f"🏗️ SAYAR YAPI | {html.escape(str(yetki_deger))}"
    alt_metin = "Müşteri Sipariş İzleme Paneli"
elif yetki_tipi == "SIPARIS_VEREN":
    baslik_metni = f"🏗️ SAYAR YAPI | {html.escape(str(yetki_deger))}"
    alt_metin = "Personel Sipariş İzleme Paneli"
else:
    baslik_metni = "🏗️ SAYAR YAPI | Sipariş İzleme"
    alt_metin = "Yönetici Canlı Takip Paneli"

refresh_href = f"?action=refresh{token_param}"

st.markdown(
    f'<div class="header-banner">'
    f'<div class="header-info">'
    f'<div class="header-title">{baslik_metni}</div>'
    f'<div class="header-sub">'
    f'<span>{alt_metin}</span>'
    f'<span class="live-badge" title="Veriler her 30 saniyede bir güncellenir"><span class="live-dot"></span>Güncel • {son_guncelleme}</span>'
    f'</div>'
    f'</div>'
    f'<div class="header-actions">'
    f'<a href="{refresh_href}" target="_self" class="icon-btn" title="Yenile">🔄</a>'
    f'<a href="?action=logout" target="_self" class="icon-btn" title="Çıkış">🚪</a>'
    f'</div></div>',
    unsafe_allow_html=True
)

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

st.markdown(
    f'<div class="kpi-grid">'
    f'<a href="?kpi=TUMU{token_param}" target="_self" class="kpi-card kpi-blue {cls_tumu}" title="Tüm siparişleri göster">'
    f'<div class="kpi-label">Toplam Sipariş</div><div class="kpi-value">{toplam_siparis}</div></a>'
    f'<a href="?kpi=ONAY{token_param}" target="_self" class="kpi-card kpi-orange {cls_onay}" title="Sadece onay bekleyenleri göster">'
    f'<div class="kpi-label">Onay Bekleyen</div><div class="kpi-value">{onay_bekleyen}</div></a>'
    f'<a href="?kpi=SEVK{token_param}" target="_self" class="kpi-card kpi-green {cls_sevk}" title="Sadece sevk bekleyenleri göster">'
    f'<div class="kpi-label">Sevk Bekleyen</div><div class="kpi-value">{sevk_bekleyen}</div></a>'
    f'</div>',
    unsafe_allow_html=True
)

# 4. Hızlı Arama + Yüzen Popover Filtre Menüsü
op_listesi = ["[TÜMÜ]"] + sorted(df_sip["operasyon"].dropna().unique().tolist())
firma_listesi = ["[TÜMÜ]"] + sorted(df_sip["firma"].dropna().unique().tolist())
musteri_listesi = ["[TÜMÜ]"] + sorted(df_sip["musteri"].dropna().unique().tolist())

if "f_op" not in st.session_state:
    st.session_state.f_op = "ONAY BEKLİYOR" if kpi_mod == "ONAY" else "[TÜMÜ]"
if st.session_state.f_op not in op_listesi:
    st.session_state.f_op = "[TÜMÜ]"
if "f_firma" not in st.session_state or st.session_state.f_firma not in firma_listesi:
    st.session_state.f_firma = "[TÜMÜ]"
if "f_musteri" not in st.session_state or st.session_state.f_musteri not in musteri_listesi:
    st.session_state.f_musteri = "[TÜMÜ]"
if "f_gizle_muh" not in st.session_state:
    st.session_state.f_gizle_muh = (kpi_mod == "SEVK")
if "f_gizle_ipt" not in st.session_state:
    st.session_state.f_gizle_ipt = (kpi_mod == "SEVK")

ek_filtre_aktif = (
    st.session_state.f_op != "[TÜMÜ]" or
    st.session_state.f_firma != "[TÜMÜ]" or
    st.session_state.f_musteri != "[TÜMÜ]" or
    st.session_state.f_gizle_muh or
    st.session_state.f_gizle_ipt
)
popover_etiket = "⚙️ •" if ek_filtre_aktif else "⚙️"

col_arama, col_filtre = st.columns([5, 1])
with col_arama:
    arama = st.text_input(
        "Arama",
        key="arama_metni",
        placeholder="🔍 Sipariş no, müşteri, firma, ürün ara...",
        label_visibility="collapsed"
    )

with col_filtre:
    with st.popover(popover_etiket, use_container_width=True):
        st.selectbox("Operasyon Durumu", op_listesi, key="f_op")
        st.selectbox("Tedarikçi / Firma", firma_listesi, key="f_firma")
        if yetki_tipi != "MUSTERI":
            st.selectbox("Müşteri", musteri_listesi, key="f_musteri")
        st.checkbox("Muhasebeye İletilenleri Gizle", key="f_gizle_muh")
        st.checkbox("İptal Edilenleri Gizle", key="f_gizle_ipt")
        st.button("Filtreleri Sıfırla", on_click=filtreleri_sifirla, use_container_width=True)

# 4.1. Aktif Filtre Etiketleri / Chips (Öneri 3)
aktif_chipler = []
if st.session_state.f_op != "[TÜMÜ]":
    aktif_chipler.append(("op", f"Durum: {st.session_state.f_op}"))
if st.session_state.f_firma != "[TÜMÜ]":
    aktif_chipler.append(("firma", f"Firma: {st.session_state.f_firma}"))
if yetki_tipi != "MUSTERI" and st.session_state.f_musteri != "[TÜMÜ]":
    aktif_chipler.append(("musteri", f"Müşteri: {st.session_state.f_musteri}"))
if st.session_state.f_gizle_muh:
    aktif_chipler.append(("gizle_muh", "Muhasebe Gizli"))
if st.session_state.f_gizle_ipt:
    aktif_chipler.append(("gizle_ipt", "İptaller Gizli"))
if arama and arama.strip():
    aktif_chipler.append(("arama", f'Arama: "{arama.strip()}"'))

if aktif_chipler:
    chip_html_parcalari = ['<div class="chip-bar">']
    for c_key, c_label in aktif_chipler:
        chip_html_parcalari.append(
            f'<a href="?drop_filter={c_key}{token_param}" target="_self" class="filter-chip" title="Bu filtreyi kaldır">'
            f'{html.escape(c_label)} ✕</a>'
        )
    if len(aktif_chipler) > 1:
        chip_html_parcalari.append(
            f'<a href="?drop_filter=all{token_param}" target="_self" class="filter-chip filter-chip-clear" title="Tüm filtreleri temizle">'
            f'Tümünü Temizle</a>'
        )
    chip_html_parcalari.append('</div>')
    st.markdown("".join(chip_html_parcalari), unsafe_allow_html=True)

# 5. Verileri Filtreleme
df_filtre = df_sip.copy()

if st.session_state.f_op != "[TÜMÜ]":
    df_filtre = df_filtre[df_filtre["operasyon"] == st.session_state.f_op]

if st.session_state.f_firma != "[TÜMÜ]":
    df_filtre = df_filtre[df_filtre["firma"] == st.session_state.f_firma]

if yetki_tipi != "MUSTERI" and st.session_state.f_musteri != "[TÜMÜ]":
    df_filtre = df_filtre[df_filtre["musteri"] == st.session_state.f_musteri]

if st.session_state.f_gizle_muh:
    df_filtre = df_filtre[df_filtre["operasyon"] != "MUHASEBEYE İLETİLDİ"]

if st.session_state.f_gizle_ipt:
    df_filtre = df_filtre[
        (df_filtre["operasyon"] != "İPTAL EDİLDİ") &
        (df_filtre["durum"] != "İptal")
    ]

if arama and arama.strip():
    q = arama.strip().lower()
    urun_eslesen_nolar = set(
        df_kalem[
            df_kalem["urun_adi"].fillna("").str.lower().str.contains(q, regex=False)
        ]["siparis_no"].tolist()
    )
    maske = (
        df_filtre["siparis_no"].astype(str).str.lower().str.contains(q, regex=False) |
        df_filtre["musteri"].fillna("").str.lower().str.contains(q, regex=False) |
        df_filtre["firma"].fillna("").str.lower().str.contains(q, regex=False) |
        df_filtre["siparis_veren"].fillna("").str.lower().str.contains(q, regex=False) |
        df_filtre["aciklama"].fillna("").str.lower().str.contains(q, regex=False) |
        df_filtre["siparis_no"].isin(urun_eslesen_nolar)
    )
    df_filtre = df_filtre[maske]

# 6. Sipariş Kartlarını Listeleme ve Empty State
toplam_bulunan = len(df_filtre)

if toplam_bulunan == 0:
    st.markdown(
        '<div class="empty-state-box">'
        '<div class="empty-state-icon">📭</div>'
        '<div class="empty-state-title">Kayıt Bulunamadı</div>'
        '<div class="empty-state-desc">Seçili filtrelere veya arama kriterine uygun sipariş yok.</div>'
        '</div>',
        unsafe_allow_html=True
    )
else:
    gosterilecek_df = df_filtre.head(st.session_state.sayfa_limiti)

    def durum_bilgisi(op_metni, durum_metni):
        op = str(op_metni or "").upper()
        drm = str(durum_metni or "").upper()
        if "İPTAL" in op or "İPTAL" in drm:
            return "#ef4444", "🔴", "status-flag-red"
        if "ONAY BEKLİYOR" in op:
            return "#f97316", "🟠", "status-flag-orange"
        if "MUHASEBE" in op or "TESLİM" in op:
            return "#16a34a", "🟢", "status-flag-green"
        return "#0284c7", "🔵", "status-flag-blue"

    for _, row in gosterilecek_df.iterrows():
        sip_no = row.get("siparis_no", "-")
        musteri = md_temizle(row.get("musteri"))
        firma = md_temizle(row.get("firma"))
        operasyon = md_temizle(row.get("operasyon"))
        tarih = md_temizle(row.get("tarih"))
        veren = md_temizle(row.get("siparis_veren"))
        durum = md_temizle(row.get("durum"))
        aciklama = html.escape(str(row.get("aciklama") or "-"))

        renk, ikon, flag_cls = durum_bilgisi(operasyon, durum)
        baslik = f"{ikon} #{sip_no} | {musteri} — {firma} ({operasyon})"

        with st.expander(baslik, expanded=False):
            # Gizli flag span'i (CSS :has() ile expander sol kenar rengini boyar - Öneri 2)
            st.markdown(
                f'<span class="{flag_cls}" style="display:none;"></span>'
                f'<div class="info-grid">'
                f'<div><span class="info-item-label">Operasyon</span><span class="badge" style="background-color:{renk};">{html.escape(operasyon)}</span></div>'
                f'<div><span class="info-item-label">Tarih</span><span class="info-item-val">{html.escape(tarih)}</span></div>'
                f'<div><span class="info-item-label">Müşteri</span><span class="info-item-val">{html.escape(musteri)}</span></div>'
                f'<div><span class="info-item-label">Tedarikçi Firma</span><span class="info-item-val">{html.escape(firma)}</span></div>'
                f'<div><span class="info-item-label">Sipariş Veren</span><span class="info-item-val">{html.escape(veren)}</span></div>'
                f'<div><span class="info-item-label">Genel Durum</span><span class="info-item-val">{html.escape(durum)}</span></div>'
                f'<div style="grid-column: span 2;"><span class="info-item-label">Açıklama / Not</span><span class="info-item-val">{aciklama}</span></div>'
                f'</div>',
                unsafe_allow_html=True
            )

            kalemler = df_kalem[df_kalem["siparis_no"] == sip_no]
            if not kalemler.empty:
                satirlar_html = ""
                for _, k in kalemler.iterrows():
                    u_adi = html.escape(str(k.get("urun_adi") or "-"))
                    miktar = html.escape(str(k.get("miktar") or ""))
                    birim = html.escape(str(k.get("birim") or ""))
                    satirlar_html += f"<tr><td>{u_adi}</td><td class='urun-miktar'>{miktar} {birim}</td></tr>"

                st.markdown(
                    f'<table class="urun-table">'
                    f'<thead><tr><th>Ürün / Malzeme</th><th style="text-align:right;">Miktar</th></tr></thead>'
                    f'<tbody>{satirlar_html}</tbody>'
                    f'</table>',
                    unsafe_allow_html=True
                )

    # 7. Sayfalama ve İlerleme Çubuğu
    gosterilen_sayi = len(gosterilecek_df)
    yuzde = min(100, int((gosterilen_sayi / toplam_bulunan) * 100))

    st.markdown(
        f'<div class="pagination-box">'
        f'<div class="pagination-text">{toplam_bulunan} siparişten {gosterilen_sayi} tanesi gösteriliyor</div>'
        f'<div class="progress-track"><div class="progress-fill" style="width: {yuzde}%;"></div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if gosterilen_sayi < toplam_bulunan:
        if st.button("Daha Fazla Göster (+50)", use_container_width=True):
            st.session_state.sayfa_limiti += 50
            st.rerun()
