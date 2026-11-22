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
    }})();
    </script>
    """,
    height=0,
    width=0
)

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
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
    overflow-x: hidden !important;
    max-width: 100vw !important;
}
.block-container {
    padding-top: 0.35rem !important;
    padding-bottom: 1.2rem !important;
    padding-left: 0.6rem !important;
    padding-right: 0.6rem !important;
    max-width: 540px !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
[data-testid="stVerticalBlock"] {
    gap: 0.32rem !important;
}
.header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-left: 5px solid #f97316;
    border-radius: 9px;
    padding: 7px 10px;
    margin-bottom: 4px;
    color: #f8fafc;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.14);
    gap: 8px;
}
.header-info {
    flex: 1;
    min-width: 0;
}
.header-title {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 14px;
    font-weight: 700;
    margin: 0;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.header-logo {
    height: 24px;
    width: auto;
    object-fit: contain;
    border-radius: 4px;
    flex-shrink: 0;
}
.header-sub {
    font-size: 10.5px;
    color: #cbd5e1;
    margin-top: 1px;
}
.header-actions {
    display: flex;
    gap: 5px;
    flex-shrink: 0;
}
.icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 7px;
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.18);
    color: #ffffff !important;
    text-decoration: none !important;
    font-size: 15px;
    cursor: pointer;
}
.icon-btn:active {
    background-color: #f97316;
}
.auto-toast-banner {
    background-color: #dcfce7;
    border: 1px solid #86efac;
    border-left: 4px solid #16a34a;
    color: #14532d;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 12.5px;
    font-weight: 700;
    margin-bottom: 4px;
    opacity: 1;
    transition: opacity 0.35s ease;
    box-shadow: 0 2px 6px rgba(22, 163, 74, 0.12);
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 7px !important;
    color: #0f172a !important;
    min-height: 37px !important;
    font-size: 13px !important;
}
button[kind="primary"] {
    background-color: #f97316 !important;
    border-color: #ea580c !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    height: 42px !important;
    border-radius: 8px !important;
    font-size: 13.5px !important;
}
button[kind="primary"]:hover {
    background-color: #ea580c !important;
}
.urun-ayirici {
    border-top: 2px solid #cbd5e1;
    margin: 6px 0 4px 0;
}
.eklenen-urun-satir {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #16a34a;
    border-radius: 7px;
    padding: 6px 9px;
    min-height: 36px;
}
.eklenen-urun-ad {
    font-size: 12.5px;
    font-weight: 700;
    color: #0f172a;
    word-break: break-word;
}
.eklenen-urun-miktar {
    font-size: 11.5px;
    font-weight: 800;
    color: #0369a1;
    background-color: #e0f2fe;
    padding: 2px 7px;
    border-radius: 5px;
    white-space: nowrap;
    margin-left: 6px;
    flex-shrink: 0;
}
.bos-liste-kutusu {
    background-color: #f8fafc;
    border: 1px dashed #94a3b8;
    border-radius: 7px;
    padding: 8px;
    text-align: center;
    font-size: 11.5px;
    color: #64748b;
    font-weight: 600;
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
            f'<div class="header-sub">Hızlı Mobil Sipariş Girişi</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
        if url_veren:
            st.caption(f"Personel Girişi: **{url_veren}**")

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


# PYTSAYAR.PY tanimlar ve siparisler tablolarından seçim listelerini çek (60 sn önbellekli)
@st.cache_data(ttl=60, show_spinner=False)
def secim_listelerini_getir():
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
        varsayilan["arac"] = tanim_listesi("ARAÇ") or siparis_gecmis_listesi("arac")
        varsayilan["fabrika"] = tanim_listesi("FABRİKA") or siparis_gecmis_listesi("fabrika")
        varsayilan["nakliye"] = tanim_listesi("NAKLİYE") or siparis_gecmis_listesi("nakliye")
        varsayilan["siparis_veren"] = tanim_listesi("SİPARİŞ VEREN") or siparis_gecmis_listesi("siparis_veren")

        varsayilan["musteri"] = sorted(list(set(tanim_listesi("MÜŞTERİ") + siparis_gecmis_listesi("musteri"))))
        varsayilan["santiye"] = sorted(list(set(tanim_listesi("ŞANTİYE") + siparis_gecmis_listesi("santiye"))))
        varsayilan["sehir"] = sorted(list(set(tanim_listesi("ŞEHİR") + siparis_gecmis_listesi("sehir"))))

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


def kompakt_hibrit_alan(etiket: str, key_prefix: str, secenekler: list, zorunlu: bool = False, yeni_ekle_aktif: bool = True):
    """Üst etiketi gizler; alan adını doğrudan açılır kutunun içine yerleştiren kompakt seçim kutusu."""
    YENI_SECENEK = "➕ Yeni Giriş..."
    bos_etiket = f"{etiket} *" if zorunlu else etiket
    opsiyonlar = [bos_etiket] + secenekler + ([YENI_SECENEK] if yeni_ekle_aktif else [])
    secim = st.selectbox(
        bos_etiket,
        opsiyonlar,
        key=f"{key_prefix}_sel",
        label_visibility="collapsed"
    )
    if secim == bos_etiket:
        return ""
    if yeni_ekle_aktif and secim == YENI_SECENEK:
        return st.text_input(
            bos_etiket,
            key=f"{key_prefix}_txt",
            placeholder=f"Yeni {etiket} yazınız...",
            label_visibility="collapsed"
        ).strip()
    return secim.strip()


if st.query_params.get("action") == "refresh":
    st.cache_data.clear()
    st.query_params.pop("action", None)
    st.rerun()

if "eklenen_urunler" not in st.session_state:
    st.session_state.eklenen_urunler = []
if "urun_input_versiyon" not in st.session_state:
    st.session_state.urun_input_versiyon = 0
if "form_versiyon" not in st.session_state:
    st.session_state.form_versiyon = 0
if "flash_mesaj" not in st.session_state:
    st.session_state.flash_mesaj = None

yetki_tipi = st.session_state.yetki_tipi
yetki_deger = st.session_state.yetki_deger
aktif_token = st.session_state.get("active_token") or st.query_params.get("token", "")
token_param = f"&token={aktif_token}" if aktif_token else ""
refresh_href = f"?action=refresh{token_param}"

alt_baslik = f"Personel: {yetki_deger}" if yetki_tipi == "SIPARIS_VEREN" else "Yönetici Hızlı Sipariş Ekranı"
st.markdown(
    f'<div class="header-banner">'
    f'<div class="header-info">'
    f'<div class="header-title">{LOGO_HTML}<span>SAYAR YAPI | Sipariş Gir</span></div>'
    f'<div class="header-sub">{html.escape(alt_baslik)}</div>'
    f'</div>'
    f'<div class="header-actions">'
    f'<a data-spa="1" href="{refresh_href}" target="_self" class="icon-btn" title="Listeleri Yenile">🔄</a>'
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

listeler = secim_listelerini_getir()
fv = st.session_state.form_versiyon
uv = st.session_state.urun_input_versiyon

# ==============================================================================
# 1. TÜM SİPARİŞ & SEVKİYAT ALANLARI (ALT ALTA, ETİKETSİZ, MOBİL UYUMLU)
# ==============================================================================
siparis_tarihi = st.date_input("Tarih", value=date.today(), format="DD.MM.YYYY", key=f"tarih_{fv}", label_visibility="collapsed")

if yetki_tipi == "SIPARIS_VEREN" and yetki_deger:
    siparis_veren = st.text_input("Sipariş Veren", value=str(yetki_deger), disabled=True, key=f"veren_kilit_{fv}", label_visibility="collapsed").strip()
else:
    siparis_veren = kompakt_hibrit_alan("Sipariş Veren", f"veren_{fv}", listeler["siparis_veren"], zorunlu=True, yeni_ekle_aktif=False)

firma = kompakt_hibrit_alan("Firma", f"firma_{fv}", listeler["firma"], zorunlu=True, yeni_ekle_aktif=False)
musteri = kompakt_hibrit_alan("Müşteri", f"musteri_{fv}", listeler["musteri"], zorunlu=True, yeni_ekle_aktif=True)
santiye = kompakt_hibrit_alan("Şantiye", f"santiye_{fv}", listeler["santiye"], zorunlu=True, yeni_ekle_aktif=True)
sehir = kompakt_hibrit_alan("Şehir", f"sehir_{fv}", listeler["sehir"], zorunlu=False, yeni_ekle_aktif=True)
fabrika = kompakt_hibrit_alan("Fabrika", f"fabrika_{fv}", listeler["fabrika"], zorunlu=True, yeni_ekle_aktif=False)
nakliye = kompakt_hibrit_alan("Nakliye", f"nakliye_{fv}", listeler["nakliye"], zorunlu=True, yeni_ekle_aktif=False)
arac = kompakt_hibrit_alan("Araç", f"arac_{fv}", listeler["arac"], zorunlu=True, yeni_ekle_aktif=False)

st.markdown('<div class="urun-ayirici"></div>', unsafe_allow_html=True)

# ==============================================================================
# 2. ÜRÜN EKLEME VE EKLENEN ÜRÜNLER LİSTESİ (ALT ALTA)
# ==============================================================================
filtrelenmis_urunler = [
    u["deger"] for u in listeler["urunler_detay"]
    if not firma or not u["firma"] or u["firma"].upper() == firma.upper()
]

u_ad = kompakt_hibrit_alan("Ürün / Malzeme Seçin", f"urun_giris_{fv}_{uv}", filtrelenmis_urunler, zorunlu=False, yeni_ekle_aktif=True)

u_miktar = st.number_input(
    "Miktar",
    min_value=0.0,
    step=1.0,
    value=None,
    placeholder="Miktar Giriniz",
    format="%g",
    key=f"miktar_giris_{fv}_{uv}",
    label_visibility="collapsed"
)

u_birim = st.selectbox(
    "Birim",
    listeler["birim"],
    key=f"birim_giris_{fv}_{uv}",
    label_visibility="collapsed"
)

if st.button("➕ ÜRÜN EKLE", use_container_width=True, key=f"btn_urun_ekle_{fv}_{uv}"):
    girilen_miktar = float(u_miktar) if u_miktar is not None else 0.0
    if not u_ad:
        st.warning("Lütfen eklenecek ürünü seçin veya yazın.")
    elif girilen_miktar <= 0:
        st.warning("Lütfen 0'dan büyük bir miktar girin.")
    else:
        miktar_str = str(int(girilen_miktar)) if girilen_miktar.is_integer() else str(girilen_miktar)
        st.session_state.eklenen_urunler.append({
            "urun": u_ad,
            "miktar": miktar_str,
            "birim": u_birim
        })
        st.session_state.urun_input_versiyon += 1
        st.rerun()

# Eklenen Ürünlerin Altta Listelenmesi
if st.session_state.eklenen_urunler:
    for idx, item in enumerate(st.session_state.eklenen_urunler):
        st.markdown(
            f'<div class="eklenen-urun-satir">'
            f'<span class="eklenen-urun-ad">{idx + 1}. {html.escape(item["urun"])}</span>'
            f'<span class="eklenen-urun-miktar">{html.escape(item["miktar"])} {html.escape(item["birim"])}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button(f"🗑️ {idx + 1}. Ürünü Sil", key=f"sil_urun_{fv}_{idx}", use_container_width=True):
            st.session_state.eklenen_urunler.pop(idx)
            st.rerun()
else:
    st.markdown(
        '<div class="bos-liste-kutusu">Henüz ürün eklenmedi.</div>',
        unsafe_allow_html=True
    )

st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 3. KAYDET VE GÖNDER
# ==============================================================================
if st.button("✅ SİPARİŞİ KAYDET VE GÖNDER", type="primary", use_container_width=True):
    eksikler = []
    if not firma:
        eksikler.append("Firma")
    if not musteri:
        eksikler.append("Müşteri")
    if not santiye:
        eksikler.append("Şantiye")
    if not fabrika:
        eksikler.append("Fabrika")
    if not nakliye:
        eksikler.append("Nakliye")
    if not arac:
        eksikler.append("Araç")
    if not siparis_veren:
        eksikler.append("Sipariş Veren")

    gonderilecek_urunler = list(st.session_state.eklenen_urunler)
    son_miktar = float(u_miktar) if u_miktar is not None else 0.0
    if u_ad and son_miktar > 0:
        miktar_str = str(int(son_miktar)) if son_miktar.is_integer() else str(son_miktar)
        gonderilecek_urunler.append({
            "urun": u_ad,
            "miktar": miktar_str,
            "birim": u_birim
        })

    if not gonderilecek_urunler:
        eksikler.append("En az 1 eklenmiş Ürün")

    if eksikler:
        st.error(f"Lütfen zorunlu alanları doldurunuz: **{', '.join(eksikler)}**")
    else:
        tarih_iso = siparis_tarihi.strftime("%Y-%m-%d")
        yeni_siparis_paketi = {
            "mobil_kayit_id": f"MOB-{int(time.time() * 1000)}",
            "kayit_zamani": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tarih": tarih_iso,
            "sevk_tarihi": tarih_iso,
            "firma": firma,
            "musteri": musteri,
            "santiye": santiye,
            "sehir": sehir,
            "arac": arac,
            "fabrika": fabrika,
            "nakliye": nakliye,
            "siparis_veren": siparis_veren,
            "durum": "BEKLEMEDE",
            "operasyon": "ONAY BEKLİYOR",
            "urunler": gonderilecek_urunler
        }

        try:
            with st.spinner("Sipariş iletiliyor..."):
                yeni_siparis_kuyruguna_yaz(yeni_siparis_paketi)
                yeni_siparis_ntfy_gonder(yeni_siparis_paketi)

            secim_listelerini_getir.clear()
            st.session_state.eklenen_urunler = []
            st.session_state.urun_input_versiyon = 0
            st.session_state.form_versiyon += 1
            st.session_state.flash_mesaj = f"{musteri} ({santiye}) siparişi başarıyla kaydedildi!"
            st.rerun()
        except Exception as err:
            st.error(f"Sipariş Google Drive kuyruğuna yazılamadı: {err}")
