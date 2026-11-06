#!/usr/bin/env Rscript
# Reproduce the submitter-published limma-voom E/weights for GSE176260
# and compare them with the frozen GEO supplementary reference matrices.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4L) {
  stop("Usage: validate_gse176260_voom.R counts.tsv.gz reference_E.tsv.gz reference_weights.tsv.gz report.json")
}
suppressPackageStartupMessages({
  library(GEOquery)
  library(edgeR)
  library(limma)
  library(jsonlite)
})

counts_path <- args[[1]]
reference_e_path <- args[[2]]
reference_w_path <- args[[3]]
report_path <- args[[4]]

read_matrix <- function(path) {
  x <- read.delim(gzfile(path), row.names = 1, check.names = FALSE,
                  stringsAsFactors = FALSE)
  as.matrix(x)
}
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

gse <- GEOquery::getGEO("GSE176260", GSEMatrix = TRUE, getGPL = FALSE)
if (length(gse) != 1L) stop("Expected exactly one GSE176260 ExpressionSet.")
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
  identical(tolower(get_field(x, "discovery_analysis_sample")), "yes")
}, logical(1))
if (!any(keep)) stop("No discovery_analysis_sample=Yes samples found in GEO metadata.")
selected <- pd[keep, , drop = FALSE]
selected_meta <- metadata[keep]
sample_ids <- as.character(selected$geo_accession)
if (!setequal(sample_ids, colnames(counts)) || length(sample_ids) != ncol(counts)) {
  stop("GEO discovery sample IDs do not exactly match the published count matrix.")
}
selected <- selected[match(colnames(counts), selected$geo_accession), , drop = FALSE]
selected_meta <- selected_meta[match(colnames(counts), sample_ids)]
phenotype <- vapply(selected_meta, get_field, character(1), key = "phenotype")
gender <- vapply(selected_meta, get_field, character(1), key = "gender")
if (anyNA(phenotype) || anyNA(gender) || any(!nzchar(phenotype)) || any(!nzchar(gender))) {
  stop("GEO phenotype/gender labels are incomplete; refusing to infer sample groups.")
}
sample_data <- data.frame(
  phenotype = factor(phenotype),
  gender = factor(gender),
  row.names = colnames(counts)
)
design <- model.matrix(~ 0 + phenotype + gender, data = sample_data)
if (qr(design)$rank != ncol(design)) stop("Published GEO design is rank deficient.")

dge <- edgeR::DGEList(counts = counts, samples = sample_data)
dge <- edgeR::calcNormFactors(dge, method = "TMM")
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

report <- list(
  status = "COMPLETED_EXTERNAL_REFERENCE_COMPARISON",
  dataset_accession = "GSE176260",
  dataset_title = "Host gene expression profiling of fungal, bacterial, viral, and non-infectious illness (discovery cohort)",
  source_url = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176260",
  publication_pmid = "34225776",
  reference_origin = "GEO submitter-supplied QCed_counts_discovery, Log2_normalized_expression_discovery, and Voom_weights_discovery files",
  reference_method = "edgeR TMM normalization followed by limma voom; design ~ 0 + phenotype + gender",
  software = list(R = as.character(getRversion()),
                  GEOquery = as.character(packageVersion("GEOquery")),
                  edgeR = as.character(packageVersion("edgeR")),
                  limma = as.character(packageVersion("limma"))),
  sample_count = ncol(counts),
  feature_count = nrow(counts),
  phenotype_counts = as.list(table(sample_data$phenotype)),
  gender_counts = as.list(table(sample_data$gender)),
  input_sha256 = list(
    counts = digest::digest(file = counts_path, algo = "sha256"),
    reference_expression = digest::digest(file = reference_e_path, algo = "sha256"),
    reference_weights = digest::digest(file = reference_w_path, algo = "sha256")
  ),
  expression_matrix_metrics = as.list(e_metrics),
  precision_weight_metrics = as.list(w_metrics),
  limitations = paste(
    "This is an external real-dataset reproducibility comparison against",
    "submitter-published GEO voom outputs. It validates numerical agreement",
    "for this dataset, design, preprocessing, and software versions only;",
    "it does not establish general biological correctness or model superiority."
  )
)
jsonlite::write_json(report, report_path, auto_unbox = TRUE, pretty = TRUE, na = "null")
cat(jsonlite::toJSON(report[c("status", "sample_count", "feature_count",
    "expression_matrix_metrics", "precision_weight_metrics")],
    auto_unbox = TRUE, pretty = TRUE))
