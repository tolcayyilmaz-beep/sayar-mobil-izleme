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

# Üstteki Fork/GitHub menüsünü ve alttaki Streamlit simgelerini gizleyen özel CSS
st.markdown("""
    <style>
    /* Üstteki Fork, GitHub ve Menü çubuğunu gizle */
    header[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
    }
    [data-testid="stToolbar"] {
        display: none !important;
    }
    [data-testid="stDecoration"] {
        display: none !important;
    }
    /* Sağ alttaki Streamlit Cloud rozetini ve footer'ı gizle */
    footer {
        display: none !important;
        visibility: hidden !important;
    }
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    .viewerBadge_container__r5tak,
    .viewerBadge_link__qRIco,
    div[class^="viewerBadge_"] {
        display: none !important;
    }
    /* Üst ve alt boşluğu daralt */
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 1.5rem !important;
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
        st.title("🏗️ SAYAR YAPI")
        if url_musteri:
            st.subheader(f"Müşteri Sipariş Takip ({url_musteri})")
        elif url_veren:
            st.subheader(f"Personel Sipariş Takip ({url_veren})")
        else:
            st.subheader("Sipariş İzleme Girişi")

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

# Üst Başlık ve Yenileme / Çıkış Butonları
col_title, col_btn1, col_btn2 = st.columns([3, 1, 1])
with col_title:
    if yetki_tipi in ("MUSTERI", "SIPARIS_VEREN"):
        st.markdown(f"### 🏗️ SAYAR YAPI | {yetki_deger}")
    else:
        st.markdown("### 🏗️ SAYAR YAPI | Sipariş İzleme")
with col_btn1:
    if st.button("🔄 Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_btn2:
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

# 3. Özet KPI Kartları (Toplam - Muhasebeye İletildi - İptal Edildi = Sevk Bekleyen)
toplam_siparis = len(df_sip)
onay_bekleyen = len(df_sip[df_sip["operasyon"] == "ONAY BEKLİYOR"])
sevk_bekleyen = len(
    df_sip[
        (df_sip["operasyon"] != "MUHASEBEYE İLETİLDİ") &
        (df_sip["operasyon"] != "İPTAL EDİLDİ") &
        (df_sip["durum"] != "İptal")
    ]
)

k1, k2, k3 = st.columns(3)
k1.metric("Toplam Sipariş", toplam_siparis)
k2.metric("Onay Bekleyen", onay_bekleyen)
k3.metric("Sevk Bekleyen", sevk_bekleyen)

st.divider()

# 4. Mobil Filtre Alanı
arama = st.text_input("🔍 Ara (Sipariş No, Tedarikçi, Müşteri, Şantiye, Plaka)...", "")

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

# Varsayılan olarak işaretli
gizle_muhasebe = st.checkbox("Muhasebeye İletilenleri Gizle", value=True)
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
