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

metadata_text <- function(pd) {
  apply(pd, 1, function(row) paste(as.character(row), collapse = " ; "))
}

extract_age <- function(txt) {
  vapply(txt, function(value) {
    # Require a whole-word age field: without the boundary, "percentage"
    # contains the substring "age" and can make unrelated values look like ages.
    # Reject impossible values rather than silently treating them as human ages.
    match <- regexec(
      "(?i)\\b(?:age|years?[ _-]*old|age[ _-]*years?)\\b[^0-9]{0,16}([0-9]{1,3}(?:\\.[0-9]+)?)(?!\\s*[-–]\\s*[0-9])",
      value, perl = TRUE
    )
    parts <- regmatches(value, match)[[1]]
    if (length(parts) >= 2) {
      age_value <- as.numeric(parts[[2]])
      if (is.finite(age_value) && age_value >= 0 && age_value <= 120) age_value else NA_real_
    } else NA_real_
  }, numeric(1))
}

# Guard against false matches inside unrelated words such as "percentage".
.age_parser_test <- extract_age(c(
  "age: 90 ; cf-dna (ug/ml): 1.015",
  "percentage: 811",
  "years old: 23"
))
if (!identical(.age_parser_test[[1]], 90) ||
    !is.na(.age_parser_test[[2]]) ||
    !identical(.age_parser_test[[3]], 23)) {
  stop("Age metadata parser regression check failed.")
}

extract_age_group <- function(txt) {
  vapply(txt, function(value) {
    lower <- tolower(value)
    # A sample can inherit cohort-level text such as "nonagenarian cohort"
    # while its own title/characteristics say "young control". Specific young
    # labels must take precedence over broad cohort descriptors.
    if (grepl("young control|young adult|younger", lower)) {
      "younger"
    } else if (grepl("nonagenarian|centenarian|older adult|elderly|old control", lower)) {
      "older"
    } else {
      NA_character_
    }
  }, character(1))
}

.age_group_parser_test <- extract_age_group(c(
  "young control; nonagenarian cohort",
  "nonagenarian age: 92",
  "young adult age: 25"
))
if (!identical(unname(.age_group_parser_test), c("younger", "older", "younger"))) {
  stop("Age-group metadata parser regression check failed.")
}

extract_sex <- function(txt) {
  vapply(txt, function(value) {
    lower <- tolower(value)
    if (grepl("\\bfemale\\b|\\bwomen\\b|\\bwoman\\b", lower)) {
      "female"
    } else if (grepl("\\bmale\\b|\\bmen\\b|\\bman\\b", lower)) {
      "male"
    } else {
      NA_character_
    }
  }, character(1))
}

