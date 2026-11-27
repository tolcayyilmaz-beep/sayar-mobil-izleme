import os
import hashlib
import urllib.request
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

st.set_page_config(
    page_title="SAYAR YAPI • Mobil Sipariş",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

RAILWAY_DEFAULT_DB_URL = "postgresql://postgres:vRnqPZifPAhgHJkVconMThDtIillFNFN@trolley.proxy.rlwy.net:41607/railway"
NTFY_TOPIC_URL = "https://ntfy.sh/sayar_yapi_siparis_2026xxx"
MOBIL_IZLEME_URL = "https://sayar-yapi-kamyon.up.railway.app"


def get_db_url():
    url = os.environ.get("DATABASE_URL", "").strip() or RAILWAY_DEFAULT_DB_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def get_conn():
    return psycopg2.connect(get_db_url(), connect_timeout=10, cursor_factory=RealDictCursor)


def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    if not stored_password_hash:
        return False
    if ":" not in stored_password_hash:
        return stored_password_hash == provided_password
    try:
        salt_hex, key_hex = stored_password_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt, 100000)
        return new_key == key
    except Exception:
        return False


def format_durum_text(val) -> str:
    metin = str(val or "").strip()
    if not metin:
        return ""
    tr_upper = metin.replace("i", "İ").replace("ı", "I").upper()
    if tr_upper in ("SEVK EDİLDİ", "İPTAL"):
        return tr_upper
    return metin


def send_ntfy_notification(siparis_no, firma, musteri, operasyon):
    try:
        baslik = f"Yeni Siparis #{siparis_no}"
        safe_title = (
            baslik.replace("İ", "I").replace("ı", "i")
            .replace("Ş", "S").replace("ş", "s")
            .replace("Ğ", "G").replace("ğ", "g")
            .replace("Ü", "U").replace("ü", "u")
            .replace("Ö", "O").replace("ö", "o")
            .replace("Ç", "C").replace("ç", "c")
        )
        mesaj = f"Firma: {firma}\nMüşteri: {musteri}\nOperasyon Durumu: {operasyon}"
        req = urllib.request.Request(NTFY_TOPIC_URL, data=mesaj.encode("utf-8"), method="POST")
        req.add_header("Title", safe_title)
        req.add_header("Priority", "high")
        req.add_header("Tags", "package")
        req.add_header("Click", MOBIL_IZLEME_URL)
        req.add_header("Actions", f"view, Onayla, {MOBIL_IZLEME_URL}")
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception:
        pass


def get_tanimlar(cur, kategori, sadece_aktif=False):
    if kategori == "ÜRÜN" and sadece_aktif:
        cur.execute(
            "SELECT DISTINCT deger FROM tanimlar WHERE kategori='ÜRÜN' AND COALESCE(aktif, 1)=1 ORDER BY deger ASC"
        )
    else:
        cur.execute(
            "SELECT DISTINCT deger FROM tanimlar WHERE kategori=%s ORDER BY deger ASC",
            (kategori,)
        )
    return [r["deger"] for r in cur.fetchall() if r["deger"]]


def get_default_tanim(cur, kategori):
    if kategori == "ÜRÜN":
        cur.execute(
            "SELECT deger FROM tanimlar WHERE kategori='ÜRÜN' AND is_default=1 AND COALESCE(aktif, 1)=1 LIMIT 1"
        )
    else:
        cur.execute(
            "SELECT deger FROM tanimlar WHERE kategori=%s AND is_default=1 LIMIT 1",
            (kategori,)
        )
    row = cur.fetchone()
    return row["deger"] if row else ""


def ensure_tanim(cur, kategori, deger):
    val = (format_durum_text(deger) if kategori == "SİPARİŞ DURUMU" else str(deger or "").strip())
    if not val:
        return
    cur.execute(
        "INSERT INTO tanimlar (kategori, deger, aktif) VALUES (%s, %s, 1) ON CONFLICT DO NOTHING",
        (kategori, val)
    )


