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
LOGO_HTML = (
    f'<img src="{LOGO_DATA_URI}" class="brand-logo" alt="Sayar Yapı">'
    if LOGO_DATA_URI
    else '<div class="brand-monogram">SY</div>'
)

# Sayfa ve Mobil Görünüm Ayarları
st.set_page_config(
    page_title="Sayar Yapı | Canlı Sipariş & Lojistik Radarı",
    page_icon=LOGO_DATA_URI if LOGO_DATA_URI else "🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# iOS Ana Ekran İkonu + SPA Link Yakalayıcı + Canlı Saat + Akış Yüksekliği Hesaplayıcı
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

        if (!win.__liveClockStarted) {{
            win.__liveClockStarted = true;
            setInterval(function() {{
                const clockEl = doc.getElementById('sy-live-clock');
                if (clockEl) {{
                    const now = new Date();
                    const hh = String(now.getHours()).padStart(2, '0');
                    const mm = String(now.getMinutes()).padStart(2, '0');
                    const ss = String(now.getSeconds()).padStart(2, '0');
                    clockEl.textContent = hh + ':' + mm + ':' + ss;
                }}
            }}, 1000);
        }}

        function updateStreamHeight() {{
            const streamEl = doc.getElementById('sy-scroll-stream');
            if (!streamEl) return;
            const rect = streamEl.getBoundingClientRect();
            const vh = win.innerHeight || doc.documentElement.clientHeight;
            const avail = Math.max(220, Math.floor(vh - rect.top - 8));
            streamEl.style.height = avail + 'px';
            streamEl.style.maxHeight = avail + 'px';
        }}

        updateStreamHeight();
        setTimeout(updateStreamHeight, 100);
        setTimeout(updateStreamHeight, 350);
        setTimeout(updateStreamHeight, 800);
        if (!win.__streamResizeHooked) {{
            win.__streamResizeHooked = true;
            win.addEventListener('resize', updateStreamHeight);
            win.addEventListener('orientationchange', updateStreamHeight);
            const obs = new MutationObserver(updateStreamHeight);
            obs.observe(doc.body, {{ childList: true, subtree: true }});
        }}
    }})();
    </script>
    """,
    height=0,
    width=0
)

# ==============================================================================
# SIFIR ÇAKIŞMALI, KABARTMALI, ÜST ALAN SABİT + KARTLAR KAYDIRMALI MOBİL TASARIM
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=JetBrains+Mono:wght@600;700;800&display=swap');

:root {
    --bg-canvas: #e9eff7;
    --bg-surface: #ffffff;
    --ink-primary: #0b1528;
    --ink-secondary: #475569;
    --ink-muted: #64748b;
    --brand-cobalt: #0052ff;
    --brand-cyan: #0ea5e9;
    --brand-amber: #f97316;
    --brand-emerald: #10b981;
    --emboss-card:
        0 3px 8px -2px rgba(15, 23, 42, 0.08),
        0 1px 2px rgba(15, 23, 42, 0.05),
        inset 0 1px 0 rgba(255, 255, 255, 0.96),
        inset 0 -1px 0 rgba(15, 23, 42, 0.05);
    --emboss-tile:
        0 4px 10px -3px rgba(15, 23, 42, 0.09),
        0 1px 2px rgba(15, 23, 42, 0.05),
        inset 0 1.5px 0 rgba(255, 255, 255, 1),
        inset 0 -1.5px 0 rgba(15, 23, 42, 0.06);
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

/* Küresel Arka Plan ve Yazı Tipi */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    max-width: 100vw !important;
    overflow-x: hidden !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background:
        radial-gradient(circle at 15% 0%, rgba(0, 82, 255, 0.06) 0%, transparent 40%),
        radial-gradient(circle at 88% 2%, rgba(14, 165, 233, 0.07) 0%, transparent 36%),
        var(--bg-canvas) !important;
    color: var(--ink-primary) !important;
    -webkit-font-smoothing: antialiased;
}

*, *::before, *::after {
    box-sizing: border-box !important;
}

.block-container {
    max-width: 720px !important;
    margin: 0 auto !important;
    padding: 8px 0.55rem 0.5rem 0.55rem !important;
}

/*
   ÖNEMLİ: Streamlit'in kendi dikey konteynerlerinin height/overflow özelliklerine
   ASLA müdahale edilmiyor. Her blok kendi doğal yüksekliğinde alt alta sıralanır,
   böylece hiçbir üst bileşen bir diğerinin üzerine binmez.
*/
[data-testid="stVerticalBlock"] {
    gap: 6px !important;
}

div[data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}

/* ==========================================================================
   ÜST BAR (KOMPAKT & CABARTMALI)
   ========================================================================== */
@keyframes pulseRing {
    0% { transform: scale(0.85); opacity: 0.9; }
    70% { transform: scale(2.1); opacity: 0; }
    100% { transform: scale(2.1); opacity: 0; }
}

@keyframes shimmerSweep {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.command-header {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 7px;
    background: linear-gradient(180deg, #ffffff 0%, #f5f8fd 100%);
    border: 1px solid rgba(15, 23, 42, 0.10);
    border-radius: 12px;
    padding: 6px 9px;
    box-shadow: var(--emboss-tile);
    overflow: hidden;
    margin: 0;
}

.command-header::after {
    content: "";
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, #0052ff, #0ea5e9, #10b981, #0052ff);
    background-size: 200% 100%;
    animation: shimmerSweep 5s linear infinite;
}

.brand-cluster {
    display: flex;
    align-items: center;
    gap: 7px;
    min-width: 0;
    flex: 1 1 auto;
}

.brand-logo {
    width: 26px;
    height: 26px;
    border-radius: 7px;
    object-fit: contain;
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.09);
    padding: 1.5px;
    flex-shrink: 0;
    box-shadow: 0 2px 4px rgba(15, 23, 42, 0.07);
}

.brand-monogram {
    width: 26px;
    height: 26px;
    border-radius: 7px;
    background: linear-gradient(135deg, #0052ff 0%, #0ea5e9 100%);
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.brand-text-wrap {
    min-width: 0;
    flex: 1 1 auto;
}

.brand-title-row {
    display: flex;
    align-items: center;
    gap: 5px;
    min-width: 0;
}

.brand-name {
    font-size: 12.5px;
    font-weight: 800;
    color: var(--ink-primary);
    letter-spacing: -0.2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.30);
    color: #047857;
    padding: 1px 5px;
    border-radius: 999px;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 0.35px;
    flex-shrink: 0;
}

.live-dot-wrap {
    position: relative;
    width: 6px;
    height: 6px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.live-dot-core {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background-color: #10b981;
}

.live-dot-ring {
    position: absolute;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #10b981;
    animation: pulseRing 1.8s cubic-bezier(0.24, 0, 0.38, 1) infinite;
}

.brand-sub-row {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 1px;
    font-size: 9.5px;
    color: var(--ink-muted);
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.telemetry-clock {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    color: var(--brand-cobalt);
    background: rgba(0, 82, 255, 0.08);
    padding: 0.5px 4.5px;
    border-radius: 4px;
    flex-shrink: 0;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
}

a.cmd-icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: linear-gradient(180deg, #ffffff 0%, #eef3fa 100%);
    border: 1px solid rgba(15, 23, 42, 0.11);
    color: var(--ink-primary) !important;
    text-decoration: none !important;
    font-size: 12.5px;
    font-weight: 800;
    box-shadow: 0 2px 4px rgba(15, 23, 42, 0.06), inset 0 1px 0 #ffffff;
}

a.cmd-icon-btn:active {
    transform: scale(0.93);
}

/* ==========================================================================
   3'LÜ KOMPAKT KABARTMALI KPI KARTLARI
   ========================================================================== */
.kpi-deck {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    width: 100%;
    margin: 0;
}

a.kpi-tile {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-width: 0;
    background: linear-gradient(180deg, #ffffff 0%, #f6f9fe 100%);
    border: 1px solid rgba(15, 23, 42, 0.10);
    border-radius: 10px;
    padding: 5px 7px 4px 7px;
    text-decoration: none !important;
    box-shadow: var(--emboss-tile);
    overflow: hidden;
}

a.kpi-tile:active {
    transform: scale(0.97);
}

.kpi-tile-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 3px;
    margin-bottom: 1.5px;
}

.kpi-tag {
    font-size: 9.2px;
    font-weight: 700;
    color: var(--ink-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.kpi-badge-dot {
    width: 5.5px;
    height: 5.5px;
    border-radius: 50%;
    flex-shrink: 0;
}

.kpi-tile-mid {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 3px;
}

.kpi-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    font-weight: 800;
    line-height: 1.05;
    color: var(--ink-primary);
    letter-spacing: -0.5px;
}

.kpi-pct {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    font-weight: 700;
    padding: 0.5px 4px;
    border-radius: 4px;
    flex-shrink: 0;
}

.kpi-mini-bar {
    width: 100%;
    height: 2.5px;
    background: #e5ebf3;
    border-radius: 999px;
    margin-top: 3px;
    overflow: hidden;
}

.kpi-mini-fill {
    height: 100%;
    border-radius: 999px;
}

.kpi-t-blue .kpi-badge-dot { background: #0052ff; }
.kpi-t-blue .kpi-pct { background: rgba(0, 82, 255, 0.09); color: #0052ff; }
.kpi-t-blue .kpi-mini-fill { background: linear-gradient(90deg, #0052ff, #38bdf8); }

.kpi-t-amber .kpi-badge-dot { background: #f97316; box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.18); }
.kpi-t-amber .kpi-pct { background: rgba(249, 115, 22, 0.12); color: #c2410c; }
.kpi-t-amber .kpi-mini-fill { background: linear-gradient(90deg, #f97316, #fbbf24); }

.kpi-t-emerald .kpi-badge-dot { background: #10b981; }
.kpi-t-emerald .kpi-pct { background: rgba(16, 185, 129, 0.11); color: #047857; }
.kpi-t-emerald .kpi-mini-fill { background: linear-gradient(90deg, #10b981, #34d399); }

a.kpi-tile.kpi-selected.kpi-t-blue {
    background: linear-gradient(180deg, #ffffff 0%, #e8f1ff 100%);
    border: 1.5px solid #0052ff;
}
a.kpi-tile.kpi-selected.kpi-t-amber {
    background: linear-gradient(180deg, #ffffff 0%, #fff1e5 100%);
    border: 1.5px solid #f97316;
}
a.kpi-tile.kpi-selected.kpi-t-emerald {
    background: linear-gradient(180deg, #ffffff 0%, #e6fbf2 100%);
    border: 1.5px solid #10b981;
}

/* ==========================================================================
   ARAMA & FİLTRE SATIRI (DOĞAL AKIŞTA, HİÇBİR ŞEYLE ÇAKIŞMAZ)
   ========================================================================== */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 6px !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:first-child {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    width: auto !important;
}

div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:last-child {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 48px !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafd 100%) !important;
    border: 1px solid rgba(15, 23, 42, 0.12) !important;
    border-radius: 9px !important;
    color: var(--ink-primary) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05), inset 0 1px 0 #ffffff !important;
}

div[data-testid="stTextInput"] input {
    height: 35px !important;
    padding: 0 10px !important;
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: #0052ff !important;
    box-shadow: 0 0 0 2px rgba(0, 82, 255, 0.14) !important;
}

div[data-testid="stPopover"] > button {
    background: linear-gradient(180deg, #ffffff 0%, #f1f5fb 100%) !important;
    border: 1px solid rgba(15, 23, 42, 0.12) !important;
    border-radius: 9px !important;
    color: var(--ink-primary) !important;
    height: 35px !important;
    min-width: 48px !important;
    padding: 0 9px !important;
    font-weight: 700 !important;
    font-size: 12.5px !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05), inset 0 1px 0 #ffffff !important;
}

/* ==========================================================================
   AKIŞ SAYACI ŞERİDİ ("Aktif Sevkiyat Akışı" YAZISININ OLDUĞU BAR)
   ========================================================================== */
.feed-header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding: 3px 2px 5px 2px;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    font-size: 10.5px;
    color: var(--ink-muted);
    font-weight: 600;
}

.feed-count-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.08);
    padding: 1.5px 7px;
    border-radius: 999px;
    color: var(--ink-secondary);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.feed-count-pill strong {
    font-family: 'JetBrains Mono', monospace;
    color: var(--ink-primary);
    font-weight: 800;
}

.feed-mode-badge {
    font-size: 9.5px;
    font-weight: 700;
    color: var(--brand-cobalt);
    background: rgba(0, 82, 255, 0.08);
    padding: 1.5px 7px;
    border-radius: 999px;
    white-space: nowrap;
}

/* ==========================================================================
   KAYDIRILABİLİR SİPARİŞ LİSTESİ KONTEYNERİ
   (ÜST BÖLGE SABİT KALIR, YALNIZCA BU ALAN KAYAR)
   ========================================================================== */
.sy-scroll-stream {
    overflow-y: auto !important;
    overflow-x: hidden !important;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-y: contain;
    padding: 2px 1px 16px 1px;
    height: calc(100dvh - 188px);
    max-height: calc(100dvh - 188px);
}

.sy-scroll-stream::-webkit-scrollbar {
    width: 4px;
}

.sy-scroll-stream::-webkit-scrollbar-thumb {
    background: rgba(100, 116, 139, 0.28);
    border-radius: 999px;
}

.sip-stream {
    display: flex;
    flex-direction: column;
    gap: 5px;
    width: 100%;
    max-width: 100%;
}

.sip-row-wrap {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: stretch;
    gap: 5px;
    width: 100%;
    max-width: 100%;
}

details.neo-card {
    position: relative;
    flex: 1 1 auto;
    min-width: 0;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafd 100%);
    border: 1px solid rgba(15, 23, 42, 0.10);
    border-left: 3.5px solid var(--accent-color, #0052ff);
    border-radius: 10px;
    box-shadow: var(--emboss-card);
    overflow: hidden;
}

details.neo-card.is-pending-approval {
    background: linear-gradient(180deg, #ffffff 0%, #fff7ed 100%);
    border-color: rgba(249, 115, 22, 0.36);
    box-shadow:
        0 3px 10px -2px rgba(249, 115, 22, 0.15),
        0 1px 2px rgba(15, 23, 42, 0.05),
        inset 0 1px 0 #ffffff;
}

details.neo-card[open] {
    border-color: rgba(0, 82, 255, 0.30);
    box-shadow: 0 6px 14px -4px rgba(15, 23, 42, 0.12), inset 0 1px 0 #ffffff;
}

/* Daraltılmış Kart Başlığı (40px kompakt yükseklik) */
details.neo-card > summary {
    list-style: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding: 4.5px 8px;
    cursor: pointer;
    user-select: none;
    min-height: 40px;
    width: 100%;
}

details.neo-card > summary::-webkit-details-marker {
    display: none;
}

details.neo-card > summary:hover {
    background-color: rgba(241, 245, 251, 0.7);
}

.card-left-rail {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    flex: 1 1 auto;
}

.sip-no-chip {
    display: inline-flex;
    align-items: center;
    gap: 3.5px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 800;
    color: var(--ink-primary);
    background: linear-gradient(180deg, #f8fafd 0%, #e9eff8 100%);
    border: 1px solid rgba(15, 23, 42, 0.10);
    padding: 2px 5.5px;
    border-radius: 6px;
    box-shadow: inset 0 1px 0 #ffffff;
    flex-shrink: 0;
}

.status-dot {
    width: 5.5px;
    height: 5.5px;
    border-radius: 50%;
    background: var(--accent-color, #0052ff);
    flex-shrink: 0;
}

.status-dot.pulse {
    animation: pulseRing 1.8s infinite;
}

.card-main-info {
    min-width: 0;
    flex: 1 1 auto;
}

.card-route-line {
    font-size: 11.8px;
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.route-arrow {
    color: var(--brand-cobalt);
    font-weight: 800;
    padding: 0 1px;
}

.card-meta-line {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 1.5px;
    font-size: 9.8px;
    font-weight: 500;
    color: var(--ink-muted);
    line-height: 1.15;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.card-meta-site {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.card-meta-date {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    color: var(--ink-secondary);
    flex-shrink: 0;
}

.card-right-rail {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
}

.mini-op-pill {
    font-size: 8.6px;
    font-weight: 800;
    letter-spacing: 0.15px;
    padding: 2px 5px;
    border-radius: 5px;
    background: var(--accent-bg, #eff6ff);
    color: var(--accent-color, #0052ff);
    border: 1px solid var(--accent-border, rgba(0, 82, 255, 0.22));
    white-space: nowrap;
    max-width: 78px;
    overflow: hidden;
    text-overflow: ellipsis;
}

.neo-chevron {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    background: linear-gradient(180deg, #f8fafd 0%, #e9eff8 100%);
    border: 1px solid rgba(15, 23, 42, 0.08);
    color: var(--ink-secondary);
    font-size: 9px;
    font-weight: 800;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

details.neo-card[open] .neo-chevron {
    transform: rotate(90deg);
    background: #0052ff;
    color: #ffffff;
}

.neo-card-body {
    padding: 8px 9px 9px 9px;
    border-top: 1px dashed rgba(15, 23, 42, 0.10);
    background: #ffffff;
}

/* Yönetici Hızlı Onay İnceleme Butonu (Kart yüksekliği ile uyumlu 40px) */
a.quick-inspect-btn {
    flex: 0 0 40px;
    width: 40px;
    min-height: 40px;
    border-radius: 10px;
    background: linear-gradient(180deg, #fb923c 0%, #ea580c 100%);
    border: 1px solid #c2410c;
    color: #ffffff !important;
    text-decoration: none !important;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5px;
    box-shadow: 0 3px 8px rgba(234, 88, 12, 0.26), inset 0 1px 0 rgba(255, 255, 255, 0.35);
}

a.quick-inspect-btn:active {
    transform: scale(0.95);
}

.qi-icon {
    font-size: 12.5px;
    font-weight: 900;
    line-height: 1;
}

.qi-txt {
    font-size: 7.6px;
    font-weight: 800;
    letter-spacing: 0.25px;
    text-transform: uppercase;
}

/* Kaydırma Alanı İçi Sayfalama ve Daha Fazla Yükle Bağlantısı */
.pagination-box {
    background: linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 10px;
    padding: 8px 10px;
    margin-top: 7px;
    text-align: center;
    box-shadow: var(--emboss-card);
}

.pagination-text {
    font-size: 10.5px;
    color: var(--ink-secondary);
    margin-bottom: 5px;
    font-weight: 700;
}

.progress-track {
    width: 100%;
    max-width: 220px;
    height: 4.5px;
    background-color: #e2e8f0;
    border-radius: 999px;
    margin: 0 auto;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #0052ff 0%, #0ea5e9 50%, #10b981 100%);
    border-radius: 999px;
}

a.load-more-link {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 36px;
    margin-top: 6px;
    border-radius: 10px;
    background: linear-gradient(180deg, #ffffff 0%, #eef4ff 100%);
    border: 1px solid rgba(0, 82, 255, 0.24);
    color: #0052ff !important;
    font-size: 12px;
    font-weight: 800;
    text-decoration: none !important;
    box-shadow: var(--emboss-card);
}

/* Toast Bildirim Bandı */
.auto-toast-banner {
    display: flex;
    align-items: center;
    gap: 7px;
    background: linear-gradient(180deg, #ecfdf5 0%, #d1fae5 100%);
    border: 1px solid #6ee7b7;
    border-left: 4px solid #10b981;
    color: #064e3b;
    border-radius: 9px;
    padding: 5px 9px;
    font-size: 11.5px;
    font-weight: 700;
    opacity: 1;
    transition: opacity 0.35s ease;
}

/* ==========================================================================
   DETAY ROZETİ, BİLGİ IZGARASI & ÜRÜN TABLOSU
   ========================================================================== */
.detail-status-strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 5px;
    margin-bottom: 6px;
}

.op-status-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 7px;
    color: #ffffff;
    font-size: 10.5px;
    font-weight: 800;
    letter-spacing: 0.2px;
}

.sevk-status-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10.5px;
    font-weight: 700;
    color: var(--ink-secondary);
    background: #f1f5fb;
    border: 1px solid rgba(15, 23, 42, 0.08);
    padding: 2.5px 7px;
    border-radius: 7px;
}

.info-matrix {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 5px;
    margin-bottom: 7px;
}

.matrix-cell {
    background: linear-gradient(180deg, #fafcff 0%, #f3f6fc 100%);
    border: 1px solid rgba(15, 23, 42, 0.07);
    border-radius: 8px;
    padding: 4px 7px;
    min-width: 0;
    box-shadow: inset 0 1px 0 #ffffff;
}

.matrix-cell.span-2 {
    grid-column: span 2;
}

.matrix-lbl {
    display: block;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: var(--ink-muted);
    margin-bottom: 1px;
}

.matrix-val {
    display: block;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--ink-primary);
    word-break: break-word;
}

.matrix-val-red {
    display: block;
    font-size: 11.8px;
    font-weight: 800;
    color: #dc2626;
    word-break: break-word;
}

.matrix-val-navy {
    display: block;
    font-size: 11.5px;
    font-weight: 700;
    color: #0052ff;
    word-break: break-word;
}

.neo-table-wrap {
    width: 100%;
    overflow-x: auto;
    border-radius: 9px;
    border: 1px solid rgba(15, 23, 42, 0.10);
}

.urun-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.3px;
    background: #ffffff;
}

.urun-table th {
    background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
    color: #f8fafc;
    text-align: left;
    padding: 5px 7px;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 0.25px;
}

.urun-table td {
    padding: 5px 7px;
    color: var(--ink-primary);
    border-bottom: 1px solid #eef2f7;
    font-weight: 600;
}

.urun-table tr:last-child td {
    border-bottom: none;
}

.urun-table tr:nth-child(even) td {
    background-color: #f8fafd;
}

.urun-miktar {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    text-align: right;
    white-space: nowrap;
    color: #0052ff !important;
}

/* ==========================================================================
   YÖNETİCİ TAM EKRAN ONAY İNCELEME KONSOLU
   ========================================================================== */
.review-console {
    background: #ffffff;
    border: 1px solid rgba(249, 115, 22, 0.34);
    border-top: 4px solid #f97316;
    border-radius: 14px;
    padding: 11px;
    margin-top: 4px;
    box-shadow: var(--emboss-card);
}

.review-console-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    padding-bottom: 8px;
    margin-bottom: 8px;
    border-bottom: 1px solid #eef2f7;
}

.review-console-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13.5px;
    font-weight: 800;
    color: var(--ink-primary);
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.review-id-pill {
    font-family: 'JetBrains Mono', monospace;
    background: #fff7ed;
    color: #ea580c;
    border: 1px solid #fed7aa;
    padding: 1.5px 6px;
    border-radius: 6px;
    font-size: 12px;
}

a.close-review-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: #f1f5fb;
    border: 1px solid rgba(15, 23, 42, 0.1);
    color: var(--ink-secondary) !important;
    font-size: 12.5px;
    font-weight: 800;
    text-decoration: none !important;
    flex-shrink: 0;
}

.onay-aksiyon-bar {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed rgba(15, 23, 42, 0.12);
    width: 100%;
}

a.aksiyon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    height: 40px;
    border-radius: 10px;
    font-size: 11.5px;
    font-weight: 800;
    letter-spacing: 0.25px;
    text-decoration: none !important;
    padding: 0 5px;
    white-space: nowrap;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

a.aksiyon-btn:active {
    transform: scale(0.96);
}

a.aksiyon-onayla {
    background: linear-gradient(180deg, #10b981 0%, #059669 100%) !important;
    color: #ffffff !important;
}

a.aksiyon-revize {
    background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 100%) !important;
    color: #0f172a !important;
}

a.aksiyon-reddet {
    background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%) !important;
    color: #ffffff !important;
}

/* ==========================================================================
   GİRİŞ FORMU & BOŞ DURUM
   ========================================================================== */
div[data-testid="stForm"] {
    background: linear-gradient(180deg, #ffffff 0%, #f7faff 100%) !important;
    border: 1px solid rgba(0, 82, 255, 0.14) !important;
    border-radius: 14px !important;
    padding: 14px !important;
    box-shadow: var(--emboss-tile) !important;
    margin-top: 6px !important;
}

.empty-state-box {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafd 100%);
    border: 1.5px dashed rgba(0, 82, 255, 0.24);
    border-radius: 14px;
    padding: 22px 14px;
    text-align: center;
    margin: 4px 0;
    box-shadow: var(--emboss-card);
}

.empty-state-icon {
    font-size: 26px;
    margin-bottom: 5px;
}

.empty-state-title {
    font-size: 13.5px;
    font-weight: 800;
    color: var(--ink-primary);
    margin-bottom: 3px;
}

.empty-state-desc {
    font-size: 11.5px;
    color: var(--ink-muted);
}

/* Küçük Mobil Ekranlar (< 380px) Ek Koruma */
@media (max-width: 380px) {
    .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
    }
    .kpi-num { font-size: 14.5px; }
    .kpi-tag { font-size: 8.6px; }
    .mini-op-pill { display: none; }
    .brand-name { font-size: 12px; }
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
        st.markdown(
            f'<div class="command-header">'
            f'<div class="brand-cluster">'
            f'{LOGO_HTML}'
            f'<div class="brand-text-wrap">'
            f'<div class="brand-title-row"><span class="brand-name">SAYAR YAPI</span><span class="live-pill"><span class="live-dot-wrap"><span class="live-dot-ring"></span><span class="live-dot-core"></span></span>GÜVENLİ</span></div>'
            f'<div class="brand-sub-row">Canlı Sipariş & Sevkiyat Telemetri Sistemi</div>'
            f'</div></div></div>',
            unsafe_allow_html=True
        )

        if url_musteri:
            st.caption(f"Müşteri Erişimi: **{url_musteri}**")
        elif url_veren:
            st.caption(f"Personel Erişimi: **{url_veren}**")

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

if st.query_params.get("action") == "more":
    st.session_state.sayfa_limiti += 50
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
anlik_saat = datetime.now().strftime("%H:%M:%S")

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

OP_STYLE = {
    "İŞLENDİ": {"color": "#0052ff", "bg": "#eff6ff", "border": "rgba(0,82,255,0.22)", "short": "İŞLENDİ", "pulse": True},
    "ONAY BEKLİYOR": {"color": "#f97316", "bg": "#fff7ed", "border": "rgba(249,115,22,0.28)", "short": "ONAY BEKLİYOR", "pulse": True},
    "ONAYLANDI": {"color": "#10b981", "bg": "#ecfdf5", "border": "rgba(16,185,129,0.25)", "short": "ONAYLANDI", "pulse": True},
    "REVİZE İSTENDİ": {"color": "#d97706", "bg": "#fffbeb", "border": "rgba(217,119,6,0.28)", "short": "REVİZE", "pulse": True},
    "REDDEDİLDİ": {"color": "#ef4444", "bg": "#fef2f2", "border": "rgba(239,68,68,0.25)", "short": "REDDEDİLDİ", "pulse": False},
    "TAMAMLANDI": {"color": "#059669", "bg": "#ecfdf5", "border": "rgba(5,150,105,0.22)", "short": "TAMAMLANDI", "pulse": False},
    "MUHASEBEYE İLETİLDİ": {"color": "#0284c7", "bg": "#f0f9ff", "border": "rgba(2,132,199,0.22)", "short": "MUHASEBE", "pulse": False},
    "İPTAL EDİLDİ": {"color": "#dc2626", "bg": "#fef2f2", "border": "rgba(220,38,38,0.22)", "short": "İPTAL", "pulse": False},
    "KISMİ EVRAK": {"color": "#7c3aed", "bg": "#f5f3ff", "border": "rgba(124,58,237,0.25)", "short": "KISMİ EVRAK", "pulse": True}
}

DEFAULT_OP_STYLE = {"color": "#475569", "bg": "#f1f5f9", "border": "rgba(71,85,105,0.2)", "short": "BEKLİYOR", "pulse": False}

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
    st_info = OP_STYLE.get(op_upper, DEFAULT_OP_STYLE)
    renk = st_info["color"]
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
            val_cls = "matrix-val-red"
        elif vurgulu_onay and col_lower in lacivert_alanlar:
            val_cls = "matrix-val-navy"
        else:
            val_cls = "matrix-val"

        span_cls = " span-2" if (col_lower == "notlar" or len(deger_str) > 32) else ""
        grid_items_html += (
            f'<div class="matrix-cell{span_cls}">'
            f'<span class="matrix-lbl">{html.escape(etiket)}</span>'
            f'<span class="{val_cls}">{deger_str}</span>'
            f'</div>'
        )

    grid_html = f'<div class="info-matrix">{grid_items_html}</div>' if grid_items_html else ""

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
                f"<td style='text-align:left; white-space:nowrap; color:#64748b; font-weight:700;'>{birim_str}</td>"
                f"<td class='urun-miktar'>{miktar_str}</td>"
                f"</tr>"
            )

        tablo_html = (
            f"<div class='neo-table-wrap'>"
            f"<table class='urun-table'>"
            f"<thead><tr>"
            f"<th>Malzeme / Ürün</th>"
            f"<th style='text-align:left;'>Birim</th>"
            f"<th style='text-align:right;'>Miktar</th>"
            f"</tr></thead>"
            f"<tbody>{satirlar_html}</tbody>"
            f"</table>"
            f"</div>"
        )

    rozet_html = (
        f"<div class='detail-status-strip'>"
        f"<span class='op-status-badge' style='background-color:{renk};'>● {html.escape(op_val)}</span>"
        f"<span class='sevk-status-chip'>Sevk Durumu: <strong>{durum_gosterim}</strong></span>"
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
        st.session_state.flash_mesaj = f"Sipariş #{sip_no} için {karar} kararı işlendi."
        st.rerun()
    except Exception as err:
        st.error(f"Karar PostgreSQL'e yazılamadı: {err}")


@st.dialog("Revize Talebi Notu")
def revize_not_penceresi(sip_no: int, row_data):
    st.caption(f"Sipariş #{sip_no} için revize açıklamasını giriniz:")
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
# YÖNETİCİ TAM EKRAN ONAY İNCELEME KONSOLU
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
        f'<div class="review-console">'
        f'<div class="review-console-head">'
        f'<div class="review-console-title"><span class="review-id-pill">#{html.escape(str(aktif_inceleme_no))}</span><span>Yönetici Onay İnceleme</span></div>'
        f'<a data-spa="1" href="?incele_kapat=1{token_param}" target="_self" class="close-review-link" title="Listeye Dön">✕</a>'
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
# ÜST BÖLGE: 1) ÜST BAR + 3'LÜ KPI KARTLARI
# ==============================================================================
tamamlandi_siparis = len(df_sip[df_sip["operasyon"].isin(["TAMAMLANDI", "MUHASEBEYE İLETİLDİ"])])
onay_bekleyen = len(df_sip[df_sip["operasyon"] == "ONAY BEKLİYOR"])
sevk_bekleyen = len(
    df_sip[
        (~df_sip["operasyon"].isin(["TAMAMLANDI", "MUHASEBEYE İLETİLDİ", "İPTAL EDİLDİ"])) &
        (df_sip["durum"].fillna("").str.replace("i", "İ").str.upper() != "İPTAL")
    ]
)

kpi_toplam = max(tamamlandi_siparis + onay_bekleyen + sevk_bekleyen, 1)
pct_tamam = int(round((tamamlandi_siparis / kpi_toplam) * 100))
pct_onay = int(round((onay_bekleyen / kpi_toplam) * 100))
pct_sevk = int(round((sevk_bekleyen / kpi_toplam) * 100))

kpi_mod = st.session_state.kpi_mod
cls_tamamlandi = "kpi-selected" if kpi_mod == "TAMAMLANDI" else ""
cls_onay = "kpi-selected" if kpi_mod == "ONAY" else ""
cls_sevk = "kpi-selected" if kpi_mod == "SEVK" else ""

if yetki_tipi == "MUSTERI":
    baslik_metni = f"SAYAR YAPI · {html.escape(str(yetki_deger))}"
    alt_metin = "Müşteri İzleme"
elif yetki_tipi == "SIPARIS_VEREN":
    baslik_metni = f"SAYAR YAPI · {html.escape(str(yetki_deger))}"
    alt_metin = "Personel Takip"
else:
    baslik_metni = "SAYAR YAPI"
    alt_metin = "Canlı Lojistik Radarı"

st.markdown(
    f'<div class="command-header">'
    f'<div class="brand-cluster">'
    f'{LOGO_HTML}'
    f'<div class="brand-text-wrap">'
    f'<div class="brand-title-row">'
    f'<span class="brand-name">{baslik_metni}</span>'
    f'<span class="live-pill"><span class="live-dot-wrap"><span class="live-dot-ring"></span><span class="live-dot-core"></span></span>CANLI</span>'
    f'</div>'
    f'<div class="brand-sub-row"><span>{alt_metin}</span><span>•</span><span id="sy-live-clock" class="telemetry-clock">{anlik_saat}</span></div>'
    f'</div>'
    f'</div>'
    f'<div class="header-actions">'
    f'<a data-spa="1" href="{refresh_href}" target="_self" class="cmd-icon-btn" title="Verileri Yenile">↻</a>'
    f'<a data-spa="1" href="?action=logout" target="_self" class="cmd-icon-btn" title="Güvenli Çıkış">⏻</a>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

st.markdown(
    f'<div class="kpi-deck">'
    f'<a data-spa="1" href="?kpi=TAMAMLANDI{token_param}" target="_self" class="kpi-tile kpi-t-blue {cls_tamamlandi}" title="Tamamlanan siparişleri filtrele">'
    f'<div class="kpi-tile-top"><span class="kpi-tag">Tamamlanan</span><span class="kpi-badge-dot"></span></div>'
    f'<div class="kpi-tile-mid"><span class="kpi-num">{tamamlandi_siparis}</span><span class="kpi-pct">%{pct_tamam}</span></div>'
    f'<div class="kpi-mini-bar"><div class="kpi-mini-fill" style="width:{max(pct_tamam, 6)}%;"></div></div>'
    f'</a>'
    f'<a data-spa="1" href="?kpi=ONAY{token_param}" target="_self" class="kpi-tile kpi-t-amber {cls_onay}" title="Onay bekleyenleri filtrele">'
    f'<div class="kpi-tile-top"><span class="kpi-tag">Onay Bekleyen</span><span class="kpi-badge-dot"></span></div>'
    f'<div class="kpi-tile-mid"><span class="kpi-num">{onay_bekleyen}</span><span class="kpi-pct">%{pct_onay}</span></div>'
    f'<div class="kpi-mini-bar"><div class="kpi-mini-fill" style="width:{max(pct_onay, 6)}%;"></div></div>'
    f'</a>'
    f'<a data-spa="1" href="?kpi=SEVK{token_param}" target="_self" class="kpi-tile kpi-t-emerald {cls_sevk}" title="Sevk bekleyen aktif siparişleri filtrele">'
    f'<div class="kpi-tile-top"><span class="kpi-tag">Sevk Bekleyen</span><span class="kpi-badge-dot"></span></div>'
    f'<div class="kpi-tile-mid"><span class="kpi-num">{sevk_bekleyen}</span><span class="kpi-pct">%{pct_sevk}</span></div>'
    f'<div class="kpi-mini-bar"><div class="kpi-mini-fill" style="width:{max(pct_sevk, 6)}%;"></div></div>'
    f'</a>'
    f'</div>',
    unsafe_allow_html=True
)

# ==============================================================================
# ÜST BÖLGE: 2) ARAMA & FİLTRE ÇUBUĞU
# ==============================================================================
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
        placeholder="🔎 Sipariş No, Firma, Müşteri, Şantiye...",
        label_visibility="collapsed"
    )

with col_filtre:
    with st.popover(popover_etiket, use_container_width=True):
        st.markdown("**Akıllı Filtre Merkezi**")
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

# Flash Bildirim Bandı
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

# ==============================================================================
# FİLTRELEME + SABİT "AKTİF SEVKİYAT AKIŞI" ŞERİDİ + ALTINDA KAYDIRMALI LİSTE
# ==============================================================================
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

MOD_ETIKET = {
    "SEVK": "Aktif Sevkiyat Akışı",
    "ONAY": "Onay Bekleyenler",
    "TAMAMLANDI": "Tamamlanan Arşiv"
}

if toplam_filtrelenen == 0:
    st.markdown(
        '<div class="empty-state-box">'
        '<div class="empty-state-icon">📡</div>'
        '<div class="empty-state-title">Kriterlere Uygun Kayıt Bulunamadı</div>'
        '<div class="empty-state-desc">Arama terimini değiştirebilir veya aktif filtreleri tek dokunuşla sıfırlayabilirsiniz.</div>'
        '</div>',
        unsafe_allow_html=True
    )
    col_e1, col_e2, col_e3 = st.columns([1, 2, 1])
    with col_e2:
        st.button("↻ Tüm Filtreleri Temizle", on_click=filtreleri_sifirla, use_container_width=True, type="primary")
else:
    st.markdown(
        f'<div class="feed-header-bar">'
        f'<span class="feed-count-pill">Akış: <strong>{gosterilen_adet}</strong> / {toplam_filtrelenen}</span>'
        f'<span class="feed-mode-badge">{MOD_ETIKET.get(kpi_mod, "Canlı Akış")}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    kart_parcalari = ['<div id="sy-scroll-stream" class="sy-scroll-stream"><div class="sip-stream">']
    for _, row in filtered.head(gosterilen_limit).iterrows():
        sip_no = row.get("siparis_no", "-")
        op_val = str(row.get("operasyon") or "-")
        op_upper = op_val.upper()
        st_info = OP_STYLE.get(op_upper, DEFAULT_OP_STYLE)

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
            rota_html = f'{html.escape(f_md)}'
        else:
            rota_html = f'{html.escape(f_md)} <span class="route-arrow">➔</span> {html.escape(m_md)}'

        dot_pulse_cls = " pulse" if st_info["pulse"] else ""
        pending_cls = " is-pending-approval" if op_upper == "ONAY BEKLİYOR" else ""
        card_style = (
            f'--accent-color:{st_info["color"]};'
            f'--accent-bg:{st_info["bg"]};'
            f'--accent-border:{st_info["border"]};'
        )

        onay_buton_html = ""
        if yetki_tipi == "YONETICI" and op_upper == "ONAY BEKLİYOR":
            onay_buton_html = (
                f'<a data-spa="1" href="?incele={sip_no}{token_param}" target="_self" class="quick-inspect-btn" title="Siparişi İncele">'
                f'<span class="qi-icon">✓</span>'
                f'<span class="qi-txt">ONAY</span>'
                f'</a>'
            )

        kart_parcalari.append(
            f'<div class="sip-row-wrap">'
            f'<details class="neo-card{pending_cls}" style="{card_style}">'
            f'<summary>'
            f'<div class="card-left-rail">'
            f'<span class="sip-no-chip"><span class="status-dot{dot_pulse_cls}"></span>#{html.escape(str(sip_no))}</span>'
            f'<div class="card-main-info">'
            f'<div class="card-route-line">{rota_html}</div>'
            f'<div class="card-meta-line"><span class="card-meta-site">📍 {html.escape(s_md)}</span><span>•</span><span class="card-meta-date">{html.escape(t_md)}</span></div>'
            f'</div>'
            f'</div>'
            f'<div class="card-right-rail">'
            f'<span class="mini-op-pill">{html.escape(st_info["short"])}</span>'
            f'<span class="neo-chevron">❯</span>'
            f'</div>'
            f'</summary>'
            f'<div class="neo-card-body">{rozet_html}{grid_html}{tablo_html}</div>'
            f'</details>'
            f'{onay_buton_html}'
            f'</div>'
        )

    kart_parcalari.append('</div>')

    yuzde = int((gosterilen_adet / toplam_filtrelenen) * 100) if toplam_filtrelenen > 0 else 100
    kart_parcalari.append(
        f'<div class="pagination-box">'
        f'<div class="pagination-text">{toplam_filtrelenen} siparişten {gosterilen_adet} tanesi canlı akışta (%{yuzde})</div>'
        f'<div class="progress-track"><div class="progress-fill" style="width:{yuzde}%;"></div></div>'
        f'</div>'
    )

    if gosterilen_adet < toplam_filtrelenen:
        kalan = toplam_filtrelenen - gosterilen_adet
        eklenecek = min(50, kalan)
        kart_parcalari.append(
            f'<a data-spa="1" href="?action=more{token_param}" target="_self" class="load-more-link">'
            f'Daha Fazla Sipariş Yükle (+{eklenecek})'
            f'</a>'
        )

    kart_parcalari.append('</div>')
    st.markdown("".join(kart_parcalari), unsafe_allow_html=True)
