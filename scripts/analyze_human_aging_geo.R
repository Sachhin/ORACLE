#!/usr/bin/env Rscript
# Exploratory replication of published human longevity candidate genes in
# public human age-spectrum GEO expression cohorts. This is not a centenarian
# cohort analysis and cannot establish exceptional longevity.
options(timeout = 600)

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

extract_age <- function(pd) {
  # Parse only explicit age fields or age-labelled characteristics. Never
  # search arbitrary metadata text: years, sample numbers, and cohort codes
  # elsewhere in GEO characteristics are not participant ages.
  columns <- colnames(pd)
  direct_cols <- grep(
    "^(age|age[ _]?(in[ _]?)?years?|age[ _]*\\(years\\)|age at sampling)$",
    columns, ignore.case = TRUE, value = TRUE
  )
  characteristic_cols <- grep("characteristics|^title$", columns, ignore.case = TRUE, value = TRUE)
  candidate_cols <- unique(c(direct_cols, characteristic_cols))
  pattern <- "(?i)(?:^|[;|,])\\s*(?:age|age[_ ]?in[_ ]?years|age\\s*\\(years\\))\\s*[:=]\\s*([0-9]{1,3}(?:\\.[0-9]+)?)\\b"
  vapply(seq_len(nrow(pd)), function(i) {
    values <- numeric()
    for (column in candidate_cols) {
      raw <- trimws(as.character(pd[i, column]))
      if (is.na(raw) || !nzchar(raw)) next
      if (column %in% direct_cols) {
        numeric_value <- suppressWarnings(as.numeric(raw))
        if (is.finite(numeric_value) && numeric_value >= 0 && numeric_value <= 120) {
          values <- c(values, numeric_value)
        }
      }
      match <- regexec(pattern, raw, perl = TRUE)
      parts <- regmatches(raw, match)[[1]]
      if (length(parts) >= 2) {
        age_value <- as.numeric(parts[[2]])
        if (is.finite(age_value) && age_value >= 0 && age_value <= 120) {
          values <- c(values, age_value)
        }
      }
    }
    values <- unique(values[is.finite(values) & values >= 0 & values <= 120])
    if (length(values) == 1) values[[1]] else NA_real_
  }, numeric(1))
}

get_geo_with_retry <- function(accession, attempts = 3) {
  last_error <- NULL
  for (attempt in seq_len(attempts)) {
    result <- tryCatch(
      getGEO(GEO = accession, GSEMatrix = TRUE, getGPL = TRUE),
      error = function(e) {
        last_error <<- conditionMessage(e)
        NULL
      }
    )
    if (!is.null(result)) return(result)
    if (attempt < attempts) {
      wait_seconds <- 10 * attempt
      message("GEO retrieval failed for ", accession, " (attempt ", attempt,
              "/", attempts, "): ", last_error, "; retrying in ", wait_seconds, " seconds")
      Sys.sleep(wait_seconds)
    }
  }
  stop(sprintf("GEO retrieval failed after %d attempts: %s", attempts, last_error))
}

extract_age_group <- function(txt) {
  vapply(txt, function(value) {
    lower <- tolower(value)
    # Specific participant labels take precedence over broad cohort descriptors.
    # A young control may inherit "nonagenarian cohort" in another metadata field.
    if (grepl("young control|young adult|younger", lower)) {
      "younger"
    } else if (grepl("nonagenarian|centenarian|older adult|elderly|old control", lower)) {
      "older"
    } else {
      NA_character_
    }
  }, character(1))
}

# Regression guards for the two metadata edge cases found in legacy GEO fixes.
.age_parser_regression <- extract_age(data.frame(
  age = c("90", "811", "23"),
  characteristics_ch1 = c("age: 90", "age: 811", "age: 23"),
  stringsAsFactors = FALSE
))
if (!identical(unname(.age_parser_regression), c(90, NA_real_, 23))) {
  stop("GEO age parser must reject impossible ages and retain explicit valid ages.")
}
.age_group_parser_regression <- extract_age_group(c(
  "young control; nonagenarian cohort",
  "nonagenarian age: 92",
  "young adult age: 25"
))
if (!identical(unname(.age_group_parser_regression), c("younger", "older", "younger"))) {
  stop("GEO age-group parser must prioritize specific young labels.")
}

