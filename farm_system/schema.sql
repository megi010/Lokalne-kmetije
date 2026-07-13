-- =====================================================================
-- Kmetijski trg - shema podatkovne baze (SQLite)
--
-- Tabele brišemo v obratnem vrstnem redu od ustvarjanja, da ne kršimo
-- tujih ključev (najprej "otroci", nato "starši").
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Ocena;
DROP TABLE IF EXISTS Postavka_narocila;
DROP TABLE IF EXISTS Narocilo;
DROP TABLE IF EXISTS Izdelek;
DROP TABLE IF EXISTS Kmetija;
DROP TABLE IF EXISTS Uporabnik;


-- ---------------------------------------------------------------------
-- Uporabnik: kupci, lastniki kmetij in administratorji.
-- Geslo je vedno shranjeno kot zgoščena vrednost (hash), nikoli v čistopisu.
-- ---------------------------------------------------------------------
CREATE TABLE Uporabnik (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ime TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    geslo TEXT NOT NULL,
    tip TEXT NOT NULL
        CHECK (tip IN ('kupec', 'lastnik kmetije', 'admin'))
);


-- ---------------------------------------------------------------------
-- Kmetija: vsako kmetijo upravlja natanko en uporabnik (1:N, ker ima
-- uporabnik lahko več kmetij).
--
-- ON DELETE RESTRICT: uporabnika, ki je lastnik kmetije, ne moremo
-- izbrisati, dokler kmetije ne prenesemo na drugega lastnika ali izbrišemo.
-- Tako nikoli ne ostane kmetija brez odgovorne osebe.
-- ---------------------------------------------------------------------
CREATE TABLE Kmetija (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ime_kmetije TEXT NOT NULL,
    vrsta_kmetije TEXT,
    delovni_cas TEXT,
    kraj TEXT,
    regija TEXT,
    telefonska_stevilka TEXT
        CHECK (telefonska_stevilka GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    spletna_stran TEXT,
    id_uporabnika INTEGER NOT NULL,
    FOREIGN KEY (id_uporabnika) REFERENCES Uporabnik(id)
        ON DELETE RESTRICT
);


-- ---------------------------------------------------------------------
-- Izdelek: pripada natanko eni kmetiji (1:N).
--
-- ON DELETE CASCADE: če kmetija preneha delovati, njeni izdelki nimajo
-- več pomena in se izbrišejo skupaj z njo.
-- ---------------------------------------------------------------------
CREATE TABLE Izdelek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ime_izdelka TEXT NOT NULL,
    vrsta TEXT,
    kolicina TEXT,                                  -- opis pakiranja, npr. "500 g"
    cena REAL NOT NULL CHECK (cena > 0),
    zaloga INTEGER NOT NULL DEFAULT 0 CHECK (zaloga >= 0),
    id_kmetije INTEGER NOT NULL,
    FOREIGN KEY (id_kmetije) REFERENCES Kmetija(id)
        ON DELETE CASCADE
);


-- ---------------------------------------------------------------------
-- Narocilo: naročilo enega uporabnika.
--
-- Status 'kosarica' pomeni odprto (še neoddano) košarico. Vsak uporabnik
-- ima lahko največ eno naročilo s tem statusom hkrati.
--
-- ON DELETE RESTRICT: uporabnika z zgodovino naročil ne izbrišemo, ker bi
-- s tem izgubili podatke o prodaji, ki jih potrebujejo kmetije.
-- ---------------------------------------------------------------------
CREATE TABLE Narocilo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_uporabnika INTEGER NOT NULL,
    datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL
        CHECK (status IN ('kosarica', 'oddano', 'zakljuceno', 'preklicano')),
    FOREIGN KEY (id_uporabnika) REFERENCES Uporabnik(id)
        ON DELETE RESTRICT
);


-- ---------------------------------------------------------------------
-- Postavka_narocila: vezna tabela, ki realizira odnos M:N med naročili
-- in izdelki. Hrani tudi ceno ob nakupu, ker se cena izdelka lahko
-- pozneje spremeni, znesek starega računa pa mora ostati nespremenjen.
--
-- ON DELETE CASCADE (Narocilo): postavka brez naročila nima pomena.
-- ON DELETE RESTRICT (Izdelek): izdelka, ki je bil že kdaj naročen, ne
-- moremo izbrisati - s tem bi uničili zgodovino nakupov. Namesto brisanja
-- mu nastavimo zalogo na 0.
-- ---------------------------------------------------------------------
CREATE TABLE Postavka_narocila (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_narocila INTEGER NOT NULL,
    id_izdelka INTEGER NOT NULL,
    kolicina INTEGER NOT NULL CHECK (kolicina > 0),
    cena_ob_nakupu REAL NOT NULL CHECK (cena_ob_nakupu > 0),
    UNIQUE (id_narocila, id_izdelka),               -- isti izdelek se v naročilu pojavi le enkrat
    FOREIGN KEY (id_narocila) REFERENCES Narocilo(id)
        ON DELETE CASCADE,
    FOREIGN KEY (id_izdelka) REFERENCES Izdelek(id)
        ON DELETE RESTRICT
);


-- ---------------------------------------------------------------------
-- Ocena: uporabnik lahko vsak izdelek oceni natanko enkrat (UNIQUE).
--
-- ON DELETE CASCADE: ocena je osebni podatek uporabnika in nima pomena
-- brez izdelka, na katerega se nanaša.
-- ---------------------------------------------------------------------
CREATE TABLE Ocena (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_uporabnika INTEGER NOT NULL,
    id_izdelka INTEGER NOT NULL,
    ocena INTEGER NOT NULL CHECK (ocena BETWEEN 1 AND 5),
    komentar TEXT,
    datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_uporabnika, id_izdelka),
    FOREIGN KEY (id_uporabnika) REFERENCES Uporabnik(id)
        ON DELETE CASCADE,
    FOREIGN KEY (id_izdelka) REFERENCES Izdelek(id)
        ON DELETE CASCADE
);


-- ---------------------------------------------------------------------
-- Indeksi na tujih ključih, po katerih pogosto iščemo (pohitritev JOIN-ov).
-- ---------------------------------------------------------------------
CREATE INDEX idx_izdelek_kmetija ON Izdelek(id_kmetije);
CREATE INDEX idx_postavka_narocilo ON Postavka_narocila(id_narocila);
CREATE INDEX idx_ocena_izdelek ON Ocena(id_izdelka);
CREATE INDEX idx_narocilo_uporabnik ON Narocilo(id_uporabnika, status);
