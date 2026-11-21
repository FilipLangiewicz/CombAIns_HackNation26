from odw2json.classify import load_types
from odw2json.extractors.pelnomocnictwo import extract

DOC_TYPE = next(t for t in load_types() if t.name == "pelnomocnictwo")


def run(text: str) -> dict:
    return extract(text, DOC_TYPE, {})


COMPANY = """P E Ł N O M O C N I C T W O
Mocodawca Hartica Serwis S.A.
ul. Akacjowa 54, 80-122 Gdańsk
Dane rejestrowe KRS 9999669444, NIP 9990678035, REGON 999114017
Pełnomocnicy adw. Bartosz Szymanski, nr wpisu WA 33513
r. pr. Katarzyna Michalak, PESEL 85071204278
Zakres: udzielania dalszych pełnomocnictw radcom prawnym i adwokatom.
............
Aleksandra Nowakowicz
Prokurent
"""


def test_company_with_two_attorneys():
    data = run(COMPANY)
    principal = data["mocodawca"][0]
    assert principal["data"] == {
        "imie_nazwisko": None, "krs": "9999669444", "nazwa": "Hartica Serwis S.A.", "nip": "9990678035", "typ": "osoba_prawna",
    }  # fmt: skip
    assert principal["podpisujacy"] == [{"imie_nazwisko": "Aleksandra Nowakowicz"}]
    assert data["pelnomocnicy"] == [
        {"imie_nazwisko": "Bartosz Szymanski", "pesel": None},
        {"imie_nazwisko": "Katarzyna Michalak", "pesel": "85071204278"},
    ]


def test_natural_person():
    text = (
        "PEŁNOMOCNICTWO\nJa, niżej podpisany Jarosław Dudek, prowadzący działalność gospodarczą pod firmą DUDEK-TECH\n"
        "Jarosław Dudek, ul. Nadbystrzycka 40, 20-618 Lublin, NIP 9994150873, REGON 999603218, niniejszym udzielam\n"
        "pełnomocnictwa: adw. Natalia Górecka (nr wpisu na listę: LU/Adw/733).\n"
    )
    data = run(text)["mocodawca"][0]
    assert data["data"]["typ"] == "osoba_fizyczna"
    assert data["data"]["imie_nazwisko"] == "Jarosław Dudek"
    assert data["data"]["nazwa"] == "DUDEK-TECH Jarosław Dudek"
    assert data["data"]["krs"] is None
    assert data["podpisujacy"] == [{"imie_nazwisko": "Jarosław Dudek"}]


def test_consortium_signers_follow_the_company():
    text = (
        "PEŁNOMOCNICTWO\nKonsorcjum: 1) Torvex Budownictwo sp. z o.o., ul. Przemysłowa 8, 87-100 Toruń, KRS 9995540127, "
        "NIP 9992284611, REGON 999473016; 2) Hydromel Instalacje sp.j., ul. Lipowa 15, 85-016 Bydgoszcz, KRS "
        "9997108834, NIP 9994417025, REGON 999650438 udzielają pełnomocnictwa: adw. Piotr Zalewski.\n"
        "W imieniu Torvex Budownictwo sp. z o.o.:\n....\nMarek Domański\nPrezes Zarządu\n"
        "W imieniu Hydromel Instalacje sp.j.:\n....\nAgnieszka Kurek\nWspólnik\n....\nRobert Kurek\nWspólnik\n"
    )
    principals = run(text)["mocodawca"]
    assert [p["data"]["nazwa"] for p in principals] == ["Torvex Budownictwo sp. z o.o.", "Hydromel Instalacje sp.j."]
    assert [len(p["podpisujacy"]) for p in principals] == [1, 2]
