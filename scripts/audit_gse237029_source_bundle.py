#!/usr/bin/env python3
"""Authenticate GSE237029 GEO metadata and inventory the nine raw GPL570 CEL files."""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, re, tarfile
from pathlib import Path

EXPECTED = {f"GSM{i}" for i in range(7593228, 7593237)}
ACC = re.compile(r"^!Sample_geo_accession\s*=\s*(GSM\d+)\s*$")
TITLE = re.compile(r"^!Sample_title\s*=\s*(.*?)\s*$")
CHAR = re.compile(r"^!Sample_characteristics_ch1\s*=\s*(.*?)\s*$")

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""): h.update(block)
    return h.hexdigest()

def parse_soft(path: Path) -> list[dict]:
    records=[]; cur=None
    with gzip.open(path,"rt",encoding="utf-8",errors="replace") as f:
        for raw in f:
            line=raw.rstrip("\r\n")
            if line.startswith("^SAMPLE = "):
                if cur and cur.get("accession"): records.append(cur)
                cur={"accession":"","title":"","characteristics":[]}
            elif cur is not None:
                m=ACC.match(line)
                if m: cur["accession"]=m.group(1); continue
                m=TITLE.match(line)
                if m: cur["title"]=m.group(1); continue
                m=CHAR.match(line)
                if m: cur["characteristics"].append(m.group(1))
    if cur and cur.get("accession"): records.append(cur)
    return records

def audit(soft: Path, raw_tar: Path, outdir: Path) -> dict:
    records=parse_soft(soft); ids=[x["accession"] for x in records]; issues=[]
    if len(records)!=9 or set(ids)!=EXPECTED or len(set(ids))!=9:
        issues.append(f"Expected exact nine GEO records {sorted(EXPECTED)}; found {ids}")
    outdir.mkdir(parents=True,exist_ok=True); cel_dir=outdir/"cel"; cel_dir.mkdir(exist_ok=True)
    found={}
    with tarfile.open(raw_tar,"r:*") as tf:
        for member in tf.getmembers():
            if not member.isfile() or not member.name.lower().endswith(".cel.gz"): continue
            name=Path(member.name).name
            m=re.match(r"(GSM\d+).*\.CEL\.gz$",name,re.I)
            if not m: issues.append(f"Unrecognized CEL filename: {name}"); continue
            gsm=m.group(1)
            if gsm in found: issues.append(f"Duplicate CEL for {gsm}"); continue
            src=tf.extractfile(member)
            if src is None: issues.append(f"Cannot read tar member {name}"); continue
            target=cel_dir/(gsm+".CEL")
            with gzip.GzipFile(fileobj=src,mode="rb") as gz, target.open("wb") as dst:
                while True:
                    block=gz.read(1024*1024)
                    if not block: break
                    dst.write(block)
            if target.stat().st_size==0: issues.append(f"Empty decompressed CEL: {gsm}")
            found[gsm]={"path":str(target),"bytes":target.stat().st_size,"sha256":sha256(target),"archive_member":member.name}
    if set(found)!=EXPECTED: issues.append(f"Expected nine CEL files; found {sorted(found)}")
    manifest=[]
    for rec in records:
        chars=rec["characteristics"]
        age=[v.split(":",1)[1].strip() for v in chars if v.lower().startswith("age:")]
        gender=[v.split(":",1)[1].strip() for v in chars if v.lower().startswith(("gender:","sex:"))]
        manifest.append({"sample_accession":rec["accession"],"title":rec["title"],
                         "age_category":age[0] if len(age)==1 else "",
                         "gender":gender[0] if len(gender)==1 else "",
                         "cel_path":found.get(rec["accession"],{}).get("path",""),
                         "cel_sha256":found.get(rec["accession"],{}).get("sha256","")})
    if any(not row["age_category"] for row in manifest): issues.append("At least one sample lacks a unique explicit age-category field.")
    if any(not row["cel_path"] for row in manifest): issues.append("At least one GEO sample has no matched CEL file.")
    fields=["sample_accession","title","age_category","gender","cel_path","cel_sha256"]
    with (outdir/"sample_manifest.tsv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter="\t"); w.writeheader(); w.writerows(manifest)
    report={"dataset":"GSE237029","evidence_class":"small_n_human_age_reference_not_longevity_replication",
            "status":"PASS_SOURCE_BUNDLE" if not issues else "BLOCKED_SOURCE_BUNDLE",
            "sample_count":len(records),"matched_cel_count":len(found),"samples":manifest,
            "raw_tar_bytes":raw_tar.stat().st_size,"raw_tar_sha256":sha256(raw_tar),
            "soft_bytes":soft.stat().st_size,"soft_sha256":sha256(soft),"issues":issues,
            "limitations":["Only age categories (not exact ages) are source-authenticated.",
                           "n=5 old and n=4 middle-aged; exploratory panel sensitivity only.",
                           "Submitter processed values are GCOS signals scaled to target intensity 200, not RMA.",
                           "No exceptional-longevity group or causal mechanism is tested."]}
    (outdir/"source_audit.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    if issues: raise SystemExit(json.dumps(report,indent=2))
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--soft",type=Path,required=True); p.add_argument("--raw-tar",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args()
    print(json.dumps(audit(a.soft,a.raw_tar,a.output_dir),indent=2))
if __name__=="__main__": main()
