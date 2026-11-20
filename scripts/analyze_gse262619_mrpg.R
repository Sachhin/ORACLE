#!/usr/bin/env Rscript
# Exploratory, age-reference-only test of the published 8-mRPG panel in GSE262619.
# This is not an exceptional-longevity replication or a causal analysis.
suppressPackageStartupMessages({
  library(edgeR)
  library(limma)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("Usage: analyze_gse262619_mrpg.R counts.txt.gz sample_manifest.tsv output_dir")
}
counts_path <- args[[1]]
manifest_path <- args[[2]]
outdir <- args[[3]]
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

mrpg8 <- c("MRPL3", "MRPL32", "MRPL42", "MRPL45",
           "MRPL50", "MRPS10", "MRPS33", "MRPS35")
crpg7 <- c("RPL10A", "RPL22", "RPL4", "RPL5", "RPS13", "RPS23", "RPS6")

manifest <- read.delim(manifest_path, check.names = FALSE, stringsAsFactors = FALSE)
required_manifest <- c("sample_accession", "title", "explicit_age_years", "title_sex")
if (!all(required_manifest %in% colnames(manifest))) {
  stop("Sample manifest is missing required source fields")
}
if (nrow(manifest) != 35 || anyDuplicated(manifest$sample_accession) ||
    anyDuplicated(manifest$title)) {
  stop("Expected 35 unique GEO sample accessions and unique submitter titles")
}
manifest$age_years <- suppressWarnings(as.numeric(manifest$explicit_age_years))
manifest$sex <- factor(manifest$title_sex, levels = c("female", "male"))
if (any(!is.finite(manifest$age_years)) ||
    any(manifest$age_years < 0 | manifest$age_years > 120) ||
    any(is.na(manifest$sex))) {
  stop("Exact age or title-coded sex is missing/invalid; refusing to model")
}

raw <- read.delim(gzfile(counts_path), check.names = FALSE,
                  stringsAsFactors = FALSE, quote = "", comment.char = "")
sample_columns <- paste0("count.G", manifest$title)
if (anyDuplicated(sample_columns) || !all(sample_columns %in% colnames(raw))) {
  stop("Count-table columns do not exactly match all 35 source-authenticated sample titles")
}
count_matrix <- as.matrix(raw[, sample_columns, drop = FALSE])
storage.mode(count_matrix) <- "numeric"
if (any(!is.finite(count_matrix)) || any(count_matrix < 0) ||
    any(abs(count_matrix - round(count_matrix)) > 1e-8)) {
  stop("Count table must contain finite non-negative integer counts")
}
if (ncol(count_matrix) != nrow(manifest)) {
  stop("Count matrix and sample manifest dimensions do not match")
}

symbols <- toupper(trimws(as.character(raw$gene_name)))
valid <- !is.na(symbols) & nzchar(symbols) &
  !symbols %in% c("---", "NA", "N/A", "NONE")
if (!any(valid)) stop("No usable gene symbols in submitted count matrix")
gene_counts <- rowsum(count_matrix[valid, , drop = FALSE],
                      group = symbols[valid], reorder = FALSE)
rownames(gene_counts) <- toupper(rownames(gene_counts))
if (anyDuplicated(rownames(gene_counts))) stop("Gene-symbol aggregation produced duplicate symbols")

gene_row_counts <- table(symbols[valid])
measured_mrpg <- mrpg8[mrpg8 %in% rownames(gene_counts)]
measured_crpg <- crpg7[crpg7 %in% rownames(gene_counts)]
if (!setequal(measured_mrpg, mrpg8)) {
  stop(paste("The exact 8-mRPG panel is incomplete in GSE262619:",
             paste(setdiff(mrpg8, measured_mrpg), collapse = ", ")))
}

design <- model.matrix(~ age_years + sex, data = manifest)
if (qr(design)$rank != ncol(design)) stop("Age/sex design matrix is rank deficient")
dge <- DGEList(counts = gene_counts)
keep <- filterByExpr(dge, design = design)
dge <- dge[keep, , keep.lib.sizes = FALSE]
dge <- calcNormFactors(dge, method = "TMM")
v <- voom(dge, design, plot = FALSE)
fit <- eBayes(lmFit(v, design), robust = TRUE)
if (!"age_years" %in% colnames(design)) stop("Age coefficient missing from design")
all_results <- topTable(fit, coef = "age_years", number = Inf, sort.by = "none")
all_results$gene_symbol <- rownames(all_results)
all_results <- all_results[, c("gene_symbol", setdiff(colnames(all_results), "gene_symbol"))]
write.csv(all_results, file.path(outdir, "all_gene_age_associations.csv"), row.names = FALSE)

panel_results <- all_results[match(mrpg8, all_results$gene_symbol), , drop = FALSE]
panel_results$gene_symbol <- mrpg8
panel_results$raw_gene_rows <- as.integer(gene_row_counts[mrpg8])
panel_results$tested_after_filter <- mrpg8 %in% rownames(v$E)
write.csv(panel_results, file.path(outdir, "mrpg8_age_associations.csv"), row.names = FALSE)

panel_expression <- v$E[mrpg8, , drop = FALSE]
panel_z <- t(scale(t(panel_expression)))
if (any(!is.finite(panel_z))) stop("Cannot standardize one or more mRPG genes")
panel_score <- colMeans(panel_z)
score_fit <- lm(panel_score ~ age_years + sex, data = manifest)
score_coef <- summary(score_fit)$coefficients["age_years", ]
score_ci <- confint(score_fit)["age_years", ]

measured_summary <- function(genes) {
  data.frame(
    gene_symbol = genes,
    raw_gene_rows = as.integer(gene_row_counts[genes]),
    present_in_count_matrix = genes %in% rownames(gene_counts),
    tested_after_filter = genes %in% rownames(v$E),
    stringsAsFactors = FALSE
  )
}
crpg_inventory <- measured_summary(crpg7)
write.csv(crpg_inventory, file.path(outdir, "crpg7_completeness.csv"), row.names = FALSE)

report <- list(
  dataset = "GSE262619",
  status = "EXPLORATORY_AGE_REFERENCE_ANALYSIS_COMPLETE",
  evidence_class = "public_human_age_reference_not_exceptional_longevity",
  source_sample_count = nrow(manifest),
  sample_count = ncol(v$E),
  exact_age_min_years = min(manifest$age_years),
  exact_age_max_years = max(manifest$age_years),
  sex_source = "GEO sample-title suffix (_F/_M); no explicit sex characteristic was present in the SOFT manifest",
  sex_counts = as.list(table(manifest$sex)),
  age_model = "limma-voom with TMM normalization; gene-level counts aggregated by exact GEO gene_name; age_years + title-derived sex",
  transcriptome_tested_genes = nrow(v$E),
  mrpg8 = list(
    genes = as.list(mrpg8),
    complete_in_count_matrix = length(measured_mrpg) == length(mrpg8),
    all_genes_retained_after_filter = all(mrpg8 %in% rownames(v$E)),
    panel_score_age_slope_per_year = unname(score_coef[["Estimate"]]),
    panel_score_age_p_value = unname(score_coef[["Pr(>|t|)"]]),
    panel_score_age_ci95 = as.list(unname(score_ci)),
    gene_level_results_file = "mrpg8_age_associations.csv"
  ),
  crpg7 = list(
    genes = as.list(crpg7),
    measured_gene_count = length(measured_crpg),
    measured_genes = as.list(measured_crpg),
    complete_in_count_matrix = length(measured_crpg) == length(crpg7),
    composite_score_status = if (length(measured_crpg) == length(crpg7)) "eligible_for_prespecified_analysis" else "WITHHELD_INCOMPLETE_PANEL",
    completeness_file = "crpg7_completeness.csv"
  ),
  provenance = list(
    count_table_sha256 = unname(tools::md5sum(counts_path)),
    sample_manifest_sha256 = unname(tools::md5sum(manifest_path)),
    count_table_rows = nrow(raw),
    count_table_columns = ncol(raw),
    aggregated_gene_symbols = nrow(gene_counts),
    normalization_factors = as.list(setNames(dge$samples$norm.factors, manifest$title))
  ),
  limitations = list(
    "This cohort contains no centenarian or exceptional-longevity group and cannot replicate longevity-specific mRPG preservation.",
    "The analysis tests chronological-age association only; it does not test age-trajectory deviation in long-lived individuals.",
    "Sex is inferred from the GEO submitter sample-title suffix because the source SOFT characteristics lack explicit sex fields.",
    "The cRPG-7 composite is withheld unless all seven published genes are present.",
    "Observational cross-sectional association does not establish causality or a new longevity mechanism."
  )
)
write_json(report, file.path(outdir, "analysis_report.json"), pretty = TRUE, auto_unbox = TRUE)
cat(toJSON(report, pretty = TRUE, auto_unbox = TRUE), "\n")