def inject_mobile_css():
    st.markdown(
        """
        <style>
        /* Mobil tam uyum ve yatay taşma engeli */
        html, body, [data-testid="stAppViewContainer"], .main {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
            overflow-x: hidden !important;
            max-width: 100vw !important;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {
            display: none !important;
        }
        .block-container {
            padding: 0.45rem 0.55rem 2rem 0.55rem !important;
            max-width: 520px !important;
            margin: 0 auto !important;
        }
        /* Sabit Üst Başlık */
        .sy-topbar {
            position: sticky;
            top: 0;
            z-index: 99;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 8px 11px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05);
        }
        .sy-brand {
            display: flex;
            align-items: center;
            gap: 7px;
            font-weight: 800;
            font-size: 14px;
            color: #0f172a;
        }
        .sy-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.22);
            animation: syPulse 1.8s infinite;
        }
        @keyframes syPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.35; }
        }
        .sy-user-badge {
            font-size: 11px;
            font-weight: 700;
            color: #475569;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 2px 8px;
            border-radius: 99px;
        }
        /* 4'lü Kompakt KPI Şeridi */
        .sy-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 5px;
            margin-bottom: 6px;
        }
        .sy-kpi {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 6px 3px;
            text-align: center;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
        }
        .sy-kpi-val {
            font-size: 15px;
            font-weight: 800;
            line-height: 1.1;
            display: block;
        }
        .sy-kpi-lbl {
            font-size: 9px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
        }
        /* Kompakt Form ve Girdi Elemanları */
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stTextArea"] textarea {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 7px !important;
            font-size: 13px !important;
            min-height: 36px !important;
            padding: 4px 9px !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 7px !important;
            min-height: 36px !important;
            font-size: 13px !important;
        }
        label[data-testid="stWidgetLabel"] p {
            font-size: 11px !important;
            font-weight: 700 !important;
            color: #475569 !important;
            margin-bottom: 1px !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.42rem !important;
        }
        /* Tam Genişlik Kompakt Butonlar */
        .stButton > button, .stFormSubmitButton > button {
            width: 100% !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            font-size: 12.5px !important;
            min-height: 36px !important;
            padding: 4px 10px !important;
        }
        /* Accordion Sipariş Kartları */
        div[data-testid="stExpander"] {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 9px !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
            margin-bottom: 2px !important;
        }
        div[data-testid="stExpander"] details summary p {
            font-size: 12.5px !important;
            font-weight: 700 !important;
            color: #0f172a !important;
            word-break: break-word !important;
        }
        .sy-meta-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px 8px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 7px;
            padding: 7px 8px;
            margin-bottom: 6px;
            font-size: 11.5px;
        }
        .sy-meta-grid span {
            color: #64748b;
            font-size: 10px;
            display: block;
        }
        .sy-meta-grid strong {
            color: #0f172a;
            font-weight: 700;
            word-break: break-word;
        }
        .sy-item-row {
            display: flex;
            justify-content: space-between;
            gap: 6px;
            padding: 4px 8px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 11.5px;
            margin-bottom: 4px;
        }
        .sy-badge {
            display: inline-block;
            padding: 2px 7px;
            border-radius: 5px;
            color: #ffffff;
            font-size: 10px;
            font-weight: 800;
        }
        /* Tabs */
        button[data-baseweb="tab"] {
            flex: 1 !important;
            font-weight: 700 !important;
            font-size: 12.5px !important;
            padding: 6px 4px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login():
    st.markdown(
        """
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px;
                    padding:16px 14px; margin-top:18px; text-align:center;
                    box-shadow:0 4px 14px rgba(15,23,42,0.05);">
            <div style="font-size:17px; font-weight:900; color:#0f172a;">SAYAR YAPI</div>
            <div style="font-size:11px; color:#64748b; font-weight:600;">Mobil Sipariş & Sevkiyat Paneli</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        username = st.text_input("Kullanıcı Adı", placeholder="Kullanıcı adınız")
        password = st.text_input("Şifre", type="password", placeholder="••••••")
        submitted = st.form_submit_button("Giriş Yap", type="primary")
        if submitted:
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, kullanici_adi, sifre, rol, kendi_siparisleri_gor, kullanici_siparis_veren "
                        "FROM kullanicilar WHERE kullanici_adi=%s",
                        (username.strip(),),
                    )
                    u = cur.fetchone()
            finally:
                conn.close()

            if u and verify_password(u["sifre"], password.strip()):
                st.session_state["mobil_user"] = {
                    "id": u["id"],
                    "username": u["kullanici_adi"],
                    "role": u["rol"],
                    "kendi_siparisleri_gor": u["kendi_siparisleri_gor"] or 0,
                    "siparis_veren": u["kullanici_siparis_veren"] or "",
                }
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")


