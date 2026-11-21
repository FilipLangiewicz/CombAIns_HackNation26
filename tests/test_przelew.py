from odw2json.classify import load_types
from odw2json.extractors.przelew import extract

TYPE = next(t for t in load_types() if t.name == "przelew")


def run(text: str) -> dict:
    return extract(text, TYPE, {})["przelew_bankowy"]


def test_label_and_value_on_separate_lines():
    box = run(
        "Potwierdzenie\nRachunek obciążany\nPL05470680287581539721455024\nRachunek odbiorcy\n"
        "PL68438223049992295262834736\nKwota operacji\n1 200,50 PLN\nData transakcji\n2026-03-21\n"
        "Opis\nopłata skarbowa dla Jan Nowak w\npostępowaniu CEN2604016344389\nNr ref.\nCEN2604016344389\nZREALIZOWANO"
    )
    assert box["z_rachunku"] == "05470680287581539721455024"
    assert box["na_rachunek"] == "68438223049992295262834736"
    assert box["kwota"] == 1200.5
    assert box["data_operacji"] == "2026-03-21"
    assert box["tytul"] == "opłata skarbowa dla Jan Nowak w postępowaniu CEN2604016344389"
    assert box["numer_transakcji"] == "CEN2604016344389"


def test_dotted_leaders_and_print_date():
    box = run(
        "KWOTA PRZELEWU ........ PLN 34.00\nDATA TRANSAKCJI ........ 28.03.2026\nGODZ. ..... 13:42\n"
        "Z RACHUNKU\nPL93 8658 8132 1456 1688 8952 7298\nRACHUNEK ODBIORCY\nPL33 1125 1150 1590 5289 1601 4892\n"
        "TYTUŁ:\nopłata skarbowa\nCEN2604095639258\nNR REF. ..... CEN2604095639258\nSTATUS ..... Wykonany\n"
        "Data wydruku: 30.03.2026"
    )
    assert box["kwota"] == 34.0
    assert box["data_operacji"] == "2026-03-28"
    assert box["tytul"] == "opłata skarbowa CEN2604095639258"
    assert box["z_rachunku"].startswith("93")


def test_letter_with_quoted_title():
    box = run(
        "Warszawa, 29 kwietnia 2026\nBank potwierdza, że w dniu 26 kwietnia 2026 z rachunku nr "
        "PL97 5520 7608 8416 4658 2056 3693, prowadzonego dla A, wykonano przelew krajowy w kwocie 100,00 "
        "na rachunek nr PL98 2596 0273 7060 8888 3198\n4936, prowadzony dla B.\n"
        "Tytuł przelewu: „opłata skarbowa dla X w\nprzetargu DI.578.2026 CEN2605113961811”.\n"
        "Numer referencyjny operacji: CEN2605113961811.\nStatus: Zrealizowany."
    )
    assert box["data_operacji"] == "2026-04-26"
    assert box["kwota"] == 100.0
    assert box["na_rachunek"] == "98259602737060888831984936"
    assert box["tytul"] == "opłata skarbowa dla X w przetargu DI.578.2026 CEN2605113961811"
    assert box["numer_transakcji"] == "CEN2605113961811"


def test_missing_values_stay_null():
    box = run("Potwierdzenie przelewu\nKwota 10,00 PLN")
    assert box["kwota"] == 10.0
    assert box["tytul"] is None and box["z_rachunku"] is None
