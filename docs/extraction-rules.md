# Extraction rules

This file tells how the application extracts the data from a document after the classification. The application uses rules, not an LLM.

## General principles

- Each type has one extractor in `src/odw2json/extractors/`. The words and the labels are in `config/types/<type>.yaml`, not in the code.
- An extractor uses anchors: labels ("Kwota", "NIP"), section names ("Odwołujący:", "Zamawiający:") and titles of persons ("r. pr.", "adw.").
- Values with a fixed form (NIP, KRS, REGON, PESEL, account number, date, amount, e-mail) come from regular expressions in `src/odw2json/common.py`.
- Each extractor records the source text of each value (evidence), under the path of the value, for example `Odwolujacy[0].nip` or `mocodawca[1].data.krs`. The web interface shows it next to the value.
- Each value that is not `null` has an evidence entry. A test checks this for all dev documents (`tests/test_evidence.py`). The test also checks that the source text occurs in the text of the document.
- If a rule finds no value, the field is `null`. The application does not invent values.

## Common normalization

| Value | Rule | Example |
|---|---|---|
| Date | Formats `DD.MM.YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, a Polish month name, a Roman month. Output in ISO. | "20 marca 2026 r." → `2026-03-20` |
| Amount | Spaces or dots between thousands, a comma or a dot before the decimal part. | "1 234,50 zł" → `1234.5` |
| Account | 26 digits, with or without "PL" and spaces. Output without "PL". | "PL05 4706 …" → `05470680…` |
| NIP, KRS, REGON | The digits after the label. Hyphens and spaces are removed. | "NIP: 123-456-32-18" → `1234563218` |
| Name of a person | Titles are removed. Some names in another case go to the nominative (see below). | "r. pr. Jana Kowalskiego" → `Jan Kowalski` |

## Payment confirmation (`przelew`)

The code is in `extractors/przelew.py`. The labels are in the key `labels` of `przelew.yaml`.

1. **Preparation:** the text is split into lines. Page markers ("Strona 1 z 2", "1/2") and lines of only "-", "=" or "_" are removed. A row of dots between a label and a value becomes a colon.
2. **Label and value:** for each field, the extractor tests the labels of its list in their order. The value is the rest of the line, the rest joined with the next line, or the next line. The first text that gives a correct value wins.
3. **`data_operacji`:** the labels have three priority levels: "data operacji/transakcji/realizacji/wykonania", then "w dniu", then "data zlecenia/księgowania/waluty". If no label gives a date, the first date on a line without "wydruk", "wygenerowano" or "sporządzono" wins.
4. **`kwota`:** a number with a decimal part or with "PLN" or "zł". A number without these signs is not an amount, because it can be a part of a date.
5. **`numer_transakcji`:** a word with a digit after "Nr ref.", "numer transakcji", "identyfikator" and similar labels. If no label gives a value, the first text "CEN" with 10 or more digits (key `fallback`).
6. **Accounts:** the extractor finds each account number (26 digits, with or without "PL" and spaces) in the full text. The role comes from the nearest keyword in the 250 characters before the account: `z_rachunku` ("nadawca", "obciążany", "płatnik", "z rachunku") or `na_rachunek` ("odbiorca", "beneficjent", "adresat", "na rachunek"). An account without a keyword gets the free role, in the order of the text.
7. **`tytul`:** the text after "Tytuł" or "Opis". The title ends at one of these places:
   - at the end quote, if the title starts with a quote,
   - after the reference number (`numer_transakcji`),
   - before a line that starts with a capital word from `stop` ("Status", "Kwota", "Data", …),
   - before a capital word from `stop_inline` inside the line, because a PDF reader can join two lines.

## Power of attorney (`pelnomocnictwo`)

The code is in `extractors/pelnomocnictwo.py`. The words are in the key `extract` of `pelnomocnictwo.yaml`: `titles`, `roles`, `legal_forms`, `stop_words`.

1. **Natural person:** if the text has "niżej podpisany <Name Surname>,", the principal is a natural person (`typ: osoba_fizyczna`). `nazwa` is the text after "pod firmą" up to the address. If there is no such text, `nazwa` is the name of the person. The person is also the signer.
2. **Companies:** if there is no natural person, each group of labelled identifiers (KRS, NIP, REGON) is one company (`typ: osoba_prawna`). A new group starts when a label repeats, after a ";", or after a gap of more than 150 characters. Groups with the same NIP (or KRS) are kept once. Thus a consortium gives more than one principal.
3. **Company name:** the extractor finds the last legal form (`legal_forms`, for example "sp. z o.o.", "S.A.") in the 220 characters before the group. The name is the words before the legal form that start with a capital letter or a digit. The search stops at a word in `stop_words` or at a word that ends with a punctuation mark. If there is no legal form, the name is the text after an anchor ("Mocodawca", "w imieniu", "Za", "1)") up to a comma, "KRS", "NIP" or "z siedzibą".
4. **Signers:** a name of two words with a role from `roles` ("Prezes Zarządu", "Prokurent", …) on the same line or on the next line. A name without a role is also a signer if it stands under a signature line (dots) and before the block "Pełnomocnictwo przyjmuję".
5. **Signers in a consortium:** a signer belongs to the company whose name occurs last in the text before the signature.
6. **Attorneys:** a professional title from `titles` ("adw.", "r. pr.", "radca prawny", "apl. adw.", …) and a name of two words after it. A name that occurs two times is kept once. `pesel` is the PESEL in the 90 characters after the name. If no title occurs, the extractor uses the name after "Pan", "Pani", "Panu", "Panią" or "Pełnomocnik".

## Appeal (`odwolanie`)

The code is in `extractors/odwolanie.py`. The action codes and their rules are in the keys `actions` and `action_rules` of `odwolanie.yaml`.

1. **Preparation:** the extractor joins titles with spaces between the letters, removes page markers ("Strona 1 z 2", "- 1 -", "1/2"), and joins the text into one line. Thus line breaks do not change the result.
2. **Head:** the head is the text before "Działając w imieniu", "wnoszę odwołanie" or "wnoszę o:". If there is no such text, the head is the first 4000 characters.
3. **Sections:** the labels "Odwołujący…:", "Zamawiający…:" and "Wykonawca wybrany…:" start the sections of the parties. The text after "dotyczy:" is the section of the procurement.
4. **Parties:** each group of identifiers (KRS, NIP, REGON) in a section is one party. The name is the text before the street ("ul.", "al.", "pl.", "os.") or before the postal code. The text before the last e-mail and before the last colon is not part of the name.
5. **Appellant:** if more than one party is in the section, the party with "lider" in its role wins. Else the first party wins.
6. **Attorney:** the first person after "reprezentowany/-a/-ego przez", without titles. If the word is "reprezentowanego", "reprezentowanej" or "reprezentowanych", the name goes to the nominative. The firm of the attorney (`nazwa`) is the text after "adres do korespondencji:" up to the street or the postal code. `mail` is the first e-mail after the attorney. If the text has no "reprezentowany przez", `przez-pelnomocnika` is 0 and `pelnomocnik` is `null`.
7. **Contracting authorities:** each party in the sections "Zamawiający". If there is more than one, `prowadzacy_postepowanie` is 1 for a party with "lider" or "prowadzący" in its role, and 0 for the others. If there is only one, the value is `null`.
8. **Town and date:** the first text "<Town>, (dnia) <date> (r.)" in the head. If a postal code stands before the town, the town is part of an address, and the extractor removes the first word. If no such text occurs, both fields are `null`.
9. **Text of the first charge:** the extractor collects these texts, from the most exact to the least exact:
   1. the text after "polegających na:" up to the item "2)",
   2. the sentence "Zamawiający w dniu … ." after "wnoszę o:",
   3. the first sentence "Zamawiający w dniu … .",
   4. the text after "Zarzut nr 1" up to "Zarzut nr 2".
10. **Action code (`czynnosc_powod_id`):** the extractor tests the rules of `action_rules` in their order on each text. The first rule that matches gives the code. The order is important: "zaniechanie unieważnienia" (10) comes before "unieważnienie" (9). `czynnosc_opis` is the text of the code in `actions`, without a change.
11. **Action date (`czynnosc_dzien`):** the date after "w dniu" or "z dnia" in the texts of step 9. If there is no such date, the first date in these texts.
12. **Procurement:** these rules apply to the section "dotyczy", or to the head if there is no such section:
    - `numer_bzp`: "YYYY/BZP ########" (with an optional "/NN"), written without spaces.
    - `numer_ted`: "YYYY/S ###-NNNNNN" or "NNNNNN-YYYY" after "TED" or "Dzienniku Urzędowym", written as "NNNNNN-YYYY".
    - `numer_postepowania`: the word after "nr referencyjny", "numer sprawy", "znak postępowania" and similar labels.
    - `tytul`: the text in quotes after "pn.". If there is none, the first text in quotes.

## Evidence

The evidence of a field is a short text from the document. It is the label with the value when a label exists, for example "NIP: 999-928-40-65".

| Field | Source text |
|---|---|
| Identifier (`krs`, `nip`, `regon`) | The label and the number, as written. |
| Name (`nazwa`, `imie_nazwisko`) | The name as written, with the title or the role when they stand next to it. A name in another case stays in that case, because it is the source. |
| `przelew` fields | The line of the label and the value. For a title on more lines, the lines of the title. |
| Account of `przelew` | The text from the keyword of the role ("Płatnik", "Beneficjent") to the account, at most 150 characters. |
| `czynnosc_powod_id`, `czynnosc_opis` | The words that match the rule of the action, with 60 characters on each side. |
| `czynnosc_dzien` | The text "w dniu <date>", or the first date with some text before it. |
| `przez-pelnomocnika` | The text "reprezentowany przez …". If it is absent, the first 100 characters of the section of the appellant. |
| `prowadzacy_postepowanie` | The role text of the party ("Lider", "Zamawiający prowadzący"). If the role is empty, the name of the party. |
| `typ` (`pelnomocnictwo`) | For a natural person, the text "niżej podpisany <Name>". For a company, the first identifier of its group. |
| `numer_bzp`, `numer_ted`, `numer_postepowania`, `tytul` | The text that the rule matches, as written. |

The text of `przelew` is read line by line. Thus a row of dots in the source is a colon in the evidence.

## Names in the nominative

The organizer wants names in the nominative ("Mateusz Szymański", not "Mateusza Szymańskiego"). One function does this: `common.to_nominative(name, first_names_masc, first_names_fem)`. The two lists are optional. If they are absent, the function reads them from `config/names.yaml` (one time, with `functools.cache`).

The extractors call the function in these places:

- `pelnomocnictwo`: for each name of a principal who is a natural person, of a signer and of an attorney.
- `odwolanie`: only for the attorney, and only after "reprezentowanego/-ej/-ych przez".

The rules of the function:

1. A name with less than two words does not change.
2. The first name gives the gender. If it is in a list, the name is nominative. Else the function removes a case suffix and tests the result in the lists. Examples: "Piotra" → "Piotr", "Marka" → "Marek", "Katarzynie" → "Katarzyna", "Annę" → "Anna".
3. For a male first name, a surname with the ending "-iego", "-iemu" or "-im" changes to "-i" ("Kowalskiego" → "Kowalski"). If the first name had a case suffix, the suffix of the surname is removed too ("Nowaka" → "Nowak").
4. For a female first name, the endings "-iej", "-ej" and "-ą" of the surname change to "-a" ("Nowickiej" → "Nowicka").
5. If the first name is not in the lists, only a surname that ends in "-skiego", "-ckiego", "-zkiego", "-skiemu", "-skim" and similar changes. Also "-skiej" and "-ską" change to "-ska". The first name does not change.
6. A name that is already nominative does not change. Thus "Jolanta Zajkowski" and "Bartosz Szymanski" stay as written, like in the expected JSON.

`config/names.yaml` has about 140 male and 125 female first names in the nominative. Add a name there if the application leaves its case unchanged.

## The risk of a too close fit to the examples

All 60 example cases come from one generator with about 15 layouts for each type. Thus the result F1 = 1.0 tells that the rules work for these layouts. It does not tell that the rules work for new layouts.

We use these measures against this risk:

1. **Holdout:** 15 cases are not used to write the rules (`config/split.json`). Because these cases have the same layouts, this check is weak.
2. **Robustness test:** `odw2json.perturb` changes the form of the text and keeps the values (formats of dates, NIP and accounts, line breaks, upper case, quotes, page markers). The result went from 0.87 to 1.00 after the robustness work.
3. **General anchors:** the rules use labels, sections and the form of values, not the position of a line or the exact text of one template.
4. **Safe failure:** if a rule finds no value, the field is `null`. A `null` gives a false negative only, not also a false positive.

Open items:

- A test with whole layouts held out (for example, one bank in the holdout only).
- New layouts from the organizer. The UZP stand shows examples of the test data.
- The 30 scans, which come from other layouts. They need OCR.
