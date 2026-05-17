import re
import io
import streamlit as st
import pdfplumber

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Financial Ratio Calculator", layout="centered")

st.title("Financial Ratio Calculator")
st.subheader("Built for consulting, investment, and corporate finance analysis")
st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
#  PDF EXTRACTION ENGINE  v2
#
#  Strategy (two-pass):
#    Pass 1 — Table extraction (primary):  pdfplumber detects actual financial
#             statement tables; rows have clean label / value columns so there
#             is no ambiguity about which number belongs to which line item.
#    Pass 2 — Text fallback: for any field still missing after the table pass,
#             scan each line of raw text.  Uses include + exclude guards and
#             picks the LARGEST qualifying number on the line (not the last).
#
#  Key fixes vs v1:
#    • Unicode apostrophes (U+2019 ' ) normalised before matching — fixes Apple
#      "shareholders' equity" not found.
#    • Strict exclude lists prevent "Other current assets" matching before
#      "Total current assets", narrative gross-margin % lines, etc.
#    • Minimum number threshold (≥ 10) in text-fallback skips footnote refs,
#      single-digit index numbers and percentage points.
#    • Year-shaped numbers (1 900 – 2 100) filtered out in text-fallback.
#    • Apple-specific labels added: "net sales", "gross margin",
#      "term debt, non-current".
# ─────────────────────────────────────────────────────────────────────────────

