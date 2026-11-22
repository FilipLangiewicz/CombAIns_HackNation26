"""A local web interface: upload PDF files, see the PDF and the extracted JSON side by side."""

from __future__ import annotations

import importlib
import json
import re
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from odw2json import ocr, pdftext
from odw2json.classify import CONFIG_DIR, classify, load_types
from odw2json.pipeline import process_pdf

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD = 100 * 1024 * 1024


def type_info() -> dict[str, dict]:
    """The label and the minimum score of each type, read from config/types."""
    return {t.name: {"label": t.label, "min_score": t.min_score} for t in load_types()}


def pipeline_info() -> dict:
    """The steps of the pipeline and the rules of each type, read from the code and from config/types.

    The page /graph shows only these values, so the configuration stays the one source of the rules.
    """
    types = []
    for t in load_types():
        module = importlib.import_module(f"odw2json.extractors.{t.extractor}")
        path = CONFIG_DIR / f"{t.name}.yaml"
        types.append(
            {
                "name": t.name,
                "label": t.label,
                "extractor": t.extractor,
                "extractor_doc": (module.__doc__ or "").strip(),
                "min_score": t.min_score,
                "head_chars": t.head_chars,
                "title_weight": t.title_weight,
                "config": t.raw,
                "yaml": path.read_text(encoding="utf-8") if path.exists() else "",
                "file": f"config/types/{t.name}.yaml",
            }
        )
    return {
        "min_page_chars": pdftext.MIN_PAGE_CHARS,
        "max_ocr_pages": pdftext.MAX_OCR_PAGES,
        "ocr_dpi": ocr.DPI,
        "ocr_retry_dpi": ocr.RETRY_DPI,
        "ocr_available": ocr.available(),
        "types": types,
    }


def normalize_path(key: str) -> str:
    """Write a path of the evidence in the form a.b.0.c, as the page builds it."""
    key = re.sub(r"\[(\d+)\]", r".\1", key)
    return key.replace("/", ".").strip(".")


class Session:
    """The uploaded files and their results. The files stay in a temp folder until the server stops."""

    def __init__(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="odw2json_"))
        self.docs: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.counter = 0

    def add(self, name: str, content: bytes) -> dict:
        with self.lock:
            self.counter += 1
            doc_id = str(self.counter)
        path = self.folder / f"{doc_id}.pdf"
        path.write_bytes(content)
        try:
            result = process_pdf(path)
            info = type_info()
            doc = {
                "doc_type": result.doc_type,
                "type_label": info[result.doc_type]["label"] if result.doc_type else "Nieznany typ",
                "types": info,
                "hits": classify(result.text).hits if result.text else {},
                "text": result.text,
                "data": result.data,
                "evidence": {normalize_path(k): v for k, v in result.evidence.items()},
                "scores": result.scores,
                "ocr_pages": result.ocr_pages,
                "ocr_missing": result.ocr_missing,
                "page_count": result.page_count,
                "ocr_retry": result.ocr_retry,
                "skipped_pages": result.skipped_pages,
                "warnings": result.warnings,
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001 - a bad file must not stop the server.
            doc = {
                "doc_type": None,
                "type_label": "Nieznany typ",
                "types": {},
                "hits": {},
                "text": "",
                "data": {},
                "evidence": {},
                "scores": {},
                "ocr_pages": [],
                "ocr_missing": False,
                "page_count": 0,
                "ocr_retry": False,
                "skipped_pages": [],
                "warnings": [],
                "error": str(exc),
            }
        doc.update(id=doc_id, name=name, pdf_url=f"/pdf/{doc_id}")
        self.docs[doc_id] = doc
        return doc

    def close(self) -> None:
        shutil.rmtree(self.folder, ignore_errors=True)


def make_handler(session: Session) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def send_bytes(self, status: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: int, payload: object) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_bytes(status, body, "application/json; charset=utf-8")

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                self.send_bytes(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif path in ("/graph", "/rules"):
                self.send_bytes(200, (STATIC / "graph.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/pipeline":
                self.send_json(200, pipeline_info())
            elif path == "/api/docs":
                self.send_json(200, list(session.docs.values()))
            elif match := re.fullmatch(r"/pdf/(\d+)", path):
                pdf = session.folder / f"{match.group(1)}.pdf"
                if match.group(1) not in session.docs or not pdf.exists():
                    self.send_json(404, {"error": "Nie znaleziono pliku"})
                else:
                    self.send_bytes(200, pdf.read_bytes(), "application/pdf", {"Content-Disposition": "inline"})
            else:
                self.send_json(404, {"error": "Nie znaleziono"})

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if url.path != "/api/analyze":
                self.send_json(404, {"error": "Nie znaleziono"})
                return
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_UPLOAD:
                self.send_json(400, {"error": "Niepoprawny rozmiar pliku"})
                return
            name = unquote(parse_qs(url.query).get("name", ["dokument.pdf"])[0])
            content = self.rfile.read(length)
            if not content.startswith(b"%PDF"):
                self.send_json(400, {"error": "To nie jest plik PDF"})
                return
            self.send_json(200, session.add(Path(name).name, content))

    return Handler


def serve(port: int = 8000, host: str = "127.0.0.1") -> None:
    session = Session()
    server = ThreadingHTTPServer((host, port), make_handler(session))
    print(f"GUI: http://{host}:{port}  (Ctrl+C stops the server)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        session.close()
