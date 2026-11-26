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
LOGO_HTML = f'<img src="{LOGO_DATA_URI}" class="sy-brand-logo" alt="Sayar Yapı">' if LOGO_DATA_URI else '<span class="sy-brand-mark">SY</span>'

# Sayfa ve Mobil Görünüm Ayarları
st.set_page_config(
    page_title="Sayar Yapı | Saha & Sevkiyat Merkezi",
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
# YENİ NESİL SAHA LOJİSTİK & KOMUTA MERKEZİ ARAYÜZÜ (MODERN BENTO & CARD UI)
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@600;700;800&display=swap');

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

:root {
    --bg-app: #f3f5f8;
    --bg-card: #ffffff;
    --bg-soft: #f8fafc;
    --ink-main: #0f172a;
    --ink-sub: #475569;
    --ink-mute: #64748b;
    --border-light: #e2e8f0;
    --border-mid: #cbd5e1;
    --brand-navy: #0c192c;
    --brand-orange: #f97316;
    --brand-orange-dark: #ea580c;
    --brand-orange-bg: #fff7ed;
    --shadow-card: 0 4px 14px -2px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
    --shadow-float: 0 12px 28px -6px rgba(15, 23, 42, 0.14);
}

.stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-app) !important;
    color: var(--ink-main) !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.block-container {
    max-width: 760px !important;
    margin: 0 auto !important;
    padding-top: 0.6rem !important;
    padding-bottom: 5.5rem !important;
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
}

[data-testid="stVerticalBlock"] {
    gap: 0.5rem !important;
}

/* Bildirim Toast */
.sy-toast {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #064e3b;
    color: #ecfdf5;
    border-radius: 14px;
    padding: 11px 14px;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 8px;
    box-shadow: var(--shadow-float);
    transition: opacity 0.35s ease;
}

/* Üst Komuta Kartı */
.sy-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(135deg, #091322 0%, #132540 55%, #1e3a5f 100%);
    border-radius: 18px;
    padding: 12px 14px;
    color: #ffffff;
    box-shadow: 0 10px 24px -8px rgba(9, 19, 34, 0.45);
    margin-bottom: 10px;
    position: relative;
    overflow: hidden;
}

.sy-topbar::after {
    content: "";
    position: absolute;
    right: -25px;
    top: -35px;
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(249, 115, 22, 0.28) 0%, transparent 70%);
    pointer-events: none;
}

.sy-top-left {
    display: flex;
    align-items: center;
    gap: 11px;
    min-width: 0;
    flex: 1;
}

.sy-brand-logo {
    height: 36px;
    width: 36px;
    object-fit: contain;
    border-radius: 10px;
    background: #ffffff;
    padding: 3px;
    flex-shrink: 0;
}

.sy-brand-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #f97316, #ea580c);
    color: #ffffff;
    font-weight: 800;
    font-size: 14px;
    letter-spacing: 0.04em;
    flex-shrink: 0;
}

.sy-top-titles {
    min-width: 0;
    flex: 1;
}

.sy-top-role {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #fdba74;
    margin-bottom: 1px;
}

.sy-top-name {
    font-size: 15.5px;
    font-weight: 800;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    letter-spacing: -0.01em;
}

.sy-top-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    z-index: 1;
}

.sy-circle-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.11);
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: #ffffff !important;
    text-decoration: none !important;
    transition: all 0.15s ease;
}

.sy-circle-btn:hover {
    background: rgba(255, 255, 255, 0.2);
}

.sy-circle-btn:active {
    transform: scale(0.94);
    background: var(--brand-orange);
}

/* Segmented Durum Sekmeleri (Bento Switcher) */
.sy-segment-wrap {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 10px;
}

a.sy-seg-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: space-between;
    background: var(--bg-card);
    border: 1.5px solid var(--border-light);
    border-radius: 15px;
    padding: 10px 11px;
    text-decoration: none !important;
    box-shadow: var(--shadow-card);
    transition: all 0.16s ease;
    position: relative;
}