# Synthetic design regression: verify the factorial model has the expected
# full-rank coefficient and that the male contrast adds the interaction.
.synthetic_design_data <- data.frame(
  age_group = factor(
    rep(c("younger", "older"), each = 4),
    levels = c("younger", "older")
  ),
  sex = factor(
    rep(c("female", "male", "female", "male"), 2),
    levels = c("female", "male")
  )
)
.synthetic_design <- model.matrix(
  ~ age_group * sex, data = .synthetic_design_data
)
.synthetic_interaction <- "age_groupolder:sexmale"
if (qr(.synthetic_design)$rank != ncol(.synthetic_design) ||
    !.synthetic_interaction %in% colnames(.synthetic_design)) {
  stop("Age-by-sex interaction design regression failed.")
}
.synthetic_contrasts <- matrix(
  0, nrow = ncol(.synthetic_design), ncol = 2,
  dimnames = list(colnames(.synthetic_design), c("female_age", "male_age"))
)
.synthetic_contrasts["age_groupolder", "female_age"] <- 1
.synthetic_contrasts["age_groupolder", "male_age"] <- 1
.synthetic_contrasts[.synthetic_interaction, "male_age"] <- 1
if (!identical(
  unname(.synthetic_contrasts[, "male_age"] -
           .synthetic_contrasts[, "female_age"]),
  unname(as.numeric(colnames(.synthetic_design) == .synthetic_interaction))
)) {
  stop("Sex-specific age contrast regression failed.")
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
  age <- extract_age(pd)
  # Reject impossible ages before reporting or modelling them. The GSE65219
  # group contrast is defined by explicit cohort titles, so invalid numeric
  # age metadata must not contaminate the reported age range.
  invalid_age <- is.finite(age) & (age < 0 | age > 120)
  age[invalid_age] <- NA_real_
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

  # Published GSE65219 cohort composition: 103 older women + 43 older men,
  # and 21 young women + 9 young men. Treat disagreement as a provenance
  # failure rather than silently modelling a changed/misparsed sample set.
  if (identical(accession, "GSE65219")) {
    expected_counts <- matrix(
      c(21L, 9L, 103L, 43L), nrow = 2, byrow = TRUE,
      dimnames = list(c("younger", "older"), c("female", "male"))
    )
    observed_counts <- table(
      factor(age_group, levels = c("younger", "older")),
      factor(sex, levels = c("female", "male"))
    )
    if (!identical(as.vector(observed_counts), as.vector(expected_counts))) {
      stop(
        "GSE65219 age-group-by-sex counts do not match published cohort ",
        "composition (young 21F/9M; nonagenarian 103F/43M). Observed: ",
        paste(as.vector(observed_counts), collapse = "/")
      )
    }
  }

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
  sex_interaction_used <- identical(accession, "GSE65219") &&
    use_group_contrast && sex_used

  if (sex_used) {
    design_data$sex <- factor(sex[keep], levels = c("female", "male"))
  }

  if (sex_interaction_used) {
    design_data$age_group <- factor(
      design_data$age_group, levels = c("younger", "older")
    )
    design <- model.matrix(~ age_group * sex, data = design_data)
    effect_name <- "age_groupolder:sexmale"
    design_label <- "age_group_by_sex_interaction"
  } else if (use_group_contrast) {
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

  base_fit <- lmFit(gene_expr, design)
  if (sex_interaction_used) {
    interaction_fit <- eBayes(base_fit, trend = TRUE, robust = TRUE)
    all_results <- topTable(
      interaction_fit, coef = effect_name, number = Inf, sort.by = "P"
    )
    all_results$gene_symbol <- rownames(all_results)

    contrast_matrix <- matrix(
      0, nrow = ncol(design), ncol = 2,
      dimnames = list(colnames(design), c("female_age", "male_age"))
    )
    contrast_matrix["age_groupolder", "female_age"] <- 1
    contrast_matrix["age_groupolder", "male_age"] <- 1
    contrast_matrix[effect_name, "male_age"] <- 1
    sex_fit <- eBayes(
      contrasts.fit(base_fit, contrast_matrix),
      trend = TRUE, robust = TRUE
    )
    female_results <- topTable(
      sex_fit, coef = "female_age", number = Inf, sort.by = "none"
    )
    male_results <- topTable(
      sex_fit, coef = "male_age", number = Inf, sort.by = "none"
    )
    female_idx <- match(all_results$gene_symbol, female_results$gene_symbol)
    male_idx <- match(all_results$gene_symbol, male_results$gene_symbol)
    all_results$female_age_logFC <- female_results$logFC[female_idx]
    all_results$female_age_p_value <- female_results$P.Value[female_idx]
    all_results$female_age_fdr <- female_results$adj.P.Val[female_idx]
    all_results$male_age_logFC <- male_results$logFC[male_idx]
    all_results$male_age_p_value <- male_results$P.Value[male_idx]
    all_results$male_age_fdr <- male_results$adj.P.Val[male_idx]
    all_results$sex_interaction_logFC <- all_results$logFC
    all_results$sex_interaction_p_value <- all_results$P.Value
    all_results$sex_interaction_fdr <- all_results$adj.P.Val
    all_results$direction <- ifelse(
      all_results$logFC > 0,
      "larger_older_vs_younger_effect_in_males",
      "larger_older_vs_younger_effect_in_females"
    )
  } else {
    fit <- eBayes(base_fit, trend = TRUE, robust = TRUE)
    all_results <- topTable(
      fit, coef = effect_name, number = Inf, sort.by = "P"
    )
    all_results$gene_symbol <- rownames(all_results)
    all_results$direction <- if (use_continuous_age) {
      ifelse(all_results$logFC > 0, "higher_with_age", "lower_with_age")
    } else {
      ifelse(all_results$logFC > 0, "higher_in_older", "lower_in_older")
    }
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
    sex_interaction_tested = sex_interaction_used,
    age_group_by_sex_counts = if (use_group_contrast && sex_used) {
      as.data.frame.matrix(table(
        factor(age_group[keep], levels = c("younger", "older")),
        factor(sex[keep], levels = c("female", "male"))
      ))
    } else NULL,
    interaction_definition = if (sex_interaction_used) {
      "(older-younger in males) minus (older-younger in females)"
    } else NULL,
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
    invalid_age_samples = sum(invalid_age),
    older_group_samples = sum(age_group[keep] == "older", na.rm = TRUE),
    younger_group_samples = sum(age_group[keep] == "younger", na.rm = TRUE),
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
        female_age_logFC = if ("female_age_logFC" %in% colnames(selected)) unname(row$female_age_logFC) else NULL,
        female_age_p_value = if ("female_age_p_value" %in% colnames(selected)) unname(row$female_age_p_value) else NULL,
        female_age_fdr = if ("female_age_fdr" %in% colnames(selected)) unname(row$female_age_fdr) else NULL,
        male_age_logFC = if ("male_age_logFC" %in% colnames(selected)) unname(row$male_age_logFC) else NULL,
        male_age_p_value = if ("male_age_p_value" %in% colnames(selected)) unname(row$male_age_p_value) else NULL,
        male_age_fdr = if ("male_age_fdr" %in% colnames(selected)) unname(row$male_age_fdr) else NULL,
        sex_interaction_logFC = if ("sex_interaction_logFC" %in% colnames(selected)) unname(row$sex_interaction_logFC) else NULL,
        sex_interaction_p_value = if ("sex_interaction_p_value" %in% colnames(selected)) unname(row$sex_interaction_p_value) else NULL,
        sex_interaction_fdr = if ("sex_interaction_fdr" %in% colnames(selected)) unname(row$sex_interaction_fdr) else NULL,
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
    sets <- get_geo_with_retry(accession)
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
