import os
import io
import json
import time
import hmac
import html
import base64
import hashlib
import sqlite3
import tempfile
import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Railway ortam değişkeninden secrets.toml dosyasını sadece yoksa oluştur
if os.environ.get("STREAMLIT_SECRETS") and not os.path.exists(".streamlit/secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMLIT_SECRETS"])

NTFY_TOPIC = "sayar_yapi_kamyon_2026x"
NEW_ORDER_QUEUE_FILE = "mobil_yeni_siparisler.json"


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
    page_title="Sayar Yapı | Yeni Sipariş",
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

# mobil_izleme.py kart ve tablo yapısına birebir uyumlu CSS
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
    padding-bottom: 4.6rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
}
[data-testid="stVerticalBlock"] {
    gap: 0.35rem !important;
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
    margin-bottom: 4px;
    opacity: 1;
    transition: opacity 0.35s ease;
    box-shadow: 0 2px 6px rgba(22, 163, 74, 0.12);
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
div[data-testid="stForm"] {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    padding: 14px !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
}

/* mobil_izleme.py Tam Ekran İnceleme Kartı Yapısı */
.fullscreen-review-card {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-top: 4px solid #f97316;
    border-radius: 11px;
    padding: 10px 11px 12px 11px;
    margin-top: 2px;
    margin-bottom: 10px;
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
.info-item-label {
    font-size: 10px;
    color: #64748b;
    display: block;
    font-weight: 600;
    margin-bottom: 1px;
}

/* Form kontrollerini mobil_izleme.py alanlarıyla uyumlu kompakt yap */
div[data-testid="stTextInput"] input,
div[data-testid="stDateInput"] input,
div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 7px !important;
    color: #0f172a !important;
    min-height: 34px !important;
    height: 34px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
}
div[data-testid="stTextInput"] input:disabled {
    background-color: #e2e8f0 !important;
    color: #0f172a !important;
    font-weight: 800 !important;
    opacity: 1 !important;
}
div[data-testid="stButton"] button {
    min-height: 34px !important;
    height: 34px !important;
    padding: 0 8px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    border-radius: 7px !important;
    width: 100% !important;
}

/* Eklenen ürün tablosu (mobil_izleme.py .urun-table ile aynı) */
.urun-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 6px;
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
.bos-liste-kutusu {
    background-color: #f8fafc;
    border: 1px dashed #cbd5e1;
    border-radius: 8px;
    padding: 10px;
    text-align: center;
    font-size: 12px;
    color: #64748b;
    margin-top: 6px;
}

/* En altta sabit bar: KAYDET | TEMİZLE | KAPAT */
.sticky-bottom-bar {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    padding: 7px 0.75rem 9px 0.75rem !important;
    background: linear-gradient(180deg, rgba(241,245,249,0.9) 0%, #f1f5f9 30%) !important;
    backdrop-filter: blur(4px);
    border-top: 1px solid #cbd5e1;
    z-index: 9999 !important;
}
.sticky-bottom-bar button {
    height: 40px !important;
    min-height: 40px !important;
    font-size: 12.5px !important;
    font-weight: 800 !important;
    border-radius: 9px !important;
}
.sticky-bottom-bar button[kind="primary"] {
    background-color: #16a34a !important;
    border: 1px solid #15803d !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_gdrive_service():
    sa_info = dict(st.secrets["GDRIVE_SERVICE_ACCOUNT"])
    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


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
            f'<div class="header-sub">Yeni Sipariş Giriş Sistemi</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
        if url_veren:
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
                st.error("Hatalı erişim şifresi!")
        st.stop()


check_password()


@st.cache_data(ttl=60, show_spinner=False)
def secim_listelerini_getir():
    varsayilan = {
        "firma": [],
        "musteri": [],
        "santiye": [],
        "sehir": ["İSTANBUL"],
        "arac": ["TIR ( 27 TON )"],
        "fabrika": [],
        "nakliye": [],
        "siparis_gecen": [],
        "siparis_veren": [],
        "urunler_detay": [],
        "birim": ["ADET", "TON", "KG", "M2", "M3", "MT", "TORBA", "PALET", "PAKET"]
    }
    try:
        file_id = str(st.secrets["GDRIVE_FILE_ID"]).strip()
        if not file_id:
            return varsayilan

        service = get_gdrive_service()
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        db_bytes = fh.getvalue()
        if not db_bytes:
            return varsayilan

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
                tmp_file.write(db_bytes)
                tmp_path = tmp_file.name

            conn = sqlite3.connect(tmp_path, check_same_thread=False)
            try:
                df_tanim = pd.read_sql_query("SELECT * FROM tanimlar", conn)
                df_sip = pd.read_sql_query("SELECT * FROM siparisler ORDER BY siparis_no DESC LIMIT 1000", conn)
            finally:
                conn.close()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        def tanim_listesi(kat):
            if df_tanim.empty or "kategori" not in df_tanim.columns:
                return []
            sub = df_tanim[df_tanim["kategori"] == kat]
            if "aktif" in sub.columns:
                sub = sub[sub["aktif"].fillna(1) == 1]
            vals = sub["deger"].dropna().astype(str).str.strip()
            vals = vals[(vals != "") & (vals != "-")]
            return sorted(vals.unique().tolist())

        def siparis_gecmis_listesi(col):
            if df_sip.empty or col not in df_sip.columns:
                return []
            vals = df_sip[col].dropna().astype(str).str.strip()
            vals = vals[(vals != "") & (vals != "-") & (vals.str.lower() != "none") & (vals.str.lower() != "nan")]
            return sorted(vals.unique().tolist())

        varsayilan["firma"] = tanim_listesi("FİRMA") or siparis_gecmis_listesi("firma")

        arac_liste = tanim_listesi("ARAÇ") or siparis_gecmis_listesi("arac")
        if "TIR ( 27 TON )" not in arac_liste:
            arac_liste = ["TIR ( 27 TON )"] + arac_liste
        varsayilan["arac"] = arac_liste

        varsayilan["fabrika"] = tanim_listesi("FABRİKA") or siparis_gecmis_listesi("fabrika")
        varsayilan["nakliye"] = tanim_listesi("NAKLİYE") or siparis_gecmis_listesi("nakliye")
        varsayilan["siparis_gecen"] = tanim_listesi("SİPARİŞ GEÇEN") or siparis_gecmis_listesi("siparis_gecen")
        varsayilan["siparis_veren"] = tanim_listesi("SİPARİŞ VEREN") or siparis_gecmis_listesi("siparis_veren")

        varsayilan["musteri"] = sorted(list(set(tanim_listesi("MÜŞTERİ") + siparis_gecmis_listesi("musteri"))))
        varsayilan["santiye"] = sorted(list(set(tanim_listesi("ŞANTİYE") + siparis_gecmis_listesi("santiye"))))

        sehir_liste = sorted(list(set(tanim_listesi("ŞEHİR") + siparis_gecmis_listesi("sehir"))))
        if "İSTANBUL" not in sehir_liste:
            sehir_liste = ["İSTANBUL"] + sehir_liste
        varsayilan["sehir"] = sehir_liste

        t_birim = tanim_listesi("BİRİM")
        if t_birim:
            varsayilan["birim"] = t_birim

        if not df_tanim.empty and "kategori" in df_tanim.columns:
            u_sub = df_tanim[df_tanim["kategori"] == "ÜRÜN"]
            if "aktif" in u_sub.columns:
                u_sub = u_sub[u_sub["aktif"].fillna(1) == 1]
            urun_list = []
            for _, r in u_sub.iterrows():
                ad = str(r.get("deger") or "").strip()
                frm = str(r.get("firma") or "").strip() if "firma" in u_sub.columns else ""
                if ad:
                    urun_list.append({"deger": ad, "firma": frm})
            varsayilan["urunler_detay"] = sorted(urun_list, key=lambda x: x["deger"])

    except Exception:
        pass

    return varsayilan


def yeni_siparis_kuyruguna_yaz(siparis_verisi: dict):
    """Yeni siparişi Google Drive'daki mobil_yeni_siparisler.json kuyruğuna ekler."""
    service = get_gdrive_service()
    folder_id = str(st.secrets["GDRIVE_FOLDER_ID"]).strip()

    query = f"name='{NEW_ORDER_QUEUE_FILE}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
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

    mevcut_kayitlar.append(siparis_verisi)

    json_bytes = json.dumps(mevcut_kayitlar, ensure_ascii=False, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(json_bytes), mimetype="application/json", resumable=False)

    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        file_metadata = {
            "name": NEW_ORDER_QUEUE_FILE,
            "parents": [folder_id]
        }
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()


def yeni_siparis_ntfy_gonder(sip: dict):
    try:
        urun_ozet = ", ".join([f"{u['urun']} ({u['miktar']} {u['birim']})" for u in sip.get("urunler", [])[:3]])
        if len(sip.get("urunler", [])) > 3:
            urun_ozet += f" +{len(sip['urunler']) - 3} kalem"

        baslik = f"Yeni Mobil Siparis - {sip.get('musteri') or '-'}"
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


yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger
kilitli_veren = str(yetki_deger).strip() if (yetki_tipi == "SIPARIS_VEREN" and yetki_deger) else ""


def varsayilan_form_verisi():
    return {
        "siparis_tarihi": date.today(),
        "sevk_tarihi": date.today(),
        "firma": "",
        "musteri": "",
        "santiye": "",
        "sehir": "İSTANBUL",
        "fabrika": "",
        "nakliye": "",
        "arac": "TIR ( 27 TON )",
        "siparis_gecen": "",
        "siparis_veren": kilitli_veren
    }


if "form_versiyon" not in st.session_state:
    st.session_state.form_versiyon = 0
if "urun_input_versiyon" not in st.session_state:
    st.session_state.urun_input_versiyon = 0
if "eklenen_urunler" not in st.session_state:
    st.session_state.eklenen_urunler = []
if "aktif_buton_alan" not in st.session_state:
    st.session_state.aktif_buton_alan = None
if "ekran_kapali" not in st.session_state:
    st.session_state.ekran_kapali = False
if "flash_mesaj" not in st.session_state:
    st.session_state.flash_mesaj = None
if "form_data" not in st.session_state:
    st.session_state.form_data = varsayilan_form_verisi()
elif kilitli_veren:
    st.session_state.form_data["siparis_veren"] = kilitli_veren


def formu_sifirla():
    st.session_state.form_versiyon += 1
    st.session_state.urun_input_versiyon += 1
    st.session_state.eklenen_urunler = []
    st.session_state.aktif_buton_alan = None
    st.session_state.form_data = varsayilan_form_verisi()


if st.query_params.get("action") == "refresh":
    st.cache_data.clear()
    st.session_state.ekran_kapali = False
    st.query_params.pop("action", None)
    st.rerun()

if st.query_params.get("kapat") == "1":
    st.session_state.ekran_kapali = True
    st.query_params.pop("kapat", None)
    st.rerun()

aktif_token = st.session_state.get("active_token") or st.query_params.get("token", "")
token_param = f"&token={aktif_token}" if aktif_token else ""
refresh_href = f"?action=refresh{token_param}"

if not st.session_state.ekran_kapali:
    alt_baslik = f"Personel: {kilitli_veren}" if kilitli_veren else "Yönetici Canlı Sipariş Girişi"
    st.markdown(
        f'<div class="header-banner">'
        f'<div class="header-info"><div class="header-title">{LOGO_HTML}<span>SAYAR YAPI | Yeni Sipariş</span></div><div class="header-sub">{html.escape(alt_baslik)}</div></div>'
        f'<div class="header-actions">'
        f'<a data-spa="1" href="{refresh_href}" target="_self" class="icon-btn" title="Yenile">🔄</a>'
        f'<a data-spa="1" href="?action=logout" target="_self" class="icon-btn" title="Çıkış">🚪</a>'
        f'</div></div>',
        unsafe_allow_html=True
    )

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

if st.session_state.ekran_kapali:
    st.markdown(
        '<div class="fullscreen-review-card" style="text-align:center; padding:24px 14px;">'
        '<div style="font-size:14.5px; font-weight:800; color:#0f172a; margin-bottom:6px;">YENİ SİPARİŞ EKRANI KAPATILDI</div>'
        '<div style="font-size:12px; color:#64748b;">Yeni sipariş girmek için aşağıdaki butona basın.</div>'
        '</div>',
        unsafe_allow_html=True
    )
    if st.button("🟠 YENİ SİPARİŞ EKRANINI AÇ", use_container_width=True):
        formu_sifirla()
        st.session_state.ekran_kapali = False
        st.rerun()
    st.stop()

listeler = secim_listelerini_getir()
fv = st.session_state.form_versiyon
uv = st.session_state.urun_input_versiyon
fd = st.session_state.form_data


def acilir_kutulu_alan(etiket: str, key_name: str, secenekler: list, mevcut_deger: str = "", yeni_ekle: bool = True):
    st.markdown(f'<span class="info-item-label">{html.escape(etiket)}</span>', unsafe_allow_html=True)
    BOS = "Seçiniz..."
    YENI = "➕ Yeni Yaz..."
    temiz = [x for x in secenekler if x]
    opts = [BOS] + temiz + ([YENI] if yeni_ekle else [])
    sel_key = f"sel_{key_name}_{fv}"
    txt_key = f"txt_{key_name}_{fv}"

    if sel_key not in st.session_state:
        if mevcut_deger and mevcut_deger in temiz:
            st.session_state[sel_key] = mevcut_deger
        elif mevcut_deger and yeni_ekle:
            st.session_state[sel_key] = YENI
            st.session_state[txt_key] = mevcut_deger
        else:
            st.session_state[sel_key] = BOS

    secim = st.selectbox(etiket, opts, key=sel_key, label_visibility="collapsed")
    if secim == BOS:
        return ""
    if yeni_ekle and secim == YENI:
        return st.text_input(etiket, key=txt_key, placeholder=f"{etiket}...", label_visibility="collapsed").strip()
    return secim.strip()


def buton_acilan_alan(etiket: str, alan_key: str, secenekler: list):
    st.markdown(f'<span class="info-item-label">{html.escape(etiket)}</span>', unsafe_allow_html=True)
    mevcut = fd.get(alan_key, "")
    acik = (st.session_state.aktif_buton_alan == alan_key)
    buton_yazi = mevcut if mevcut else "Seç..."
    if st.button(buton_yazi, key=f"btn_alan_{alan_key}_{fv}", use_container_width=True):
        st.session_state.aktif_buton_alan = None if acik else alan_key
        st.rerun()

    if acik:
        for i, sec in enumerate(secenekler):
            if st.button(sec, key=f"sec_{alan_key}_{fv}_{i}", use_container_width=True):
                fd[alan_key] = sec
                st.session_state.aktif_buton_alan = None
                st.rerun()
        yeni_giris = st.text_input(
            f"Yeni {etiket}",
            key=f"yeni_{alan_key}_{fv}",
            placeholder="Farklı yaz...",
            label_visibility="collapsed"
        ).strip()
        if yeni_giris and st.button(f"✓ {yeni_giris}", key=f"onay_{alan_key}_{fv}", use_container_width=True):
            fd[alan_key] = yeni_giris
            st.session_state.aktif_buton_alan = None
            st.rerun()

    return fd.get(alan_key, "")


# ==============================================================================
# YENİ SİPARİŞ KARTI (EKRAN GÖRÜNTÜSÜNDEKİ SİPARİŞ ONAY İNCELEME DÜZENİ)
# ==============================================================================
st.markdown(
    f'<div class="fullscreen-review-card">'
    f'<div class="fullscreen-review-header">'
    f'<div class="fullscreen-review-title">🟠 YENİ SİPARİŞ</div>'
    f'<a data-spa="1" href="?kapat=1{token_param}" target="_self" class="close-review-link" title="Kapat">✕</a>'
    f'</div>',
    unsafe_allow_html=True
)

# 1. Satır: Sipariş Tarihi | Sevk Tarihi
c1, c2 = st.columns(2)
with c1:
    st.markdown('<span class="info-item-label">Sipariş Tarihi</span>', unsafe_allow_html=True)
    fd["siparis_tarihi"] = st.date_input(
        "Sipariş Tarihi",
        value=fd.get("siparis_tarihi", date.today()),
        format="DD.MM.YYYY",
        key=f"sip_t_{fv}",
        label_visibility="collapsed"
    )
with c2:
    st.markdown('<span class="info-item-label">Sevk Tarihi</span>', unsafe_allow_html=True)
    fd["sevk_tarihi"] = st.date_input(
        "Sevk Tarihi",
        value=fd.get("sevk_tarihi", date.today()),
        format="DD.MM.YYYY",
        key=f"sevk_t_{fv}",
        label_visibility="collapsed"
    )

# 2. Satır: Tedarikçi Firma | Müşteri
c1, c2 = st.columns(2)
with c1:
    fd["firma"] = acilir_kutulu_alan("Tedarikçi Firma", "firma", listeler["firma"], fd.get("firma", ""), yeni_ekle=False)
with c2:
    fd["musteri"] = acilir_kutulu_alan("Müşteri", "musteri", listeler["musteri"], fd.get("musteri", ""), yeni_ekle=True)

# 3. Satır: Şantiye | Şehir
c1, c2 = st.columns(2)
with c1:
    fd["santiye"] = acilir_kutulu_alan("Şantiye", "santiye", listeler["santiye"], fd.get("santiye", ""), yeni_ekle=True)
with c2:
    fd["sehir"] = acilir_kutulu_alan("Şehir", "sehir", listeler["sehir"], fd.get("sehir", "İSTANBUL"), yeni_ekle=True)

# 4. Satır: Fabrika | Nakliye (Buton seçimli)
c1, c2 = st.columns(2)
with c1:
    buton_acilan_alan("Fabrika", "fabrika", listeler["fabrika"])
with c2:
    buton_acilan_alan("Nakliye", "nakliye", listeler["nakliye"])

# 5. Satır: Araç | Sipariş Geçen (Buton seçimli)
c1, c2 = st.columns(2)
with c1:
    buton_acilan_alan("Araç", "arac", listeler["arac"])
with c2:
    buton_acilan_alan("Sipariş Geçen", "siparis_gecen", listeler["siparis_gecen"])

# 6. Satır: Sipariş Veren
c1, c2 = st.columns(2)
with c1:
    st.markdown('<span class="info-item-label">Sipariş Veren</span>', unsafe_allow_html=True)
    if kilitli_veren:
        st.text_input(
            "Sipariş Veren",
            value=kilitli_veren,
            disabled=True,
            key=f"veren_kilit_{fv}",
            label_visibility="collapsed"
        )
        fd["siparis_veren"] = kilitli_veren
    else:
        fd["siparis_veren"] = acilir_kutulu_alan("Sipariş Veren", "siparis_veren", listeler["siparis_veren"], fd.get("siparis_veren", ""), yeni_ekle=True)

# Ürün - Birim - Adet (manuel sayı/tonaj) + Ekle (+)
firma_aktif = fd.get("firma", "")
filtrelenmis_urunler = [
    u["deger"] for u in listeler["urunler_detay"]
    if not firma_aktif or not u["firma"] or u["firma"].upper() == firma_aktif.upper()
]

u1, u2, u3, u4 = st.columns([4, 2, 2, 1])
with u1:
    st.markdown('<span class="info-item-label">Ürün</span>', unsafe_allow_html=True)
    u_opts = ["Seçiniz..."] + filtrelenmis_urunler + ["➕ Yeni Yaz..."]
    u_sel = st.selectbox("Ürün", u_opts, key=f"u_sel_{fv}_{uv}", label_visibility="collapsed")
    if u_sel == "➕ Yeni Yaz...":
        u_ad = st.text_input("Yeni Ürün", key=f"u_txt_{fv}_{uv}", placeholder="Ürün...", label_visibility="collapsed").strip()
    elif u_sel == "Seçiniz...":
        u_ad = ""
    else:
        u_ad = u_sel.strip()
with u2:
    st.markdown('<span class="info-item-label">Birim</span>', unsafe_allow_html=True)
    u_birim = st.selectbox("Birim", listeler["birim"], key=f"u_birim_{fv}_{uv}", label_visibility="collapsed")
with u3:
    st.markdown('<span class="info-item-label">Adet / Tonaj</span>', unsafe_allow_html=True)
    u_adet = st.text_input("Adet", key=f"u_adet_{fv}_{uv}", placeholder="Adet/Ton", label_visibility="collapsed").strip()
with u4:
    st.markdown('<span class="info-item-label">&nbsp;</span>', unsafe_allow_html=True)
    ekle_tiklandi = st.button("+", key=f"u_ekle_{fv}_{uv}", use_container_width=True)

if ekle_tiklandi:
    if not u_ad:
        st.warning("Lütfen ürün seçin veya yazın.")
    elif not u_adet:
        st.warning("Lütfen adet veya tonaj girin.")
    else:
        st.session_state.eklenen_urunler.append({
            "urun": u_ad,
            "birim": u_birim,
            "miktar": u_adet
        })
        st.session_state.urun_input_versiyon += 1
        st.rerun()

# Eklenen Ürünler Alt Tablosu
if st.session_state.eklenen_urunler:
    satirlar_html = ""
    for kalem in st.session_state.eklenen_urunler:
        satirlar_html += (
            f"<tr>"
            f"<td>{html.escape(str(kalem['urun']))}</td>"
            f"<td style='text-align:left; white-space:nowrap; color:#475569; font-weight:600;'>{html.escape(str(kalem['birim']))}</td>"
            f"<td class='urun-miktar'>{html.escape(str(kalem['miktar']))}</td>"
            f"</tr>"
        )
    st.markdown(
        f"<table class='urun-table'>"
        f"<thead><tr>"
        f"<th>Malzeme / Ürün</th>"
        f"<th style='text-align:left;'>Birim</th>"
        f"<th style='text-align:right;'>Miktar</th>"
        f"</tr></thead>"
        f"<tbody>{satirlar_html}</tbody>"
        f"</table>",
        unsafe_allow_html=True
    )
    if st.button(f"🗑️ Son Kalemi Sil ({len(st.session_state.eklenen_urunler)})", key=f"sil_kalem_{fv}", use_container_width=True):
        st.session_state.eklenen_urunler.pop()
        st.rerun()
else:
    st.markdown('<div class="bos-liste-kutusu">Henüz ürün eklenmedi.</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# SABİT ALT BAR: KAYDET | TEMİZLE | KAPAT
# ==============================================================================
st.markdown('<div class="sticky-bottom-bar">', unsafe_allow_html=True)
b1, b2, b3 = st.columns(3)
with b1:
    kaydet_tiklandi = st.button("KAYDET", type="primary", key=f"b_kaydet_{fv}", use_container_width=True)
with b2:
    temizle_tiklandi = st.button("TEMİZLE", key=f"b_temizle_{fv}", use_container_width=True)
with b3:
    kapat_tiklandi = st.button("KAPAT", key=f"b_kapat_{fv}", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if temizle_tiklandi:
    formu_sifirla()
    st.session_state.flash_mesaj = "Form temizlendi."
    st.rerun()

if kapat_tiklandi:
    st.session_state.ekran_kapali = True
    st.rerun()

if kaydet_tiklandi:
    urun_listesi = list(st.session_state.eklenen_urunler)
    if u_ad and u_adet:
        urun_listesi.append({"urun": u_ad, "birim": u_birim, "miktar": u_adet})

    eksikler = []
    if not fd.get("siparis_veren"):
        eksikler.append("Sipariş Veren")
    if not fd.get("firma"):
        eksikler.append("Tedarikçi Firma")
    if not fd.get("musteri"):
        eksikler.append("Müşteri")
    if not fd.get("santiye"):
        eksikler.append("Şantiye")
    if not urun_listesi:
        eksikler.append("En az 1 ürün")

    if eksikler:
        st.error(f"Eksik alanlar: **{', '.join(eksikler)}**")
    else:
        yeni_siparis_paketi = {
            "mobil_kayit_id": f"MOB-{int(time.time() * 1000)}",
            "kayit_zamani": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tarih": fd["siparis_tarihi"].strftime("%Y-%m-%d"),
            "sevk_tarihi": fd["sevk_tarihi"].strftime("%Y-%m-%d"),
            "firma": fd["firma"],
            "musteri": fd["musteri"],
            "santiye": fd["santiye"],
            "sehir": fd.get("sehir") or "İSTANBUL",
            "arac": fd.get("arac") or "TIR ( 27 TON )",
            "fabrika": fd.get("fabrika", ""),
            "nakliye": fd.get("nakliye", ""),
            "siparis_gecen": fd.get("siparis_gecen", ""),
            "siparis_veren": fd["siparis_veren"],
            "urunler": urun_listesi
        }

        try:
            with st.spinner("Kaydediliyor..."):
                yeni_siparis_kuyruguna_yaz(yeni_siparis_paketi)
                yeni_siparis_ntfy_gonder(yeni_siparis_paketi)

            secim_listelerini_getir.clear()
            formu_sifirla()
            st.session_state.flash_mesaj = f"{yeni_siparis_paketi['musteri']} ({yeni_siparis_paketi['santiye']}) siparişi kaydedildi!"
            st.rerun()
        except Exception as err:
            st.error(f"Sipariş Google Drive kuyruğuna yazılamadı: {err}")
