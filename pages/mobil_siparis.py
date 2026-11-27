
Gemini
Yeni sohbet
Kitaplık
Resimler
Planlandı
Öğrenciler

Daha fazla
Yeni not defteri
Sayar Yapı Mobil Sipariş Terminali Tasarımı
Program Kullanıcı Kolaylığı Önerileri
Sayar Yapı Mobil Sipariş Arayüzü
Sayar Yapı Mobil Lojistik Radarı
Lojistik Komuta Merkezi Arayüz Tasarımı
Bu programın çalışma mantığını hiç bozmadan. sadece görsel tamamen yepyeni bir tasarım yaparmısın. d
Gemini ile sohbet
Bu programın çalışma mantığını hiç bozmadan. sadece görselde tamamen yepyeni bir tasarım yaparmısın. daha yenilikçi, daha kurumsal, daha teknolojik, bambaşka bir tasarım. görsel olarak herşeyi değiştirebilirsin. Senden bambaşka yepyeni bir tasarım bekliyorum. beni çoook şaşırtmalısın. özellikle cep telefonunda kullanılacak mobil uyum ve kolay girişler çok önemli, taşma olmamamlı indirilebilir tam dosya olarak verBu programın çalışma mantığını hiç bozmadan. sadece görselde tamamen yepyeni bir tasarım yaparmısın. daha yenilikçi, daha kurumsal, daha teknolojik, bambaşka bir tasarım. görsel olarak herşeyi değiştirebilirsin. Senden bambaşka yepyeni bir tasarım bekliyorum. beni çoook şaşırtmalısın. özellikle cep telefonunda kullanılacak mobil uyum ve kolay girişler çok önemli, veri giriş yöntemlerinide değiştirebilirsin taşma olmamamlı. indirilebilir tam dosya olarak ver

mobil_siparis.py için çalışma mantığını, veritabanı işlemlerini (yeni_siparis_pg_kaydet), kimlik doğrulamayı ve ntfy bildirim sistemini birebir koruyarak; açık tonlu, kurumsal, teknolojik ve tamamen mobil odaklı (sıfır yatay taşma garantili) yepyeni bir arayüz tasarladım.

Tasarımda Yapılan Yenilikler
Sıfır Taşmalı Teknolojik Kart Mimarisi: Yan yana daralan kutular yerine mobilde parmakla tek dokunuşta hata payını sıfıra indiren tam genişlikli, mikro-gölgeli modern kart düzenine geçildi; başlık kalabalıkları kaldırıldı.

Akıllı Veri Giriş Yöntemleri: Buton açılırları yerine dokunmatik arama destekli açılır seçim kutularına (selectbox) geçildi. Miktar girişi için standart sayısal alana ek olarak tek dokunuşla TONAJ ve Y.TONAJ seçimi sağlayan hızlı çip (pill) düğmeleri eklendi.

Canlı İlerleme Çubuğu (Progress Bar) & Durum Göstergesi: Üst barda canlı sistem göstergesi ile doldurulan zorunlu alanların oranını ve eklenen kalem sayısını anlık gösteren ilerleme çubuğu yerleştirildi.

Sabit Alt Komut Konsolu: Ekranın en altına sabitlenen (sticky) ve cam efekti (backdrop-blur) uygulanan panel ile KAYDET, TEMİZLE ve KAPAT işlemlerine her an tek parmakla erişim sağlandı.

Python
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
LOGO_HTML = f'<img src="{LOGO_DATA_URI}" class="brand-logo" alt="Sayar Yapı">' if LOGO_DATA_URI else "🏗️"

st.set_page_config(
    page_title="Sayar Yapı | Akıllı Sipariş Terminali",
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
    --bg-canvas: #eef2f6;
    --surface-card: #ffffff;
    --surface-subtle: #f8fafc;
    --ink-primary: #0f172a;
    --ink-secondary: #475569;
    --ink-muted: #64748b;
    --accent-primary: #2563eb;
    --accent-primary-dark: #1d4ed8;
    --accent-amber: #f97316;
    --accent-emerald: #10b981;
    --border-soft: #e2e8f0;
    --border-strong: #cbd5e1;
}

