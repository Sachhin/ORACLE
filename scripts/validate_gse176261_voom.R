#!/usr/bin/env Rscript
# Reproduce the submitter-published limma-voom E/weights for GSE176261
# Diagnostic cohort job runs independently of the discovery and GSE64099 jobs.
# Report remains explicit if the pre-registered tolerance is not met.
# and compare them with the frozen GEO supplementary reference matrices.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 5L) {
  stop("Usage: validate_gse176261_voom.R all_samples_counts.tsv.gz validation_counts.tsv.gz reference_E.tsv.gz reference_weights.tsv.gz report.json")
}
suppressPackageStartupMessages({
  library(GEOquery)
  library(edgeR)
  library(limma)
  library(jsonlite)
})

# GEOquery reads a long Series Matrix metadata line; increase vroom buffer.
Sys.setenv(VROOM_CONNECTION_SIZE = "10485760")

all_counts_path <- args[[1]]
counts_path <- args[[2]]
reference_e_path <- args[[3]]
reference_w_path <- args[[4]]
report_path <- args[[5]]

read_matrix <- function(path) {
  x <- read.delim(gzfile(path), row.names = 1, check.names = FALSE,
                  stringsAsFactors = FALSE)
  as.matrix(x)
}
all_counts <- read_matrix(all_counts_path)
counts <- read_matrix(counts_path)
reference_e <- read_matrix(reference_e_path)
reference_w <- read_matrix(reference_w_path)

if (!is.numeric(counts) || any(!is.finite(counts)) ||
    any(counts < 0) || any(counts != floor(counts))) {
  stop("Published count matrix must contain finite non-negative integer counts.")
}
if (is.null(rownames(counts)) || is.null(colnames(counts)) ||
    anyDuplicated(rownames(counts)) || anyDuplicated(colnames(counts))) {
  stop("Count matrix must have unique feature and sample identifiers.")
}

