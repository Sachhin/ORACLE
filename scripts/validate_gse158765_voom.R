#!/usr/bin/env Rscript
# Independent-study reference comparison for GSE158765.
# Reconstructs the submitter's TMM + repeated-measures voom pipeline from
# sample-level GEO attachments and the published sample design.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Usage: validate_gse158765_voom.R OUTPUT_REPORT.json")
report_path <- args[[1]]
required <- c("GEOquery", "edgeR", "limma", "digest", "jsonlite")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Missing R packages: ", paste(missing, collapse = ", "))
library(GEOquery)
library(edgeR)
library(limma)

sha256 <- function(path) digest::digest(file = path, algo = "sha256", serialize = FALSE)
read_matrix <- function(path) {
  con <- if (grepl("\\.gz$", path, ignore.case = TRUE)) gzfile(path, "rt") else file(path, "rt")
  on.exit(close(con))
  x <- read.delim(con, check.names = FALSE, stringsAsFactors = FALSE,
                  quote = "", comment.char = "")
  if (ncol(x) < 2) stop("Expected feature ID plus numeric columns in ", path)
  ids <- as.character(x[[1]])
  if (anyNA(ids) || any(!nzchar(ids)) || anyDuplicated(ids)) stop("Invalid feature IDs in ", path)
  values <- as.matrix(x[-1])
  suppressWarnings(storage.mode(values) <- "numeric")
  if (any(!is.finite(values))) stop("Non-finite/non-numeric values in ", path)
  rownames(values) <- ids
  values
}
get_characteristic <- function(pd, key) {
  norm_key <- gsub("[^a-z0-9]", "", tolower(key))
  result <- rep(NA_character_, nrow(pd))
  for (column in names(pd)) {
    norm_col <- gsub("[^a-z0-9]", "", tolower(column))
    if (grepl(norm_key, norm_col, fixed = TRUE)) {
      candidate <- as.character(pd[[column]])
      if (any(!is.na(candidate) & nzchar(candidate))) result <- candidate
    }
  }
  char_cols <- grep("characteristics_ch1", names(pd), value = TRUE, ignore.case = TRUE)
  for (i in seq_len(nrow(pd))) {
    if (!is.na(result[[i]]) && nzchar(result[[i]])) next
    for (column in char_cols) {
      value <- as.character(pd[[column]][[i]])
      if (is.na(value)) next
      prefix <- paste0("^\\s*", key, "\\s*:\\s*")
      if (grepl(prefix, value, ignore.case = TRUE)) {
        result[[i]] <- sub(prefix, "", value, ignore.case = TRUE)
        break
      }
    }
  }
  prefix <- paste0("^\\\\s*", key, "\\\\s*:\\\\s*")
  result <- sub(prefix, "", result, ignore.case = TRUE)
  result
}

gse <- getGEO("GSE158765", GSEMatrix = TRUE, getGPL = FALSE)
if (!length(gse)) stop("No GEO Series Matrix returned for GSE158765")
pd <- pData(gse[[1]])
gsm_ids <- rownames(pd)
if (is.null(gsm_ids) || !length(gsm_ids) || anyDuplicated(gsm_ids)) stop("Missing/duplicate GEO sample accessions")
metadata <- data.frame(
  gsm = gsm_ids,
  title = as.character(pd$title),
  treatment_drug = get_characteristic(pd, "treatment_drug"),
  sex.x = get_characteristic(pd, "sex.x"),
  Qubitconc.ng.ul = get_characteristic(pd, "Qubitconc.ng.ul"),
  Order_Flowcell = get_characteristic(pd, "Order_Flowcell"),
  StudyID = get_characteristic(pd, "StudyID"),
  stringsAsFactors = FALSE, check.names = FALSE
)
for (field in c("treatment_drug", "sex.x", "Qubitconc.ng.ul", "Order_Flowcell", "StudyID")) {
  if (anyNA(metadata[[field]]) || any(!nzchar(metadata[[field]]))) {
    stop("GEO metadata missing required field ", field, "; characteristics columns: ",
         paste(grep("characteristics_ch1", names(pd), value = TRUE), collapse = ", "))
  }
}
metadata$treatment_drug <- factor(metadata$treatment_drug)
metadata$sex.x <- factor(metadata$sex.x)
metadata$Qubitconc.ng.ul <- as.numeric(metadata$Qubitconc.ng.ul)
metadata$Order_Flowcell <- as.numeric(metadata$Order_Flowcell)
metadata$StudyID <- factor(metadata$StudyID)
if (anyNA(metadata$Qubitconc.ng.ul) || anyNA(metadata$Order_Flowcell)) stop("Qubitconc.ng.ul and Order_Flowcell must be numeric")

work <- tempfile("gse158765_")
dir.create(work)
for (gsm in gsm_ids) {
  files <- GEOquery::getGEOSuppFiles(
    gsm, makeDirectory = TRUE, baseDir = work, fetch_files = TRUE,
    filter_regex = "QCed_counts|Log2_normalized_expression|Voom_weights"
  )
  if (is.null(files) || !nrow(files)) stop("No count/E/weight supplementary files found for ", gsm)
}

