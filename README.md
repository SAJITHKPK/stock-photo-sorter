# Stock Photo Sorter

Pick today's in-stock product photos into one folder, ready to share with customers.

## Use
1. **Photos folder** – folder with product photos named after the product (`Blue Shirt.jpg`).
2. **Stock file** – `.xlsx`, `.csv` or `.txt`. Needs a product-name column (header like *Product/Item/Name*)
   and optionally a stock column (*Stock/Qty/Quantity*). Rows with stock ≤ 0 are skipped.
   With no header, column 1 = name, first numeric column = stock. A `.txt` with one name per line also works.
3. **Output folder** – a `Stock_YYYY-MM-DD` subfolder is created inside (optional).
4. **Preview matches**, then **Prepare share folder**.

Matching ignores case, spaces, `_`/`-` and the file extension. Near-misses (e.g. typos) show as
"Similar name" and are only used if *Include similar names* is ticked.
By default photos are **copied**; tick *Move* to move them instead.

## Run / test / build
    pip install -r requirements.txt
    python app.py
    pip install -r requirements-dev.txt && pytest tests
    ./build.sh        # macOS/Linux  -> dist/StockPhotoSorter.app
    build.bat         # Windows      -> dist\StockPhotoSorter.exe  (must be built on Windows)
