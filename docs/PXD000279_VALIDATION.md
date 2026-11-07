# PXD000279 controlled-mixture benchmark

ORACLE includes a reproducible benchmark for the public MaxQuant
HeLa/E. coli controlled-mixture dataset.

## Ground truth and method

The published design has three E. coli 10% replicates (L1-L3) and three
E. coli 30% replicates (H1-H3), with a constant HeLa input. Expected
Ecoli30-versus-Ecoli10 log2 fold change is therefore 0 for human proteins and
log2(3) for E. coli proteins. Species are assigned from MaxQuant FASTA
organism annotations. Decoys, contaminants, site-only identifications,
ambiguous species, and proteins with fewer than two measured replicates in
either group are excluded.

The benchmark evaluates observed-only group effects and two explicit missing
value baselines (per-protein row median and seeded per-sample left-censored
Gaussian/MinProb). It measures downstream ratio recovery under the deposited
missingness; it does not claim that each missing cell has a known exact value.

## Run

```bash
curl --fail --location https://ftp.ebi.ac.uk/pride-archive/2014/09/PXD000279/proteomebenchmark.zip -o proteomebenchmark.zip
unzip -q proteomebenchmark.zip -d pxd000279
python scripts/benchmark_pxd000279_mixture.py --input pxd000279/proteinGroups.txt --output pxd000279/known-mixture-report.json
```

The script detects explicit condition labels when available. Otherwise it
uses the published DEqMS PXD000279 LFQ column contract (columns 89-91 H =
Ecoli30; 92-94 L = Ecoli10), and fails closed if that exact layout is absent.

## Empirical report

GitHub Actions run
[42253421249](https://github.com/Sachhin/ORACLE/actions/runs/42253421249)
downloaded the published MaxQuant output and generated a hashed report:

- 5,019 proteins in the scored universe; 612 / 30,114 LFQ cells missing
  (2.03%).
- Human expected log2 fold change: 0. Observed-only median: -0.510;
  row-median: -0.504; MinProb: -0.549.
- E. coli expected log2 fold change: log2(3) = 1.585. Observed-only median:
  1.219; row-median: 1.205; MinProb: 1.226.
- The row-median baseline did not outperform observed-only on the E. coli
  median ratio error; MinProb was worse on the reported MAE/RMSE metrics.

This is a completed controlled-mixture scoring run, not a claim that an
imputer has passed every performance criterion or that one method is
universally superior. The result indicates systematic ratio attenuation and
a non-zero human offset in this dataset; investigate normalization, protein
identification, and replicate effects before drawing broader conclusions.

Source publication DOI: 10.1074/mcp.M113.031591.
Dataset: https://www.ebi.ac.uk/pride/archive/projects/PXD000279
