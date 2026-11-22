import os
import re
import json
import time
import hmac
import html
import base64
import hashlib
import requests
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date

import sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from firebase_db import FirebaseRealtimeStore, DEFAULT_DATABASE_URL, DEFAULT_SERVICE_ACCOUNT_FILE

# Railway ortam değişkeninden secrets.toml dosyasını sadece yoksa oluştur
if os.environ.get("STREAMLIT_SECRETS") and not os.path.exists(".streamlit/secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMLIT_SECRETS"])

NTFY_TOPIC = "sayar_yapi_kamyon_2026x"


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
    padding-left: 0.70rem !important;
    padding-right: 0.70rem !important;
    max-width: 540px !important;
    width: 100% !important;
    margin: 0 auto !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
[data-testid="stVerticalBlock"] {
    gap: 0.32rem !important;
    width: 100% !important;
    max-width: 100% !important;
}
[data-testid="element-container"] {
    width: 100% !important;
    max-width: 100% !important;
}
div[data-testid="stHorizontalBlock"]:has(.iki-sutun-isaret) {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(.iki-sutun-isaret) > div[data-testid="column"] {
    flex: 1 1 50% !important;
    width: 50% !important;
    min-width: 0 !important;
    max-width: 50% !important;
    padding: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(.ozet-satir-isaret) {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: stretch !important;
    gap: 6px !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(.ozet-satir-isaret) > div[data-testid="column"]:nth-child(1) {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    padding: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(.ozet-satir-isaret) > div[data-testid="column"]:nth-child(2) {
    flex: 0 0 42px !important;
    width: 42px !important;
    min-width: 42px !important;
    max-width: 42px !important;
    padding: 0 !important;
}
.header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #ffffff;
    border: 0;
    border-bottom: 1px solid #e2e8f0;
    border-radius: 0;
    padding: 1px 0 8px;
    margin: 0 0 8px;
    color: #0f172a;
    box-shadow: none;
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
    gap: 7px;
    font-size: 14px;
    font-weight: 800;
    margin: 0;
    color: #172033;
    letter-spacing: 0.2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.header-logo {
    height: 23px;
    width: auto;
    object-fit: contain;
    border-radius: 4px;
    flex-shrink: 0;
}
.header-sub {
    font-size: 10.5px;
    color: #64748b;
    margin-top: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
    width: 31px;
    height: 31px;
    border-radius: 7px;
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #475569 !important;
    text-decoration: none !important;
    font-size: 14px;
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
.st-key-siparis-form-card {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-top: 4px solid #f97316 !important;
    border-radius: 11px !important;
    padding: 10px 11px 12px 11px !important;
    margin-top: 2px !important;
    margin-bottom: 10px !important;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.07) !important;
}
.st-key-siparis-form-card > div {
    gap: 0.42rem !important;
}
.st-key-siparis-form-card .siparis-kalem-baslik {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 74px 72px;
    gap: 6px;
    background: #1e293b;
    color: #ffffff;
    border-radius: 7px 7px 0 0;
    padding: 9px 8px;
    font-size: 11px;
    font-weight: 800;
    margin-top: 8px;
}
.siparis-kalem-baslik span:nth-child(2),
.siparis-kalem-baslik span:nth-child(3) { text-align: center; }
.eklenen-urun-birim {
    width: 74px;
    text-align: center;
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    flex-shrink: 0;
}
div[data-testid="stHorizontalBlock"] {
    gap: 8px !important;
}
div[data-testid="stDateInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label {
    color: #64748b !important;
    font-size: 10px !important;
    font-weight: 600 !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
    color: #0f172a !important;
    min-height: 43px !important;
    font-size: 14px !important;
    width: 100% !important;
    max-width: 100% !important;
}
div[data-testid="stNumberInput"] button {
    display: none !important;
}
div[data-testid="stNumberInput"] input {
    padding-left: 10px !important;
    padding-right: 8px !important;
}
div[data-testid="stButton"] button {
    min-height: 42px !important;
    padding: 0 6px !important;
    font-size: 12.5px !important;
    font-weight: 800 !important;
    border-radius: 9px !important;
    width: 100% !important;
    max-width: 100% !important;
}
button[kind="primary"] {
    background-color: #f97316 !important;
    border-color: #ea580c !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    height: 42px !important;
    border-radius: 9px !important;
    font-size: 12.5px !important;
}
button[kind="primary"]:hover {
    background-color: #ea580c !important;
}
div[data-testid="element-container"]:has(.sticky-gonder-isaret) + div[data-testid="element-container"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: 100% !important;
    max-width: 540px !important;
    padding: 7px 0.55rem 9px 0.55rem !important;
    background: linear-gradient(180deg, rgba(241,245,249,0.88) 0%, #f1f5f9 30%) !important;
    backdrop-filter: blur(4px);
    z-index: 9999 !important;
    margin: 0 !important;
}
.eklenen-urun-satir {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 74px 72px;
    gap: 6px;
    align-items: center;
    background-color: #f8fafc;
    border: 1px solid #dbe2ea;
    border-left: 3px solid #0284c7;
    border-radius: 8px;
    padding: 7px 10px;
    min-height: 37px;
    width: 100%;
    overflow: hidden;
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
.eklenen-urun-miktar {
    font-size: 11.5px;
    font-weight: 800;
    color: #0f172a;
    padding: 2px 0;
    border-radius: 5px;
    white-space: nowrap;
    flex-shrink: 0;
    text-align: center;
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
    width: 100%;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_firebase_store() -> FirebaseRealtimeStore:
    db_url = DEFAULT_DATABASE_URL
    sa_info = None
    sa_file = None

    try:
        if "FIREBASE_DATABASE_URL" in st.secrets and str(st.secrets["FIREBASE_DATABASE_URL"]).strip():
            db_url = str(st.secrets["FIREBASE_DATABASE_URL"]).strip()
    except Exception:
        pass

    try:
        if "FIREBASE_SERVICE_ACCOUNT" in st.secrets and st.secrets["FIREBASE_SERVICE_ACCOUNT"]:
            sa_info = dict(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
        elif "GDRIVE_SERVICE_ACCOUNT" in st.secrets and st.secrets["GDRIVE_SERVICE_ACCOUNT"]:
            sa_info = dict(st.secrets["GDRIVE_SERVICE_ACCOUNT"])
    except Exception:
        sa_info = None

    if sa_info is None and os.path.exists(DEFAULT_SERVICE_ACCOUNT_FILE):
        sa_file = DEFAULT_SERVICE_ACCOUNT_FILE

    return FirebaseRealtimeStore(
        service_account_info=sa_info,
        service_account_file=sa_file,
        database_url=db_url,
        app_name="mobil_siparis_rtdb"
    )


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
        store = get_firebase_store()
        tanim_rows = store.tum_tanimlari_getir()
        sip_rows = store.tum_siparisleri_getir()[:1000]

        def tanim_listesi(kat):
            vals = []
            for r in tanim_rows:
                if r.get("kategori") == kat and int(r.get("aktif", 1)) == 1:
                    d = str(r.get("deger") or "").strip()
                    if d and d != "-":
                        vals.append(d)
            return sorted(list(set(vals)))

        def siparis_gecmis_listesi(col):
            vals = []
            for r in sip_rows:
                v = str(r.get(col) or "").strip()
                if v and v != "-" and v.lower() not in ("none", "nan"):
                    vals.append(v)
            return sorted(list(set(vals)))

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

        urun_list = []
        for r in tanim_rows:
            if r.get("kategori") == "ÜRÜN" and int(r.get("aktif", 1)) == 1:
                ad = str(r.get("deger") or "").strip()
                frm = str(r.get("firma") or "").strip()
                if ad:
                    urun_list.append({"deger": ad, "firma": frm})
        varsayilan["urunler_detay"] = sorted(urun_list, key=lambda x: x["deger"])

    except Exception:
        pass

    return varsayilan


def yeni_siparisi_firebase_kaydet(siparis_paketi: dict) -> int:
    store = get_firebase_store()

    # Serbest yazılmış yeni müşteri / şantiye / şehir / ürün varsa tanımlara ekle
    for kat, val in (
        ("MÜŞTERİ", siparis_paketi.get("musteri")),
        ("ŞANTİYE", siparis_paketi.get("santiye")),
        ("ŞEHİR", siparis_paketi.get("sehir")),
    ):
        v = str(val or "").strip()
        if v:
            try:
                store.tanim_ekle_veya_guncelle(kat, v, aktif=1)
            except Exception:
                pass

    for k in siparis_paketi.get("urunler", []):
        u_ad = str(k.get("urun") or "").strip()
        if u_ad:
            try:
                store.tanim_ekle_veya_guncelle("ÜRÜN", u_ad, aktif=1)
            except Exception:
                pass

    kayit_dict = {
        "tarih": siparis_paketi.get("tarih", ""),
        "firma": siparis_paketi.get("firma", ""),
        "musteri": siparis_paketi.get("musteri", ""),
        "santiye": siparis_paketi.get("santiye", ""),
        "sehir": siparis_paketi.get("sehir", "İSTANBUL"),
        "telefon": "",
        "yetkili": "",
        "arac": siparis_paketi.get("arac", ""),
        "fabrika": siparis_paketi.get("fabrika", ""),
        "nakliye": siparis_paketi.get("nakliye", ""),
        "notlar": f"[Mobil Kayıt: {siparis_paketi.get('mobil_kayit_id', '')} - {siparis_paketi.get('kayit_zamani', '')}]",
        "sevk_tarihi": siparis_paketi.get("sevk_tarihi", ""),
        "ted_sip_no": "",
        "plaka": "",
        "nakliye_fatura": "",
        "siparis_veren": siparis_paketi.get("siparis_veren", ""),
        "firma_yetkili": "",
        "siparis_gecen": "",
        "durum": siparis_paketi.get("durum", "BEKLEMEDE"),
        "operasyon": siparis_paketi.get("operasyon", "ONAY BEKLİYOR"),
        "kalemler": siparis_paketi.get("urunler", [])
    }

    return store.siparis_kaydet(kayit_dict)


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


def secim_alani(etiket: str, key: str, secenekler: list, varsayilan: str = ""):
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


def hizli_secim_alani(etiket: str, key: str, secenekler: list, varsayilan: str = ""):
    temiz = [str(x).strip() for x in secenekler if str(x).strip() and str(x).strip() != "-"]
    secenekler = list(dict.fromkeys(temiz))
    if varsayilan and varsayilan not in secenekler:
        secenekler.insert(0, varsayilan)
    secim_key = f"{key}_value"
    acik_key = f"{key}_open"
    if secim_key not in st.session_state:
        st.session_state[secim_key] = varsayilan if varsayilan in secenekler else ""
    secili = st.session_state[secim_key]
    baslik = secili if secili else f"— {etiket} seçin —"

    if st.button(baslik, key=f"{key}_toggle", use_container_width=True):
        st.session_state[acik_key] = not st.session_state.get(acik_key, False)

    if st.session_state.get(acik_key, False):
        if not secenekler:
            st.caption(f"{etiket} için kayıtlı seçenek bulunamadı.")
        else:
            sutun_sayisi = 2
            for baslangic in range(0, len(secenekler), sutun_sayisi):
                kolonlar = st.columns(sutun_sayisi)
                for offset, secenek in enumerate(secenekler[baslangic:baslangic + sutun_sayisi]):
                    with kolonlar[offset]:
                        if st.button(
                            secenek, key=f"{key}_opt_{baslangic + offset}",
                            use_container_width=True,
                            type="primary" if secenek == secili else "secondary"
                        ):
                            st.session_state[secim_key] = secenek
                            st.session_state[acik_key] = False
                            st.rerun()
    return st.session_state[secim_key]


def miktar_metni_gecerli_mi(deger: str) -> bool:
    metin = str(deger or "").strip().replace(",", ".")
    if not metin:
        return False
    try:
        return float(metin) > 0
    except ValueError:
        return bool(re.fullmatch(r"\d+(?:[.,]\d+)?\s*[A-Za-zÇĞİÖŞÜçğıöşü]+", str(deger).strip()))


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

with st.container(key="siparis-form-card"):
    alt_baslik = f"Personel: {yetki_deger}" if yetki_tipi == "SIPARIS_VEREN" else "Yeni Sipariş Girişi"
    st.markdown(
        f'<div class="header-banner">'
        f'<div class="header-info">'
        f'<div class="header-title">{LOGO_HTML}<span>YENİ SİPARİŞ</span></div>'
        f'<div class="header-sub">{html.escape(str(alt_baslik))}</div>'
        f'</div>'
        f'<div class="header-actions">'
        f'<a data-spa="1" href="{refresh_href}" target="_self" class="icon-btn" title="Listeleri Yenile">🔄</a>'
        f'<a data-spa="1" href="?action=logout" target="_self" class="icon-btn" title="Çıkış">🚪</a>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    flash_msg = st.session_state.flash_mesaj
    if flash_msg:
        st.markdown(
            f'<div class="auto-toast-banner">✅ {html.escape(str(flash_msg))}</div>',
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

    alan_sol, alan_sag = st.columns(2)
    with alan_sol:
        firma = secim_alani("Firma", f"firma_{fv}", listeler["firma"], taslak.get("firma", ""))
    with alan_sag:
        musteri = secim_alani("Müşteri", f"musteri_{fv}", listeler["musteri"], taslak.get("musteri", ""))

    alan_sol, alan_sag = st.columns(2)
    with alan_sol:
        santiye = secim_alani("Şantiye", f"santiye_{fv}", listeler["santiye"], taslak.get("santiye", ""))
    with alan_sag:
        sehir = secim_alani("Şehir", f"sehir_{fv}", listeler["sehir"], taslak.get("sehir") or "İSTANBUL")

    alan_sol, alan_sag = st.columns(2)
    with alan_sol:
        fabrika = hizli_secim_alani(
            "Fabrika", f"fabrika_{fv}", listeler["fabrika"], taslak.get("fabrika", "")
        )
    with alan_sag:
        nakliye = hizli_secim_alani(
            "Nakliye", f"nakliye_{fv}", listeler["nakliye"], taslak.get("nakliye", "")
        )

    alan_sol, alan_sag = st.columns(2)
    with alan_sol:
        arac = hizli_secim_alani(
            "Araç", f"arac_{fv}", listeler["arac"], taslak.get("arac") or "TIR ( 27 TON )"
        )
    with alan_sag:
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
    urun_col, birim_col, miktar_col, ekle_col = st.columns([4, 2, 3, 1])
    with urun_col:
        urun_serbest = st.text_input(
            "Ürün", key=f"urun_serbest_{fv}_{uv}",
            placeholder="Ürün", label_visibility="collapsed"
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
            "Adet / Tonaj", key=f"miktar_giris_{fv}_{uv}",
            placeholder="Adet / Tonaj", label_visibility="collapsed"
        ).strip()
    with ekle_col:
        ekle_tiklandi = st.button("＋", key=f"btn_urun_ekle_{fv}_{uv}", use_container_width=True)

    if ekle_tiklandi:
        if not u_ad:
            st.warning("Lütfen ürün seçin veya yazın.")
        elif not miktar_metni_gecerli_mi(u_miktar):
            st.warning("Lütfen geçerli bir adet veya tonaj giriniz.")
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

st.markdown('<div class="sticky-gonder-isaret"></div>', unsafe_allow_html=True)
alt_kaydet, alt_temizle, alt_kapat = st.columns(3)
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
            "mobil_kayit_id": f"MOB-{int(time.time() * 1000)}",
            "kayit_zamani": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tarih": siparis_tarihi.strftime("%Y-%m-%d"),
            "sevk_tarihi": sevk_tarihi.strftime("%Y-%m-%d"),
            "firma": firma,
            "musteri": musteri,
            "santiye": santiye,
            "sehir": sehir or "İSTANBUL",
            "arac": arac,
            "fabrika": fabrika,
            "nakliye": nakliye,
            "siparis_veren": siparis_veren,
            "durum": "BEKLEMEDE",
            "operasyon": "ONAY BEKLİYOR",
            "urunler": list(st.session_state.eklenen_urunler)
        }
        try:
            with st.spinner("Sipariş kaydediliyor..."):
                yeni_no = yeni_siparisi_firebase_kaydet(yeni_siparis_paketi)
                yeni_siparis_ntfy_gonder(yeni_siparis_paketi)
            secim_listelerini_getir.clear()
            st.session_state.eklenen_urunler = []
            st.session_state.urun_input_versiyon = 0
            st.session_state.taslak_bilgi = {}
            st.session_state.form_versiyon += 1
            st.session_state.flash_mesaj = f"#{yeni_no} - {musteri} ({santiye}) siparişi kaydedildi!"
            st.rerun()
        except Exception as err:
            st.error(f"Sipariş Firebase veritabanına yazılamadı: {err}")
