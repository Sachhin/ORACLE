"""Optional limma-voom adapter for explicit two-group raw-count GEO data."""
from __future__ import annotations
import csv, hashlib, math, shutil, subprocess, tempfile
from pathlib import Path
from typing import Mapping
from .geo_analysis import GEOExpressionAnalyzer

_SCRIPT = r'''
a <- commandArgs(trailingOnly=TRUE)
suppressPackageStartupMessages({
 if (!requireNamespace("edgeR",quietly=TRUE)) stop("edgeR is not installed.")
 if (!requireNamespace("limma",quietly=TRUE)) stop("limma is not installed.")
})
x <- read.delim(a[1],row.names=1,check.names=FALSE)
m <- read.delim(a[2],row.names=1,check.names=FALSE)
if (!identical(colnames(x),rownames(m))) stop("Sample order mismatch.")
m$group <- factor(m$group,levels=c(a[4],a[5]))
d <- model.matrix(~0+group,data=m); colnames(d) <- c("A","B")
if (qr(d)$rank<ncol(d)) stop("Rank-deficient design.")
y <- edgeR::DGEList(counts=as.matrix(x))
k <- edgeR::filterByExpr(y,design=d)
if (!any(k)) stop("No expressed features remain.")
y <- y[k,,keep.lib.sizes=FALSE]
y <- edgeR::calcNormFactors(y,method="TMM")
v <- limma::voom(y,d,plot=FALSE)
fit <- limma::lmFit(v,d)
fit <- limma::contrasts.fit(fit,limma::makeContrasts(B-A,levels=d))
fit <- limma::eBayes(fit)
z <- limma::topTable(fit,number=Inf,sort.by="none",adjust.method="BH")
z$feature <- rownames(z)
z <- z[,c("feature","logFC","AveExpr","t","P.Value","adj.P.Val","B")]
write.table(z,file=a[3],sep="\t",quote=FALSE,row.names=FALSE,na="NA")
cat(as.character(getRversion()),"\t",as.character(packageVersion("edgeR")),"\t",
 as.character(packageVersion("limma")),sep="")
'''

class VoomUnavailableError(RuntimeError):
    """Rscript, edgeR or limma is unavailable."""

class GEOVoomAnalyzer:
    """Run edgeR TMM + limma-voom on explicit two-group integer raw counts."""
    def analyze(self,path,group_labels:Mapping[str,str],group_a,group_b,
                rscript="Rscript",timeout_seconds=900,min_replicates=2,
                max_features=100000,max_cells=5000000):
        if not group_a or not group_b or group_a==group_b:
            raise ValueError("Two distinct contrast groups are required.")
        if timeout_seconds<1 or min_replicates<2:
            raise ValueError("Positive timeout and at least two replicates are required.")
        exe=shutil.which(rscript)
        if not exe: raise VoomUnavailableError(f"Cannot find {rscript!r}.")
        src=Path(path); text=GEOExpressionAnalyzer()._read_text(src)
        table=GEOExpressionAnalyzer._table_text(text)
        lines=table.splitlines()
        if not lines: raise ValueError("Empty expression matrix.")
        delim="\t" if lines[0].count("\t")>=lines[0].count(",") else ","
        reader=csv.reader(lines,delimiter=delim); header=next(reader)
        samples=[x.strip() for x in header[1:]]
        if not samples or any(not x for x in samples) or len(set(samples))!=len(samples):
            raise ValueError("Unique sample columns are required.")
        if set(group_labels)!=set(samples) or set(group_labels.values())!={group_a,group_b}:
            raise ValueError("Group labels must cover all samples and exactly two groups.")
        groups={g:[s for s in samples if group_labels[s]==g] for g in (group_a,group_b)}
        if any(len(v)<min_replicates for v in groups.values()):
            raise ValueError("Insufficient biological replicates.")
        features=[]; rows=[]; seen=set()
        for n,row in enumerate(reader,2):
            if not row or not any(v.strip() for v in row): continue
            if len(row)!=len(samples)+1: raise ValueError(f"Malformed row {n}.")
            feature=row[0].strip()
            if not feature or feature in seen: raise ValueError("Feature IDs must be unique.")
            seen.add(feature); values=[]
            for raw in row[1:]:
                value=GEOExpressionAnalyzer._number(raw)
                if value is None or value<0 or not value.is_integer():
                    raise ValueError("Voom requires finite non-negative integer raw counts.")
                values.append(int(value))
            features.append(feature); rows.append(values)
            if len(features)>max_features or len(features)*len(samples)>max_cells:
                raise ValueError("Matrix exceeds configured size limits.")
        if not rows: raise ValueError("No count rows found.")
        digest=hashlib.sha256(src.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="oracle-voom-") as tmp:
            root=Path(tmp); counts=root/"counts.tsv"; meta=root/"meta.tsv"
            script=root/"run.R"; output=root/"out.tsv"
            with counts.open("w",encoding="utf-8",newline="") as h:
                w=csv.writer(h,delimiter="\t",lineterminator="\n"); w.writerow(["feature",*samples])
                for f,v in zip(features,rows): w.writerow([f,*v])
            with meta.open("w",encoding="utf-8",newline="") as h:
                w=csv.writer(h,delimiter="\t",lineterminator="\n"); w.writerow(["sample","group"])
                for s in samples: w.writerow([s,group_labels[s]])
            script.write_text(_SCRIPT,encoding="utf-8")
            try:
                run=subprocess.run([exe,"--vanilla",str(script),str(counts),str(meta),
                    str(output),group_a,group_b],capture_output=True,text=True,
                    timeout=timeout_seconds,check=False)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("limma-voom timed out.") from exc
            if run.returncode:
                detail=(run.stderr or run.stdout or "R analysis failed").strip()
                if "not installed" in detail: raise VoomUnavailableError(detail[-2000:])
                raise RuntimeError(f"limma-voom failed: {detail[-4000:]}")
            if not output.is_file(): raise RuntimeError("limma-voom produced no result file.")
            versions=(run.stdout or "").strip().split("\t")
            if len(versions)!=3: raise RuntimeError("Missing R/edgeR/limma version provenance.")
            results=[]
            with output.open(encoding="utf-8",newline="") as h:
                for item in csv.DictReader(h,delimiter="\t"):
                    def number(key):
                        raw=item.get(key,"")
                        if raw in {"","NA","NaN"}: return None
                        value=float(raw)
                        return value if math.isfinite(value) else None
                    results.append({"feature":item["feature"],"log2_fold_change":number("logFC"),
                        "average_log_expression":number("AveExpr"),"moderated_t":number("t"),
                        "p_value":number("P.Value"),"p_value_adjusted_bh":number("adj.P.Val"),
                        "b_statistic":number("B")})
        results.sort(key=lambda x:(x["p_value_adjusted_bh"] is None,
            x["p_value_adjusted_bh"] if x["p_value_adjusted_bh"] is not None else 1,
            x["feature"]))
        return {"method":"edgeR TMM + limma-voom + empirical Bayes",
            "contrast":{"group_a":group_a,"group_b":group_b,"direction":f"{group_b} vs {group_a}"},
            "sample_groups":groups,"sample_count":len(samples),"features_input":len(features),"features_returned":len(results),\n            "features_with_adjusted_p_value":sum(x["p_value_adjusted_bh"] is not None for x in results),
            "matrix_sha256":digest,"software":{"r":versions[0],"edgeR":versions[1],"limma":versions[2]},
            "results":results,"limitations":"Requires raw integer counts, biological replicates and explicit two-group labels. No covariates or group inference. Review sample QC, filtering and design assumptions. Results are associations, not causal discoveries."}
