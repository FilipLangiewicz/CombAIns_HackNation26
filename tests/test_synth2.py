import json
import re
from pathlib import Path

import pytest

from odw2json.synth2 import CODES, generate

ORG = Path(__file__).resolve().parents[1] / "docs" / "task" / "organizer" / "oczekiwane-json"
DATA = generate(14, 3)


def keys(o):
    if isinstance(o, dict):
        return {k: keys(v) for k, v in o.items()}
    if isinstance(o, list):
        return [keys(o[0])] if o else []
    return None


def schema(name):
    text = re.sub(r"//.*", "", (ORG / name).read_text(encoding="utf-8"))
    text = re.sub(r'(?<=")\s*\n\s*(?=")', ",\n", text)
    text = text.replace('"pesel": 85120133547', '"pesel": null')
    return keys(json.loads(re.sub(r",(\s*[}\]])", r"\1", text)))


def squash(s):
    return re.sub(r"[\s \-]", "", s)


def present(value, text, flat, kind=None):
    if isinstance(value, float):
        return True
    v = str(value)
    if v in text or squash(v) in flat:
        return True
    if kind == "name":
        return all(w[: max(2, len(w) - 3)] in text for w in v.split())
    return " ".join(v.split()) in " ".join(text.split())


def leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, k)
    elif isinstance(o, list):
        for v in o:
            yield from leaves(v, path)
    else:
        yield path, o


def test_counts_and_determinism():
    assert len(DATA) == 56
    assert DATA == generate(14, 3)
    assert len({n.split("/")[1] for n, _, _ in DATA if n.startswith("odwolanie")}) >= 5
    assert len({n.split("/")[1] for n, _, _ in DATA if n.startswith("przelew")}) >= 5
    assert len({n.split("/")[1] for n, _, _ in DATA if n.startswith("pelnomocnictwo")}) >= 5
    assert len({n.split("/")[1] for n, _, _ in DATA if n.startswith("negatyw")}) >= 5


@pytest.mark.parametrize("name,text,gold", DATA, ids=[d[0] for d in DATA])
def test_gold(name, text, gold):
    kind = name.split("/")[0]
    if kind == "negatyw":
        assert gold == {}
        return
    top = {"odwolanie": "OdwolanieKIO", "pelnomocnictwo": "mocodawca", "przelew": "przelew_bankowy"}[kind]
    ref = schema({"odwolanie": "odwolanie.json", "pelnomocnictwo": "pelnomocnictwo.json", "przelew": "przelew.json"}[kind])
    assert set(gold) == set(ref)
    assert top in gold
    flat = squash(text)
    for path, v in leaves(gold):
        if v is None:
            continue
        if path == "czynnosc_opis":
            assert v in CODES.values()
        elif path == "czynnosc_powod_id":
            assert CODES[v] == gold["OdwolanieKIO"]["czynnosc_opis"]
        elif path in ("data", "czynnosc_dzien", "data_operacji") and re.fullmatch(r"\d{4}-\d\d-\d\d", str(v)):
            y, m, d = v.split("-")
            assert any(s in text for s in (v, f"{d}.{m}.{y}", f"{int(d)}.{int(m)}.{y}", f"{d}-{m}-{y}")) or f"{int(d)} " in text
        elif path in ("prowadzacy_postepowanie", "przez-pelnomocnika", "typ"):
            continue
        elif path == "numer_bzp":
            assert re.fullmatch(r"\d{4}/BZP\d{8}(/\d\d)?", v)
            assert squash(v) in flat
        elif path == "numer_ted":
            assert re.fullmatch(r"\d{6}-\d{4}", v) and v.split("-")[0] in text
        elif path in ("na_rachunek", "z_rachunku"):
            assert re.fullmatch(r"\d{26}", v) and v in flat
        elif path == "pesel":
            assert re.fullmatch(r"\d{11}", v) and v in text
        elif path == "kwota":
            assert isinstance(v, float)
        else:
            assert present(v, text, flat, "name" if path == "imie_nazwisko" else None), (path, v)
    if kind == "odwolanie":
        o = gold["OdwolanieKIO"]
        assert (o["data"] is None) == (o["miejscowosc"] is None)
        assert gold["Odwolujacy"][0]["przez-pelnomocnika"] in (0, 1)
        leads = [z["prowadzacy_postepowanie"] for z in gold["Zamawiajacy"]]
        assert (leads == [None]) if len(leads) == 1 else set(leads) <= {0, 1}
    if kind == "przelew":
        assert isinstance(gold["przelew_bankowy"]["kwota"], float)
