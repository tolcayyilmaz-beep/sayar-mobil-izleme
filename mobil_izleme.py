import os
import json
import time
import hmac
import html
import base64
import hashlib
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

# Railway ortam değişkeninden secrets.toml dosyasını sadece yoksa oluştur
if os.environ.get("STREAMLIT_SECRETS") and not os.path.exists(".streamlit/secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMLIT_SECRETS"])

NTFY_TOPIC = "sayar_yapi_kamyon_2026x"
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
LOGO_HTML = f'<img src="{LOGO_DATA_URI}" class="sy-logo-img" alt="Sayar Yapı">' if LOGO_DATA_URI else '<span class="sy-logo-fallback">SY</span>'

# Sayfa ve Mobil Görünüm Ayarları
st.set_page_config(
    page_title="SAYAR YAPI • Lojistik Komuta Merkezi",
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

# ==============================================================================
# MODERN KURUMSAL AYDINLIK TELEMETRİ & SABİT ÜST KOMUTA MERKEZİ TASARIMI (CSS)
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

:root {
    --bg-canvas: #eef2f6;
    --bg-surface: rgba(255, 255, 255, 0.94);
    --bg-surface-solid: #ffffff;
    --bg-elevated: #f8fafc;
    --border-subtle: rgba(15, 23, 42, 0.09);
    --border-strong: rgba(15, 23, 42, 0.16);
    --accent-primary: #ea580c;
    --accent-secondary: #0284c7;
    --accent-emerald: #059669;
    --accent-amber: #d97706;
    --accent-rose: #e11d48;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
}

/* Streamlit Varsayılan Chrome Gizleme */
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

/* Ana Tuval & Aydınlık Mimari Izgara Arka Planı */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-canvas) !important;
    background-image: 
        radial-gradient(circle at 12% 0%, rgba(249, 115, 22, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 88% 6%, rgba(2, 132, 199, 0.08) 0%, transparent 40%),
        linear-gradient(rgba(15, 23, 42, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(15, 23, 42, 0.03) 1px, transparent 1px) !important;
    background-size: 100% 100%, 100% 100%, 24px 24px, 24px 24px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.block-container {
    max-width: 960px !important;
    padding-top: 0.45rem !important;
    padding-bottom: 1.4rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
}

[data-testid="stVerticalBlock"] {
    gap: 0.4rem !important;
}

/* ============================================================================
   SABİT ÜST KOMUTA ALANI (HEADER + KPI + ARAMA ÇUBUĞU STICKY)
   ============================================================================ */
div[data-testid="stVerticalBlock"] > div:has(.sy-cmd-header),
div[data-testid="stVerticalBlock"] > div:has(.sy-kpi-grid),
div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stPopover"]) {
    position: sticky !important;
    z-index: 95 !important;
    background-color: var(--bg-canvas) !important;
}

div[data-testid="stVerticalBlock"] > div:has(.sy-cmd-header) {
    top: 0px !important;
    padding-top: 4px !important;
    z-index: 98 !important;
}

div[data-testid="stVerticalBlock"] > div:has(.sy-kpi-grid) {
    top: 66px !important;
    padding-top: 2px !important;
    padding-bottom: 2px !important;
    z-index: 97 !important;
}

div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stPopover"]) {
    top: 138px !important;
    padding-top: 2px !important;
    padding-bottom: 6px !important;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08) !important;
    box-shadow: 0 6px 14px -8px rgba(15, 23, 42, 0.14) !important;
    z-index: 96 !important;
}

/* Bildirim Toast Banner */
.auto-toast-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    background: linear-gradient(135deg, #ecfdf5 0%, #ffffff 100%);
    border: 1px solid #6ee7b7;
    border-left: 4px solid #059669;
    color: #064e3b;
    border-radius: 11px;
    padding: 8px 12px;
    font-size: 12.5px;
    font-weight: 700;
    margin-bottom: 4px;
    opacity: 1;
    transition: opacity 0.35s ease;
    box-shadow: 0 4px 14px rgba(5, 150, 105, 0.15);
}

/* Üst Komuta Başlığı (Aydınlık Modern Kurumsal Cam Panel) */
.sy-cmd-header {
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid var(--border-strong);
    border-radius: 14px;
    padding: 9px 12px;
    margin-bottom: 0px;
    box-shadow: 0 4px 16px -4px rgba(15, 23, 42, 0.08), inset 0 1px 0 #ffffff;
    overflow: hidden;
    gap: 10px;
}

.sy-cmd-header::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #f97316 0%, #0284c7 55%, #10b981 100%);
}

.sy-brand-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    flex: 1;
}

.sy-logo-box {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #fff7ed, #ffedd5);
    border: 1px solid rgba(249, 115, 22, 0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(249, 115, 22, 0.15);
}

.sy-logo-img {
    height: 24px;
    width: 24px;
    object-fit: contain;
    border-radius: 5px;
}

.sy-logo-fallback {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 800;
    font-size: 13.5px;
    color: #ea580c;
    letter-spacing: 0.5px;
}

.sy-title-col {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.sy-main-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 15px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: 0.2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2;
}

.sy-sub-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;
}

.sy-live-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #047857;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 999px;
    letter-spacing: 0.4px;
    flex-shrink: 0;
}

.sy-live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 6px #10b981;
    animation: syPulse 1.8s infinite;
}

@keyframes syPulse {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.8); }
    100% { opacity: 1; transform: scale(1); }
}

.sy-sub-text {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-header-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
}

.sy-cmd-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #334155 !important;
    text-decoration: none !important;
    transition: all 0.18s ease;
    cursor: pointer;
}

.sy-cmd-btn:hover {
    background: #fff7ed;
    border-color: #f97316;
    color: #ea580c !important;
    transform: translateY(-1px);
}

.sy-cmd-btn:active {
    transform: scale(0.95);
}

/* Telemetri KPI Kartları (Kompakt Aydınlık Tasarım) */
.sy-kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 2px;
    margin-bottom: 2px;
}

a.sy-kpi-card {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 7px 10px;
    text-decoration: none !important;
    transition: all 0.18s ease;
    overflow: hidden;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
}

a.sy-kpi-card:hover {
    transform: translateY(-1px);
    border-color: #94a3b8;
    background: #f8fafc;
}

a.sy-kpi-card:active {
    transform: scale(0.98);
}

.sy-kpi-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    margin-bottom: 2px;
}

.sy-kpi-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: #475569;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-kpi-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}

