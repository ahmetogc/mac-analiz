# Her gece GitHub'da çalışır: football-data.co.uk'dan sonuçları ve
# yaklaşan maçları indirir, uygulamanın okuduğu data.json dosyasını yazar.
import csv, io, json, os, time, datetime, urllib.request, urllib.error

# Uygulamada görünecek ligler. Lig eklemek/çıkarmak için bu listeyi düzenle.
LIGLER = {
    "T1": "Türkiye Süper Lig",
    "E0": "İngiltere Premier League",
    "E1": "İngiltere Championship",
    "SP1": "İspanya La Liga",
    "SP2": "İspanya La Liga 2",
    "I1": "İtalya Serie A",
    "I2": "İtalya Serie B",
    "D1": "Almanya Bundesliga",
    "D2": "Almanya 2. Bundesliga",
    "F1": "Fransa Ligue 1",
    "F2": "Fransa Ligue 2",
    "N1": "Hollanda Eredivisie",
    "B1": "Belçika Pro League",
    "P1": "Portekiz Liga Portugal",
    "SC0": "İskoçya Premiership",
    "SC1": "İskoçya Championship",
}
# Ek ligler: tüm sezonlar tek dosyada, ilk yarı skoru yok.
EK_LIGLER = {
    "POL": ("Poland", "Polonya Ekstraklasa"),
    "RUS": ("Russia", "Rusya Premier Lig"),
    "AUT": ("Austria", "Avusturya Bundesliga"),
    "SWE": ("Sweden", "İsveç Allsvenskan"),
}
SEZON_SAYISI = 4  # bu sezon + önceki 3 sezon
ANALIZ_SEZON = 5  # oran hareketi analizinde kullanılan sezon sayısı (ana ligler)

# Oran hareketi: Pinnacle ilk oran -> kapanış oranı değişimine göre gruplar
KOVALAR = [("≤ -%15", -9, -0.15), ("-%15 / -%5", -0.15, -0.05), ("±%5", -0.05, 0.05),
           ("+%5 / +%15", 0.05, 0.15), ("≥ +%15", 0.15, 9)]
SECIMLER = {
    "MS 1": ("PSH", "PSCH", "B365CH", lambda h, a: h > a),
    "MS X": ("PSD", "PSCD", "B365CD", lambda h, a: h == a),
    "MS 2": ("PSA", "PSCA", "B365CA", lambda h, a: h < a),
    "2.5 Üst": ("P>2.5", "PC>2.5", "B365C>2.5", lambda h, a: h + a > 2),
    "2.5 Alt": ("P<2.5", "PC<2.5", "B365C<2.5", lambda h, a: h + a < 3),
}
TEMEL = "https://www.football-data.co.uk"
CIKTI = "data.json"


