import re
from pathlib import Path

import pytest

from odw2json.synth import CODES, generate

SCHEMA = Path(__file__).resolve().parents[1] / "docs" / "task" / "organizer" / "oczekiwane-json"
DOCS = generate(30, 7)


def schema_keys(name: str) -> set[str]:
    return set(re.findall(r'"([\w-]+)"\s*:', (SCHEMA / name).read_text(encoding="utf-8")))


def all_keys(obj) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | set().union(*(all_keys(v) for v in obj.values()), set())
    if isinstance(obj, list):
        return set().union(*(all_keys(v) for v in obj), set())
    return set()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def of_type(t: str):
    return [d for d in DOCS if d[0].startswith(t + "/")]


def test_counts_and_names_are_unique():
    assert len(of_type("przelew")) == len(of_type("odwolanie")) == len(of_type("pelnomocnictwo")) == 30
    assert len({d[0] for d in DOCS}) == len(DOCS)


def test_generate_is_deterministic():
    assert generate(5, 3) == generate(5, 3)


@pytest.mark.parametrize(
    "kind,file",
    [("przelew", "przelew.json"), ("odwolanie", "odwolanie.json"), ("pelnomocnictwo", "pelnomocnictwo.json")],
)
def test_gold_keys_are_the_keys_of_the_organizer(kind, file):
    expected = schema_keys(file)
    for name, _, gold in of_type(kind):
        assert all_keys(gold) == expected, name


def test_negatives_expect_empty_json():
    assert len(of_type("negative")) == 30
    assert all(g == {} for _, _, g in of_type("negative"))


def test_przelew_formats():
    for name, text, g in of_type("przelew"):
        p = g["przelew_bankowy"]
        assert re.fullmatch(r"\d{26}", p["na_rachunek"]) and re.fullmatch(r"\d{26}", p["z_rachunku"]), name
        assert isinstance(p["kwota"], float) and p["kwota"] > 0, name
        assert re.fullmatch(r"20\d\d-\d\d-\d\d", p["data_operacji"]), name
        digits = re.sub(r"\D", "", text)
        assert p["na_rachunek"] in digits and p["z_rachunku"] in digits, name
        assert norm(p["tytul"]) in norm(text), name
        assert p["numer_transakcji"] is None or p["numer_transakcji"] in text, name


def test_pelnomocnictwo_formats():
    for name, text, g in of_type("pelnomocnictwo"):
        assert g["mocodawca"] and g["pelnomocnicy"], name
        for a in g["pelnomocnicy"]:
            assert a["pesel"] is None or re.fullmatch(r"\d{11}", a["pesel"]), name
            assert a["pesel"] is None or a["pesel"] in text, name
            assert a["imie_nazwisko"] and len(a["imie_nazwisko"].split()) == 2, name
        for m in g["mocodawca"]:
            assert m["data"]["typ"] in ("osoba_prawna", "osoba_fizyczna"), name
            assert m["podpisujacy"], name
            assert (m["data"]["typ"] == "osoba_fizyczna") == (
                m["data"]["imie_nazwisko"] is not None
            ) or "/pl_5/" in name, name
            assert m["data"]["nip"] in text, name
            assert norm(m["data"]["nazwa"]) in norm(text), name
            for s in m["podpisujacy"]:
                assert s["imie_nazwisko"] in text, name


def test_odwolanie_formats():
    for name, text, g in of_type("odwolanie"):
        o = g["OdwolanieKIO"]
        assert isinstance(o["czynnosc_powod_id"], int) and 1 <= o["czynnosc_powod_id"] <= 12, name
        assert o["czynnosc_opis"] == CODES[o["czynnosc_powod_id"]], name
        assert re.fullmatch(r"20\d\d-\d\d-\d\d", o["czynnosc_dzien"]), name
        assert (o["data"] is None) == (o["miejscowosc"] is None), name
        z = g["ZamowieniePubliczne"]
        assert z["numer_bzp"] is None or re.fullmatch(r"\d{4}/BZP\d{8}(/\d{2})?", z["numer_bzp"]), name
        assert z["numer_ted"] is None or re.fullmatch(r"\d{6}-\d{4}", z["numer_ted"]), name
        assert norm(z["tytul"]) in norm(text), name
        assert len(g["Odwolujacy"]) == 1, name
        for p in g["Odwolujacy"] + g["Zamawiajacy"]:
            assert norm(p["nazwa"]) in norm(text), name
            for k in ("krs", "nip", "regon"):
                assert p[k] is None or p[k] in text, name
        w = g["Odwolujacy"][0]
        assert w["przez-pelnomocnika"] in (0, 1), name
        assert (w["pelnomocnik"]["imie_nazwisko"] is not None) == (w["przez-pelnomocnika"] == 1), name
        flags = [x["prowadzacy_postepowanie"] for x in g["Zamawiajacy"]]
        if len(flags) == 1:
            assert flags == [None], name
        else:
            assert sorted(flags) == [0, 1], name


def test_odwolanie_has_all_codes_and_headers():
    docs = generate(120, 2, types=["odwolanie"])
    assert {g["OdwolanieKIO"]["czynnosc_powod_id"] for _, _, g in docs} == set(CODES)
    assert any(g["OdwolanieKIO"]["data"] is None for _, _, g in docs)
    assert any(len(g["Zamawiajacy"]) == 2 for _, _, g in docs)
