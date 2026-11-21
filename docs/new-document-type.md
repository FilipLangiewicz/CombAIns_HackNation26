# Add a new document type

This file tells how to add a new document type or a new field without a change of the code. The test `tests/test_new_type.py` reads the example below and checks that it operates.

## How it works

- Each file `config/types/*.yaml` is one document type.
- The application reads all files in this folder at the start.
- The key `classify` gives the rules that find the type (see `docs/classification.md`).
- The key `template` gives the empty JSON structure of the output.
- The key `fields` gives the rules that find the values. The extractor `generic` uses only these rules.

## Procedure

To add a new type, do these steps:

1. Make a new file in `config/types/`, for example `config/types/faktura.yaml`.
2. Write the keys `name`, `label`, `order` and `extractor: generic`.
3. Write the `classify` rules: one rule for the title with the weight 4, and some rules for other words with the weight 1.
4. Write the `template` with all output fields and the value `null`.
5. Write one rule in `fields` for each output field.
6. Put an example PDF into `input/test/` and run `python main.py`.
7. Look at the JSON file in `output/test/`. Also look at the evidence in the web interface (`python main.py --gui`).

## Field rules

| Key | Content |
|---|---|
| `path` | The place of the value in the JSON, with dots, for example `faktura.kwota`. |
| `kind` | The kind of value: `text`, `date`, `amount`, `account`, `nip`, `krs`, `regon`, `pesel`, `email`, `number` or `regex`. |
| `labels` | A list of regular expressions. The value comes after the first label that occurs in the text. |
| `pattern` | Only for `kind: regex`: a regular expression with one group. The group is the value. |
| `override` | Only for a type with its own extractor: if `true`, the rule replaces the value of the extractor. |

The kind `text` gives the rest of the line after the label. If the line has no text after the label, the kind `text` gives the next line.

## Example: an invoice

```yaml
name: faktura
label: Faktura VAT
order: 4
extractor: generic

classify:
  head_chars: 800
  min_score: 5
  rules:
    - {pattern: '^\s*FAKTURA(\s+VAT)?\b', weight: 4, where: head}
    - {pattern: 'sprzedawca', weight: 1}
    - {pattern: 'nabywca', weight: 1}

template:
  faktura: {numer: null, data_wystawienia: null, nip_sprzedawcy: null, kwota_brutto: null, rachunek: null}

fields:
  - {path: faktura.numer, kind: regex, pattern: 'Faktura(?:\s+VAT)?\s+nr\s+(\S+)'}
  - {path: faktura.data_wystawienia, kind: date, labels: ['data\s+wystawienia']}
  - {path: faktura.nip_sprzedawcy, kind: nip, labels: ['sprzedawca[\s\S]{0,120}?(?=NIP)']}
  - {path: faktura.kwota_brutto, kind: amount, labels: ['razem\s+brutto', 'do\s+zapłaty']}
  - {path: faktura.rachunek, kind: account, labels: ['rachunek', 'konto']}
```

## Validation of the fields

The key `validate` of a type gives the rules that check the values after the extraction. The code is in `src/odw2json/validate.py`.

| Key | Content |
|---|---|
| `path` | The field. `[]` means each item of a list, for example `Odwolujacy[].nip`. |
| `kind` | `digits`, `date`, `email`, `amount` or `regex`. |
| `lengths` | For `digits`: the allowed numbers of digits, for example `[9, 14]`. |
| `pattern` | For `regex`: the value must match it completely. |
| `checksum` | For `digits`: `nip`, `regon` or `pesel`. It is optional, because the example data is synthetic. |

- For `digits`, the typical OCR errors are repaired first, for example "O" becomes "0".
- A value that is not valid becomes `null`. The result gets a warning with the reason.

Example:

```yaml
validate:
  - {path: "Odwolujacy[].nip", kind: digits, lengths: [10]}
  - {path: "przelew_bankowy.data_operacji", kind: date}
```

## Add a field to a known type

To add a field to `odwolanie`, `pelnomocnictwo` or `przelew`, do these steps:

1. Add the field to the `template` of the type.
2. Add a rule for the field in the key `fields` of the type.

The dedicated extractor of the type fills its own fields. Then the application applies the rules in `fields`.

## Test the configuration in another folder

To test a new configuration without a change of `config/types/`, set the environment variable `ODW2JSON_CONFIG_DIR`:

```bash
ODW2JSON_CONFIG_DIR=/path/to/types python main.py
```