a.sy-seg-card:hover {
    border-color: var(--border-mid);
    transform: translateY(-1px);
}

a.sy-seg-card.active {
    background: #0f172a;
    border-color: #0f172a;
    box-shadow: 0 8px 20px -6px rgba(15, 23, 42, 0.35);
}

.sy-seg-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    margin-bottom: 6px;
}

.sy-seg-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
}

.dot-green { background: #10b981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.18); }
.dot-orange { background: #f97316; box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.2); }
.dot-blue { background: #0ea5e9; box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.18); }

.sy-seg-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 800;
    color: var(--ink-main);
    line-height: 1;
}

a.sy-seg-card.active .sy-seg-num {
    color: #ffffff;
}

.sy-seg-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--ink-sub);
    letter-spacing: -0.01em;
    white-space: nowrap;
}

a.sy-seg-card.active .sy-seg-label {
    color: #cbd5e1;
}

/* Arama ve Filtre Çubuğu */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 8px !important;
    margin-bottom: 6px !important;
}

div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:first-child {
    flex: 1 1 auto !important;
    min-width: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:last-child {
    flex: 0 0 auto !important;
    width: auto !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background-color: var(--bg-card) !important;
    border: 1.5px solid var(--border-light) !important;
    border-radius: 13px !important;
    color: var(--ink-main) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    box-shadow: var(--shadow-card) !important;
}

div[data-testid="stTextInput"] input {
    height: 42px !important;
    font-size: 13.5px !important;
    padding-left: 14px !important;
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--brand-orange) !important;
    box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.15) !important;
}

div[data-testid="stPopover"] > button {
    background-color: var(--bg-card) !important;
    border: 1.5px solid var(--border-light) !important;
    border-radius: 13px !important;
    color: var(--ink-main) !important;
    height: 42px !important;
    padding: 0 13px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    box-shadow: var(--shadow-card) !important;
}

div[data-testid="stPopover"] > button:hover {
    border-color: var(--brand-orange) !important;
    background-color: var(--brand-orange-bg) !important;
}

div[data-testid="stForm"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border-light) !important;
    border-radius: 18px !important;
    padding: 18px !important;
    box-shadow: var(--shadow-card) !important;
}

/* Sonuç Sayaç Şeridi */
.sy-list-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--ink-mute);
    padding: 2px 4px 6px 4px;
}

/* YENİ ZENGİN SİPARİŞ KARTLARI */
.sy-feed {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

details.sy-order-card {
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: 16px;
    box-shadow: var(--shadow-card);
    overflow: hidden;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

details.sy-order-card[open] {
    border-color: var(--border-mid);
    box-shadow: 0 10px 24px -6px rgba(15, 23, 42, 0.12);
}

details.sy-order-card > summary {
    list-style: none;
    cursor: pointer;
    user-select: none;
    padding: 12px 13px;
    display: block;
}

details.sy-order-card > summary::-webkit-details-marker {
    display: none;
}

.sy-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
}

.sy-card-id-group {
    display: flex;
    align-items: center;
    gap: 6px;
}

.sy-order-no {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 800;
    color: #0f172a;
    background: #f1f5f9;
    padding: 3px 8px;
    border-radius: 7px;
}

.sy-order-date {
    font-size: 11.5px;
    font-weight: 600;
    color: var(--ink-mute);
}

.sy-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 10.5px;
    font-weight: 800;
    letter-spacing: 0.02em;
    padding: 3px 9px;
    border-radius: 999px;
    color: #ffffff;
    white-space: nowrap;
}

/* Rota Akış Bloğu (Tedarikçi -> Müşteri) */
.sy-route-box {
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin-bottom: 9px;
}

