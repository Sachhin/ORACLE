#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(edgeR))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3) {
  stop("Usage: edgeR_riken2018_mrpg.R <pseudobulk_counts.tsv> <donor_metadata.tsv> <output_dir>")
}
counts_path <- args[[1]]
metadata_path <- args[[2]]
outdir <- args[[3]]
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

counts_df <- read.delim(counts_path, check.names = FALSE, stringsAsFactors = FALSE)
if (!"gene_symbol" %in% names(counts_df)) stop("Counts table must have gene_symbol column")
rownames(counts_df) <- counts_df$gene_symbol
counts_df$gene_symbol <- NULL
counts <- as.matrix(counts_df)
storage.mode(counts) <- "integer"

metadata <- read.delim(metadata_path, stringsAsFactors = FALSE)
if (!all(colnames(counts) %in% metadata$patient)) stop("Donor metadata does not cover all count columns")
metadata <- metadata[match(colnames(counts), metadata$patient), ]
group <- factor(metadata$group, levels = c("CT", "SC"))
if (anyNA(group) || sum(group == "SC") != 7 || sum(group == "CT") != 5) {
  stop("Expected seven SC and five CT biological donors")
}

y <- DGEList(counts = counts, group = group)
keep <- filterByExpr(y, group = group)
y <- y[keep, , keep.lib.sizes = FALSE]
y <- calcNormFactors(y, method = "TMM")
y <- estimateDisp(y, robust = TRUE)
test <- exactTest(y, pair = c("CT", "SC"))
tab <- topTags(test, n = Inf, sort.by = "PValue")$table
tab$gene_symbol <- rownames(tab)
tab <- tab[, c("gene_symbol", "logFC", "logCPM", "PValue", "FDR")]
write.table(tab, file.path(outdir, paste0("edger_all_genes_", label, ".tsv")), sep = "\t", quote = FALSE, row.names = FALSE)

panel <- c("MRPL3", "MRPL32", "MRPL42", "MRPL45", "MRPL50", "MRPS10", "MRPS33", "MRPS35")
missing <- setdiff(panel, rownames(tab))
if (length(missing)) stop(paste("Missing mRPG8 genes after expression filtering:", paste(missing, collapse = ", ")))
panel_tab <- tab[match(panel, tab$gene_symbol), ]
write.table(panel_tab, file.path(outdir, paste0("mRPG8_gene_results_", label, ".tsv")), sep = "\t", quote = FALSE, row.names = FALSE)

logcpm <- cpm(y, log = TRUE, prior.count = 2)
panel_logcpm <- logcpm[panel, , drop = FALSE]
panel_z <- t(scale(t(panel_logcpm)))
scores <- colMeans(panel_z)
score_df <- data.frame(
  patient = metadata$patient,
  group = as.character(group),
  mRPG8_score = as.numeric(scores),
  stringsAsFactors = FALSE
)
write.table(score_df, file.path(outdir, paste0("mRPG8_panel_scores_", label, ".tsv")), sep = "\t", quote = FALSE, row.names = FALSE)

observed <- mean(scores[group == "SC"]) - mean(scores[group == "CT"])
combinations <- combn(seq_along(scores), sum(group == "SC"))
permuted <- apply(combinations, 2, function(idx) {
  is_sc <- seq_along(scores) %in% idx
  mean(scores[is_sc]) - mean(scores[!is_sc])
})
permutation_p <- mean(abs(permuted) >= abs(observed) - 1e-12)

summary <- data.frame(
  metric = c(
    "n_SC_donors", "n_CT_donors", "mRPG8_score_mean_SC",
    "mRPG8_score_mean_CT", "mRPG8_score_difference_SC_minus_CT",
    "mRPG8_exact_two_sided_permutation_p", "permutation_assignments",
    "normalization", "differential_expression_method"
  ),
  value = c(
    sum(group == "SC"), sum(group == "CT"),
    mean(scores[group == "SC"]), mean(scores[group == "CT"]),
    observed, permutation_p, ncol(combinations),
    "edgeR TMM; log2 CPM with prior.count=2; per-gene z-score across 12 donors",
    "edgeR robust dispersion and exactTest; SC versus CT"
  ),
  stringsAsFactors = FALSE
)
write.table(summary, file.path(outdir, paste0("mRPG8_panel_summary_", label, ".tsv")), sep = "\t", quote = FALSE, row.names = FALSE)
writeLines(capture.output(sessionInfo()), file.path(outdir, paste0("R_sessionInfo_", label, ".txt")))
cat("RIKEN SC2018 edgeR complete\n")
print(summary)
