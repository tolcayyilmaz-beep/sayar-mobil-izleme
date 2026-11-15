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

# Özel CSS: Kurumsal Çelik & Beton (Sıkılaştırılmış Kompakt Aydınlık Tema)
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
    margin-top: 1px;
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
    margin-top: 10px;
    margin-bottom: 10px;
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
    margin-top: 12px !important; /*
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
/* Sipariş Kartları ve Çekmeceler: Kompakt Beyaz Zemin + Çelik Çerçeve */
div[data-testid="stExpander"] {
    background-color: #ffffff !important;
    border-radius: 9px !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
    margin-bottom: 3px !important;
    overflow: hidden;
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
        # KPI değiştiğinde ilgili widget state'lerini de senkronize et
        st.session_state.f_op = "ONAY BEKLİYOR" if st.session_state.kpi_mod == "ONAY" else "[TÜMÜ]"
        st.session_state.f_gizle_muh = (st.session_state.kpi_mod == "SEVK")
        st.session_state.f_gizle_ipt = (st.session_state.kpi_mod == "SEVK")
        st.session_state.sayfa_limiti = 50
    st.query_params.pop("kpi", None)
    st.rerun()

yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger
aktif_token = st.session_state.get("active_token") or st.query_params.get("token", "")

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
        return df_siparisler, df_kalemler
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# Renk Kodlu Üst Başlık Şeridi
if yetki_tipi == "MUSTERI":
    baslik_metni = f"🏗️ SAYAR YAPI | {html.escape(str(yetki_deger))}"
    alt_metin = "Müşteri Sipariş İzleme Paneli"
elif yetki_tipi == "SIPARIS_VEREN":
    baslik_metni = f"🏗️ SAYAR YAPI | {html.escape(str(yetki_deger))}"
    alt_metin = "Personel Sipariş İzleme Paneli"
else:
    baslik_metni = "🏗️ SAYAR YAPI | Sipariş İzleme"
    alt_metin = "Yönetici Canlı Takip Paneli"

token_param = f"&token={aktif_token}" if aktif_token else ""
refresh_href = f"?action=refresh{token_param}"

st.markdown(
    f'<div class="header-banner">'
    f'<div class="header-info"><div class="header-title">{baslik_metni}</div><div class="header-sub">{alt_metin}</div></div>'
    f'<div class="header-actions">'
    f'<a href="{refresh_href}" target="_self" class="icon-btn" title="Yenile">🔄</a>'
    f'<a href="?action=logout" target="_self" class="icon-btn" title="Çıkış">🚪</a>'
    f'</div></div>',
    unsafe_allow_html=True
)

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

# 4. Hızlı Arama + Yüzen Popover Filtre Menüsü (Madde 3)
op_listesi = ["[TÜMÜ]"] + sorted(df_sip["operasyon"].dropna().unique().tolist())
firma_listesi = ["[TÜMÜ]"] + sorted(df_sip["firma"].dropna().unique().tolist())
musteri_listesi = ["[TÜMÜ]"] + sorted(df_sip["musteri"].dropna().unique().tolist())

# Varsayılan state değerlerini ilk açılışta ata
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

# Aktif ek filtre var mı kontrolü (Butonda turuncu nokta göstermek için)
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
        placeholder="🔍 Sipariş No, Firma, Müşteri, Şantiye...",
        label_visibility="collapsed"
    )

with col_filtre:
    with st.popover(popover_etiket, use_container_width=True):
        st.markdown("**Detaylı Filtreleme**")
        secili_op = st.selectbox("Operasyon", op_listesi, key="f_op")
        secili_firma = st.selectbox("Tedarikçi Firma", firma_listesi, key="f_firma")

        if yetki_tipi != "MUSTERI":
            secili_musteri = st.selectbox("Müşteri", musteri_listesi, key="f_musteri")
        else:
            secili_musteri = "[TÜMÜ]"

        gizle_muhasebe = st.checkbox("Muhasebeye İletilenleri Gizle", key="f_gizle_muh")
        gizle_iptal = st.checkbox("İptal Edilenleri Gizle", key="f_gizle_ipt")

        if ek_filtre_aktif or arama.strip():
            st.button("Filtreleri Sıfırla", on_click=filtreleri_sifirla, use_container_width=True)

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

toplam_filtrelenen = len(filtered)
gosterilen_limit = st.session_state.sayfa_limiti
gosterilen_adet = min(toplam_filtrelenen, gosterilen_limit)

# 5. Boş Durum (Empty State) Kontrolü (Madde 6)
if toplam_filtrelenen == 0:
    st.markdown(
        '<div class="empty-state-box">'
        '<div class="empty-state-icon">🔍</div>'
        '<div class="empty-state-title">Eşleşen Sipariş Bulunamadı</div>'
        '<div class="empty-state-desc">Arama kriterlerinizi değiştirerek veya aktif filtreleri temizleyerek tekrar deneyebilirsiniz.</div>'
        '</div>',
        unsafe_allow_html=True
    )
    col_e1, col_e2, col_e3 = st.columns([1, 2, 1])
    with col_e2:
        st.button("🔄 Tüm Filtreleri Temizle", on_click=filtreleri_sifirla, use_container_width=True, type="primary")