# Each field has:
#   include  — list of regex patterns; ANY match triggers the field candidate
#   exclude  — list of regex patterns; ANY match on the same text DISQUALIFIES it
# Patterns are tried against the normalised (lower-case, ASCII apostrophe) text.
FIELD_CONFIG = {
    "revenue": {
        "include": [
            r"total\s+revenue",                  # Microsoft — no anchors, matches anywhere in line
            r"^net\s+sales$",
            r"^total\s+net\s+sales$",
            r"^revenues?$",
            r"^total\s+revenues?$",             # covers "total revenue" and "total revenues"
            r"^net\s+revenues?$",
            r"^revenue\s+from\s+operations$",
            r"^total\s+sales$",
            r"^turnover$",
            r"net\s+sales",
            r"total\s+revenues?",
            r"total\s+net\s+sales",
        ],
        "exclude": [
            r"\bother\b",
            r"cost\s+of",
            r"deferred",
            r"unearned",
            r"per\s+share",
            r"growth",
            r"\bincreased?\b",
            r"\bdecreased?\b",
            r"\bimproved?\b",
            r"percent",
            r"\d\s*%",
            r"%",                # exclude any line containing a percentage sign
        ],
        "label": "Total Revenue",
    },
    "gross_profit": {
        "include": [
            r"^total\s+gross\s+margin$",        # Apple 10-K exact label
            r"total\s+gross\s+margin\b",        # inline / look-ahead text
            r"^gross\s+margin$",
            r"^gross\s+profit$",
            r"^gross\s+income$",
            r"gross\s+margin\b",
            r"gross\s+profit\b",
            r"gross\s+income\b",
        ],
        "exclude": [
            r"percent",
            r"\d\s*%",
            r"\bas\s+a\b",
            r"ratio",
            r"rate\b",
            r"basis\s+point",
            r"\bimproved?\b",
            r"\bincreased?\b",
            r"\bdecreased?\b",
        ],
        "label": "Gross Profit",
    },
    "net_income": {
        "include": [
            r"^net\s+income$",
            r"^net\s+earnings$",
            r"^net\s+profit$",
            r"^profit\s+for\s+the\s+year$",
            r"^profit\s+after\s+(?:income\s+)?tax",
            r"net\s+income\b",
            r"net\s+earnings\b",
            r"net\s+profit\b",
            r"profit\s+for\s+the\s+year",
        ],
        "exclude": [
            r"per\s+share",
            r"\bdiluted\b",
            r"\bbasic\b",
            r"attributable\s+to\s+non",
            r"noncontrolling",
            r"non.controlling",
            r"minority",
            r"other\s+comprehensive",
            r"percent",
            r"\d\s*%",
        ],
        "label": "Net Income",
    },
    "total_equity": {
        "include": [
            r"total\s+shareholders",              # Apple  — bare, survives cell splits
            r"total\s+stockholders",              # Microsoft — bare, survives cell splits
            r"total\s+shareholders\s+equity",
            r"total\s+stockholders\s+equity",     # Microsoft no-apostrophe variant
            r"total\s+shareholders\s*'?\s*equity",
            r"total\s+stockholders\s*'?\s*equity",
            r"shareholders\s*'?\s*equity(?:\s*\(?deficit\)?)?",
            r"stockholders\s*'?\s*equity(?:\s*\(?deficit\)?)?",
            r"^total\s+equity$",
            r"total\s+equity\b",
            r"owners\s*'?\s*equity",
        ],
        "exclude": [
            r"non.?controlling",
            r"minority",
            r"other\s+comprehensive",
            r"per\s+share",
            r"accumulated",
            r"additional\s+paid",
            r"retained",
            r"common\s+stock",
        ],
        "label": "Total Shareholders Equity",
    },
    "total_debt": {
        # sum_matches=True accumulates ALL matching rows so current + non-current
        # portions are combined into a single Total Debt figure.
        #
        # Apple  (two identical "Term debt" rows):
        #   Term debt  10,912  (current liabilities section)
        #   Term debt  85,750  (non-current liabilities section)
        #   → sum = 96,662
        #
        # Microsoft (two distinct labels):
        #   Long-term debt               40,152
        #   Current portion of long-term debt  2,999
        #   → sum = 43,151
        "sum_matches": True,
        "include": [
            r"^term\s+debt$",
            r"^term\s+debt,?\s+non.?current$",
            r"^long.?term\s+debt$",              # Microsoft: "Long-term debt"
            r"^long.?term\s+borrowings?$",
            r"^total\s+(?:long.?term\s+)?debt$",
            r"^notes\s+payable$",
            r"^total\s+borrowings?$",
            r"current\s+portion\s+of\s+long.?term\s+debt",    # Microsoft current portion
            r"current\s+maturities\s+of\s+long.?term\s+debt", # alternative phrasing
            r"term\s+debt,?\s+non.?current",
            r"long.?term\s+(?:debt|borrowings?)",
            r"total\s+debt\b",
            r"total\s+borrowings?\b",
        ],
        "exclude": [
            # "current portion" and "current maturities" removed from excludes —
            # they are now explicitly included so both Apple and Microsoft
            # current-debt rows are summed into the total.
            r",\s*current",          # still blocks "term debt, current" cell splits
            r"short.?term\s+debt",   # short-term debt (not long-term, don't include)
            r"finance\s+lease",
            r"operating\s+lease",
            r"due\s+within",
        ],
        "label": "Total Debt",
    },
    "current_assets": {
        # Only match the TOTAL line — never partial line items
        "include": [
            r"^total\s+current\s+assets$",
            r"total\s+current\s+assets\b",
        ],
        "exclude": [
            r"\bother\b",
            r"\bnet\b",
            r"non.current",
        ],
        "label": "Current Assets",
    },
    "current_liabilities": {
        "include": [
            r"^total\s+current\s+liabilities$",
            r"total\s+current\s+liabilities\b",
        ],
        "exclude": [
            r"\bother\b",
            r"non.current",
        ],
        "label": "Current Liabilities",
    },
}

# ── Scale detection (label only — we do NOT multiply) ────────────────────────
# Numbers in financial PDFs are already expressed in the stated unit.
# "391,035" in an Apple 10-K that says "in millions" means 391,035 (millions).
# We store it exactly as printed and surface the unit label for the user.
_SCALE_PATTERNS = [
    (re.compile(r"\bin\s+billions?\b",  re.I), "billions"),
    (re.compile(r"\bin\s+millions?\b",  re.I), "millions"),
    (re.compile(r"\bin\s+thousands?\b", re.I), "thousands"),
]

def _detect_scale_label(text: str) -> str:
    """Return a human-readable unit label found on this page, or '' if none."""
    for pat, label in _SCALE_PATTERNS:
        if pat.search(text):
            return label
    return ""