*, *::before, *::after {
    box-sizing: border-box !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
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
    background: radial-gradient(circle at 50% 0%, #f8fafc 0%, var(--bg-canvas) 100%) !important;
    color: var(--ink-primary) !important;
    overflow-x: hidden !important;
    max-width: 100vw !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
}

.block-container {
    padding-top: 0.45rem !important;
    padding-bottom: 5.4rem !important;
    padding-left: 0.55rem !important;
    padding-right: 0.55rem !important;
    max-width: 480px !important;
    width: 100% !important;
    margin: 0 auto !important;
}

[data-testid="stVerticalBlock"] {
    gap: 0.34rem !important;
    width: 100% !important;
    max-width: 100% !important;
}

[data-testid="element-container"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
}

/* Yatay kolonların mobilde taşmasını kesin olarak engelleyen yapı */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    min-width: 0 !important;
    padding: 0 !important;
}

/* Üst Kurumsal Komuta Merkezi Barı */
.tech-topbar {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    padding: 9px 11px;
    box-shadow: 0 4px 14px -2px rgba(15, 23, 42, 0.06);
    margin-bottom: 4px;
}

.tech-topbar-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.brand-cluster {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
    flex: 1;
}

.brand-logo-wrap {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: #f1f5f9;
    border: 1px solid var(--border-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    overflow: hidden;
}

.brand-logo {
    width: 26px;
    height: 26px;
    object-fit: contain;
}

.brand-meta {
    min-width: 0;
    flex: 1;
}

.brand-title-line {
    display: flex;
    align-items: center;
    gap: 6px;
}

.brand-title {
    font-size: 13.5px;
    font-weight: 800;
    color: var(--ink-primary);
    letter-spacing: -0.2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.live-pulse {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: var(--accent-emerald);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6);
    animation: pulseRing 2s infinite;
    flex-shrink: 0;
}

@keyframes pulseRing {
    0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.65); }
    70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.brand-sub {
    font-size: 10.5px;
    font-weight: 600;
    color: var(--ink-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 1px;
}

.action-cluster {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
}

.nav-pill-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 32px;
    padding: 0 9px;
    border-radius: 9px;
    background: #f1f5f9;
    border: 1px solid var(--border-strong);
    color: var(--ink-primary) !important;
    text-decoration: none !important;
    font-size: 12px;
    font-weight: 700;
    transition: all 0.15s ease;
}

.nav-pill-btn:active {
    transform: scale(0.96);
    background: #e2e8f0;
}

/* İlerleme Çubuğu & Telemetri Şeridi */
.telemetry-bar {
    margin-top: 8px;
    padding-top: 7px;
    border-top: 1px dashed var(--border-soft);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.progress-track {
    flex: 1;
    height: 5px;
    background: #e2e8f0;
    border-radius: 999px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563eb 0%, #10b981 100%);
    border-radius: 999px;
    transition: width 0.3s ease;
}

.telemetry-badge {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px;
    font-weight: 700;
    color: #1e40af;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    padding: 2px 7px;
    border-radius: 6px;
    white-space: nowrap;
}

/* Bildirim Toast */
.smart-toast {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
    border: 1px solid #6ee7b7;
    border-left: 4px solid #059669;
    color: #064e3b;
    border-radius: 11px;
    padding: 8px 11px;
    font-size: 12px;
    font-weight: 700;
    box-shadow: 0 3px 10px rgba(5, 150, 105, 0.12);
}

/* Ana Kart Konteynerleri */
.st-key-terminal-ana-kart,
.st-key-urun-sepet-kart,
.st-key-login-kart {
    background: var(--surface-card) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 14px !important;
    padding: 10px 10px 11px 10px !important;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04) !important;
    width: 100% !important;
    max-width: 100% !important;
}

.st-key-urun-sepet-kart {
    border-top: 3px solid var(--accent-primary) !important;
}

/* Form Input ve Selectbox Stilleri */
div[data-testid="stTextInput"] input,
div[data-testid="stDateInput"] input,
div[data-baseweb="select"] > div {
    background-color: var(--surface-subtle) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 10px !important;
    color: var(--ink-primary) !important;
    min-height: 41px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    width: 100% !important;
    max-width: 100% !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stDateInput"] input:focus,
div[data-baseweb="select"] > div:focus-within {
    background-color: #ffffff !important;
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
}

div[data-baseweb="select"] span {
    font-size: 13px !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

/* Tarih Alanı Kompakt Etiket Rozeti */
.date-chip-row {
    display: flex;
    justify-content: space-between;
    gap: 6px;
    margin-bottom: -2px;
}
.date-chip {
    flex: 1;
    font-size: 9.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: var(--ink-muted);
    padding-left: 3px;
}

/* Hızlı Tonaj Çip Butonları */
div[data-testid="stButton"] button {
    min-height: 40px !important;
    padding: 0 6px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    width: 100% !important;
    max-width: 100% !important;
    border: 1px solid var(--border-strong) !important;
    background-color: #f8fafc !important;
    color: var(--ink-primary) !important;
    transition: all 0.14s ease !important;
}

div[data-testid="stButton"] button:active {
    transform: scale(0.97);
}

button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
    border: 1px solid #1e40af !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    box-shadow: 0 3px 10px rgba(37, 99, 235, 0.25) !important;
}

button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1d4ed8 0%, #1e3a8a 100%) !important;
}

