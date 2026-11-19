import os
import io
import json
import time
import html
import base64
import sqlite3
import tempfile
import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from cryptography.fernet import Fernet
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Railway ortam değişkeninden secrets.toml dosyasını otomatik oluştur
if os.environ.get("STREAMLIT_SECRETS"):
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMLIT_SECRETS"])

NTFY_TOPIC = "sayar_yapi_siparis_2026"
QUEUE_FILE_NAME = "mobil_onaylar.json"


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

# Sayfa ve Mobil Görünüm Ayarları
st.set_page_config(
    page_title="Sayar Yapı | Sipariş İzleme",
    page_icon=LOGO_DATA_URI if LOGO_DATA_URI else "🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# iOS Ana Ekran İkonunu Çekirdek Dosyalara Dokunmadan <head> İçine Enjekte Et
logo_hedef_url = ""
try:
    if "LOGO_URL" in st.secrets:
        logo_hedef_url = str(st.secrets["LOGO_URL"]).strip()
except Exception:
    pass

if not logo_hedef_url and LOGO_DATA_URI:
    logo_hedef_url = LOGO_DATA_URI

if logo_hedef_url:
    components.html(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;
            const head = doc.head || doc.getElementsByTagName('head')[0];
            if (!head) return;
            doc.querySelectorAll('link[rel*="apple-touch-icon"]').forEach(el => el.remove());
            const l1 = doc.createElement('link');
            l1.rel = 'apple-touch-icon';
            l1.sizes = '180x180';
            l1.href = {json.dumps(logo_hedef_url)};
            head.appendChild(l1);
        }})();
        </script>
        """,
        height=0,
        width=0
    )

# Özel CSS: Kurumsal Çelik & Beton (Sıkılaştırılmış Kompakt Aydınlık Tema)
st.markdown("""
<style>
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
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
}
.block-container {
    padding-top: 0.45rem !important;
    padding-bottom: 1.5rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
}
[data-testid="stVerticalBlock"] {
    gap: 0.45rem !important;
}
.header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-left: 5px solid #f97316;
    border-radius: 10px;
    padding: 9px 12px;
    margin-bottom: 4px;
    color: #f8fafc;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.14);
    gap: 8px;
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
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 10px;
    margin-bottom: 10px;
}
a.kpi-card {
    display: block;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 9px;
    padding: 7px 8px;
    text-align: center;
    text-decoration: none !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    transition: transform 0.1s ease, box-shadow 0.15s ease;
    cursor: pointer;
}
a.kpi-card:hover {
    background-color: #f8fafc;
}
a.kpi-card:active {
    transform: scale(0.98);
}
.kpi-blue { border-top: 3px solid #0284c7 !important; }
.kpi-orange { border-top: 3px solid #f97316 !important; }
.kpi-green { border-top: 3px solid #16a34a !important; }
.kpi-active {
    background-color: #ffffff !important;
    border: 2px solid #ef4444 !important;
    box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2);
}
.kpi-label {
    font-size: 11px;
    color: #475569;
    font-weight: 600;
    margin-bottom: 1px;
    white-space: nowrap;
}
.kpi-value {
    font-size: 19px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
}
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 6px !important;
    margin-top: 12px !important;
}
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:first-child {
    flex: 1 1 auto !important;
    min-width: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:last-child {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 54px !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
    color: #0f172a !important;
}
div[data-testid="stTextInput"] input {
    height: 38px !important;
    padding-top: 6px !important;
    padding-bottom: 6px !important;
}
div[data-testid="stForm"] {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    padding: 14px !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
}
div[data-testid="stPopover"] > button {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
    color: #0f172a !important;
    height: 38px !important;
    padding: 0 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
}
div[data-testid="stPopover"] > button:hover {
    border-color: #f97316 !important;
    background-color: #fff7ed !important;
}
.sip-list-container {
    display: flex;
    flex-direction: column;
    gap: 6px;
    width: 100%;
    margin: 0;
    padding: 0;
}
.sip-row-wrap {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: flex-start;
    gap: 6px;
    width: 100%;
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
details.custom-sip-card {
    flex: 1 1 auto;
    min-width: 0;
    margin: 0;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 9px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    overflow: hidden;
    box-sizing: border-box;
}
details.custom-sip-card > summary {
    list-style: none;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    cursor: pointer;
    user-select: none;
    height: 48px;
    box-sizing: border-box;
}
details.custom-sip-card > summary::-webkit-details-marker {
    display: none;
}
details.custom-sip-card > summary:hover {
    background-color: #f8fafc;
}
.custom-card-arrow {
    font-size: 11px;
    color: #475569;
    font-weight: 700;
    transition: transform 0.15s ease;
    flex-shrink: 0;
}
details.custom-sip-card[open] .custom-card-arrow {
    transform: rotate(90deg);
}
.custom-card-lines {
    flex: 1;
    min-width: 0;
    font-size: 13px;
    line-height: 1.3;
    color: #0f172a;
}
.custom-card-line1 {
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.custom-card-line2 {
    font-weight: 400;
    color: #334155;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.custom-card-body {
    padding: 6px 10px 10px 10px;
    border-top: 1px solid #e2e8f0;
    background-color: #ffffff;
}
a.mini-onay-btn {
    flex: 0 0 42px;
    width: 42px;
    height: 48px;
    box-sizing: border-box;
    background-color: #f97316;
    border: 1px solid #ea580c;
    border-radius: 9px;
    color: #ffffff !important;
    font-size: 20px;
    font-weight: 900;
    text-decoration: none !important;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 2px rgba(249, 115, 22, 0.25);
}
a.mini-onay-btn:active {
    background-color: #ea580c;
    transform: scale(0.96);
}
/* Tam Ekran Onay İnceleme Kartı */
.fullscreen-review-card {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-top: 4px solid #f97316;
    border-radius: 11px;
    padding: 10px 11px 10px 11px;
    margin-top: 2px;
    margin-bottom: 8px;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.07);
}
.fullscreen-review-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 6px;
    margin-bottom: 8px;
    gap: 8px;
}
.fullscreen-review-title {
    font-size: 14px;
    font-weight: 800;
    color: #0f172a;
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
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    text-decoration: none !important;
    flex-shrink: 0;
}
a.close-review-link:active {
    background-color: #e2e8f0;
}
/* İnceleme Modu Aksiyon Satırı: 3 Eşit Sütun ve Renkler */
.review-actions-grid {
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
    gap: 8px !important;
    width: 100% !important;
    margin-top: 8px !important;
    padding-top: 8px !important;
    border-top: 1px solid #cbd5e1 !important;
    box-sizing: border-box !important;
}
.review-actions-grid [data-testid="stHorizontalBlock"],
.review-actions-grid .stHorizontalBlock {
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
    gap: 8px !important;
    width: 100% !important;
    margin: 0 !important;
}
.review-actions-grid [data-testid="stHorizontalBlock"] > div,
.review-actions-grid .stHorizontalBlock > div,
.review-actions-grid [data-testid="column"] {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    flex: unset !important;
}
.review-actions-grid button,
.review-actions-grid .stButton > button {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: 40px !important;
    font-weight: 800 !important;
    font-size: 12px !important;
    border-radius: 9px !important;
    padding: 0 4px !important;
    white-space: nowrap !important;
}
.review-actions-grid [data-testid="stHorizontalBlock"] > div:nth-child(1) button,
.review-actions-grid .stHorizontalBlock > div:nth-child(1) button {
    background-color: #16a34a !important;
    border: 1px solid #15803d !important;
    color: #ffffff !important;
}
.review-actions-grid [data-testid="stHorizontalBlock"] > div:nth-child(1) button:hover {
    background-color: #15803d !important;
}
.review-actions-grid [data-testid="stHorizontalBlock"] > div:nth-child(2) button,
.review-actions-grid .stHorizontalBlock > div:nth-child(2) button {
    background-color: #facc15 !important;
    border: 1px solid #eab308 !important;
    color: #0f172a !important;
}
.review-actions-grid [data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover {
    background-color: #eab308 !important;
}
.review-actions-grid [data-testid="stHorizontalBlock"] > div:nth-child(3) button,
.review-actions-grid .stHorizontalBlock > div:nth-child(3) button {
    background-color: #dc2626 !important;
    border: 1px solid #b91c1c !important;
    color: #ffffff !important;
}
.review-actions-grid [data-testid="stHorizontalBlock"] > div:nth-child(3) button:hover {
    background-color: #b91c1c !important;
}
.info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 5px 8px;
    font-size: 12px;
    margin-top: 6px;
    margin-bottom: 8px;
    padding: 7px 8px;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
.info-item-label {
    font-size: 10px;
    color: #64748b;
    display: block;
}
.info-item-val {
    font-weight: 600;
    color: #0f172a;
}
.info-item-val-red {
    font-weight: 800;
    color: #dc2626;
}
.info-item-val-navy {
    font-weight: 700;
    color: #1e3a8a;
}
.urun-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 4px;
    font-size: 12px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}
.urun-table th {
    background-color: #1e293b;
    color: #f8fafc;
    text-align: left;
    padding: 5px 7px;
    font-weight: 600;
    font-size: 11px;
}
.urun-table td {
    padding: 5px 7px;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
}
.urun-table tr:nth-child(even) td {
    background-color: #f8fafc;
}
.urun-miktar {
    font-weight: 700;
    text-align: right;
    white-space: nowrap;
}
.badge {
    padding: 3px 8px;
    border-radius: 5px;
    color: white;
    font-weight: bold;
    font-size: 11px;
    display: inline-block;
}
.durum-plain {
    color: #0f172a;
    font-weight: 600;
    font-size: 11.5px;
}
.empty-state-box {
    background-color: #ffffff;
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
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
    font-size: 14.5px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 4px;
}
.empty-state-desc {
    font-size: 12.5px;
    color: #64748b;
}
.pagination-box {
    margin-top: 12px;
    margin-bottom: 6px;
    text-align: center;
}
.pagination-text {
    font-size: 11.5px;
    color: #64748b;
    margin-bottom: 5px;
    font-weight: 500;
}
.progress-track {
    width: 100%;
    max-width: 240px;
    height: 5px;
    background-color: #e2e8f0;
    border-radius: 999px;
    margin: 0 auto 8px auto;
    overflow: hidden;
}
.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #0f172a 0%, #f97316 100%);
    border-radius: 999px;
    transition: width 0.25s ease;
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


# Google Drive API Servisi ve Onay Kuyruğu İşlemleri
def get_gdrive_service():
    sa_info = dict(st.secrets["GDRIVE_SERVICE_ACCOUNT"])
    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def onay_kuyruguna_yaz(siparis_no: int, karar: str, aciklama: str = ""):
    """Kararı Google Drive'daki mobil_onaylar.json dosyasına çakışmasız şekilde ekler."""
    service = get_gdrive_service()
    folder_id = str(st.secrets["GDRIVE_FOLDER_ID"]).strip()

    query = f"name='{QUEUE_FILE_NAME}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    mevcut_kayitlar = []
    file_id = None

    if files:
        file_id = files[0]["id"]
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        try:
            icerik = fh.getvalue().decode("utf-8").strip()
            if icerik:
                mevcut_kayitlar = json.loads(icerik)
        except Exception:
            mevcut_kayitlar = []

    mevcut_kayitlar = [k for k in mevcut_kayitlar if int(k.get("siparis_no", -1)) != int(siparis_no)]
    mevcut_kayitlar.append({
        "siparis_no": int(siparis_no),
        "karar": karar,
        "not": aciklama.strip(),
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    json_bytes = json.dumps(mevcut_kayitlar, ensure_ascii=False, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(json_bytes), mimetype="application/json", resumable=False)

    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        file_metadata = {
            "name": QUEUE_FILE_NAME,
            "parents": [folder_id]
        }
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()


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
            timeout=5
        )
    except Exception:
        pass


# Şifreli Oturum Jetonu (Beni Hatırla) Oluşturma ve Doğrulama
def token_olustur(yetki_tipi, yetki_deger, gun=90):
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
            f'<div class="header-banner"><div class="header-info">'
            f'<div class="header-title">{LOGO_HTML}<span>SAYAR YAPI</span></div>'
            f'<div class="header-sub">Sipariş Takip ve İzleme Sistemi</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        if url_musteri:
            st.caption(f"Müşteri Girişi: **{url_musteri}**")
        elif url_veren:
            st.caption(f"Personel Girişi: **{url_veren}**")

        with st.form("login_form", clear_on_submit=False):
            pin = st.text_input("Erişim Şifresi:", type="password")
            beni_hatirla = st.checkbox("Beni Hatırla", value=True)
            giris_yapildi = st.form_submit_button("Giriş Yap", use_container_width=True, type="primary")

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
    st.rerun()

if "incele_kapat" in st.query_params:
    st.session_state.onay_inceleme_sip_no = None
    st.query_params.pop("incele_kapat", None)
    st.rerun()

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


# 2. Google Drive'dan Şifreli DB İndirme ve RAM'de Çözme
@st.cache_data(ttl=15)
def verileri_getir():
    file_id = st.secrets["GDRIVE_FILE_ID"]
    secret_key = st.secrets["DB_SECRET_KEY"].encode("utf-8")

    download_url = f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
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
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Drive'daki mobil_onaylar.json kuyruğunu da oku ve bekleyen kararları anlık yansıt
    try:
        service = get_gdrive_service()
        folder_id = str(st.secrets["GDRIVE_FOLDER_ID"]).strip()
        q = f"name='{QUEUE_FILE_NAME}' and '{folder_id}' in parents and trashed=false"
        res = service.files().list(q=q, fields="files(id)").execute()
        files = res.get("files", [])
        if files:
            req = service.files().get_media(fileId=files[0]["id"])
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            kuyruk = json.loads(fh.getvalue().decode("utf-8") or "[]")
            for k in kuyruk:
                s_no = int(k.get("siparis_no", -1))
                karar = str(k.get("karar") or "").strip()
                k_not = str(k.get("not") or "").strip()
                mask = df_siparisler["siparis_no"] == s_no
                if mask.any() and karar:
                    db_op = str(df_siparisler.loc[mask, "operasyon"].iloc[0] or "").upper()
                    if db_op == "ONAY BEKLİYOR":
                        df_siparisler.loc[mask, "operasyon"] = karar
                        if k_not:
                            mevcut_not = str(df_siparisler.loc[mask, "notlar"].iloc[0] or "").strip()
                            ek_not = f"[Yönetici Notu - {karar}]: {k_not}"
                            df_siparisler.loc[mask, "notlar"] = f"{mevcut_not}\n{ek_not}".strip() if mevcut_not else ek_not
    except Exception:
        pass

    return df_siparisler, df_kalemler


token_param = f"&token={aktif_token}" if aktif_token else ""
refresh_href = f"?action=refresh{token_param}"

# İnceleme modunda en üstteki SAYAR YAPI + yenile/çıkış barı kaldırılır
if not inceleme_aktif_mi:
    if yetki_tipi == "MUSTERI":
        baslik_metni = f'{LOGO_HTML}<span>SAYAR YAPI | {html.escape(str(yetki_deger))}</span>'
        alt_metin = "Müşteri Sipariş İzleme Paneli"
    elif yetki_tipi == "SIPARIS_VEREN":
        baslik_metni = f'{LOGO_HTML}<span>SAYAR YAPI | {html.escape(str(yetki_deger))}</span>'
        alt_metin = "Personel Sipariş İzleme Paneli"
    else:
        baslik_metni = f'{LOGO_HTML}<span>SAYAR YAPI | Sipariş İzleme</span>'
        alt_metin = "Yönetici Canlı Takip Paneli"

    st.markdown(
        f'<div class="header-banner">'
        f'<div class="header-info"><div class="header-title">{baslik_metni}</div><div class="header-sub">{alt_metin}</div></div>'
        f'<div class="header-actions">'
        f'<a href="{refresh_href}" target="_self" class="icon-btn" title="Yenile">🔄</a>'
        f'<a href="?action=logout" target="_self" class="icon-btn" title="Çıkış">🚪</a>'
        f'</div></div>',
        unsafe_allow_html=True
    )

try:
    df_sip, df_kalem = verileri_getir()
except Exception as e:
    st.error(f"Veritabanı okunamadı. Bağlantıyı ve anahtarı kontrol edin.\nDetay: {e}")
    st.stop()

# Mobil oturumda verilen kararları ana DB güncellenene kadar anlık yansıt
if st.session_state.yerel_kararlar and not df_sip.empty:
    for s_no, karar_bilgi in list(st.session_state.yerel_kararlar.items()):
        mask = df_sip["siparis_no"] == int(s_no)
        if mask.any():
            db_op = str(df_sip.loc[mask, "operasyon"].iloc[0] or "").upper()
            if db_op == "ONAY BEKLİYOR":
                df_sip.loc[mask, "operasyon"] = karar_bilgi["karar"]
                if karar_bilgi.get("not"):
                    mevcut_not = str(df_sip.loc[mask, "notlar"].iloc[0] or "").strip()
                    ek_not = f"[Yönetici Notu - {karar_bilgi['karar']}]: {karar_bilgi['not']}"
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
    "ONAYLANDI": "#16a34a",
    "REVİZE İSTENDİ": "#f59e0b",
    "REDDEDİLDİ": "#dc2626",
    "TAMAMLANDI": "#16a34a",
    "MUHASEBEYE İLETİLDİ": "#16a34a",
    "İPTAL EDİLDİ": "#dc2626",
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
            val_cls = "info-item-val-red"
        elif vurgulu_onay and col_lower in lacivert_alanlar:
            val_cls = "info-item-val-navy"
        else:
            val_cls = "info-item-val"

        span_style = ' style="grid-column: span 2;"' if col_lower == "notlar" or len(deger_str) > 35 else ""
        grid_items_html += (
            f'<div{span_style}>'
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
        f"<span class='badge' style='background-color:{renk};'>{html.escape(op_val)}</span> &nbsp; "
        f"<span class='durum-plain'>Durum: {durum_gosterim}</span>"
    )
    return rozet_html, grid_html, tablo_html


def karari_uygula(sip_no: int, row_data, karar: str, aciklama: str = ""):
    """Kararı Drive kuyruğuna yazar, yerel oturuma işler ve ntfy bildirimi gönderir."""
    try:
        onay_kuyruguna_yaz(sip_no, karar, aciklama)
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
        st.session_state.onay_inceleme_sip_no = None
        st.session_state.flash_mesaj = f"Sipariş #{sip_no} {karar} kararı iletildi."
        st.cache_data.clear()
        st.rerun()
    except Exception as err:
        st.error(f"Karar Google Drive'a yazılamadı: {err}")


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
    rozet_html, grid_html, tablo_html = siparis_detay_html_olustur(inceleme_row, aktif_inceleme_no, vurgulu_onay=True)

    st.markdown(
        f'<div class="fullscreen-review-card">'
        f'<div class="fullscreen-review-header">'
        f'<div class="fullscreen-review-title">🟠 SİPARİŞ ONAY İNCELEME — #{html.escape(str(aktif_inceleme_no))}</div>'
        f'<a href="?incele_kapat=1{token_param}" target="_self" class="close-review-link" title="Kapat">✕</a>'
        f'</div>'
        f'{rozet_html}'
        f'{grid_html}'
        f'{tablo_html}'
        f'<div class="review-actions-grid" id="review-actions-target"></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button("ONAYLA", use_container_width=True, key="btn_onayla"):
            karari_uygula(aktif_inceleme_no, inceleme_row, "ONAYLANDI", "")
    with col_b2:
        if st.button("REVİZE", use_container_width=True, key="btn_revize"):
            revize_not_penceresi(aktif_inceleme_no, inceleme_row)
    with col_b3:
        if st.button("REDDET", use_container_width=True, key="btn_reddet"):
            karari_uygula(aktif_inceleme_no, inceleme_row, "REDDEDİLDİ", "")

    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const target = doc.getElementById('review-actions-target');
            if (!target) return;
            const btns = Array.from(doc.querySelectorAll('button')).filter(b => {
                const t = (b.innerText || '').trim();
                return t === 'ONAYLA' || t === 'REVİZE' || t === 'REDDET';
            });
            if (btns.length === 3) {
                const rowBlock = btns[0].closest('[data-testid="stHorizontalBlock"]');
                if (rowBlock && rowBlock.parentElement !== target) {
                    target.innerHTML = '';
                    target.appendChild(rowBlock);
                }
            }
        })();
        </script>
        """,
        height=0,
        width=0
    )

    st.stop()

# ==============================================================================
# ANA LİSTE VE KPI GÖRÜNÜMÜ
# ==============================================================================
flash_box = st.empty()
flash_msg = st.session_state.flash_mesaj
if flash_msg:
    flash_box.success(flash_msg)
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
cls_tamamlandi = "kpi-active" if kpi_mod == "TAMAMLANDI" else ""
cls_onay = "kpi-active" if kpi_mod == "ONAY" else ""
cls_sevk = "kpi-active" if kpi_mod == "SEVK" else ""

st.markdown(
    f'<div class="kpi-grid">'
    f'<a href="?kpi=TAMAMLANDI{token_param}" target="_self" class="kpi-card kpi-blue {cls_tamamlandi}" title="Sadece tamamlanan siparişleri göster">'
    f'<div class="kpi-label">Tamamlandı</div><div class="kpi-value">{tamamlandi_siparis}</div></a>'
    f'<a href="?kpi=ONAY{token_param}" target="_self" class="kpi-card kpi-orange {cls_onay}" title="Sadece onay bekleyenleri göster">'
    f'<div class="kpi-label">Onay Bekleyen</div><div class="kpi-value">{onay_bekleyen}</div></a>'
    f'<a href="?kpi=SEVK{token_param}" target="_self" class="kpi-card kpi-green {cls_sevk}" title="Sadece devam edenleri göster">'
    f'<div class="kpi-label">Sevk Bekleyen</div><div class="kpi-value">{sevk_bekleyen}</div></a>'
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
popover_etiket = "⚙️ •" if ek_filtre_aktif else "⚙️"

col_arama, col_filtre = st.columns([5, 1])
with col_arama:
    arama = st.text_input(
        "Arama",
        key="arama_metni",
        placeholder="🔍 Sipariş No, Firma, Müşteri, Şantiye...",
        label_visibility="collapsed"
    )

with col_filtre:
    with st.popover(popover_etiket, use_container_width=True):
        st.markdown("**Detaylı Filtreleme**")
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

filtered = df_sip.copy()

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
        '<div class="empty-state-icon">🔍</div>'
        '<div class="empty-state-title">Eşleşen Sipariş Bulunamadı</div>'
        '<div class="empty-state-desc">Arama kriterlerinizi değiştirerek veya aktif filtreleri temizleyerek tekrar deneyebilirsiniz.</div>'
        '</div>',
        unsafe_allow_html=True
    )
    col_e1, col_e2, col_e3 = st.columns([1, 2, 1])
    with col_e2:
        st.button("🔄 Tüm Filtreleri Temizle", on_click=filtreleri_sifirla, use_container_width=True, type="primary")
else:
    st.caption(f"Gösterilen sipariş sayısı: **{gosterilen_adet} / {toplam_filtrelenen}**")

    kart_parcalari = ['<div class="sip-list-container">']
    for _, row in filtered.head(gosterilen_limit).iterrows():
        sip_no = row.get("siparis_no", "-")
        op_val = str(row.get("operasyon") or "-")
        op_upper = op_val.upper()
        durum_ikon = OP_IKON.get(op_upper, "⚪")

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
            satir1_html = f"{durum_ikon} #{html.escape(str(sip_no))} | {html.escape(f_md)}"
        else:
            satir1_html = f"{durum_ikon} #{html.escape(str(sip_no))} | {html.escape(f_md)} ➔ {html.escape(m_md)}"
        satir2_html = f"📍 {html.escape(s_md)} &nbsp; • &nbsp; {html.escape(t_md)}"

        onay_buton_html = ""
        if yetki_tipi == "YONETICI" and op_upper == "ONAY BEKLİYOR":
            onay_buton_html = f'<a href="?incele={sip_no}{token_param}" target="_self" class="mini-onay-btn" title="Siparişi İncele">✓</a>'

        kart_parcalari.append(
            f'<div class="sip-row-wrap">'
            f'<details class="custom-sip-card">'
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

    kart_parcalari.append('</div>')
    st.markdown("".join(kart_parcalari), unsafe_allow_html=True)

    yuzde = int((gosterilen_adet / toplam_filtrelenen) * 100) if toplam_filtrelenen > 0 else 100
    st.markdown(
        f'<div class="pagination-box">'
        f'<div class="pagination-text">{toplam_filtrelenen} siparişten {gosterilen_adet} tanesi gösteriliyor</div>'
        f'<div class="progress-track"><div class="progress-fill" style="width:{yuzde}%;"></div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if gosterilen_adet < toplam_filtrelenen:
        kalan = toplam_filtrelenen - gosterilen_adet
        eklenecek = min(50, kalan)
        if st.button(f"Daha Fazla Göster (+{eklenecek})", use_container_width=True):
            st.session_state.sayfa_limiti += 50
            st.rerun()

if flash_msg:
    time.sleep(2)
    flash_box.empty()