.sy-kpi-cyan .sy-kpi-dot { background: #0284c7; box-shadow: 0 0 6px rgba(2, 132, 199, 0.5); }
.sy-kpi-amber .sy-kpi-dot { background: #f97316; box-shadow: 0 0 6px rgba(249, 115, 22, 0.5); }
.sy-kpi-emerald .sy-kpi-dot { background: #10b981; box-shadow: 0 0 6px rgba(16, 185, 129, 0.5); }

.sy-kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 19px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.1;
    letter-spacing: -0.5px;
}

.sy-kpi-bar {
    height: 3px;
    width: 100%;
    border-radius: 999px;
    margin-top: 5px;
    background: #e2e8f0;
    overflow: hidden;
}

.sy-kpi-cyan .sy-kpi-bar-fill { height: 100%; width: 100%; background: linear-gradient(90deg, #0284c7, #38bdf8); }
.sy-kpi-amber .sy-kpi-bar-fill { height: 100%; width: 100%; background: linear-gradient(90deg, #ea580c, #fb923c); }
.sy-kpi-emerald .sy-kpi-bar-fill { height: 100%; width: 100%; background: linear-gradient(90deg, #059669, #34d399); }

/* Aktif Seçili KPI Kartı Vurgusu */
a.sy-kpi-card.sy-kpi-active {
    background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%) !important;
    border: 1.5px solid #f97316 !important;
    box-shadow: 0 4px 12px rgba(249, 115, 22, 0.18) !important;
}

a.sy-kpi-card.sy-kpi-active .sy-kpi-label {
    color: #c2410c !important;
}

/* Arama ve Filtre Çubuğu */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 7px !important;
    margin-top: 0px !important;
}

div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:first-child {
    flex: 1 1 auto !important;
    min-width: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:last-child {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 56px !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    color: #0f172a !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.18s ease !important;
}

div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {
    color: #94a3b8 !important;
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: #f97316 !important;
    box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.15) !important;
}

div[data-testid="stTextInput"] input {
    height: 38px !important;
    padding: 0 12px !important;
}

div[data-testid="stPopover"] > button {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    color: #0f172a !important;
    height: 38px !important;
    padding: 0 11px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.18s ease !important;
}

div[data-testid="stPopover"] > button:hover {
    border-color: #f97316 !important;
    background: #fff7ed !important;
    color: #ea580c !important;
}

/* Popover İçeriği Aydınlık Tema Uyumu */
div[data-testid="stPopoverBody"] {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 12px !important;
    color: #0f172a !important;
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.14) !important;
}

/* Login Formu Özel Tasarımı (Aydınlık) */
.sy-login-hero {
    background: linear-gradient(165deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #cbd5e1;
    border-top: 4px solid #f97316;
    border-radius: 16px;
    padding: 20px 16px;
    margin-top: 14px;
    margin-bottom: 10px;
    text-align: center;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
}

.sy-login-badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.9px;
    color: #c2410c;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    padding: 3px 10px;
    border-radius: 999px;
    margin-bottom: 10px;
}

.sy-login-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 20px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 4px;
}

.sy-login-sub {
    font-size: 12.5px;
    color: #475569;
}

div[data-testid="stForm"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
    padding: 16px !important;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06) !important;
}

/* Genel Butonlar */
button[kind="primary"] {
    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;
    border: 1px solid #ea580c !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    letter-spacing: 0.2px !important;
    box-shadow: 0 4px 12px rgba(249, 115, 22, 0.28) !important;
}

button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    color: #0f172a !important;
    font-weight: 600 !important;
}

button[kind="secondary"]:hover {
    border-color: #f97316 !important;
    color: #ea580c !important;
    background: #fff7ed !important;
}

/* Liste Sayacı Üst Satırı */
.sy-list-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 2px 4px 2px 4px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
}

.sy-list-meta strong {
    font-family: 'JetBrains Mono', monospace;
    color: #0f172a;
}

/* ============================================================================
   KAYDIRILABİLİR SEVKİYAT AKIŞI BÖLÜMÜ (ÜST YAPI SABİT, KARTLAR İÇERİDE KAYAR)
   ============================================================================ */
.sy-scroll-viewport {
    max-height: calc(100dvh - 215px);
    min-height: 260px;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 3px;
    padding-bottom: 6px;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-y: contain;
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
}

.sy-scroll-viewport::-webkit-scrollbar {
    width: 5px;
}

.sy-scroll-viewport::-webkit-scrollbar-track {
    background: transparent;
}

.sy-scroll-viewport::-webkit-scrollbar-thumb {
    background-color: #cbd5e1;
    border-radius: 999px;
}

/* ============================================================================
   KOMPAKT SİPARİŞ KARTLARI (YÜKSEKLİK DAHA İNCE VE SIKI)
   ============================================================================ */
.sip-list-container {
    display: flex;
    flex-direction: column;
    gap: 5px;
    width: 100%;
    margin: 0;
    padding: 0;
}

.sip-row-wrap {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: stretch;
    gap: 6px;
    width: 100%;
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

details.custom-sip-card {
    position: relative;
    flex: 1 1 auto;
    min-width: 0;
    margin: 0;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 4px solid var(--card-accent, #0284c7);
    border-radius: 10px;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
    overflow: hidden;
    box-sizing: border-box;
    transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

details.custom-sip-card[open] {
    border-color: #f97316;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.1);
}

details.custom-sip-card > summary {
    list-style: none;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 10px;
    cursor: pointer;
    user-select: none;
    height: 43px;
    min-height: 43px;
    box-sizing: border-box;
    transition: background-color 0.12s ease;
}

details.custom-sip-card > summary::-webkit-details-marker {
    display: none;
}

details.custom-sip-card > summary:hover {
    background-color: #f8fafc;
}

.custom-card-arrow {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    border-radius: 5px;
    background: #f1f5f9;
    font-size: 9.5px;
    color: #475569;
    font-weight: 800;
    transition: transform 0.18s ease, background-color 0.18s ease, color 0.18s ease;
    flex-shrink: 0;
}

details.custom-sip-card[open] .custom-card-arrow {
    transform: rotate(90deg);
    background: #fff7ed;
    color: #ea580c;
}

.custom-card-lines {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
}

.custom-card-line1 {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12.5px;
    font-weight: 700;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2;
}

.sy-sip-chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 700;
    padding: 0px 5px;
    border-radius: 4px;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #0f172a;
    flex-shrink: 0;
}

.sy-route-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.sy-route-arrow {
    color: #ea580c;
    font-weight: 800;
    margin: 0 2px;
}

.custom-card-line2 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    font-size: 11px;
    color: #475569;
    line-height: 1.15;
}

.sy-site-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-date-pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    color: #475569;
    background: #f1f5f9;
    padding: 0px 5px;
    border-radius: 4px;
    flex-shrink: 0;
}

/* Kart Açılır Gövde */
.custom-card-body {
    padding: 8px 10px 10px 10px;
    border-top: 1px solid #e2e8f0;
    background: #f8fafc;
}

/* Hızlı Onay İnceleme Butonu (Kartla Birebir Aynı Yükseklikte: 43px) */
a.mini-onay-btn {
    flex: 0 0 42px;
    width: 42px;
    height: 43px;
    min-height: 43px;
    max-height: 43px;
    box-sizing: border-box;
    background: linear-gradient(145deg, #f97316 0%, #ea580c 100%);
    border: 1px solid #ea580c;
    border-radius: 10px;
    color: #ffffff !important;
    font-size: 17px;
    font-weight: 900;
    text-decoration: none !important;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(249, 115, 22, 0.25);
    transition: all 0.15s ease;
}

a.mini-onay-btn:hover {
    background: #ea580c;
    transform: translateY(-1px);
}

a.mini-onay-btn:active {
    transform: scale(0.95);
}

/* Yönetici Tam Ekran Onay İnceleme Konsolu (Aydınlık) */
.fullscreen-review-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-top: 4px solid #f97316;
    border-radius: 14px;
    padding: 12px 12px 14px 12px;
    margin-top: 4px;
    margin-bottom: 10px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.1);
}