def load_mobile_data(user, q_text, op_filter, firma_filter):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            tanimlar = {
                "FIRMA": get_tanimlar(cur, "FİRMA"),
                "MUSTERI": get_tanimlar(cur, "MÜŞTERİ"),
                "SANTIYE": get_tanimlar(cur, "ŞANTİYE"),
                "SEHIR": get_tanimlar(cur, "ŞEHİR"),
                "ARAC": get_tanimlar(cur, "ARAÇ"),
                "FABRIKA": get_tanimlar(cur, "FABRİKA"),
                "NAKLIYE": get_tanimlar(cur, "NAKLİYE"),
                "SIPARIS_VEREN": get_tanimlar(cur, "SİPARİŞ VEREN"),
                "FIRMA_YETKILI": get_tanimlar(cur, "FİRMA YETKİLİ"),
                "DURUM": [format_durum_text(x) for x in get_tanimlar(cur, "SİPARİŞ DURUMU")],
                "OPERASYON": get_tanimlar(cur, "OPERASYON"),
                "URUN": get_tanimlar(cur, "ÜRÜN", sadece_aktif=True),
                "BIRIM": get_tanimlar(cur, "BİRİM"),
            }
            defaults = {
                "FIRMA": get_default_tanim(cur, "FİRMA"),
                "ARAC": get_default_tanim(cur, "ARAÇ"),
                "FABRIKA": get_default_tanim(cur, "FABRİKA"),
                "NAKLIYE": get_default_tanim(cur, "NAKLİYE"),
                "SIPARIS_VEREN": get_default_tanim(cur, "SİPARİŞ VEREN"),
                "FIRMA_YETKILI": get_default_tanim(cur, "FİRMA YETKİLİ"),
                "DURUM": format_durum_text(get_default_tanim(cur, "SİPARİŞ DURUMU")),
                "OPERASYON": get_default_tanim(cur, "OPERASYON"),
                "URUN": get_default_tanim(cur, "ÜRÜN"),
                "BIRIM": get_default_tanim(cur, "BİRİM"),
            }

            cur.execute("SELECT COUNT(*) AS c FROM siparisler")
            toplam = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM siparisler WHERE operasyon='ONAY BEKLİYOR'")
            bekleyen = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM siparisler WHERE operasyon='ONAYLANDI'")
            onayli = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM siparisler WHERE operasyon='TAMAMLANDI'")
            tamam = cur.fetchone()["c"]
            kpi = {"toplam": toplam, "bekleyen": bekleyen, "onayli": onayli, "tamam": tamam}

            sql = "SELECT * FROM siparisler WHERE 1=1"
            params = []

            if user.get("kendi_siparisleri_gor") == 1 and user.get("siparis_veren"):
                sql += " AND siparis_veren = %s"
                params.append(user["siparis_veren"])

            if op_filter == "Aktifler":
                sql += " AND COALESCE(operasyon, '') NOT IN ('TAMAMLANDI', 'İPTAL EDİLDİ') AND UPPER(COALESCE(durum, '')) != 'İPTAL'"
            elif op_filter != "Tümü":
                sql += " AND operasyon = %s"
                params.append(op_filter)

            if firma_filter and firma_filter != "Tümü":
                sql += " AND firma = %s"
                params.append(firma_filter)

            if q_text.strip():
                sql += (
                    " AND (CAST(siparis_no AS TEXT) ILIKE %s OR firma ILIKE %s OR musteri ILIKE %s "
                    "OR santiye ILIKE %s OR fabrika ILIKE %s OR ted_sip_no ILIKE %s)"
                )
                like = f"%{q_text.strip()}%"
                params.extend([like, like, like, like, like, like])

            sql += " ORDER BY siparis_no DESC LIMIT 60"
            cur.execute(sql, params)
            siparisler = [dict(r) for r in cur.fetchall()]

            if siparisler:
                nos = [s["siparis_no"] for s in siparisler]
                cur.execute(
                    "SELECT siparis_no, urun, birim, miktar FROM siparis_kalemleri WHERE siparis_no = ANY(%s) ORDER BY id ASC",
                    (nos,),
                )
                kalem_map = {}
                for k in cur.fetchall():
                    kalem_map.setdefault(k["siparis_no"], []).append(dict(k))
                for s in siparisler:
                    s["kalemler"] = kalem_map.get(s["siparis_no"], [])
            return tanimlar, defaults, kpi, siparisler
    finally:
        conn.close()


