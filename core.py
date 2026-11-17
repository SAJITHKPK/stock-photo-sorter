"""Core logic for Stock Photo Sorter (no GUI imports, fully testable)."""
from __future__ import annotations

import csv
import difflib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"}

NAME_HEADERS = {"product", "productname", "product name", "item", "itemname", "item name",
                "name", "article", "articlename", "article name", "description", "particulars"}
QTY_HEADERS = {"stock", "qty", "quantity", "balance", "closing", "closing stock",
               "available", "on hand", "stock qty", "stockqty"}


def normalize(name: str) -> str:
    """Case/spacing/punctuation-insensitive key for a product or file name."""
    s = str(name).strip()
    s = re.sub(r"\.(jpe?g|png|webp|gif|bmp|tiff?|heic)$", "", s, flags=re.I)
    s = re.sub(r"[_\-.]+", " ", s)
    s = re.sub(r"[^\w\s]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip().lower()


@dataclass
class StockRow:
    name: str
    qty: float | None = None  # None = no quantity info (treated as in stock)

    @property
    def in_stock(self) -> bool:
        return self.qty is None or self.qty > 0


def _to_number(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _rows_from_table(table: list[list]) -> list[StockRow]:
    table = [r for r in table if any(c not in (None, "") for c in r)]
    if not table:
        return []
    header = [normalize(c) if c is not None else "" for c in table[0]]
    name_i = next((i for i, h in enumerate(header) if h in NAME_HEADERS), None)
    qty_i = next((i for i, h in enumerate(header) if h in QTY_HEADERS), None)
    has_header = name_i is not None or qty_i is not None
    body = table[1:] if has_header else table
    if name_i is None:
        name_i = 0 if qty_i != 0 else 1
    if qty_i is None:
        # Guess: first other column that holds numbers
        for i in range(len(table[0])):
            if i != name_i and any(_to_number(r[i] if i < len(r) else None) is not None for r in body):
                qty_i = i
                break
    out: list[StockRow] = []
    for r in body:
        raw = r[name_i] if name_i < len(r) else None
        if raw is None or str(raw).strip() == "":
            continue
        qty = _to_number(r[qty_i]) if qty_i is not None and qty_i < len(r) else None
        out.append(StockRow(str(raw).strip(), qty))
    return out


def read_stock(path: str | Path) -> list[StockRow]:
    """Read product names (+ optional stock quantity) from .xlsx / .csv / .txt."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        wb = load_workbook(p, read_only=True, data_only=True)
        try:
            ws = wb.active
            table = [list(r) for r in ws.iter_rows(values_only=True)]
        finally:
            wb.close()
        return _rows_from_table(table)
    if ext in (".csv", ".txt", ".tsv"):
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        if ext == ".txt" and "," not in text and "\t" not in text:
            return [StockRow(l.strip()) for l in text.splitlines() if l.strip()]
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        return _rows_from_table(list(csv.reader(text.splitlines(), dialect)))
    raise ValueError(f"Unsupported stock file type: {ext or p.name} (use .xlsx, .csv or .txt)")


def scan_images(folder: str | Path, recursive: bool = False) -> dict[str, list[Path]]:
    """Map normalized image name -> image paths (several if different extensions)."""
    root = Path(folder)
    it = root.rglob("*") if recursive else root.glob("*")
    index: dict[str, list[Path]] = {}
    for f in sorted(it):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS and not f.name.startswith("."):
            index.setdefault(normalize(f.stem), []).append(f)
    return index


@dataclass
class MatchResult:
    row: StockRow
    status: str  # "found" | "close" | "missing" | "out_of_stock"
    files: list[Path] = field(default_factory=list)
    suggestion: str = ""


def match(rows: list[StockRow], index: dict[str, list[Path]], cutoff: float = 0.88) -> list[MatchResult]:
    results: list[MatchResult] = []
    seen: set[str] = set()
    keys = list(index)
    for row in rows:
        key = normalize(row.name)
        if key in seen:
            continue
        seen.add(key)
        if not row.in_stock:
            results.append(MatchResult(row, "out_of_stock"))
        elif key in index:
            results.append(MatchResult(row, "found", index[key]))
        else:
            close = difflib.get_close_matches(key, keys, n=1, cutoff=cutoff)
            if close:
                files = index[close[0]]
                results.append(MatchResult(row, "close", files, files[0].stem))
            else:
                results.append(MatchResult(row, "missing"))
    return results


def transfer(results: list[MatchResult], dest: str | Path, move: bool = False,
             include_close: bool = False) -> tuple[int, list[str]]:
    """Copy/move matched images into dest. Returns (files_done, errors)."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    done, errors = 0, []
    for r in results:
        if r.status == "found" or (r.status == "close" and include_close):
            for f in r.files:
                try:
                    target = dest / f.name
                    if move:
                        shutil.move(str(f), str(target))
                    else:
                        shutil.copy2(f, target)
                    done += 1
                except OSError as e:
                    errors.append(f"{f.name}: {e}")
    return done, errors


def unmatched(results: list[MatchResult], include_close: bool = False) -> list[MatchResult]:
    """In-stock items for which no photo was (or will be) shared."""
    return [r for r in results if r.status == "missing" or (r.status == "close" and not include_close)]


def write_report(items: list[MatchResult], path: str | Path) -> None:
    """Write a CSV error report of items without photographs."""
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Product", "Stock", "Issue", "Closest photo name"])
        for r in items:
            issue = "No photo found" if r.status == "missing" else "Only a similar photo name found"
            w.writerow([r.row.name, "" if r.row.qty is None else f"{r.row.qty:g}", issue, r.suggestion])
