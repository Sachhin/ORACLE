#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(edgeR))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  stop("Usage: edgeR_gse32493.R <counts.csv> <output_dir>")
}
counts_path <- args[[1]]
outdir <- args[[2]]
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

counts_df <- read.csv(counts_path, check.names = FALSE, stringsAsFactors = FALSE)
if (!"mirna_id" %in% names(counts_df)) stop("Count matrix must contain mirna_id")
rownames(counts_df) <- counts_df$mirna_id
counts_df$mirna_id <- NULL
counts <- as.matrix(counts_df)
storage.mode(counts) <- "integer"

metadata <- read.csv(file.path(dirname(counts_path), "sample_metadata.csv"),
                     stringsAsFactors = FALSE)
if (!all(colnames(counts) %in% metadata$sample)) {
  stop("Sample metadata does not cover every count-matrix column")
}
metadata <- metadata[match(colnames(counts), metadata$sample), ]
group <- factor(metadata$group, levels = c("control", "centenarian"))
if (anyNA(group) || any(table(group) != 3)) {
  stop("Expected exactly three control and three centenarian biological samples")
}

y <- DGEList(counts = counts, group = group)
keep <- filterByExpr(y, group = group)
if (sum(keep) < 2) stop("Too few miRNAs remain after filterByExpr")
y <- y[keep, , keep.lib.sizes = FALSE]
y <- calcNormFactors(y)
y <- estimateDisp(y, robust = TRUE)
test <- exactTest(y, pair = c("control", "centenarian"))
tab <- topTags(test, n = Inf, sort.by = "PValue")$table
tab$mirna_id <- rownames(tab)
tab <- tab[, c("mirna_id", "logFC", "logCPM", "PValue", "FDR")]
write.csv(tab, file.path(outdir, "edger_differential_expression.csv"), row.names = FALSE)

summary <- data.frame(
  metric = c("samples_control", "samples_centenarian", "features_input",
             "features_tested", "fdr_below_0_05", "higher_in_centenarians_fdr",
             "lower_in_centenarians_fdr"),
  value = c(sum(group == "control"), sum(group == "centenarian"),
            nrow(counts), nrow(tab), sum(tab$FDR < 0.05),
            sum(tab$FDR < 0.05 & tab$logFC > 0),
            sum(tab$FDR < 0.05 & tab$logFC < 0))
)
write.csv(summary, file.path(outdir, "edger_summary.csv"), row.names = FALSE)
writeLines(capture.output(sessionInfo()), file.path(outdir, "R_sessionInfo.txt"))
cat("edgeR exact test complete; tested", nrow(tab), "miRNAs\n")
print(summary)
