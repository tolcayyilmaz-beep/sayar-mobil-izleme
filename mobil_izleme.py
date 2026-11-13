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

# Koyu Tema ve Kart Stilleri
st.markdown("""
    <style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
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

# 1. Güvenlik / PIN Kontrolü
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🏗️ SAYAR YAPI")
        st.subheader("Mobil Sipariş İzleme Girişi")
        pin = st.text_input("Erişim Şifresi / PIN:", type="password")
        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            if pin == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Hatalı erişim şifresi!")
        st.stop()

check_password()

# 2. Google Drive'dan Şifreli DB İndirme ve RAM'de Çözme
@st.cache_data(ttl=30)  # 30 saniyede bir önbelleği tazeler
def verileri_getir():
    file_id = st.secrets["GDRIVE_FILE_ID"]
    secret_key = st.secrets["DB_SECRET_KEY"].encode("utf-8")

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(download_url, timeout=15)
    response.raise_for_status()

    fernet = Fernet(secret_key)
    decrypted_bytes = fernet.decrypt(response.content)

    # Geçici dosya üzerinden SQLite okuma ve anında silme
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

# Üst Başlık ve Yenileme Butonu
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.markdown("### 🏗️ SAYAR YAPI | Sipariş İzleme")
with col_btn:
    if st.button("🔄 Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    df_sip, df_kalem = verileri_getir()
except Exception as e:
    st.error(f"Veritabanı okunamadı. Bağlantıyı ve anahtarı kontrol edin.\nDetay: {e}")
    st.stop()

# 3. Özet KPI Kartları
k1, k2, k3 = st.columns(3)
k1.metric("Toplam Sipariş", len(df_sip))
k2.metric("Onay Bekleyen", len(df_sip[df_sip["operasyon"] == "ONAY BEKLİYOR"]))
k3.metric("Onaylandı", len(df_sip[df_sip["operasyon"] == "ONAYLANDI"]))

st.divider()

# 4. Mobil Filtre Alanı
arama = st.text_input("🔍 Ara (Sipariş No, Firma, Müşteri, Şantiye, Plaka)...", "")

f_col1, f_col2 = st.columns(2)
with f_col1:
    op_listesi = ["[TÜMÜ]"] + sorted(df_sip["operasyon"].dropna().unique().tolist())
    secili_op = st.selectbox("Operasyon", op_listesi)
with f_col2:
    firma_listesi = ["[TÜMÜ]"] + sorted(df_sip["firma"].dropna().unique().tolist())
    secili_firma = st.selectbox("Firma", firma_listesi)

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

# Renk Haritası
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
            st.markdown(f"**Fabrika:** {row['fabrika'] or '-'}")
            st.markdown(f"**Nakliye:** {row['nakliye'] or '-'}")
            st.markdown(f"**Araç:** {row['arac'] or '-'}")
            st.markdown(f"**Plaka:** `{row['plaka'] or '-'}`")
        with c2:
            st.markdown(f"**Sevk Tarihi:** {row['sevk_tarihi'] or '-'}")
            st.markdown(f"**Ted. Sip. No:** {row['ted_sip_no'] or '-'}")
            st.markdown(f"**Sipariş Veren:** {row['siparis_veren'] or '-'}")
            st.markdown(f"**Yetkili / Tel:** {row['yetkili'] or '-'} {row['telefon'] or ''}")

        if row["notlar"]:
            st.info(f"📝 **Not:** {row['notlar']}")

        # Sipariş Ürün Kalemleri
        urunler = df_kalem[df_kalem["siparis_no"] == sip_no][["urun", "birim", "miktar"]]
        if not urunler.empty:
            urunler.columns = ["Ürün", "Birim", "Miktar"]
            st.dataframe(urunler, use_container_width=True, hide_index=True)
        else:
            st.caption("Bu siparişe ait ürün kalemi bulunmuyor.")