def _select_index(options, target):
    if not target:
        return 0
    for i, opt in enumerate(options):
        if str(opt).strip().upper() == str(target).strip().upper():
            return i
    return 0


def main():
    inject_mobile_css()

    user = st.session_state.get("mobil_user")
    if not user:
        render_login()
        return

    if "mobil_kalemler" not in st.session_state:
        st.session_state["mobil_kalemler"] = []

    # Sabit Üst Bar + Çıkış
    col_head, col_out = st.columns([3.5, 1])
    with col_head:
        st.markdown(
            f"""
            <div class="sy-topbar">
                <div class="sy-brand"><span class="sy-dot"></span> SAYAR YAPI</div>
                <div class="sy-user-badge">{user['username']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_out:
        if st.button("Çıkış", key="btn_logout"):
            st.session_state.pop("mobil_user", None)
            st.rerun()

    q_val = st.session_state.get("f_q", "")
    op_val = st.session_state.get("f_op", "Aktifler")
    firma_val = st.session_state.get("f_firma", "Tümü")

    tanimlar, defaults, kpi, siparisler = load_mobile_data(user, q_val, op_val, firma_val)

    # 4'lü Özet KPI Şeridi
    st.markdown(
        f"""
        <div class="sy-kpi-grid">
            <div class="sy-kpi"><span class="sy-kpi-val" style="color:#0284c7;">{kpi['toplam']}</span><span class="sy-kpi-lbl">Toplam</span></div>
            <div class="sy-kpi"><span class="sy-kpi-val" style="color:#d97706;">{kpi['bekleyen']}</span><span class="sy-kpi-lbl">Onay Bek.</span></div>
            <div class="sy-kpi"><span class="sy-kpi-val" style="color:#0d9488;">{kpi['onayli']}</span><span class="sy-kpi-lbl">Onaylı</span></div>
            <div class="sy-kpi"><span class="sy-kpi-val" style="color:#059669;">{kpi['tamam']}</span><span class="sy-kpi-lbl">Tamam</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if user.get("role") == "OKUMA":
        tab_takip = st.container()
        tab_yeni = None
    else:
        tab_takip, tab_yeni = st.tabs(["📋 Sipariş Takip", "➕ Yeni Sipariş"])

    # ==========================================
    # SEKME 1: SİPARİŞ TAKİP
    # ==========================================
    with tab_takip:
        st.text_input("Ara", key="f_q", placeholder="Firma, müşteri, şantiye, sipariş no...", label_visibility="collapsed")
        op_secenekler = ["Aktifler", "Tümü"] + tanimlar["OPERASYON"]
        st.selectbox("Operasyon Filtresi", op_secenekler, key="f_op")
        firma_secenekler = ["Tümü"] + tanimlar["FIRMA"]
        st.selectbox("Firma Filtresi", firma_secenekler, key="f_firma")

        op_colors = {
            "İŞLENDİ": "#0284c7",
            "ONAY BEKLİYOR": "#d97706",
            "ONAYLANDI": "#0d9488",
            "REVİZE İSTENDİ": "#ca8a04",
            "REDDEDİLDİ": "#b91c1c",
            "TAMAMLANDI": "#059669",
            "İPTAL EDİLDİ": "#dc2626",
            "KISMİ EVRAK": "#7c3aed",
        }

        if not siparisler:
            st.info("Kriterlere uygun sipariş bulunamadı.")
        else:
            with st.container(height=470, border=False):
                for s in siparisler:
                    sip_no = s["siparis_no"]
                    op_txt = str(s.get("operasyon") or "İŞLENDİ").upper()
                    badge_col = op_colors.get(op_txt, "#475569")
                    baslik = f"#{sip_no} • {s.get('musteri') or '-'} ({s.get('santiye') or '-'}) — [{op_txt}]"

                    with st.expander(baslik, expanded=False):
                        st.markdown(
                            f"""
                            <div style="margin-bottom:5px;">
                                <span class="sy-badge" style="background:{badge_col};">{op_txt}</span>
                                <span style="font-size:11px; font-weight:700; color:#475569; margin-left:6px;">{s.get('tarih') or ''}</span>
                            </div>
                            <div class="sy-meta-grid">
                                <div><span>Firma</span><strong>{s.get('firma') or '-'}</strong></div>
                                <div><span>Durum</span><strong>{s.get('durum') or '-'}</strong></div>
                                <div><span>Fabrika</span><strong>{s.get('fabrika') or '-'}</strong></div>
                                <div><span>Nakliye / Araç</span><strong>{s.get('nakliye') or '-'} / {s.get('arac') or '-'}</strong></div>
                                <div><span>Plaka / Ted.No</span><strong>{s.get('plaka') or '-'} / {s.get('ted_sip_no') or '-'}</strong></div>
                                <div><span>Sipariş Veren</span><strong>{s.get('siparis_veren') or '-'}</strong></div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        if s.get("notlar"):
                            st.markdown(
                                f"<div style='background:#fffbeb; border:1px solid #fde68a; border-radius:6px; "
                                f"padding:5px 8px; font-size:11px; color:#92400e; margin-bottom:6px;'>"
                                f"<b>Not:</b> {s['notlar']}</div>",
                                unsafe_allow_html=True,
                            )

                        for k in s.get("kalemler", []):
                            st.markdown(
                                f"<div class='sy-item-row'><span>{k.get('urun') or ''}</span>"
                                f"<strong>{k.get('miktar') or ''} {k.get('birim') or ''}</strong></div>",
                                unsafe_allow_html=True,
                            )

                        if user.get("role") != "OKUMA":
                            with st.form(key=f"upd_form_{sip_no}"):
                                op_opts = tanimlar["OPERASYON"] or ["İŞLENDİ"]
                                dr_opts = tanimlar["DURUM"] or ["Beklemede", "SEVK EDİLDİ", "İPTAL"]

                                new_op = st.selectbox(
                                    "Operasyon",
                                    op_opts,
                                    index=_select_index(op_opts, s.get("operasyon")),
                                    key=f"op_{sip_no}",
                                )
                                new_dr = st.selectbox(
                                    "Sipariş Durumu",
                                    dr_opts,
                                    index=_select_index(dr_opts, s.get("durum")),
                                    key=f"dr_{sip_no}",
                                )
                                new_plaka = st.text_input("Plaka", value=s.get("plaka") or "", key=f"plk_{sip_no}")
                                new_ted = st.text_input("Ted. Sip. No", value=s.get("ted_sip_no") or "", key=f"ted_{sip_no}")

                                if st.form_submit_button("Güncelle", type="primary"):
                                    fin_op = new_op.strip()
                                    fin_dr = format_durum_text(new_dr)
                                    if fin_op.upper() == "TAMAMLANDI":
                                        fin_dr = "SEVK EDİLDİ"
                                    elif fin_op.upper() == "İPTAL EDİLDİ" or fin_dr == "İPTAL":
                                        fin_op = "İPTAL EDİLDİ"
                                        fin_dr = "İPTAL"

                                    conn = get_conn()
                                    try:
                                        with conn.cursor() as cur:
                                            cur.execute(
                                                "UPDATE siparisler SET operasyon=%s, durum=%s, plaka=%s, ted_sip_no=%s WHERE siparis_no=%s",
                                                (fin_op, fin_dr, new_plaka.strip(), new_ted.strip(), sip_no),
                                            )
                                        conn.commit()
                                    finally:
                                        conn.close()
                                    st.success(f"Sipariş #{sip_no} güncellendi.")
                                    st.rerun()

    # ==========================================
    # SEKME 2: YENİ SİPARİŞ GİRME
    # ==========================================
    if tab_yeni is not None:
        with tab_yeni:
            # Ürün kalemi ekleme kutusu (Dikey yığılım, sıfır taşma)
            urun_opts = [""] + tanimlar["URUN"]
            birim_opts = tanimlar["BIRIM"] or ["TON", "ADET", "PALET"]

            sel_urun = st.selectbox(
                "Ürün Seçin",
                urun_opts,
                index=_select_index(urun_opts, defaults["URUN"]),
                key="new_inp_urun",
            )
            sel_birim = st.selectbox(
                "Birim",
                birim_opts,
                index=_select_index(birim_opts, defaults["BIRIM"]),
                key="new_inp_birim",
            )
            inp_miktar = st.text_input("Miktar / Tonaj", placeholder="Örn: 25", key="new_inp_miktar")

            if st.button("+ Ürün Kalemi Ekle", key="btn_add_kalem"):
                if sel_urun.strip() and inp_miktar.strip():
                    st.session_state["mobil_kalemler"].append(
                        {"urun": sel_urun.strip(), "birim": sel_birim.strip(), "miktar": inp_miktar.strip()}
                    )
                    st.rerun()
                else:
                    st.warning("Lütfen ürün seçin ve miktar girin.")

            if st.session_state["mobil_kalemler"]:
                for idx, k in enumerate(st.session_state["mobil_kalemler"]):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(
                            f"<div class='sy-item-row'><span>{k['urun']}</span>"
                            f"<strong>{k['miktar']} {k['birim']}</strong></div>",
                            unsafe_allow_html=True,
                        )
                    with c2:
                        if st.button("Sil", key=f"del_k_{idx}"):
                            st.session_state["mobil_kalemler"].pop(idx)
                            st.rerun()

            with st.form("yeni_siparis_form", clear_on_submit=False):
                tarih_val = st.date_input("Tarih", value=date.today())
                sevk_val = st.date_input("Sevk Tarihi", value=date.today())

                firma_opts = [""] + tanimlar["FIRMA"]
                firma_val = st.selectbox("Firma *", firma_opts, index=_select_index(firma_opts, defaults["FIRMA"]))

                musteri_sec = st.selectbox("Müşteri (Listeden) *", ["[Yeni Yaz]"] + tanimlar["MUSTERI"])
                musteri_yaz = st.text_input("Müşteri Adı (Listede yoksa yazın)", placeholder="Müşteri ünvanı")

                santiye_sec = st.selectbox("Şantiye (Listeden) *", ["[Yeni Yaz]"] + tanimlar["SANTIYE"])
                santiye_yaz = st.text_input("Şantiye Adı (Listede yoksa yazın)", placeholder="Şantiye adı")

                sehir_opts = [""] + tanimlar["SEHIR"]
                sehir_val = st.selectbox("Şehir", sehir_opts)
                telefon_val = st.text_input("Telefon", placeholder="05XX XXX XX XX")
                yetkili_val = st.text_input("Şantiye Yetkili", placeholder="Yetkili kişi")

                arac_opts = [""] + tanimlar["ARAC"]
                arac_val = st.selectbox("Araç *", arac_opts, index=_select_index(arac_opts, defaults["ARAC"]))

                fabrika_opts = [""] + tanimlar["FABRIKA"]
                fabrika_val = st.selectbox("Fabrika *", fabrika_opts, index=_select_index(fabrika_opts, defaults["FABRIKA"]))

                nakliye_opts = [""] + tanimlar["NAKLIYE"]
                nakliye_val = st.selectbox("Nakliye *", nakliye_opts, index=_select_index(nakliye_opts, defaults["NAKLIYE"]))

                veren_opts = [""] + tanimlar["SIPARIS_VEREN"]
                def_veren = user.get("siparis_veren") or defaults["SIPARIS_VEREN"]
                veren_val = st.selectbox("Sipariş Veren *", veren_opts, index=_select_index(veren_opts, def_veren))

                fy_opts = [""] + tanimlar["FIRMA_YETKILI"]
                fy_val = st.selectbox("Firma Yetkili", fy_opts, index=_select_index(fy_opts, defaults["FIRMA_YETKILI"]))

                dr_opts = tanimlar["DURUM"] or ["Beklemede"]
                dr_val = st.selectbox("Sipariş Durumu", dr_opts, index=_select_index(dr_opts, defaults["DURUM"] or "Beklemede"))

                op_opts = tanimlar["OPERASYON"] or ["İŞLENDİ"]
                op_val = st.selectbox("Operasyon", op_opts, index=_select_index(op_opts, defaults["OPERASYON"] or "İŞLENDİ"))

                not_val = st.text_area("Notlar", placeholder="Teslimat notu...", height=60)

                kaydet_btn = st.form_submit_button("✓ Siparişi Kaydet", type="primary")
                if kaydet_btn:
                    musteri_final = musteri_yaz.strip() if musteri_sec == "[Yeni Yaz]" else musteri_sec.strip()
                    santiye_final = santiye_yaz.strip() if santiye_sec == "[Yeni Yaz]" else santiye_sec.strip()

                    # Ekle butonuna basılmadan bırakılmış ürün varsa otomatik dahil et
                    kalem_listesi = list(st.session_state["mobil_kalemler"])
                    if sel_urun.strip() and inp_miktar.strip():
                        ekli_mi = any(
                            k["urun"] == sel_urun.strip() and k["miktar"] == inp_miktar.strip()
                            for k in kalem_listesi
                        )
                        if not ekli_mi:
                            kalem_listesi.append(
                                {"urun": sel_urun.strip(), "birim": sel_birim.strip(), "miktar": inp_miktar.strip()}
                            )

                    if not (firma_val and musteri_final and santiye_final and arac_val and fabrika_val and nakliye_val and veren_val):
                        st.error("Lütfen zorunlu (*) alanların tamamını doldurun.")
                    else:
                        fin_op = op_val.strip() or "İŞLENDİ"
                        fin_dr = format_durum_text(dr_val) or "Beklemede"
                        if fin_op.upper() == "TAMAMLANDI":
                            fin_dr = "SEVK EDİLDİ"
                        elif fin_op.upper() == "İPTAL EDİLDİ" or fin_dr == "İPTAL":
                            fin_op = "İPTAL EDİLDİ"
                            fin_dr = "İPTAL"

                        conn = get_conn()
                        try:
                            with conn.cursor() as cur:
                                ensure_tanim(cur, "MÜŞTERİ", musteri_final)
                                ensure_tanim(cur, "ŞANTİYE", santiye_final)
                                if sehir_val:
                                    ensure_tanim(cur, "ŞEHİR", sehir_val)

                                cur.execute(
                                    """
                                    INSERT INTO siparisler (
                                        tarih, firma, musteri, santiye, sehir, telefon, yetkili, arac, fabrika,
                                        nakliye, notlar, sevk_tarihi, ted_sip_no, plaka, nakliye_fatura,
                                        siparis_veren, firma_yetkili, siparis_gecen, durum, operasyon
                                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'','','',%s,%s,%s,%s,%s)
                                    RETURNING siparis_no
                                    """,
                                    (
                                        tarih_val.strftime("%Y-%m-%d"),
                                        firma_val.strip(),
                                        musteri_final,
                                        santiye_final,
                                        sehir_val.strip(),
                                        telefon_val.strip(),
                                        yetkili_val.strip(),
                                        arac_val.strip(),
                                        fabrika_val.strip(),
                                        nakliye_val.strip(),
                                        not_val.strip(),
                                        sevk_val.strftime("%Y-%m-%d"),
                                        veren_val.strip(),
                                        fy_val.strip(),
                                        user["username"],
                                        fin_dr,
                                        fin_op,
                                    ),
                                )
                                sip_no = cur.fetchone()["siparis_no"]

                                for k in kalem_listesi:
                                    cur.execute(
                                        "INSERT INTO siparis_kalemleri (siparis_no, urun, birim, miktar) VALUES (%s,%s,%s,%s)",
                                        (sip_no, k["urun"], k["birim"], k["miktar"]),
                                    )
                            conn.commit()
                        finally:
                            conn.close()

                        st.session_state["mobil_kalemler"] = []
                        send_ntfy_notification(sip_no, firma_val.strip(), musteri_final, fin_op)
                        st.success(f"Sipariş #{sip_no} başarıyla kaydedildi!")
                        st.rerun()


if __name__ == "__main__":
    main()
