import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import core


def mk(tmp, names):
    for n in names:
        (tmp / n).write_bytes(b"x")


def test_normalize():
    assert core.normalize("Blue_Shirt-XL.JPG") == "blue shirt xl"
    assert core.normalize("  Red   Dress ") == "red dress"


def test_read_csv_with_header_and_qty(tmp_path):
    f = tmp_path / "s.csv"
    f.write_text("Product,Qty\nBlue Shirt,5\nRed Dress,0\nGreen Hat,\n")
    rows = core.read_stock(f)
    assert [(r.name, r.qty) for r in rows] == [("Blue Shirt", 5), ("Red Dress", 0), ("Green Hat", None)]
    assert [r.in_stock for r in rows] == [True, False, True]


def test_read_xlsx_no_header(tmp_path):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["Blue Shirt", 3]); ws.append(["Red Dress", 0])
    f = tmp_path / "s.xlsx"; wb.save(f)
    rows = core.read_stock(f)
    assert [(r.name, r.qty) for r in rows] == [("Blue Shirt", 3), ("Red Dress", 0)]


def test_read_txt_names_only(tmp_path):
    f = tmp_path / "s.txt"; f.write_text("A\nB\n")
    assert [r.name for r in core.read_stock(f)] == ["A", "B"]


def test_match_and_transfer_copy(tmp_path):
    photos, out = tmp_path / "p", tmp_path / "o"; photos.mkdir()
    mk(photos, ["Blue Shirt.jpg", "red_dress.PNG", "Green Hat.jpg", "Grren Hat2.txt", "Yellow Scarf.jpg"])
    rows = [core.StockRow("blue shirt", 4), core.StockRow("Red Dress", 0), core.StockRow("Green Hatt", 2),
            core.StockRow("Purple Sock", 1), core.StockRow("BLUE SHIRT", 9)]
    res = core.match(rows, core.scan_images(photos))
    st = {r.row.name: r.status for r in res}
    assert st == {"blue shirt": "found", "Red Dress": "out_of_stock", "Green Hatt": "close", "Purple Sock": "missing"}
    n, err = core.transfer(res, out)
    assert n == 1 and not err and (out / "Blue Shirt.jpg").exists() and (photos / "Blue Shirt.jpg").exists()
    n, _ = core.transfer(res, out, include_close=True)
    assert (out / "Green Hat.jpg").exists()


def test_transfer_move(tmp_path):
    photos, out = tmp_path / "p", tmp_path / "o"; photos.mkdir()
    mk(photos, ["a.jpg", "a.png"])
    res = core.match([core.StockRow("a", 1)], core.scan_images(photos))
    n, _ = core.transfer(res, out, move=True)
    assert n == 2 and not (photos / "a.jpg").exists() and (out / "a.png").exists()


def test_unmatched_and_report(tmp_path):
    photos = tmp_path / "p"; photos.mkdir(); mk(photos, ["Green Hat.jpg"])
    res = core.match([core.StockRow("Green Hatt", 2), core.StockRow("Sock", 1), core.StockRow("X", 0)],
                     core.scan_images(photos))
    assert [r.row.name for r in core.unmatched(res)] == ["Green Hatt", "Sock"]
    assert [r.row.name for r in core.unmatched(res, include_close=True)] == ["Sock"]
    core.write_report(core.unmatched(res), tmp_path / "r.csv")
    txt = (tmp_path / "r.csv").read_text(encoding="utf-8-sig")
    assert "Sock,1,No photo found" in txt and "Green Hat" in txt
