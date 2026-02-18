DROP TABLE IF EXISTS Ocena;
DROP TABLE IF EXISTS Postavka_narocila;
DROP TABLE IF EXISTS Narocilo;
DROP TABLE IF EXISTS Izdelek;
DROP TABLE IF EXISTS Kmetija;
DROP TABLE IF EXISTS Uporabnik;

CREATE TABLE Uporabnik (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ime TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    geslo TEXT NOT NULL,
    tip TEXT CHECK(tip IN ('kupec', 'lastnik kmetije', 'admin')) NOT NULL
);

CREATE TABLE Kmetija (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ime_kmetije TEXT NOT NULL,
    vrsta_kmetije TEXT,
    kraj TEXT,
    regija TEXT,
    telefonska_stevilka TEXT,
    spletna_stran TEXT,
    id_uporabnika INTEGER,
    FOREIGN KEY (id_uporabnika) REFERENCES Uporabnik(id)
);

CREATE TABLE Izdelek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ime_izdelka TEXT NOT NULL,
    vrsta TEXT,
    kolicina TEXT,
    cena REAL NOT NULL,
    zaloga INTEGER DEFAULT 0,
    id_kmetije INTEGER,
    povprecna_ocena REAL DEFAULT 0,
    FOREIGN KEY (id_kmetije) REFERENCES Kmetija(id)
);

CREATE TABLE Narocilo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_uporabnika INTEGER,
    datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    skupna_cena REAL,
    FOREIGN KEY (id_uporabnika) REFERENCES Uporabnik(id)
);

CREATE TABLE Postavka_narocila (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_narocila INTEGER,
    id_izdelka INTEGER,
    kolicina INTEGER,
    cena REAL,
    FOREIGN KEY (id_narocila) REFERENCES Narocilo(id),
    FOREIGN KEY (id_izdelka) REFERENCES Izdelek(id)
);

CREATE TABLE Ocena (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_uporabnika INTEGER,
    id_izdelka INTEGER,
    ocena INTEGER CHECK(ocena >= 1 AND ocena <= 5),
    komentar TEXT,
    datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_uporabnika) REFERENCES Uporabnik(id),
    FOREIGN KEY (id_izdelka) REFERENCES Izdelek(id)
);
