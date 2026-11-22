import os
import json
import firebase_admin
from firebase_admin import credentials, db

DEFAULT_SERVICE_ACCOUNT_FILE = "firebase_service_account.json"
DEFAULT_DATABASE_URL = "https://sayar-yapi-takip-default-rtdb.europe-west1.firebasedatabase.app"


def _resolve_config(service_account_info=None, service_account_file=None, database_url=None):
    db_url = (database_url or os.environ.get("FIREBASE_DATABASE_URL") or "").strip()
    sa_dict = None
    sa_path = None

    if isinstance(service_account_info, dict) and service_account_info:
        sa_dict = dict(service_account_info)
        if not db_url:
            db_url = str(sa_dict.get("database_url") or sa_dict.get("DATABASE_URL") or "").strip()
    elif os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON"):
        try:
            sa_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
        except Exception:
            sa_dict = None

    if sa_dict is None:
        aday_yollar = []
        if service_account_file:
            aday_yollar.append(service_account_file)
        if os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE"):
            aday_yollar.append(os.environ["FIREBASE_SERVICE_ACCOUNT_FILE"])
        aday_yollar.append(DEFAULT_SERVICE_ACCOUNT_FILE)

        for yol in aday_yollar:
            if yol and os.path.exists(yol):
                sa_path = yol
                break

    if not db_url:
        db_url = DEFAULT_DATABASE_URL

    return sa_dict, sa_path, db_url.rstrip("/")


