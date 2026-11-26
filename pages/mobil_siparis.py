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
    yol = dosya_yolu if os.path.exists(dosya_yolu) else os.path.join("static", dosya_yolu)
    if os.path.exists(yol):
        ext = os.path.splitext(yol)[1].lower()
        mime = "image/svg+xml" if ext == ".svg" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/png")
        with open(yol, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    return None


LOGO_DATA_URI = logo_base64_getir("logo.png")
LOGO_HTML = f'<img src="{LOGO_DATA_URI}" class="sy-logo-img" alt="Logo">' if LOGO_DATA_URI else '<span class="sy-logo-fallback">🏗️</span>'

st.set_page_config(
    page_title="Sayar Yapı | Hızlı Sipariş Girişi",
    page_icon=LOGO_DATA_URI if LOGO_DATA_URI else "🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

        function syncLiveClock() {{
            const clockEl = doc.getElementById('sy-live-clock');
            if (!clockEl) return;
            const now = new Date();
            const hh = String(now.getHours()).padStart(2, '0');
            const mm = String(now.getMinutes()).padStart(2, '0');
            const ss = String(now.getSeconds()).padStart(2, '0');
            clockEl.textContent = `${{hh}}:${{mm}}:${{ss}}`;
        }}
        syncLiveClock();
        if (!win.__syClockTimer) {{
            win.__syClockTimer = win.setInterval(syncLiveClock, 1000);
        }}
    }})();
    </script>
    """,
    height=0,
    width=0
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=JetBrains+Mono:wght@600;700&display=swap');

:root {
    --bg-canvas: #f3f6fb;
    --surface-card: #ffffff;
    --surface-subtle: #f8fafc;
    --surface-indigo: #eef2ff;
    --ink-primary: #0f172a;
    --ink-secondary: #475569;
    --ink-muted: #64748b;
    --accent: #4f46e5;
    --accent-dark: #3730a3;
    --emerald: #059669;
    --border-soft: #e2e8f0;
    --border-strong: #cbd5e1;
}

*, *::before, *::after {
    box-sizing: border-box !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
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
    background-color: var(--bg-canvas) !important;
    color: var(--ink-primary) !important;
    overflow-x: hidden !important;
    max-width: 100vw !important;
    width: 100% !important;
}

.block-container {
    padding-top: 0.45rem !important;
    padding-bottom: 4.8rem !important;
    padding-left: 0.55rem !important;
    padding-right: 0.55rem !important;
    max-width: 480px !important;
    width: 100% !important;
    margin: 0 auto !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

[data-testid="stVerticalBlock"] {
    gap: 0.26rem !important;
    width: 100% !important;
    max-width: 100% !important;
}

[data-testid="element-container"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
}

/* Yatay satırları tek satırda ve taşmadan tut */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 5px !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    align-items: center !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    min-width: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

/* Kompakt Canlı Başlık */
.sy-top-bar {
    background: linear-gradient(135deg, #ffffff 0%, #f5f7ff 100%);
    border: 1px solid #dbe4ff;
    border-top: 3px solid var(--accent);
    border-radius: 14px;
    padding: 8px 10px;
    margin-bottom: 5px;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
    width: 100%;
}

.sy-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    width: 100%;
}

.sy-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    flex: 1;
}

.sy-logo-box {
    width: 32px;
    height: 32px;
    border-radius: 9px;
    background: #ffffff;
    border: 1px solid var(--border-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.sy-logo-img {
    width: 24px;
    height: 24px;
    object-fit: contain;
}

.sy-logo-fallback {
    font-size: 16px;
    line-height: 1;
}

.sy-title-wrap {
    min-width: 0;
    flex: 1;
}

.sy-title {
    font-size: 13.5px;
    font-weight: 800;
    color: var(--ink-primary);
    line-height: 1.15;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-sub {
    font-size: 10px;
    color: var(--ink-secondary);
    margin-top: 1px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-live-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #ecfdf5;
    color: #047857;
    border: 1px solid #a7f3d0;
    border-radius: 999px;
    padding: 2px 6px;
    font-size: 9px;
    font-weight: 800;
    white-space: nowrap;
    flex-shrink: 0;
}

.sy-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
    animation: syBlink 1.6s infinite;
}

@keyframes syBlink {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.35; transform: scale(0.8); }
}

.sy-clock {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    color: var(--ink-primary);
    background: #ffffff;
    border: 1px solid var(--border-soft);
    border-radius: 7px;
    padding: 2px 6px;
    white-space: nowrap;
    flex-shrink: 0;
}

.sy-btn-group {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
}

.sy-act-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    background: #ffffff;
    border: 1px solid var(--border-strong);
    color: var(--ink-primary) !important;
    text-decoration: none !important;
    font-size: 13px;
}

.sy-meta-line {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    margin-top: 6px;
    padding-top: 5px;
    border-top: 1px dashed #e2e8f0;
    font-size: 10px;
    color: var(--ink-secondary);
}

/* Bildirim */
.sy-flash {
    background: #ecfdf5;
    border: 1px solid #6ee7b7;
    border-left: 3.5px solid #059669;
    color: #064e3b;
    border-radius: 10px;
    padding: 7px 10px;
    font-size: 11.5px;
    font-weight: 700;
    margin-bottom: 4px;
}

/* Kompakt Form Kartı */
.st-key-siparis-form-card {
    background: var(--surface-card) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 16px !important;
    padding: 8px 9px 10px 9px !important;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06) !important;
    width: 100% !important;
    max-width: 100% !important;
}

.st-key-siparis-form-card > div {
    gap: 0.26rem !important;
}

.sy-mini-lbl {
    font-size: 9.5px;
    font-weight: 700;
    color: var(--ink-muted);
    margin: 0 0 1px 2px;
    line-height: 1.1;
}

/* Giriş Alanları */
div[data-testid="stDateInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label {
    display: none !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1.2px solid var(--border-strong) !important;
    border-radius: 10px !important;
    color: var(--ink-primary) !important;
    min-height: 38px !important;
    height: 38px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stDateInput"] input:focus,
div[data-baseweb="select"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.12) !important;
}

div[data-baseweb="select"] > div > div {
    min-width: 0 !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

div[data-testid="stNumberInput"] button {
    display: none !important;
}

/* Butonlar & Popover Açılır Kutular */
div[data-testid="stButton"] button,
div[data-testid="stPopover"] > button {
    min-height: 38px !important;
    height: 38px !important;
    padding: 0 6px !important;
    font-size: 11.5px !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    border: 1.2px solid var(--border-strong) !important;
    background-color: #ffffff !important;
    color: var(--ink-primary) !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    width: 100% !important;
    max-width: 100% !important;
}

div[data-testid="stButton"] button:hover,
div[data-testid="stPopover"] > button:hover {
    border-color: var(--accent) !important;
    background-color: var(--surface-indigo) !important;
    color: var(--accent-dark) !important;
}

button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important;
    border: 1.2px solid #3730a3 !important;
    color: #ffffff !important;
    font-weight: 800 !important;
}

button[kind="primary"]:hover {
    background: linear-gradient(135deg, #4338ca 0%, #312e81 100%) !important;
    color: #ffffff !important;
}

/* Alt Sabit Aksiyon Çubuğu */
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: 100% !important;
    max-width: 480px !important;
    padding: 6px 0.55rem 8px 0.55rem !important;
    background: rgba(243, 246, 251, 0.94) !important;
    backdrop-filter: blur(10px) !important;
    border-top: 1px solid var(--border-soft) !important;
    z-index: 9999 !important;
    margin: 0 !important;
}

/* Kalem Listesi */
.sy-kalem-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 54px 62px;
    gap: 4px;
    background: #1e293b;
    color: #ffffff;
    border-radius: 8px 8px 0 0;
    padding: 6px 8px;
    font-size: 10px;
    font-weight: 700;
    margin-top: 4px;
}

.sy-kalem-head span:nth-child(2),
.sy-kalem-head span:nth-child(3) {
    text-align: center;
}

.sy-kalem-item {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 54px 62px;
    gap: 4px;
    align-items: center;
    background: #f8fafc;
    border: 1px solid var(--border-soft);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 6px 8px;
    min-height: 36px;
    width: 100%;
}

.sy-kalem-name {
    font-size: 11px;
    font-weight: 700;
    color: var(--ink-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-kalem-unit {
    font-size: 9.5px;
    font-weight: 700;
    color: #0369a1;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-kalem-qty {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 700;
    color: var(--ink-primary);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-empty {
    background: #f8fafc;
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    padding: 8px;
    text-align: center;
    font-size: 10.5px;
    color: var(--ink-secondary);
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


def get_postgres_url() -> str:
    """Railway PostgreSQL bağlantı adresini döndürür."""
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if env_url:
        return env_url.replace("postgres://", "postgresql://", 1)

    try:
        for secret_key in ("DATABASE_URL", "POSTGRES_URL", "RAILWAY_DB_URL"):
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


def _render_kompakt_ust_panel(baslik: str, alt_baslik: str, sag_aksiyon_html: str = "", kalem_adet: int = 0):
    st.markdown(
        f'<div class="sy-top-bar">'
        f'<div class="sy-top-row">'
        f'<div class="sy-brand">'
        f'<div class="sy-logo-box">{LOGO_HTML}</div>'
        f'<div class="sy-title-wrap">'
        f'<div class="sy-title">{html.escape(str(baslik))}</div>'
        f'<div class="sy-sub">{html.escape(str(alt_baslik))}</div>'
        f'</div>'
        f'</div>'
        f'{sag_aksiyon_html}'
        f'</div>'
        f'<div class="sy-meta-line">'
        f'<span class="sy-live-badge"><span class="sy-dot"></span>CANLI</span>'
        f'<span>Kalem: <b>{kalem_adet}</b></span>'
        f'<span class="sy-clock" id="sy-live-clock">{datetime.now().strftime("%H:%M:%S")}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )


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
        _render_kompakt_ust_panel("SAYAR YAPI", "Mobil Sipariş Girişi")
        if url_veren:
            st.caption(f"Personel: **{url_veren}**")

        with st.form("login_form", clear_on_submit=False):
            pin = st.text_input("Erişim Şifresi", placeholder="Erişim Şifresi...", type="password", label_visibility="collapsed")
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
    """Başlıksız açılır kutu; alan adı kutunun içinde görünür."""
    temiz = [str(x).strip() for x in secenekler if str(x).strip() and str(x).strip() != "-"]
    secenekler = list(dict.fromkeys(temiz))
    if varsayilan and varsayilan not in secenekler:
        secenekler.insert(0, varsayilan)
    secimler = [f"▾ {etiket}"] + secenekler
    if key not in st.session_state:
        st.session_state[key] = varsayilan if varsayilan in secenekler else secimler[0]
    secim = st.selectbox(
        etiket, secimler, key=key,
        label_visibility="collapsed"
    )
    return "" if secim == secimler[0] else secim


def hizli_secim_alani(etiket: str, key: str, secenekler: list, varsayilan: str = ""):
    """Kayıtlı değerleri açılır kutu (popover) içinde sunan seçim alanı."""
    temiz = [str(x).strip() for x in secenekler if str(x).strip() and str(x).strip() != "-"]
    secenekler = list(dict.fromkeys(temiz))
    if varsayilan and varsayilan not in secenekler:
        secenekler.insert(0, varsayilan)
    secim_key = f"{key}_value"
    if secim_key not in st.session_state:
        st.session_state[secim_key] = varsayilan if varsayilan in secenekler else ""
    secili = st.session_state[secim_key]
    baslik = secili if secili else f"▾ {etiket}"

    with st.popover(baslik, use_container_width=True):
        st.markdown(f"**{etiket}**")
        if not secenekler:
            st.caption("Kayıtlı seçenek yok.")
        else:
            for idx, secenek in enumerate(secenekler):
                if st.button(
                    secenek,
                    key=f"{key}_pop_{idx}",
                    use_container_width=True,
                    type="primary" if secenek == secili else "secondary"
                ):
                    st.session_state[secim_key] = secenek
                    st.rerun()
        if secili:
            if st.button("Temizle", key=f"{key}_pop_clear", use_container_width=True):
                st.session_state[secim_key] = ""
                st.rerun()

    return st.session_state[secim_key]


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
    "quick_open_field": None,
    "siparis_ekrani_kapali": False,
}.items():
    if alan not in st.session_state:
        st.session_state[alan] = varsayilan

yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger
aktif_token = st.session_state.get("active_token") or st.query_params.get("token", "")
token_param = f"&token={aktif_token}" if aktif_token else ""
refresh_href = f"?action=refresh{token_param}"

alt_baslik = f"Personel: {yetki_deger}" if yetki_tipi == "SIPARIS_VEREN" else "Yeni Sipariş Girişi"
sag_aksiyon = (
    f'<div class="sy-btn-group">'
    f'<a data-spa="1" href="{refresh_href}" target="_self" class="sy-act-btn" title="Yenile">🔄</a>'
    f'<a data-spa="1" href="?action=logout" target="_self" class="sy-act-btn" title="Çıkış">🚪</a>'
    f'</div>'
)
_render_kompakt_ust_panel("SAYAR YAPI", alt_baslik, sag_aksiyon, len(st.session_state.eklenen_urunler))

flash_msg = st.session_state.flash_mesaj
if flash_msg:
    st.markdown(
        f'<div class="sy-flash">✅ {html.escape(str(flash_msg))}</div>',
        unsafe_allow_html=True
    )
    st.session_state.flash_mesaj = None

if st.session_state.siparis_ekrani_kapali:
    st.info("Yeni sipariş ekranı kapatıldı.")
    if st.button("YENİ SİPARİŞ AÇ", type="primary", use_container_width=True):
        st.session_state.siparis_ekrani_kapali = False
        st.rerun()
    st.stop()

listeler = secim_listelerini_getir()
fv = st.session_state.form_versiyon
uv = st.session_state.urun_input_versiyon
taslak = st.session_state.taslak_bilgi
bugun = date.today()

with st.container(key="siparis-form-card"):
    tarih_default = taslak.get("tarih_obj", bugun)
    sevk_default = taslak.get("sevk_tarihi_obj", bugun)

    tarih_col, sevk_col = st.columns(2)
    with tarih_col:
        st.markdown('<div class="sy-mini-lbl">Sipariş Tarihi</div>', unsafe_allow_html=True)
        siparis_tarihi = st.date_input(
            "Sipariş Tarihi", value=tarih_default, format="DD.MM.YYYY",
            key=f"siparis_tarihi_{fv}", label_visibility="collapsed"
        )
    with sevk_col:
        st.markdown('<div class="sy-mini-lbl">Sevk Tarihi</div>', unsafe_allow_html=True)
        sevk_tarihi = st.date_input(
            "Sevk Tarihi", value=sevk_default, format="DD.MM.YYYY",
            key=f"sevk_tarihi_{fv}", label_visibility="collapsed"
        )

    firma = secim_alani("Firma", f"firma_{fv}", listeler["firma"], taslak.get("firma", ""))
    musteri = secim_alani("Müşteri", f"musteri_{fv}", listeler["musteri"], taslak.get("musteri", ""))
    santiye = secim_alani("Şantiye", f"santiye_{fv}", listeler["santiye"], taslak.get("santiye", ""))
    sehir = secim_alani("Şehir", f"sehir_{fv}", listeler["sehir"], taslak.get("sehir") or "İSTANBUL")

    fabrika = hizli_secim_alani(
        "Fabrika", f"fabrika_{fv}", listeler["fabrika"], taslak.get("fabrika", "")
    )
    nakliye = hizli_secim_alani(
        "Nakliye", f"nakliye_{fv}", listeler["nakliye"], taslak.get("nakliye", "")
    )
    arac = hizli_secim_alani(
        "Araç", f"arac_{fv}", listeler["arac"], taslak.get("arac") or "TIR ( 27 TON )"
    )

    if yetki_tipi == "SIPARIS_VEREN" and yetki_deger:
        siparis_veren = st.text_input(
            "Sipariş Veren", value=str(yetki_deger), disabled=True,
            key=f"veren_kilit_{fv}", placeholder="Sipariş Veren",
            label_visibility="collapsed"
        ).strip()
    else:
        siparis_veren = hizli_secim_alani(
            "Sipariş Veren", f"veren_{fv}", listeler["siparis_veren"],
            taslak.get("siparis_veren", "")
        )

    firma_aktif = firma or taslak.get("firma", "")
    filtrelenmis_urunler = [
        u["deger"] for u in listeler["urunler_detay"]
        if not firma_aktif or not u.get("firma") or u["firma"].upper() == firma_aktif.upper()
    ]
    urun_secimi = secim_alani("Ürün", f"urun_giris_{fv}_{uv}", filtrelenmis_urunler)
    urun_serbest = st.text_input(
        "Ürün", key=f"urun_serbest_{fv}_{uv}",
        placeholder="Serbest ürün adı...", label_visibility="collapsed"
    ).strip()
    u_ad = urun_serbest or urun_secimi

    birim_col, miktar_col, ekle_col = st.columns([3.5, 4.5, 2])
    with birim_col:
        birim_opsiyon = list(dict.fromkeys(listeler["birim"] or ["ADET", "TON", "KG"]))
        u_birim = st.selectbox(
            "Birim", birim_opsiyon, key=f"birim_giris_{fv}_{uv}",
            label_visibility="collapsed"
        )
    with miktar_col:
        u_miktar = st.text_input(
            "Adet / Tonaj", key=f"miktar_giris_{fv}_{uv}",
            placeholder="Adet / Tonaj", label_visibility="collapsed"
        ).strip()
    with ekle_col:
        ekle_tiklandi = st.button("＋", key=f"btn_urun_ekle_{fv}_{uv}", use_container_width=True)

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
            '<div class="sy-kalem-head">'
            '<span>Malzeme / Ürün</span><span>Birim</span><span>Miktar</span>'
            '</div>',
            unsafe_allow_html=True
        )
        for idx, item in enumerate(st.session_state.eklenen_urunler):
            satir_col, sil_col = st.columns([8.2, 1.8])
            with satir_col:
                st.markdown(
                    f'<div class="sy-kalem-item">'
                    f'<span class="sy-kalem-name">{idx + 1}. {html.escape(str(item["urun"]))}</span>'
                    f'<span class="sy-kalem-unit">{html.escape(str(item["birim"]))}</span>'
                    f'<span class="sy-kalem-qty">{html.escape(str(item["miktar"]))}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with sil_col:
                if st.button("✕", key=f"sil_urun_{fv}_{idx}", use_container_width=True):
                    st.session_state.eklenen_urunler.pop(idx)
                    st.rerun()
    else:
        st.markdown(
            '<div class="sy-empty">Henüz ürün eklenmedi · ＋ ile ekleyin</div>',
            unsafe_allow_html=True
        )

st.markdown('<div class="sticky-gonder-isaret"></div>', unsafe_allow_html=True)
alt_kaydet, alt_temizle, alt_kapat = st.columns([1.2, 1, 1])
with alt_kaydet:
    kaydet_tiklandi = st.button("KAYDET", key=f"btn_kaydet_{fv}", type="primary", use_container_width=True)
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
        ("Sipariş Veren", siparis_veren), ("Firma", firma), ("Müşteri", musteri),
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
