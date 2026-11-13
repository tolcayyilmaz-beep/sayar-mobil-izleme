import os
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

# Özel CSS: Streamlit barlarını gizle + Kompakt KPI şeridi ve başlık kartı
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
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-left: 5px solid #007acc;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 10px;
        color: #f8fafc;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    }
    .header-title {
        font-size: 16px;
        font-weight: 700;
        margin: 0;
        color: #ffffff;
        letter-spacing: 0.3px;
    }
    .header-sub {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 2px;
    }
    /* Kompakt Yan Yana 3'lü KPI Şeridi (Mobilde Alt Alta Düşmez) */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-bottom: 10px;
    }
    .kpi-card {
        background-color: #1e1e24;
        border: 1px solid #32323a;
        border-radius: 8px;
        padding: 8px 10px;
        text-align: center;
    }
    .kpi-blue { border-top: 3px solid #007acc; }
    .kpi-orange { border-top: 3px solid #e67e22; }
    .kpi-green { border-top: 3px solid #2ecc71; }
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
    .badge {
        padding: 3px 8px;
        border-radius: 4px;
        color: white;
        font-weight: bold;
        font-size: 12px;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# 1. Rol, Müşteri ve Sipariş Veren Bazlı Şifre Kontrolü
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.yetki_tipi = None   # "YONETICI", "MUSTERI", "SIPARIS_VEREN"
        st.session_state.yetki_deger = None  # İlgili müşteri veya personel adı

    url_musteri = st.query_params.get("musteri", "")
    url_veren = st.query_params.get("veren", "")

    if not st.session_state.authenticated:
        st.markdown("""
            <div class="header-banner">
                <div class="header-title">🏗️ SAYAR YAPI</div>
                <div class="header-sub">Sipariş Takip ve İzleme Sistemi</div>
            </div>
        """, unsafe_allow_html=True)

        if url_musteri:
            st.caption(f"Müşteri Girişi: **{url_musteri}**")
        elif url_veren:
            st.caption(f"Personel Girişi: **{url_veren}**")

        pin = st.text_input("Erişim Şifresi:", type="password")
        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            # 1) Yönetici şifresi kontrolü
            if pin == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.session_state.yetki_tipi = "YONETICI"
                st.session_state.yetki_deger = None
                st.rerun()

            # 2) Müşteri şifreleri kontrolü
            if not url_veren:
                musteri_map = st.secrets.get("MUSTERI_SIFRELERI", {})
                for m_adi, m_sifre in musteri_map.items():
                    if pin == str(m_sifre):
                        if not url_musteri or url_musteri.strip().upper() == m_adi.strip().upper():
                            st.session_state.authenticated = True
                            st.session_state.yetki_tipi = "MUSTERI"
                            st.session_state.yetki_deger = m_adi
                            st.rerun()

            # 3) Sipariş Veren (Personel) şifreleri kontrolü
            if not url_musteri:
                veren_map = st.secrets.get("SIPARIS_VEREN_SIFRELERI", {})
                for v_adi, v_sifre in veren_map.items():
                    if pin == str(v_sifre):
                        if not url_veren or url_veren.strip().upper() == v_adi.strip().upper():
                            st.session_state.authenticated = True
                            st.session_state.yetki_tipi = "SIPARIS_VEREN"
                            st.session_state.yetki_deger = v_adi
                            st.rerun()

            st.error("Hatalı erişim şifresi!")
        st.stop()

check_password()

yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger

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

st.markdown(f"""
    <div class="header-banner">
        <div class="header-title">{baslik_metni}</div>
        <div class="header-sub">{alt_metin}</div>
    </div>
""", unsafe_allow_html=True)

# Yenile ve Çıkış Butonları (Kompakt Yan Yana)
b1, b2 = st.columns(2)
with b1:
    if st.button("🔄 Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with b2:
    if st.button("🚪 Çıkış", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.yetki_tipi = None
        st.session_state.yetki_deger = None
        st.rerun()

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

# 3. Kompakt Yan Yana 3'lü KPI Şeridi (Toplam - Muhasebeye İletildi - İptal Edildi = Sevk Bekleyen)
toplam_siparis = len(df_sip)
onay_bekleyen = len(df_sip[df_sip["operasyon"] == "ONAY BEKLİYOR"])
sevk_bekleyen = len(
    df_sip[
        (df_sip["operasyon"] != "MUHASEBEYE İLETİLDİ") &
        (df_sip["operasyon"] != "İPTAL EDİLDİ") &
        (df_sip["durum"] != "İptal")
    ]
)

st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card kpi-blue">
            <div class="kpi-label">Toplam Sipariş</div>
            <div class="kpi-value">{toplam_siparis}</div>
        </div>
        <div class="kpi-card kpi-orange">
            <div class="kpi-label">Onay Bekleyen</div>
            <div class="kpi-value">{onay_bekleyen}</div>
        </div>
        <div class="kpi-card kpi-green">
            <div class="kpi-label">Sevk Bekleyen</div>
            <div class="kpi-value">{sevk_bekleyen}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 4. Hızlı Arama + Tek "Filtrele" Çekmecesi
arama = st.text_input("", placeholder="🔍 Ara (Sipariş No, Tedarikçi, Müşteri, Şantiye, Plaka)...", label_visibility="collapsed")

with st.expander("⚙️ Filtrele", expanded=False):
    if yetki_tipi == "MUSTERI":
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            op_listesi = ["[TÜMÜ]"] + sorted(df_sip["operasyon"].dropna().unique().tolist())
            secili_op = st.selectbox("Operasyon", op_listesi)
        with f_col2:
            firma_listesi = ["[TÜMÜ]"] + sorted(df_sip["firma"].dropna().unique().tolist())
            secili_firma = st.selectbox("Tedarikçi Firma", firma_listesi)
        secili_musteri = "[TÜMÜ]"
    else:
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            op_listesi = ["[TÜMÜ]"] + sorted(df_sip["operasyon"].dropna().unique().tolist())
            secili_op = st.selectbox("Operasyon", op_listesi)
        with f_col2:
            firma_listesi = ["[TÜMÜ]"] + sorted(df_sip["firma"].dropna().unique().tolist())
            secili_firma = st.selectbox("Tedarikçi Firma", firma_listesi)
        with f_col3:
            musteri_listesi = ["[TÜMÜ]"] + sorted(df_sip["musteri"].dropna().unique().tolist())
            secili_musteri = st.selectbox("Müşteri", musteri_listesi)

    c_chk1, c_chk2 = st.columns(2)
    with c_chk1:
        gizle_muhasebe = st.checkbox("Muhasebeye İletilenleri Gizle", value=True)
    with c_chk2:
        gizle_iptal = st.checkbox("İptal Edilenleri Gizle", value=True)

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
        filtered["santiye"].fillna("").str.lower().str.contains(q) |
        filtered["plaka"].fillna("").str.lower().str.contains(q)
    )
    filtered = filtered[mask]

st.caption(f"Gösterilen sipariş sayısı: **{len(filtered)}**")

OP_RENK = {
    "İŞLENDİ": "#007acc",
    "ONAY BEKLİYOR": "#e67e22",
    "ONAYLANDI": "#1abc9c",
    "MUHASEBEYE İLETİLDİ": "#2ecc71",
    "İPTAL EDİLDİ": "#e74c3c",
    "KISMİ EVRAK": "#8e44ad"
}

# 5. Mobil Sipariş Kartları ve Detay Açılır Panelleri
for _, row in filtered.head(50).iterrows():
    sip_no = row["siparis_no"]
    op_val = str(row["operasyon"] or "-")
    renk = OP_RENK.get(op_val.upper(), "#555555")

    if yetki_tipi == "MUSTERI":
        baslik = f"#{sip_no} | {row['firma'] or '-'} ({row['tarih'] or '-'})"
    else:
        baslik = f"#{sip_no} | {row['firma'] or '-'} ➔ {row['musteri'] or '-'} ({row['santiye'] or '-'})"

    with st.expander(baslik):
        st.markdown(
            f"<span class='badge' style='background-color:{renk};'>{op_val}</span> &nbsp; "
            f"**Durum:** {row['durum'] or '-'} &nbsp; | &nbsp; **Tarih:** {row['tarih'] or '-'}",
            unsafe_allow_html=True
        )
        st.write("")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Tedarikçi Firma:** {row['firma'] or '-'}")
            st.markdown(f"**Şantiye:** {row['santiye'] or '-'}")
            st.markdown(f"**Fabrika:** {row['fabrika'] or '-'}")
            st.markdown(f"**Nakliye:** {row['nakliye'] or '-'}")
            st.markdown(f"**Araç:** {row['arac'] or '-'}")
            st.markdown(f"**Plaka:** `{row['plaka'] or '-'}`")
        with c2:
            st.markdown(f"**Sevk Tarihi:** {row['sevk_tarihi'] or '-'}")
            st.markdown(f"**Ted. Sip. No:** {row['ted_sip_no'] or '-'}")
            st.markdown(f"**Yetkili / Tel:** {row['yetkili'] or '-'} {row['telefon'] or ''}")
            if yetki_tipi != "MUSTERI":
                st.markdown(f"**Müşteri:** {row['musteri'] or '-'}")
                st.markdown(f"**Sipariş Veren:** {row['siparis_veren'] or '-'}")

        if row["notlar"]:
            st.info(f"📝 **Not:** {row['notlar']}")

        urunler = df_kalem[df_kalem["siparis_no"] == sip_no][["urun", "birim", "miktar"]]
        if not urunler.empty:
            urunler.columns = ["Ürün", "Birim", "Miktar"]
            st.dataframe(urunler, use_container_width=True, hide_index=True)
        else:
            st.caption("Bu siparişe ait ürün kalemi bulunmuyor.")