# GEO's Series Matrix contains long metadata lines; raise vroom's connection
# buffer before GEOquery reads it (default 128 KiB is too small).
Sys.setenv(VROOM_CONNECTION_SIZE = "50000000")
gse <- GEOquery::getGEO("GSE176261", GSEMatrix = TRUE, getGPL = FALSE)
if (length(gse) != 1L) stop("Expected exactly one GSE176261 ExpressionSet.")
pd <- Biobase::pData(gse[[1]])
char_cols <- grep("^characteristics_ch1", names(pd), value = TRUE)
if (!("geo_accession" %in% names(pd)) || length(char_cols) == 0L) {
  stop("GEO metadata is missing sample accessions or characteristics.")
}
parse_characteristics <- function(i) {
  out <- list()
  for (raw in as.character(unlist(pd[i, char_cols, drop = FALSE], use.names = FALSE))) {
    if (is.na(raw) || !grepl(":", raw, fixed = TRUE)) next
    parts <- strsplit(raw, ":", fixed = TRUE)[[1]]
    key <- tolower(trimws(parts[[1]]))
    value <- trimws(paste(parts[-1], collapse = ":"))
    if (nzchar(key)) out[[key]] <- value
  }
  out
}
metadata <- lapply(seq_len(nrow(pd)), parse_characteristics)
get_field <- function(x, key) {
  value <- x[[key]]
  if (is.null(value)) return(NA_character_)
  as.character(value)
}
keep <- vapply(metadata, function(x) {
  identical(tolower(get_field(x, "validation_analysis_sample")), "yes")
}, logical(1))
if (!any(keep)) stop("No validation_analysis_sample=Yes samples found in GEO metadata.")
selected <- pd[keep, , drop = FALSE]
selected_meta <- metadata[keep]
# GEO sample titles append a platform description to the submitter alias
# (for example, "9A4D98 RNA-seq [discovery cohort]"). Count matrices use only
# that leading alias. Strip the suffix and require exact one-to-one matching.
sample_ids <- sub("\\s+RNA-seq.*$", "", as.character(selected$title))
if (anyNA(sample_ids) || any(!nzchar(sample_ids)) || anyDuplicated(sample_ids)) {
  stop("GEO validation sample titles must be unique non-empty sample aliases.")
}
if (!setequal(sample_ids, colnames(counts)) || length(sample_ids) != ncol(counts)) {
  counts_only <- setdiff(colnames(counts), sample_ids)
  metadata_only <- setdiff(sample_ids, colnames(counts))
  validation_values <- vapply(metadata, get_field, character(1), key = "validation_analysis_sample")
  stop(paste0(
    "GEO validation sample title aliases do not exactly match the published count matrix. ",
    "count_columns=", ncol(counts), "; validation_metadata_samples=", length(sample_ids),
    "; counts_only_first20=", paste(head(counts_only, 20), collapse = ","),
    "; metadata_only_first20=", paste(head(metadata_only, 20), collapse = ","),
    "; validation_metadata_values=", paste(names(table(validation_values)), as.integer(table(validation_values)), collapse = ";")
  ))
}
selected <- selected[match(colnames(counts), sample_ids), , drop = FALSE]
selected_meta <- selected_meta[match(colnames(counts), sample_ids)]
phenotype <- vapply(selected_meta, get_field, character(1), key = "phenotype")
gender <- vapply(selected_meta, get_field, character(1), key = "gender")
if (anyNA(phenotype) || anyNA(gender) || any(!nzchar(phenotype)) || any(!nzchar(gender))) {
  stop("GEO phenotype/gender labels are incomplete; refusing to infer sample groups.")
}
# GEO documents TMM normalization on the batch-2 all-samples count matrix.
# Calculate normalization factors on that full matrix first, then retain the
# validation_analysis_sample=Yes columns for the published validation voom run.
all_sample_ids <- sub("\\s+RNA-seq.*$", "", as.character(pd$title))
if (anyNA(all_sample_ids) || any(!nzchar(all_sample_ids)) || anyDuplicated(all_sample_ids)) {
  stop("GEO sample title aliases must be unique and non-empty.")
}
# The all-samples count file contains the submitter's QC-passing batch-2
# samples; GEO may also list excluded samples. Require every count column to
# map one-to-one to a GEO sample, without requiring excluded samples in counts.
all_sample_rows <- match(colnames(all_counts), all_sample_ids)
if (anyNA(all_sample_rows) || anyDuplicated(all_sample_rows)) {
  stop("All-samples count matrix columns do not map one-to-one to GEO sample title aliases.")
}
if (!setequal(rownames(all_counts), rownames(counts))) {
  stop("All-samples and validation count matrices have different feature identifiers.")
}
all_counts <- all_counts[rownames(counts), , drop = FALSE]
validation_from_all <- all_counts[, colnames(counts), drop = FALSE]
if (!isTRUE(all.equal(validation_from_all, counts, tolerance = 0,
                      check.attributes = FALSE))) {
  stop("Validation counts differ from the corresponding columns in the all-samples count matrix.")
}

dge_all <- edgeR::DGEList(counts = all_counts)
dge_all <- edgeR::calcNormFactors(dge_all, method = "TMM")
if (!all(colnames(counts) %in% colnames(dge_all))) {
  stop("Validation samples are missing from the all-samples normalized DGEList.")
}
dge <- dge_all[, colnames(counts), keep.lib.sizes = TRUE]

# Preserve the validation GEO metadata while retaining the full-cohort
# library sizes and TMM normalization factors calculated above.
sample_data <- selected
rownames(sample_data) <- colnames(counts)
for (field in intersect(c("lib.size", "norm.factors"), names(sample_data))) {
  sample_data[[field]] <- as.numeric(sample_data[[field]])
  if (anyNA(sample_data[[field]]) || any(!is.finite(sample_data[[field]]))) {
    stop("GEO sample metadata contains invalid ", field)
  }
}
for (field in setdiff(names(sample_data), names(dge$samples))) {
  dge$samples[[field]] <- sample_data[[field]]
}
dge$samples$phenotype <- factor(phenotype)
dge$samples$gender <- factor(gender)
design <- model.matrix(~ 0 + phenotype + gender, data = dge$samples)
if (qr(design)$rank != ncol(design)) stop("Published GEO design is rank deficient.")

