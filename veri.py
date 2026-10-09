# Her gece GitHub'da çalışır: football-data.co.uk'dan sonuçları ve
# yaklaşan maçları indirir, uygulamanın okuduğu data.json dosyasını yazar.
import csv, io, json, os, time, datetime, urllib.request, urllib.error

# Uygulamada görünecek ligler. Lig eklemek/çıkarmak için bu listeyi düzenle.
LIGLER = {
    "T1": "Süper Lig",
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
}
SEZON_SAYISI = 4  # bu sezon + önceki 3 sezon
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


def satirlar(metin):
    sonuc = []
    for r in csv.DictReader(io.StringIO(metin)):
        ev = (r.get("HomeTeam") or r.get("HT") or "").strip()
        dep = (r.get("AwayTeam") or r.get("AT") or "").strip()
        t = tarih(r.get("Date") or "")
        if not ev or not dep or not t:
            continue
        sonuc.append({
            "div": (r.get("Div") or "").strip(),
            "t": t,
            "saat": (r.get("Time") or "").strip(),
            "ev": ev, "dep": dep,
            "fh": sayi(r.get("FTHG") or r.get("HG")), "fa": sayi(r.get("FTAG") or r.get("AG")),
            "hh": sayi(r.get("HTHG")), "ha": sayi(r.get("HTAG")),
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
    etiket = lambda y: f"{y}/{(y + 1) % 100:02d}"

    maclar = {}
    for div in LIGLER:
        maclar[div] = {}
        for y in sezonlar:
            kod = f"{y % 100:02d}{(y + 1) % 100:02d}"
            metin = indir(f"{TEMEL}/mmz4281/{kod}/{div}.csv")
            time.sleep(3)
            if metin is None:
                onceki = eski.get("maclar", {}).get(div, {}).get(etiket(y))
                if onceki:
                    maclar[div][etiket(y)] = onceki
                continue
            liste = [m for m in satirlar(metin) if m["fh"] is not None]
            liste.sort(key=lambda m: (m["t"], m["saat"]))
            maclar[div][etiket(y)] = [
                [m["t"], m["saat"], m["ev"], m["dep"], m["fh"], m["fa"], m["hh"], m["ha"]]
                for m in liste
            ]

    fikstur = []
    metin = indir(f"{TEMEL}/fixtures.csv")
    if metin:
        for m in satirlar(metin):
            if m["div"] in LIGLER and m["t"] >= bugun.isoformat():
                fikstur.append([m["div"], m["t"], m["saat"], m["ev"], m["dep"]])
        fikstur.sort(key=lambda x: (x[1], x[2]))
    else:
        fikstur = eski.get("fikstur", [])

    veri = {
        "guncelleme": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
        "ligler": LIGLER,
        "sezonlar": [etiket(y) for y in sezonlar],
        "maclar": maclar,
        "fikstur": fikstur,
    }
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
