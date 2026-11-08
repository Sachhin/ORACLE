#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(jsonlite))
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) stop("Usage: inspect_mendeley_longevity_dataset.R <extracted-dir> <output.json>")
root <- normalizePath(args[[1]], mustWork = TRUE)
out <- args[[2]]
files <- list.files(root, pattern = "\\.(rda|RData)$", recursive = TRUE,
                    full.names = TRUE, ignore.case = TRUE)
if (!length(files)) stop("No .rda/.RData files found in public Mendeley archive")
inspect_one <- function(file) {
  env <- new.env(parent = baseenv())
  loaded <- tryCatch(load(file, envir = env), error = function(e) structure(list(message=conditionMessage(e)), class="load_error"))
  if (inherits(loaded, "load_error")) return(list(file=substring(file,nchar(root)+2), error=loaded$message))
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
      item$metadata <- list(rows=nrow(x), columns=cols,
        age_column=if(length(age_col)) age_col[[1]] else NULL,
        sex_column=if(length(sex_col)) sex_col[[1]] else NULL,
        region_column=if(length(region_col)) region_col[[1]] else NULL,
        id_column=if(length(id_col)) id_col[[1]] else NULL)
      if(length(age_col)) {
        age <- suppressWarnings(as.numeric(x[[age_col[[1]]]]))
        item$metadata$age_summary <- list(n=sum(is.finite(age)),
          min=if(any(is.finite(age))) min(age,na.rm=TRUE) else NULL,
          median=if(any(is.finite(age))) median(age,na.rm=TRUE) else NULL,
          max=if(any(is.finite(age))) max(age,na.rm=TRUE) else NULL,
          n_ge_90=sum(age>=90,na.rm=TRUE), n_lt_90=sum(age<90,na.rm=TRUE))
      }
    }
    if (!is.null(d) && length(d)==2 && d[[1]]>=1000 && d[[2]]>=50) {
      item$matrix_candidate <- TRUE
      item$rownames_present <- !is.null(rownames(x))
      item$colnames_present <- !is.null(colnames(x))
    }
    item
  })
  list(file=substring(file,nchar(root)+2), objects=objects)
}
inventory <- list(
  dataset="Mendeley Data fpf4y72kfz version 1",
  doi="10.17632/fpf4y72kfz.1",
  files= lapply(files, inspect_one),
  notes=c("This is an archive/object inventory, not a biological result.",
          "Sample identifiers are not emitted in this report.",
          "Expression matrices require design, library-preparation and cohort checks before inference.")
)
write_json(inventory, out, auto_unbox=TRUE, pretty=TRUE, null="null")
cat(toJSON(list(rda_files=length(files), inventory=out), auto_unbox=TRUE), "\\n")