voom_result <- limma::voom(dge, design = design, plot = FALSE)

align_reference <- function(reference, label) {
  if (!setequal(rownames(reference), rownames(voom_result$E)) ||
      !setequal(colnames(reference), colnames(voom_result$E))) {
    stop(paste(label, "feature/sample identifiers do not exactly match recomputed voom output."))
  }
  reference[rownames(voom_result$E), colnames(voom_result$E), drop = FALSE]
}
reference_e <- align_reference(reference_e, "Published E matrix")
reference_w <- align_reference(reference_w, "Published weights matrix")

metrics <- function(actual, reference) {
  delta <- as.numeric(actual) - as.numeric(reference)
  c(
    n = length(delta),
    mae = mean(abs(delta)),
    rmse = sqrt(mean(delta^2)),
    mean_signed_error = mean(delta),
    pearson_r = suppressWarnings(cor(as.numeric(actual), as.numeric(reference)))
  )
}
e_metrics <- metrics(voom_result$E, reference_e)
w_metrics <- metrics(voom_result$weights, reference_w)

# Preserve recomputed matrices and sample-level residual diagnostics. The
# pooled RMSE alone cannot distinguish a global offset from a subset of
# samples or genes driving the discrepancy.
out_dir <- dirname(report_path)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
write_matrix_gz <- function(x, path) {
  con <- gzfile(path, open = "wt")
  on.exit(close(con), add = TRUE)
  utils::write.table(cbind(feature_id = rownames(x), x), con,
                     sep = "\t", quote = FALSE, row.names = FALSE)
}
write_matrix_gz(voom_result$E, file.path(out_dir, "gse176261_recomputed_E.tsv.gz"))
write_matrix_gz(voom_result$weights, file.path(out_dir, "gse176261_recomputed_weights.tsv.gz"))

sample_diagnostics <- lapply(seq_len(ncol(voom_result$E)), function(j) {
  delta <- voom_result$E[, j] - reference_e[, j]
  c(
    sample_alias = colnames(voom_result$E)[j],
    geo_accession = as.character(selected$geo_accession[j]),
    phenotype = as.character(sample_data$phenotype[j]),
    gender = as.character(sample_data$gender[j]),
    library_size = as.character(dge$samples$lib.size[j]),
    norm_factor = as.character(dge$samples$norm.factors[j]),
    mean_signed_error = as.character(mean(delta)),
    centered_error_sd = as.character(sd(delta - mean(delta))),
    max_abs_centered_error = as.character(max(abs(delta - mean(delta)))),
    mae = as.character(mean(abs(delta))),
    rmse = as.character(sqrt(mean(delta^2))),
    pearson_r = as.character(suppressWarnings(cor(voom_result$E[, j], reference_e[, j])))
  )
})
sample_diagnostics <- as.data.frame(do.call(rbind, sample_diagnostics), stringsAsFactors = FALSE)
utils::write.table(sample_diagnostics,
                   file.path(out_dir, "gse176261_sample_diagnostics.tsv"),
                   sep = "\t", quote = FALSE, row.names = FALSE)


