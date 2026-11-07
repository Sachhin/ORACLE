"""Deterministic sample-neighbour imputer for paired PXD047528 DDA/DIA evaluation."""
from __future__ import annotations
import argparse, csv, json, math, statistics
from pathlib import Path


def read_matrix(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader=csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames or len(reader.fieldnames)<3:
            raise ValueError("Expected feature ID and at least two sample columns")
        feature_col=reader.fieldnames[0]; samples=reader.fieldnames[1:]
        if len(set(samples))!=len(samples): raise ValueError("Duplicate sample IDs")
        matrix={}
        for line,row in enumerate(reader,2):
            feature=(row.get(feature_col) or "").strip()
            if not feature or feature in matrix: raise ValueError(f"Invalid feature at line {line}")
            vals={}
            for s in samples:
                raw=(row.get(s) or "").strip()
                if raw in {"","NA","N/A","NaN","nan","null","NULL"}: vals[s]=None
                else:
                    x=float(raw)
                    if not math.isfinite(x): raise ValueError(f"Non-finite value at line {line}")
                    vals[s]=x
            matrix[feature]=vals
    return samples,matrix


def pearson(x,y):
    if len(x)<3:return None
    mx=sum(x)/len(x); my=sum(y)/len(y)
    dx=[v-mx for v in x]; dy=[v-my for v in y]
    den=math.sqrt(sum(v*v for v in dx)*sum(v*v for v in dy))
    return sum(a*b for a,b in zip(dx,dy))/den if den else None


def impute(observed_path, output_path, neighbors=5, min_overlap=30):
    if neighbors<1 or min_overlap<3: raise ValueError("Invalid neighbour settings")
    samples,matrix=read_matrix(observed_path)
    original={f:dict(row) for f,row in matrix.items()}
    # Sample similarity is computed only from measurements observed in both
    # samples. Correlation is invariant to additive sample offsets.
    similarities={}
    offsets={}
    for target in samples:
        ranked=[]
        for donor in samples:
            if donor==target: continue
            pairs=[(row[target],row[donor]) for row in matrix.values()
                   if row[target] is not None and row[donor] is not None]
            if len(pairs)<min_overlap: continue
            corr=pearson([p[0] for p in pairs],[p[1] for p in pairs])
            if corr is None: continue
            offset=float(statistics.median(a-b for a,b in pairs))
            ranked.append((corr,donor,offset,len(pairs)))
        ranked.sort(key=lambda z:(-z[0],z[1]))
        similarities[target]=ranked
    fallback=0; predicted=0
    for feature,row in matrix.items():
        available=[v for v in row.values() if v is not None]
        if not available: continue
        median=float(statistics.median(available))
        for target in samples:
            if row[target] is not None: continue
            candidates=[]
            for corr,donor,offset,n in similarities[target]:
                value=row[donor]
                if value is not None and corr>0:
                    weight=corr*corr
                    candidates.append((weight,value+offset))
                if len(candidates)>=neighbors: break
            if candidates:
                row[target]=sum(w*v for w,v in candidates)/sum(w for w,_ in candidates)
            else:
                row[target]=median; fallback+=1
            predicted+=1
    # Original observed measurements must remain byte-equivalent numerically.
    changed=[(f,s) for f in matrix for s in samples
             if original[f][s] is not None and matrix[f][s]!=original[f][s]]
    if changed: raise RuntimeError(f"Changed {len(changed)} observed cells")
    out=Path(output_path); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,delimiter="\t",lineterminator="\n")
        w.writerow(["Sequence",*samples])
        for feature in sorted(matrix):
            w.writerow([feature,*[ "" if matrix[feature][s] is None else format(matrix[feature][s],".12g") for s in samples]])
    return {"method":"sample-neighbour Pearson KNN with median additive sample-offset alignment",
            "neighbors":neighbors,"minimum_shared_observed_features":min_overlap,
            "samples":len(samples),"features":len(matrix),"imputed_cells":predicted,
            "median_fallback_cells":fallback,"observed_cells_preserved":True,
            "sample_neighbor_counts":{s:len(similarities[s]) for s in samples},
            "output":str(out)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--observed",required=True);p.add_argument("--output",required=True)
    p.add_argument("--neighbors",type=int,default=5);p.add_argument("--min-overlap",type=int,default=30)
    a=p.parse_args()
    print(json.dumps(impute(a.observed,a.output,a.neighbors,a.min_overlap),indent=2))
if __name__=="__main__":main()
