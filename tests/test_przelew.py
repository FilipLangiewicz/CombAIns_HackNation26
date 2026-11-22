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
    assert box["z_rachunku"] == "PL05470680287581539721455024"
    assert box["na_rachunek"] == "PL68438223049992295262834736"
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
    assert box["z_rachunku"].startswith("PL93")


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
    assert box["na_rachunek"] == "PL98259602737060888831984936"
    assert box["tytul"] == "opłata skarbowa dla X w przetargu DI.578.2026 CEN2605113961811"
    assert box["numer_transakcji"] == "CEN2605113961811"


def test_missing_values_stay_null():
    box = run("Potwierdzenie przelewu\nKwota 10,00 PLN")
    assert box["kwota"] == 10.0
    assert box["tytul"] is None and box["z_rachunku"] is None


def test_amount_forms_and_date_with_time():
    assert run("Kwota: PLN 1 234,56\nData księgowania 22.03.2026\nData realizacji 21.03.2026 12:34")["kwota"] == 1234.56
    box = run("Kwota przelewu 1.234,56 zł\nData księgowania 22.03.2026\nData realizacji 21.03.2026 12:34")
    assert box["kwota"] == 1234.56
    assert box["data_operacji"] == "2026-03-21"


def test_account_labels_with_konto():
    box = run("Konto nadawcy: 05 4706 8028 7581 5397 2145 5024\nKonto odbiorcy: PL68438223049992295262834736")
    assert box["z_rachunku"] == "05470680287581539721455024"
    assert box["na_rachunek"] == "PL68438223049992295262834736"


def test_title_wraps_onto_line_that_starts_with_a_label_word():
    box = run(
        "Tytuł przelewu opłata od pełnomocnictwa w przetargu\nnr 5/2026 CEN2604016344389\n"
        "Numer referencyjny CEN2604016344389\nStatus Wykonany"
    )
    assert box["tytul"] == "opłata od pełnomocnictwa w przetargu nr 5/2026 CEN2604016344389"


def test_joined_lines_and_page_marker():
    box = run(
        "Tytuł przelewu opłata skarbowa w przetargu ZP.1.2026 CEN2604016344389 Kwota 17,00 PLN Data transakcji 2026-08-12\n"
        "Rachunek odbiorcy PL68 4382 2304 9992\n1/2\n2952 6283 4736"
    )
    assert box["tytul"] == "opłata skarbowa w przetargu ZP.1.2026 CEN2604016344389"
    assert box["na_rachunek"] == "PL68438223049992295262834736"


def test_table_with_labels_first_and_english_labels():
    box = run(
        "Transfer details\nDebit account\nCredit account\nAmount\nExecution date\nPayment details\n"
        "PL50-9149-2777-3285-0564-7953-8535\nPL84-8710-6501-1666-0434-6461-5387\n50,00 PLN\n04/09/2026\nopłata skarbowa OI/11/2026"
    )
    assert box["z_rachunku"] == "PL50914927773285056479538535"
    assert box["na_rachunek"] == "PL84871065011666043464615387"
    assert box["kwota"] == 50.0 and box["data_operacji"] == "2026-09-04"
    assert box["tytul"] == "opłata skarbowa OI/11/2026"


def test_amount_without_label_and_nr_in_title():
    box = run(
        "Przelew\n- 7 500,00 PLN\nZ konta: PL26 9453 8585 3400 9655 1641 3734\nOpis: ZESPÓŁ SZKÓŁ NR 10 W WROCŁAWIU\nSaldo po operacji: 10,00 PLN"
    )
    assert box["kwota"] == 7500.0
    assert box["tytul"] == "ZESPÓŁ SZKÓŁ NR 10 W WROCŁAWIU"


def test_foreign_iban_and_polish_account():
    box = run(
        "Potwierdzenie przelewu\nRachunek nadawcy: DE89 3704 0044 0532 0130 00\n"
        "Rachunek odbiorcy: 68 4382 2304 9992 2952 6283 4736\nKwota: 100,00 PLN\nData operacji: 2026-03-21"
    )
    assert box["z_rachunku"] == "DE89370400440532013000"
    assert box["na_rachunek"] == "68438223049992295262834736"


def _transfer(text: str) -> dict:
    from odw2json.classify import load_types
    from odw2json.extractors import przelew

    doc_type = next(t for t in load_types() if t.name == "przelew")
    return przelew.extract(text, doc_type, {})["przelew_bankowy"]


def test_date_in_the_next_line_is_not_the_amount():
    box = _transfer("Potwierdzenie transakcji\nKwota\n11.09.2026\n7 500,00 PLN\n")
    assert box["kwota"] == 7500.0


def test_reference_with_a_slash_is_not_a_page_number():
    box = _transfer("Kwota przelewu\n15 000,00 PLN\nNumer transakcji\n20260715/3219039\n")
    assert box["numer_transakcji"] == "20260715/3219039"


def test_account_with_a_dot_from_the_ocr():
    box = _transfer("Rachunek beneficjenta\n60 1010 1010 0081.3622 3100 0000\nKwota\n100,00 PLN\n")
    assert box["na_rachunek"] == "60101010100081362231000000"


def test_damaged_account_of_the_uzp():
    box = _transfer("Dane odbiorcy\nNumer rachunku\nUrza a blich Pstep17A 60 101001362231000\nKwota\n7 500,00 PLN\n")
    assert box["na_rachunek"] == "60101010100081362231000000"


def test_table_with_a_title_in_more_lines():
    # The labels come first and then the values. The title takes two lines of the table.
    text = (
        "Bank Pekao S.A.\nPotwierdzenie przelewu\nZleceniodawca\nZ rachunku\nBeneficjent\nNa rachunek\nKwota\n"
        "Tytuł płatności\nData realizacji\nNumer transakcji\nMedi-Serwis sp. k.\nPL17116012029682912440455846\n"
        "Urząd Miasta Olsztyn\nPL 34 1050 1012 1775 5248 4800 9964\n34,00 PLN\n"
        "opłata skarbowa od pełnomocnictwa - Podlasie Dostawy\nMedyczne S.A., postępowanie BZP/ZP/10/2026\n"
        "02-11-2025\nCEN29409124493\n"
    )
    box = run(text)
    assert (
        box["tytul"]
        == "opłata skarbowa od pełnomocnictwa - Podlasie Dostawy Medyczne S.A., postępowanie BZP/ZP/10/2026"
    )
    assert (box["numer_transakcji"], box["data_operacji"], box["kwota"]) == ("CEN29409124493", "2025-11-02", 34.0)


def test_domestic_transfer_printout():
    from odw2json.pipeline import process_text

    text = (
        "B Bank Karpacki\nPrzelew krajowy\nDane zleceniodawcy\n11 1240 1111 9078 8570 5000 0455\n"
        "Dane kontrahenta\nRachunek kontrahenta 25 1030 1508 9486 5035 5622 1675\nKwota 17.00 PLN\n"
        "Szczegóły płatności opłata skarbowa od pełnomocnictwa\nSignature Not Verified\n"
    )
    result = process_text(text)
    assert result.doc_type == "przelew"
    assert result.data["przelew_bankowy"]["tytul"] == "opłata skarbowa od pełnomocnictwa"