.fullscreen-review-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 8px;
    margin-bottom: 8px;
    gap: 8px;
}

.fullscreen-review-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: 0.2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

a.close-review-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    font-size: 13px;
    font-weight: 800;
    color: #475569 !important;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    text-decoration: none !important;
    flex-shrink: 0;
}

a.close-review-link:hover {
    background: #fee2e2;
    border-color: #ef4444;
    color: #b91c1c !important;
}

.onay-aksiyon-bar {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #e2e8f0;
    width: 100%;
    box-sizing: border-box;
}

a.aksiyon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 42px;
    border-radius: 10px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 12.5px;
    font-weight: 800;
    letter-spacing: 0.3px;
    text-decoration: none !important;
    box-sizing: border-box;
    padding: 0 6px;
    white-space: nowrap;
}

a.aksiyon-btn:active {
    transform: scale(0.97);
}

a.aksiyon-onayla {
    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
    border: 1px solid #15803d !important;
    color: #ffffff !important;
    box-shadow: 0 3px 10px rgba(22, 163, 74, 0.25);
}

a.aksiyon-revize {
    background: linear-gradient(135deg, #facc15 0%, #eab308 100%) !important;
    border: 1px solid #ca8a04 !important;
    color: #0f172a !important;
    box-shadow: 0 3px 10px rgba(234, 179, 8, 0.25);
}

a.aksiyon-reddet {
    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
    border: 1px solid #b91c1c !important;
    color: #ffffff !important;
    box-shadow: 0 3px 10px rgba(220, 38, 38, 0.25);
}

/* Detay Bilgi Izgarası (Data Cells - Aydınlık) */
.info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 5px 7px;
    font-size: 11.5px;
    margin-top: 6px;
    margin-bottom: 8px;
    padding: 7px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 9px;
}

.info-cell {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px 7px;
}

.info-item-label {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: #64748b;
    font-weight: 700;
    display: block;
    margin-bottom: 1px;
}

.info-item-val {
    font-weight: 600;
    color: #0f172a;
    word-break: break-word;
}

.info-item-val-red {
    font-weight: 800;
    color: #dc2626;
    word-break: break-word;
}

.info-item-val-navy {
    font-weight: 700;
    color: #1d4ed8;
    word-break: break-word;
}

/* Malzeme / Kalem Tablosu (Aydınlık) */
.urun-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin-top: 5px;
    font-size: 11.5px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
}

.urun-table th {
    background: #1e293b;
    color: #f8fafc;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    text-align: left;
    padding: 5px 8px;
    font-weight: 700;
    font-size: 10px;
}

.urun-table td {
    padding: 5px 8px;
    color: #0f172a;
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}

.urun-table tr:nth-child(even) td {
    background: #f8fafc;
}

.urun-table tr:last-child td {
    border-bottom: none;
}

.urun-miktar {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    color: #0284c7 !important;
    text-align: right;
    white-space: nowrap;
}

/* Operasyon Rozeti & Durum Etiketi */
.sy-status-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 6px;
    padding-bottom: 3px;
}

.badge {
    padding: 2px 8px;
    border-radius: 5px;
    color: #ffffff;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 0.3px;
    display: inline-flex;
    align-items: center;
}

.durum-plain {
    color: #334155;
    font-weight: 600;
    font-size: 11px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    padding: 2px 7px;
    border-radius: 5px;
}

/* Boş Durum (Empty State) */
.empty-state-box {
    background: #ffffff;
    border: 1px dashed #cbd5e1;
    border-radius: 14px;
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
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14.5px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 4px;
}

.empty-state-desc {
    font-size: 12px;
    color: #64748b;
}

/* Sayfalama & İlerleme Barı */
.pagination-box {
    margin-top: 10px;
    margin-bottom: 4px;
    text-align: center;
}

.pagination-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    color: #64748b;
    margin-bottom: 5px;
    font-weight: 600;
}