analyse_eset <- function(eset, accession, index) {
  pd <- pData(eset)
  if (nrow(pd) < 20) stop("fewer than 20 samples; exploratory age analysis not run")
  txt <- metadata_text(pd)
  age <- extract_age(txt)
  age_group <- extract_age_group(txt)

  # GSE65219: use explicit sample titles for cohort assignment.
  if (identical(accession, "GSE65219") && "title" %in% colnames(pd)) {
    sample_title <- tolower(as.character(pd$title))
    title_group <- ifelse(
      grepl("nonagenarian", sample_title, fixed = TRUE), "older",
      ifelse(grepl("young control", sample_title, fixed = TRUE),
             "younger", NA_character_)
    )
    age_group <- title_group
  }
  sex <- extract_sex(txt)


  # Prefer explicit biological group labels over continuous age.
  # This prevents bimodal young-control/nonagenarian cohorts
  # from being incorrectly analysed as a linear age spectrum.
  group_counts <- table(factor(age_group, levels = c("younger", "older")))
  has_usable_continuous_age <- sum(is.finite(age)) >= 20 &&
    length(unique(age[is.finite(age)])) >= 3

  # Force the validated nonagenarian-versus-young-control contrast for GSE65219.
  # Other cohorts retain continuous-age analysis when adequate exact ages exist.
  use_group_contrast <- all(group_counts >= 10) &&
    (identical(accession, "GSE65219") || !has_usable_continuous_age)

  if (use_group_contrast) {
    use_continuous_age <- FALSE
    keep <- !is.na(age_group)
    design_data <- data.frame(
      age_group = factor(age_group[keep], levels = c("younger", "older"))
    )
    effect_name <- "age_groupolder"
    design_label <- "explicit_older_vs_younger"
  } else {
    use_continuous_age <- sum(is.finite(age)) >= 20 &&
      length(unique(age[is.finite(age)])) >= 3

    if (!use_continuous_age) {
      stop(sprintf(
        "Insufficient metadata: %d younger and %d older labels; %d exact ages",
        group_counts[["younger"]], group_counts[["older"]],
        sum(is.finite(age))
      ))
    }

    keep <- is.finite(age)
    design_data <- data.frame(age = age[keep])
    effect_name <- "age"
    design_label <- "continuous_age_years"
  }

  if (sum(keep) < 20) {
    stop("Fewer than 20 samples remain after metadata validation")
  }

  sex_used <- all(!is.na(sex[keep])) &&
    length(unique(sex[keep])) >= 2

  if (sex_used) {
    design_data$sex <- factor(sex[keep])
  }

  if (use_group_contrast) {
    design <- if (sex_used) {
      model.matrix(~ age_group + sex, data = design_data)
    } else {
      model.matrix(~ age_group, data = design_data)
    }
  } else {
    design <- if (sex_used) {
      model.matrix(~ age + sex, data = design_data)
    } else {
      model.matrix(~ age, data = design_data)
    }
  }

  if (qr(design)$rank < ncol(design)) {
    stop("Design matrix is rank-deficient; age effect cannot be reliably estimated")
  }

  if (!effect_name %in% colnames(design)) {
    stop("Requested age coefficient is absent from design matrix")
  }

  # Verify expression columns match phenotype metadata sample order.
  raw_expr <- exprs(eset)
  if (is.null(colnames(raw_expr)) || is.null(rownames(pd)) ||
      !identical(colnames(raw_expr), rownames(pd))) {
    stop("Expression columns do not match phenotype metadata sample order")
  }

  expr <- raw_expr[, keep, drop = FALSE]
  if (ncol(expr) != nrow(design_data)) {
    stop("Expression and design sample counts do not match")
  }
  if (any(colSums(is.finite(expr)) == 0)) {
    stop("At least one selected sample has no finite expression measurements")
  }

  fd <- fData(eset)
  symbol_col <- grep("gene.?symbol|symbol", colnames(fd), ignore.case = TRUE, value = TRUE)
  if (length(symbol_col)) {
    symbols <- trimws(as.character(fd[[symbol_col[[1]]]]))
  } else if (requireNamespace("lumiHumanIDMapping", quietly = TRUE)) {
    data("nuID_MappingInfo", package = "lumiHumanIDMapping", envir = environment())
    mapping <- get("nuID_MappingInfo", envir = environment())
    mapping <- as.data.frame(mapping)
    id_col <- grep("^nuID$|nu.?id", colnames(mapping), ignore.case = TRUE, value = TRUE)
    map_symbol_col <- grep("symbol", colnames(mapping), ignore.case = TRUE, value = TRUE)
    if (!length(map_symbol_col)) stop("lumi nuID mapping lacks a symbol column")
    mapping_ids <- if (length(id_col)) as.character(mapping[[id_col[[1]]]]) else rownames(mapping)
    if (is.null(mapping_ids)) stop("lumi nuID mapping lacks probe identifiers")
    mapped <- mapping[[map_symbol_col[[1]]]][match(rownames(expr), mapping_ids)]
    symbols <- as.character(mapped)
  } else {
    stop("platform annotation has no gene-symbol field and lumiHumanIDMapping is unavailable")
  }
  symbols <- sub("\\s*///.*$", "", trimws(symbols))
  valid <- !is.na(symbols) & nzchar(symbols) & !symbols %in% c("---", "NA", "N/A")
  expr <- expr[valid, , drop = FALSE]
  symbols <- symbols[valid]
  groups <- split(seq_along(symbols), toupper(symbols))
  if (!length(groups)) stop("No valid gene symbols remain after annotation")

  gene_expr <- vapply(groups, function(ix) {
    apply(expr[ix, , drop = FALSE], 2, median, na.rm = TRUE)
  }, numeric(ncol(expr)))

  gene_expr <- t(gene_expr)

  # Preserve missing measurements; never convert them into artificial values.
  gene_expr[!is.finite(gene_expr)] <- NA_real_

  # Record gene-level missingness before filtering.
  gene_expression_measurements_total <- length(gene_expr)
  gene_expression_missing_measurements <- sum(!is.finite(gene_expr))

  # Remove genes with no usable measurements in any sample.
  gene_keep <- rowSums(is.finite(gene_expr)) > 0
  genes_removed_all_missing <- sum(!gene_keep)
  gene_expr <- gene_expr[gene_keep, , drop = FALSE]

  if (!nrow(gene_expr)) stop("No genes have usable expression measurements")
  if (any(colSums(is.finite(gene_expr)) == 0)) {
    stop("At least one sample has no usable gene expression measurements")
  }

  residual_df <- nrow(design) - qr(design)$rank
  if (residual_df <= 0) {
    stop("Insufficient residual degrees of freedom for statistical testing")
  }

  fit <- eBayes(lmFit(gene_expr, design), trend = TRUE, robust = TRUE)
  all_results <- topTable(fit, coef = effect_name, number = Inf, sort.by = "P")
  all_results$gene_symbol <- rownames(all_results)
  all_results$direction <- if (use_continuous_age) {
    ifelse(all_results$logFC > 0, "higher_with_age", "lower_with_age")
  } else {
    ifelse(all_results$logFC > 0, "higher_in_older", "lower_in_older")
  }
  selected <- all_results[toupper(all_results$gene_symbol) %in% candidate_genes, , drop = FALSE]
  selected$centenarian_candidate_gene <- toupper(selected$gene_symbol)
  selected <- selected[match(candidate_genes, toupper(selected$gene_symbol), nomatch = 0), , drop = FALSE]

  platform <- annotation(eset)
  tag <- paste0(accession, "_platform", index)

  sex_counts <- table(factor(
    tolower(sex[keep]),
    levels = c("female", "male")
  ))

  write.csv(all_results, file.path(outdir, paste0(tag, "_all_genes_age_association.csv")), row.names = FALSE)
  write.csv(selected, file.path(outdir, paste0(tag, "_longevity_candidate_genes.csv")), row.names = FALSE)

  list(
    accession = accession,
    platform_index = index,
    platform = platform,
    design = design_label,
    sex_adjusted = sex_used,
    sex_distribution = list(
      female = unname(as.integer(sex_counts[["female"]])),
      male = unname(as.integer(sex_counts[["male"]])),
      missing = sum(is.na(sex[keep]))
    ),
    residual_degrees_of_freedom = residual_df,
    probe_expression_measurements_total = length(expr),
    probe_expression_missing_measurements = sum(!is.finite(expr)),
    probe_expression_missing_fraction = sum(!is.finite(expr)) / length(expr),
    gene_expression_measurements_total = gene_expression_measurements_total,
    gene_expression_missing_measurements = gene_expression_missing_measurements,
    gene_expression_missing_fraction = gene_expression_missing_measurements /
      gene_expression_measurements_total,
    genes_removed_all_missing = genes_removed_all_missing,
    samples_total = nrow(pd),
    samples_analyzed = sum(keep),
    exact_age_samples = sum(is.finite(age)),
    # Group counts are not meaningful for continuous-age regression.
    # Report NA rather than counting cohort descriptors that happen to occur
    # in sample metadata for those same exact-age samples.
    older_group_samples = if (use_continuous_age) NA_integer_ else sum(age_group[keep] == "older", na.rm = TRUE),
    younger_group_samples = if (use_continuous_age) NA_integer_ else sum(age_group[keep] == "younger", na.rm = TRUE),
    age_min_years = if (any(is.finite(age[keep]))) min(age[keep], na.rm = TRUE) else NA_real_,
    age_max_years = if (any(is.finite(age[keep]))) max(age[keep], na.rm = TRUE) else NA_real_,
    gene_symbols_tested = nrow(all_results),
    candidate_genes_detected = nrow(selected),
    candidate_genes_fdr_lt_0_05 = sum(selected$adj.P.Val < 0.05, na.rm = TRUE),
    candidate_gene_results = lapply(seq_len(nrow(selected)), function(i) {
      row <- selected[i, ]
      list(
        gene = as.character(row$gene_symbol),
        effect = unname(row$logFC),
        effect_scale = if (use_continuous_age) "logFC_per_year" else "older_minus_younger_logFC",
        p_value = unname(row$P.Value),
        fdr = unname(row$adj.P.Val),
        direction = as.character(row$direction)
      )
    }),
    limitation = paste(
      "Cross-sectional age association in public blood-derived cohorts; not a",
      "centenarian survival cohort. Does not establish exceptional longevity or causality."
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
  analysis = "limma empirical-Bayes age association, exact age where available; otherwise explicit older/younger metadata contrast",
  accessions_requested = accessions,
  successful_platforms = successes,
  failures = failures,
  candidate_gene_set = candidate_genes,
  provenance = list(
    software = list(R = as.character(getRversion()), GEOquery = as.character(packageVersion("GEOquery")),
                    limma = as.character(packageVersion("limma"))),
    source = "NCBI GEO processed series matrices, GPL annotations, and sample metadata"
  ),
  interpretation = paste(
    "This exploratory analysis tests whether selected genes previously reported",
    "in a centenarian study associate with ordinary human age or a nonagenarian",
    "versus young-control contrast. It is not direct replication in exceptional-",
    "longevity participants, does not test survival, and cannot establish causality."
  )
)
write_json(report, file.path(outdir, "human_aging_geo_candidate_gene_report.json"),
           pretty = TRUE, auto_unbox = TRUE, null = "null")
cat(toJSON(report, pretty = TRUE, auto_unbox = TRUE))