.sy-supplier {
    font-size: 14px;
    font-weight: 800;
    color: var(--ink-main);
    line-height: 1.25;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-customer-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--ink-sub);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sy-arrow-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #fff7ed;
    color: #ea580c;
    border-radius: 5px;
    padding: 1px 5px;
    font-size: 10.5px;
    font-weight: 800;
    flex-shrink: 0;
}

/* Alt Bilgi Çipleri (Şantiye + Malzeme Özeti + Açılır Ok) */
.sy-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding-top: 8px;
    border-top: 1px dashed var(--border-light);
}

.sy-chips {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    flex: 1;
    overflow: hidden;
}

.sy-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 600;
    color: var(--ink-sub);
    background: var(--bg-soft);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    padding: 3px 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 56%;
}

.sy-chip-item {
    background: #eff6ff;
    border-color: #dbeafe;
    color: #1e40af;
    font-weight: 700;
    max-width: 44%;
}

.sy-expand-hint {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: #f1f5f9;
    color: var(--ink-sub);
    flex-shrink: 0;
    transition: transform 0.18s ease, background-color 0.15s ease;
}

details.sy-order-card[open] .sy-expand-hint {
    transform: rotate(180deg);
    background: #0f172a;
    color: #ffffff;
}

/* Kart İçi Hızlı Onay Şeridi (Yönetici & Onay Bekleyenler) */
.sy-quick-approve-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(90deg, #fff7ed 0%, #ffedd5 100%);
    border-top: 1px solid #fed7aa;
    padding: 8px 13px;
}

.sy-quick-approve-text {
    font-size: 11.5px;
    font-weight: 700;
    color: #9a3412;
}

a.sy-quick-approve-cta {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
    color: #ffffff !important;
    text-decoration: none !important;
    font-size: 11.5px;
    font-weight: 800;
    padding: 6px 12px;
    border-radius: 9px;
    box-shadow: 0 3px 8px rgba(234, 88, 12, 0.28);
}

a.sy-quick-approve-cta:active {
    transform: scale(0.96);
}

/* Açılır Detay Alanı */
.sy-card-drawer {
    background: #f8fafc;
    border-top: 1px solid var(--border-light);
    padding: 12px 13px 14px 13px;
}

.sy-drawer-status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    font-size: 12px;
    font-weight: 700;
    color: var(--ink-sub);
}

.sy-spec-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 10px;
}

.sy-spec-cell {
    background: #ffffff;
    border: 1px solid var(--border-light);
    border-radius: 10px;
    padding: 7px 9px;
}

.sy-spec-cell.full {
    grid-column: span 2;
}

.sy-spec-lbl {
    display: block;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-mute);
    margin-bottom: 2px;
}

.sy-spec-val {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--ink-main);
    word-break: break-word;
}

.sy-spec-val.red { color: #b91c1c; font-weight: 800; }
.sy-spec-val.navy { color: #1d4ed8; font-weight: 700; }

/* Malzeme Listesi Kartı */
.sy-items-box {
    background: #ffffff;
    border: 1px solid var(--border-light);
    border-radius: 11px;
    overflow: hidden;
}

.sy-items-header {
    background: #0f172a;
    color: #f8fafc;
    font-size: 10.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 7px 10px;
    display: flex;
    justify-content: space-between;
}

.sy-item-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 10px;
    border-bottom: 1px solid var(--border-light);
    font-size: 12.5px;
}

.sy-item-row:last-child {
    border-bottom: none;
}

.sy-item-name {
    font-weight: 700;
    color: var(--ink-main);
    flex: 1;
    min-width: 0;
}

.sy-item-qty {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 800;
    color: #0f172a;
    background: #f1f5f9;
    padding: 3px 8px;
    border-radius: 7px;
    white-space: nowrap;
}

/* ==========================================================================
   YÖNETİCİ TAM EKRAN ONAY İNCELEME EKRANI
   ========================================================================== */
.sy-review-sheet {
    background: #ffffff;
    border: 1px solid var(--border-light);
    border-radius: 20px;
    padding: 14px;
    box-shadow: var(--shadow-float);
    margin-bottom: 14px;
}

.sy-review-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 11px;
    margin-bottom: 11px;
    border-bottom: 1px solid var(--border-light);
}

