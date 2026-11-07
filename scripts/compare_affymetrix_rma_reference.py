"""Compare ORACLE Affymetrix RMA output with a published same-platform GEO matrix."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, statistics
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_matrix(path: str):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fields = reader.fieldnames or []
        if len(fields) < 3:
            raise ValueError(f"{path}: expected feature ID and at least two samples")
        feature_col, samples = fields[0], fields[1:]
        if len(set(samples)) != len(samples) or any(not x for x in samples):
            raise ValueError(f"{path}: sample identifiers must be unique")
        matrix = {}
        for line, row in enumerate(reader, start=2):
            feature = (row.get(feature_col) or "").strip()
            if not feature or feature in matrix:
                raise ValueError(f"{path}:{line}: duplicate or empty feature identifier")
            values = {}
            for sample in samples:
                raw = (row.get(sample) or "").strip()
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(f"{path}:{line}: invalid value for {sample}: {raw!r}") from exc
                if not math.isfinite(value):
                    raise ValueError(f"{path}:{line}: non-finite value for {sample}")
                values[sample] = value
            matrix[feature] = values
    if not matrix:
        raise ValueError(f"{path}: no feature rows")
    return samples, matrix


def pearson(x, y):
    if len(x) < 2:
        return None
    mx, my = statistics.mean(x), statistics.mean(y)
    dx, dy = [v-mx for v in x], [v-my for v in y]
    den = math.sqrt(sum(v*v for v in dx) * sum(v*v for v in dy))
    return sum(a*b for a,b in zip(dx,dy))/den if den else None


def compare(oracle_path, reference_path, *, max_rmse=0.25, min_pearson=0.995):
    osamples, om = read_matrix(oracle_path)
    rsamples, rm = read_matrix(reference_path)
    if set(osamples) != set(rsamples) or len(osamples) != len(rsamples):
        raise ValueError("Oracle and GEO reference sample identifiers do not exactly match")
    common = sorted(set(om) & set(rm))
    overlap = len(common) / min(len(om), len(rm))
    if overlap < 0.95:
        raise ValueError(f"Probe-set overlap {overlap:.4f} is below 0.95")
    errors, ox, rx, per_sample = [], [], [], {}
    for sample in osamples:
        sx, sy = [], []
        for feature in common:
            a, b = om[feature][sample], rm[feature][sample]
            sx.append(a); sy.append(b); errors.append(a-b)
        e = [a-b for a,b in zip(sx,sy)]
        per_sample[sample] = {
            "n": len(e),
            "mae": statistics.mean(abs(v) for v in e),
            "rmse": math.sqrt(statistics.mean(v*v for v in e)),
            "pearson_r": pearson(sx,sy),
        }
        ox.extend(sx); rx.extend(sy)
    mae = statistics.mean(abs(v) for v in errors)
    rmse = math.sqrt(statistics.mean(v*v for v in errors))
    corr = pearson(ox,rx)
    passed = rmse <= max_rmse and corr is not None and corr >= min_pearson
    return {
        "dataset": "GSE12837",
        "platform": "GPL96 / Affymetrix HG-U133A",
        "reference_processing": "GEO submitter-deposited RMA signal; sample records describe Bioconductor RMA preprocessing",
        "oracle_processing": "ORACLE affy::rma on all 24 raw CEL files from the same GEO series",
        "sample_count": len(osamples),
        "feature_count_oracle": len(om),
        "feature_count_reference": len(rm),
        "matched_probe_sets": len(common),
        "probe_set_overlap_fraction": overlap,
        "metrics": {"n": len(errors), "mae": mae, "rmse": rmse, "pearson_r": corr},
        "per_sample": per_sample,
        "thresholds": {"max_rmse": max_rmse, "min_pearson_r": min_pearson},
        "status": "PASS" if passed else "FAIL_NUMERICAL_TOLERANCE",
        "provenance": {
            "oracle_matrix_sha256": sha256(Path(oracle_path)),
            "geo_reference_matrix_sha256": sha256(Path(reference_path)),
        },
        "limitations": (
            "This is a same-study, same-platform implementation comparison against the submitter's "
            "RMA-processed GEO matrix. It validates preprocessing reproducibility for GSE12837 only; "
            "it does not establish universal Affymetrix platform accuracy or biological validity."
        ),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--oracle", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--max-rmse", type=float, default=0.25)
    p.add_argument("--min-pearson", type=float, default=0.995)
    a = p.parse_args()
    report = compare(a.oracle, a.reference, max_rmse=a.max_rmse, min_pearson=a.min_pearson)
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
