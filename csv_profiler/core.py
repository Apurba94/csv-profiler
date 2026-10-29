"""Type inference, missing values and summary statistics for each CSV column."""
import csv
import io
import math
import re
import statistics
from collections import Counter
from datetime import datetime

MISSING = {"", "na", "n/a", "nan", "null", "none", "-", ".", "?", "missing", "#n/a"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")
_INT = re.compile(r"^[-+]?\d+$")
_FLOAT = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def read_table(text, delimiter=None):
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    if not rows:
        return [], []
    header = [h.strip() or "column_%d" % (i + 1) for i, h in enumerate(rows[0])]
    data = [r + [""] * (len(header) - len(r)) for r in rows[1:] if any(c.strip() for c in r)]
    return header, data


def is_missing(v):
    return v.strip().lower() in MISSING


def _parse_date(v):
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(v, f)
        except ValueError:
            pass
    return None


def infer_type(values):
    """Infer one of: empty, boolean, integer, float, date, categorical, text."""
    vals = [v.strip() for v in values if not is_missing(v)]
    if not vals:
        return "empty"
    low = {v.lower() for v in vals}
    if low <= {"true", "false", "yes", "no", "y", "n", "0", "1", "t", "f"} and len(low) <= 2 and not low <= {"0", "1"} \
            or low <= {"true", "false"}:
        return "boolean"
    if all(_INT.match(v) for v in vals):
        return "integer"
    if all(_FLOAT.match(v.replace(",", "")) for v in vals):
        return "float"
    if all(_parse_date(v) for v in vals[:200]):
        return "date"
    distinct = len(set(vals))
    if distinct <= max(20, int(0.05 * len(vals))) and distinct < len(vals):
        return "categorical"
    return "text"


def _quantile(sorted_vals, q):
    pos = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def profile_column(name, values):
    n = len(values)
    present = [v.strip() for v in values if not is_missing(v)]
    t = infer_type(values)
    p = {"name": name, "type": t, "count": n, "missing": n - len(present),
         "missing_pct": round(100.0 * (n - len(present)) / n, 1) if n else 0.0, "unique": len(set(present))}
    if t in ("integer", "float"):
        nums = sorted(float(v.replace(",", "")) for v in present)
        p.update({"min": nums[0], "q1": _quantile(nums, .25), "median": _quantile(nums, .5), "q3": _quantile(nums, .75),
                  "max": nums[-1], "mean": statistics.fmean(nums),
                  "std": statistics.stdev(nums) if len(nums) > 1 else 0.0, "zeros": sum(1 for x in nums if x == 0),
                  "negatives": sum(1 for x in nums if x < 0)})
        if p["std"] > 0 and len(nums) > 2:
            m, s = p["mean"], p["std"]
            p["skew"] = sum(((x - m) / s) ** 3 for x in nums) * len(nums) / ((len(nums) - 1) * (len(nums) - 2))
    elif t == "date":
        ds = sorted(_parse_date(v) for v in present)
        p.update({"min": ds[0].isoformat(), "max": ds[-1].isoformat(), "span_days": (ds[-1] - ds[0]).days})
    else:
        c = Counter(present)
        p["top"] = c.most_common(5)
        lens = [len(v) for v in present]
        if lens:
            p["min_length"], p["max_length"] = min(lens), max(lens)
        variants = {}
        for v in present:
            variants.setdefault(v.strip().lower(), set()).add(v)
        p["case_variants"] = sorted(sorted(s) for s in variants.values() if len(s) > 1)[:5]
    warnings = []
    if p["missing_pct"] > 20:
        warnings.append("more than 20% missing")
    if p["unique"] == 1 and present:
        warnings.append("constant column")
    if t in ("text", "categorical") and p["unique"] == len(present) and len(present) > 10:
        warnings.append("all values unique (identifier?)")
    if p.get("case_variants"):
        warnings.append("inconsistent capitalization/spacing in categories")
    mixed = [v for v in present if _FLOAT.match(v.replace(",", ""))]
    if t in ("text", "categorical") and 0.5 < len(mixed) / max(1, len(present)) < 1:
        warnings.append("mostly numeric with %d non-numeric value(s)" % (len(present) - len(mixed)))
    p["warnings"] = warnings
    return p


def profile(header, rows):
    cols = list(zip(*rows)) if rows else [[] for _ in header]
    dup = len(rows) - len({tuple(r) for r in rows})
    return {"rows": len(rows), "columns": len(header), "duplicate_rows": dup,
            "complete_rows": sum(1 for r in rows if not any(is_missing(v) for v in r)),
            "profiles": [profile_column(h, list(c)) for h, c in zip(header, cols)]}


def _fmt(v):
    if isinstance(v, float):
        return ("%.4g" % v) if abs(v) < 1e6 else ("%.3e" % v)
    return str(v)


def to_markdown(rep, title="Dataset profile"):
    lines = ["# %s" % title, "",
             "%d rows x %d columns, %d complete rows, %d duplicate rows" % (rep["rows"], rep["columns"],
                                                                           rep["complete_rows"], rep["duplicate_rows"]),
             "", "| Column | Type | Missing | Unique | Summary | Warnings |", "|---|---|---|---|---|---|"]
    for p in rep["profiles"]:
        if p["type"] in ("integer", "float"):
            s = "min %s, median %s, mean %s, max %s, sd %s" % tuple(_fmt(p[k]) for k in ("min", "median", "mean", "max", "std"))
        elif p["type"] == "date":
            s = "%s to %s" % (p["min"][:10], p["max"][:10])
        elif p.get("top"):
            s = ", ".join("%s (%d)" % (v[:20], n) for v, n in p["top"][:3])
        else:
            s = ""
        lines.append("| %s | %s | %d (%.1f%%) | %d | %s | %s |" % (p["name"], p["type"], p["missing"], p["missing_pct"],
                                                               p["unique"], s.replace("|", "/"), "; ".join(p["warnings"])))
    return "\n".join(lines) + "\n"
