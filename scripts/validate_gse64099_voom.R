#!/usr/bin/env Rscript
# Independent GEO experiment validation against the published Smchd1 analysis.
# Dataset: GSE64099; reference: Liu et al. (2014) supplementary analysis PDF.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Usage: validate_gse64099_voom.R OUTPUT_REPORT.json")
report_path <- args[[1]]
required <- c("edgeR", "limma", "digest", "jsonlite")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Missing R packages: ", paste(missing, collapse = ", "))
library(edgeR)
library(limma)

source_url <- "https://bioinf.wehi.edu.au/voomWithQualityWeights/smchd1/x.rda"
rda_path <- tempfile(fileext = ".rda")
download.file(source_url, rda_path, mode = "wb", quiet = TRUE)
source_sha256 <- digest::digest(file = rda_path, algo = "sha256", serialize = FALSE)
load(rda_path)
if (!exists("x") || !inherits(x, "DGEList")) stop("Published x.rda did not contain an edgeR DGEList named x")

# Reproduce the published GSE64099 analysis code, including its CPM filter,
# TMM normalization, group design, limma-voom, lmFit, and empirical Bayes.
full_feature_count <- nrow(x$counts)
full_sample_count <- ncol(x$counts)
if (full_sample_count != 7) stop("Expected the published seven-sample GSE64099 experiment")
fullanno <- x$genes
sel <- rowSums(edgeR::cpm(x$counts) > 0.5) >= 3
x <- x[sel, , keep.lib.sizes = FALSE]
if (nrow(x$counts) < 100) stop("Unexpectedly few genes remain after the published CPM filter")
x$genes <- x$genes[, c(1, 3), drop = FALSE]
design <- model.matrix(~x$samples$group)
if (ncol(design) != 2) stop("Expected a two-group Smchd1 null vs WT design")
colnames(design)[2] <- "Smchd1nullvsWt"
x <- edgeR::calcNormFactors(x, method = "TMM")
v <- limma::voom(x, design = design, plot = FALSE)
fit <- limma::eBayes(limma::lmFit(v))
top <- limma::topTable(fit, coef = 2, number = Inf, sort.by = "P")
if (!"GeneID" %in% colnames(top)) stop("Published gene identifier column was not retained")

# Frozen values transcribed from the published supplementary PDF's voom-only
# topTable (Smchd1.pdf, pp. 1-2): top ten logFC values and FDR hit counts.
published <- data.frame(
  GeneID = c("74355", "18028", "75605", "667435", "381126",
             "381413", "75033", "69136", "233552", "80890"),
  Symbol = c("Smchd1", "Nfib", "Kdm5b", "Igkv17-121", "Garem",
             "Gpr176", "Mei4", "Tusc1", "Gdpd5", "Trim2"),
  logFC = c(-3.12, 8.98, -3.55, -5.35, 6.17, -4.02, 6.44, 5.67, -2.82, -1.43),
  stringsAsFactors = FALSE
)
top$GeneID <- as.character(top$GeneID)
published$GeneID <- as.character(published$GeneID)
matched <- merge(published, top[, c("GeneID", "logFC", "adj.P.Val")],
                 by = "GeneID", suffixes = c("_published", "_recomputed"))
if (nrow(matched) < 8) stop("Fewer than eight published top-ten genes matched by stable GeneID")
delta <- matched$logFC_recomputed - matched$logFC_published
top10_ids <- as.character(head(top$GeneID, 10))
top10_recall <- length(intersect(published$GeneID, top10_ids)) / nrow(published)
direction_agreement <- mean(sign(matched$logFC_recomputed) == sign(matched$logFC_published))
logfc_rmse <- sqrt(mean(delta^2))
fdr05 <- sum(top$adj.P.Val < 0.05, na.rm = TRUE)
fdr01 <- sum(top$adj.P.Val < 0.01, na.rm = TRUE)
published_fdr05 <- 12L
published_fdr01 <- 1L

# Freeze numerical outputs so the run can be independently audited.
out_dir <- dirname(report_path)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
E_path <- file.path(out_dir, "gse64099_voom_E.tsv.gz")
W_path <- file.path(out_dir, "gse64099_voom_weights.tsv.gz")
utils::write.table(cbind(GeneID = rownames(v$E), v$E), gzfile(E_path),
                   sep = "\t", quote = FALSE, row.names = FALSE)
utils::write.table(cbind(GeneID = rownames(v$weights), v$weights), gzfile(W_path),
                   sep = "\t", quote = FALSE, row.names = FALSE)

report <- list(
  status = if (top10_recall >= 0.8 && direction_agreement >= 0.9 &&
               logfc_rmse <= 0.5 && abs(fdr05 - published_fdr05) <= 5) "PASS" else "FAIL",
  dataset_accession = "GSE64099",
  dataset_title = "Smchd1 knockout versus wild-type mouse experiment",
  source_url = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE64099",
  reference_source_url = "https://bioinf.wehi.edu.au/voomWithQualityWeights/smchd1/Smchd1.pdf",
  reference_method = "Published edgeR TMM + limma voom; design ~ genotype group",
  sample_count = ncol(x$counts),
  feature_count_after_published_filter = nrow(x$counts),
  feature_count_before_filter = full_feature_count,
  sample_count_before_filter = full_sample_count,
  software = list(R = R.version.string,
                  edgeR = as.character(packageVersion("edgeR")),
                  limma = as.character(packageVersion("limma"))),
  published_reference = list(
    top10_gene_logFC = published,
    fdr_below_0_05 = published_fdr05,
    fdr_below_0_01 = published_fdr01
  ),
  recomputed = list(
    top10 = top[, c("GeneID", "logFC", "P.Value", "adj.P.Val")][seq_len(min(10, nrow(top))), , drop = FALSE],
    fdr_below_0_05 = fdr05,
    fdr_below_0_01 = fdr01
  ),
  comparison = list(
    matched_published_top10_genes = nrow(matched),
    top10_recall = top10_recall,
    logFC_rmse = logfc_rmse,
    logFC_direction_agreement = direction_agreement,
    fdr05_count_difference = fdr05 - published_fdr05,
    fdr01_count_difference = fdr01 - published_fdr01
  ),
  thresholds = list(top10_recall_min = 0.8, logFC_rmse_max = 0.5,
                    direction_agreement_min = 0.9, fdr05_count_difference_abs_max = 5),
  source_rda_sha256 = source_sha256,
  generated_output_sha256 = list(
    voom_E = digest::digest(file = E_path, algo = "sha256", serialize = FALSE),
    voom_weights = digest::digest(file = W_path, algo = "sha256", serialize = FALSE)
  ),
  limitations = paste(
    "This is a second independent GEO experiment and an external comparison",
    "against the published top-table results, not a published E/weights matrix.",
    "Differences can arise from R/Bioconductor version drift; full matrices are",
    "frozen for audit but are not claimed to be the submitter's original outputs."
  )
)
jsonlite::write_json(report, report_path, auto_unbox = TRUE, pretty = TRUE,
                     dataframe = "rows", na = "null")
if (report$status != "PASS") stop("GSE64099 published result comparison failed thresholds")
