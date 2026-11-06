"""Conservative domain-specific experiment protocol scaffolds.

Templates provide reproducibility prompts, not validated wet-lab SOPs. Every
returned experiment remains PROPOSED and requires domain-expert review.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Experiment, ResearchRun


@dataclass(frozen=True)
class ProtocolTemplate:
    domain: str
    version: str
    steps: tuple[str, ...]
    limitations: str


_TEMPLATES = {
    "plant_biology": ProtocolTemplate(
        "plant_biology", "1.0",
        (
            "State the biological question, species, accession/ecotype, genotype, developmental stage, and tissue.",
            "Pre-register treatment conditions, exposure duration, environmental conditions, and primary phenotype/readout.",
            "Include matched untreated/vehicle controls and, where available, a positive control that verifies assay responsiveness.",
            "Define independent biological replicates before data collection; distinguish biological from technical replicates.",
            "Randomize sample allocation and pot/plate/tray positions; record growth-chamber, plate, and harvest batch metadata.",
            "Blind image scoring or quantitative phenotype assessment where practical; document exclusions before unblinding.",
            "Record sample identifiers, collection time, instrument settings, reagent/seed lot identifiers, and protocol deviations.",
            "Specify the statistical model, multiple-testing correction, effect-size reporting, and missing-data handling before analysis.",
            "Archive raw measurements, sample metadata, analysis code, software versions, and checksums.",
        ),
        "Template only; species-, facility-, biosafety-, and treatment-specific requirements need expert review. No experiment is performed by ORACLE.",
    ),
    "molecular_biology": ProtocolTemplate(
        "molecular_biology", "1.0",
        (
            "Define the target, biological system, primary molecular readout, and pre-specified effect size of interest.",
            "Document organism/cell-line provenance, genotype, passage or generation, and authentication status.",
            "Predefine negative controls, positive assay controls, and an orthogonal validation readout.",
            "Specify independent biological replicates and technical replicates separately; justify sample size.",
            "Randomize sample processing order and record operator, reagent lots, instrument, and batch metadata.",
            "Predefine quality-control thresholds and exclusion rules before examining group differences.",
            "Record exact reagent identities, catalog/lot information, instrument settings, and protocol deviations.",
            "Predefine statistical contrasts, covariates, multiple-testing correction, and uncertainty reporting.",
            "Preserve raw instrument outputs, metadata, analysis scripts, software versions, and checksums.",
        ),
        "Template only; reagent-specific, organism-specific, and institutional biosafety review is required. No experiment is performed by ORACLE.",
    ),
    "cell_biology": ProtocolTemplate(
        "cell_biology", "1.0",
        (
            "Specify cell type, source, authentication, passage range, culture conditions, and primary endpoint.",
            "Define treatment groups, exposure window, vehicle controls, positive controls, and untreated controls.",
            "Predefine mycoplasma status checks and cell-health/viability acceptance criteria.",
            "Use independent biological replicates (independent cultures/experiments); do not count image fields as biological replicates.",
            "Randomize plate positions and acquisition order; record plate, incubator, operator, and reagent-lot batches.",
            "Blind image acquisition/quantification where practical and predefine segmentation/exclusion rules.",
            "Record microscope/cytometer settings, calibration, raw images/files, and all protocol deviations.",
            "Predefine the statistical model, nested structure where needed, multiple-testing correction, and effect sizes.",
            "Archive raw data, metadata, analysis code, software versions, and checksums.",
        ),
        "Template only; cell-line, facility, ethics, and biosafety requirements need expert review. No experiment is performed by ORACLE.",
    ),
    "computational_biology": ProtocolTemplate(
        "computational_biology", "1.0",
        (
            "State the computational hypothesis, target estimand, primary endpoint, and falsifiable success criterion.",
            "Record dataset accession, source URL, licence, retrieval date, file checksums, and inclusion criteria.",
            "Predefine sample/feature identifiers, phenotype labels, covariates, batch variables, and missing-data handling.",
            "Prevent information leakage by separating training, validation, and held-out test data before model fitting.",
            "Specify preprocessing and normalization methods, reference genome/annotation versions, and all parameter values.",
            "Include simple baselines, negative controls/permutation checks, and sensitivity analyses.",
            "Fix and record random seeds; pin software, package, and runtime versions; capture hardware when relevant.",
            "Predefine metrics, confidence intervals, multiple-testing correction, and model-selection rules.",
            "Archive executable code, environment lockfiles, logs, intermediate manifests, and checksums for independent reruns.",
        ),
        "Template only; dataset licences, study design, and analysis assumptions require review. Reproducibility is not guaranteed until independently rerun.",
    ),
}


class ExperimentProtocolBuilder:
    """Create a proposed experiment from a reviewed run context and domain template."""

    @staticmethod
    def domains() -> tuple[str, ...]:
        return tuple(sorted(_TEMPLATES))

    def build(
        self, run: ResearchRun, domain: str, hypothesis_id: str = "",
    ) -> Experiment:
        template = _TEMPLATES.get(domain)
        if template is None:
            raise ValueError(f"Unknown domain {domain!r}; choose one of {', '.join(self.domains())}.")
        hypothesis = None
        if hypothesis_id:
            hypothesis = next((item for item in run.hypotheses
                               if item.hypothesis_id == hypothesis_id), None)
            if hypothesis is None:
                raise ValueError(f"Hypothesis not found in run: {hypothesis_id}")
        question = (
            f"Test hypothesis: {hypothesis.statement}" if hypothesis
            else run.question
        )
        predictions = list(hypothesis.predictions) if hypothesis else [
            "Pre-register one primary measurable outcome and the observation that would falsify the working explanation."
        ]
        protocol = [
            f"[{template.domain} protocol template v{template.version}]",
            *template.steps,
            "Before execution, have a qualified reviewer approve feasibility, ethics, biosafety, controls, and statistical design.",
        ]
        experiment = Experiment(
            question=question,
            protocol=protocol,
            predictions=predictions,
            limitations=template.limitations,
        )
        run.experiments.append(experiment)
        return experiment
