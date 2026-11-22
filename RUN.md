# Run

Run this command in the folder `/opt/solution`:

```bash
docker compose run --rm cli
```

The command reads all PDF files in `input/` and writes one JSON file for each PDF file to `output/`. It stops when all files are processed.

- The application uses no external service and no API key. It needs no internet.
- The Docker image contains the OCR models. To make the image again, run `docker compose build cli`.