# ── Text normalisation ───────────────────────────────────────────────────────
# Explicit Unicode code-points — avoids source-file encoding surprises.
# \uXXXX escapes inside a normal (non-raw) string are resolved by Python at
# parse time, making this encoding-safe regardless of how the .py file is saved.
# U+2019 = ‘  U+2018 = ‘  U+02BC = ʼ  U+0060 = `  U+00B4 = ´  U+FF07 = ＇
# Python resolves \uXXXX escapes in normal (non-raw) strings at parse time.
# This is encoding-safe: the code-point is baked in regardless of .py encoding.
# "[’‘...]" compiles to a regex character class containing the exact
# Unicode chars — U+2019 is the curly apostrophe Apple’s 10-K uses.
_APOSTROPHE_RE = re.compile("[’‘ʼ`´＇]")

def _norm(text: str) -> str:
    """Lower-case and normalise all Unicode apostrophe variants to ASCII ‘."""
    return _APOSTROPHE_RE.sub("’", text.lower())

# ── Number parsing ───────────────────────────────────────────────────────────
# Matches:  391,035  |  (3,634)  |  $391,035.00  |  1 234 567
_NUM_RE = re.compile(
    r"(?<!\d)"                           # not preceded by a digit
    r"(\(?)?"                            # optional opening paren  → negative
    r"[$£€]?"                            # optional currency symbol
    r"(\d{1,3}(?:,\d{3})*"              # integer with comma separators only (not space)
    r"(?:\.\d+)?)"                       # optional decimal part
    r"(\)?)?"                            # optional closing paren
)

def _parse_num(raw: str) -> float | None:
    """Parse a single raw token to float; return None on failure."""
    raw = raw.strip()
    if not raw or raw in ("-", "—", "–", "N/A", "*"):
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = re.sub(r"[^\d.]", "", raw)
    if not cleaned:
        return None
    try:
        v = float(cleaned)
    except ValueError:
        return None
    return -v if negative else v

def _extract_numbers(text: str) -> list[float]:
    """Return all parseable numbers found in a text string."""
    out = []
    for m in _NUM_RE.finditer(text):
        raw = m.group(0).strip()
        v = _parse_num(raw)
        if v is not None:
            out.append(v)
    return out

def _is_year(v: float) -> bool:
    return 1_900 <= abs(v) <= 2_100 and v == int(v)

def _best_number(numbers: list[float], min_abs: float = 10.0) -> float | None:
    """
    Return the FIRST qualifying financial figure — the most recent year in
    side-by-side two-year tables (current year is always printed first).
    Skips calendar-year-shaped numbers and values below min_abs.
    """
    for n in numbers:
        if abs(n) >= min_abs and not _is_year(n):
            return n
    return None

# ── Field matching helpers ───────────────────────────────────────────────────
def _matches_field(text_norm: str, config: dict) -> bool:
    """Return True if text matches any include pattern and no exclude pattern."""
    if any(re.search(ex, text_norm) for ex in config["exclude"]):
        return False
    return any(re.search(inc, text_norm) for inc in config["include"])

# ── pdfplumber table extraction strategies ───────────────────────────────────
# Apple's 10-K and other complex filings sometimes need non-default settings.
# We try each strategy in turn and merge results (first found wins per field).
_TABLE_STRATEGIES = [
    {},                                                              # pdfplumber default
    {"vertical_strategy": "lines",  "horizontal_strategy": "lines"},
    {"vertical_strategy": "text",   "horizontal_strategy": "text"},
    {"vertical_strategy": "lines",  "horizontal_strategy": "text"},
    {"vertical_strategy": "text",   "horizontal_strategy": "lines"},
]

def _rows_from_page(page) -> list[list[str]]:
    """
    Try every table strategy and return ALL rows from ALL detected tables on
    this page (deduplicated by row content).  Returns a flat list of cell lists.
    """
    seen: set[tuple] = set()
    all_rows: list[list[str]] = []
    for settings in _TABLE_STRATEGIES:
        try:
            tables = page.extract_tables(settings) if settings else page.extract_tables()
        except Exception:
            continue
        for table in (tables or []):
            for raw_row in table:
                if not raw_row:
                    continue
                cells = [str(c).strip() if c else "" for c in raw_row]
                key = tuple(cells)
                if key not in seen:
                    seen.add(key)
                    all_rows.append(cells)
    return all_rows