.progress-track {
    width: 100%;
    max-width: 240px;
    height: 5px;
    background-color: #e2e8f0;
    border-radius: 999px;
    margin: 0 auto 6px auto;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #0284c7 0%, #f97316 100%);
    border-radius: 999px;
    transition: width 0.3s ease;
}
</style>
""", unsafe_allow_html=True)


def md_temizle(metin):
    return str(metin or "-").replace("*", "").replace("_", " ").replace("`", "").strip()


def durum_metni_formatla(durum_val):
    metin = str(durum_val or "-").strip()
    if not metin or metin == "-":
        return "-"
    tr_upper = metin.replace("i", "İ").replace("ı", "I").upper()
    if tr_upper in ("SEVK EDİLDİ", "İPTAL", "İPTAL EDİLDİ"):
        return tr_upper
    return metin


def get_postgres_url() -> str:
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if env_url:
        return env_url.replace("postgres://", "postgresql://", 1)
    try:
        secret_url = str(st.secrets.get("DATABASE_URL") or st.secrets.get("RAILWAY_DATABASE_URL") or "").strip()
        if secret_url:
            return secret_url.replace("postgres://", "postgresql://", 1)
    except Exception:
        pass
    return RAILWAY_DEFAULT_DB_URL


def get_pg_connection():
    conn = psycopg2.connect(get_postgres_url(), connect_timeout=10)
    conn.autocommit = False
    return conn


def _imza_anahtari():
    if "DB_SECRET_KEY" in st.secrets and str(st.secrets["DB_SECRET_KEY"]).strip():
        return str(st.secrets["DB_SECRET_KEY"]).encode("utf-8")
    return str(st.secrets["APP_PASSWORD"]).encode("utf-8")


def onay_kararini_veritabanina_yaz(siparis_no: int, karar: str, aciklama: str = ""):
    """Yönetici onay/revize/red kararını doğrudan PostgreSQL siparisler tablosuna işler."""
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    not_ek = aciklama.strip()

    conn = get_pg_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT notlar FROM siparisler WHERE siparis_no = %s", (int(siparis_no),))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Sipariş #{siparis_no} veritabanında bulunamadı.")

            if not_ek:
                mevcut_not = str(row.get("notlar") or "").strip()
                etiket = f"[Mobil {karar} - {zaman}]: {not_ek}"
                yeni_not = f"{mevcut_not}\n{etiket}".strip() if mevcut_not else etiket
                cur.execute(
                    "UPDATE siparisler SET operasyon = %s, notlar = %s WHERE siparis_no = %s",
                    (karar, yeni_not, int(siparis_no))
                )
            else:
                cur.execute(
                    "UPDATE siparisler SET operasyon = %s WHERE siparis_no = %s",
                    (karar, int(siparis_no))
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def onay_ntfy_gonder(siparis_no: int, firma: str, musteri: str, karar: str, aciklama: str = ""):
    """Yönetici kararını ntfy kanalına anlık bildirim olarak gönderir."""
    try:
        ikon_tag = "white_check_mark" if karar == "ONAYLANDI" else ("warning" if karar == "REVİZE İSTENDİ" else "no_entry")
        baslik = f"Siparis #{siparis_no} - {karar}"
        mesaj_satirlar = [
            f"Karar: {karar}",
            f"Firma: {firma or '-'}",
            f"Musteri: {musteri or '-'}"
        ]
        if aciklama and aciklama.strip():
            mesaj_satirlar.append(f"Not: {aciklama.strip()}")

        mesaj = "\n".join(mesaj_satirlar)
        headers = {
            "Title": baslik.encode("utf-8").decode("latin-1", errors="ignore"),
            "Priority": "high",
            "Tags": ikon_tag
        }
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mesaj.encode("utf-8"),
            headers=headers,
            timeout=2
        )
    except Exception:
        pass


# Şifrelemesiz Oturum Jetonu (Beni Hatırla) Oluşturma ve Doğrulama
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
        st.session_state.onay_inceleme_sip_no = None
        st.query_params.clear()
        st.rerun()

    if not st.session_state.authenticated:
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
        rol_bilgi = "Kurumsal Sevkiyat & Sipariş İzleme Platformu"
        if url_musteri:
            rol_bilgi = f"Müşteri Erişim Portalı • {html.escape(url_musteri)}"
        elif url_veren:
            rol_bilgi = f"Personel Erişim Portalı • {html.escape(url_veren)}"

        st.markdown(
            f'<div class="sy-login-hero">'
            f'<div class="sy-login-badge">KURUMSAL LOJİSTİK PORTALI</div>'
            f'<div style="display:flex; justify-content:center; margin-bottom:10px;">'
            f'<div class="sy-logo-box" style="width:48px; height:48px; border-radius:14px;">{LOGO_HTML}</div>'
            f'</div>'
            f'<div class="sy-login-title">SAYAR YAPI</div>'
            f'<div class="sy-login-sub">{rol_bilgi}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        with st.form("login_form", clear_on_submit=False):
            pin = st.text_input("Erişim Şifresi:", type="password", placeholder="••••••••")
            beni_hatirla = st.checkbox("Bu cihazda oturumu açık tut (90 Gün)", value=True)
            giris_yapildi = st.form_submit_button("Sisteme Bağlan", use_container_width=True, type="primary")

        if giris_yapildi:
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
                st.error("Erişim reddedildi: Hatalı güvenlik şifresi.")
        st.stop()


check_password()

# Session State Varsayılanları
if "kpi_mod" not in st.session_state:
    st.session_state.kpi_mod = "SEVK"
if "sayfa_limiti" not in st.session_state:
    st.session_state.sayfa_limiti = 50
if "arama_metni" not in st.session_state:
    st.session_state.arama_metni = ""
if "onay_inceleme_sip_no" not in st.session_state:
    st.session_state.onay_inceleme_sip_no = None
if "bekleyen_revize_sip_no" not in st.session_state:
    st.session_state.bekleyen_revize_sip_no = None
if "yerel_kararlar" not in st.session_state:
    st.session_state.yerel_kararlar = {}
if "flash_mesaj" not in st.session_state:
    st.session_state.flash_mesaj = None


def filtreleri_sifirla():
    st.session_state.kpi_mod = "SEVK"
    st.session_state.arama_metni = ""
    st.session_state.f_op = "[TÜMÜ]"
    st.session_state.f_firma = "[TÜMÜ]"
    st.session_state.f_musteri = "[TÜMÜ]"
    st.session_state.f_gizle_muh = True
    st.session_state.f_gizle_ipt = True
    st.session_state.sayfa_limiti = 50


if st.query_params.get("action") == "refresh":
    st.cache_data.clear()
    st.session_state.sayfa_limiti = 50
    st.query_params.pop("action", None)
    st.rerun()

if "incele" in st.query_params:
    incele_val = st.query_params.get("incele", "").strip()
    if incele_val.isdigit():
        st.session_state.onay_inceleme_sip_no = int(incele_val)
    st.query_params.pop("incele", None)

if "incele_kapat" in st.query_params:
    st.session_state.onay_inceleme_sip_no = None
    st.session_state.bekleyen_revize_sip_no = None
    st.query_params.pop("incele_kapat", None)
    st.query_params.pop("karar", None)
    st.rerun()

bekleyen_karar_param = st.query_params.get("karar", "").strip().upper()
if bekleyen_karar_param:
    st.query_params.pop("karar", None)

if "kpi" in st.query_params:
    secilen_kpi = st.query_params.get("kpi", "").upper()
    if secilen_kpi in ("TAMAMLANDI", "ONAY", "SEVK"):
        if st.session_state.kpi_mod == secilen_kpi and secilen_kpi != "SEVK":
            st.session_state.kpi_mod = "SEVK"
        else:
            st.session_state.kpi_mod = secilen_kpi

        if st.session_state.kpi_mod == "ONAY":
            st.session_state.f_op = "ONAY BEKLİYOR"
        elif st.session_state.kpi_mod == "TAMAMLANDI":
            st.session_state.f_op = "TAMAMLANDI"
        else:
            st.session_state.f_op = "[TÜMÜ]"

        st.session_state.f_gizle_muh = (st.session_state.kpi_mod == "SEVK")
        st.session_state.f_gizle_ipt = (st.session_state.kpi_mod == "SEVK")
        st.session_state.sayfa_limiti = 50
        st.session_state.onay_inceleme_sip_no = None
    st.query_params.pop("kpi", None)
    st.rerun()

yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger
aktif_token = st.session_state.get("active_token") or st.query_params.get("token", "")
inceleme_aktif_mi = (yetki_tipi == "YONETICI" and st.session_state.get("onay_inceleme_sip_no") is not None)


# 2. Railway PostgreSQL'den doğrudan veri okuma (15 sn önbellekli)
@st.cache_data(ttl=15, show_spinner=False)
def verileri_getir():
    conn = get_pg_connection()
    try:
        df_siparisler = pd.read_sql_query(
            "SELECT * FROM siparisler ORDER BY siparis_no DESC", conn
        )
        df_kalemler = pd.read_sql_query(
            "SELECT * FROM siparis_kalemleri ORDER BY id ASC", conn
        )
    finally:
        conn.close()

    return df_siparisler, df_kalemler


token_param = f"&token={aktif_token}" if aktif_token else ""
refresh_href = f"?action=refresh{token_param}"

# İnceleme modunda en üstteki SAYAR YAPI + yenile/çıkış barı kaldırılır
if not inceleme_aktif_mi:
    if yetki_tipi == "MUSTERI":
        baslik_metni = f'SAYAR YAPI • {html.escape(str(yetki_deger))}'
        alt_metin = "Müşteri Sevkiyat İzleme"
    elif yetki_tipi == "SIPARIS_VEREN":
        baslik_metni = f'SAYAR YAPI • {html.escape(str(yetki_deger))}'
        alt_metin = "Saha & Personel Takibi"
    else:
        baslik_metni = 'SAYAR YAPI'
        alt_metin = "Lojistik Komuta Merkezi"

    svg_refresh = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>'
    svg_logout = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>'

    st.markdown(
        f'<div class="sy-cmd-header">'
        f'<div class="sy-brand-wrap">'
        f'<div class="sy-logo-box">{LOGO_HTML}</div>'
        f'<div class="sy-title-col">'
        f'<div class="sy-main-title">{baslik_metni}</div>'
        f'<div class="sy-sub-row">'
        f'<span class="sy-live-pill"><span class="sy-live-dot"></span>CANLI</span>'
        f'<span class="sy-sub-text">{alt_metin}</span>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div class="sy-header-actions">'
        f'<a data-spa="1" href="{refresh_href}" target="_self" class="sy-cmd-btn" title="Verileri Yenile">{svg_refresh}</a>'
        f'<a data-spa="1" href="?action=logout" target="_self" class="sy-cmd-btn" title="Güvenli Çıkış">{svg_logout}</a>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

try:
    df_sip, df_kalem = verileri_getir()
except Exception as e:
    st.error(f"PostgreSQL veritabanı okunamadı. Bağlantıyı kontrol edin.\nDetay: {e}")
    st.stop()

# Mobil oturumda verilen kararları güncel veri gelene kadar anlık yansıt
if st.session_state.yerel_kararlar and not df_sip.empty:
    df_sip = df_sip.copy()
    for s_no, karar_bilgi in list(st.session_state.yerel_kararlar.items()):
        mask = df_sip["siparis_no"] == int(s_no)
        if mask.any():
            db_op = str(df_sip.loc[mask, "operasyon"].iloc[0] or "").upper()
            if db_op == "ONAY BEKLİYOR":
                df_sip.loc[mask, "operasyon"] = karar_bilgi["karar"]
                if karar_bilgi.get("not"):
                    mevcut_not = str(df_sip.loc[mask, "notlar"].iloc[0] or "").strip()
                    ek_not = f"[Mobil {karar_bilgi['karar']}]: {karar_bilgi['not']}"
                    df_sip.loc[mask, "notlar"] = f"{mevcut_not}\n{ek_not}".strip() if mevcut_not else ek_not
            else:
                st.session_state.yerel_kararlar.pop(s_no, None)

# Yetki Tipine Göre Veriyi Kısıtlama
if yetki_tipi == "MUSTERI":
    df_sip = df_sip[df_sip["musteri"].fillna("").str.strip().str.upper() == yetki_deger.strip().upper()]
elif yetki_tipi == "SIPARIS_VEREN":
    df_sip = df_sip[df_sip["siparis_veren"].fillna("").str.strip().str.upper() == yetki_deger.strip().upper()]

OP_RENK = {
    "İŞLENDİ": "#0284c7",
    "ONAY BEKLİYOR": "#f97316",
    "ONAYLANDI": "#10b981",
    "REVİZE İSTENDİ": "#f59e0b",
    "REDDEDİLDİ": "#e11d48",
    "TAMAMLANDI": "#10b981",
    "MUHASEBEYE İLETİLDİ": "#10b981",
    "İPTAL EDİLDİ": "#e11d48",
    "KISMİ EVRAK": "#7c3aed"
}

OP_IKON = {
    "İŞLENDİ": "🔵",
    "ONAY BEKLİYOR": "🟠",
    "ONAYLANDI": "🟢",
    "REVİZE İSTENDİ": "🟡",
    "REDDEDİLDİ": "⛔",
    "TAMAMLANDI": "✅",
    "MUHASEBEYE İLETİLDİ": "✅",
    "İPTAL EDİLDİ": "🔴",
    "KISMİ EVRAK": "🟣"
}

ETIKET_MAP = {
    "tarih": "Sipariş Tarihi",
    "sevk_tarihi": "Sevk Tarihi",
    "firma": "Tedarikçi Firma",
    "musteri": "Müşteri",
    "santiye": "Şantiye",
    "sehir": "Şehir",
    "fabrika": "Fabrika",
    "nakliye": "Nakliye",
    "yetkili": "Yetkili",
    "telefon": "Telefon",
    "arac": "Araç",
    "ted_sip_no": "Ted.Sip.No",
    "siparis_veren": "Sipariş Veren",
    "plaka": "Plaka",
    "notlar": "Not",
    "nakliye_fatura": "Nakliye Fatura",
    "firma_yetkili": "Firma Yetkili",
    "siparis_gecen": "Sipariş Geçen"
}

oncelik = [
    "tarih",
    "sevk_tarihi",
    "firma",
    "musteri",
    "santiye",
    "sehir",
    "fabrika",
    "nakliye",
    "yetkili",
    "telefon",
    "arac",
    "ted_sip_no",
    "siparis_veren",
    "plaka",
    "notlar"
]

kalem_gruplari = dict(tuple(df_kalem.groupby("siparis_no"))) if not df_kalem.empty else {}


def siparis_detay_html_olustur(row, sip_no, vurgulu_onay=False):
    op_val = str(row.get("operasyon") or "-")
    op_upper = op_val.upper()
    renk = OP_RENK.get(op_upper, "#64748b")
    durum_gosterim = html.escape(durum_metni_formatla(row.get("durum")))

    haric_sutunlar = {
        "id", "siparis_no", "operasyon", "durum",
        "nakliye_fatura", "firma_yetkili", "siparis_gecen",
        "musteri" if yetki_tipi == "MUSTERI" else ""
    }
    if vurgulu_onay:
        haric_sutunlar.update({"yetkili", "telefon", "plaka"})

    kirmizi_alanlar = {"firma", "musteri", "nakliye"}
    lacivert_alanlar = {"notlar"}

    sirali_sutunlar = [c for c in oncelik if c in row.index] + [c for c in row.index if c not in oncelik]
    grid_items_html = ""
    for col_name in sirali_sutunlar:
        col_lower = col_name.lower()
        if col_lower in haric_sutunlar:
            continue
        val = row.get(col_name)
        bos_mu = pd.isna(val) or str(val).strip() in ("", "None", "nan")

        etiket = ETIKET_MAP.get(col_lower, col_name.replace("_", " ").title())
        deger_str = "-" if bos_mu else html.escape(str(val).strip())

        if vurgulu_onay and col_lower in kirmizi_alanlar:
            val_cls = "info-item-val-red"
        elif vurgulu_onay and col_lower in lacivert_alanlar:
            val_cls = "info-item-val-navy"
        else:
            val_cls = "info-item-val"

        span_style = ' style="grid-column: span 2;"' if col_lower == "notlar" or len(deger_str) > 35 else ""
        grid_items_html += (
            f'<div class="info-cell"{span_style}>'
            f'<span class="info-item-label">{html.escape(etiket)}</span>'
            f'<span class="{val_cls}">{deger_str}</span>'
            f'</div>'
        )

    grid_html = f'<div class="info-grid">{grid_items_html}</div>' if grid_items_html else ""

    tablo_html = ""
    kalemler = kalem_gruplari.get(sip_no)
    if kalemler is not None and not kalemler.empty:
        olasi_ad = ["urun", "urun_adi", "malzeme", "malzeme_adi", "stok_adi", "kalem", "aciklama", "cinsi"]
        ad_sutunu = next((c for c in olasi_ad if c in kalemler.columns), None)

        olasi_miktar = ["miktar", "adet", "siparis_miktari", "siparis_adet", "tonaj", "kilo", "metraj", "miktari"]
        miktar_sutunu = next((c for c in olasi_miktar if c in kalemler.columns), None)

        olasi_birim = ["birim", "birimi", "olcu_birimi"]
        birim_sutunu = next((c for c in olasi_birim if c in kalemler.columns), None)

        haric = {"id", "siparis_no", ad_sutunu, miktar_sutunu, birim_sutunu}
        kalan_sutunlar = [c for c in kalemler.columns if c not in haric]

        if ad_sutunu is None and kalan_sutunlar:
            ad_sutunu = kalan_sutunlar.pop(0)
        if miktar_sutunu is None and kalan_sutunlar:
            miktar_sutunu = kalan_sutunlar.pop(0)

        satirlar_html = ""
        for _, k_row in kalemler.iterrows():
            urun_adi = html.escape(str(k_row.get(ad_sutunu) or "-")) if ad_sutunu else "-"
            miktar_val = k_row.get(miktar_sutunu) if miktar_sutunu else "-"
            if isinstance(miktar_val, float) and miktar_val.is_integer():
                miktar_val = int(miktar_val)
            miktar_str = html.escape(str(miktar_val if pd.notna(miktar_val) and str(miktar_val).strip() != "" else "-"))
            birim_str = html.escape(str(k_row.get(birim_sutunu) or "-")) if birim_sutunu else "-"

            satirlar_html += (
                f"<tr>"
                f"<td>{urun_adi}</td>"
                f"<td style='text-align:left; white-space:nowrap; color:#475569; font-weight:600;'>{birim_str}</td>"
                f"<td class='urun-miktar'>{miktar_str}</td>"
                f"</tr>"
            )

        tablo_html = (
            f"<table class='urun-table'>"
            f"<thead><tr>"
            f"<th>Malzeme / Ürün</th>"
            f"<th style='text-align:left;'>Birim</th>"
            f"<th style='text-align:right;'>Miktar</th>"
            f"</tr></thead>"
            f"<tbody>{satirlar_html}</tbody>"
            f"</table>"
        )

    rozet_html = (
        f"<div class='sy-status-strip'>"
        f"<span class='badge' style='background-color:{renk};'>{html.escape(op_val)}</span>"
        f"<span class='durum-plain'>Durum: {durum_gosterim}</span>"
        f"</div>"
    )
    return rozet_html, grid_html, tablo_html


def karari_uygula(sip_no: int, row_data, karar: str, aciklama: str = ""):
    """Kararı doğrudan PostgreSQL'e yazar, önbelleği yeniler ve listeye döner."""
    try:
        onay_kararini_veritabanina_yaz(sip_no, karar, aciklama)
        onay_ntfy_gonder(
            siparis_no=sip_no,
            firma=str(row_data.get("firma") or "-"),
            musteri=str(row_data.get("musteri") or "-"),
            karar=karar,
            aciklama=aciklama
        )
        st.session_state.yerel_kararlar[int(sip_no)] = {
            "karar": karar,
            "not": aciklama.strip()
        }
        st.cache_data.clear()
        st.session_state.onay_inceleme_sip_no = None
        st.session_state.bekleyen_revize_sip_no = None
        st.session_state.flash_mesaj = f"Sipariş #{sip_no} {karar} kararı kaydedildi."
        st.rerun()
    except Exception as err:
        st.error(f"Karar PostgreSQL'e yazılamadı: {err}")


