# Extraction rules

This file tells how the application extracts the data from a document after the classification. The application uses rules, not an LLM.

## General principles

- Each type has one extractor in `src/odw2json/extractors/`. The words and the labels are in `config/types/<type>.yaml`, not in the code.
- An extractor uses anchors: labels ("Kwota", "NIP"), section names ("Odwołujący:", "Zamawiający:") and titles of persons ("r. pr.", "adw.").
- Values with a fixed form (NIP, KRS, REGON, PESEL, account number, date, amount, e-mail) come from regular expressions in `src/odw2json/common.py`.
- Each extractor records the source text of each value (evidence). The web interface shows it next to the value.
- If a rule finds no value, the field is `null`. The application does not invent values.

## Common normalization

| Value | Rule | Example |
|---|---|---|
| Date | Formats `DD.MM.YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, a Polish month name, a Roman month. Output in ISO. | "20 marca 2026 r." → `2026-03-20` |
| Amount | Spaces or dots between thousands, a comma or a dot before the decimal part. | "1 234,50 zł" → `1234.5` |
| Account | 26 digits, with or without "PL" and spaces. Output without "PL". | "PL05 4706 …" → `05470680…` |
| NIP, KRS, REGON | The digits after the label. Hyphens and spaces are removed. | "NIP: 123-456-32-18" → `1234563218` |
| Name of a person | Titles are removed. A name in another case goes to the nominative (see below). | "r. pr. Jana Kowalskiego" → `Jan Kowalski` |

## Payment confirmation (`przelew`)

The code is in `extractors/przelew.py`. The labels are in the key `labels` of `przelew.yaml`.

1. The text is split into lines. Page markers ("Strona 1 z 2") and rows of dots are removed.
2. For each field, the extractor finds the first label of its list. The value is the rest of the line, the rest joined with the next line, or the next line.
3. The date of the operation has priority levels: "data operacji/realizacji/wykonania", then "w dniu", then "data zlecenia/księgowania". The date of the print ("wydrukowano", "wygenerowano") is not used.
4. The two accounts get their role from the nearest keyword before each account: "nadawca", "obciążany", "z rachunku" for the sender, and "odbiorca", "beneficjent", "na rachunek" for the recipient.
5. The title ends at the reference number, at the end quote, or at a line that starts with a label word ("Status", "Kwota", …).

## Power of attorney (`pelnomocnictwo`)

The code is in `extractors/pelnomocnictwo.py`. The words are in the key `extract` of `pelnomocnictwo.yaml`.

1. **Attorneys:** a professional title ("adw.", "r. pr.", "radca prawny", "apl.") and a name after it. A name that occurs two times (in the text and in the block "Pełnomocnictwo przyjmuję") is kept once.
2. **Principals:** each group of identifiers (KRS, NIP, REGON) near each other is one company. Thus a consortium gives more than one principal. The name of the company is the text before the group that ends with a legal form ("sp. z o.o.", "S.A.", "sp. k.").
3. **Natural person:** a text such as "niżej podpisany X, prowadzący działalność pod firmą Y" gives `typ: osoba_fizyczna`.
4. **Signers:** a name with a role ("Prezes Zarządu", "Prokurent", "Członek Zarządu") on the same line or on the next line. In a consortium, a signer belongs to the company in the nearest "W imieniu X" before the signature.

## Appeal (`odwolanie`)

The code is in `extractors/odwolanie.py`. The action codes and their rules are in the keys `actions` and `action_rules` of `odwolanie.yaml`.

1. The text is joined into one line. Thus line breaks do not change the result.
2. **Parties:** the head of the document is split into the sections "Odwołujący", "Zamawiający" and "dotyczy". Each party is found from its group of identifiers. The name is the text between the previous boundary (a colon, a role or an e-mail) and the street.
3. **Consortium and more than one "Zamawiający":** the party marked "Lider" or "prowadzący" is the leader. `prowadzacy_postepowanie` is `null` if there is only one "Zamawiający".
4. **Attorney:** the first person after "reprezentowany przez". The firm of the attorney is the text after "adres do korespondencji". If there is no attorney, `przez-pelnomocnika` is 0.
5. **Town and date:** a line such as "Poznań, dnia 11.09.2026" in the head. If there is no such line, both fields are `null`.
6. **Action code (`czynnosc_powod_id`):** only the first charge is used. The extractor takes the text of the first charge and tests the keyword rules of each code in `action_rules`. The description comes from the list `actions` without a change.
7. **Procurement:** the title in quotes after "pn.", the reference number after "nr referencyjny", BZP and TED numbers in their normalized forms.

## Names in the nominative

The organizer wants names in the nominative ("Mateusz Szymański", not "Mateusza Szymańskiego").

- The conversion applies only after words that require another case, for example "reprezentowanego przez" or "udzielam pełnomocnictwa Panu".
- Surnames: endings such as "-skiego" → "-ski" and "-skiej" → "-ska".
- First names: lists of male and female first names in `pelnomocnictwo.yaml` and a list of irregular forms ("Marka" → "Marek").
- A name that is not in the lists stays as it is in the text.

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