else:
    st.caption(f"Gösterilen sipariş sayısı: **{gosterilen_adet} / {toplam_filtrelenen}**")

    OP_RENK = {
        "İŞLENDİ": "#0284c7",
        "ONAY BEKLİYOR": "#f97316",
        "ONAYLANDI": "#16a34a",
        "MUHASEBEYE İLETİLDİ": "#475569",
        "İPTAL EDİLDİ": "#dc2626",
        "KISMİ EVRAK": "#7c3aed"
    }

    OP_IKON = {
        "İŞLENDİ": "🔵",
        "ONAY BEKLİYOR": "🟠",
        "ONAYLANDI": "🟢",
        "MUHASEBEYE İLETİLDİ": "✔️",
        "İPTAL EDİLDİ": "🔴",
        "KISMİ EVRAK": "🟣"
    }

    # N+1 Optimizasyonu
    kalem_gruplari = dict(tuple(df_kalem.groupby("siparis_no"))) if not df_kalem.empty else {}

    # 6. Odaklı ve Sıkılaştırılmış 2 Satırlı Mobil Sipariş Kartları
    for _, row in filtered.head(gosterilen_limit).iterrows():
        sip_no = row.get("siparis_no", "-")
        op_val = str(row.get("operasyon") or "-")
        op_upper = op_val.upper()
        renk = OP_RENK.get(op_upper, "#475569")
        durum_ikon = OP_IKON.get(op_upper, "⚪")

        firma_str = row.get("firma") or "-"
        musteri_str = row.get("musteri") or "-"
        santiye_str = row.get("santiye") or "-"
        tarih_str = row.get("tarih") or "-"

        f_md = md_temizle(firma_str)
        m_md = md_temizle(musteri_str)
        s_md = md_temizle(santiye_str)
        t_md = md_temizle(tarih_str)

        if yetki_tipi == "MUSTERI":
            baslik = (
                f"{durum_ikon} **#{sip_no} | {f_md}**  \n"
                f"📍 {s_md} \u00A0 • \u00A0  {t_md}"
            )
        else:
            baslik = (
                f"{durum_ikon} **#{sip_no} | {f_md} ➔ {m_md}**  \n"
                f"📍 {s_md} \u00A0 • \u00A0  {t_md}"
            )

        with st.expander(baslik):
            st.markdown(
                f"<span class='badge' style='background-color:{renk};'>{html.escape(op_val)}</span> &nbsp; "
                f"**Durum:** {html.escape(str(row.get('durum') or '-'))}",
                unsafe_allow_html=True
            )

            musteri_blok = "" if yetki_tipi == "MUSTERI" else (
                f'<div><span class="info-item-label">Müşteri</span><span class="info-item-val">{html.escape(str(musteri_str))}</span></div>'
            )

            st.markdown(
                f'<div class="info-grid">'
                f'<div><span class="info-item-label">Tedarikçi Firma</span><span class="info-item-val">{html.escape(str(firma_str))}</span></div>'
                f'{musteri_blok}'
                f'<div><span class="info-item-label">Şantiye</span><span class="info-item-val">{html.escape(str(santiye_str))}</span></div>'
                f'<div><span class="info-item-label">Sipariş Tarihi</span><span class="info-item-val">{html.escape(str(tarih_str))}</span></div>'
                f'<div><span class="info-item-label">Sipariş Veren</span><span class="info-item-val">{html.escape(str(row.get("siparis_veren") or "-"))}</span></div>'
                f'</div>',
                unsafe_allow_html=True
            )

            # Sipariş Kalemleri Tablosu
            kalemler = kalem_gruplari.get(sip_no)
            if kalemler is not None and not kalemler.empty:
                satirlar_html = ""
                for _, k_row in kalemler.iterrows():
                    urun_adi = html.escape(str(k_row.get("urun_adi") or k_row.get("malzeme") or "-"))
                    miktar = html.escape(str(k_row.get("miktar") or "-"))
                    birim = html.escape(str(k_row.get("birim") or ""))
                    satirlar_html += f"<tr><td>{urun_adi}</td><td class='urun-miktar'>{miktar} {birim}</td></tr>"

                st.markdown(
                    f"<table class='urun-table'>"
                    f"<thead><tr><th>Malzeme / Ürün</th><th style='text-align:right;'>Miktar</th></tr></thead>"
                    f"<tbody>{satirlar_html}</tbody>"
                    f"</table>",
                    unsafe_allow_html=True
                )

    # 7. İlerleme Çubuğu ve "Daha Fazla Göster" Sayfalama (Madde 6)
    yuzde = int((gosterilen_adet / toplam_filtrelenen) * 100) if toplam_filtrelenen > 0 else 100
    st.markdown(
        f'<div class="pagination-box">'
        f'<div class="pagination-text">{toplam_filtrelenen} siparişten {gosterilen_adet} tanesi gösteriliyor</div>'
        f'<div class="progress-track"><div class="progress-fill" style="width:{yuzde}%;"></div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if gosterilen_adet < toplam_filtrelenen:
        kalan = toplam_filtrelenen - gosterilen_adet
        eklenecek = min(50, kalan)
        if st.button(f"Daha Fazla Göster (+{eklenecek})", use_container_width=True):
            st.session_state.sayfa_limiti += 50
            st.rerun()