@st.dialog("Revize Notu")
def revize_not_penceresi(sip_no: int, row_data):
    st.caption(f"Sipariş #{sip_no} için revize açıklaması giriniz:")
    revize_aciklama = st.text_area(
        "Revize Açıklaması",
        placeholder="Örn: Fiyat kontrol edilsin veya araç bilgisi güncellensin...",
        height=100,
        label_visibility="collapsed"
    )
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("Gönder", type="primary", use_container_width=True):
            if not revize_aciklama.strip():
                st.warning("Lütfen kısa bir revize açıklaması yazınız.")
            else:
                karari_uygula(sip_no, row_data, "REVİZE İSTENDİ", revize_aciklama)
    with col_r2:
        if st.button("İptal", use_container_width=True):
            st.session_state.bekleyen_revize_sip_no = None
            st.rerun()


# ==============================================================================
# YÖNETİCİ TAM EKRAN ONAY İNCELEME MODU
# ==============================================================================
aktif_inceleme_no = st.session_state.get("onay_inceleme_sip_no")
if inceleme_aktif_mi and aktif_inceleme_no is not None:
    secili_df = df_sip[df_sip["siparis_no"] == aktif_inceleme_no]
    if secili_df.empty:
        st.session_state.onay_inceleme_sip_no = None
        st.rerun()

    inceleme_row = secili_df.iloc[0]

    if bekleyen_karar_param == "ONAYLA":
        karari_uygula(aktif_inceleme_no, inceleme_row, "ONAYLANDI", "")
    elif bekleyen_karar_param == "REDDET":
        karari_uygula(aktif_inceleme_no, inceleme_row, "REDDEDİLDİ", "")
    elif bekleyen_karar_param == "REVIZE":
        st.session_state.bekleyen_revize_sip_no = int(aktif_inceleme_no)

    rozet_html, grid_html, tablo_html = siparis_detay_html_olustur(inceleme_row, aktif_inceleme_no, vurgulu_onay=True)

    base_incele_href = f"?incele={aktif_inceleme_no}{token_param}"
    onayla_href = f"{base_incele_href}&karar=ONAYLA"
    revize_href = f"{base_incele_href}&karar=REVIZE"
    reddet_href = f"{base_incele_href}&karar=REDDET"

    st.markdown(
        f'<div class="fullscreen-review-card">'
        f'<div class="fullscreen-review-header">'
        f'<div class="fullscreen-review-title">⚡ YÖNETİCİ ONAY KONSOLU • #{html.escape(str(aktif_inceleme_no))}</div>'
        f'<a data-spa="1" href="?incele_kapat=1{token_param}" target="_self" class="close-review-link" title="Kapat">✕</a>'
        f'</div>'
        f'{rozet_html}'
        f'{grid_html}'
        f'{tablo_html}'
        f'<div class="onay-aksiyon-bar">'
        f'<a data-spa="1" href="{onayla_href}" target="_self" class="aksiyon-btn aksiyon-onayla">✓ ONAYLA</a>'
        f'<a data-spa="1" href="{revize_href}" target="_self" class="aksiyon-btn aksiyon-revize">↻ REVİZE</a>'
        f'<a data-spa="1" href="{reddet_href}" target="_self" class="aksiyon-btn aksiyon-reddet">✕ REDDET</a>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if st.session_state.get("bekleyen_revize_sip_no") == int(aktif_inceleme_no):
        revize_not_penceresi(aktif_inceleme_no, inceleme_row)

    st.stop()

# ==============================================================================
# ANA LİSTE VE TELEMETRİ KPI GÖRÜNÜMÜ (ÜST YAPI SABİT, ALTTA AKIŞ KAYAR)
# ==============================================================================
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
            }}, 2500);
        }})();
        </script>
        """,
        height=0,
        width=0
    )
    st.session_state.flash_mesaj = None

tamamlandi_siparis = len(df_sip[df_sip["operasyon"].isin(["TAMAMLANDI", "MUHASEBEYE İLETİLDİ"])])
onay_bekleyen = len(df_sip[df_sip["operasyon"] == "ONAY BEKLİYOR"])
sevk_bekleyen = len(
    df_sip[
        (~df_sip["operasyon"].isin(["TAMAMLANDI", "MUHASEBEYE İLETİLDİ", "İPTAL EDİLDİ"])) &
        (df_sip["durum"].fillna("").str.replace("i", "İ").str.upper() != "İPTAL")
    ]
)

kpi_mod = st.session_state.kpi_mod
cls_tamamlandi = "sy-kpi-active" if kpi_mod == "TAMAMLANDI" else ""
cls_onay = "sy-kpi-active" if kpi_mod == "ONAY" else ""
cls_sevk = "sy-kpi-active" if kpi_mod == "SEVK" else ""

st.markdown(
    f'<div class="sy-kpi-grid">'
    f'<a data-spa="1" href="?kpi=TAMAMLANDI{token_param}" target="_self" class="sy-kpi-card sy-kpi-cyan {cls_tamamlandi}" title="Sadece tamamlanan siparişleri göster">'
    f'<div class="sy-kpi-top"><span class="sy-kpi-label">Tamamlandı</span><span class="sy-kpi-dot"></span></div>'
    f'<div class="sy-kpi-value">{tamamlandi_siparis}</div>'
    f'<div class="sy-kpi-bar"><div class="sy-kpi-bar-fill"></div></div>'
    f'</a>'
    f'<a data-spa="1" href="?kpi=ONAY{token_param}" target="_self" class="sy-kpi-card sy-kpi-amber {cls_onay}" title="Sadece onay bekleyenleri göster">'
    f'<div class="sy-kpi-top"><span class="sy-kpi-label">Onay Bekleyen</span><span class="sy-kpi-dot"></span></div>'
    f'<div class="sy-kpi-value">{onay_bekleyen}</div>'
    f'<div class="sy-kpi-bar"><div class="sy-kpi-bar-fill"></div></div>'
    f'</a>'
    f'<a data-spa="1" href="?kpi=SEVK{token_param}" target="_self" class="sy-kpi-card sy-kpi-emerald {cls_sevk}" title="Sadece devam edenleri göster">'
    f'<div class="sy-kpi-top"><span class="sy-kpi-label">Sevk Bekleyen</span><span class="sy-kpi-dot"></span></div>'
    f'<div class="sy-kpi-value">{sevk_bekleyen}</div>'
    f'<div class="sy-kpi-bar"><div class="sy-kpi-bar-fill"></div></div>'
    f'</a>'
    f'</div>',
    unsafe_allow_html=True
)

op_listesi = ["[TÜMÜ]"] + sorted(df_sip["operasyon"].dropna().unique().tolist())
firma_listesi = ["[TÜMÜ]"] + sorted(df_sip["firma"].dropna().unique().tolist())
musteri_listesi = ["[TÜMÜ]"] + sorted(df_sip["musteri"].dropna().unique().tolist())

if "f_op" not in st.session_state:
    if kpi_mod == "ONAY":
        st.session_state.f_op = "ONAY BEKLİYOR"
    elif kpi_mod == "TAMAMLANDI":
        st.session_state.f_op = "TAMAMLANDI"
    else:
        st.session_state.f_op = "[TÜMÜ]"
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
popover_etiket = "🎛️ •" if ek_filtre_aktif else "🎛️"

col_arama, col_filtre = st.columns([5, 1])
with col_arama:
    arama = st.text_input(
        "Arama",
        key="arama_metni",
        placeholder="🔍 Sipariş No, Tedarikçi, Müşteri veya Şantiye ara...",
        label_visibility="collapsed"
    )

with col_filtre:
    with st.popover(popover_etiket, use_container_width=True):
        st.markdown("**Gelişmiş Parametre Filtresi**")
        secili_op = st.selectbox("Operasyon", op_listesi, key="f_op")
        secili_firma = st.selectbox("Tedarikçi Firma", firma_listesi, key="f_firma")

        if yetki_tipi != "MUSTERI":
            secili_musteri = st.selectbox("Müşteri", musteri_listesi, key="f_musteri")
        else:
            secili_musteri = "[TÜMÜ]"

        gizle_tamamlanan = st.checkbox("Tamamlananları Gizle", key="f_gizle_muh")
        gizle_iptal = st.checkbox("İptal Edilenleri Gizle", key="f_gizle_ipt")

        if ek_filtre_aktif or arama.strip():
            st.button("Filtreleri Sıfırla", on_click=filtreleri_sifirla, use_container_width=True)

filtered = df_sip

if gizle_tamamlanan:
    filtered = filtered[~filtered["operasyon"].isin(["TAMAMLANDI", "MUHASEBEYE İLETİLDİ"])]
if gizle_iptal:
    filtered = filtered[
        (filtered["operasyon"] != "İPTAL EDİLDİ") &
        (filtered["durum"].fillna("").str.replace("i", "İ").str.upper() != "İPTAL")
    ]
if secili_op != "[TÜMÜ]":
    if secili_op == "TAMAMLANDI":
        filtered = filtered[filtered["operasyon"].isin(["TAMAMLANDI", "MUHASEBEYE İLETİLDİ"])]
    else:
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

if toplam_filtrelenen == 0:
    st.markdown(
        '<div class="empty-state-box">'
        '<div class="empty-state-icon">📡</div>'
        '<div class="empty-state-title">Kayıtlı Sevkiyat Bulunamadı</div>'
        '<div class="empty-state-desc">Arama sorgunuzu güncelleyebilir veya aktif filtre parametrelerini sıfırlayabilirsiniz.</div>'
        '</div>',
        unsafe_allow_html=True
    )
    col_e1, col_e2, col_e3 = st.columns([1, 2, 1])
    with col_e2:
        st.button("🔄 Tüm Filtreleri Temizle", on_click=filtreleri_sifirla, use_container_width=True, type="primary")
else:
    st.markdown(
        f'<div class="sy-list-meta">'
        f'<span>SEVKİYAT AKIŞI</span>'
        f'<span>Gösterilen: <strong>{gosterilen_adet}</strong> / <strong>{toplam_filtrelenen}</strong></span>'
        f'</div>',
        unsafe_allow_html=True
    )

    kart_parcalari = ['<div class="sy-scroll-viewport"><div class="sip-list-container">']
    for _, row in filtered.head(gosterilen_limit).iterrows():
        sip_no = row.get("siparis_no", "-")
        op_val = str(row.get("operasyon") or "-")
        op_upper = op_val.upper()
        durum_ikon = OP_IKON.get(op_upper, "⚪")
        kart_accent = OP_RENK.get(op_upper, "#0284c7")

        firma_str = row.get("firma") or "-"
        musteri_str = row.get("musteri") or "-"
        santiye_str = row.get("santiye") or "-"
        tarih_str = row.get("tarih") or "-"

        f_md = md_temizle(firma_str)
        m_md = md_temizle(musteri_str)
        s_md = md_temizle(santiye_str)
        t_md = md_temizle(tarih_str)

        rozet_html, grid_html, tablo_html = siparis_detay_html_olustur(row, sip_no)

        if yetki_tipi == "MUSTERI":
            satir1_html = (
                f'<span class="sy-sip-chip">{durum_ikon} #{html.escape(str(sip_no))}</span>'
                f'<span class="sy-route-text">{html.escape(f_md)}</span>'
            )
        else:
            satir1_html = (
                f'<span class="sy-sip-chip">{durum_ikon} #{html.escape(str(sip_no))}</span>'
                f'<span class="sy-route-text">{html.escape(f_md)} <span class="sy-route-arrow">➔</span> {html.escape(m_md)}</span>'
            )
        satir2_html = (
            f'<span class="sy-site-text">📍 {html.escape(s_md)}</span>'
            f'<span class="sy-date-pill">{html.escape(t_md)}</span>'
        )

        onay_buton_html = ""
        if yetki_tipi == "YONETICI" and op_upper == "ONAY BEKLİYOR":
            onay_buton_html = f'<a data-spa="1" href="?incele={sip_no}{token_param}" target="_self" class="mini-onay-btn" title="Siparişi İncele">✓</a>'

        kart_parcalari.append(
            f'<div class="sip-row-wrap">'
            f'<details class="custom-sip-card" style="--card-accent:{kart_accent};">'
            f'<summary>'
            f'<span class="custom-card-arrow">❯</span>'
            f'<div class="custom-card-lines">'
            f'<div class="custom-card-line1">{satir1_html}</div>'
            f'<div class="custom-card-line2">{satir2_html}</div>'
            f'</div>'
            f'</summary>'
            f'<div class="custom-card-body">{rozet_html}{grid_html}{tablo_html}</div>'
            f'</details>'
            f'{onay_buton_html}'
            f'</div>'
        )

    kart_parcalari.append('</div></div>')
    st.markdown("".join(kart_parcalari), unsafe_allow_html=True)

    yuzde = int((gosterilen_adet / toplam_filtrelenen) * 100) if toplam_filtrelenen > 0 else 100
    st.markdown(
        f'<div class="pagination-box">'
        f'<div class="pagination-text">{toplam_filtrelenen} KAYITTAN {gosterilen_adet} TANESİ LİSTELENDİ (%{yuzde})</div>'
        f'<div class="progress-track"><div class="progress-fill" style="width:{yuzde}%;"></div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if gosterilen_adet < toplam_filtrelenen:
        kalan = toplam_filtrelenen - gosterilen_adet
        eklenecek = min(50, kalan)
        if st.button(f"Daha Fazla Kayıt Yükle (+{eklenecek})", use_container_width=True):
            st.session_state.sayfa_limiti += 50
            st.rerun()