assemble <- function(pattern) {
  mats <- vector("list", length(gsm_ids))
  names(mats) <- gsm_ids
  paths <- character()
  for (gsm in gsm_ids) {
    candidates <- list.files(file.path(work, gsm), pattern = pattern,
                             full.names = TRUE, recursive = TRUE, ignore.case = TRUE)
    if (length(candidates) != 1) stop("Expected exactly one ", pattern, " file for ", gsm,
                                      "; found ", length(candidates))
    paths <- c(paths, candidates)
    mats[[gsm]] <- read_matrix(candidates)
  }
  # Some GEO submissions repeat a full matrix on each sample page. Accept that
  # only when all copies are byte-identical; otherwise require one sample column.
  hashes <- vapply(paths, sha256, character(1))
  if (length(unique(hashes)) == 1) {
    mat <- mats[[1]]
    if (all(gsm_ids %in% colnames(mat))) return(mat[, gsm_ids, drop = FALSE])
    if (all(metadata$title %in% colnames(mat))) {
      mat <- mat[, metadata$title, drop = FALSE]
      colnames(mat) <- gsm_ids
      return(mat)
    }
    if (ncol(mat) == 1 && length(gsm_ids) == 1) {
      colnames(mat) <- gsm_ids
      return(mat)
    }
    stop("Repeated full matrix columns do not match GEO GSM accessions or sample titles")
  }
  if (!all(vapply(mats, ncol, integer(1)) == 1L)) {
    stop("Per-sample GEO attachments are not identical and are not one-column sample matrices")
  }
  feature_ids <- rownames(mats[[1]])
  if (!all(vapply(mats, function(x) identical(rownames(x), feature_ids), logical(1)))) {
    stop("Per-sample matrices have different feature IDs or order")
  }
  result <- do.call(cbind, mats)
  colnames(result) <- gsm_ids
  result
}

counts <- assemble("QCed_counts")
published_E <- assemble("Log2_normalized_expression")
published_weights <- assemble("Voom_weights")
if (!setequal(colnames(counts), gsm_ids) || ncol(counts) != length(gsm_ids)) stop("Count/GEO sample mismatch")
if (!identical(rownames(counts), rownames(published_E)) ||
    !identical(rownames(counts), rownames(published_weights))) stop("Count/E/weight feature IDs differ")
if (!identical(colnames(counts), colnames(published_E)) ||
    !identical(colnames(counts), colnames(published_weights))) stop("Count/E/weight sample IDs differ")
if (any(counts < 0)) stop("Counts contain negative values")

metadata <- metadata[match(colnames(counts), metadata$gsm), , drop = FALSE]
rownames(metadata) <- metadata$gsm
dge <- DGEList(counts = counts)
dge$samples <- cbind(dge$samples, metadata[, c("treatment_drug", "sex.x",
  "Qubitconc.ng.ul", "Order_Flowcell", "StudyID"), drop = FALSE])
dge <- calcNormFactors(dge, method = "TMM")
design <- model.matrix(~0 + treatment_drug + sex.x + Qubitconc.ng.ul + Order_Flowcell,
                       data = dge$samples)
rownames(design) <- colnames(counts)
v1 <- voom(dge, design, plot = FALSE)
cor1 <- duplicateCorrelation(v1, design, block = dge$samples$StudyID)
v2 <- voom(dge, design, plot = FALSE, block = dge$samples$StudyID,
           correlation = cor1$consensus.correlation)

compare <- function(actual, reference) {
  delta <- as.numeric(actual - reference)
  list(rmse = sqrt(mean(delta^2)), mae = mean(abs(delta)),
       bias = mean(delta), correlation = suppressWarnings(cor(as.numeric(actual), as.numeric(reference))))
}
E_metrics <- compare(v2$E, published_E)
weight_metrics <- compare(v2$weights, published_weights)
report <- list(
  dataset = "GSE158765",
  study = "Independent platelet mRNA ticagrelor/antiplatelet exposure study",
  independent_of_GSE176260 = TRUE,
  sample_count = ncol(counts),
  feature_count = nrow(counts),
  design = "~0+treatment_drug + sex.x + Qubitconc.ng.ul + Order_Flowcell",
  repeated_measures_block = "StudyID",
  consensus_correlation = cor1$consensus.correlation,
  software = list(R = R.version.string, GEOquery = as.character(packageVersion("GEOquery")),
                  edgeR = as.character(packageVersion("edgeR")), limma = as.character(packageVersion("limma"))),
  expression = E_metrics,
  weights = weight_metrics,
  thresholds = list(expression_rmse_max = 0.05, expression_correlation_min = 0.999,
                    weights_rmse_max = 0.10, weights_correlation_min = 0.99),
  passed = E_metrics$rmse <= 0.05 && E_metrics$correlation >= 0.999 &&
           weight_metrics$rmse <= 0.10 && weight_metrics$correlation >= 0.99,
  input_sha256 = list(
    counts = vapply(list.files(work, pattern = "QCed_counts", full.names = TRUE, recursive = TRUE), sha256, character(1)),
    expression = vapply(list.files(work, pattern = "Log2_normalized_expression", full.names = TRUE, recursive = TRUE), sha256, character(1)),
    weights = vapply(list.files(work, pattern = "Voom_weights", full.names = TRUE, recursive = TRUE), sha256, character(1))
  ),
  sample_mapping = metadata[, c("gsm", "title", "treatment_drug", "sex.x", "StudyID"), drop = FALSE]
)
dir.create(dirname(report_path), recursive = TRUE, showWarnings = FALSE)
jsonlite::write_json(report, report_path, auto_unbox = TRUE, pretty = TRUE, dataframe = "rows", na = "null")
if (!report$passed) stop("GSE158765 published voom reference comparison failed thresholds; inspect report")