# ── Pass 0 — Priority text patterns (highest confidence) ─────────────────────
#
#  Problem: pdfplumber's table pass finds a different row on the same page
#  before it reaches "Total net sales" / "Total gross margin", returning a
#  small spurious value (e.g. 202) from an earlier cell.
#
#  Fix: scan raw page text FIRST using patterns that include the "$" sign.
#  "Total net sales $ 391,035" is unique to the financial statement row —
#  narrative text never puts a bare $ immediately after that label.
#  This pass claims the field before the table pass can pick the wrong row.
# ─────────────────────────────────────────────────────────────────────────────
_PRIORITY_PATTERNS = {
    "revenue":      re.compile(r"total\s+net\s+sales\s*\$\s*([\d,]+)",    re.I),
    "gross_profit": re.compile(r"total\s+gross\s+margin\s*\$\s*([\d,]+)", re.I),
}

def _extract_priority_text(pdf, results: dict) -> None:
    """
    Pass 0: $-anchored patterns that uniquely identify financial-statement rows.
    Runs before the table pass so these fields are already claimed.
    Mutates `results` in place.
    """
    for page_num, page in enumerate(pdf.pages, start=1):
        if all(results[f] is not None for f in _PRIORITY_PATTERNS):
            break
        page_text = page.extract_text()
        if not page_text:
            continue
        scale_label = _detect_scale_label(page_text)
        for field, pat in _PRIORITY_PATTERNS.items():
            if results[field] is not None:
                continue
            m = pat.search(page_text)
            if m:
                v = _parse_num(m.group(1))
                if v is not None:
                    results[field] = {
                        "value": v,
                        "page": page_num,
                        "raw_line": m.group(0).strip(),
                        "method": "priority",
                        "scale": scale_label,
                    }

# ── Pass 1 — Table-aware extraction ─────────────────────────────────────────
def _extract_from_tables(pdf, results: dict, sums: dict) -> None:
    """
    Iterate every pdfplumber table on every page (trying multiple extraction
    strategies).  For each row whose label cell matches a field, take the first
    large numeric value in that row.
    Fields with sum_matches=True accumulate all matching rows into `sums`.
    Mutates `results` and `sums` in place.
    """
    for page_num, page in enumerate(pdf.pages, start=1):
        page_text = page.extract_text() or ""
        scale_label = _detect_scale_label(page_text)

        for cells in _rows_from_page(page):
            non_empty = [c for c in cells if c]
            if not non_empty:
                continue

            label_norm = _norm(non_empty[0])

            for field, config in FIELD_CONFIG.items():
                # Regular fields: skip once found. sum_matches fields: always accumulate.
                if not config.get("sum_matches") and results[field] is not None:
                    continue

                if not _matches_field(label_norm, config):
                    continue

                for cell in non_empty[1:]:
                    v = _best_number(_extract_numbers(cell), min_abs=0)
                    if v is not None:
                        if config.get("sum_matches"):
                            if field not in sums:
                                sums[field] = {
                                    "value": 0.0, "page": page_num,
                                    "raw_line": "", "method": "table",
                                    "scale": scale_label,
                                }
                            sums[field]["value"] += v
                            row_text = " | ".join(non_empty)
                            sums[field]["raw_line"] = (
                                f"{sums[field]['raw_line']} ＋ {row_text}"
                                if sums[field]["raw_line"] else row_text
                            )
                        else:
                            results[field] = {
                                "value": v,
                                "page": page_num,
                                "raw_line": " | ".join(non_empty),
                                "method": "table",
                                "scale": scale_label,
                            }
                        break

# ── Pass 2 — Text-line fallback with look-ahead ───────────────────────────────
#
#  ROOT CAUSE fixed here:
#  In many financial PDFs (including Apple's 10-K), pdfplumber extracts the
#  row label and its numbers on *separate* lines:
#
#     line i  :  "Net sales"                   ← keyword found, no number
#     line i+1:  "391,035  383,285  394,328"   ← numbers are here
#
#  The old code looked only at line i, found no number, moved on, and later
#  hit a narrative sentence ("grew net sales by 62%") that did have a number.
#
#  Fix: when a keyword line has no qualifying number, look ahead up to 2 lines.
#  Stop look-ahead early if the next line is itself a financial label row.
# ─────────────────────────────────────────────────────────────────────────────
def _is_label_line(line_norm: str) -> bool:
    """Return True if this line looks like a financial statement label."""
    return any(
        _matches_field(line_norm, cfg)
        for cfg in FIELD_CONFIG.values()
    )

