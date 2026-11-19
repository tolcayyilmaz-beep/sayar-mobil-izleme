import io
import os
import json
import time
import sqlite3
import tempfile
from datetime import datetime
import pandas as pd
import streamlit as st
from cryptography.fernet import Fernet
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# ==========================================
# SAYFA YAPILANDIRMASI
# ==========================================
st.set_page_config(
    page_title="Sayar Yapı | Sipariş İzleme",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# ÖZEL MOBİL TASARIM CSS
# ==========================================
st.markdown("""
<style>
    .block-container {
        padding-top: 1.1rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        max-width: 760px !important;
        margin: 0 auto !important;
    }
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0.5rem !important;
    }
    #MainMenu, footer { visibility: hidden; }

    /* Kompakt Kapatma (✕) Butonu */
    button[kind="tertiary"] {
        padding: 0.15rem 0.55rem !important;
        min-height: 2rem !important;
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        color: #94a3b8 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        background-color: #1e293b !important;
    }
    button[kind="tertiary"]:hover {
        color: #f8fafc !important;
        border-color: #64748b !important;
    }

    /* Başlık Alanı */
    .app-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-left: 5px solid #0284c7;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .app-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #f8fafc;
        margin: 0;
        letter-spacing: 0.3px;
    }
    .app-subtitle {
        font-size: 0.78rem;
        color: #94a3b8;
        margin-top: 2px;
    }

    /* KPI Kartları */
    div[data-testid="stHorizontalBlock"] {
        gap: 6px !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        min-width: 0 !important;
        flex: 1 1 0 !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        padding: 6px 4px !important;
        min-height: 54px !important;
        height: auto !important;
        width: 100% !important;
        color: #f8fafc !important;
        line-height: 1.15 !important;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        border-color: #475569 !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        background-color: #1e293b !important;
        border: 2px solid #ef4444 !important;
        border-radius: 10px !important;
        padding: 6px 4px !important;
        min-height: 54px !important;
        height: auto !important;
        width: 100% !important;
        color: #f8fafc !important;
        line-height: 1.15 !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"]:hover,
    div[data-testid="stHorizontalBlock"] button[kind="primary"]:focus {
        background-color: #1e293b !important;
        border: 2px solid #ef4444 !important;
        color: #f8fafc !important;
    }
    div[data-testid="stHorizontalBlock"] button p {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        white-space: pre-line !important;
        text-align: center !important;
    }

    /* Arama ve Filtre Kutuları */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: #f8fafc !important;
        font-size: 0.88rem !important;
    }

    /* Sipariş Kartı */
    .order-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 6px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.22);
    }
    .card-top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }
    .badge {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        color: #ffffff;
        white-space: nowrap;
    }
    .card-company {
        font-size: 1.05rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 2px;
        line-height: 1.25;
    }
    .card-customer {
        font-size: 0.90rem;
        font-weight: 600;
        color: #38bdf8;
        margin-bottom: 2px;
    }
    .card-site {
        font-size: 0.84rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 4px;
    }
    .card-date-row {
        font-size: 0.78rem;
        color: #94a3b8;
        font-weight: 600;
        border-top: 1px solid #334155;
        padding-top: 6px;
        margin-top: 4px;
    }

    /* Detay & Onay İnceleme Paneli */
    .detail-box {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .detail-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        margin-top: 8px;
    }
    .detail-item {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 7px 10px;
    }
    .detail-label {
        font-size: 0.70rem;
        color: #94a3b8;
        font-weight: 600;
    }
    .detail-val {
        font-size: 0.84rem;
        color: #f8fafc;
        font-weight: 700;
        margin-top: 1px;
        word-break: break-word;
    }
    .note-box {
        background-color: #1e293b;
        border-left: 3px solid #f59e0b;
        border-radius: 6px;
        padding: 8px 10px;
        margin-top: 10px;
        font-size: 0.82rem;
        color: #fef3c7;
    }
    .product-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 8px 10px;
        margin-top: 6px;
    }
    .product-name {
        font-size: 0.84rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .product-qty {
        font-size: 0.84rem;
        font-weight: 800;
        color: #38bdf8;
        white-space: nowrap;
        margin-left: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# RENK HARİTALARI & YARDIMCI FONKSİYONLAR
# ==========================================
OP_RENK = {
    "İŞLENDİ": "#0284c7",
    "ONAY BEKLİYOR": "#ea580c",
    "ONAYLANDI": "#0d9488",
    "REVİZE İSTENDİ": "#d97706",
    "REDDEDİLDİ": "#dc2626",
    "TAMAMLANDI": "#16a34a",
    "İPTAL EDİLDİ": "#dc2626",
    "KISMİ EVRAK": "#7c3aed"
}

QUEUE_FILE_NAME = "mobil_onaylar.json"


def format_durum_text(val) -> str:
    metin = str(val or "").strip()
    if not metin:
        return ""
    tr_upper = metin.replace("i", "İ").replace("ı", "I").upper()
    if tr_upper in ("SEVK EDİLDİ", "İPTAL"):
        return tr_upper
    return metin


def format_miktar(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    try:
        f = float(s)
        return str(int(f)) if f.is_integer() else str(f)
    except ValueError:
        return s


# ==========================================
# GOOGLE DRIVE BAĞLANTISI & ONAY KUYRUĞU YAZMA
# ==========================================
def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def mobil_karar_gonder(siparis_no: int, yeni_karar: str, aciklama: str = "") -> bool:
    """Yönetici onay/revize/ret kararını Google Drive üzerindeki mobil_onaylar.json kuyruğuna ekler."""
    try:
        folder_id = st.secrets["GDRIVE_FOLDER_ID"]
        service = get_drive_service()

        query = f"name='{QUEUE_FILE_NAME}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])

        mevcut_kuyruk = []
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
                    mevcut_kuyruk = json.loads(icerik)
                    if not isinstance(mevcut_kuyruk, list):
                        mevcut_kuyruk = []
            except Exception:
                mevcut_kuyruk = []

        # Aynı sipariş için bekleyen önceki karar varsa güncelle
        mevcut_kuyruk = [k for k in mevcut_kuyruk if int(k.get("siparis_no", -1)) != int(siparis_no)]
        mevcut_kuyruk.append({
            "siparis_no": int(siparis_no),
            "karar": yeni_karar,
            "not": aciklama.strip(),
            "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        json_bytes = json.dumps(mevcut_kuyruk, ensure_ascii=False, indent=2).encode("utf-8")
        media = MediaIoBaseUpload(io.BytesIO(json_bytes), mimetype="application/json", resumable=False)

        if file_id:
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {
                "name": QUEUE_FILE_NAME,
                "parents": [folder_id]
            }
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        # İyimser yerel önbellek güncellemesi
        if "lokal_kararlar" not in st.session_state:
            st.session_state["lokal_kararlar"] = {}
        st.session_state["lokal_kararlar"][int(siparis_no)] = {
            "karar": yeni_karar,
            "not": aciklama.strip()
        }
        return True
    except Exception as e:
        st.error(f"Karar Google Drive'a iletilemedi: {e}")
        return False


@st.cache_data(ttl=25, show_spinner=False)
def load_orders_from_drive():
    """Google Drive üzerindeki şifreli .db.enc dosyasını indirir, çözer ve tüm siparişleri tek seferde çeker."""
    folder_id = st.secrets["GDRIVE_FOLDER_ID"]
    db_filename = st.secrets.get("DB_FILENAME", "siparis_takip.db.enc")
    fernet_key = st.secrets["DB_ENCRYPTION_KEY"].encode("utf-8")

    service = get_drive_service()

    query = f"name='{db_filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc"
    ).execute()
    files = results.get("files", [])

    if not files:
        raise FileNotFoundError(f"Google Drive klasöründe '{db_filename}' dosyası bulunamadı.")

    file_meta = files[0]
    file_id = file_meta["id"]
    modified_time = file_meta.get("modifiedTime", "")

    # Bekleyen mobil karar kuyruğunu da oku
    bekleyen_kararlar = {}
    q_queue = f"name='{QUEUE_FILE_NAME}' and '{folder_id}' in parents and trashed=false"
    res_q = service.files().list(q=q_queue, fields="files(id)").execute()
    q_files = res_q.get("files", [])
    if q_files:
        req_q = service.files().get_media(fileId=q_files[0]["id"])
        fh_q = io.BytesIO()
        dl_q = MediaIoBaseDownload(fh_q, req_q)
        done_q = False
        while not done_q:
            _, done_q = dl_q.next_chunk()
        try:
            q_list = json.loads(fh_q.getvalue().decode("utf-8"))
            if isinstance(q_list, list):
                for item in q_list:
                    bekleyen_kararlar[int(item["siparis_no"])] = {
                        "karar": item.get("karar", ""),
                        "not": item.get("not", "")
                    }
        except Exception:
            pass

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    fernet = Fernet(fernet_key)
    decrypted_bytes = fernet.decrypt(fh.getvalue())

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(decrypted_bytes)
        tmp_path = tmp.name

    try:
        conn = sqlite3.connect(tmp_path)
        df_orders = pd.read_sql_query("SELECT * FROM siparisler ORDER BY siparis_no DESC", conn)
        df_items = pd.read_sql_query("SELECT siparis_no, urun, birim, miktar FROM siparis_kalemleri", conn)
        conn.close()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    items_map = {}
    for _, r in df_items.iterrows():
        s_no = int(r["siparis_no"])
        items_map.setdefault(s_no, []).append({
            "urun": str(r["urun"] or ""),
            "birim": str(r["birim"] or ""),
            "miktar": format_miktar(r["miktar"])
        })

    return df_orders, items_map, modified_time, bekleyen_kararlar


# ==========================================
# ŞİFRE KORUMASI
# ==========================================
def check_mobile_password():
    app_pass = st.secrets.get("APP_PASSWORD", "")
    if not app_pass:
        return True

    if st.session_state.get("mobil_auth_ok"):
        return True

    st.markdown("""
    <div class="app-header">
        <div class="app-title">SAYAR YAPI | MOBİL ERİŞİM</div>
        <div class="app-subtitle">Sipariş izleme ekranına erişmek için şifre giriniz</div>
    </div>
    """, unsafe_allow_html=True)

    pwd = st.text_input("Erişim Şifresi", type="password", placeholder="Şifrenizi girin...")
    if st.button("Giriş Yap", type="primary", use_container_width=True):
        if pwd == app_pass:
            st.session_state["mobil_auth_ok"] = True
            st.rerun()
        else:
            st.error("Hatalı şifre!")
    return False


# ==========================================
# REVİZE NOTU AÇILIR PENCERESİ (DIALOG)
# ==========================================
@st.dialog("Revize Notu")
def revize_not_penceresi(siparis_no: int):
    st.caption(f"Sipariş #{siparis_no} için revize açıklaması giriniz:")
    revize_notu = st.text_area(
        "Revize Açıklaması",
        placeholder="Revize sebebini yazınız...",
        height=110,
        label_visibility="collapsed"
    )
    c_gonder, c_iptal = st.columns(2)
    with c_gonder:
        if st.button("Revize Gönder", type="primary", use_container_width=True):
            if mobil_karar_gonder(siparis_no, "REVİZE İSTENDİ", revize_notu):
                st.session_state["flash_mesaj"] = f"Sipariş #{siparis_no} REVİZE İSTENDİ kararı iletildi."
                st.session_state["onay_inceleme_no"] = None
                st.rerun()
    with c_iptal:
        if st.button("İptal", use_container_width=True):
            st.rerun()


# ==========================================
# DETAY & ONAY İNCELEME EKRANLARI
# ==========================================
def render_onay_inceleme_ekrani(row, items):
    """'Onayla / İncele' tıklandığında açılan sadeleştirilmiş onay ekranı."""
    sip_no = int(row["siparis_no"])
    op_val = str(row.get("operasyon") or "ONAY BEKLİYOR").strip().upper()
    op_bg = OP_RENK.get(op_val, "#ea580c")

    col_baslik, col_kapat = st.columns([8, 1])
    with col_baslik:
        st.markdown(f"### 📋 Sipariş Onay İncelemesi — #{sip_no}")
    with col_kapat:
        if st.button("✕", key="btn_vazgec_top", type="tertiary"):
            st.session_state["onay_inceleme_no"] = None
            st.rerun()

    st.markdown(f"""
    <div class="detail-box">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:0.95rem; font-weight:800; color:#f8fafc;">{row.get('firma') or '-'}</span>
            <span class="badge" style="background-color:{op_bg};">{op_val}</span>
        </div>
        <div style="font-size:0.86rem; font-weight:700; color:#38bdf8; margin-top:3px;">{row.get('musteri') or '-'}</div>
        <div class="detail-grid">
            <div class="detail-item"><div class="detail-label">Sipariş Tarihi</div><div class="detail-val">{row.get('tarih') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Sevk Tarihi</div><div class="detail-val">{row.get('sevk_tarihi') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Şantiye</div><div class="detail-val">{row.get('santiye') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Şehir</div><div class="detail-val">{row.get('sehir') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Fabrika</div><div class="detail-val">{row.get('fabrika') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Nakliye</div><div class="detail-val">{row.get('nakliye') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Araç Tipi</div><div class="detail-val">{row.get('arac') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Ted. Sip. No</div><div class="detail-val">{row.get('ted_sip_no') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Sipariş Veren</div><div class="detail-val">{row.get('siparis_veren') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Firma Yetkili</div><div class="detail-val">{row.get('firma_yetkili') or '-'}</div></div>
        </div>
        {f'<div class="note-box"><b>Mevcut Not:</b> {row.get("notlar")}</div>' if str(row.get("notlar") or "").strip() else ''}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**📦 Sipariş Ürün Kalemleri**")
    if not items:
        st.info("Bu siparişe ait ürün kalemi bulunmuyor.")
    else:
        for it in items:
            birim_str = f" {it['birim']}" if it["birim"] else ""
            st.markdown(f"""
            <div class="product-row">
                <span class="product-name">{it['urun']}</span>
                <span class="product-qty">{it['miktar']}{birim_str}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**⚡ Yönetici Kararı**")

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("✅ Onayla", key="btn_karar_onayla", type="primary", use_container_width=True):
            if mobil_karar_gonder(sip_no, "ONAYLANDI", ""):
                st.session_state["flash_mesaj"] = f"Sipariş #{sip_no} ONAYLANDI kararı iletildi."
                st.session_state["onay_inceleme_no"] = None
                st.rerun()

    with b2:
        if st.button("🔄 Revize", key="btn_karar_revize", use_container_width=True):
            revize_not_penceresi(sip_no)

    with b3:
        if st.button("❌ Reddet", key="btn_karar_reddet", use_container_width=True):
            if mobil_karar_gonder(sip_no, "REDDEDİLDİ", ""):
                st.session_state["flash_mesaj"] = f"Sipariş #{sip_no} REDDEDİLDİ kararı iletildi."
                st.session_state["onay_inceleme_no"] = None
                st.rerun()


def render_detay_ekrani(row, items):
    """Normal sipariş kartından 'Detay' tıklandığında açılan tam görünüm."""
    sip_no = int(row["siparis_no"])
    op_val = str(row.get("operasyon") or "-").strip().upper()
    durum_val = format_durum_text(row.get("durum")) or "-"
    op_bg = OP_RENK.get(op_val, "#475569")

    if st.button("← Sipariş Listesine Dön", use_container_width=True):
        st.session_state["selected_order_no"] = None
        st.rerun()

    st.markdown(f"""
    <div class="detail-box">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.1rem; font-weight:800; color:#38bdf8;">Sipariş #{sip_no}</span>
            <span class="badge" style="background-color:{op_bg};">{op_val}</span>
        </div>
        <div style="font-size:0.8rem; color:#cbd5e1; margin-top:4px;">Sipariş Durumu: <b>{durum_val}</b></div>
        <div class="detail-grid">
            <div class="detail-item"><div class="detail-label">Sipariş Tarihi</div><div class="detail-val">{row.get('tarih') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Sevk Tarihi</div><div class="detail-val">{row.get('sevk_tarihi') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Firma</div><div class="detail-val">{row.get('firma') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Müşteri</div><div class="detail-val">{row.get('musteri') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Şantiye</div><div class="detail-val">{row.get('santiye') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Şehir</div><div class="detail-val">{row.get('sehir') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Yetkili</div><div class="detail-val">{row.get('yetkili') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Telefon</div><div class="detail-val">{row.get('telefon') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Fabrika</div><div class="detail-val">{row.get('fabrika') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Nakliye</div><div class="detail-val">{row.get('nakliye') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Araç Tipi</div><div class="detail-val">{row.get('arac') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Plaka</div><div class="detail-val">{row.get('plaka') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Ted. Sip. No</div><div class="detail-val">{row.get('ted_sip_no') or '-'}</div></div>
            <div class="detail-item"><div class="detail-label">Sipariş Veren</div><div class="detail-val">{row.get('siparis_veren') or '-'}</div></div>
        </div>
        {f'<div class="note-box"><b>Not:</b> {row.get("notlar")}</div>' if str(row.get("notlar") or "").strip() else ''}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**📦 Ürün Kalemleri**")
    if not items:
        st.info("Bu siparişe ait ürün kalemi girilmemiş.")
    else:
        for it in items:
            birim_str = f" {it['birim']}" if it["birim"] else ""
            st.markdown(f"""
            <div class="product-row">
                <span class="product-name">{it['urun']}</span>
                <span class="product-qty">{it['miktar']}{birim_str}</span>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# ANA UYGULAMA AKIŞI
# ==========================================
def main():
    if not check_mobile_password():
        return

    if "aktif_kpi" not in st.session_state:
        st.session_state["aktif_kpi"] = "TUMU"
    if "selected_order_no" not in st.session_state:
        st.session_state["selected_order_no"] = None
    if "onay_inceleme_no" not in st.session_state:
        st.session_state["onay_inceleme_no"] = None

    # 2 saniyelik geçici bildirim alanı
    flash_box = st.empty()
    flash_msg = st.session_state.pop("flash_mesaj", None)
    if flash_msg:
        flash_box.success(flash_msg)

    try:
        df, items_map, modified_time, drive_kuyruk = load_orders_from_drive()
    except Exception as e:
        st.error("Google Drive veritabanına bağlanırken hata oluştu.")
        st.exception(e)
        if st.button("Tekrar Dene", type="primary"):
            st.cache_data.clear()
            st.rerun()
        return

    # Bekleyen mobil kararları görüntülenen DataFrame üzerine uygula
    birlesik_kararlar = {}
    birlesik_kararlar.update(drive_kuyruk)
    birlesik_kararlar.update(st.session_state.get("lokal_kararlar", {}))

    if birlesik_kararlar and not df.empty:
        for idx, r in df.iterrows():
            s_no = int(r["siparis_no"])
            if s_no in birlesik_kararlar:
                yeni_k = birlesik_kararlar[s_no]["karar"]
                ek_not = birlesik_kararlar[s_no]["not"]
                df.at[idx, "operasyon"] = yeni_k
                if ek_not:
                    eski = str(r.get("notlar") or "").strip()
                    df.at[idx, "notlar"] = f"{eski}\n[Mobil {yeni_k}]: {ek_not}".strip() if eski else f"[Mobil {yeni_k}]: {ek_not}"

    # 1) Onay İnceleme Ekranı Açık İse
    if st.session_state["onay_inceleme_no"] is not None:
        hedef_no = st.session_state["onay_inceleme_no"]
        secili_df = df[df["siparis_no"] == hedef_no]
        if not secili_df.empty:
            render_onay_inceleme_ekrani(secili_df.iloc[0], items_map.get(hedef_no, []))
            if flash_msg:
                time.sleep(2)
                flash_box.empty()
            return
        else:
            st.session_state["onay_inceleme_no"] = None

    # 2) Normal Detay Ekranı Açık İse
    if st.session_state["selected_order_no"] is not None:
        hedef_no = st.session_state["selected_order_no"]
        secili_df = df[df["siparis_no"] == hedef_no]
        if not secili_df.empty:
            render_detay_ekrani(secili_df.iloc[0], items_map.get(hedef_no, []))
            if flash_msg:
                time.sleep(2)
                flash_box.empty()
            return
        else:
            st.session_state["selected_order_no"] = None

    # Üst Başlık ve Yenile Butonu
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        son_guncelleme = modified_time.replace("T", " ")[:16] if modified_time else "-"
        st.markdown(f"""
        <div class="app-header">
            <div class="app-title">SAYAR YAPI | SİPARİŞ İZLEME</div>
            <div class="app-subtitle">Son Senkronizasyon (UTC): {son_guncelleme}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Yenile", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Tıklanabilir KPI Özet Kartları
    op_series = df["operasyon"].fillna("").astype(str).str.strip().str.upper()
    toplam_sayi = len(df)
    onay_bekleyen = int((op_series == "ONAY BEKLİYOR").sum())
    onaylanan = int((op_series == "ONAYLANDI").sum())
    tamamlanan = int((op_series == "TAMAMLANDI").sum())

    aktif_kpi = st.session_state["aktif_kpi"]

    def kpi_tikla(secim_kodu: str):
        st.session_state["aktif_kpi"] = "TUMU" if st.session_state["aktif_kpi"] == secim_kodu else secim_kodu
        st.rerun()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        if st.button(f"TOPLAM\n{toplam_sayi}", key="kpi_tumu", type="primary" if aktif_kpi == "TUMU" else "secondary", use_container_width=True):
            st.session_state["aktif_kpi"] = "TUMU"
            st.rerun()
    with k2:
        if st.button(f"ONAY BEKL.\n{onay_bekleyen}", key="kpi_bekleyen", type="primary" if aktif_kpi == "ONAY BEKLİYOR" else "secondary", use_container_width=True):
            kpi_tikla("ONAY BEKLİYOR")
    with k3:
        if st.button(f"ONAYLI\n{onaylanan}", key="kpi_onayli", type="primary" if aktif_kpi == "ONAYLANDI" else "secondary", use_container_width=True):
            kpi_tikla("ONAYLANDI")
    with k4:
        if st.button(f"TAMAM\n{tamamlanan}", key="kpi_tamam", type="primary" if aktif_kpi == "TAMAMLANDI" else "secondary", use_container_width=True):
            kpi_tikla("TAMAMLANDI")

    # Arama ve Hızlı Filtreler
    arama = st.text_input(
        "Arama",
        placeholder="🔍 Firma, Müşteri, Şantiye, Fabrika veya Sipariş No ara...",
        label_visibility="collapsed"
    )

    f1, f2 = st.columns([3, 2])
    with f1:
        op_listesi = ["Tüm Operasyonlar"] + sorted([x for x in op_series.unique() if x])
        secili_op = st.selectbox("Operasyon", op_listesi, label_visibility="collapsed")
    with f2:
        tamam_gizle = st.checkbox("Tamamlananları Gizle", value=True)

    # Filtreleme Uygulama
    filtered = df.copy()
    f_op = filtered["operasyon"].fillna("").astype(str).str.strip().str.upper()

    if aktif_kpi != "TUMU":
        filtered = filtered[f_op == aktif_kpi]
        f_op = filtered["operasyon"].fillna("").astype(str).str.strip().str.upper()
    elif tamam_gizle and secili_op != "TAMAMLANDI":
        filtered = filtered[f_op != "TAMAMLANDI"]
        f_op = filtered["operasyon"].fillna("").astype(str).str.strip().str.upper()

    if secili_op != "Tüm Operasyonlar":
        filtered = filtered[f_op == secili_op]

    if arama.strip():
        q = arama.strip().lower()
        mask = (
            filtered["siparis_no"].astype(str).str.contains(q, na=False) |
            filtered["firma"].fillna("").astype(str).str.lower().str.contains(q, na=False) |
            filtered["musteri"].fillna("").astype(str).str.lower().str.contains(q, na=False) |
            filtered["santiye"].fillna("").astype(str).str.lower().str.contains(q, na=False) |
            filtered["fabrika"].fillna("").astype(str).str.lower().str.contains(q, na=False) |
            filtered["ted_sip_no"].fillna("").astype(str).str.lower().str.contains(q, na=False)
        )
        filtered = filtered[mask]

    st.caption(f"Gösterilen sipariş sayısı: **{len(filtered)}**")

    if filtered.empty:
        st.info("Seçilen filtrelere uygun sipariş bulunamadı.")
    else:
        max_gosterim = 40
        gosterilecek_df = filtered.head(max_gosterim)

        for _, row in gosterilecek_df.iterrows():
            sip_no = int(row["siparis_no"])
            op_val = str(row.get("operasyon") or "-").strip().upper()
            op_bg = OP_RENK.get(op_val, "#475569")

            firma = str(row.get("firma") or "-")
            musteri = str(row.get("musteri") or "-")
            santiye = str(row.get("santiye") or "-")
            tarih = str(row.get("tarih") or "-")

            st.markdown(f"""
            <div class="order-card">
                <div class="card-top-row">
                    <span class="badge" style="background-color:{op_bg};">{op_val}</span>
                    <span style="font-size:0.75rem; color:#94a3b8; font-weight:700;">#{sip_no}</span>
                </div>
                <div class="card-company">{firma}</div>
                <div class="card-customer">{musteri}</div>
                <div class="card-site">📍 {santiye}</div>
                <div class="card-date-row">📅 Sipariş Tarihi: {tarih}</div>
            </div>
            """, unsafe_allow_html=True)

            if op_val == "ONAY BEKLİYOR":
                c_btn1, c_btn2 = st.columns([2, 1])
                with c_btn1:
                    if st.button("🔍 Onayla / İncele", key=f"onay_btn_{sip_no}", type="primary", use_container_width=True):
                        st.session_state["onay_inceleme_no"] = sip_no
                        st.rerun()
                with c_btn2:
                    if st.button("Detay", key=f"detay_btn_{sip_no}", use_container_width=True):
                        st.session_state["selected_order_no"] = sip_no
                        st.rerun()
            else:
                if st.button("Detay", key=f"detay_btn_{sip_no}", use_container_width=True):
                    st.session_state["selected_order_no"] = sip_no
                    st.rerun()

        if len(filtered) > max_gosterim:
            st.info(f"İlk {max_gosterim} sipariş gösteriliyor. Diğer kayıtlar için arama veya filtre kullanabilirsiniz.")

    # Geçici onay/revize/ret mesajını 2 saniye gösterip temizle
    if flash_msg:
        time.sleep(2)
        flash_box.empty()


if __name__ == "__main__":
    main()
