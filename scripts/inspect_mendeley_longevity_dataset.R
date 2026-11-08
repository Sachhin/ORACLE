#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(jsonlite))
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) stop("Usage: inspect_mendeley_longevity_dataset.R <extracted-dir> <output.json>")
root <- normalizePath(args[[1]], mustWork = TRUE)
out <- args[[2]]
all_files <- list.files(root, recursive = TRUE, full.names = TRUE)
if (!length(all_files)) stop("The downloaded public Mendeley archive is empty")
files <- all_files[grepl("\\.(rda|RData)$", all_files, ignore.case = TRUE)]
text_files <- all_files[grepl("\\.(csv|tsv|txt)(\\.gz)?$", all_files, ignore.case = TRUE)]
file_inventory <- lapply(all_files, function(file) {
  rel <- substring(file, nchar(root) + 2)
  ext <- tolower(tools::file_ext(file))
  info <- list(path=rel, bytes=as.numeric(file.info(file)$size), extension=ext)
  if (file %in% text_files) {
    con <- if(grepl("\\.gz$", file, ignore.case=TRUE)) gzfile(file, "rt") else file(file, "rt")
    on.exit(close(con), add=TRUE)
    first <- tryCatch(readLines(con, n=2, warn=FALSE), error=function(e) character())
    if(length(first)) {
      delimiter <- if(grepl("\\t", first[[1]])) "\\t" else if(grepl(",", first[[1]])) "," else ""
      info$header_field_count <- if(nzchar(delimiter)) length(strsplit(first[[1]], delimiter, fixed=TRUE)[[1]]) else NA_integer_
      info$first_line_preview <- substr(first[[1]], 1, 240)
    }
  }
  info
})
inspect_one <- function(file) {
  env <- new.env(parent = baseenv())
  loaded <- tryCatch(load(file, envir = env), error = function(e) structure(list(message=conditionMessage(e)), class="load_error"))
  if (inherits(loaded, "load_error")) return(list(file=substring(file,nchar(root)+2), error=loaded$message))
  phen_name <- loaded[vapply(loaded, function(nm) {
    x <- get(nm, envir=env)
    is.data.frame(x) && any(tolower(names(x)) %in% c("age","ages","age_years","age_at_sampling")) &&
      any(tolower(names(x)) %in% c("id","sample_id","sample","individual_id"))
  }, logical(1))][1]
  phen <- if(length(phen_name) && !is.na(phen_name)) get(phen_name, envir=env) else NULL
  phen_cols <- if(!is.null(phen)) names(phen) else character()
  phen_id_col <- phen_cols[tolower(phen_cols) %in% c("id","sample_id","sample","individual_id")]
  phen_ids <- if(length(phen_id_col)) as.character(phen[[phen_id_col[[1]]]]) else character()
  objects <- lapply(loaded, function(nm) {
    x <- get(nm, envir=env)
    d <- tryCatch(dim(x), error=function(e) NULL)
    item <- list(name=nm, class=class(x), dimensions=if(is.null(d)) NULL else as.integer(d))
    if (is.data.frame(x) && nrow(x) > 20) {
      cols <- names(x)
      age_col <- cols[tolower(cols) %in% c("age","ages","age_years","age_at_sampling")]
      sex_col <- cols[tolower(cols) %in% c("sex","gender")]
      region_col <- cols[tolower(cols) %in% c("region","location","province","cohort")]
      id_col <- cols[tolower(cols) %in% c("id","sample_id","sample","individual_id")]
      library_col <- cols[grepl("library|prep|sequenc|capture|protocol|method", tolower(cols))]
      item$metadata <- list(rows=nrow(x), columns=cols,
        age_column=if(length(age_col)) age_col[[1]] else NULL,
        sex_column=if(length(sex_col)) sex_col[[1]] else NULL,
        region_column=if(length(region_col)) region_col[[1]] else NULL,
        library_preparation_columns=library_col,
        id_column=if(length(id_col)) id_col[[1]] else NULL)
      if(length(age_col)) {
        age <- suppressWarnings(as.numeric(x[[age_col[[1]]]]))
        item$metadata$age_summary <- list(n=sum(is.finite(age)),
          min=if(any(is.finite(age))) min(age,na.rm=TRUE) else NULL,
          median=if(any(is.finite(age))) median(age,na.rm=TRUE) else NULL,
          max=if(any(is.finite(age))) max(age,na.rm=TRUE) else NULL,
          n_ge_90=sum(age>=90,na.rm=TRUE), n_lt_90=sum(age<90,na.rm=TRUE))
      }
      if(length(sex_col)) item$metadata$sex_counts <- as.list(table(as.character(x[[sex_col[[1]]]])))
      if(length(region_col)) item$metadata$region_counts <- as.list(table(as.character(x[[region_col[[1]]]])))
      if(length(library_col)) item$metadata$library_preparation_counts <- lapply(library_col, function(nm2) as.list(table(as.character(x[[nm2]]))))
    }
    if (!is.null(d) && length(d)==2 && d[[1]]>=1000 && d[[2]]>=50) {
      item$matrix_candidate <- TRUE
      item$rownames_present <- !is.null(rownames(x))
      item$colnames_present <- !is.null(colnames(x))
      if(length(phen_ids) && !is.null(colnames(x))) {
        overlap <- intersect(phen_ids, colnames(x))
        item$phenotype_matrix_id_overlap <- length(overlap)
        item$phenotype_id_coverage <- length(overlap) / length(unique(phen_ids))
      }
    }
    item
  })
  list(file=substring(file,nchar(root)+2), objects=objects)
}
inventory <- list(
  dataset="Mendeley Data fpf4y72kfz version 1",
  doi="10.17632/fpf4y72kfz.1",
  archive_files=file_inventory,
  rdata_objects= lapply(files, inspect_one),
  notes=c("This is an archive/object inventory, not a biological result.",
          "Sample identifiers are not emitted in this report.",
          "Expression matrices require design, library-preparation and cohort checks before inference.",
          "RData object inspection is skipped when the archive uses other file formats.")
)
write_json(inventory, out, auto_unbox=TRUE, pretty=TRUE, null="null")
cat(toJSON(list(archive_files=length(all_files), rda_files=length(files), tabular_files=length(text_files), inventory=out), auto_unbox=TRUE), "\\n")