/* Sepet / Kalem Listesi */
.kalem-grid-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 58px 64px;
    gap: 5px;
    background: #0f172a;
    color: #f8fafc;
    border-radius: 9px;
    padding: 7px 9px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}

.kalem-grid-head span:nth-child(2),
.kalem-grid-head span:nth-child(3) {
    text-align: center;
}

.kalem-item-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 58px 64px;
    gap: 5px;
    align-items: center;
    background: #f8fafc;
    border: 1px solid var(--border-soft);
    border-left: 3px solid var(--accent-amber);
    border-radius: 9px;
    padding: 7px 8px;
    min-height: 40px;
    width: 100%;
    overflow: hidden;
}

.kalem-name {
    font-size: 12px;
    font-weight: 700;
    color: var(--ink-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.kalem-unit {
    font-size: 10.5px;
    font-weight: 700;
    color: var(--ink-secondary);
    background: #e2e8f0;
    border-radius: 6px;
    padding: 2px 4px;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.kalem-qty {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px;
    font-weight: 700;
    color: #1d4ed8;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 2px 4px;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.empty-cart-box {
    background: #f8fafc;
    border: 1.5px dashed #cbd5e1;
    border-radius: 10px;
    padding: 11px 8px;
    text-align: center;
    font-size: 11.5px;
    font-weight: 600;
    color: var(--ink-muted);
}

/* Sabit Alt Komut Konsolu (Sticky Dock) */
div[data-testid="element-container"]:has(.sticky-dock-anchor) + div[data-testid="element-container"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: 100% !important;
    max-width: 480px !important;
    padding: 8px 0.55rem 10px 0.55rem !important;
    background: rgba(255, 255, 255, 0.92) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border-top: 1px solid var(--border-soft) !important;
    box-shadow: 0 -4px 16px rgba(15, 23, 42, 0.06) !important;
    z-index: 9999 !important;
    margin: 0 !important;
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
            f'<div class="tech-topbar">'
            f'<div class="tech-topbar-row">'
            f'<div class="brand-cluster">'
            f'<div class="brand-logo-wrap">{LOGO_HTML}</div>'
            f'<div class="brand-meta">'
            f'<div class="brand-title-line"><span class="brand-title">SAYAR YAPI</span><span class="live-pulse"></span></div>'
            f'<div class="brand-sub">Saha &amp; Lojistik Sipariş Terminali</div>'
            f'</div></div></div></div>',
            unsafe_allow_html=True
        )
        with st.container(key="login-kart"):
            if url_veren:
                st.caption(f"Yetkili Personel: **{url_veren}**")

            with st.form("login_form", clear_on_submit=False):
                pin = st.text_input("Erişim Şifresi", placeholder="Güvenlik PIN / Şifre...", type="password", label_visibility="collapsed")
                beni_hatirla = st.checkbox("Bu cihazda oturumu açık tut (90 Gün)", value=True)
                giris_yapildi = st.form_submit_button("TERMİNALE BAĞLAN", use_container_width=True, type="primary")

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
    """Dokunmatik arama destekli, başlıksız açılır kutu."""
    temiz = [str(x).strip() for x in secenekler if str(x).strip() and str(x).strip() != "-"]
    secenekler = list(dict.fromkeys(temiz))
    if varsayilan and varsayilan not in secenekler:
        secenekler.insert(0, varsayilan)
    secimler = [f"{etiket} seçin..."] + secenekler
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

if st.session_state.siparis_ekrani_kapali:
    st.markdown(
        f'<div class="tech-topbar"><div class="tech-topbar-row">'
        f'<div class="brand-cluster"><div class="brand-logo-wrap">{LOGO_HTML}</div>'
        f'<div class="brand-meta"><div class="brand-title">SAYAR YAPI</div>'
        f'<div class="brand-sub">Oturum Beklemede</div></div></div>'
        f'<div class="action-cluster"><a data-spa="1" href="?action=logout" target="_self" class="nav-pill-btn">Çıkış</a></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )
    if st.button("YENİ SİPARİŞ TERMİNALİNİ AÇ", type="primary", use_container_width=True):
        st.session_state.siparis_ekrani_kapali = False
        st.rerun()
    st.stop()

listeler = secim_listelerini_getir()
fv = st.session_state.form_versiyon
uv = st.session_state.urun_input_versiyon
taslak = st.session_state.taslak_bilgi
bugun = date.today()

# Form Alanları Kartı
with st.container(key="terminal-ana-kart"):
    st.markdown(
        '<div class="date-chip-row"><span class="date-chip">Sipariş Tarihi</span><span class="date-chip">Sevk Tarihi</span></div>',
        unsafe_allow_html=True
    )
    tarih_default = taslak.get("tarih_obj", bugun)
    sevk_default = taslak.get("sevk_tarihi_obj", bugun)
    tarih_col, sevk_col = st.columns(2)
    with tarih_col:
        siparis_tarihi = st.date_input(
            "Sipariş Tarihi", value=tarih_default, format="DD.MM.YYYY",
            key=f"siparis_tarihi_{fv}", label_visibility="collapsed"
        )
    with sevk_col:
        sevk_tarihi = st.date_input(
            "Sevk Tarihi", value=sevk_default, format="DD.MM.YYYY",
            key=f"sevk_tarihi_{fv}", label_visibility="collapsed"
        )

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

    firma = secim_alani("Firma", f"firma_{fv}", listeler["firma"], taslak.get("firma", ""))
    musteri = secim_alani("Müşteri", f"musteri_{fv}", listeler["musteri"], taslak.get("musteri", ""))

    santiye_col, sehir_col = st.columns([3, 2])
    with santiye_col:
        santiye = secim_alani("Şantiye", f"santiye_{fv}", listeler["santiye"], taslak.get("santiye", ""))
    with sehir_col:
        sehir = secim_alani("Şehir", f"sehir_{fv}", listeler["sehir"], taslak.get("sehir") or "İSTANBUL")

    fab_col, nak_col = st.columns(2)
    with fab_col:
        fabrika = secim_alani("Fabrika", f"fabrika_{fv}", listeler["fabrika"], taslak.get("fabrika", ""))
    with nak_col:
        nakliye = secim_alani("Nakliye", f"nakliye_{fv}", listeler["nakliye"], taslak.get("nakliye", ""))

    arac = secim_alani("Araç Tipi", f"arac_{fv}", listeler["arac"], taslak.get("arac") or "TIR ( 27 TON )")

# Ürün Giriş ve Kalem Listesi Kartı
with st.container(key="urun-sepet-kart"):
    firma_aktif = firma or taslak.get("firma", "")
    filtrelenmis_urunler = [
        u["deger"] for u in listeler["urunler_detay"]
        if not firma_aktif or not u.get("firma") or u["firma"].upper() == firma_aktif.upper()
    ]
    urun_secimi = secim_alani("Listeden Ürün Seç", f"urun_giris_{fv}_{uv}", filtrelenmis_urunler)
    urun_serbest = st.text_input(
        "Özel Ürün Adı", key=f"urun_serbest_{fv}_{uv}",
        placeholder="Veya özel ürün / malzeme adı yazın...", label_visibility="collapsed"
    ).strip()
    u_ad = urun_serbest or urun_secimi

    miktar_key = f"miktar_giris_{fv}_{uv}"
    birim_col, miktar_col, hizli_t1, hizli_t2, ekle_col = st.columns([2.2, 2.5, 1.5, 1.7, 1.3])
    with birim_col:
        birim_opsiyon = list(dict.fromkeys(listeler["birim"] or ["ADET", "TON", "KG"]))
        u_birim = st.selectbox(
            "Birim", birim_opsiyon, key=f"birim_giris_{fv}_{uv}",
            label_visibility="collapsed"
        )
    with hizli_t1:
        if st.button("TONAJ", key=f"chip_tonaj_{fv}_{uv}", use_container_width=True):
            st.session_state[miktar_key] = "TONAJ"
    with hizli_t2:
        if st.button("Y.TONAJ", key=f"chip_ytonaj_{fv}_{uv}", use_container_width=True):
            st.session_state[miktar_key] = "Y.TONAJ"
    with miktar_col:
        u_miktar = st.text_input(
            "Miktar", key=miktar_key,
            placeholder="Miktar...", label_visibility="collapsed"
        ).strip()
    with ekle_col:
        ekle_tiklandi = st.button("＋", key=f"btn_urun_ekle_{fv}_{uv}", type="primary", use_container_width=True)

    if ekle_tiklandi:
        if not u_ad:
            st.warning("Lütfen listeden ürün seçin veya ürün adı yazın.")
        elif not miktar_metni_gecerli_mi(u_miktar):
            st.warning("Geçerli bir sayı, TONAJ veya Y.TONAJ giriniz.")
        else:
            st.session_state.eklenen_urunler.append({
                "urun": u_ad, "miktar": u_miktar, "birim": u_birim
            })
            st.session_state.urun_input_versiyon += 1
            st.rerun()

    if st.session_state.eklenen_urunler:
        st.markdown(
            '<div class="kalem-grid-head">'
            '<span>Malzeme</span><span>Birim</span><span>Miktar</span>'
            '</div>',
            unsafe_allow_html=True
        )
        for idx, item in enumerate(st.session_state.eklenen_urunler):
            satir_col, sil_col = st.columns([6.5, 1])
            with satir_col:
                st.markdown(
                    f'<div class="kalem-item-card">'
                    f'<span class="kalem-name">{idx + 1}. {html.escape(str(item["urun"]))}</span>'
                    f'<span class="kalem-unit">{html.escape(str(item["birim"]))}</span>'
                    f'<span class="kalem-qty">{html.escape(str(item["miktar"]))}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with sil_col:
                if st.button("✕", key=f"sil_urun_{fv}_{idx}", use_container_width=True):
                    st.session_state.eklenen_urunler.pop(idx)
                    st.rerun()
    else:
        st.markdown(
            '<div class="empty-cart-box">Sepette ürün yok — Yukarıdan ürün ve miktar seçip <b>＋</b> ile ekleyin.</div>',
            unsafe_allow_html=True
        )

# Dinamik İlerleme Hesabı ve Üst Komuta Barı (En üstte görünmesi için boşluk tutucu üzerinden render)
zorunlu_alanlar = [siparis_veren, firma, musteri, santiye, fabrika, nakliye, arac]
dolu_sayisi = sum(1 for x in zorunlu_alanlar if str(x or "").strip())
kalem_var = 1 if st.session_state.eklenen_urunler else 0
ilerleme_yuzde = int(((dolu_sayisi + kalem_var) / 8) * 100)
kalem_adet = len(st.session_state.eklenen_urunler)

alt_baslik = f"Personel: {yetki_deger}" if yetki_tipi == "SIPARIS_VEREN" else "Yönetici Modu • Canlı Sync"
st.markdown(
    f"""
    <div id="top-telemetry-source" style="display:none;">
        <div class="tech-topbar">
            <div class="tech-topbar-row">
                <div class="brand-cluster">
                    <div class="brand-logo-wrap">{LOGO_HTML}</div>
                    <div class="brand-meta">
                        <div class="brand-title-line">
                            <span class="brand-title">SAYAR YAPI</span>
                            <span class="live-pulse"></span>
                        </div>
                        <div class="brand-sub">{html.escape(str(alt_baslik))}</div>
                    </div>
                </div>
                <div class="action-cluster">
                    <a data-spa="1" href="{refresh_href}" target="_self" class="nav-pill-btn" title="Yenile">🔄</a>
                    <a data-spa="1" href="?action=logout" target="_self" class="nav-pill-btn" title="Çıkış">🚪</a>
                </div>
            </div>
            <div class="telemetry-bar">
                <div class="progress-track">
                    <div class="progress-fill" style="width:{ilerleme_yuzde}%;"></div>
                </div>
                <span class="telemetry-badge">%{ilerleme_yuzde} • {kalem_adet} KALEM</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

components.html(
    """
    <script>
    (function() {
        const doc = window.parent.document;
        const src = doc.getElementById('top-telemetry-source');
        const container = doc.querySelector('.block-container');
        if (!src || !container) return;
        let mount = doc.getElementById('top-telemetry-mount');
        if (!mount) {
            mount = doc.createElement('div');
            mount.id = 'top-telemetry-mount';
            container.insertBefore(mount, container.firstChild);
        }
        mount.innerHTML = src.innerHTML;
    })();
    </script>
    """,
    height=0,
    width=0
)

flash_msg = st.session_state.flash_mesaj
if flash_msg:
    st.markdown(
        f'<div class="smart-toast">✅ {html.escape(str(flash_msg))}</div>',
        unsafe_allow_html=True
    )
    st.session_state.flash_mesaj = None

# Sabit Alt Komut Konsolu
st.markdown('<div class="sticky-dock-anchor"></div>', unsafe_allow_html=True)
alt_kaydet, alt_temizle, alt_kapat = st.columns([2.2, 1.1, 1])
with alt_kaydet:
    kaydet_tiklandi = st.button("SİPARİŞİ KAYDET", key=f"btn_kaydet_{fv}", type="primary", use_container_width=True)
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




Gemini bir yapay zeka modeli olduğu için hata yapabilir.

