#!/usr/bin/env Rscript
# Exploratory replication of published human longevity candidate genes in
# public human age-spectrum GEO expression cohorts. This is not a centenarian
# cohort analysis and cannot establish exceptional longevity.
suppressPackageStartupMessages({
  library(GEOquery)
  library(Biobase)
  library(limma)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
accessions <- if (length(args) >= 1) strsplit(args[[1]], ",", fixed = TRUE)[[1]] else c("GSE58137", "GSE65219")
outdir <- if (length(args) >= 2) args[[2]] else "artifacts/human-aging-geo"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

candidate_genes <- c(
  "ATG4D", "ATP6V0C", "CTSB", "WIPI1", "BCL2L1", "IGF1R", "IRS1",
  "DDIT4", "ABCA2", "CD68", "SQSTM1", "LAMP1", "LAMP2", "BECN1",
  "MAP1LC3B", "IFNG", "TNF", "TGFB1", "IL32"
)

extract_age <- function(pd) {
  txt <- apply(pd, 1, function(row) paste(as.character(row), collapse = " ; "))
  vapply(txt, function(value) {
    match <- regexec(
      "(?i)(?:age|years?[ _-]*old|age[ _-]*years?)[^0-9]{0,16}([0-9]{1,3}(?:\\.[0-9]+)?)(?!\\s*[-–]\\s*[0-9])",
      value, perl = TRUE
    )
    parts <- regmatches(value, match)[[1]]
    if (length(parts) >= 2) as.numeric(parts[[2]]) else NA_real_
  }, numeric(1))
}

analyse_eset <- function(eset, accession, index) {
  pd <- pData(eset)
  if (nrow(pd) < 20) stop("fewer than 20 samples; exploratory age trend not run")
  age <- extract_age(pd)
  if (sum(is.finite(age)) < 20) {
    stop(sprintf("only %d samples have explicit parseable age metadata", sum(is.finite(age))))
  }
  keep_samples <- is.finite(age)
  expr <- exprs(eset)[, keep_samples, drop = FALSE]
  age <- age[keep_samples]
  if (ncol(expr) != length(age) || length(unique(age)) < 3) {
    stop("age metadata does not support a continuous age association")
  }
  fd <- fData(eset)
  symbol_col <- grep("gene.?symbol|symbol", colnames(fd), ignore.case = TRUE, value = TRUE)
  if (!length(symbol_col)) stop("platform annotation has no gene-symbol field")
  symbols <- trimws(as.character(fd[[symbol_col[[1]]]]))
  symbols <- sub("\\s*///.*$", "", symbols)
  valid <- !is.na(symbols) & nzchar(symbols) & !symbols %in% c("---", "NA", "N/A")
  expr <- expr[valid, , drop = FALSE]
  symbols <- symbols[valid]
  groups <- split(seq_along(symbols), toupper(symbols))
  gene_expr <- vapply(groups, function(ix) {
    apply(expr[ix, , drop = FALSE], 2, median, na.rm = TRUE)
  }, numeric(ncol(expr)))
  gene_expr <- t(gene_expr)
  design <- model.matrix(~ age)
  fit <- eBayes(lmFit(gene_expr, design), trend = TRUE, robust = TRUE)
  all_results <- topTable(fit, coef = "age", number = Inf, sort.by = "P")
  all_results$gene_symbol <- rownames(all_results)
  all_results$direction <- ifelse(all_results$logFC > 0, "increases_with_age", "decreases_with_age")
  selected <- all_results[toupper(all_results$gene_symbol) %in% candidate_genes, , drop = FALSE]
  selected$centenarian_candidate_gene <- toupper(selected$gene_symbol)
  selected <- selected[match(candidate_genes, toupper(selected$gene_symbol), nomatch = 0), , drop = FALSE]
  platform <- annotation(eset)
  tag <- paste0(accession, "_platform", index)
  write.csv(all_results, file.path(outdir, paste0(tag, "_all_genes_age_trend.csv")), row.names = FALSE)
  write.csv(selected, file.path(outdir, paste0(tag, "_longevity_candidate_genes.csv")), row.names = FALSE)
  list(
    accession = accession,
    platform_index = index,
    platform = platform,
    samples_total = nrow(pd),
    samples_with_age = length(age),
    age_min_years = min(age),
    age_max_years = max(age),
    gene_symbols_tested = nrow(all_results),
    candidate_genes_detected = nrow(selected),
    candidate_genes_fdr_lt_0_05 = sum(selected$adj.P.Val < 0.05, na.rm = TRUE),
    candidate_gene_results = lapply(seq_len(nrow(selected)), function(i) {
      row <- selected[i, ]
      list(
        gene = as.character(row$gene_symbol),
        logFC_per_year = unname(row$logFC),
        p_value = unname(row$P.Value),
        fdr = unname(row$adj.P.Val),
        direction = as.character(row$direction)
      )
    }),
    limitation = paste(
      "Ordinary age-spectrum association in a public GEO cohort; not a centenarian",
      "or survival cohort. Does not establish a longevity mechanism or causality."
    )
  )
}

successes <- list()
failures <- list()
for (accession in accessions) {
  accession <- trimws(accession)
  message("Retrieving ", accession)
  result <- tryCatch({
    sets <- getGEO(GEO = accession, GSEMatrix = TRUE, getGPL = TRUE)
    if (inherits(sets, "ExpressionSet")) sets <- list(sets)
    if (!length(sets)) stop("GEO returned no processed expression sets")
    cohort_results <- list()
    for (i in seq_along(sets)) {
      cohort_results[[length(cohort_results) + 1]] <- tryCatch(
        analyse_eset(sets[[i]], accession, i),
        error = function(e) {
          failures[[length(failures) + 1]] <<- list(
            accession = accession, platform_index = i, error = conditionMessage(e)
          )
          NULL
        }
      )
    }
    Filter(Negate(is.null), cohort_results)
  }, error = function(e) {
    failures[[length(failures) + 1]] <<- list(accession = accession, error = conditionMessage(e))
    list()
  })
  successes <- c(successes, result)
}

if (!length(successes)) {
  stop("No GEO cohort yielded a valid age-associated expression analysis; see failure log.")
}
report <- list(
  status = if (length(failures)) "PARTIAL_EXPLORATORY_ANALYSIS" else "EXPLORATORY_ANALYSIS_COMPLETE",
  analysis = "limma empirical-Bayes continuous age association",
  accessions_requested = accessions,
  successful_platforms = successes,
  failures = failures,
  candidate_gene_set = candidate_genes,
  provenance = list(
    software = list(R = as.character(getRversion()), GEOquery = as.character(packageVersion("GEOquery")),
                    limma = as.character(packageVersion("limma"))),
    source = "NCBI GEO processed series matrices and sample metadata"
  ),
  interpretation = paste(
    "This exploratory cross-sectional age-trend analysis tests whether selected",
    "genes previously reported in centenarian studies associate with ordinary",
    "ageing. It is not direct replication in exceptional-longevity participants,",
    "does not test lifespan or survival, and cannot establish causal mechanisms."
  )
)
write_json(report, file.path(outdir, "human_aging_geo_candidate_gene_report.json"),
           pretty = TRUE, auto_unbox = TRUE, null = "null")
cat(toJSON(report, pretty = TRUE, auto_unbox = TRUE))