def _extract_from_text(pdf, results: dict, sums: dict) -> None:
    """
    For fields still missing after the table pass, scan raw text lines with
    look-ahead.  Fields with sum_matches=True accumulate all matches into `sums`.
    Mutates `results` and `sums` in place.
    """
    for page_num, page in enumerate(pdf.pages, start=1):
        # Stop early only when ALL non-sum fields are filled
        non_sum_fields = [f for f, c in FIELD_CONFIG.items() if not c.get("sum_matches")]
        if all(results[f] is not None for f in non_sum_fields):
            break

        page_text = page.extract_text()
        if not page_text:
            continue

        scale_label = _detect_scale_label(page_text)
        lines = page_text.splitlines()

        for i, line in enumerate(lines):
            line_norm = _norm(line)

            for field, config in FIELD_CONFIG.items():
                if not config.get("sum_matches") and results[field] is not None:
                    continue

                if not _matches_field(line_norm, config):
                    continue

                # ── Look-ahead: try line i, then i+1, then i+2 ──────────────
                found_value = None
                source_line = line.strip()

                for offset in range(3):
                    idx = i + offset
                    if idx >= len(lines):
                        break
                    candidate_line = lines[idx]
                    if offset > 0 and _is_label_line(_norm(candidate_line)):
                        break
                    nums = _extract_numbers(candidate_line)
                    v = _best_number(nums, min_abs=10.0)
                    if v is not None:
                        found_value = v
                        break

                if found_value is not None:
                    if config.get("sum_matches"):
                        if field not in sums:
                            sums[field] = {
                                "value": 0.0, "page": page_num,
                                "raw_line": "", "method": "text",
                                "scale": scale_label,
                            }
                        sums[field]["value"] += found_value
                        sums[field]["raw_line"] = (
                            f"{sums[field]['raw_line']} ＋ {source_line}"
                            if sums[field]["raw_line"] else source_line
                        )
                    else:
                        results[field] = {
                            "value": found_value,
                            "page": page_num,
                            "raw_line": source_line,
                            "method": "text",
                            "scale": scale_label,
                        }

# ── Public entry point ────────────────────────────────────────────────────────
def extract_financials_from_pdf(uploaded_file) -> dict:
    """
    Two-pass extraction from a PDF file object.
    Returns {field_key: {value, page, raw_line, method, scale} | None}.
    Fields with sum_matches=True (e.g. total_debt) accumulate all matching rows.
    """
    results = {k: None for k in FIELD_CONFIG}
    sums: dict = {}          # accumulator for sum_matches fields
    pdf_bytes = uploaded_file.read()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        _extract_priority_text(pdf, results)       # Pass 0 — $ anchored, highest confidence
        _extract_from_tables(pdf, results, sums)   # Pass 1 — table-aware
        _extract_from_text(pdf, results, sums)     # Pass 2 — text fallback

    # Merge accumulated sums into results (only if table/text pass didn't already set them)
    for field, acc in sums.items():
        if acc["value"] != 0:
            results[field] = acc

    return results


