#!/usr/bin/env Rscript
# Small-n exploratory GPL570 raw-CEL RMA and prespecified mRPG-8 panel sensitivity.
# Not a longevity replication, transcriptome-wide discovery, or causal analysis.
suppressPackageStartupMessages({
  library(affy); library(limma); library(AnnotationDbi); library(hgu133plus2.db); library(jsonlite)
})
args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop("Usage: analyze_gse237029_rma.R sample_manifest.tsv output_dir")
manifest <- read.delim(args[[1]], stringsAsFactors=FALSE, check.names=FALSE)
outdir <- args[[2]]; dir.create(outdir, recursive=TRUE, showWarnings=FALSE)
required <- c("sample_accession","age_category","cel_path","cel_sha256")
if (!all(required %in% names(manifest))) stop("Manifest missing required source fields")
if (nrow(manifest)!=9L || anyDuplicated(manifest$sample_accession) ||
    any(!file.exists(manifest$cel_path)) || any(!nzchar(manifest$cel_sha256)))
  stop("Expected nine unique samples with authenticated CEL files")
manifest$group <- factor(manifest$age_category, levels=c("Middle-aged","Old"))
if (anyNA(manifest$group) || sum(manifest$group=="Old")!=5L ||
    sum(manifest$group=="Middle-aged")!=4L)
  stop("Expected source-defined groups Old n=5 and Middle-aged n=4")
raw <- ReadAffy(filenames=manifest$cel_path)
design_annotation <- as.character(annotation(raw))
if (length(design_annotation)!=1L || !grepl("hgu133plus2",design_annotation,ignore.case=TRUE))
  stop(paste("CEL design does not resolve to GPL570/HG-U133 Plus 2:",paste(design_annotation,collapse=",")))
Biobase::sampleNames(raw) <- manifest$sample_accession
eset <- rma(raw)
expr <- exprs(eset)
if (ncol(expr)!=9L || nrow(expr)<20000L || !identical(colnames(expr),manifest$sample_accession))
  stop("RMA output dimensions or sample identities failed")
rma_path <- file.path(outdir,"GSE237029_RMA_probe_expression.tsv")
write.table(data.frame(probe_id=rownames(expr),expr,check.names=FALSE),
            rma_path,sep="\t",quote=FALSE,row.names=FALSE)
probes <- rownames(expr)
map <- AnnotationDbi::select(hgu133plus2.db, keys=probes, keytype="PROBEID", columns="SYMBOL")
map <- map[!is.na(map$SYMBOL) & nzchar(map$SYMBOL),c("PROBEID","SYMBOL")]
panel <- c("MRPL3","MRPL32","MRPL42","MRPL45","MRPL50","MRPS10","MRPS33","MRPS35")
mapped <- map[map$SYMBOL %in% panel,,drop=FALSE]
gene_expr <- sapply(panel,function(g) {
  ids <- unique(mapped$PROBEID[mapped$SYMBOL==g])
  ids <- intersect(ids,rownames(expr))
  if (!length(ids)) return(rep(NA_real_,ncol(expr)))
  if (length(ids)==1L) as.numeric(expr[ids,]) else apply(expr[ids,,drop=FALSE],2,median,na.rm=TRUE)
})
if (is.null(dim(gene_expr))) gene_expr <- matrix(gene_expr,ncol=length(panel))
rownames(gene_expr) <- manifest$sample_accession; colnames(gene_expr) <- panel
present <- panel[colSums(is.finite(gene_expr))==9L]
if (length(present)<1L) stop("No complete mRPG genes mapped to GPL570 probes")
design <- model.matrix(~group,data=manifest)
fit <- eBayes(lmFit(t(gene_expr[,present,drop=FALSE]),design),trend=TRUE,robust=TRUE)
coef_name <- "groupOld"
if (!(coef_name %in% colnames(design))) stop("Old-vs-middle-aged contrast not estimable")
tab <- topTable(fit,coef=coef_name,number=Inf,sort.by="none",adjust.method="BH")
tab$gene <- rownames(tab)
tab$probe_count <- vapply(rownames(tab),function(g) length(unique(mapped$PROBEID[mapped$SYMBOL==g])),integer(1))
tab <- tab[,c("gene","probe_count","logFC","AveExpr","t","P.Value","adj.P.Val","B")]
# All nine GEO records report Male. Record this explicitly; sex cannot be
# estimated as a covariate in an all-male cohort and is not silently modeled.
gender_levels <- sort(unique(manifest$gender[nzchar(manifest$gender)]))
if (length(gender_levels) != 1L || gender_levels[[1]] != "Male")
  stop(paste("Unexpected sex composition; review design before interpreting:", paste(gender_levels, collapse=",")))
