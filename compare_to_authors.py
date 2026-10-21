"""
Compare your features_P??.csv files against the authors' BrainMetastases_radiomics_data.xlsx.

Usage:
    python compare_to_authors.py                      # defaults
    python compare_to_authors.py --rtol 1e-3          # looser tolerance
    python compare_to_authors.py --ours features_P01.csv --theirs BrainMetastases_radiomics_data.xlsx
"""

import argparse
import glob
import sys
import numpy as np
import pandas as pd
import re



FEATURE_COL_CANDIDATES = ["Radiomics Feature", "RadiomicsFeature", "feature", "rads", "Feature"]
VALUE_COL_CANDIDATES   = ["Radiomics Value",   "RadiomicsValue",   "value", "Value"]
PATIENT_COL_CANDIDATES = ["patient_id", "Patient", "PatientID", "patient", "id"]


def pick_col(df, candidates, label):
    for c in candidates:
        if c in df.columns:
            return c
    raise SystemExit(f"[FATAL] couldn't find a {label} column in {list(df.columns)[:10]}...")


def load_ours(path_glob):
    """Our CSVs are already long-format: patient_id, Radiomics Feature, Radiomics Value."""
    frames = []
    for p in sorted(glob.glob(path_glob)):
        df = pd.read_csv(p)
        feat = pick_col(df, FEATURE_COL_CANDIDATES, "feature")
        val  = pick_col(df, VALUE_COL_CANDIDATES, "value")
        pat  = pick_col(df, PATIENT_COL_CANDIDATES, "patient")
        df = df[[pat, feat, val]].rename(columns={pat: "patient_id", feat: "feature", val: "value"})
        frames.append(df)
    if not frames:
        raise SystemExit(f"[FATAL] no CSV files matched: {path_glob}")
    out = pd.concat(frames, ignore_index=True)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    return out


def load_theirs(path):
    """Try every sheet. Reshape wide -> long if needed."""
    xl = pd.ExcelFile(path)
    frames = []
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        if df.empty:
            continue

        # Case A: long format already (one row per feature)
        feat_candidates_present = [c for c in FEATURE_COL_CANDIDATES if c in df.columns]
        val_candidates_present  = [c for c in VALUE_COL_CANDIDATES   if c in df.columns]
        if feat_candidates_present and val_candidates_present:
            feat = feat_candidates_present[0]
            val  = val_candidates_present[0]
            pat_cols = [c for c in PATIENT_COL_CANDIDATES if c in df.columns]
            if pat_cols:
                pat = pat_cols[0]
                frames.append(df[[pat, feat, val]].rename(
                    columns={pat: "patient_id", feat: "feature", val: "value"}))
            else:
                # No explicit patient column — maybe sheet name is the patient ID
                frames.append(df[[feat, val]].rename(
                    columns={feat: "feature", val: "value"}).assign(patient_id=sheet))
            continue

        # Case B: wide format (one row per patient, columns = features)
        pat_cols = [c for c in PATIENT_COL_CANDIDATES if c in df.columns]
        if pat_cols:
            pat = pat_cols[0]
            long = df.melt(id_vars=[pat], var_name="feature", value_name="value")
            long = long.rename(columns={pat: "patient_id"})
            frames.append(long)
            continue

        # Case C: can't tell — skip, but warn
        print(f"[WARN] sheet '{sheet}' columns look unfamiliar: {list(df.columns)[:6]} — skipping")

    if not frames:
        raise SystemExit(f"[FATAL] could not interpret {path}")
    out = pd.concat(frames, ignore_index=True)
    out["value"]      = pd.to_numeric(out["value"], errors="coerce")
    out["patient_id"] = out["patient_id"].astype(str).str.strip()
    out["feature"]    = out["feature"].astype(str).str.strip()
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ours",   default="outputs/features_P*.csv")
    p.add_argument("--theirs", default="BrainMetastases_radiomics_data.xlsx")
    p.add_argument("--rtol",   type=float, default=1e-4, help="relative tolerance for 'match'")
    p.add_argument("--atol",   type=float, default=1e-6, help="absolute tolerance for 'match'")
    p.add_argument("--out",    default="comparison_report.csv")
    args = p.parse_args()

    print(f"Loading ours   : {args.ours}")
    ours = load_ours(args.ours)
    print(f"  {len(ours):>7d} rows, {ours['patient_id'].nunique()} patient(s)")

    print(f"Loading theirs : {args.theirs}")
    theirs = load_theirs(args.theirs)
    print(f"  {len(theirs):>7d} rows, {theirs['patient_id'].nunique()} patient(s)")

    # Normalize for joining
    def normalize_feature(s: str) -> str:
        s = str(s).strip()
        # fuN  <->  follow_up_N (unify to follow_up_N)
        s = re.sub(r"__fu(\d+)__", r"__follow_up_\1__", s)
        return s

    for df in (ours, theirs):
        df["patient_id"] = df["patient_id"].astype(str).str.strip()
        df["feature"]    = df["feature"].map(normalize_feature)

    # Restrict theirs to the patients we actually extracted
    our_patients = set(ours["patient_id"])
    theirs = theirs[theirs["patient_id"].isin(our_patients)]
    print(f"  (filtered to {len(theirs)} rows for patients {sorted(our_patients)})")

    # Inner join on (patient, feature)
    merged = ours.merge(theirs, on=["patient_id", "feature"],
                        suffixes=("_ours", "_theirs"))
    merged = merged.dropna(subset=["value_ours", "value_theirs"])

    merged["abs_diff"] = (merged["value_ours"] - merged["value_theirs"]).abs()
    denom = merged["value_theirs"].abs().replace(0, np.nan)
    merged["rel_diff"] = merged["abs_diff"] / denom
    merged["match"]    = np.isclose(merged["value_ours"], merged["value_theirs"],
                                    rtol=args.rtol, atol=args.atol)

    # Which features are in only one side?
    ours_keys   = set(zip(ours["patient_id"],   ours["feature"]))
    theirs_keys = set(zip(theirs["patient_id"], theirs["feature"]))
    only_ours   = ours_keys - theirs_keys
    only_theirs = theirs_keys - ours_keys

    # ---- Report ----
    print()
    print("=" * 60)
    print(" SUMMARY")
    print("=" * 60)
    print(f"  features in ours   : {len(ours_keys)}")
    print(f"  features in theirs : {len(theirs_keys)}")
    print(f"  matched by name    : {len(merged)}")
    print(f"  only in ours       : {len(only_ours)}")
    print(f"  only in theirs     : {len(only_theirs)}")
    print()
    if len(merged):
        print(f"  values within rtol={args.rtol}, atol={args.atol}:")
        print(f"      {merged['match'].sum()} / {len(merged)}  "
              f"({100*merged['match'].mean():.1f}%)")
        print()
        print("  worst 20 mismatches by relative diff:")
        worst = merged.sort_values("rel_diff", ascending=False).head(20)
        print(worst[["patient_id", "feature", "value_ours",
                     "value_theirs", "abs_diff", "rel_diff"]].to_string(index=False))

    # Save full report
    merged.to_csv(args.out, index=False)
    print(f"\nFull per-feature report written to: {args.out}")

    if only_ours:
        print(f"\nSample of 10 features only in ours (not in theirs):")
        for k in list(only_ours)[:10]:
            print(f"  {k}")
    if only_theirs:
        print(f"\nSample of 10 features only in theirs (not in ours):")
        for k in list(only_theirs)[:10]:
            print(f"  {k}")

    sys.exit(0 if len(merged) and merged["match"].all() else 1)


if __name__ == "__main__":
    main()