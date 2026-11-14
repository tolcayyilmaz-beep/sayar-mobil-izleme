import os
import json
import time
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

# Özel CSS: Streamlit barlarını gizle + İkonlu Üst Bar + Kompakt KPI Şeridi
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
    .header-banner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-left: 5px solid #007acc;
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 10px;
        color: #f8fafc;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25);
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
        border-radius: 6px;
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

APP_BASE_URL = "https://sayar-mobil-izleme-8fhaapjyqsfgku8i9kvt8f.streamlit.app"

# Şifreli Oturum Jetonu Oluşturma ve Doğrulama (URL-safe)
def token_olustur(yetki_tipi, yetki_deger, gun=180):
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

# 1. Rol, Müşteri ve Sipariş Veren Bazlı Şifre + Kalıcı URL Token Kontrolü
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.yetki_tipi = None
        st.session_state.yetki_deger = None
        st.session_state.active_token = ""

    # Çıkış aksiyonu varsa ana pencereyi temiz URL'ye yönlendir
    if st.query_params.get("action") == "logout":
        st.session_state.authenticated = False
        st.session_state.yetki_tipi = None
        st.session_state.yetki_deger = None
        st.session_state.active_token = ""
        st.markdown(f'<meta http-equiv="refresh" content="0; url={APP_BASE_URL}">', unsafe_allow_html=True)
        st.stop()

    # URL'de ?token=... varsa doğrula ve şifre sormadan içeri al
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
        beni_hatirla = st.checkbox("Beni Hatırla (Oturumu Açık Tut)", value=True)

        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            basarili_tip = None
            basarili_deger = None

            # 1) Yönetici şifresi kontrolü
            if pin == st.secrets["APP_PASSWORD"]:
                basarili_tip = "YONETICI"
                basarili_deger = None

            # 2) Müşteri şifreleri kontrolü
            if not basarili_tip and not url_veren:
                musteri_map = st.secrets.get("MUSTERI_SIFRELERI", {})
                for m_adi, m_sifre in musteri_map.items():
                    if pin == str(m_sifre):
                        if not url_musteri or url_musteri.strip().upper() == m_adi.strip().upper():
                            basarili_tip = "MUSTERI"
                            basarili_deger = m_adi
                            break

            # 3) Sipariş Veren (Personel) şifreleri kontrolü
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
                    yeni_token = token_olustur(basarili_tip, basarili_deger, gun=180)
                    st.session_state.active_token = yeni_token
                    hedef_url = f"{APP_BASE_URL}/?token={yeni_token}"
                    # Gerçek tarayıcı adres çubuğunu token'lı URL'ye yönlendir
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={hedef_url}">', unsafe_allow_html=True)
                    st.success("Giriş başarılı, yönlendiriliyorsunuz...")
                    st.stop()
                else:
                    st.session_state.active_token = ""
                    st.rerun()
            else:
                st.error("Hatalı erişim şifresi!")
        st.stop()

check_password()

# Üstbar yenileme aksiyonunu yakala
if st.query_params.get("action") == "refresh":
    st.cache_data.clear()
    del st.query_params["action"]
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

# Renk Kodlu Üst Başlık Şeridi + Sağda Sadece İkon Butonlar
if yetki_tipi == "MUSTERI":
    baslik_metni = f"🏗️ SAYAR YAPI | {yetki_deger}"
    alt_metin = "Müşteri Sipariş İzleme Paneli"
elif yetki_tipi == "SIPARIS_VEREN":
    baslik_metni = f"🏗️ SAYAR YAPI | {yetki_deger}"
    alt_metin = "Personel Sipariş İzleme Paneli"
else:
    baslik_metni = "🏗️ SAYAR YAPI | Sipariş İzleme"
    alt_metin = "Yönetici Canlı Takip Paneli"

refresh_href = f"?action=refresh&token={aktif_token}" if aktif_token else "?action=refresh"
logout_href = f"{APP_BASE_URL}/?action=logout"

st.markdown(f"""
    <div class="header-banner">
        <div class="header-info">
            <div class="header-title">{baslik_metni}</div>
            <div class="header-sub">{alt_metin}</div>
        </div>
        <div class="header-actions">
            <a href="{refresh_href}" target="_self" class="icon-btn" title="Yenile">🔄</a>
            <a href="{logout_href}" target="_top" class="icon-btn" title="Çıkış">🚪</a>
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

# 3. Kompakt Yan Yana 3'lü KPI Şeridi
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

    # Şifresiz kalıcı giriş linki (Ana ekrana eklemek için)
    if aktif_token:
        st.divider()
        st.caption("📌 **Şifresiz Hızlı Giriş Linki** (Bu linki açıp 'Ana Ekrana Ekle' yapabilirsiniz):")
        st.code(f"{APP_BASE_URL}/?token={aktif_token}", language="text")

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

st.caption(f"Gösterilen sipariş sayısı: **{len(filtered)}**")

OP_RENK = {
    "İŞLENDİ": "#007acc",
    "ONAY BEKLİYOR": "#e67e22",
    "ONAYLANDI": "#1abc9c",
    "MUHASEBEYE İLETİLDİ": "#2ecc71",
    "İPTAL EDİLDİ": "#e74c3c",
    "KISMİ EVRAK": "#8e44ad"
}

# 6. Mobil Sipariş Kartları ve Detay Açılır Panelleri
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
