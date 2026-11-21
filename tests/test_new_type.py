"""A new type from the configuration only: the example in docs/new-document-type.md must operate."""

import re
import shutil
from pathlib import Path

import yaml

from odw2json.classify import CONFIG_DIR, classify, load_types
from odw2json.extractors import extract

DOC = Path(__file__).resolve().parents[1] / "docs" / "new-document-type.md"

INVOICE = """FAKTURA VAT
Faktura VAT nr FV/123/2026
Data wystawienia: 14.05.2026
Sprzedawca:
Alfa Serwis sp. z o.o.
ul. Długa 5, 00-001 Warszawa
NIP: 525-000-12-34
Nabywca:
Beta S.A.
Razem brutto: 1 230,00 PLN
Rachunek: PL61 1090 1014 0000 0712 1981 2874
"""


def example_yaml() -> str:
    return re.search(r"```yaml\n(.*?)```", DOC.read_text(encoding="utf-8"), re.DOTALL).group(1)


def types_with_example(tmp_path: Path):
    for path in CONFIG_DIR.glob("*.yaml"):
        shutil.copy(path, tmp_path)
    (tmp_path / "faktura.yaml").write_text(example_yaml(), encoding="utf-8")
    return load_types(tmp_path)


def test_new_type_from_configuration(tmp_path):
    types = types_with_example(tmp_path)
    found = classify(INVOICE, types)
    assert found.doc_type is not None and found.doc_type.name == "faktura"
    data, evidence = extract(INVOICE, found.doc_type)
    assert data == {
        "faktura": {
            "numer": "FV/123/2026",
            "data_wystawienia": "2026-05-14",
            "nip_sprzedawcy": "5250001234",
            "kwota_brutto": 1230.0,
            "rachunek": "61109010140000071219812874",
        }
    }
    assert set(evidence) == {f"faktura.{k}" for k in data["faktura"]}


def test_new_type_does_not_change_the_known_types(tmp_path):
    types = types_with_example(tmp_path)
    assert [t.name for t in types] == [t.name for t in load_types()] + ["faktura"]
    template = yaml.safe_load(example_yaml())["template"]
    assert template["faktura"]["numer"] is None
