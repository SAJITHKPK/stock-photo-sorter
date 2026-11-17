"""Stock Photo Sorter - pick today's in-stock product photos into a share folder."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import core


def res(name: str) -> Path:
    """Locate a bundled asset (works from source and from PyInstaller builds)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / "assets" / name

APP_NAME = "ZcaleUp Stock Photo Sorter"
CONFIG = Path.home() / ".stock_photo_sorter.json"

# Palette
BG, CARD, FG, MUTED = "#F4F6FA", "#FFFFFF", "#1F2937", "#6B7280"
ACCENT, ACCENT_DK, BORDER = "#4570B5", "#385C99", "#E5E7EB"
GREEN = "#62BD78"
STATUS = {  # status -> (label, row colour)
    "found": ("Ready", "#3E9B58"),
    "close": ("Similar name", "#D97706"),
    "missing": ("No photo", "#DC2626"),
    "out_of_stock": ("Out of stock", "#9CA3AF"),
}


def load_cfg() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def save_cfg(cfg: dict) -> None:
    try:
        CONFIG.write_text(json.dumps(cfg))
    except OSError:
        pass


def open_folder(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", path])


class Logo(tk.Label):
    """ZcaleUp wordmark: static when idle, animated snake while the app is working."""
    REST = 41  # frame showing the complete logo

    def __init__(self, parent) -> None:
        super().__init__(parent, bg=BG, bd=0)
        self.frames: list[tk.PhotoImage] = []
        for p in sorted(res("logo").glob("f*.png")):  # pre-composed full frames
            self.frames.append(tk.PhotoImage(file=str(p)))
        if not self.frames:  # asset missing: fall back to plain brand text
            self.config(text="ZcaleUp", fg=ACCENT, font=("Helvetica Neue", 26, "bold"))
        self.i, self.job = self.REST, None
        if self.frames:
            self.i = min(self.REST, len(self.frames) - 1)
            self.config(image=self.frames[self.i])

    def start(self) -> None:
        if self.frames and self.job is None:
            self._tick()

    def _tick(self) -> None:
        self.i = (self.i + 1) % len(self.frames)
        self.config(image=self.frames[self.i])
        self.job = self.after(30, self._tick)

    def stop(self) -> None:
        if self.job:
            self.after_cancel(self.job)
            self.job = None
        if self.frames:
            self.i = min(self.REST, len(self.frames) - 1)
            self.config(image=self.frames[self.i])


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x680")
        self.minsize(820, 560)
        self.configure(bg=BG)
        try:
            self.iconphoto(True, tk.PhotoImage(file=str(res("icon.png"))))
        except tk.TclError:
            pass
        cfg = load_cfg()
        self.photos_var = tk.StringVar(value=cfg.get("photos", ""))
        self.stock_var = tk.StringVar(value=cfg.get("stock", ""))
        self.out_var = tk.StringVar(value=cfg.get("out", ""))
        self.move_var = tk.BooleanVar(value=cfg.get("move", False))
        self.dated_var = tk.BooleanVar(value=cfg.get("dated", True))
        self.close_var = tk.BooleanVar(value=cfg.get("close", False))
        self.sub_var = tk.BooleanVar(value=cfg.get("sub", False))
        self.results: list[core.MatchResult] = []
        self.results_all: list[core.MatchResult] = []
        self._style()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._quit)

    # ---------- styling ----------
    def _style(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        f = ("Helvetica Neue" if sys.platform == "darwin" else "Segoe UI", 11)
        s.configure(".", background=BG, foreground=FG, font=f)
        s.configure("Card.TFrame", background=CARD, relief="flat")
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG)
        s.configure("Card.TLabel", background=CARD)
        s.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=(f[0], 10))
        s.configure("Title.TLabel", background=BG, font=(f[0], 20, "bold"))
        s.configure("Sub.TLabel", background=BG, foreground=MUTED)
        s.configure("TCheckbutton", background=CARD)
        s.map("TCheckbutton", background=[("active", CARD)])
        s.configure("TEntry", fieldbackground="#F9FAFB", bordercolor=BORDER, padding=6)
        s.configure("TButton", padding=(14, 8), background="#EEF0F6", bordercolor=BORDER, relief="flat")
        s.map("TButton", background=[("active", "#E2E5EF")])
        s.configure("Accent.TButton", background=ACCENT, foreground="white", font=(f[0], 11, "bold"))
        s.map("Accent.TButton", background=[("active", ACCENT_DK), ("disabled", "#9DB3D8")],
              foreground=[("disabled", "white")])
        s.configure("Treeview", background=CARD, fieldbackground=CARD, rowheight=30,
                    bordercolor=BORDER, borderwidth=0)
        s.configure("Treeview.Heading", background="#EEF0F6", font=(f[0], 10, "bold"),
                    relief="flat", padding=6)
        s.map("Treeview", background=[("selected", "#EAF6ED")], foreground=[("selected", FG)])
        s.configure("Horizontal.TProgressbar", background=GREEN, troughcolor=BORDER, thickness=6)

    # ---------- layout ----------
    def _build(self) -> None:
        wrap = ttk.Frame(self, padding=(24, 18, 24, 12))
        wrap.pack(fill="both", expand=True)
        head = ttk.Frame(wrap)
        head.pack(fill="x", pady=(0, 12))
        self.logo = Logo(head)
        self.logo.pack(side="left")
        txt = ttk.Frame(head)
        txt.pack(side="left", padx=18)
        ttk.Label(txt, text="Stock Photo Sorter", style="Title.TLabel").pack(anchor="w")
        ttk.Label(txt, text="Pick today's in-stock product photos into one folder, ready to share.",
                  style="Sub.TLabel").pack(anchor="w")

        card = ttk.Frame(wrap, style="Card.TFrame", padding=16)
        card.pack(fill="x")
        card.columnconfigure(1, weight=1)
        self._row(card, 0, "Photos folder", self.photos_var, self._pick_photos)
        self._row(card, 1, "Stock file", self.stock_var, self._pick_stock, "Excel / CSV / TXT")
        self._row(card, 2, "Output folder", self.out_var, self._pick_out)

        opts = ttk.Frame(card, style="Card.TFrame")
        opts.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Checkbutton(opts, text="Move photos (instead of copy)", variable=self.move_var).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(opts, text="Create dated subfolder", variable=self.dated_var).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(opts, text="Include similar names", variable=self.close_var,
                        command=self._refresh_summary).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(opts, text="Search sub-folders", variable=self.sub_var).pack(side="left")

        bar = ttk.Frame(wrap)
        bar.pack(fill="x", pady=12)
        ttk.Button(bar, text="1. Preview matches", command=self.preview).pack(side="left")
        self.go_btn = ttk.Button(bar, text="2. Prepare share folder", style="Accent.TButton",
                                 command=self.run, state="disabled")
        self.go_btn.pack(side="left", padx=10)
        self.open_btn = ttk.Button(bar, text="Open output folder", command=self._open_out)
        self.open_btn.pack(side="right")
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="right", padx=(0, 10))

        self.summary = ttk.Label(wrap, text="Choose your folders and stock file, then click Preview.",
                                 style="Sub.TLabel")
        self.summary.pack(anchor="w", pady=(0, 6))

        tf = ttk.Frame(wrap, style="Card.TFrame")
        tf.pack(fill="both", expand=True)
        cols = ("name", "qty", "status", "file")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")
        for c, t, w in (("name", "Product", 300), ("qty", "Stock", 70),
                        ("status", "Status", 130), ("file", "Photo file / suggestion", 320)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center" if c == "qty" else "w")
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for k, (_, colour) in STATUS.items():
            self.tree.tag_configure(k, foreground=colour)

        self.progress = ttk.Progressbar(wrap, mode="determinate")
        self.progress.pack(fill="x", pady=(10, 0))
        tk.Label(wrap, text="Powered by ZcaleUp", bg=BG, fg=MUTED, font=("Helvetica Neue", 9)
                 ).pack(anchor="e", pady=(6, 0))

    def _row(self, parent, r, label, var, cmd, hint="") -> None:
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(parent, textvariable=var).grid(row=r, column=1, sticky="ew", pady=5)
        ttk.Button(parent, text="Browse…", command=cmd).grid(row=r, column=2, padx=(10, 0), pady=5)

    # ---------- pickers ----------
    def _pick_photos(self) -> None:
        d = filedialog.askdirectory(title="Select photos folder", initialdir=self.photos_var.get() or None)
        if d: self.photos_var.set(d)

    def _pick_stock(self) -> None:
        f = filedialog.askopenfilename(title="Select stock file", filetypes=[
            ("Stock files", "*.xlsx *.xlsm *.csv *.txt *.tsv"), ("All files", "*.*")])
        if f: self.stock_var.set(f)

    def _pick_out(self) -> None:
        d = filedialog.askdirectory(title="Select output folder", initialdir=self.out_var.get() or None)
        if d: self.out_var.set(d)

    def _open_out(self) -> None:
        p = self._dest(create=False)
        if p and p.exists():
            open_folder(str(p))
        elif self.out_var.get() and Path(self.out_var.get()).exists():
            open_folder(self.out_var.get())
        else:
            messagebox.showinfo(APP_NAME, "Output folder does not exist yet.")

    def _dest(self, create=True) -> Path | None:
        out = self.out_var.get().strip()
        if not out:
            return None
        p = Path(out)
        if self.dated_var.get():
            p = p / f"Stock_{date.today().isoformat()}"
        return p

    # ---------- actions ----------
    def preview(self) -> None:
        photos, stock = self.photos_var.get().strip(), self.stock_var.get().strip()
        if not photos or not Path(photos).is_dir():
            return messagebox.showwarning(APP_NAME, "Please choose a valid photos folder.")
        if not stock or not Path(stock).is_file():
            return messagebox.showwarning(APP_NAME, "Please choose a valid stock file.")
        self.logo.start(); self.update()
        try:
            rows = core.read_stock(stock)
            index = core.scan_images(photos, self.sub_var.get())
        except Exception as e:
            self.logo.stop()
            return messagebox.showerror(APP_NAME, f"Could not read input:\n{e}")
        finally:
            self.after(900, self.logo.stop)
        if not rows:
            return messagebox.showwarning(APP_NAME, "No product rows found in the stock file.")
        self.results = core.match(rows, index)
        self.tree.delete(*self.tree.get_children())
        for r in self.results:
            if r.status == "close":
                info = f"≈ {r.suggestion}"
            else:
                info = ", ".join(f.name for f in r.files)
            qty = "" if r.row.qty is None else f"{r.row.qty:g}"
            self.tree.insert("", "end", values=(r.row.name, qty, STATUS[r.status][0], info), tags=(r.status,))
        self.progress["value"] = 0
        self._refresh_summary()

    def clear(self) -> None:
        """Reset for a new day: empty the preview, stock file and progress (folders are kept)."""
        self.results, self.results_all = [], []
        self.tree.delete(*self.tree.get_children())
        self.stock_var.set("")
        self.progress["value"] = 0
        self.go_btn.config(state="disabled")
        self.summary.config(text="Choose your folders and stock file, then click Preview.")

    def _counts(self) -> dict[str, int]:
        c = {k: 0 for k in STATUS}
        for r in self.results:
            c[r.status] += 1
        return c

    def _refresh_summary(self) -> None:
        if not self.results:
            return
        c = self._counts()
        n = c["found"] + (c["close"] if self.close_var.get() else 0)
        self.summary.config(text=f"{n} photo(s) will be prepared   •   {c['found']} ready   •   "
                                 f"{c['close']} similar   •   {c['missing']} no photo   •   "
                                 f"{c['out_of_stock']} out of stock")
        self.go_btn.config(state="normal" if n else "disabled")
        miss = len(core.unmatched(self.results, self.close_var.get()))
        if miss:
            self.summary.config(text=self.summary["text"] + f"\n⚠ {miss} item(s) have no photographs - "
                                     "you can download a report after preparing.")

    def run(self) -> None:
        dest = self._dest()
        if not dest:
            return messagebox.showwarning(APP_NAME, "Please choose an output folder.")
        move, inc = self.move_var.get(), self.close_var.get()
        todo = [r for r in self.results if r.status == "found" or (r.status == "close" and inc)]
        total = sum(len(r.files) for r in todo)
        verb = "move" if move else "copy"
        if not messagebox.askyesno(APP_NAME, f"{verb.capitalize()} {total} photo(s) to:\n{dest}?"):
            return
        self.progress.config(maximum=max(total, 1), value=0)
        self.logo.start()
        done, errors = 0, []
        for r in todo:
            d, e = core.transfer([r], dest, move, inc)
            done += d; errors += e
            self.progress["value"] = done
            self.update()
        self.results_all = self.results
        self.logo.stop()
        if move:  # moved files no longer exist in source; clear results
            self.results = []
            self.go_btn.config(state="disabled")
        msg = f"Done! {done} photo(s) {'moved' if move else 'copied'} to:\n{dest}"
        if errors:
            msg += f"\n\n{len(errors)} error(s):\n" + "\n".join(errors[:8])
        missing = core.unmatched(self.results_all, inc)
        self._done_dialog(msg, missing, dest)
        open_folder(str(dest))

    def _done_dialog(self, msg: str, missing: list, dest: Path) -> None:
        """Completion popup; warns about items without photos and offers an error report."""
        if not missing:
            messagebox.showinfo(APP_NAME, msg)
            return
        dlg = tk.Toplevel(self)
        dlg.title(APP_NAME)
        dlg.configure(bg=CARD)
        dlg.transient(self)
        dlg.resizable(False, False)
        body = ttk.Frame(dlg, style="Card.TFrame", padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=msg, style="Card.TLabel", justify="left").pack(anchor="w")
        n = len(missing)
        tk.Label(body, text=f"⚠  {n} item{'s' if n != 1 else ''} {'have' if n != 1 else 'has'} no photographs",
                 bg="#FEF2F2", fg="#B91C1C", font=("Helvetica Neue", 12, "bold"), padx=12, pady=10
                 ).pack(fill="x", pady=(14, 4))
        ttk.Label(body, text=", ".join(r.row.name for r in missing[:6]) + ("…" if n > 6 else ""),
                  style="Muted.TLabel", wraplength=380).pack(anchor="w")
        btns = ttk.Frame(body, style="Card.TFrame")
        btns.pack(fill="x", pady=(16, 0))
        ttk.Button(btns, text="OK", style="Accent.TButton", command=dlg.destroy).pack(side="right")
        ttk.Button(btns, text="Download error report",
                   command=lambda: self._save_report(missing, dlg)).pack(side="right", padx=8)
        dlg.update_idletasks()
        dlg.geometry(f"+{self.winfo_x() + 120}+{self.winfo_y() + 120}")
        dlg.grab_set()
        dlg.wait_window()

    def _save_report(self, missing: list, parent) -> None:
        p = filedialog.asksaveasfilename(parent=parent, title="Save error report", defaultextension=".csv",
                                         initialfile=f"missing_photos_{date.today().isoformat()}.csv",
                                         filetypes=[("CSV (opens in Excel)", "*.csv")])
        if p:
            core.write_report(missing, p)
            messagebox.showinfo(APP_NAME, f"Report saved:\n{p}", parent=parent)

    def _quit(self) -> None:
        save_cfg({"photos": self.photos_var.get(), "stock": self.stock_var.get(),
                  "out": self.out_var.get(), "move": self.move_var.get(),
                  "dated": self.dated_var.get(), "close": self.close_var.get(),
                  "sub": self.sub_var.get()})
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
