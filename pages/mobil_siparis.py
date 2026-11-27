import os
import hashlib
import urllib.request
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, session, redirect, url_for, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sayar_yapi_mobil_2026_secret_key")

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
    except Exception as e:
        print(f"ntfy uyarisi: {e}")


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


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>SAYAR YAPI • Mobil Sipariş</title>
<style>
  :root {
    --bg: #f1f5f9;
    --card: #ffffff;
    --border: #e2e8f0;
    --text: #0f172a;
    --muted: #64748b;
    --primary: #0284c7;
    --primary-dark: #0369a1;
    --success: #059669;
    --warning: #d97706;
    --danger: #dc2626;
    --radius: 10px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  html, body {
    width: 100%; max-width: 100vw; overflow-x: hidden;
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px; line-height: 1.35;
  }
  /* Sabit Üst Bar */
  .topbar {
    position: sticky; top: 0; z-index: 50;
    background: #ffffff; border-bottom: 1px solid var(--border);
    padding: 8px 12px; display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 1px 4px rgba(15,23,42,0.04);
  }
  .brand { display: flex; align-items: center; gap: 7px; font-weight: 800; font-size: 14px; color: #0f172a; }
  .live-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #10b981;
    box-shadow: 0 0 0 3px rgba(16,185,129,0.2);
    animation: pulse 1.8s infinite;
  }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }
  .user-pill {
    font-size: 11px; font-weight: 700; color: var(--muted);
    background: #f8fafc; border: 1px solid var(--border);
    padding: 3px 8px; border-radius: 99px; display: flex; align-items: center; gap: 6px;
  }
  .logout-link { color: var(--danger); text-decoration: none; font-weight: 800; }

  /* Kompakt KPI Şeridi */
  .kpi-row {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
    padding: 8px 10px 4px 10px;
  }
  .kpi {
    background: var(--card); border: 1px solid var(--border); border-radius: 8px;
    padding: 6px 4px; text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
  }
  .kpi .num { font-size: 15px; font-weight: 800; display: block; }
  .kpi .lbl { font-size: 9px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.3px; }

  /* Alt Sekme Geçişi */
  .tabs {
    display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
    padding: 6px 10px; background: var(--bg);
  }
  .tab-btn {
    padding: 8px; border-radius: 8px; border: 1px solid var(--border);
    background: var(--card); color: var(--muted); font-weight: 700; font-size: 12px;
    cursor: pointer; text-align: center;
  }
  .tab-btn.active {
    background: var(--primary); color: #ffffff; border-color: var(--primary);
    box-shadow: 0 2px 6px rgba(2,132,199,0.25);
  }

  .container { padding: 4px 10px 24px 10px; width: 100%; max-width: 100%; }

  /* Arama & Filtre */
  .filter-card {
    background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 8px; margin-bottom: 8px; display: flex; flex-direction: column; gap: 6px;
  }
  .filter-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  input, select, textarea {
    width: 100%; max-width: 100%; height: 34px; padding: 0 9px;
    border: 1px solid #cbd5e1; border-radius: 7px; background: #ffffff;
    color: var(--text); font-size: 12.5px; font-family: inherit;
  }
  textarea { height: 52px; padding: 6px 9px; resize: vertical; }
  input:focus, select:focus, textarea:focus {
    outline: none; border-color: var(--primary); box-shadow: 0 0 0 2px rgba(2,132,199,0.12);
  }

  /* Sipariş Kartları (Accordion) */
  .order-list {
    display: flex; flex-direction: column; gap: 7px;
    max-height: calc(100vh - 225px); overflow-y: auto; padding-right: 1px;
  }
  .order-card {
    background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 9px 10px; box-shadow: 0 1px 3px rgba(15,23,42,0.03);
  }
  .card-head {
    display: flex; justify-content: space-between; align-items: center; gap: 6px;
    cursor: pointer;
  }
  .card-title { font-weight: 800; font-size: 12.5px; color: #0f172a; word-break: break-word; }
  .card-sub { font-size: 11px; color: var(--muted); margin-top: 2px; word-break: break-word; }
  .badge {
    display: inline-block; padding: 2px 7px; border-radius: 6px;
    font-size: 10px; font-weight: 800; color: #fff; white-space: nowrap;
  }
  .card-body {
    display: none; margin-top: 8px; padding-top: 8px;
    border-top: 1px dashed var(--border); font-size: 11.5px;
  }
  .order-card.open .card-body { display: block; }
  .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 8px; margin-bottom: 7px; }
  .meta-item span { color: var(--muted); font-size: 10.5px; display: block; }
  .meta-item strong { font-weight: 700; color: var(--text); word-break: break-word; }

  .items-box {
    background: #f8fafc; border: 1px solid var(--border); border-radius: 7px;
    padding: 5px 8px; margin-bottom: 7px;
  }
  .item-line {
    display: flex; justify-content: space-between; gap: 6px;
    padding: 3px 0; border-bottom: 1px solid #eef2f6; font-size: 11.5px;
  }
  .item-line:last-child { border-bottom: none; }

  /* Hızlı Durum / Operasyon Güncelleme */
  .quick-actions { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; }
  .btn {
    width: 100%; height: 34px; border: none; border-radius: 7px;
    font-weight: 700; font-size: 12px; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; gap: 5px;
  }
  .btn-primary { background: var(--primary); color: #fff; }
  .btn-success { background: var(--success); color: #fff; }
  .btn-outline { background: #f8fafc; color: var(--text); border: 1px solid #cbd5e1; }
  .btn-danger { background: #fee2e2; color: var(--danger); }

  /* Form Alanları (Dikey Yığılım - Sıfır Taşma) */
  .form-card {
    background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 10px; display: flex; flex-direction: column; gap: 7px;
  }
  .field label {
    display: block; font-size: 10.5px; font-weight: 700; color: var(--muted);
    margin-bottom: 2px;
  }
  .kalem-ekle-box {
    background: #f8fafc; border: 1px solid var(--border); border-radius: 8px;
    padding: 8px; display: flex; flex-direction: column; gap: 6px;
  }
  .kalem-list { display: flex; flex-direction: column; gap: 4px; }
  .kalem-chip {
    display: flex; justify-content: space-between; align-items: center; gap: 6px;
    background: #ffffff; border: 1px solid var(--border); border-radius: 6px;
    padding: 5px 8px; font-size: 11.5px; font-weight: 600;
  }
  .del-chip {
    background: #fee2e2; color: var(--danger); border: none; border-radius: 5px;
    padding: 2px 7px; font-weight: 800; cursor: pointer;
  }
  .alert {
    padding: 8px 10px; border-radius: 8px; font-size: 12px; font-weight: 700;
    margin-bottom: 8px;
  }
  .alert-ok { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
  .alert-err { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }

  /* Login Kartı */
  .login-wrap {
    min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 16px;
  }
  .login-card {
    width: 100%; max-width: 360px; background: #fff; border: 1px solid var(--border);
    border-radius: 14px; padding: 20px; box-shadow: 0 8px 24px rgba(15,23,42,0.06);
    display: flex; flex-direction: column; gap: 10px;
  }
</style>
</head>
<body>

{% if not user %}
<div class="login-wrap">
  <form class="login-card" method="POST" action="{{ url_for('login') }}">
    <div style="text-align:center; margin-bottom:4px;">
      <div style="font-size:18px; font-weight:900; color:#0f172a;">SAYAR YAPI</div>
      <div style="font-size:11px; color:#64748b; font-weight:600;">Mobil Sipariş & Sevkiyat</div>
    </div>
    {% if error %}<div class="alert alert-err">{{ error }}</div>{% endif %}
    <div class="field">
      <label>Kullanıcı Adı</label>
      <input type="text" name="username" required autocomplete="username" placeholder="Kullanıcı adı">
    </div>
    <div class="field">
      <label>Şifre</label>
      <input type="password" name="password" required autocomplete="current-password" placeholder="••••••">
    </div>
    <button type="submit" class="btn btn-primary" style="height:38px; margin-top:4px;">Giriş Yap</button>
  </form>
</div>

{% else %}
<div class="topbar">
  <div class="brand"><span class="live-dot"></span> SAYAR YAPI</div>
  <div class="user-pill">
    <span>{{ user.username }}</span>
    <a href="{{ url_for('logout') }}" class="logout-link">Çıkış</a>
  </div>
</div>

<div class="kpi-row">
  <div class="kpi"><span class="num" style="color:#0284c7;">{{ kpi.toplam }}</span><span class="lbl">Toplam</span></div>
  <div class="kpi"><span class="num" style="color:#d97706;">{{ kpi.bekleyen }}</span><span class="lbl">Onay Bek.</span></div>
  <div class="kpi"><span class="num" style="color:#0d9488;">{{ kpi.onayli }}</span><span class="lbl">Onaylı</span></div>
  <div class="kpi"><span class="num" style="color:#059669;">{{ kpi.tamam }}</span><span class="lbl">Tamam</span></div>
</div>

<div class="tabs">
  <button type="button" class="tab-btn {% if active_tab == 'takip' %}active{% endif %}" onclick="switchTab('takip')">📋 Sipariş Takip</button>
  {% if user.role != 'OKUMA' %}
  <button type="button" class="tab-btn {% if active_tab == 'yeni' %}active{% endif %}" onclick="switchTab('yeni')">➕ Yeni Sipariş</button>
  {% endif %}
</div>

<div class="container">
  {% if msg %}<div class="alert alert-ok">{{ msg }}</div>{% endif %}
  {% if error %}<div class="alert alert-err">{{ error }}</div>{% endif %}

  <!-- SEKME 1: SİPARİŞ TAKİP -->
  <div id="tab-takip" style="display: {% if active_tab == 'takip' %}block{% else %}none{% endif %};">
    <form class="filter-card" method="GET" action="{{ url_for('index') }}">
      <input type="text" name="q" value="{{ q }}" placeholder="Ara: Firma, müşteri, şantiye, no...">
      <div class="filter-row">
        <select name="op" onchange="this.form.submit()">
          <option value="">Operasyon: Aktifler</option>
          <option value="TUMU" {% if op == 'TUMU' %}selected{% endif %}>Tümü (Tamam/İptal Dahil)</option>
          {% for o in tanimlar.OPERASYON %}
          <option value="{{ o }}" {% if op == o %}selected{% endif %}>{{ o }}</option>
          {% endfor %}
        </select>
        <select name="firma_f" onchange="this.form.submit()">
          <option value="">Firma: Tümü</option>
          {% for f in tanimlar.FIRMA %}
          <option value="{{ f }}" {% if firma_f == f %}selected{% endif %}>{{ f }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="filter-row">
        <button type="submit" class="btn btn-primary" style="height:30px;">Filtrele</button>
        <a href="{{ url_for('index') }}" class="btn btn-outline" style="height:30px; text-decoration:none;">Sıfırla</a>
      </div>
    </form>

    <div class="order-list">
      {% if not siparisler %}
      <div class="order-card" style="text-align:center; color:#64748b; padding:18px;">Kayıt bulunamadı.</div>
      {% endif %}

      {% for s in siparisler %}
      <div class="order-card" id="card-{{ s.siparis_no }}">
        <div class="card-head" onclick="toggleCard({{ s.siparis_no }})">
          <div style="min-width:0; flex:1;">
            <div class="card-title">#{{ s.siparis_no }} • {{ s.musteri or '-' }}</div>
            <div class="card-sub">{{ s.firma or '-' }} | {{ s.santiye or '-' }} ({{ s.tarih or '' }})</div>
          </div>
          <span class="badge" style="background: {{ s.op_color }};">{{ s.operasyon or 'İŞLENDİ' }}</span>
        </div>

        <div class="card-body">
          <div class="meta-grid">
            <div class="meta-item"><span>Durum</span><strong>{{ s.durum or '-' }}</strong></div>
            <div class="meta-item"><span>Fabrika</span><strong>{{ s.fabrika or '-' }}</strong></div>
            <div class="meta-item"><span>Nakliye / Araç</span><strong>{{ s.nakliye or '-' }} / {{ s.arac or '-' }}</strong></div>
            <div class="meta-item"><span>Plaka / Ted.No</span><strong>{{ s.plaka or '-' }} / {{ s.ted_sip_no or '-' }}</strong></div>
            <div class="meta-item"><span>Sevk Tarihi</span><strong>{{ s.sevk_tarihi or '-' }}</strong></div>
            <div class="meta-item"><span>Sipariş Veren</span><strong>{{ s.siparis_veren or '-' }}</strong></div>
          </div>

          {% if s.notlar %}
          <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:5px 8px; margin-bottom:7px; font-size:11px; color:#92400e;">
            <strong>Not:</strong> {{ s.notlar }}
          </div>
          {% endif %}

          {% if s.kalemler %}
          <div class="items-box">
            {% for k in s.kalemler %}
            <div class="item-line">
              <span>{{ k.urun }}</span>
              <strong>{{ k.miktar }} {{ k.birim }}</strong>
            </div>
            {% endfor %}
          </div>
          {% endif %}

          {% if user.role != 'OKUMA' %}
          <form class="quick-actions" method="POST" action="{{ url_for('update_order', siparis_no=s.siparis_no) }}">
            <div class="filter-row">
              <select name="operasyon">
                {% for o in tanimlar.OPERASYON %}
                <option value="{{ o }}" {% if (s.operasyon or '') == o %}selected{% endif %}>Op: {{ o }}</option>
                {% endfor %}
              </select>
              <select name="durum">
                {% for d in tanimlar.DURUM %}
                <option value="{{ d }}" {% if (s.durum or '') == d %}selected{% endif %}>Dr: {{ d }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="filter-row">
              <input type="text" name="plaka" value="{{ s.plaka or '' }}" placeholder="Plaka">
              <input type="text" name="ted_sip_no" value="{{ s.ted_sip_no or '' }}" placeholder="Ted. Sip No">
            </div>
            <button type="submit" class="btn btn-success" style="height:32px;">Güncelle</button>
          </form>
          {% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- SEKME 2: YENİ SİPARİŞ GİRME -->
  {% if user.role != 'OKUMA' %}
  <div id="tab-yeni" style="display: {% if active_tab == 'yeni' %}block{% else %}none{% endif %};">
    <form class="form-card" method="POST" action="{{ url_for('create_order') }}" onsubmit="return prepareSubmit()">
      <div class="filter-row">
        <div class="field">
          <label>Tarih</label>
          <input type="date" name="tarih" value="{{ today }}">
        </div>
        <div class="field">
          <label>Sevk Tarihi</label>
          <input type="date" name="sevk_tarihi" value="{{ today }}">
        </div>
      </div>

      <div class="field">
        <label>Firma *</label>
        <select name="firma" required>
          <option value="">Seçiniz...</option>
          {% for x in tanimlar.FIRMA %}
          <option value="{{ x }}" {% if defaults.FIRMA == x %}selected{% endif %}>{{ x }}</option>
          {% endfor %}
        </select>
      </div>

      <div class="field">
        <label>Müşteri *</label>
        <input type="text" name="musteri" list="dl-musteri" required placeholder="Müşteri seçin veya yazın">
        <datalist id="dl-musteri">{% for x in tanimlar.MUSTERI %}<option value="{{ x }}">{% endfor %}</datalist>
      </div>

      <div class="field">
        <label>Şantiye *</label>
        <input type="text" name="santiye" list="dl-santiye" required placeholder="Şantiye seçin veya yazın">
        <datalist id="dl-santiye">{% for x in tanimlar.SANTIYE %}<option value="{{ x }}">{% endfor %}</datalist>
      </div>

      <div class="filter-row">
        <div class="field">
          <label>Şehir</label>
          <input type="text" name="sehir" list="dl-sehir" placeholder="Şehir">
          <datalist id="dl-sehir">{% for x in tanimlar.SEHIR %}<option value="{{ x }}">{% endfor %}</datalist>
        </div>
        <div class="field">
          <label>Telefon</label>
          <input type="tel" name="telefon" placeholder="05XX XXX XX XX">
        </div>
      </div>

      <div class="filter-row">
        <div class="field">
          <label>Şantiye Yetkili</label>
          <input type="text" name="yetkili" placeholder="Yetkili adı">
        </div>
        <div class="field">
          <label>Araç *</label>
          <select name="arac" required>
            <option value="">Seçiniz...</option>
            {% for x in tanimlar.ARAC %}
            <option value="{{ x }}" {% if defaults.ARAC == x %}selected{% endif %}>{{ x }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <div class="filter-row">
        <div class="field">
          <label>Fabrika *</label>
          <select name="fabrika" required>
            <option value="">Seçiniz...</option>
            {% for x in tanimlar.FABRIKA %}
            <option value="{{ x }}" {% if defaults.FABRIKA == x %}selected{% endif %}>{{ x }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="field">
          <label>Nakliye *</label>
          <select name="nakliye" required>
            <option value="">Seçiniz...</option>
            {% for x in tanimlar.NAKLIYE %}
            <option value="{{ x }}" {% if defaults.NAKLIYE == x %}selected{% endif %}>{{ x }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <div class="filter-row">
        <div class="field">
          <label>Sipariş Veren *</label>
          <select name="siparis_veren" required>
            <option value="">Seçiniz...</option>
            {% for x in tanimlar.SIPARIS_VEREN %}
            <option value="{{ x }}" {% if (user.siparis_veren or defaults.SIPARIS_VEREN) == x %}selected{% endif %}>{{ x }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="field">
          <label>Firma Yetkili</label>
          <select name="firma_yetkili">
            <option value="">Seçiniz...</option>
            {% for x in tanimlar.FIRMA_YETKILI %}
            <option value="{{ x }}" {% if defaults.FIRMA_YETKILI == x %}selected{% endif %}>{{ x }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <div class="filter-row">
        <div class="field">
          <label>Sipariş Durumu</label>
          <select name="durum">
            {% for x in tanimlar.DURUM %}
            <option value="{{ x }}" {% if (defaults.DURUM or 'Beklemede') == x %}selected{% endif %}>{{ x }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="field">
          <label>Operasyon</label>
          <select name="operasyon">
            {% for x in tanimlar.OPERASYON %}
            <option value="{{ x }}" {% if (defaults.OPERASYON or 'İŞLENDİ') == x %}selected{% endif %}>{{ x }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <div class="field">
        <label>Notlar</label>
        <textarea name="notlar" placeholder="Teslimat veya sipariş notu..."></textarea>
      </div>

      <!-- Ürün Kalemleri -->
      <div class="kalem-ekle-box">
        <div style="font-size:11px; font-weight:800; color:#0f172a;">Ürün Kalemleri</div>
        <select id="inp-urun">
          <option value="">Ürün seçiniz...</option>
          {% for x in tanimlar.URUN %}
          <option value="{{ x }}" {% if defaults.URUN == x %}selected{% endif %}>{{ x }}</option>
          {% endfor %}
        </select>
        <div class="filter-row">
          <select id="inp-birim">
            {% for x in tanimlar.BIRIM %}
            <option value="{{ x }}" {% if defaults.BIRIM == x %}selected{% endif %}>{{ x }}</option>
            {% endfor %}
          </select>
          <input type="text" id="inp-miktar" inputmode="decimal" placeholder="Miktar / Tonaj">
        </div>
        <button type="button" class="btn btn-outline" style="height:31px;" onclick="addKalem()">+ Kalem Ekle</button>
        <div class="kalem-list" id="kalem-list"></div>
      </div>

      <input type="hidden" name="kalemler_json" id="kalemler_json" value="[]">
      <button type="submit" class="btn btn-success" style="height:38px; margin-top:4px;">✓ Siparişi Kaydet</button>
    </form>
  </div>
  {% endif %}
</div>

<script>
let kalemler = [];

function switchTab(tab) {
  const t1 = document.getElementById('tab-takip');
  const t2 = document.getElementById('tab-yeni');
  if (t1) t1.style.display = (tab === 'takip') ? 'block' : 'none';
  if (t2) t2.style.display = (tab === 'yeni') ? 'block' : 'none';
  document.querySelectorAll('.tab-btn').forEach((b, i) => {
    b.classList.toggle('active', (tab === 'takip' && i === 0) || (tab === 'yeni' && i === 1));
  });
}

function toggleCard(id) {
  const el = document.getElementById('card-' + id);
  if (el) el.classList.toggle('open');
}

function addKalem() {
  const u = document.getElementById('inp-urun').value.trim();
  const b = document.getElementById('inp-birim').value.trim();
  const m = document.getElementById('inp-miktar').value.trim();
  if (!u || !m) {
    alert('Lütfen ürün seçin ve miktar girin.');
    return;
  }
  kalemler.push({ urun: u, birim: b, miktar: m });
  document.getElementById('inp-miktar').value = '';
  renderKalemler();
}

function removeKalem(idx) {
  kalemler.splice(idx, 1);
  renderKalemler();
}

function renderKalemler() {
  const box = document.getElementById('kalem-list');
  box.innerHTML = '';
  kalemler.forEach((k, idx) => {
    const row = document.createElement('div');
    row.className = 'kalem-chip';
    row.innerHTML = `<span>${k.urun} — <b>${k.miktar} ${k.birim}</b></span>` +
                    `<button type="button" class="del-chip" onclick="removeKalem(${idx})">Sil</button>`;
    box.appendChild(row);
  });
  document.getElementById('kalemler_json').value = JSON.stringify(kalemler);
}

function prepareSubmit() {
  const u = document.getElementById('inp-urun').value.trim();
  const b = document.getElementById('inp-birim').value.trim();
  const m = document.getElementById('inp-miktar').value.trim();
  if (u && m) {
    kalemler.push({ urun: u, birim: b, miktar: m });
  }
  document.getElementById('kalemler_json').value = JSON.stringify(kalemler);
  return true;
}
</script>
{% endif %}
</body>
</html>
"""


def load_context(cur, user):
    op_colors = {
        "İŞLENDİ": "#0284c7",
        "ONAY BEKLİYOR": "#d97706",
        "ONAYLANDI": "#0d9488",
        "REVİZE İSTENDİ": "#ca8a04",
        "REDDEDİLDİ": "#b91c1c",
        "TAMAMLANDI": "#059669",
        "İPTAL EDİLDİ": "#dc2626",
        "KISMİ EVRAK": "#7c3aed"
    }

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

    q = request.args.get("q", "").strip()
    op = request.args.get("op", "").strip()
    firma_f = request.args.get("firma_f", "").strip()

    sql = "SELECT * FROM siparisler WHERE 1=1"
    params = []

    if user.get("kendi_siparisleri_gor") == 1 and user.get("siparis_veren"):
        sql += " AND siparis_veren = %s"
        params.append(user["siparis_veren"])

    if op == "":
        sql += " AND COALESCE(operasyon, '') NOT IN ('TAMAMLANDI', 'İPTAL EDİLDİ') AND UPPER(COALESCE(durum, '')) != 'İPTAL'"
    elif op != "TUMU":
        sql += " AND operasyon = %s"
        params.append(op)

    if firma_f:
        sql += " AND firma = %s"
        params.append(firma_f)

    if q:
        sql += " AND (CAST(siparis_no AS TEXT) ILIKE %s OR firma ILIKE %s OR musteri ILIKE %s OR santiye ILIKE %s OR fabrika ILIKE %s OR ted_sip_no ILIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like, like, like, like])

    sql += " ORDER BY siparis_no DESC LIMIT 80"
    cur.execute(sql, params)
    siparisler = [dict(r) for r in cur.fetchall()]

    if siparisler:
        nos = [s["siparis_no"] for s in siparisler]
        cur.execute(
            "SELECT siparis_no, urun, birim, miktar FROM siparis_kalemleri WHERE siparis_no = ANY(%s) ORDER BY id ASC",
            (nos,)
        )
        kalem_map = {}
        for k in cur.fetchall():
            kalem_map.setdefault(k["siparis_no"], []).append(dict(k))
        for s in siparisler:
            s["kalemler"] = kalem_map.get(s["siparis_no"], [])
            s["op_color"] = op_colors.get(str(s.get("operasyon") or "").upper(), "#475569")

    return tanimlar, defaults, kpi, siparisler, q, op, firma_f


@app.route("/", methods=["GET"])
def index():
    user = session.get("user")
    if not user:
        return render_template_string(HTML_TEMPLATE, user=None, error=None)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            tanimlar, defaults, kpi, siparisler, q, op, firma_f = load_context(cur, user)
    finally:
        conn.close()

    return render_template_string(
        HTML_TEMPLATE,
        user=user,
        tanimlar=tanimlar,
        defaults=defaults,
        kpi=kpi,
        siparisler=siparisler,
        q=q,
        op=op,
        firma_f=firma_f,
        active_tab=request.args.get("tab", "takip"),
        msg=request.args.get("msg"),
        error=request.args.get("error"),
        today=datetime.now().strftime("%Y-%m-%d")
    )


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, kullanici_adi, sifre, rol, kendi_siparisleri_gor, kullanici_siparis_veren "
                "FROM kullanicilar WHERE kullanici_adi=%s",
                (username,)
            )
            u = cur.fetchone()
    finally:
        conn.close()

    if u and verify_password(u["sifre"], password):
        session["user"] = {
            "id": u["id"],
            "username": u["kullanici_adi"],
            "role": u["rol"],
            "kendi_siparisleri_gor": u["kendi_siparisleri_gor"] or 0,
            "siparis_veren": u["kullanici_siparis_veren"] or ""
        }
        return redirect(url_for("index"))

    return render_template_string(HTML_TEMPLATE, user=None, error="Kullanıcı adı veya şifre hatalı!")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/siparis/ekle", methods=["POST"])
def create_order():
    user = session.get("user")
    if not user or user.get("role") == "OKUMA":
        return redirect(url_for("index", error="Yetkisiz işlem."))

    import json
    tarih = request.form.get("tarih") or datetime.now().strftime("%Y-%m-%d")
    sevk_tarihi = request.form.get("sevk_tarihi") or tarih
    firma = request.form.get("firma", "").strip()
    musteri = request.form.get("musteri", "").strip()
    santiye = request.form.get("santiye", "").strip()
    sehir = request.form.get("sehir", "").strip()
    telefon = request.form.get("telefon", "").strip()
    yetkili = request.form.get("yetkili", "").strip()
    arac = request.form.get("arac", "").strip()
    fabrika = request.form.get("fabrika", "").strip()
    nakliye = request.form.get("nakliye", "").strip()
    siparis_veren = request.form.get("siparis_veren", "").strip()
    firma_yetkili = request.form.get("firma_yetkili", "").strip()
    notlar = request.form.get("notlar", "").strip()
    durum = format_durum_text(request.form.get("durum", "Beklemede")) or "Beklemede"
    operasyon = request.form.get("operasyon", "İŞLENDİ").strip() or "İŞLENDİ"

    if operasyon.upper() == "TAMAMLANDI":
        durum = "SEVK EDİLDİ"
    elif operasyon.upper() == "İPTAL EDİLDİ" or durum == "İPTAL":
        operasyon = "İPTAL EDİLDİ"
        durum = "İPTAL"

    if not (firma and musteri and santiye and arac and fabrika and nakliye and siparis_veren):
        return redirect(url_for("index", tab="yeni", error="Lütfen zorunlu (*) alanları doldurun."))

    try:
        kalemler = json.loads(request.form.get("kalemler_json", "[]"))
    except Exception:
        kalemler = []

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            ensure_tanim(cur, "MÜŞTERİ", musteri)
            ensure_tanim(cur, "ŞANTİYE", santiye)
            if sehir:
                ensure_tanim(cur, "ŞEHİR", sehir)

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
                    tarih, firma, musteri, santiye, sehir, telefon, yetkili, arac, fabrika,
                    nakliye, notlar, sevk_tarihi, siparis_veren, firma_yetkili,
                    user["username"], durum, operasyon
                )
            )
            sip_no = cur.fetchone()["siparis_no"]

            for k in kalemler:
                u = str(k.get("urun", "")).strip()
                b = str(k.get("birim", "")).strip()
                m = str(k.get("miktar", "")).strip()
                if u and m:
                    cur.execute(
                        "INSERT INTO siparis_kalemleri (siparis_no, urun, birim, miktar) VALUES (%s,%s,%s,%s)",
                        (sip_no, u, b, m)
                    )
        conn.commit()
    finally:
        conn.close()

    send_ntfy_notification(sip_no, firma, musteri, operasyon)
    return redirect(url_for("index", tab="takip", msg=f"Sipariş #{sip_no} kaydedildi."))


@app.route("/siparis/guncelle/<int:siparis_no>", methods=["POST"])
def update_order(siparis_no):
    user = session.get("user")
    if not user or user.get("role") == "OKUMA":
        return redirect(url_for("index", error="Yetkisiz işlem."))

    operasyon = request.form.get("operasyon", "").strip()
    durum = format_durum_text(request.form.get("durum", ""))
    plaka = request.form.get("plaka", "").strip()
    ted_sip_no = request.form.get("ted_sip_no", "").strip()

    if operasyon.upper() == "TAMAMLANDI":
        durum = "SEVK EDİLDİ"
    elif operasyon.upper() == "İPTAL EDİLDİ" or durum == "İPTAL":
        operasyon = "İPTAL EDİLDİ"
        durum = "İPTAL"

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE siparisler SET operasyon=%s, durum=%s, plaka=%s, ted_sip_no=%s WHERE siparis_no=%s",
                (operasyon, durum, plaka, ted_sip_no, siparis_no)
            )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("index", tab="takip", msg=f"Sipariş #{siparis_no} güncellendi."))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