def indir(url):
    for deneme in range(4):
        try:
            istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(istek, timeout=60) as yanit:
                return yanit.read().decode("utf-8-sig", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(15 * (deneme + 1))
        except Exception:
            time.sleep(15 * (deneme + 1))
    return None


def tarih(s):
    try:
        g, a, y = s.strip().split("/")
        y = int(y)
        if y < 100:
            y += 2000
        return f"{y:04d}-{int(a):02d}-{int(g):02d}"
    except Exception:
        return None


def sayi(s):
    try:
        return int(float(s))
    except Exception:
        return None


def oran(s):
    try:
        v = float(s)
        return v if v > 1 else None
    except Exception:
        return None


def bos_analiz():
    return {sec: [[0, 0, 0.0, 0.0, 0.0, 0.0, 0] for _ in KOVALAR] for sec in SECIMLER}


def analize_ekle(hedefler, m):
    r = m["ham"]
    for sec, (ilk_s, kap_s, b_s, tuttu_mu) in SECIMLER.items():
        ilk, kap, b365 = oran(r.get(ilk_s)), oran(r.get(kap_s)), oran(r.get(b_s))
        if not ilk or not kap:
            continue
        hareket = kap / ilk - 1
        i = next(j for j, (_, a, b) in enumerate(KOVALAR) if a <= hareket < b)
        tuttu = tuttu_mu(m["fh"], m["fa"])
        for hedef in hedefler:
            k = hedef[sec][i]
            k[0] += 1
            k[1] += 1 if tuttu else 0
            k[2] += 1 / kap
            k[3] += (ilk - 1) if tuttu else -1
            k[4] += (kap - 1) if tuttu else -1
            if b365:
                k[5] += (b365 - 1) if tuttu else -1
                k[6] += 1


def satirlar(metin):
    sonuc = []
    for r in csv.DictReader(io.StringIO(metin)):
        ev = (r.get("HomeTeam") or r.get("Home") or r.get("HT") or "").strip()
        dep = (r.get("AwayTeam") or r.get("Away") or r.get("AT") or "").strip()
        t = tarih(r.get("Date") or "")
        if not ev or not dep or not t:
            continue
        sonuc.append({
            "div": (r.get("Div") or "").strip(),
            "ulke": (r.get("Country") or "").strip(),
            "sezon": (r.get("Season") or "").strip(),
            "t": t,
            "saat": (r.get("Time") or "").strip(),
            "ev": ev, "dep": dep,
            "fh": sayi(r.get("FTHG") or r.get("HG")), "fa": sayi(r.get("FTAG") or r.get("AG")),
            "hh": sayi(r.get("HTHG")), "ha": sayi(r.get("HTAG")),
            "ham": r,
        })
    return sonuc


def main():
    eski = {}
    if os.path.exists(CIKTI):
        try:
            with open(CIKTI, encoding="utf-8") as f:
                eski = json.load(f)
        except Exception:
            eski = {}

    bugun = datetime.date.today()
    bas = bugun.year if bugun.month >= 7 else bugun.year - 1
    sezonlar = [bas - i for i in range(SEZON_SAYISI)]
    analiz = {"TUM": bos_analiz()}
    etiket = lambda y: f"{y}/{(y + 1) % 100:02d}"

    satir = lambda m: [m["t"], m["saat"], m["ev"], m["dep"], m["fh"], m["fa"], m["hh"], m["ha"]]
    maclar, sezon_listesi = {}, {}
    for div in LIGLER:
        maclar[div] = {}
        sezon_listesi[div] = [etiket(y) for y in sezonlar]
        analiz[div] = bos_analiz()
        for y in [bas - i for i in range(max(SEZON_SAYISI, ANALIZ_SEZON))]:
            kod = f"{y % 100:02d}{(y + 1) % 100:02d}"
            metin = indir(f"{TEMEL}/mmz4281/{kod}/{div}.csv")
            time.sleep(3)
            if metin is None:
                if y not in sezonlar:
                    continue
                onceki = eski.get("maclar", {}).get(div, {}).get(etiket(y))
                if onceki:
                    maclar[div][etiket(y)] = onceki
                continue
            liste = [m for m in satirlar(metin) if m["fh"] is not None]
            liste.sort(key=lambda m: (m["t"], m["saat"]))
            if bas - y < ANALIZ_SEZON:
                for m in liste:
                    analize_ekle([analiz["TUM"], analiz[div]], m)
            if y in sezonlar:
                maclar[div][etiket(y)] = [satir(m) for m in liste]

    for div, (ulke, _) in EK_LIGLER.items():
        metin = indir(f"{TEMEL}/new/{div}.csv")
        time.sleep(3)
        if metin is None:
            if div in eski.get("maclar", {}):
                maclar[div] = eski["maclar"][div]
                sezon_listesi[div] = eski.get("sezonlar", {}).get(div, [])
            continue
        tum = [m for m in satirlar(metin) if m["fh"] is not None and m["sezon"]]
        def ek_etiket(s):
            p = s.split("/")
            return f"{p[0]}/{p[1][-2:]}" if len(p) == 2 else s
        sec = sorted({m["sezon"] for m in tum}, reverse=True)[:SEZON_SAYISI]
        maclar[div], sezon_listesi[div] = {}, [ek_etiket(s) for s in sec]
        for s in sec:
            liste = sorted([m for m in tum if m["sezon"] == s], key=lambda m: (m["t"], m["saat"]))
            maclar[div][ek_etiket(s)] = [satir(m) for m in liste]

    fikstur = []
    metin = indir(f"{TEMEL}/fixtures.csv")
    if metin:
        for m in satirlar(metin):
            if m["div"] in LIGLER and m["t"] >= bugun.isoformat():
                fikstur.append([m["div"], m["t"], m["saat"], m["ev"], m["dep"]])
        fikstur.sort(key=lambda x: (x[1], x[2]))
    else:
        fikstur = [f for f in eski.get("fikstur", []) if f[0] in LIGLER]
    time.sleep(3)
    ulke_kod = {u: k for k, (u, _) in EK_LIGLER.items()}
    metin = indir(f"{TEMEL}/new_league_fixtures.csv")
    if metin:
        for m in satirlar(metin):
            if m["ulke"] in ulke_kod and m["t"] >= bugun.isoformat():
                fikstur.append([ulke_kod[m["ulke"]], m["t"], m["saat"], m["ev"], m["dep"]])
    else:
        fikstur += [f for f in eski.get("fikstur", []) if f[0] in EK_LIGLER]
    fikstur.sort(key=lambda x: (x[1], x[2]))

    def yuvarla(a):
        return {d: {s: [[k[0], k[1], round(k[2], 2), round(k[3], 2), round(k[4], 2), round(k[5], 2), k[6]]
                        for k in v] for s, v in x.items()} for d, x in a.items()}
    toplam = lambda a: sum(k[0] for v in (a or {}).get("TUM", {}).values() for k in v)
    oran_bolumu = {
        "kovalar": [k[0] for k in KOVALAR],
        "secimler": list(SECIMLER),
        "sezonlar": [etiket(bas - i) for i in range(ANALIZ_SEZON)],
        "veri": yuvarla(analiz),
    }
    eski_oran = eski.get("oran")
    if eski_oran and toplam(oran_bolumu["veri"]) < 0.8 * toplam(eski_oran.get("veri")):
        oran_bolumu = eski_oran  # bu sefer indirmeler eksik kaldı, eski analizi koru

    veri = {
        "oran": oran_bolumu,
        "guncelleme": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
        "ligler": {**LIGLER, **{k: v[1] for k, v in EK_LIGLER.items()}},
        "sezonlar": sezon_listesi,
        "maclar": maclar,
        "fikstur": fikstur,
    }
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
