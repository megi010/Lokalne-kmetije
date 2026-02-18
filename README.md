# 🥕 Lokalne kmetije
Namen spletne strani bo predstaviti lokalne kmetije in njihove produkte, ki jih ponujajo (sadje, zelenjava, med, vino …). Uporabniki bodo lahko iskali po regijah, vrsti pridelka in cenovnem rangu. Sistem bo omogočal registracijo kmetij, kjer bodo lastniki sami dodajali svoje izdelke v bazo. Uporabniki pa bodo imeli možnost ustvariti “nakupovalno košarico” in naročiti izdelke neposredno preko aplikacije. Dodali bomo tudi ocenjevanje in komentarje izdelkov, kar bo povečalo zaupanje med kupci. V bazi bomo hranili statistiko, ki bo omogočala vpogled v najbolj prodajane izdelke, najbolj aktivne regije ter sezonsko povpraševanje po produktih.

Sistem za lokalne kmetije in produkte
- Pregled kmetij in njihovih izdelkov (jabolka, med, vino …).
- Možnost naročanja košaric lokalne hrane.
- Statistika: najbolj prodajani izdelki, regije z največ ponudniki.

---

### 🚀 Navodila za namestitev in testiranje

Sistem za lokalne kmetije vključuje bazo podatkov SQLite, CLI (ukazni vmesnik) za upravljanje in Flask spletno aplikacijo.

#### 1. Namestitev okolja
Najprej klonirajte projekt in pripravite virtualno okolje:

```bash
# Premik v mapo projekta
cd Lokalne-kmetije

# Ustvarjanje virtualnega okolja
python3 -m venv .venv
source .venv/bin/activate  # Za Windows uporabi: .venv\Scripts\activate

# Namestitev potrebnih knjižnic
pip install -r farm_system/requirements.txt
```

#### 2. Inicializacija baze in podatkov
Pred prvo uporabo je potrebno pripraviti bazo in naložiti vzorčne podatke iz CSV datotek:

```bash
# Ustvarjanje tabel v bazi (database.db)
python3 farm_system/init_db.py

# Uvoz vzorčnih podatkov (uporabniki, kmetije, izdelki)
python3 farm_system/load_data.py
```

#### 3. Testiranje preko CLI (ukazni vmesnik)
CLI omogoča hiter pregled podatkov in upravljanje z uporabniki. Zaženite ga z:

```bash
python3 farm_system/cli.py
```

#### 4. Testiranje spletne aplikacije (Flask)
Spletni vmesnik omogoča pregled kmetij in izdelkov v brskalniku.

```bash
python3 farm_system/web.py
```
Aplikacija bo dostopna na: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

**Glavne poti (Routes) za testiranje:**
- `/` ali `/farms`: Seznam vseh registriranih kmetij.
- `/products`: Seznam vseh izdelkov s pripadajočimi kmetijami.
- `/region/<ime_regije>`: Filtriran prikaz (npr. `http://127.0.0.1:5000/region/Goriška`).

#### 5. Struktura projekta
- `database.py`: Logika za povezavo in poizvedbe.
- `schema.sql`: Definicija SQL tabel.
- `data/`: CSV datoteke z vzorčnimi podatki.
- `templates/`: HTML predloge za spletni vmesnik.