# ─────────────────────────────────────────────
#  SESSION STATE — stores extracted values
# ─────────────────────────────────────────────
DEFAULTS = {
    "revenue": 0.0,
    "gross_profit": 0.0,
    "net_income": 0.0,
    "total_equity": 0.0,
    "total_debt": 0.0,
    "current_assets": 0.0,
    "current_liabilities": 0.0,
    "extraction_info": {},   # field -> {page, raw_line}
    "pdf_processed": False,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
#  PDF UPLOAD SECTION
# ─────────────────────────────────────────────
with st.expander("📄 Upload Annual Report PDF (optional — auto-fills fields below)", expanded=True):
    uploaded = st.file_uploader(
        "Upload a PDF annual report",
        type=["pdf"],
        help="The app will scan the PDF for financial figures and pre-fill the calculator.",
    )

    if uploaded:
        if st.button("🔍 Extract Financial Data from PDF", use_container_width=True):
            with st.spinner("Reading PDF and extracting figures…"):
                extracted = extract_financials_from_pdf(uploaded)

            found_any = False
            info = {}
            for field, result in extracted.items():
                if result is not None:
                    st.session_state[field] = result["value"]
                    info[field] = {"page": result["page"], "raw_line": result["raw_line"]}
                    found_any = True

            st.session_state["extraction_info"] = info
            st.session_state["pdf_processed"] = True

            if found_any:
                st.success(f"✅ Extracted {len(info)} of {len(FIELD_CONFIG)} figures. Fields below have been pre-filled.")
            else:
                st.warning("⚠️ No financial figures could be automatically extracted from this PDF. Please fill in the fields manually.")

    # Show extraction provenance table
    if st.session_state["pdf_processed"] and st.session_state["extraction_info"]:
        LABEL_MAP = {f: cfg["label"] for f, cfg in FIELD_CONFIG.items()}

        st.markdown("##### 🔎 Extraction Details — verify these against your source document")
        rows = []
        for field, info in st.session_state["extraction_info"].items():
            scale_label = info.get("scale", "")   # already a string, e.g. "millions"
            method_icon = "📊 table" if info.get("method") == "table" else "📝 text"
            rows.append({
                "Field": LABEL_MAP.get(field, field),
                "Extracted Value": f"{st.session_state[field]:,.2f}",
                "Scale": scale_label,
                "Page": info["page"],
                "Method": method_icon,
                "Source Line": info["raw_line"][:80] + ("…" if len(info["raw_line"]) > 80 else ""),
            })

        not_found = [
            LABEL_MAP[f] for f in FIELD_CONFIG
            if f not in st.session_state["extraction_info"]
        ]

        st.table(rows)

        if not_found:
            st.info(
                f"⚠️ **Not automatically extracted** (fill in manually below): "
                + ", ".join(not_found)
            )


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────
def badge(color, label):
    colors = {"green": "#1e7e34", "amber": "#d39e00", "red": "#bd2130"}
    hex_color = colors.get(color, "#555")
    return (
        f'<span style="background:{hex_color};color:white;padding:3px 10px;'
        f'border-radius:4px;font-size:0.8rem;font-weight:600">{label}</span>'
    )


def ratio_card(name, fmt, interpretation, color, benchmark_note):
    color_map = {"green": "#d4edda", "amber": "#fff3cd", "red": "#f8d7da"}
    border_map = {"green": "#28a745", "amber": "#ffc107", "red": "#dc3545"}
    bg = color_map.get(color, "#f8f9fa")
    border = border_map.get(color, "#ccc")
    st.markdown(
        f"""
        <div style="border-left:5px solid {border};background:{bg};padding:14px 18px;
                    border-radius:6px;margin-bottom:14px">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <strong style="font-size:1rem">{name}</strong>
                {badge(color, interpretation)}
            </div>
            <div style="font-size:1.6rem;font-weight:700;margin:6px 0">{fmt}</div>
            <div style="font-size:0.82rem;color:#555">{benchmark_note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  CALCULATOR FORM  (pre-filled from session state)
# ─────────────────────────────────────────────
st.markdown("### 📊 Financial Figures")
st.caption("Fields are pre-filled if data was extracted from a PDF. Edit any value before calculating.")

with st.form("inputs"):
    company_name = st.text_input("Company Name", placeholder="e.g. Apple Inc.")

    col1, col2 = st.columns(2)
    with col1:
        revenue = st.number_input(
            "Total Revenue", min_value=0.0, step=1000.0, format="%.2f",
            value=float(st.session_state["revenue"]),
        )
        gross_profit = st.number_input(
            "Gross Profit", min_value=0.0, step=1000.0, format="%.2f",
            value=float(st.session_state["gross_profit"]),
        )
        net_income = st.number_input(
            "Net Income", step=1000.0, format="%.2f",
            value=float(st.session_state["net_income"]),
        )
        total_equity = st.number_input(
            "Total Shareholders Equity", step=1000.0, format="%.2f",
            value=float(st.session_state["total_equity"]),
        )
    with col2:
        total_debt = st.number_input(
            "Total Debt", min_value=0.0, step=1000.0, format="%.2f",
            value=float(st.session_state["total_debt"]),
        )
        current_assets = st.number_input(
            "Current Assets", min_value=0.0, step=1000.0, format="%.2f",
            value=float(st.session_state["current_assets"]),
        )
        current_liabilities = st.number_input(
            "Current Liabilities", min_value=0.0, step=1000.0, format="%.2f",
            value=float(st.session_state["current_liabilities"]),
        )

    submitted = st.form_submit_button("Calculate Ratios", use_container_width=True)


# ─────────────────────────────────────────────
#  RATIO CALCULATIONS & OUTPUT
# ─────────────────────────────────────────────
if submitted:
    errors = []
    if revenue == 0:
        errors.append("Total Revenue cannot be zero.")
    if current_liabilities == 0:
        errors.append("Current Liabilities cannot be zero.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        st.markdown("---")
        heading = f"### Results for {company_name}" if company_name else "### Results"
        st.markdown(heading)
        st.markdown(" ")

        # 1. Gross Profit Margin
        gpm = (gross_profit / revenue) * 100
        if gpm >= 40:
            gpm_color, gpm_interp = "green", "Strong"
        elif gpm >= 20:
            gpm_color, gpm_interp = "amber", "Moderate"
        else:
            gpm_color, gpm_interp = "red", "Weak"
        ratio_card(
            "Gross Profit Margin", f"{gpm:.1f}%", gpm_interp, gpm_color,
            "Benchmark: ≥40% strong | 20–40% moderate | <20% weak — varies significantly by industry",
        )

        # 2. Net Profit Margin
        npm = (net_income / revenue) * 100
        if npm >= 15:
            npm_color, npm_interp = "green", "Strong"
        elif npm >= 5:
            npm_color, npm_interp = "amber", "Moderate"
        else:
            npm_color, npm_interp = "red", "Weak"
        ratio_card(
            "Net Profit Margin", f"{npm:.1f}%", npm_interp, npm_color,
            "Benchmark: ≥15% strong | 5–15% moderate | <5% or negative is a concern",
        )

        # 3. Return on Equity (ROE)
        if total_equity == 0:
            st.warning("ROE skipped — Shareholders Equity is zero.")
        else:
            roe = (net_income / total_equity) * 100
            if roe >= 15:
                roe_color, roe_interp = "green", "Strong"
            elif roe >= 8:
                roe_color, roe_interp = "amber", "Moderate"
            else:
                roe_color, roe_interp = "red", "Weak"
            ratio_card(
                "Return on Equity (ROE)", f"{roe:.1f}%", roe_interp, roe_color,
                "Benchmark: ≥15% strong | 8–15% moderate | <8% suggests poor capital efficiency",
            )

        # 4. Debt-to-Equity Ratio
        if total_equity == 0:
            st.warning("D/E Ratio skipped — Shareholders Equity is zero.")
        else:
            de = total_debt / total_equity
            if de <= 1.0:
                de_color, de_interp = "green", "Low Risk"
            elif de <= 2.0:
                de_color, de_interp = "amber", "Moderate Risk"
            else:
                de_color, de_interp = "red", "High Risk"
            ratio_card(
                "Debt-to-Equity Ratio", f"{de:.2f}x", de_interp, de_color,
                "Benchmark: ≤1.0x low risk | 1–2x moderate | >2x high leverage — context matters by sector",
            )

        # 5. Current Ratio
        cr = current_assets / current_liabilities
        if cr >= 2.0:
            cr_color, cr_interp = "green", "Healthy"
        elif cr >= 1.0:
            cr_color, cr_interp = "amber", "Adequate"
        else:
            cr_color, cr_interp = "red", "At Risk"
        ratio_card(
            "Current Ratio", f"{cr:.2f}x", cr_interp, cr_color,
            "Benchmark: ≥2.0x healthy | 1–2x adequate | <1.0x signals potential liquidity issues",
        )


# ─────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#888;font-size:0.8rem'>"
    "Built by Ruchas &nbsp;|&nbsp; Financial Report Analyzer v0.1 &nbsp;|&nbsp; "
    "<a href='https://github.com/Ruchas-lab' style='color:#888'>github.com/Ruchas-lab</a>"
    "</div>",
    unsafe_allow_html=True,
)
