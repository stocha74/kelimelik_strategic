#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""
Kelimelik - Deterministik "2 hamle öngörü" (Monte Carlo) + DAWG/TRIE hızlandırma (uçtan uca)

Bu sürüm, orijinal dosyanın mantığını korur; hızlandırma sadece en pahalı noktaya uygulanır:
    ke.find_valid_words_from_available_with_orientations(eldeki_harfler, sozluk2)
Bu fonksiyon engine içinde her rack için sözlüğü tarayarak permütasyon deniyor ve MC simülasyonlarında çok pahalıya patlıyor.

ÇÖZÜM:
- Sözlükten bir TRIE (DAWG benzeri prefix-pruning) kuruyoruz.
- Rack'ten üretilebilen sözlük kelimelerini TRIE üzerinde üretiyoruz (tam sözlük taraması yok).
- Rack imzası (sorted) ile LRU cache yapıyoruz.

NOTLAR:
- "Gerçek DAWG" yerine TRIE kullandım. Rack->word üretimi için pratikte aynı hızlandırma mantığını verir.
- İstersen sonra marisa-trie / dawg-python'a geçiş kolay (API aynı tutuldu).
- Bu dosya "kelimelik_engine1.py" ile aynı klasörde olmalı (veya import path ayarlanmalı).