report <- list(
  status = "COMPLETED_EXTERNAL_REFERENCE_COMPARISON",
  dataset_accession = "GSE176261",
  dataset_title = "Host gene expression profiling of fungal, bacterial, viral, and non-infectious illness (validation cohort)",
  source_url = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176261",
  publication_pmid = "34225776",
  reference_origin = "GEO submitter-supplied all-samples QCed counts plus validation QCed counts, Log2_normalized_expression_validation, and Voom_weights_validation files",
  reference_method = "edgeR TMM normalization factors calculated on the GEO batch-2 all-samples count matrix, subset to validation samples, then limma voom; design ~ 0 + phenotype + gender",
  software = list(R = as.character(getRversion()),
                  GEOquery = as.character(packageVersion("GEOquery")),
                  edgeR = as.character(packageVersion("edgeR")),
                  limma = as.character(packageVersion("limma"))),
  all_samples_count = ncol(all_counts),
  sample_count = ncol(counts),
  sample_metadata_columns = names(selected),
  metadata_lib_size_supplied = "lib.size" %in% names(selected),
  metadata_norm_factors_supplied = "norm.factors" %in% names(selected),
  feature_count = nrow(counts),
  sample_accession_mapping = as.list(setNames(as.character(selected$geo_accession), colnames(counts))),
  phenotype_counts = as.list(table(sample_data$phenotype)),
  gender_counts = as.list(table(sample_data$gender)),
  input_sha256 = list(
    all_samples_counts = digest::digest(file = all_counts_path, algo = "sha256"),
    validation_counts = digest::digest(file = counts_path, algo = "sha256"),
    reference_expression = digest::digest(file = reference_e_path, algo = "sha256"),
    reference_weights = digest::digest(file = reference_w_path, algo = "sha256")
  ),
  expression_matrix_metrics = as.list(e_metrics),
  expression_residual_structure = list(
    interpretation = paste(
      "Per-sample residuals are decomposed into a sample-wide additive offset",
      "and gene-specific residual variation. Near-zero centered residual SD",
      "indicates a sample-wise offset rather than gene-specific disagreement."
    ),
    max_per_sample_centered_error_sd = max(as.numeric(sample_diagnostics$centered_error_sd)),
    median_per_sample_centered_error_sd = median(as.numeric(sample_diagnostics$centered_error_sd)),
    max_abs_centered_error_max = max(as.numeric(sample_diagnostics$max_abs_centered_error))
  ),
  precision_weight_metrics = as.list(w_metrics),
  design_columns = colnames(design),
  normalization = list(
    method = "edgeR TMM on all batch-2 samples; factors subset to validation samples",
    effective_library_sizes = as.list(setNames(as.numeric(dge$samples$lib.size * dge$samples$norm.factors), colnames(counts))),
    library_sizes = as.list(setNames(as.numeric(dge$samples$lib.size), colnames(counts))),
    norm_factors = as.list(setNames(as.numeric(dge$samples$norm.factors), colnames(counts)))
  ),
  sample_diagnostics_file = "gse176261_sample_diagnostics.tsv",
  recomputed_expression_file = "gse176261_recomputed_E.tsv.gz",
  recomputed_weights_file = "gse176261_recomputed_weights.tsv.gz",
  acceptance_thresholds = list(expression_rmse_max = 0.05, expression_pearson_min = 0.999,
                               weights_rmse_max = 0.10, weights_pearson_min = 0.99),
  limitations = paste(
    "This is an external real-dataset reproducibility comparison against",
    "submitter-published GEO voom outputs. It validates numerical agreement",
    "for this dataset, design, preprocessing, and software versions only;",
    "it does not establish general biological correctness or model superiority."
  )
)
pass <- is.finite(e_metrics[["rmse"]]) && is.finite(e_metrics[["pearson_r"]]) &&
  is.finite(w_metrics[["rmse"]]) && is.finite(w_metrics[["pearson_r"]]) &&
  e_metrics[["rmse"]] <= 0.05 && e_metrics[["pearson_r"]] >= 0.999 &&
  w_metrics[["rmse"]] <= 0.10 && w_metrics[["pearson_r"]] >= 0.99
report$status <- if (pass) "PASS" else "FAIL_NUMERICAL_TOLERANCE"
jsonlite::write_json(report, report_path, auto_unbox = TRUE, pretty = TRUE, na = "null")
cat(jsonlite::toJSON(report[c("status", "sample_count", "feature_count",
    "expression_matrix_metrics", "precision_weight_metrics", "acceptance_thresholds")],
    auto_unbox = TRUE, pretty = TRUE))
if (!pass) cat("::warning::GSE176261 completed with FAIL_NUMERICAL_TOLERANCE; the JSON report is uploaded for audit and this result is not counted as a pass.\n")
