"""The classification of documents that are similar to a known type, but are not of a known type.

The texts are short copies of the layouts of real documents in KIO cases (see dane/negatywne/).
"""

import pytest

from odw2json.classify import classify

NEGATIVE = {
    "odpowiedz_na_odwolanie": """Warszawa, dnia 14.04.2026 r.
Krajowa Izba Odwoławcza
ul. Postępu 17a, 02-676 Warszawa
Sygn. akt: KIO 1234/26
Zamawiający: Gmina Miasto Kielce, ul. Rynek 1, 25-303 Kielce
Odwołujący: Alfa Budowa sp. z o.o., ul. Leśna 3, 00-950 Warszawa
ODPOWIEDŹ ZAMAWIAJĄCEGO NA ODWOŁANIE
Działając w imieniu Zamawiającego, w odpowiedzi na odwołanie wniesione w dniu 10.04.2026 r.,
wnoszę o oddalenie odwołania w całości. Zarzuty Odwołującego są bezzasadne.
Uzasadnienie
Zamawiający w dniu 31.03.2026 r. dokonał wyboru oferty najkorzystniejszej.
""",
    "odpowiedz_bez_sygnatury": """Kielce, 14.04.2026
Do Prezesa Krajowej Izby Odwoławczej
Zamawiający: Gmina Miasto Kielce
Odwołujący: Alfa Budowa sp. z o.o.
Pismo Zamawiającego – odpowiedź na odwołanie
Zamawiający wnosi o oddalenie odwołania. Zarzut naruszenia art. 226 ust. 1 pkt 5 Pzp
jest chybiony, bo oferta Odwołującego nie spełnia wymagań SWZ.
""",
    "przystapienie": """Gdańsk, dnia 20.04.2026 r.
Do Prezesa Krajowej Izby Odwoławczej
ul. Postępu 17a, 02-676 Warszawa
Odwołujący: Alfa Budowa sp. z o.o.
Zamawiający: Gmina Miasto Gdańsk
Wykonawca przystępujący: Beta Drogi S.A., NIP 5260001122
PRZYSTĄPIENIE DO POSTĘPOWANIA ODWOŁAWCZEGO
po stronie Zamawiającego
Działając w imieniu wykonawcy Beta Drogi S.A., zgłaszam przystąpienie do postępowania
odwoławczego toczącego się na skutek odwołania wniesionego przez Odwołującego. Zarzuty
odwołania są bezzasadne. W załączeniu kopia odwołania i pełnomocnictwo.
""",
    "wezwanie_do_uzupelnienia": """KRAJOWA IZBA ODWOŁAWCZA
Warszawa, dnia 15.04.2026 r.
KIO/WO/1234/26
Alfa Budowa sp. z o.o.
ul. Leśna 3, 00-950 Warszawa
WEZWANIE
Prezes Krajowej Izby Odwoławczej wzywa Odwołującego do uzupełnienia braków formalnych odwołania
z dnia 10.04.2026 r. przez złożenie pełnomocnictwa oraz dowodu uiszczenia wpisu, w terminie
3 dni od dnia doręczenia wezwania, pod rygorem zwrotu odwołania.
""",
    "wezwanie_zamawiajacego": """Zamawiający: Gmina Miasto Kielce
Kielce, dnia 12.04.2026 r.
Znak sprawy: ZP.271.5.2026
Wykonawcy biorący udział w postępowaniu
Wezwanie do przystąpienia do postępowania odwoławczego
Zamawiający informuje, że w dniu 10.04.2026 r. wykonawca Alfa Budowa sp. z o.o. wniósł odwołanie
do Prezesa Krajowej Izby Odwoławczej. Odwołujący zarzuca Zamawiającemu naruszenie art. 226 Pzp.
W załączeniu kopia odwołania. Wykonawca może zgłosić przystąpienie w terminie 3 dni.
""",
    "pismo_procesowe": """Warszawa, 22.04.2026 r.
Krajowa Izba Odwoławcza
Sygn. akt KIO 1234/26
Odwołujący: Alfa Budowa sp. z o.o.
Zamawiający: Gmina Miasto Kielce
PISMO PROCESOWE ODWOŁUJĄCEGO
Odwołujący podtrzymuje wszystkie zarzuty odwołania i przedstawia nowe dowody.
""",
    "pismo_procesowe_bez_sygnatury": """Warszawa, 22.04.2026 r.
Do Krajowej Izby Odwoławczej
Odwołujący: Alfa Budowa sp. z o.o.
Zamawiający: Gmina Miasto Kielce
Pismo procesowe Odwołującego
Odwołujący podtrzymuje zarzuty odwołania z dnia 10.04.2026 r. i wnosi o uwzględnienie odwołania.
""",
    "wyrok": """Sygn. akt: KIO 1234/26
WYROK
z dnia 30 kwietnia 2026 r.
Krajowa Izba Odwoławcza - w składzie: Przewodniczący: Jan Nowak
po rozpoznaniu na rozprawie odwołania wniesionego przez wykonawcę Alfa Budowa sp. z o.o.
w postępowaniu prowadzonym przez Zamawiającego: Gmina Miasto Kielce
orzeka: 1. uwzględnia odwołanie i nakazuje Zamawiającemu unieważnienie czynności wyboru oferty.
""",
    "wyrok_z_naglowkiem": """KRAJOWA IZBA ODWOŁAWCZA
w Warszawie
WYROK
z dnia 30 kwietnia 2026 r.
Krajowa Izba Odwoławcza w składzie: Przewodniczący: Jan Nowak
po rozpoznaniu odwołania wniesionego przez Odwołującego: Alfa Budowa sp. z o.o.
Zamawiający: Gmina Miasto Kielce. Zarzuty odwołania potwierdziły się.
""",
    "postanowienie": """POSTANOWIENIE
z dnia 30 kwietnia 2026 r.
Krajowa Izba Odwoławcza umarza postępowanie odwoławcze, bo Odwołujący cofnął odwołanie.
Zamawiający: Gmina Miasto Kielce. Odwołujący: Alfa Budowa sp. z o.o.
""",
    "swz": """SPECYFIKACJA WARUNKÓW ZAMÓWIENIA
w postępowaniu o udzielenie zamówienia publicznego prowadzonym w trybie podstawowym
Znak sprawy: ZP.271.5.2026
Zamawiający: Gmina Miasto Kielce, ul. Rynek 1, 25-303 Kielce, NIP 6570000000
I. Nazwa oraz adres Zamawiającego
II. Tryb udzielenia zamówienia
XXV. Pouczenie o środkach ochrony prawnej
1. Odwołanie przysługuje na niezgodną z przepisami ustawy czynność Zamawiającego.
2. Odwołanie wnosi się do Prezesa Krajowej Izby Odwoławczej.
3. Pełnomocnictwo do reprezentowania wykonawcy składa się w formie elektronicznej.
Rachunek bankowy do wniesienia wadium: 12 1020 1026 0000 0102 0001 2345, kwota 5 000,00 PLN.
""",
    "zawiadomienie_o_wyborze": """Kielce, dnia 31.03.2026 r.
Zamawiający: Gmina Miasto Kielce
Znak sprawy: ZP.271.5.2026
Zawiadomienie o wyborze najkorzystniejszej oferty
Zamawiający informuje, że jako najkorzystniejszą wybrał ofertę wykonawcy Beta Drogi S.A.
Oferta wykonawcy Alfa Budowa sp. z o.o. została odrzucona.
Pouczenie: Odwołanie wnosi się do Prezesa Krajowej Izby Odwoławczej w terminie 10 dni.
""",
    "faktura": """FAKTURA VAT nr FV/123/2026
Data wystawienia: 14.05.2026
Sprzedawca: Alfa Serwis sp. z o.o., NIP: 5250001234
Rachunek: PL61 1090 1014 0000 0712 1981 2874
Nabywca: Beta S.A., NIP: 5260001122
Usługa prawna – sporządzenie odwołania do KIO   1 000,00   230,00   1 230,00
Razem do zapłaty: 1 230,00 PLN
Sposób płatności: przelew, termin płatności: 28.05.2026
""",
    "faktura_z_naglowkiem": """Alfa Serwis sp. z o.o.
ul. Długa 5, 00-001 Warszawa
Warszawa, 14.05.2026
Faktura nr FV/123/2026
Nabywca: Beta S.A.
Kwota do zapłaty: 1 230,00 PLN
Płatność przelewem na rachunek: 61 1090 1014 0000 0712 1981 2874
Tytuł: FV/123/2026
""",
    "potwierdzenie_nadania": """POCZTA POLSKA
Potwierdzenie nadania przesyłki poleconej
Nadawca: Alfa Budowa sp. z o.o., ul. Leśna 3, 00-950 Warszawa
Adresat: Krajowa Izba Odwoławcza, ul. Postępu 17a, 02-676 Warszawa
Numer nadawczy: 00259007738123456789
Data nadania: 10.04.2026 Opłata: 12,50 zł
""",
    "upo_epuap": """Urzędowe Poświadczenie Odbioru
Dokument został doręczony
Nazwa adresata: Krajowa Izba Odwoławcza
Nadawca: Alfa Budowa sp. z o.o.
Identyfikator dokumentu: 1234567
Tytuł dokumentu: Odwołanie
Data doręczenia: 2026-04-10 12:31:05
""",
    "odpis_krs": """CENTRALNA INFORMACJA KRAJOWEGO REJESTRU SĄDOWEGO
Stan na dzień 01.04.2026 godz. 10:15:22 Numer KRS: 0000123456
ODPIS AKTUALNY
Z REJESTRU PRZEDSIĘBIORCÓW
Dział 1 Rubryka 1 - Dane podmiotu
Firma, pod którą spółka działa: ALFA BUDOWA SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ
Numer REGON/NIP: REGON: 123456789, NIP: 5250001234
Dział 2 Rubryka 1 - Organ uprawniony do reprezentacji podmiotu
Nazwa organu: ZARZĄD. Sposób reprezentacji: każdy członek zarządu samodzielnie.
Rubryka 2 - Prokurenci
1. Nazwisko: KOWALSKI, Imiona: JAN, Rodzaj prokury: PROKURA SAMOIEZALEŻNA
""",
    "wyciag_ceidg": """Wydruk z Centralnej Ewidencji i Informacji o Działalności Gospodarczej
Imię i nazwisko: Jan Kowalski
Firma przedsiębiorcy: Kowalski Usługi Budowlane Jan Kowalski
NIP: 5250001234 REGON: 123456789
Status: aktywny. Pełnomocnicy: brak.
""",
    "oswiadczenie_wykonawcy": """OŚWIADCZENIE WYKONAWCY
składane na podstawie art. 125 ust. 1 ustawy Pzp
Wykonawca: Alfa Budowa sp. z o.o., NIP 5250001234
Na potrzeby postępowania o udzielenie zamówienia publicznego prowadzonego przez Zamawiającego
oświadczam, że nie podlegam wykluczeniu z postępowania.
""",
    "ogloszenie": """Ogłoszenie o zamówieniu
Roboty budowlane
Budowa drogi gminnej
SEKCJA I – ZAMAWIAJĄCY
Gmina Miasto Kielce
SEKCJA VIII – PROCEDURA ODWOŁAWCZA
Odwołanie przysługuje do Krajowej Izby Odwoławczej.
""",
}