KULLANIM:
- En altta __main__ bloğunda örnek kullanım var.
- Sözlük yolu DICT_PATH üzerinden ayarlanır (varsayılan: turkce_kelime_listesi.txt).
"""

import copy
import random
from collections import Counter
from functools import lru_cache
from typing import Dict, List, Tuple, Optional

import numpy as np
import kelimelik_engine1 as ke


# In[2]:


with open(r"C:\Users\Cenk Toker\OneDrive\Desktop\python codes\rl_kelimelik\turkce_kelime_listesi.txt", "r", encoding="utf-8") as f:
    sozluk1 = f.read().splitlines()
sozluk = [a.replace("i","İ").replace("ı","I").replace("ğ","Ğ")
            .replace("ş","Ş").replace("ö","Ö").replace("ü","Ü")
            .replace("ç","Ç").upper() for a in sozluk1]


# In[3]:


# ============================================================
# 0) TRIE tabanlı rack -> word üretici (DAWG benzeri)
# ============================================================

_END = "\0"

class RackTrie:
    def __init__(self, words: List[str]):
        self.root: Dict[str, dict] = {}
        self._build(words)

    def _build(self, words: List[str]) -> None:
        root = self.root
        for w in words:
            if not w:
                continue
            node = root
            for ch in w:
                node = node.setdefault(ch, {})
            node[_END] = True

    @staticmethod
    def _sig(rack: str) -> str:
        # multiset signature
        return "".join(sorted(rack))

    @lru_cache(maxsize=200_000)
    def _words_from_sig(self, sig: str, min_len: int, max_len: int) -> Tuple[str, ...]:
        cnt = Counter(sig)
        out: List[str] = []
        self._dfs(self.root, cnt, [], out, min_len, max_len)
        return tuple(out)

    def words_from_rack(self, rack: str, min_len: int = 2, max_len: int = 11) -> List[str]:
        rack = (rack or "").strip().upper()
        if not rack:
            return []
        sig = self._sig(rack)
        return list(self._words_from_sig(sig, min_len, max_len))

    def words_from_rack_with_orientations(self, rack: str, min_len: int = 2, max_len: int = 11):
        """
        kelimelik_engine1.aday_kelime_yerlestir2'ye verilecek format:
            [(KELIME, "horizontal"), (KELIME, "vertical"), ...]
        (engine'deki find_valid_words_from_available_with_orientations çıktısıyla uyumlu)
        """
        words = self.words_from_rack(rack, min_len=min_len, max_len=max_len)
        out = []
        for w in words:
            out.append((w, "horizontal"))
            out.append((w, "vertical"))
        return out

    def _dfs(self, node: dict, cnt: Counter, path: List[str], out: List[str],
             min_len: int, max_len: int) -> None:
        if _END in node and min_len <= len(path) <= max_len:
            out.append("".join(path))
        if len(path) >= max_len:
            return

        # iterate remaining letters
        for ch in list(cnt.keys()):
            if cnt[ch] <= 0:
                continue
            nxt = node.get(ch)
            if nxt is None:
                continue
            cnt[ch] -= 1
            path.append(ch)
            self._dfs(nxt, cnt, path, out, min_len, max_len)
            path.pop()
            cnt[ch] += 1


def build_trie_from_dictionary(sozluk2: List[str]) -> RackTrie:
    words = [w.strip().upper() for w in sozluk2 if isinstance(w, str) and w.strip()]
    return RackTrie(words)


# In[4]:


# ============================================================
# 1) SÖZLÜK yardımcıları (orijinaldeki gibi)
# ============================================================

def trim_dictionary(words: List[str], stock: Dict[str, int]) -> List[str]:
    filtered = []
    for kelime in words:
        cnt = Counter(kelime)
        uygun = True
        for harf, adet in cnt.items():
            if harf not in stock:
                uygun = False
                break
            # +1 joker payı (orijinal mantık)
            if adet > stock[harf] + 1:
                uygun = False
                break
        if uygun:
            filtered.append(kelime)
    return filtered

def remove_long_words(words: List[str], limit: int = 11) -> List[str]:
    return [w for w in words if len(w.strip()) <= limit]



# In[5]:


harf_stogu = {
    'A': 12, 'B': 2, 'C': 2, 'Ç': 2, 'D': 2, 'E': 8, 'F': 1, 'G': 1, 'Ğ': 1,
    'H': 1, 'I': 4, 'İ': 7, 'J': 1, 'K': 7, 'L': 7, 'M': 4, 'N': 5, 'O': 3,
    'Ö': 1, 'P': 1, 'R': 6, 'S': 3, 'Ş': 2, 'T': 5, 'U': 3, 'Ü': 2, 'V': 1,
    'Y': 2, 'Z': 2
}


# In[6]:


sozluk2=trim_dictionary(sozluk, harf_stogu)
sozluk2 = remove_long_words(sozluk2, limit=11)


# In[7]:


# ============================================================
# 2) STOKTAN RASTGELE RAF ÇEKME
# ============================================================

def stok_to_list(harf_stogu: Dict[str, int]) -> List[str]:
    pool = []
    for harf, adet in harf_stogu.items():
        pool.extend([harf] * int(adet))
    return pool

def rastgele_raf_cek(harf_stogu: Dict[str, int], raf_boyutu: int = 7, rng=None) -> List[str]:
    if rng is None:
        rng = random
    pool = stok_to_list(harf_stogu)
    if len(pool) == 0:
        return []
    if len(pool) < raf_boyutu:
        raf_boyutu = len(pool)
    return rng.sample(pool, raf_boyutu)

# --- Bag (kalan stok) ile doğru çekiliş: çekilen harfler bag'den düşer ---
def stock_to_bag_list(harf_stogu: Dict[str, int], include_joker: bool = False) -> List[str]:
    bag: List[str] = []
    for harf, adet in harf_stogu.items():
        if (not include_joker) and harf == "JOKER":
            continue
        bag.extend([harf] * int(adet))
    return bag

def draw_from_bag(bag: List[str], k: int = 7, rng=None) -> Tuple[List[str], List[str]]:
    """Bag'den k harf çeker ve bag'den düşerek yeni bag döner (without replacement)."""
    if rng is None:
        rng = random
    if not bag:
        return [], bag
    k = min(k, len(bag))
    idxs = rng.sample(range(len(bag)), k)
    idxs.sort(reverse=True)
    bag2 = bag[:]  # simülasyon bağımsızlığı için kopya
    drawn: List[str] = []
    for i in idxs:
        drawn.append(bag2.pop(i))
    return drawn, bag2


# In[8]:


# ============================================================
# 3) ANA_DİZİN HESAPLAMA (TRIE ile hızlandırılmış)
# ============================================================

def hesapla_ana_dizin(
    board: np.ndarray,
    tahta_puanlari2: np.ndarray,
    sozluk2: List[str],
    eldeki_harfler: str,
    dawg: Optional[RackTrie] = None,
    top_k: int = 30,            # <-- EKLENDİ
    max_checked: int = None      # <-- EKLENDİ
):
    """
    Orijinal hesapla_ana_dizin ile aynı amaç:
    Tahtaya yerleşebilecek geçerli hamleleri ve skorlarını çıkarır.

    Hızlandırma:
    - dawg verilirse: rack -> valid word list üretimi TRIE üzerinden yapılır.
    - dawg yoksa: engine'deki orijinal (yavaş) fonksiyon çağrılır.
    """
    cikarilan = ke.extract_words(board)

    filtered_list_coklu = [item for item in cikarilan if len(item[0]) >= 2]
    filtered_list_tekli = [item for item in cikarilan if len(item[0]) == 1]

    coklu_kelimecik = [a[0] for a in filtered_list_coklu]
    tekli_kelimecik = [a[0] for a in filtered_list_tekli]

    filtreli_sozluk2 = ke.filter_scrabble_dictionary(sozluk2, coklu_kelimecik).tolist()
    filtreli_sozluk1 = ke.filter_scrabble_dictionary(sozluk2, tekli_kelimecik).tolist()

    mumkun_kelimeler = ke.find_possible_words_and_orientations4(eldeki_harfler, filtered_list_coklu, filtreli_sozluk2)
    mumkun_kelimeler += ke.find_possible_words_and_orientations4(eldeki_harfler, filtered_list_tekli, filtreli_sozluk1)

    # --- KRİTİK HIZLANDIRMA NOKTASI ---
    if dawg is None:
        eldeki_list_kelimeler = ke.find_valid_words_from_available_with_orientations(eldeki_harfler, sozluk2)
    else:
        eldeki_list_kelimeler = dawg.words_from_rack_with_orientations(eldeki_harfler, min_len=2, max_len=11)

    mumkun_kelimeler += ke.aday_kelime_yerlestir2(board, eldeki_list_kelimeler)
    # === ERKEN KESME (KRİTİK) ===
    #if max_checked is not None and max_checked > 0:
     #   if len(mumkun_kelimeler) > max_checked:
      #      mumkun_kelimeler = mumkun_kelimeler[:max_checked]


    # Skorlar
    kelime_gecerli = []
    xkoord_gecerli = []
    ykoord_gecerli = []
    orient_gecerli = []
    puan_gecerli = []
    dezavantaj_gecerli = []
    harf_basina_gecerli = []
    dezavantaj_basina_puan_gecerli = []

    yeni_tahta_puanlari = tahta_puanlari2.copy()
    yeni_tahta_puanlari[board != ''] = 0
    board_temp = copy.deepcopy(board)

    for a in range(len(mumkun_kelimeler)):
        kelime = mumkun_kelimeler[a][0]
        x_koord = mumkun_kelimeler[a][1][0]
        y_koord = mumkun_kelimeler[a][1][1]
        orient = mumkun_kelimeler[a][2][0]

        cikti = ke.kelime_yerlestir_ve_puanla5(
            kelime.upper(),
            x_koord,
            y_koord,
            orient,
            board_temp,
            yeni_tahta_puanlari,
            sozluk2
        )

        if not isinstance(cikti, dict):
            board_temp = copy.deepcopy(board)
            continue

        if cikti.get("gecerli", False):
            harf_basina = float(cikti["puan"]) / len(kelime)
            harf_basina_gecerli.append(round(harf_basina, 2))
            puan_gecerli.append(cikti["puan"])
            kelime_gecerli.append(kelime)
            xkoord_gecerli.append(x_koord)
            ykoord_gecerli.append(y_koord)
            orient_gecerli.append(orient)
            dezavantaj_gecerli.append(cikti["dezavantaj"])
            dezavantaj_basina_puan_gecerli.append(round(cikti["dezavantaj"] / max(1, cikti["puan"]), 2))

        board_temp = copy.deepcopy(board)

    ana_dizin = list(zip(
        kelime_gecerli,
        xkoord_gecerli,
        ykoord_gecerli,
        orient_gecerli,
        puan_gecerli,
        harf_basina_gecerli,
        dezavantaj_gecerli,
        dezavantaj_basina_puan_gecerli
    ))

    ana_dizin = sorted(ana_dizin, reverse=True, key=lambda tup: (tup[4], tup[5]))
    return ana_dizin


# 
# # ============================================================
# # 4) MONTE CARLO İLE EN İYİ HAMLEYİ SEÇME (TRIE destekli)
# # ============================================================
# 
# def monte_carlo_en_iyi_hamle(
#     board: np.ndarray,
#     tahta_puanlari2: np.ndarray,
#     sozluk2: List[str],
#     bizim_eldeki_harfler: str,
#     harf_stogu: Dict[str, int],
#     dawg: Optional[RackTrie] = None,
#     bag_letters_current: Optional[List[str]] = None,
#     max_aday_sayisi: int = 1,
#     rakip_simulasyon_sayisi: int = 7,
#     raf_boyutu: int = 7,
#     rng=None
# ):
#     """
#     1) Bizim için ana_dizin hesaplanır.
#     2) İlk max_aday_sayisi kelime aday alınır.
#     3) Her aday için rakip_simulasyon_sayisi kez:
#        - harf_stogu'ndan 7 harf çekilir
#        - bu elde + aday board ile rakibin ana_dizin'i hesaplanır
#        - rakibin en iyi hamle puanı alınır
#     4) Bizim puan - ortalama rakip puanı farkı en yüksek olan aday seçilir.
#     """
#     if rng is None:
#         rng = random
# 
#     ana_dizin = hesapla_ana_dizin(board, tahta_puanlari2, sozluk2, bizim_eldeki_harfler, dawg=dawg)
#     if not ana_dizin:
#         print("Hiç geçerli hamle yok.")
#         return None, []
# 
#     adaylar = ana_dizin[:max_aday_sayisi]
#     tum_skorlar = []
#     en_iyi_hamle = None
# 
#     for aday in adaylar:
#         kelime, x_koord, y_koord, orient, bizim_puan, _, _, _ = aday
# 
#         # Aday kelimeyi gerçek board üzerinde uygula -> aday board
#         board_temp = copy.deepcopy(board)
#         yeni_tahta_puanlari = tahta_puanlari2.copy()
#         yeni_tahta_puanlari[board_temp != ''] = 0
# 
#         sonuc_biz = ke.kelime_yerlestir_ve_puanla5(
#             kelime.upper(),
#             x_koord,
#             y_koord,
#             orient,
#             board_temp,
#             yeni_tahta_puanlari,
#             sozluk2
#         )
# 
#         if not isinstance(sonuc_biz, dict) or not sonuc_biz.get("gecerli", False):
#             continue
# 
#         bizim_puan = sonuc_biz["puan"]
#         aday_board = sonuc_biz["board"]  # rakip bu board üzerinde oynayacak
# 
#         rakip_puanlar = []
# 
#         # Simülasyon başlangıcındaki "kalan stok" (bag). Eğer dışarıdan verilmezse harf_stogu'ndan türetilir.
#         base_bag = bag_letters_current if bag_letters_current is not None else stock_to_bag_list(harf_stogu)
# 
#         for _ in range(rakip_simulasyon_sayisi):
#             # Her simülasyonu aynı başlangıç bag'i ile başlat (bağımsız örneklem)
#             rakip_raf_list, bag_sim = draw_from_bag(base_bag[:], k=raf_boyutu, rng=rng)
#             if not rakip_raf_list:
#                 rakip_puanlar.append(0)
#                 continue
# 
#             rakip_eldeki_harfler = "".join(rakip_raf_list)
#     '''
#             ana_dizin_rakip = hesapla_ana_dizin(aday_board, tahta_puanlari2, sozluk2, rakip_eldeki_harfler, dawg=dawg)
#             if not ana_dizin_rakip:
#                 rakip_puanlar.append(0)
#             else:
#                 rakip_puanlar.append(ana_dizin_rakip[0][4])  # en iyi rakip puanı
#     '''
# 
#         # Rakip için TEK hamle hesapla: full ana_dizin çıkarma yok
#         board_sim = copy.deepcopy(aday_board)
#         bonus_sim = tahta_puanlari2.copy()
#         bonus_sim[board_sim != ""] = 0  # engine mantığına uyum
#         
#         board_after, eksilen_r, puan_r, _ana = ke.hamle_cok_kriterli(
#             board_sim, bonus_sim, rakip_eldeki_harfler, sozluk2,
#             w_puan=1.0, w_harf=0.0, w_dez=0.0, w_oran=0.0
#         )
#         rakip_puanlar.append(float(puan_r) if puan_r else 0.0)
# 
#         rakip_ortalama = (sum(rakip_puanlar) / len(rakip_puanlar)) if rakip_puanlar else 0.0
#         fark = bizim_puan - rakip_ortalama
# 
#         sonuc_kayit = {
#             "kelime": kelime,
#             "x": x_koord,
#             "y": y_koord,
#             "orient": orient,
#             "bizim_puan": bizim_puan,
#             "rakip_ortalama_puan": rakip_ortalama,
#             "fark": fark
#         }
#         tum_skorlar.append(sonuc_kayit)
# 
#         if (en_iyi_hamle is None) or (fark > en_iyi_hamle["fark"]):
#             en_iyi_hamle = sonuc_kayit
#     return en_iyi_hamle, tum_skorlar

# In[9]:


# ============================================================
# 4) MONTE CARLO İLE EN İYİ HAMLEYİ SEÇME (TRIE destekli)
# ============================================================

def monte_carlo_en_iyi_hamle(
    board: np.ndarray,
    tahta_puanlari2: np.ndarray,
    sozluk2: List[str],
    bizim_eldeki_harfler: str,
    harf_stogu: Dict[str, int],
    dawg: Optional["RackTrie"] = None,
    bag_letters_current: Optional[List[str]] = None,
    max_aday_sayisi: int = 1,
    rakip_simulasyon_sayisi: int = 7,
    raf_boyutu: int = 7,
    rng=None
):
    """
    1) Bizim için ana_dizin hesaplanır.
    2) İlk max_aday_sayisi kelime aday alınır.
    3) Her aday için rakip_simulasyon_sayisi kez:
       - bag'den 7 harf çekilir
       - rakip TEK hamle oynar (hamle_cok_kriterli)
       - rakip hamle puanı kaydedilir
    4) Bizim puan - ortalama rakip puanı farkı en yüksek olan aday seçilir.
    """
    if rng is None:
        rng = random

    ana_dizin = hesapla_ana_dizin(
        board, tahta_puanlari2, sozluk2, bizim_eldeki_harfler, dawg=dawg
    )
    if not ana_dizin:
        print("Hiç geçerli hamle yok.")
        return None, []

    adaylar = ana_dizin[:max_aday_sayisi]
    tum_skorlar = []
    en_iyi_hamle = None

    for aday in adaylar:
        kelime, x_koord, y_koord, orient, bizim_puan, _, _, _ = aday

        # Aday kelimeyi gerçek board üzerinde uygula -> aday_board
        board_temp = copy.deepcopy(board)
        yeni_tahta_puanlari = tahta_puanlari2.copy()
        yeni_tahta_puanlari[board_temp != ""] = 0

        sonuc_biz = ke.kelime_yerlestir_ve_puanla5(
            kelime.upper(),
            x_koord,
            y_koord,
            orient,
            board_temp,
            yeni_tahta_puanlari,
            sozluk2
        )

        if (not isinstance(sonuc_biz, dict)) or (not sonuc_biz.get("gecerli", False)):
            continue

        bizim_puan = float(sonuc_biz["puan"])
        aday_board = sonuc_biz["board"]  # rakip bu board üzerinde oynayacak

        rakip_puanlar = []

        # Bu aday için simülasyon başlangıç bag'i
        base_bag = (
            bag_letters_current
            if bag_letters_current is not None
            else stock_to_bag_list(harf_stogu)
        )

        for _ in range(rakip_simulasyon_sayisi):
            # Bağımsız örneklem: her seferinde aynı başlangıç bag'inin kopyası
            rakip_raf_list, _bag_sim = draw_from_bag(base_bag[:], k=raf_boyutu, rng=rng)
            if not rakip_raf_list:
                rakip_puanlar.append(0.0)
                continue

            rakip_eldeki_harfler = "".join(rakip_raf_list)

            # Rakip için TEK hamle hesapla (full ana_dizin çıkarma yok)
            board_sim = copy.deepcopy(aday_board)
            bonus_sim = tahta_puanlari2.copy()
            bonus_sim[board_sim != ""] = 0  # engine mantığına uyum

            board_after, eksilen_r, puan_r, _ana = ke.hamle_cok_kriterli(
                board_sim,
                bonus_sim,
                rakip_eldeki_harfler,
                sozluk2,
                w_puan=1.0,
                w_harf=0.0,
                w_dez=0.0,
                w_oran=0.0
            )

            rakip_puanlar.append(float(puan_r) if puan_r else 0.0)

        rakip_ortalama = (sum(rakip_puanlar) / len(rakip_puanlar)) if rakip_puanlar else 0.0
        fark = bizim_puan - rakip_ortalama

        sonuc_kayit = {
            "kelime": kelime,
            "x": x_koord,
            "y": y_koord,
            "orient": orient,
            "bizim_puan": bizim_puan,
            "rakip_ortalama_puan": rakip_ortalama,
            "fark": fark
        }
        tum_skorlar.append(sonuc_kayit)

        if (en_iyi_hamle is None) or (fark > en_iyi_hamle["fark"]):
            en_iyi_hamle = sonuc_kayit

    return en_iyi_hamle, tum_skorlar


# In[10]:


# ============================================================
# 4) MONTE CARLO İLE EN İYİ HAMLEYİ SEÇME (TRIE destekli) - HIZLANDIRILMIŞ
#    - Rakip simülasyonunda full ana_dizin yerine tek hamle: ke.hamle_cok_kriterli
#    - (aday_board, rack_sig) bazlı cache
# ============================================================

def monte_carlo_en_iyi_hamle(
    board: np.ndarray,
    tahta_puanlari2: np.ndarray,
    sozluk2: List[str],
    bizim_eldeki_harfler: str,
    harf_stogu: Dict[str, int],
    dawg: Optional[RackTrie] = None,
    bag_letters_current: Optional[List[str]] = None,
    max_aday_sayisi: int = 1,
    rakip_simulasyon_sayisi: int = 7,
    raf_boyutu: int = 7,
    rng=None,
    # İstersen şimdiden aç:
    # top_k: int = 30,
    # max_checked: int = 400
):
    """
    1) Bizim için ana_dizin hesaplanır.
    2) İlk max_aday_sayisi aday alınır.
    3) Her aday için rakip_simulasyon_sayisi kez:
       - bag'den rakibe 7 harf çekilir (without replacement simülasyonu için base_bag[:])
       - rakip bu elde, aday_board üzerinde 1 hamle yapar (hamle_cok_kriterli)
       - rakip puanı cache'lenir
    4) Bizim puan - ortalama rakip puanı farkı en yüksek olan aday seçilir.
    """
    if rng is None:
        rng = random

    # ------------------------------
    # RAKİP SİMÜLASYON CACHE
    # ------------------------------
    sim_cache: Dict[Tuple[str, str], float] = {}  # (board_key, rack_sig) -> rakip_puan

    def board_key(b: np.ndarray) -> str:
        # 15x15 board'u tek string'e çevir (hash için yeterli)
        # boş hücre: "."
        return "".join((cell if cell else ".") for row in b for cell in row)

    def rack_sig(rack_str: str) -> str:
        # rack multiset imzası
        return "".join(sorted(rack_str))

    # ------------------------------
    # BİZİM ADAYLARI HESAPLA
    # ------------------------------
    ana_dizin = hesapla_ana_dizin(
        board=board,
        tahta_puanlari2=tahta_puanlari2,
        sozluk2=sozluk2,
        eldeki_harfler=bizim_eldeki_harfler,
        dawg=dawg,
        # İstersen aç:
        # top_k=top_k,
        # max_checked=max_checked
    )

    if not ana_dizin:
        # print("Hiç geçerli hamle yok.")
        return None, []

    adaylar = ana_dizin[:max_aday_sayisi]
    tum_skorlar = []
    en_iyi_hamle = None

    # Simülasyon başlangıcındaki "kalan stok" (bag). Dışarıdan verilmezse harf_stogu'ndan türetilir.
    base_bag = bag_letters_current if bag_letters_current is not None else stock_to_bag_list(harf_stogu)

    for aday in adaylar:
        kelime, x_koord, y_koord, orient, _bizim_puan, _, _, _ = aday

        # --- Bizim adayı gerçek board üzerinde uygula -> aday_board ---
        board_temp = copy.deepcopy(board)
        yeni_tahta_puanlari = tahta_puanlari2.copy()
        yeni_tahta_puanlari[board_temp != ""] = 0

        sonuc_biz = ke.kelime_yerlestir_ve_puanla5(
            kelime.upper(),
            x_koord,
            y_koord,
            orient,
            board_temp,
            yeni_tahta_puanlari,
            sozluk2
        )

        if (not isinstance(sonuc_biz, dict)) or (not sonuc_biz.get("gecerli", False)):
            continue

        bizim_puan = float(sonuc_biz["puan"])
        aday_board = sonuc_biz["board"]  # rakip bu board üzerinde oynayacak

        # --- Rakip simülasyonları ---
        rakip_puanlar: List[float] = []
        aday_board_key = board_key(aday_board)  # board_key'i aday başına bir kez çıkar

        for _ in range(rakip_simulasyon_sayisi):
            rakip_raf_list, _bag_sim = draw_from_bag(base_bag[:], k=raf_boyutu, rng=rng)
            if not rakip_raf_list:
                rakip_puanlar.append(0.0)
                continue

            rakip_eldeki_harfler = "".join(rakip_raf_list)
            key = (aday_board_key, rack_sig(rakip_eldeki_harfler))

            # --- CACHE HIT ---
            if key in sim_cache:
                rakip_puanlar.append(sim_cache[key])
                continue

            # --- CACHE MISS: rakip için TEK hamle hesapla ---
            board_sim = copy.deepcopy(aday_board)
            bonus_sim = tahta_puanlari2.copy()
            bonus_sim[board_sim != ""] = 0

            # Not: hamle_cok_kriterli imzası engine’inde farklıysa bu satırı uyarlaman gerekir.
            _board_after, _eksilen_r, puan_r, _ana = ke.hamle_cok_kriterli(
                board_sim,
                bonus_sim,
                rakip_eldeki_harfler,
                sozluk2,
                w_puan=1.0,
                w_harf=0.0,
                w_dez=0.0,
                w_oran=0.0
            )

            rakip_puan = float(puan_r) if puan_r else 0.0
            rakip_puanlar.append(rakip_puan)
            sim_cache[key] = rakip_puan  # --- CACHE WRITE ---

        rakip_ortalama = (sum(rakip_puanlar) / len(rakip_puanlar)) if rakip_puanlar else 0.0
        fark = bizim_puan - rakip_ortalama

        sonuc_kayit = {
            "kelime": kelime,
            "x": x_koord,
            "y": y_koord,
            "orient": orient,
            "bizim_puan": bizim_puan,
            "rakip_ortalama_puan": rakip_ortalama,
            "fark": fark,
        }
        tum_skorlar.append(sonuc_kayit)

        if (en_iyi_hamle is None) or (fark > en_iyi_hamle["fark"]):
            en_iyi_hamle = sonuc_kayit

    return en_iyi_hamle, tum_skorlar


# In[11]:


board = np.array([["" for _ in range(15)] for _ in range(15)], dtype=object)
#board[7][7:12] = list("ALTAY")  # opsiyonel demo
board=np.array(
        [['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '']],
       )


# In[12]:


tahta_puanlari2 = np.array([
    [0 , 0 , 6 , 0 , 0 , 2 , 0 , 0 , 0 , 2 , 0 , 0 , 6 , 0 , 0 ],
    [0 , 3 , 0 , 0 , 0 , 0 , 2 , 0 , 2 , 0 , 0 , 0 , 0 , 3 , 0 ], 
    [6 , 0 , 0 , 0 , 0 , 0 , 0 , 4 , 0 , 0 , 0 , 0 , 0 , 0 , 6 ], 
    [0 , 0 , 0 , 4 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 4 , 0 , 0 , 0 ],
    [25, 0 , 0 , 0 , 3 , 0 , 0 , 0 , 0 , 0 , 3 , 0 , 0 , 0 , 0 ],
    [2 , 0 , 0 , 0 , 0 , 2 , 0 , 0 , 0 , 2 , 0 , 0 , 0 , 0 , 2],
    [0 , 2 , 0 , 0 , 0 , 0 , 2 , 0 , 2 , 0 , 0 , 0 , 0 , 2 , 0], 
    [0 , 0 , 4 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 4 , 0 , 0],
    [0 , 2 , 0 , 0 , 0 , 0 , 2 , 0 , 2 , 0 , 0 , 0 , 0 , 2 , 0],
    [2 , 0 , 0 , 0 , 0 , 2 , 0 , 0 , 0 , 2 , 0 , 0 , 0 , 0 , 2],
    [0 , 0 , 0 , 0 , 3 , 0 , 0 , 0 , 0 , 0 , 3 , 0 , 0 , 0 , 0 ],
    [0 , 0 , 0 , 4 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 4 , 0 , 0 , 0 ],
    [6 , 0 , 0 , 0 , 0 , 0 , 0 , 4 , 0 , 0 , 0 , 0 , 0 , 0 , 6 ],
    [0 , 3 , 0 , 0 , 0 , 0 , 2 , 0 , 2 , 0 , 0 , 0 , 0 , 3 , 0 ], 
    [0 , 0 , 6 , 0 , 0 , 2 , 0 , 0 , 0 , 2 , 0 , 0 , 6 , 0 , 0 ]
], dtype=int)


# In[53]:


board=np.array(
        [['', '', '', '', '', '', '', '', '', '', '', '', 'K', 'İ', 'Ş'],
        ['', '', '', '', '', '', '', '', '', 'K', 'A', 'R', 'A', 'F', 'A'],
        ['', '', '', '', '', '', '', '', '', '', 'R', 'E', 'V', 'A', 'N'],
        ['', '', '', '', '', '', '', '', '', '', 'I', '', 'G', '', ''],
        ['', '', '', '', 'J', 'E', 'L', '', '', '', 'Z', '', 'A', 'B', 'A'],
        ['', '', '', '', '', 'D', 'E', '', '', 'S', 'A', 'L', '', 'A', 'B'],
        ['', '', '', '', 'Ç', 'İ', 'Ğ', '', '', '', '', '', '', 'T', 'E'],
        ['', '', '', '', '', 'K', 'E', 'Ş', '', '', '', '', 'T', 'U', ''],
        ['', '', '', '', '', '', 'N', 'O', 'M', '', '', 'S', 'Ö', 'R', ''],
        ['', '', '', '', '', '', '', 'M', 'A', 'R', 'K', 'İ', 'Z', '', ''],
        ['', '', '', '', '', '', '', '', '', '', 'O', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '', 'L', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', 'K', 'İ', 'N', 'D', 'A', 'R'],
        ['', '', '', '', '', '', '', '', '', '', '', '', 'İ', '', ''],
        ['', '', '', '', '', '', '', '', '', '', '', '', 'L', '', '']],
       )


# In[54]:


# ============================================================
# 5) ÖRNEK KULLANIM
# ============================================================

if __name__ == "__main__":
    # ---- Sözlük yükle ----
    # Orijinal kodda Windows path vardı; bunu parametrik yapıyoruz.
    #DICT_PATH = "C:\Users\Cen"
    
    # ---- TRIE/DAWG kur (SADECE 1 kere) ----
    dawg = build_trie_from_dictionary(sozluk2)

    # ---- Board örneği ----
    #board = np.array([["" for _ in range(15)] for _ in range(15)], dtype=object)
    #board[7][7:12] = list("ALTAY")  # opsiyonel demo

    # ---- Tahta puanları (senin matrisini ver) ----
    # Burada 1'lerle doldurduk; gerçek bonus matrisi sende var.
    #tahta_puanlari2 = np.ones((15, 15), dtype=int)

    # ---- Input ----
    eldeki_harfler = input("Elinizdeki Harfler: ").strip().upper()

    # Kalan stok (bag) - rakip çekilişleri bunu baz alacak
    bag_current = stock_to_bag_list(harf_stogu)


    en_iyi_hamle, tum_skorlar = monte_carlo_en_iyi_hamle(
        board=board,
        tahta_puanlari2=tahta_puanlari2,
        sozluk2=sozluk2,
        bizim_eldeki_harfler=eldeki_harfler,
        harf_stogu=harf_stogu,
        dawg=dawg,                  # <-- HIZLANDIRMA AKTİF
        max_aday_sayisi=5,
        rakip_simulasyon_sayisi=5,
        raf_boyutu=7
    )

    print("\nMonte Carlo sonuçları (kısa özet):")
    for s in tum_skorlar:
        print(s)

    if en_iyi_hamle is not None:
        print("\nSEÇİLEN EN İYİ HAMLE:")
        print(en_iyi_hamle)

        board_temp = copy.deepcopy(board)
        yeni_tahta_puanlari = tahta_puanlari2.copy()
        yeni_tahta_puanlari[board_temp != ''] = 0

        final_sonuc = ke.kelime_yerlestir_ve_puanla5(
            en_iyi_hamle["kelime"].upper(),
            en_iyi_hamle["x"],
            en_iyi_hamle["y"],
            en_iyi_hamle["orient"],
            board_temp,
            yeni_tahta_puanlari,
            sozluk2
        )

        print("\nBizim hamle puanı:", final_sonuc["puan"])
        print("\nYeni tahta:")
        ke.print_board(final_sonuc["board"])

        puanveboard = tahta_puanlari2.astype(object)
        puanveboard[final_sonuc["board"] != ''] = final_sonuc["board"][final_sonuc["board"] != '']
        print("\nPuan/Board birleşik gösterim:")
        ke.print_board(puanveboard)
    else:
        print("Geçerli hamle bulunamadı.")


# In[ ]:




