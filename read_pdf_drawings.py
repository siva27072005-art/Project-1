#!/usr/bin/env python3
"""
read_pdf_drawings.py

Select a folder or PDF file, then extract page renderings, embedded images,
and summarize drawing objects using PyMuPDF (fitz).

Usage:
  python read_pdf_drawings.py            # opens a folder selection dialog
  python read_pdf_drawings.py --folder PATH
  python read_pdf_drawings.py --pdf FILE

Requires: pip install PyMuPDF
"""
import argparse
import json
from pathlib import Path
import sys

try:
    import pymupdf as fitz
except Exception:
    print("PyMuPDF is required. Install with: pip install PyMuPDF")
    raise

def choose_folder_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="Select folder containing PDFs")
    root.destroy()
    return folder or None

def choose_pdf_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    root = tk.Tk()
    root.withdraw()
    file = filedialog.askopenfilename(title="Select a PDF file", filetypes=[('PDF','*.pdf')])
    root.destroy()
    return file or None

def find_pdfs(folder: Path):
    return sorted(folder.glob("*.pdf"))

def process_pdf(pdf_path: Path, out_dir: Path):
    doc = fitz.open(pdf_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"pdf": str(pdf_path), "pages": []}
    for pno in range(len(doc)):
        page = doc.load_page(pno)
        page_meta = {"page_number": pno+1, "drawings": [], "images": []}
        try:
            drawings = page.get_drawings()
        except Exception:
            drawings = []
        for d in drawings:
            page_meta["drawings"].append({
                "bbox": d.get("bbox"),
                "items_count": len(d.get("items", [])),
                "type": d.get("type")
            })
        images = page.get_images(full=True)
        for idx, img in enumerate(images, start=1):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
            except Exception:
                continue
            img_name = f"{pdf_path.stem}_p{pno+1}_img{idx}.png"
            img_path = out_dir / img_name
            if pix.n < 5:
                pix.save(str(img_path))
            else:
                pix2 = fitz.Pixmap(fitz.csRGB, pix)
                pix2.save(str(img_path))
                pix2 = None
            pix = None
            page_meta["images"].append(str(img_path))
        # render the page to PNG for visual inspection
        pix = page.get_pixmap(dpi=150)
        page_png = out_dir / f"{pdf_path.stem}_page{pno+1}.png"
        pix.save(str(page_png))
        page_meta["rendered_page"] = str(page_png)
        meta["pages"].append(page_meta)
    meta_path = out_dir / f"{pdf_path.stem}_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta_path

def main():
    parser = argparse.ArgumentParser(description="Scan folder for PDFs and extract drawings/images.")
    parser.add_argument("--folder", "-f", help="Folder to scan for PDFs")
    parser.add_argument("--pdf", "-p", help="Specific PDF filename to process (path or name)")
    parser.add_argument("--out", "-o", default="pdf_outputs", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser().resolve()

    pdfs = []
    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            # maybe the user provided a filename in a folder
            if args.folder:
                candidate = Path(args.folder) / args.pdf
                if candidate.exists():
                    pdf_path = candidate
        if not pdf_path.exists():
            print(f"PDF not found: {args.pdf}")
            sys.exit(1)
        pdfs = [pdf_path]
    else:
        folder = None
        if args.folder:
            folder = args.folder
        else:
            print("No folder or PDF provided — opening folder selection dialog...")
            folder = choose_folder_dialog()
            if not folder:
                # try selecting a single PDF instead
                print("No folder selected. Opening PDF file selection dialog...")
                file = choose_pdf_dialog()
                if not file:
                    print("No selection made. Exiting.")
                    sys.exit(1)
                pdfs = [Path(file)]
        if folder:
            folder_path = Path(folder).expanduser().resolve()
            if not folder_path.exists() or not folder_path.is_dir():
                print(f"Folder not found: {folder_path}")
                sys.exit(1)
            pdfs = find_pdfs(folder_path)

    if not pdfs:
        print("No PDF files found to process.")
        sys.exit(1)

    for pdf in pdfs:
        print(f"Processing: {pdf}")
        meta = process_pdf(Path(pdf), out_dir)
        print("Wrote metadata:", meta)

if __name__ == "__main__":
    main()
