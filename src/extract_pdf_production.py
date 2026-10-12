"""
MOIL-GeoSync -- Step 4: Extract mine-wise production from Annual Report PDFs
==============================================================================
Searches for mine-wise production tables in the MOIL Annual Reports
and compares with currently assumed share percentages.
"""

import os
import re
import fitz  # PyMuPDF

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PDFS = [
    os.path.join(BASE_DIR, "newdataset", "6a2fa99e40-Annual_Report_2024-25.pdf"),
    os.path.join(BASE_DIR, "newdataset", "AR_30588_MOIL_2025_2026_A_10745244_25082026152918.pdf"),
    os.path.join(BASE_DIR, "newdataset", "M6a8d1a081-Annual_Report_2025-26.pdf"),
]

# Current assumed shares from generate_real_production.py
ASSUMED_SHARES = {
    "Balaghat": 0.22,
    "Dongri_Buzurg": 0.12,
    "Chikla": 0.10,
    "Munsar": 0.08,
    "Kandri": 0.09,
    "Gumgaon": 0.07,
    "Ukwa": 0.06,
    "Tirodi": 0.05,
    "Sitapatore": 0.04,
    "Beldongri": 0.03,
}

# Keywords to search for in PDF pages
MINE_KEYWORDS = [
    "balaghat", "dongri buzurg", "chikla", "munsar", "mansar",
    "kandri", "gumgaon", "ukwa", "tirodi", "sitapatore", "beldongri",
    "mine-wise", "mine wise", "production of ore", "lakh tonnes",
    "physical performance", "operational performance",
]

def search_pdf(filepath):
    """Search PDF for pages containing mine-wise production data."""
    basename = os.path.basename(filepath)
    print(f"\n{'='*70}")
    print(f"PDF: {basename}")
    print(f"{'='*70}")

    doc = fitz.open(filepath)
    print(f"  Pages: {doc.page_count}")

    relevant_pages = []

    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = page.get_text()
        text_lower = text.lower()

        # Count how many mine names appear on this page
        mine_hits = sum(1 for kw in MINE_KEYWORDS if kw in text_lower)

        if mine_hits >= 3:  # At least 3 keywords = likely a production table page
            relevant_pages.append((page_num + 1, mine_hits, text))

    print(f"  Pages with mine production data: {len(relevant_pages)}")

    for page_num, hits, text in relevant_pages:
        print(f"\n  --- Page {page_num} ({hits} keyword hits) ---")
        # Print the text, truncated
        lines = text.strip().split("\n")
        # Filter for lines containing numbers (likely table rows)
        table_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            # Check if line contains mine names or numbers
            has_mine = any(kw in line_stripped.lower() for kw in
                          ["balaghat", "dongri", "chikla", "munsar", "mansar",
                           "kandri", "gumgaon", "ukwa", "tirodi", "sitapath", "beldongri",
                           "total", "production", "mine", "lakh"])
            has_number = bool(re.search(r'\d+[,.]?\d+', line_stripped))
            if has_mine or has_number:
                table_lines.append(line_stripped)

        for line in table_lines[:50]:
            print(f"    {line.encode('ascii', errors='replace').decode('ascii')}")

        if len(table_lines) > 50:
            print(f"    ... ({len(table_lines) - 50} more lines)")

    doc.close()
    return relevant_pages


def extract_mine_production(text):
    """
    Try to extract mine-wise production numbers from text.
    Returns dict of mine_name -> production_tonnes.
    """
    results = {}
    lines = text.strip().split("\n")

    mine_patterns = {
        "Balaghat": r"balaghat",
        "Dongri_Buzurg": r"dongri\s*buzurg",
        "Chikla": r"chikla",
        "Munsar": r"mu[n]?sar",
        "Kandri": r"kandri",
        "Gumgaon": r"gumgaon",
        "Ukwa": r"ukwa",
        "Tirodi": r"tirodi",
        "Sitapatore": r"sitap",
        "Beldongri": r"beldongri",
    }

    for line in lines:
        line_lower = line.lower().strip()
        for mine, pattern in mine_patterns.items():
            if re.search(pattern, line_lower):
                # Try to extract numbers from this line
                numbers = re.findall(r'(\d+[,.]?\d*)', line)
                if numbers:
                    # Take the largest number as production (heuristic)
                    parsed = []
                    for n in numbers:
                        try:
                            val = float(n.replace(",", ""))
                            parsed.append(val)
                        except ValueError:
                            pass
                    if parsed:
                        results[mine] = {
                            "raw_line": line.strip(),
                            "numbers": parsed,
                        }
    return results


def main():
    print("=" * 70)
    print("STEP 4: Mine-Wise Production from Annual Report PDFs")
    print("=" * 70)

    all_extractions = {}

    for pdf_path in PDFS:
        if not os.path.exists(pdf_path):
            print(f"\n[SKIP] Not found: {pdf_path}")
            continue

        relevant_pages = search_pdf(pdf_path)
        basename = os.path.basename(pdf_path)

        # Try to extract numbers from relevant pages
        for page_num, hits, text in relevant_pages:
            extracted = extract_mine_production(text)
            if extracted:
                key = f"{basename} p.{page_num}"
                all_extractions[key] = extracted

    # Print comparison table
    print(f"\n{'='*70}")
    print("COMPARISON: Assumed Share % vs PDF-Extracted Data")
    print(f"{'='*70}")
    print(f"{'Mine':20s} | {'Assumed %':>10s} | PDF Findings")
    print("-" * 80)

    for mine, share in sorted(ASSUMED_SHARES.items(), key=lambda x: -x[1]):
        pdf_info = []
        for source, mines in all_extractions.items():
            if mine in mines:
                nums = mines[mine]["numbers"]
                raw = mines[mine]["raw_line"][:60]
                pdf_info.append(f"{source}: {nums} [{raw}]")

        pdf_str = " | ".join(pdf_info) if pdf_info else "NOT FOUND in PDFs"
        print(f"  {mine:18s} | {share*100:8.1f}%  | {pdf_str}")

    # Summary
    found_mines = set()
    for source, mines in all_extractions.items():
        found_mines.update(mines.keys())

    not_found = set(ASSUMED_SHARES.keys()) - found_mines
    print(f"\n  Mines found in PDFs: {len(found_mines)}/{len(ASSUMED_SHARES)}")
    if not_found:
        print(f"  Mines NOT found: {not_found}")

    print(f"\n  NOTE: Numbers extracted are raw regex matches from PDF text.")
    print(f"  Manual verification against the actual PDF tables is required.")
    print(f"  The PDF text extraction may miss data in image-based tables.")

    print(f"\n{'='*70}")
    print("STEP 4 COMPLETE.")
    print("Files created: None.")
    print("Files modified: None.")
    print("Cannot verify: Whether extracted numbers are production (tonnes)")
    print("  vs dispatches, revenue, or other metrics. PDF table structure")
    print("  is ambiguous in text extraction. Manual cross-check needed.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
