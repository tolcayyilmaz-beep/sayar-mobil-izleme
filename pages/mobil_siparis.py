import os
import re
import json
import time
import hmac
import html
import base64
import hashlib
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date

# Ortam değişkeninden secrets.toml dosyasını sadece yoksa oluştur
if os.environ.get("STREAMLIT_SECRETS") and not os.path.exists(".streamlit/secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMLIT_SECRETS"])

NTFY_TOPIC = "sayar_yapi_siparis_2026"
RAILWAY_DEFAULT_DB_URL = "postgresql://postgres:vRnqPZifPAhgHJkVconMThDtIillFNFN@trolley.proxy.rlwy.net:41607/railway"


@st.cache_data(show_spinner=False)
def logo_base64_getir(dosya_yolu="logo.png"):
    """Logo dosyasını HTML img etiketi ve page_icon için Base64 formatına çevirir."""
    yol = dosya_yolu if os.path.exists(dosya_yolu) else os.path.join("static", dosya_yolu)
    if os.path.exists(yol):
        ext = os.path.splitext(yol)[1].lower()
        mime = "image/svg+xml" if ext == ".svg" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/png")
        with open(yol, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    return None


LOGO_DATA_URI = logo_base64_getir("logo.png")
LOGO_HTML = f'<img src="{LOGO_DATA_URI}" class="header-logo" alt="Logo">' if LOGO_DATA_URI else "🏗️"

st.set_page_config(
    page_title="Sayar Yapı | Mobil Sipariş",
    page_icon=LOGO_DATA_URI if LOGO_DATA_URI else "🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# iOS Ana Ekran İkonu + Tam Sayfa Yenilemesiz SPA Link Yakalayıcı
logo_hedef_url = ""
try:
    if "LOGO_URL" in st.secrets:
        logo_hedef_url = str(st.secrets["LOGO_URL"]).strip()
except Exception:
    pass

if not logo_hedef_url and LOGO_DATA_URI:
    logo_hedef_url = LOGO_DATA_URI

components.html(
    f"""
    <script>
    (function() {{
        const doc = window.parent.document;
        const win = window.parent;
        const head = doc.head || doc.getElementsByTagName('head')[0];
        const logoUrl = {json.dumps(logo_hedef_url)};
        if (head && logoUrl) {{
            doc.querySelectorAll('link[rel*="apple-touch-icon"]').forEach(el => el.remove());
            const l1 = doc.createElement('link');
            l1.rel = 'apple-touch-icon';
            l1.sizes = '180x180';
            l1.href = logoUrl;
            head.appendChild(l1);
        }}

        if (!win.__spaLinkHooked) {{
            win.__spaLinkHooked = true;
            doc.addEventListener('click', function(e) {{
                const a = e.target.closest('a[data-spa="1"]');
                if (!a) return;
                e.preventDefault();
                const href = a.getAttribute('href');
                if (!href) return;
                win.history.pushState({{}}, '', href);
                win.dispatchEvent(new PopStateEvent('popstate'));
            }}, true);
        }}
    }})();
    </script>
    """,
    height=0,
    width=0
)

# Özel CSS: Kurumsal Çelik & Beton (mobil_izleme Tasarım Dili + Sıkı Mobil Form)
st.markdown("""
<style>
*, *::before, *::after {
    box-sizing: border-box !important;
}
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
html, body, .stApp, [data-testid="stAppViewContainer"], section.main {
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
    overflow-x: hidden !important;
    max-width: 100% !important;
    width: 100% !important;
}
.block-container {
    padding-top: 0.45rem !important;
    padding-bottom: 5.2rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    max-width: 560px !important;
    width: 100% !important;
    margin: 0 auto !important;
}
[data-testid="stVerticalBlock"] {
    gap: 0.36rem !important;
    width: 100% !important;
    max-width: 100% !important;
}
[data-testid="element-container"] {
    width: 100% !important;
    max-width: 100% !important;
}
.auto-toast-banner {
    background-color: #dcfce7;
    border: 1px solid #86efac;
    border-left: 4px solid #16a34a;
    color: #14532d;
    border-radius: 9px;
    padding: 8px 12px;
    font-size: 12.5px;
    font-weight: 700;
    margin-bottom: 2px;
    opacity: 1;
    transition: opacity 0.35s ease;
    box-shadow: 0 2px 6px rgba(22, 163, 74, 0.12);
}
/* mobil_izleme Üst Kurumsal Banner */
.header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-left: 5px solid #f97316;
    border-radius: 10px;
    padding: 9px 12px;
    margin-bottom: 2px;
    color: #f8fafc;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.14);
    gap: 8px;
    width: 100%;
}
.header-info {
    flex: 1;
    min-width: 0;
}
.header-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    margin: 0;
    color: #ffffff;
    letter-spacing: 0.2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.header-title span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.header-logo {
    height: 26px;
    width: auto;
    object-fit: contain;
    border-radius: 4px;
    flex-shrink: 0;
}
.header-sub {
    font-size: 11px;
    color: #cbd5e1;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
/* mobil_izleme 3'lü KPI Özet Şeridi */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin-top: 4px;
    margin-bottom: 4px;
    width: 100%;
}
.kpi-card {
    display: block;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 9px;
    padding: 6px 8px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    min-width: 0;
}
.kpi-blue { border-top: 3px solid #0284c7 !important; }
.kpi-orange { border-top: 3px solid #f97316 !important; }
.kpi-green { border-top: 3px solid #16a34a !important; }
.kpi-label {
    font-size: 10.5px;
    color: #475569;
    font-weight: 600;
    margin-bottom: 1px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.kpi-value {
    font-size: 15px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
/* mobil_izleme fullscreen-review-card Stili Form Kartı */
.st-key-siparis-form-card {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-top: 4px solid #f97316 !important;
    border-radius: 11px !important;
    padding: 9px 10px 11px 10px !important;
    margin-top: 2px !important;
    margin-bottom: 8px !important;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.07) !important;
}
.st-key-siparis-form-card > div {
    gap: 0.36rem !important;
}
.form-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 6px;
    margin-bottom: 4px;
    gap: 8px;
}
.form-card-title {
    font-size: 13.5px;
    font-weight: 800;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.form-card-badge {
    font-size: 10.5px;
    font-weight: 700;
    color: #c2410c;
    background-color: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 6px;
    padding: 2px 7px;
    white-space: nowrap;
    flex-shrink: 0;
}
/* Yatay Sütunların Mobilde Taşmasını Önleyen Yapı */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 6px !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    min-width: 0 !important;
    padding: 0 !important;
}
/* Input & Dropdown Kontrolleri */
div[data-testid="stDateInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label {
    color: #475569 !important;
    font-size: 10.5px !important;
    font-weight: 700 !important;
    margin-bottom: 2px !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-baseweb="select"] > div {
    background-color: #f8fafc !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
    color: #0f172a !important;
    min-height: 40px !important;
    height: 40px !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    width: 100% !important;
    max-width: 100% !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03) !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stDateInput"] input:focus,
div[data-baseweb="select"] > div:focus-within {
    background-color: #ffffff !important;
    border-color: #f97316 !important;
    box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.16) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] div {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
div[data-testid="stForm"] {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    padding: 14px !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
}
/* Buton Stilleri */
div[data-testid="stButton"] button {
    min-height: 40px !important;
    height: 40px !important;
    padding: 0 8px !important;
    font-size: 12.5px !important;
    font-weight: 800 !important;
    border-radius: 9px !important;
    width: 100% !important;
    max-width: 100% !important;
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    color: #0f172a !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
}
div[data-testid="stButton"] button:hover {
    border-color: #f97316 !important;
    background-color: #fff7ed !important;
}
button[kind="primary"] {
    background-color: #f97316 !important;
    border: 1px solid #ea580c !important;
    color: #ffffff !important;
}
button[kind="primary"]:hover {
    background-color: #ea580c !important;
    color: #ffffff !important;
}
/* Ürün Kalemleri Tablosu (mobil_izleme urun-table Stili) */
.siparis-kalem-baslik {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 68px 72px;
    gap: 6px;
    background-color: #1e293b;
    color: #f8fafc;
    border-radius: 8px 8px 0 0;
    padding: 6px 9px;
    font-size: 11px;
    font-weight: 700;
    margin-top: 4px;
    width: 100%;
}
.siparis-kalem-baslik span:nth-child(2) { text-align: center; }
.siparis-kalem-baslik span:nth-child(3) { text-align: right; }
.eklenen-urun-satir {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 68px 72px;
    gap: 6px;
    align-items: center;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 3px solid #f97316;
    border-radius: 8px;
    padding: 6px 9px;
    min-height: 40px;
    width: 100%;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.eklenen-urun-ad {
    font-size: 12.5px;
    font-weight: 700;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
}
.eklenen-urun-birim {
    text-align: center;
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    background-color: #f1f5f9;
    border-radius: 5px;
    padding: 2px 4px;
    white-space: nowrap;
}
.eklenen-urun-miktar {
    font-size: 12px;
    font-weight: 800;
    color: #0f172a;
    text-align: right;
    white-space: nowrap;
}
.bos-liste-kutusu {
    background-color: #f8fafc;
    border: 1px dashed #cbd5e1;
    border-radius: 9px;
    padding: 12px 10px;
    text-align: center;
    font-size: 12px;
    color: #64748b;
    font-weight: 600;
    width: 100%;
}
/* Sabit Alt Aksiyon Barı (mobil_izleme onay-aksiyon-bar Renk Kodu) */
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: 100% !important;
    max-width: 560px !important;
    padding: 8px 0.75rem 10px 0.75rem !important;
    background: linear-gradient(180deg, rgba(241, 245, 249, 0.88) 0%, #f1f5f9 32%) !important;
    backdrop-filter: blur(6px);
    border-top: 1px solid #cbd5e1;
    z-index: 9999 !important;
    margin: 0 !important;
}
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] div[data-testid="column"]:nth-child(1) button {
    background-color: #16a34a !important;
    border: 1px solid #15803d !important;
    color: #ffffff !important;
    height: 42px !important;
    box-shadow: 0 2px 5px rgba(22, 163, 74, 0.25) !important;
}
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] div[data-testid="column"]:nth-child(1) button:hover {
    background-color: #15803d !important;
}
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] div[data-testid="column"]:nth-child(2) button {
    background-color: #facc15 !important;
    border: 1px solid #eab308 !important;
    color: #0f172a !important;
    height: 42px !important;
}
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] div[data-testid="column"]:nth-child(2) button:hover {
    background-color: #eab308 !important;
}
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] div[data-testid="column"]:nth-child(3) button {
    background-color: #dc2626 !important;
    border: 1px solid #b91c1c !important;
    color: #ffffff !important;
    height: 42px !important;
}
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] div[data-testid="column"]:nth-child(3) button:hover {
    background-color: #b91c1c !important;
}
/* Kapalı Ekran Durum Kutusu */
.empty-state-box {
    background-color: #ffffff;
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    padding: 26px 16px;
    text-align: center;
    margin-top: 8px;
    margin-bottom: 10px;
}
.empty-state-icon {
    font-size: 30px;
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
</style>
""", unsafe_allow_html=True)


def get_postgres_url() -> str:
    """Railway PostgreSQL bağlantı adresini döndürür."""
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if env_url:
        return env_url.replace("postgres://", "postgresql://", 1)

    try:
        for secret_key in ("DATABASE_URL", "POSTGRES_URL", "RAILWAY_DB_URL", "RAILWAY_DATABASE_URL"):
            if secret_key in st.secrets and str(st.secrets[secret_key]).strip():
                return str(st.secrets[secret_key]).strip().replace("postgres://", "postgresql://", 1)
    except Exception:
        pass

    return RAILWAY_DEFAULT_DB_URL


def get_pg_connection():
    """Yeni bir PostgreSQL bağlantısı açar."""
    url = get_postgres_url()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(url, connect_timeout=10)
    conn.autocommit = False
    return conn


def _imza_anahtari():
    if "DB_SECRET_KEY" in st.secrets and str(st.secrets["DB_SECRET_KEY"]).strip():
        return str(st.secrets["DB_SECRET_KEY"]).encode("utf-8")
    return str(st.secrets["APP_PASSWORD"]).encode("utf-8")


def token_olustur(yetki_tipi, yetki_deger, gun=90):
    exp = int(time.time()) + (gun * 86400)
    payload_json = json.dumps({"tip": yetki_tipi, "deger": yetki_deger, "exp": exp}, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    sig = hmac.new(_imza_anahtari(), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def token_dogrula(token_str):
    try:
        payload_b64, sig = token_str.split(".", 1)
        expected_sig = hmac.new(_imza_anahtari(), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None, None
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        if int(data.get("exp", 0)) > int(time.time()):
            return data.get("tip"), data.get("deger")
    except Exception:
        pass
    return None, None


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

    if not st.session_state.authenticated:
        url_token = st.query_params.get("token", "")
        if url_token:
            t_tip, t_deger = token_dogrula(url_token)
            if t_tip in ("YONETICI", "SIPARIS_VEREN"):
                st.session_state.authenticated = True
                st.session_state.yetki_tipi = t_tip
                st.session_state.yetki_deger = t_deger
                st.session_state.active_token = url_token
            else:
                st.query_params.pop("token", None)

    url_veren = st.query_params.get("veren", "")

    if not st.session_state.authenticated:
        st.markdown(
            f'<div class="header-banner"><div class="header-info">'
            f'<div class="header-title">{LOGO_HTML}<span>SAYAR YAPI</span></div>'
            f'<div class="header-sub">Hızlı Mobil Sipariş Girişi</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
        if url_veren:
            st.caption(f"Personel Girişi: **{url_veren}**")

        with st.form("login_form", clear_on_submit=False):
            pin = st.text_input("Erişim Şifresi:", placeholder="Erişim Şifresi...", type="password")
            beni_hatirla = st.checkbox("Beni Hatırla", value=True)
            giris_yapildi = st.form_submit_button("Giriş Yap", use_container_width=True, type="primary")

        if giris_yapildi:
            basarili_tip = None
            basarili_deger = None

            if pin == st.secrets["APP_PASSWORD"]:
                basarili_tip = "YONETICI"
                basarili_deger = None

            if not basarili_tip:
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
                st.error("Hatalı şifre veya yetkisiz giriş!")
        st.stop()


check_password()


@st.cache_data(ttl=60, show_spinner=False)
def secim_listelerini_getir():
    """PostgreSQL tanimlar ve siparisler tablolarından seçim listelerini çeker (60 sn önbellekli)."""
    varsayilan = {
        "firma": [],
        "musteri": [],
        "santiye": [],
        "sehir": [],
        "arac": [],
        "fabrika": [],
        "nakliye": [],
        "siparis_veren": [],
        "urunler_detay": [],
        "birim": ["ADET", "TON", "KG", "M2", "M3", "MT", "TORBA", "PALET", "PAKET"]
    }
    conn = None
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT kategori, deger, COALESCE(aktif, 1) AS aktif, COALESCE(firma, '') AS firma FROM tanimlar")
            tanim_rows = cur.fetchall()

            cur.execute(
                """
                SELECT DISTINCT
                    TRIM(musteri) AS musteri,
                    TRIM(santiye) AS santiye,
                    TRIM(sehir) AS sehir,
                    TRIM(firma) AS firma,
                    TRIM(arac) AS arac,
                    TRIM(fabrika) AS fabrika,
                    TRIM(nakliye) AS nakliye,
                    TRIM(siparis_veren) AS siparis_veren
                FROM siparisler
                ORDER BY musteri ASC
                LIMIT 1000
                """
            )
            sip_rows = cur.fetchall()

        def tanim_listesi(kat):
            vals = set()
            for r in tanim_rows:
                if r.get("kategori") == kat and int(r.get("aktif") if r.get("aktif") is not None else 1) == 1:
                    d = str(r.get("deger") or "").strip()
                    if d and d != "-":
                        vals.add(d)
            return sorted(vals)

        def siparis_gecmis_listesi(col):
            vals = set()
            for r in sip_rows:
                d = str(r.get(col) or "").strip()
                if d and d != "-" and d.lower() not in ("none", "nan"):
                    vals.add(d)
            return sorted(vals)

        varsayilan["firma"] = tanim_listesi("FİRMA") or siparis_gecmis_listesi("firma")
        varsayilan["arac"] = tanim_listesi("ARAÇ") or siparis_gecmis_listesi("arac")
        varsayilan["fabrika"] = tanim_listesi("FABRİKA") or siparis_gecmis_listesi("fabrika")
        varsayilan["nakliye"] = tanim_listesi("NAKLİYE") or siparis_gecmis_listesi("nakliye")
        varsayilan["siparis_veren"] = tanim_listesi("SİPARİŞ VEREN") or siparis_gecmis_listesi("siparis_veren")

        varsayilan["musteri"] = sorted(set(tanim_listesi("MÜŞTERİ") + siparis_gecmis_listesi("musteri")))
        varsayilan["santiye"] = sorted(set(tanim_listesi("ŞANTİYE") + siparis_gecmis_listesi("santiye")))
        varsayilan["sehir"] = sorted(set(tanim_listesi("ŞEHİR") + siparis_gecmis_listesi("sehir")))

        t_birim = tanim_listesi("BİRİM")
        if t_birim:
            varsayilan["birim"] = t_birim

        urun_list = []
        for r in tanim_rows:
            if r.get("kategori") == "ÜRÜN" and int(r.get("aktif") if r.get("aktif") is not None else 1) == 1:
                ad = str(r.get("deger") or "").strip()
                frm = str(r.get("firma") or "").strip()
                if ad:
                    urun_list.append({"deger": ad, "firma": frm})
        varsayilan["urunler_detay"] = sorted(urun_list, key=lambda x: x["deger"])

    except Exception:
        pass
    finally:
        if conn is not None and not conn.closed:
            try:
                conn.close()
            except Exception:
                pass

    return varsayilan


def yeni_siparis_pg_kaydet(siparis_verisi: dict) -> int:
    """Yeni siparişi ve ürün kalemlerini doğrudan PostgreSQL'e kaydeder; oluşan siparis_no değerini döndürür."""
    conn = None
    try:
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO siparisler (
                    tarih, firma, musteri, santiye, sehir, telefon, yetkili, arac, fabrika,
                    nakliye, notlar, sevk_tarihi, ted_sip_no, plaka, nakliye_fatura,
                    siparis_veren, firma_yetkili, siparis_gecen, durum, operasyon
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING siparis_no
                """,
                (
                    siparis_verisi.get("tarih", ""),
                    siparis_verisi.get("firma", ""),
                    siparis_verisi.get("musteri", ""),
                    siparis_verisi.get("santiye", ""),
                    siparis_verisi.get("sehir", "İSTANBUL"),
                    siparis_verisi.get("telefon", ""),
                    siparis_verisi.get("yetkili", ""),
                    siparis_verisi.get("arac", ""),
                    siparis_verisi.get("fabrika", ""),
                    siparis_verisi.get("nakliye", ""),
                    siparis_verisi.get("notlar", ""),
                    siparis_verisi.get("sevk_tarihi", ""),
                    siparis_verisi.get("ted_sip_no", ""),
                    siparis_verisi.get("plaka", ""),
                    siparis_verisi.get("nakliye_fatura", ""),
                    siparis_verisi.get("siparis_veren", ""),
                    siparis_verisi.get("firma_yetkili", ""),
                    siparis_verisi.get("siparis_gecen", ""),
                    siparis_verisi.get("durum", "Beklemede"),
                    siparis_verisi.get("operasyon", "ONAY BEKLİYOR"),
                )
            )
            yeni_siparis_no = int(cur.fetchone()[0])

            for kalem in siparis_verisi.get("urunler", []):
                cur.execute(
                    """
                    INSERT INTO siparis_kalemleri (siparis_no, urun, birim, miktar)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        yeni_siparis_no,
                        str(kalem.get("urun") or "").strip(),
                        str(kalem.get("birim") or "").strip(),
                        str(kalem.get("miktar") or "").strip(),
                    )
                )

        conn.commit()
        return yeni_siparis_no
    except Exception:
        if conn is not None and not conn.closed:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn is not None and not conn.closed:
            try:
                conn.close()
            except Exception:
                pass


def yeni_siparis_ntfy_gonder(sip: dict):
    try:
        urun_ozet = ", ".join([f"{u['urun']} ({u['miktar']} {u['birim']})" for u in sip.get("urunler", [])[:3]])
        if len(sip.get("urunler", [])) > 3:
            urun_ozet += f" +{len(sip['urunler']) - 3} kalem"

        sip_no_etiket = f" #{sip['siparis_no']}" if sip.get("siparis_no") else ""
        baslik = f"Yeni Mobil Siparis{sip_no_etiket} - {sip.get('musteri') or '-'}"
        mesaj = "\n".join([
            f"Firma: {sip.get('firma') or '-'}",
            f"Musteri: {sip.get('musteri') or '-'}",
            f"Santiye: {sip.get('santiye') or '-'} ({sip.get('sehir') or '-'})",
            f"Siparis Veren: {sip.get('siparis_veren') or '-'}",
            f"Urunler: {urun_ozet}"
        ])
        headers = {
            "Title": baslik.encode("utf-8").decode("latin-1", errors="ignore"),
            "Priority": "high",
            "Tags": "package"
        }
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mesaj.encode("utf-8"),
            headers=headers,
            timeout=2
        )
    except Exception:
        pass


def secim_alani(etiket: str, key: str, secenekler: list, varsayilan: str = ""):
    """Açılır liste alanı; alan adı kutunun içinde yer tutucu olarak görünür."""
    temiz = [str(x).strip() for x in secenekler if str(x).strip() and str(x).strip() != "-"]
    secenekler = list(dict.fromkeys(temiz))
    if varsayilan and varsayilan not in secenekler:
        secenekler.insert(0, varsayilan)
    secimler = [f"— {etiket} —"] + secenekler
    if key not in st.session_state:
        st.session_state[key] = varsayilan if varsayilan in secenekler else secimler[0]
    secim = st.selectbox(
        etiket, secimler, key=key,
        label_visibility="collapsed"
    )
    return "" if secim == secimler[0] else secim


def miktar_metni_gecerli_mi(deger: str) -> bool:
    """Pozitif sayılar, '2,5 TON' gibi sayı+birim ve sayılar dışında yalnızca TONAJ / Y.TONAJ kabul eder."""
    ham = str(deger or "").strip()
    if not ham:
        return False

    if ham.upper() in ("TONAJ", "Y.TONAJ"):
        return True

    metin = ham.replace(",", ".")
    try:
        return float(metin) > 0
    except ValueError:
        return bool(re.fullmatch(r"\d+(?:[.,]\d+)?\s*[A-Za-zÇĞİÖŞÜçğıöşü]+", ham))


if st.query_params.get("action") == "refresh":
    st.cache_data.clear()
    st.query_params.pop("action", None)
    st.rerun()

for alan, varsayilan in {
    "eklenen_urunler": [],
    "urun_input_versiyon": 0,
    "form_versiyon": 0,
    "flash_mesaj": None,
    "taslak_bilgi": {},
    "siparis_ekrani_kapali": False,
}.items():
    if alan not in st.session_state:
        st.session_state[alan] = varsayilan

yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger
aktif_token = st.session_state.get("active_token") or st.query_params.get("token", "")
token_param = f"&token={aktif_token}" if aktif_token else ""
refresh_href = f"?action=refresh{token_param}"

# 1. mobil_izleme Koyu Lacivert-Turuncu Üst Banner
if yetki_tipi == "SIPARIS_VEREN" and yetki_deger:
    baslik_metni = f'{LOGO_HTML}<span>SAYAR YAPI | {html.escape(str(yetki_deger))}</span>'
    alt_metin = "Personel Mobil Sipariş Paneli"
else:
    baslik_metni = f'{LOGO_HTML}<span>SAYAR YAPI | Mobil Sipariş</span>'
    alt_metin = "Hızlı Sipariş & Sevkiyat Girişi"

st.markdown(
    f'<div class="header-banner">'
    f'<div class="header-info">'
    f'<div class="header-title">{baslik_metni}</div>'
    f'<div class="header-sub">{alt_metin}</div>'
    f'</div>'
    f'<div class="header-actions">'
    f'<a data-spa="1" href="{refresh_href}" target="_self" class="icon-btn" title="Listeleri Yenile">🔄</a>'
    f'<a data-spa="1" href="?action=logout" target="_self" class="icon-btn" title="Çıkış">🚪</a>'
    f'</div></div>',
    unsafe_allow_html=True
)

# Otomatik Kaybolan Başarı Bildirimi
flash_msg = st.session_state.flash_mesaj
if flash_msg:
    toast_id = f"toast_{int(time.time() * 1000)}"
    st.markdown(
        f'<div id="{toast_id}" class="auto-toast-banner">✅ {html.escape(str(flash_msg))}</div>',
        unsafe_allow_html=True
    )
    components.html(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;
            const el = doc.getElementById({json.dumps(toast_id)});
            if (!el) return;
            setTimeout(function() {{
                el.style.opacity = '0';
                setTimeout(function() {{
                    if (el && el.parentNode) el.parentNode.removeChild(el);
                }}, 350);
            }}, 2800);
        }})();
        </script>
        """,
        height=0,
        width=0
    )
    st.session_state.flash_mesaj = None

if st.session_state.siparis_ekrani_kapali:
    st.markdown(
        '<div class="empty-state-box">'
        '<div class="empty-state-icon">📦</div>'
        '<div class="empty-state-title">Sipariş Giriş Ekranı Kapatıldı</div>'
        '<div class="empty-state-desc">Yeni bir sipariş oluşturmak için aşağıdaki butona dokunun.</div>'
        '</div>',
        unsafe_allow_html=True
    )
    if st.button("➕ YENİ SİPARİŞ OLUŞTUR", type="primary", use_container_width=True):
        st.session_state.siparis_ekrani_kapali = False
        st.rerun()
    st.stop()

# 2. mobil_izleme 3'lü KPI Durum Şeridi
kalem_sayisi = len(st.session_state.eklenen_urunler)
bugun_etiket = date.today().strftime("%d.%m.%Y")
veren_ozet = str(yetki_deger) if (yetki_tipi == "SIPARIS_VEREN" and yetki_deger) else "Yönetici"

st.markdown(
    f'<div class="kpi-grid">'
    f'<div class="kpi-card kpi-blue"><div class="kpi-label">Sipariş Tarihi</div><div class="kpi-value">{bugun_etiket}</div></div>'
    f'<div class="kpi-card kpi-orange"><div class="kpi-label">Eklenen Kalem</div><div class="kpi-value">{kalem_sayisi}</div></div>'
    f'<div class="kpi-card kpi-green"><div class="kpi-label">Yetkili</div><div class="kpi-value">{html.escape(veren_ozet)}</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

# 3. mobil_izleme İnceleme Kartı Stilinde Kompakt Sipariş Formu
with st.container(key="siparis-form-card"):
    st.markdown(
        '<div class="form-card-header">'
        '<div class="form-card-title">🟠 YENİ SİPARİŞ KAYDI</div>'
        '<div class="form-card-badge">ONAY BEKLİYOR</div>'
        '</div>',
        unsafe_allow_html=True
    )

    listeler = secim_listelerini_getir()
    fv = st.session_state.form_versiyon
    uv = st.session_state.urun_input_versiyon
    taslak = st.session_state.taslak_bilgi
    bugun = date.today()

    tarih_default = taslak.get("tarih_obj", bugun)
    sevk_default = taslak.get("sevk_tarihi_obj", bugun)
    tarih_col, sevk_col = st.columns(2)
    with tarih_col:
        siparis_tarihi = st.date_input(
            "Sipariş Tarihi", value=tarih_default, format="DD.MM.YYYY",
            key=f"siparis_tarihi_{fv}"
        )
    with sevk_col:
        sevk_tarihi = st.date_input(
            "Sevk Tarihi", value=sevk_default, format="DD.MM.YYYY",
            key=f"sevk_tarihi_{fv}"
        )

    alan_sol, alan_sag = st.columns(2)
    with alan_sol:
        firma = secim_alani("Tedarikçi Firma", f"firma_{fv}", listeler["firma"], taslak.get("firma", ""))
    with alan_sag:
        musteri = secim_alani("Müşteri", f"musteri_{fv}", listeler["musteri"], taslak.get("musteri", ""))

    alan_sol, alan_sag = st.columns(2)
    with alan_sol:
        santiye = secim_alani("Şantiye", f"santiye_{fv}", listeler["santiye"], taslak.get("santiye", ""))
    with alan_sag:
        sehir = secim_alani("Şehir", f"sehir_{fv}", listeler["sehir"], taslak.get("sehir") or "İSTANBUL")

    alan_sol, alan_sag = st.columns(2)
    with alan_sol:
        fabrika = secim_alani("Fabrika", f"fabrika_{fv}", listeler["fabrika"], taslak.get("fabrika", ""))
    with alan_sag:
        nakliye = secim_alani("Nakliye", f"nakliye_{fv}", listeler["nakliye"], taslak.get("nakliye", ""))

    alan_sol, alan_sag = st.columns(2)
    with alan_sol:
        arac = secim_alani("Araç", f"arac_{fv}", listeler["arac"], taslak.get("arac") or "TIR ( 27 TON )")
    with alan_sag:
        if yetki_tipi == "SIPARIS_VEREN" and yetki_deger:
            siparis_veren = st.text_input(
                "Sipariş Veren", value=str(yetki_deger), disabled=True,
                key=f"veren_kilit_{fv}", placeholder="Sipariş Veren",
                label_visibility="collapsed"
            ).strip()
        else:
            siparis_veren = secim_alani(
                "Sipariş Veren", f"veren_{fv}", listeler["siparis_veren"],
                taslak.get("siparis_veren", "")
            )

    firma_aktif = firma or taslak.get("firma", "")
    filtrelenmis_urunler = [
        u["deger"] for u in listeler["urunler_detay"]
        if not firma_aktif or not u.get("firma") or u["firma"].upper() == firma_aktif.upper()
    ]
    urun_secimi = secim_alani("Kayıtlı Ürün Seçin", f"urun_giris_{fv}_{uv}", filtrelenmis_urunler)

    urun_col, birim_col, miktar_col, ekle_col = st.columns([4, 2, 3, 1])
    with urun_col:
        urun_serbest = st.text_input(
            "Ürün Adı", key=f"urun_serbest_{fv}_{uv}",
            placeholder="Veya ürün adı yazın...", label_visibility="collapsed"
        ).strip()
        u_ad = urun_serbest or urun_secimi
    with birim_col:
        birim_opsiyon = list(dict.fromkeys(listeler["birim"] or ["ADET", "TON", "KG"]))
        u_birim = st.selectbox(
            "Birim", birim_opsiyon, key=f"birim_giris_{fv}_{uv}",
            label_visibility="collapsed"
        )
    with miktar_col:
        u_miktar = st.text_input(
            "Miktar", key=f"miktar_giris_{fv}_{uv}",
            placeholder="Miktar / TONAJ", label_visibility="collapsed"
        ).strip()
    with ekle_col:
        ekle_tiklandi = st.button("＋", key=f"btn_urun_ekle_{fv}_{uv}", type="primary", use_container_width=True)

    if ekle_tiklandi:
        if not u_ad:
            st.warning("Lütfen ürün seçin veya yazın.")
        elif not miktar_metni_gecerli_mi(u_miktar):
            st.warning("Lütfen geçerli bir adet veya tonaj (TONAJ / Y.TONAJ) giriniz.")
        else:
            st.session_state.eklenen_urunler.append({
                "urun": u_ad, "miktar": u_miktar, "birim": u_birim
            })
            st.session_state.urun_input_versiyon += 1
            st.rerun()

    if st.session_state.eklenen_urunler:
        st.markdown(
            '<div class="siparis-kalem-baslik">'
            '<span>Malzeme / Ürün</span><span>Birim</span><span>Miktar</span>'
            '</div>',
            unsafe_allow_html=True
        )
        for idx, item in enumerate(st.session_state.eklenen_urunler):
            satir_col, sil_col = st.columns([6, 1])
            with satir_col:
                st.markdown(
                    f'<div class="eklenen-urun-satir">'
                    f'<span class="eklenen-urun-ad">{idx + 1}. {html.escape(str(item["urun"]))}</span>'
                    f'<span class="eklenen-urun-birim">{html.escape(str(item["birim"]))}</span>'
                    f'<span class="eklenen-urun-miktar">{html.escape(str(item["miktar"]))}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with sil_col:
                if st.button("✕", key=f"sil_urun_{fv}_{idx}", use_container_width=True):
                    st.session_state.eklenen_urunler.pop(idx)
                    st.rerun()
    else:
        st.markdown(
            '<div class="bos-liste-kutusu">Henüz ürün eklenmedi. Ürün, birim ve miktar girerek ＋ butonuna dokunun.</div>',
            unsafe_allow_html=True
        )

# 4. Sabit Alt Aksiyon Barı (mobil_izleme Yeşil / Sarı / Kırmızı Paleti)
st.markdown('<div class="sticky-gonder-isaret"></div>', unsafe_allow_html=True)
alt_kaydet, alt_temizle, alt_kapat = st.columns(3)
with alt_kaydet:
    kaydet_tiklandi = st.button("KAYDET", key=f"btn_kaydet_{fv}", use_container_width=True)
with alt_temizle:
    temizle_tiklandi = st.button("TEMİZLE", key=f"btn_temizle_{fv}", use_container_width=True)
with alt_kapat:
    kapat_tiklandi = st.button("KAPAT", key=f"btn_kapat_{fv}", use_container_width=True)

if temizle_tiklandi:
    st.session_state.eklenen_urunler = []
    st.session_state.taslak_bilgi = {}
    st.session_state.urun_input_versiyon += 1
    st.session_state.form_versiyon += 1
    st.rerun()

if kapat_tiklandi:
    st.session_state.eklenen_urunler = []
    st.session_state.taslak_bilgi = {}
    st.session_state.siparis_ekrani_kapali = True
    st.rerun()

if kaydet_tiklandi:
    eksikler = []
    for alan_adi, alan_degeri in [
        ("Sipariş Veren", siparis_veren), ("Tedarikçi Firma", firma), ("Müşteri", musteri),
        ("Şantiye", santiye), ("Fabrika", fabrika), ("Nakliye", nakliye), ("Araç", arac)
    ]:
        if not str(alan_degeri or "").strip():
            eksikler.append(alan_adi)
    if eksikler:
        st.error(f"Eksik alanlar: {', '.join(eksikler)}")
    elif not st.session_state.eklenen_urunler:
        st.error("Lütfen en az bir ürün kalemi ekleyiniz.")
    else:
        yeni_siparis_paketi = {
            "tarih": siparis_tarihi.strftime("%Y-%m-%d"),
            "sevk_tarihi": sevk_tarihi.strftime("%Y-%m-%d"),
            "firma": firma,
            "musteri": musteri,
            "santiye": santiye,
            "sehir": sehir or "İSTANBUL",
            "telefon": "",
            "yetkili": "",
            "arac": arac,
            "fabrika": fabrika,
            "nakliye": nakliye,
            "notlar": "",
            "ted_sip_no": "",
            "plaka": "",
            "nakliye_fatura": "",
            "siparis_veren": siparis_veren,
            "firma_yetkili": "",
            "siparis_gecen": "",
            "durum": "Beklemede",
            "operasyon": "ONAY BEKLİYOR",
            "urunler": list(st.session_state.eklenen_urunler)
        }
        try:
            with st.spinner("PostgreSQL veritabanına kaydediliyor..."):
                kaydedilen_no = yeni_siparis_pg_kaydet(yeni_siparis_paketi)
                yeni_siparis_ntfy_gonder({**yeni_siparis_paketi, "siparis_no": kaydedilen_no})
            secim_listelerini_getir.clear()
            st.session_state.eklenen_urunler = []
            st.session_state.urun_input_versiyon = 0
            st.session_state.taslak_bilgi = {}
            st.session_state.form_versiyon += 1
            st.session_state.flash_mesaj = f"Sipariş #{kaydedilen_no} — {musteri} ({santiye}) kaydedildi!"
            st.rerun()
        except Exception as err:
            st.error(f"Sipariş PostgreSQL veritabanına yazılamadı: {err}")