.sy-review-badge-title {
    display: flex;
    align-items: center;
    gap: 8px;
}

.sy-review-pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 800;
    background: #fff7ed;
    color: #ea580c;
    border: 1px solid #fed7aa;
    padding: 4px 10px;
    border-radius: 9px;
}

.sy-review-heading {
    font-size: 14px;
    font-weight: 800;
    color: var(--ink-main);
}

a.sy-close-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: #f1f5f9;
    color: var(--ink-sub) !important;
    text-decoration: none !important;
    font-weight: 800;
    font-size: 14px;
}

.sy-decision-dock {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid var(--border-light);
}

a.sy-dec-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 46px;
    border-radius: 12px;
    font-size: 12.5px;
    font-weight: 800;
    letter-spacing: 0.03em;
    text-decoration: none !important;
    box-shadow: var(--shadow-card);
    transition: transform 0.1s ease;
}

a.sy-dec-btn:active {
    transform: scale(0.97);
}

a.dec-approve {
    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
    color: #ffffff !important;
}

a.dec-revise {
    background: linear-gradient(135deg, #facc15 0%, #eab308 100%);
    color: #0f172a !important;
}

a.dec-reject {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: #ffffff !important;
}

/* Boş Durum & Sayfalama */
.sy-empty {
    background: #ffffff;
    border: 1.5px dashed var(--border-mid);
    border-radius: 18px;
    padding: 32px 18px;
    text-align: center;
    margin-top: 10px;
}

.sy-empty-ico {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: #f1f5f9;
    color: var(--ink-sub);
    margin-bottom: 10px;
}

.sy-empty-t {
    font-size: 15px;
    font-weight: 800;
    color: var(--ink-main);
    margin-bottom: 4px;
}

.sy-empty-d {
    font-size: 12.5px;
    color: var(--ink-sub);
}

.sy-pager {
    margin-top: 14px;
    margin-bottom: 8px;
    text-align: center;
}

.sy-pager-lbl {
    font-size: 11.5px;
    font-weight: 700;
    color: var(--ink-sub);
    margin-bottom: 6px;
}

.sy-pager-bar {
    width: 100%;
    max-width: 220px;
    height: 6px;
    background: #e2e8f0;
    border-radius: 999px;
    margin: 0 auto 10px auto;
    overflow: hidden;
}

.sy-pager-fill {
    height: 100%;
    background: linear-gradient(90deg, #0f172a 0%, #f97316 100%);
    border-radius: 999px;
}
</style>
""", unsafe_allow_html=True)

ICON_REFRESH = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>'
ICON_LOGOUT = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>'
ICON_DOWN = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>'
ICON_CHECK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
ICON_SEARCH = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'


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


# Oturum Jetonu (Beni Hatırla) Oluşturma ve Doğrulama
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
        st.markdown(
            f'<div class="sy-topbar"><div class="sy-top-left">'
            f'{LOGO_HTML}'
            f'<div class="sy-top-titles">'
            f'<span class="sy-top-role">Saha & Sevkiyat Merkezi</span>'
            f'<div class="sy-top-name">SAYAR YAPI</div>'
            f'</div></div></div>',
            unsafe_allow_html=True
        )

        if url_musteri:
            st.caption(f"Müşteri Girişi: **{url_musteri}**")
        elif url_veren:
            st.caption(f"Personel Girişi: **{url_veren}**")

        with st.form("login_form", clear_on_submit=False):
            pin = st.text_input("Erişim Şifresi:", type="password")
            beni_hatirla = st.checkbox("Oturumu Açık Tut (90 Gün)", value=True)
            giris_yapildi = st.form_submit_button("Sisteme Giriş Yap", use_container_width=True, type="primary")

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

if not inceleme_aktif_mi:
    if yetki_tipi == "MUSTERI":
        rol_etiket = "Müşteri Portalı"
        ana_baslik = html.escape(str(yetki_deger))
    elif yetki_tipi == "SIPARIS_VEREN":
        rol_etiket = "Personel Takip"
        ana_baslik = html.escape(str(yetki_deger))
    else:
        rol_etiket = "Yönetici Komuta"
        ana_baslik = "SAYAR YAPI"

    st.markdown(
        f'<div class="sy-topbar">'
        f'<div class="sy-top-left">{LOGO_HTML}'
        f'<div class="sy-top-titles"><span class="sy-top-role">{rol_etiket}</span><div class="sy-top-name">{ana_baslik}</div></div>'
        f'</div>'
        f'<div class="sy-top-actions">'
        f'<a data-spa="1" href="{refresh_href}" target="_self" class="sy-circle-btn" title="Yenile">{ICON_REFRESH}</a>'
        f'<a data-spa="1" href="?action=logout" target="_self" class="sy-circle-btn" title="Çıkış">{ICON_LOGOUT}</a>'
        f'</div></div>',
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
    "ONAY BEKLİYOR": "#ea580c",
    "ONAYLANDI": "#16a34a",
    "REVİZE İSTENDİ": "#ca8a04",
    "REDDEDİLDİ": "#dc2626",
    "TAMAMLANDI": "#059669",
    "MUHASEBEYE İLETİLDİ": "#059669",
    "İPTAL EDİLDİ": "#dc2626",
    "KISMİ EVRAK": "#7c3aed"
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
    "arac": "Araç Sınıfı",
    "ted_sip_no": "Ted. Sipariş No",
    "siparis_veren": "Sipariş Veren",
    "plaka": "Plaka",
    "notlar": "Sipariş Notu"
}

oncelik = [
    "sevk_tarihi",
    "tarih",
    "firma",
    "musteri",
    "santiye",
    "sehir",
    "fabrika",
    "nakliye",
    "arac",
    "plaka",
    "yetkili",
    "telefon",
    "ted_sip_no",
    "siparis_veren",
    "notlar"
]

kalem_gruplari = dict(tuple(df_kalem.groupby("siparis_no"))) if not df_kalem.empty else {}


def kalem_ozeti_getir(sip_no):
    """Kart ön yüzünde gösterilecek kısa malzeme özetini döner (örn: 'GRİO MATİK • 26 TON')."""
    kalemler = kalem_gruplari.get(sip_no)
    if kalemler is None or kalemler.empty:
        return None
    olasi_ad = ["urun", "urun_adi", "malzeme", "malzeme_adi", "stok_adi", "kalem", "aciklama", "cinsi"]
    ad_col = next((c for c in olasi_ad if c in kalemler.columns), None)
    olasi_mik = ["miktar", "adet", "siparis_miktari", "siparis_adet", "tonaj", "kilo", "metraj", "miktari"]
    mik_col = next((c for c in olasi_mik if c in kalemler.columns), None)
    olasi_bir = ["birim", "birimi", "olcu_birimi"]
    bir_col = next((c for c in olasi_bir if c in kalemler.columns), None)

    ilk = kalemler.iloc[0]
    ad = str(ilk.get(ad_col) or "").strip() if ad_col else ""
    mik = ilk.get(mik_col) if mik_col else None
    if isinstance(mik, float) and mik.is_integer():
        mik = int(mik)
    mik_s = str(mik).strip() if pd.notna(mik) and str(mik).strip() != "" else ""
    bir_s = str(ilk.get(bir_col) or "").strip() if bir_col else ""

    parcalar = []
    if ad:
        parcalar.append(ad)
    if mik_s:
        parcalar.append(f"{mik_s} {bir_s}".strip())
    ozet = " • ".join(parcalar)
    if len(kalemler) > 1 and ozet:
        ozet += f" (+{len(kalemler) - 1})"
    return ozet or None


def siparis_detay_html_olustur(row, sip_no, vurgulu_onay=False):
    op_val = str(row.get("operasyon") or "-")
    op_upper = op_val.upper()
    renk = OP_RENK.get(op_upper, "#475569")
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
            val_cls = "sy-spec-val red"
        elif vurgulu_onay and col_lower in lacivert_alanlar:
            val_cls = "sy-spec-val navy"
        else:
            val_cls = "sy-spec-val"

        full_cls = " full" if col_lower == "notlar" or len(deger_str) > 32 else ""
        grid_items_html += (
            f'<div class="sy-spec-cell{full_cls}">'
            f'<span class="sy-spec-lbl">{html.escape(etiket)}</span>'
            f'<span class="{val_cls}">{deger_str}</span>'
            f'</div>'
        )

    grid_html = f'<div class="sy-spec-grid">{grid_items_html}</div>' if grid_items_html else ""

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
            birim_str = html.escape(str(k_row.get(birim_sutunu) or "")) if birim_sutunu else ""
            miktar_etiket = f"{miktar_str} {birim_str}".strip()

            satirlar_html += (
                f'<div class="sy-item-row">'
                f'<span class="sy-item-name">{urun_adi}</span>'
                f'<span class="sy-item-qty">{miktar_etiket}</span>'
                f'</div>'
            )

        tablo_html = (
            f'<div class="sy-items-box">'
            f'<div class="sy-items-header"><span>Sipariş Kalemleri ({len(kalemler)})</span><span>Miktar</span></div>'
            f'{satirlar_html}'
            f'</div>'
        )

    rozet_html = (
        f'<div class="sy-drawer-status-row">'
        f'<span class="sy-status-pill" style="background-color:{renk};">{html.escape(op_val)}</span>'
        f'<span>Sevk Durumu: <strong>{durum_gosterim}</strong></span>'
        f'</div>'
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
        st.session_state.flash_mesaj = f"Sipariş #{sip_no} için {karar} kararı kaydedildi."
        st.rerun()
    except Exception as err:
        st.error(f"Karar PostgreSQL'e yazılamadı: {err}")


@st.dialog("Revize Talebi Notu")
def revize_not_penceresi(sip_no: int, row_data):
    st.caption(f"Sipariş #{sip_no} için revize gerekçesini yazınız:")
    revize_aciklama = st.text_area(
        "Revize Açıklaması",
        placeholder="Örn: Nakliye fiyatı veya araç tipi güncellensin...",
        height=100,
        label_visibility="collapsed"
    )
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("Revize Gönder", type="primary", use_container_width=True):
            if not revize_aciklama.strip():
                st.warning("Lütfen kısa bir revize açıklaması yazınız.")
            else:
                karari_uygula(sip_no, row_data, "REVİZE İSTENDİ", revize_aciklama)
    with col_r2:
        if st.button("Vazgeç", use_container_width=True):
            st.session_state.bekleyen_revize_sip_no = None
            st.rerun()


# ==============================================================================
# YÖNETİCİ TAM EKRAN ONAY İNCELEME SAYFASI
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
        f'<div class="sy-review-sheet">'
        f'<div class="sy-review-top">'
        f'<div class="sy-review-badge-title">'
        f'<span class="sy-review-pill">#{html.escape(str(aktif_inceleme_no))}</span>'
        f'<span class="sy-review-heading">Yönetici Onay İnceleme</span>'
        f'</div>'
        f'<a data-spa="1" href="?incele_kapat=1{token_param}" target="_self" class="sy-close-btn" title="Listeye Dön">✕</a>'
        f'</div>'
        f'{rozet_html}'
        f'{grid_html}'
        f'{tablo_html}'
        f'<div class="sy-decision-dock">'
        f'<a data-spa="1" href="{onayla_href}" target="_self" class="sy-dec-btn dec-approve">✓ ONAYLA</a>'
        f'<a data-spa="1" href="{revize_href}" target="_self" class="sy-dec-btn dec-revise">✎ REVİZE</a>'
        f'<a data-spa="1" href="{reddet_href}" target="_self" class="sy-dec-btn dec-reject">✕ REDDET</a>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if st.session_state.get("bekleyen_revize_sip_no") == int(aktif_inceleme_no):
        revize_not_penceresi(aktif_inceleme_no, inceleme_row)

    st.stop()

# ==============================================================================
# ANA AKIŞ EKRANI (BENTO SEGMENTLER + ZENGİN KART LİSTESİ)
# ==============================================================================
flash_msg = st.session_state.flash_mesaj
if flash_msg:
    toast_id = f"toast_{int(time.time() * 1000)}"
    st.markdown(
        f'<div id="{toast_id}" class="sy-toast">✅ <span>{html.escape(str(flash_msg))}</span></div>',
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
            }}, 2600);
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
act_sevk = " active" if kpi_mod == "SEVK" else ""
act_onay = " active" if kpi_mod == "ONAY" else ""
act_tamam = " active" if kpi_mod == "TAMAMLANDI" else ""

st.markdown(
    f'<div class="sy-segment-wrap">'
    f'<a data-spa="1" href="?kpi=SEVK{token_param}" target="_self" class="sy-seg-card{act_sevk}">'
    f'<div class="sy-seg-top"><span class="sy-seg-num">{sevk_bekleyen}</span><span class="sy-seg-dot dot-green"></span></div>'
    f'<div class="sy-seg-label">Sevk Bekleyen</div></a>'
    f'<a data-spa="1" href="?kpi=ONAY{token_param}" target="_self" class="sy-seg-card{act_onay}">'
    f'<div class="sy-seg-top"><span class="sy-seg-num">{onay_bekleyen}</span><span class="sy-seg-dot dot-orange"></span></div>'
    f'<div class="sy-seg-label">Onay Bekleyen</div></a>'
    f'<a data-spa="1" href="?kpi=TAMAMLANDI{token_param}" target="_self" class="sy-seg-card{act_tamam}">'
    f'<div class="sy-seg-top"><span class="sy-seg-num">{tamamlandi_siparis}</span><span class="sy-seg-dot dot-blue"></span></div>'
    f'<div class="sy-seg-label">Tamamlanan</div></a>'
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
popover_etiket = "Filtre •" if ek_filtre_aktif else "Filtre"

col_arama, col_filtre = st.columns([4.5, 1.3])
with col_arama:
    arama = st.text_input(
        "Arama",
        key="arama_metni",
        placeholder="Sipariş no, tedarikçi, müşteri, şantiye ara...",
        label_visibility="collapsed"
    )

with col_filtre:
    with st.popover(popover_etiket, use_container_width=True):
        st.markdown("**Detaylı Filtreleme**")
        secili_op = st.selectbox("Operasyon Durumu", op_listesi, key="f_op")
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
        f'<div class="sy-empty">'
        f'<div class="sy-empty-ico">{ICON_SEARCH}</div>'
        f'<div class="sy-empty-t">Kayıt Bulunamadı</div>'
        f'<div class="sy-empty-d">Seçili filtrelere veya arama metnine uygun sipariş kaydı yok.</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    col_e1, col_e2, col_e3 = st.columns([1, 2, 1])
    with col_e2:
        st.button("Tüm Filtreleri Temizle", on_click=filtreleri_sifirla, use_container_width=True, type="primary")
else:
    aktif_sekme_adi = {"SEVK": "Sevk Bekleyenler", "ONAY": "Onay Bekleyenler", "TAMAMLANDI": "Tamamlananlar"}.get(kpi_mod, "Liste")
    st.markdown(
        f'<div class="sy-list-meta">'
        f'<span>{aktif_sekme_adi}</span>'
        f'<span>{gosterilen_adet} / {toplam_filtrelenen} kayıt</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    kart_parcalari = ['<div class="sy-feed">']
    for _, row in filtered.head(gosterilen_limit).iterrows():
        sip_no = row.get("siparis_no", "-")
        op_val = str(row.get("operasyon") or "-")
        op_upper = op_val.upper()
        rozet_renk = OP_RENK.get(op_upper, "#475569")

        firma_str = md_temizle(row.get("firma"))
        musteri_str = md_temizle(row.get("musteri"))
        santiye_str = md_temizle(row.get("santiye"))
        sevk_t = str(row.get("sevk_tarihi") or "").strip()
        sip_t = str(row.get("tarih") or "").strip()
        tarih_gosterim = sevk_t if sevk_t and sevk_t not in ("None", "nan", "-") else (sip_t or "-")

        kalem_ozet = kalem_ozeti_getir(sip_no)
        kalem_chip_html = f'<span class="sy-chip sy-chip-item">📦 {html.escape(kalem_ozet)}</span>' if kalem_ozet else ""

        rozet_html, grid_html, tablo_html = siparis_detay_html_olustur(row, sip_no)

        if yetki_tipi == "MUSTERI":
            rota_html = f'<div class="sy-supplier">{html.escape(firma_str)}</div>'
        else:
            rota_html = (
                f'<div class="sy-supplier">{html.escape(firma_str)}</div>'
                f'<div class="sy-customer-row"><span class="sy-arrow-badge">TESLİM</span><span>{html.escape(musteri_str)}</span></div>'
            )

        onay_cta_html = ""
        if yetki_tipi == "YONETICI" and op_upper == "ONAY BEKLİYOR":
            onay_cta_html = (
                f'<div class="sy-quick-approve-bar">'
                f'<span class="sy-quick-approve-text">Yönetici onayı bekleniyor</span>'
                f'<a data-spa="1" href="?incele={sip_no}{token_param}" target="_self" class="sy-quick-approve-cta">{ICON_CHECK} İncele & Karar Ver</a>'
                f'</div>'
            )

        kart_parcalari.append(
            f'<details class="sy-order-card">'
            f'<summary>'
            f'<div class="sy-card-head">'
            f'<div class="sy-card-id-group">'
            f'<span class="sy-order-no">#{html.escape(str(sip_no))}</span>'
            f'<span class="sy-order-date">📅 {html.escape(tarih_gosterim)}</span>'
            f'</div>'
            f'<span class="sy-status-pill" style="background-color:{rozet_renk};">{html.escape(op_val)}</span>'
            f'</div>'
            f'<div class="sy-route-box">{rota_html}</div>'
            f'<div class="sy-card-footer">'
            f'<div class="sy-chips">'
            f'<span class="sy-chip">📍 {html.escape(santiye_str)}</span>'
            f'{kalem_chip_html}'
            f'</div>'
            f'<span class="sy-expand-hint">{ICON_DOWN}</span>'
            f'</div>'
            f'</summary>'
            f'{onay_cta_html}'
            f'<div class="sy-card-drawer">{rozet_html}{grid_html}{tablo_html}</div>'
            f'</details>'
        )

    kart_parcalari.append('</div>')
    st.markdown("".join(kart_parcalari), unsafe_allow_html=True)

    yuzde = int((gosterilen_adet / toplam_filtrelenen) * 100) if toplam_filtrelenen > 0 else 100
    st.markdown(
        f'<div class="sy-pager">'
        f'<div class="sy-pager-lbl">{toplam_filtrelenen} siparişten {gosterilen_adet} tanesi listeleniyor</div>'
        f'<div class="sy-pager-bar"><div class="sy-pager-fill" style="width:{yuzde}%;"></div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if gosterilen_adet < toplam_filtrelenen:
        kalan = toplam_filtrelenen - gosterilen_adet
        eklenecek = min(50, kalan)
        if st.button(f"Daha Fazla Sipariş Yükle (+{eklenecek})", use_container_width=True):
            st.session_state.sayfa_limiti += 50
            st.rerun()