POSITIVE = {
    "odwolanie_tytul_w_linii": (
        "odwolanie",
        """Warszawa, dnia 10.04.2026 r.
Do Prezesa Krajowej Izby Odwoławczej
ul. Postępu 17a, 02-676 Warszawa
Odwołujący: Alfa Budowa sp. z o.o., NIP 5250001234
Zamawiający: Gmina Miasto Kielce
Odwołanie od czynności Zamawiającego w postępowaniu nr ZP.271.5.2026
Na podstawie art. 513 Pzp wnoszę odwołanie od czynności odrzucenia oferty Odwołującego.
Zarzucam Zamawiającemu naruszenie art. 226 ust. 1 pkt 5 Pzp.
""",
    ),
    "odwolanie_wielkie_litery": (
        "odwolanie",
        """Warszawa, 10.04.2026
Krajowa Izba Odwoławcza
Odwołujący: Alfa Budowa sp. z o.o.
Zamawiający: Gmina Miasto Kielce
O D W O Ł A N I E
Zaskarżam czynność Zamawiającego z dnia 31.03.2026 r. i zarzucam naruszenie art. 226 Pzp.
""",
    ),
    "pelnomocnictwo_procesowe": (
        "pelnomocnictwo",
        """Warszawa, 09.04.2026
PEŁNOMOCNICTWO PROCESOWE
Alfa Budowa sp. z o.o., KRS 0000123456, NIP 5250001234, reprezentowana przez Jana Kowalskiego
– Prezesa Zarządu, udziela pełnomocnictwa adw. Annie Nowak do reprezentowania Mocodawcy
w postępowaniu odwoławczym przed Krajową Izbą Odwoławczą.
""",
    ),
    "pelnomocnictwo_male_litery": (
        "pelnomocnictwo",
        """Pełnomocnictwo
Ja, niżej podpisany Jan Kowalski, działając w imieniu Alfa Budowa sp. z o.o., upoważniam
radcę prawnego Annę Nowak do wniesienia odwołania do Krajowej Izby Odwoławczej.
""",
    ),
    "przelew_wpis": (
        "przelew",
        """Potwierdzenie wykonania przelewu
Data operacji: 10.04.2026
Z rachunku: 12 1020 1026 0000 0102 0001 2345
Na rachunek: 33 1010 1010 0001 1122 3100 0000
Kwota: 15 000,00 PLN
Tytuł: Wpis od odwołania, ZP.271.5.2026
""",
    ),
    "przelew_oplata_skarbowa": (
        "przelew",
        """Szczegóły transakcji
Nadawca: Alfa Budowa sp. z o.o.
Rachunek nadawcy: PL12 1020 1026 0000 0102 0001 2345
Odbiorca: Urząd Miasta Stołecznego Warszawy
Rachunek odbiorcy: PL21 1030 1508 0000 0005 5000 0070
Kwota: 17,00 PLN
Tytuł: opłata skarbowa od pełnomocnictwa
""",
    ),
}


@pytest.mark.parametrize("name", NEGATIVE)
def test_similar_documents_have_no_known_type(name):
    found = classify(NEGATIVE[name])
    assert found.doc_type is None, (found.doc_type.name, found.hits[found.doc_type.name])


@pytest.mark.parametrize("name", POSITIVE)
def test_known_types_in_other_forms(name):
    expected, text = POSITIVE[name]
    found = classify(text)
    assert found.doc_type is not None and found.doc_type.name == expected, found.scores
