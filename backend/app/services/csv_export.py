import csv
import io
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime

from fastapi.responses import StreamingResponse

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
SYNTHETIC_LABEL = "# SYNTHETIC DEMO DATA - not real people, facilities or inventory"


def safe_cell(value: object) -> str:
    """Render a value for CSV, neutralising spreadsheet formula injection."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool | int | float):
        return str(value)
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def build_csv(header: Sequence[str], rows: Iterable[Sequence[object]], synthetic: bool) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    if synthetic:
        buf.write(SYNTHETIC_LABEL + "\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([safe_cell(v) for v in row])
    return buf.getvalue()


def csv_response(filename: str, header: Sequence[str], rows: Iterable[Sequence[object]], synthetic: bool) -> StreamingResponse:
    body = build_csv(header, rows, synthetic)
    name = filename.replace(".csv", "_SYNTHETIC_DEMO.csv") if synthetic else filename
    return StreamingResponse(
        iter([body]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"},
    )
