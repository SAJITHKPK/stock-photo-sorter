import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unittest import mock
import app, core
root = Path(__file__).resolve().parent.parent / "sample"
out = tempfile.mkdtemp()
app.CONFIG = Path(tempfile.mkdtemp()) / "c.json"
with mock.patch.object(app.messagebox, "askyesno", return_value=True), \
     mock.patch.object(app.messagebox, "showinfo") as info, \
     mock.patch.object(app, "open_folder"):
    a = app.App(); a.update()
    a.photos_var.set(str(root/"photos")); a.stock_var.set(str(root/"stock.xlsx")); a.out_var.set(out)
    a.preview(); a.update()
    assert len(a.tree.get_children()) == 5, a.tree.get_children()
    assert str(a.go_btn["state"]) == "normal"
    a.close_var.set(True); a._refresh_summary()
    print(a.summary["text"])
    seen = {}
    def fake_dialog(msg, missing, dest):
        seen["m"] = [r.row.name for r in missing]
        core.write_report(missing, Path(out) / "rep.csv")
    a._done_dialog = fake_dialog
    a.run(); a.update()
    assert seen["m"] == ["Purple Sock"], seen
    print((Path(out) / "rep.csv").read_text(encoding="utf-8-sig"))
    got = sorted(p.name for p in Path(out).rglob("*.*") if p.suffix != ".csv")
    print(got); assert got == ["Black Shoes.jpeg", "Blue Shirt.jpg", "Green Hat.jpg"], got
    if len(sys.argv) > 1:
        a.geometry("+80+80"); a.update(); a.lift()
        import subprocess; subprocess.run(["screencapture", "-x", sys.argv[1]])
    a.destroy()
print("GUI SMOKE OK")