# Leave-one-donor-out sensitivity: quantify whether each panel-gene direction
# depends on any single donor. These are diagnostics, not independent replication.
loo <- do.call(rbind, lapply(seq_len(nrow(manifest)), function(i) {
  keep <- seq_len(nrow(manifest)) != i
  m <- droplevels(manifest[keep,,drop=FALSE])
  d <- model.matrix(~group, data=m)
  ff <- eBayes(lmFit(t(gene_expr[keep,present,drop=FALSE]), d), trend=TRUE, robust=TRUE)
  tt <- topTable(ff, coef="groupOld", number=Inf, sort.by="none", adjust.method="BH")
  data.frame(excluded_sample=manifest$sample_accession[[i]], gene=rownames(tt),
             logFC=tt$logFC, P.Value=tt$P.Value, adj.P.Val=tt$adj.P.Val,
             stringsAsFactors=FALSE)
}))
write.csv(loo,file.path(outdir,"mrpg8_leave_one_donor_out.csv"),row.names=FALSE)
loo_summary <- do.call(rbind,lapply(present,function(g) {
  z <- loo[loo$gene==g,,drop=FALSE]
  base <- tab[tab$gene==g,,drop=FALSE]
  data.frame(gene=g, full_data_logFC=base$logFC,
             loo_same_direction=sum(sign(z$logFC)==sign(base$logFC)),
             loo_fits=nrow(z), loo_logFC_min=min(z$logFC),
             loo_logFC_max=max(z$logFC),
             loo_nominal_p_min=min(z$P.Value), loo_nominal_p_max=max(z$P.Value))
}))
write.csv(loo_summary,file.path(outdir,"mrpg8_leave_one_donor_out_summary.csv"),row.names=FALSE)
write.csv(tab,file.path(outdir,"mrpg8_old_vs_middle_aged.csv"),row.names=FALSE)
summary <- list(dataset="GSE237029",status="EXPLORATORY_RMA_PANEL_ANALYSIS_COMPLETE",
 evidence_class="small_n_human_age_reference_not_longevity_replication",
 platform="GPL570 / Affymetrix Human Genome U133 Plus 2.0",
 preprocessing="affy::rma on all nine raw CEL files jointly",
 sample_count=nrow(manifest),old_n=sum(manifest$group=="Old"),
 middle_aged_n=sum(manifest$group=="Middle-aged"),
 age_metadata="categorical only; no exact ages supplied",
 gender_levels=gender_levels,gender_design_status="all nine GEO samples are male; sex is invariant and cannot be estimated as a covariate",
 leave_one_out_summary=unname(split(loo_summary,seq_len(nrow(loo_summary)))),
 design_annotation=design_annotation, rma_probe_count=nrow(expr),
 mRPG8_genes=panel,measured_genes=present,missing_genes=setdiff(panel,present),
 results=unname(split(tab,seq_len(nrow(tab)))),
 cel_sha256=setNames(manifest$cel_sha256,manifest$sample_accession),
 rma_sha256=sub("\\s+.*$", "", system2("sha256sum", shQuote(rma_path), stdout=TRUE)),
 limitations=c("n=5 versus n=4; underpowered and vulnerable to individual-donor effects.",
 "Only categorical age groups are available; no continuous-age model is possible.",
 "Probe-to-symbol mapping can be one-to-many; multiple probes were summarized by within-sample median.",
 "Panel-only FDR is exploratory and is not transcriptome-wide discovery.",
 "GCOS submitter signals are not numerically equated with RMA values.",
 "This dataset has no centenarian or exceptional-longevity participants; no causal claim is tested."))
write_json(summary,file.path(outdir,"analysis_report.json"),pretty=TRUE,auto_unbox=TRUE)
cat(toJSON(summary,pretty=TRUE,auto_unbox=TRUE))