class FirebaseRealtimeStore:
    def __init__(self, service_account_info=None, service_account_file=None, database_url=None, app_name=None):
        sa_dict, sa_path, db_url = _resolve_config(
            service_account_info=service_account_info,
            service_account_file=service_account_file,
            database_url=database_url
        )
        if not db_url:
            raise ValueError("Firebase database_url tanımlanmamış.")

        if sa_dict is not None:
            cred = credentials.Certificate(sa_dict)
        elif sa_path:
            cred = credentials.Certificate(sa_path)
        else:
            raise FileNotFoundError(
                f"Firebase servis hesabı bulunamadı ({DEFAULT_SERVICE_ACCOUNT_FILE})."
            )

        self.database_url = db_url
        if app_name:
            try:
                self.app = firebase_admin.get_app(app_name)
            except ValueError:
                self.app = firebase_admin.initialize_app(cred, {"databaseURL": db_url}, name=app_name)
        else:
            if not firebase_admin._apps:
                self.app = firebase_admin.initialize_app(cred, {"databaseURL": db_url})
            else:
                self.app = firebase_admin.get_app()

    def _ref(self, path: str = "/"):
        temiz = path.strip("/")
        return db.reference("/" if not temiz else f"/{temiz}", app=self.app)

    # -------------------------
    # SİPARİŞ İŞLEMLERİ
    # -------------------------
    def tum_siparisleri_getir(self) -> list[dict]:
        ham = self._ref("siparisler").get()
        if not ham:
            return []

        kayitlar = []
        if isinstance(ham, dict):
            iter_items = ham.items()
        elif isinstance(ham, list):
            iter_items = [(str(i), v) for i, v in enumerate(ham) if v is not None]
        else:
            return []

        for key, val in iter_items:
            if not isinstance(val, dict):
                continue
            item = dict(val)
            try:
                sip_no = int(item.get("siparis_no") or key)
            except (TypeError, ValueError):
                continue
            item["siparis_no"] = sip_no
            kalemler = item.get("kalemler")
            item["kalemler"] = [dict(k) for k in kalemler if isinstance(k, dict)] if isinstance(kalemler, list) else []
            kayitlar.append(item)

        kayitlar.sort(key=lambda x: x["siparis_no"], reverse=True)
        return kayitlar

    def siparis_getir(self, siparis_no: int) -> dict | None:
        val = self._ref(f"siparisler/{int(siparis_no)}").get()
        if not isinstance(val, dict):
            return None
        item = dict(val)
        item["siparis_no"] = int(item.get("siparis_no") or siparis_no)
        kalemler = item.get("kalemler")
        item["kalemler"] = [dict(k) for k in kalemler if isinstance(k, dict)] if isinstance(kalemler, list) else []
        return item

    def sonraki_siparis_no_uret(self) -> int:
        def _arttir(guncel):
            mevcut_sayac = 0
            if isinstance(guncel, dict):
                mevcut_sayac = int(guncel.get("son_siparis_no") or 0)
            elif isinstance(guncel, (int, float)):
                mevcut_sayac = int(guncel)

            # Mevcut siparişlerde daha büyük numara varsa altına düşmemek için kontrol et
            sip_keys = self._ref("siparisler").get(shallow=True)
            max_sip = 0
            if isinstance(sip_keys, dict):
                for k in sip_keys.keys():
                    if str(k).isdigit():
                        max_sip = max(max_sip, int(k))

            yeni_no = max(mevcut_sayac, max_sip) + 1
            return {"son_siparis_no": yeni_no}

        sonuc = self._ref("sayac").transaction(_arttir)
        if isinstance(sonuc, dict) and "son_siparis_no" in sonuc:
            return int(sonuc["son_siparis_no"])
        raise RuntimeError("Yeni sipariş numarası üretilemedi.")

    def siparis_kaydet(self, siparis_dict: dict, siparis_no: int | None = None) -> int:
        veri = dict(siparis_dict)
        if siparis_no is not None:
            hedef_no = int(siparis_no)
        elif veri.get("siparis_no") is not None and str(veri.get("siparis_no")).isdigit():
            hedef_no = int(veri["siparis_no"])
        else:
            hedef_no = self.sonraki_siparis_no_uret()

        veri["siparis_no"] = hedef_no
        kalemler = veri.get("kalemler")
        if not isinstance(kalemler, list):
            kalemler = veri.get("urunler") if isinstance(veri.get("urunler"), list) else []
        veri["kalemler"] = [
            {
                "urun": str(k.get("urun") or "").strip(),
                "birim": str(k.get("birim") or "").strip(),
                "miktar": k.get("miktar") if k.get("miktar") is not None else ""
            }
            for k in kalemler
            if isinstance(k, dict) and str(k.get("urun") or "").strip()
        ]
        veri.pop("urunler", None)

        self._ref(f"siparisler/{hedef_no}").set(veri)
        return hedef_no

    def siparis_guncelle(self, siparis_no: int, guncel_alanlar: dict):
        self._ref(f"siparisler/{int(siparis_no)}").update(dict(guncel_alanlar))

    def siparis_sil(self, siparis_no: int):
        self._ref(f"siparisler/{int(siparis_no)}").delete()

    # -------------------------
    # TANIM İŞLEMLERİ
    # -------------------------
    def tum_tanimlari_getir(self) -> list[dict]:
        ham = self._ref("tanimlar").get()
        if not isinstance(ham, dict):
            return []

        sonuc = []
        for kat, kayitlar in ham.items():
            if not isinstance(kayitlar, dict):
                continue
            for rec_id, val in kayitlar.items():
                if not isinstance(val, dict):
                    continue
                item = dict(val)
                item["kategori"] = str(item.get("kategori") or kat).strip()
                item["id"] = str(item.get("id") or rec_id)
                item["deger"] = str(item.get("deger") or "").strip()
                item["firma"] = str(item.get("firma") or "").strip()
                item["aktif"] = int(item.get("aktif") if item.get("aktif") is not None else 1)
                item["is_default"] = int(item.get("is_default") or 0)
                if item["deger"]:
                    sonuc.append(item)
        return sonuc

    def tanim_ekle_veya_guncelle(self, kategori: str, deger: str, firma: str = "", aktif: int = 1, is_default: int = 0, rec_id: str | None = None) -> str:
        kat = str(kategori).strip()
        val = str(deger).strip()
        if not kat or not val:
            raise ValueError("Kategori ve değer boş olamaz.")

        if int(is_default) == 1:
            mevcut_kat = self._ref(f"tanimlar/{kat}").get()
            if isinstance(mevcut_kat, dict):
                for k_id in mevcut_kat.keys():
                    self._ref(f"tanimlar/{kat}/{k_id}").update({"is_default": 0})

        if rec_id:
            hedef_id = str(rec_id)
        else:
            mevcut_kat = self._ref(f"tanimlar/{kat}").get()
            hedef_id = None
            if isinstance(mevcut_kat, dict):
                for k_id, item in mevcut_kat.items():
                    if isinstance(item, dict) and str(item.get("deger") or "").strip().lower() == val.lower():
                        hedef_id = str(k_id)
                        break
            if not hedef_id:
                hedef_id = self._ref(f"tanimlar/{kat}").push().key

        payload = {
            "id": hedef_id,
            "kategori": kat,
            "deger": val,
            "firma": str(firma or "").strip(),
            "aktif": int(aktif),
            "is_default": int(is_default)
        }
        self._ref(f"tanimlar/{kat}/{hedef_id}").set(payload)
        return hedef_id

    def tanim_sil(self, kategori: str, rec_id: str):
        self._ref(f"tanimlar/{kategori}/{rec_id}").delete()

    # -------------------------
    # KULLANICI İŞLEMLERİ
    # -------------------------
    def tum_kullanicilari_getir(self) -> list[dict]:
        ham = self._ref("kullanicilar").get()
        if not ham:
            return []

        kullanicilar = []
        if isinstance(ham, dict):
            iter_items = ham.items()
        elif isinstance(ham, list):
            iter_items = [(str(i), v) for i, v in enumerate(ham) if v is not None]
        else:
            return []

        for k_id, val in iter_items:
            if not isinstance(val, dict):
                continue
            item = dict(val)
            item["id"] = str(item.get("id") or k_id)
            item["kullanici_adi"] = str(item.get("kullanici_adi") or "").strip()
            item["rol"] = str(item.get("rol") or "KULLANICI").strip()
            item["kendi_siparisleri_gor"] = int(item.get("kendi_siparisleri_gor") or 0)
            item["kullanici_siparis_veren"] = str(item.get("kullanici_siparis_veren") or "").strip()
            item["secili_sutunlar"] = str(item.get("secili_sutunlar") or "")
            item["gizli_operasyonlar"] = str(item.get("gizli_operasyonlar") or "")
            item["gizli_durumlar"] = str(item.get("gizli_durumlar") or "")
            if item["kullanici_adi"]:
                kullanicilar.append(item)

        kullanicilar.sort(key=lambda x: str(x["id"]))
        return kullanicilar

    def kullanici_kaydet(self, user_dict: dict, user_id: str | None = None) -> str:
        veri = dict(user_dict)
        hedef_id = str(user_id or veri.get("id") or "").strip()
        if not hedef_id:
            hedef_id = self._ref("kullanicilar").push().key
        veri["id"] = hedef_id
        self._ref(f"kullanicilar/{hedef_id}").set(veri)
        return hedef_id

    def kullanici_guncelle(self, user_id: str, guncel_alanlar: dict):
        self._ref(f"kullanicilar/{str(user_id)}").update(dict(guncel_alanlar))

    def kullanici_sil(self, user_id: str):
        self._ref(f"kullanicilar/{str(user_id)}").delete()