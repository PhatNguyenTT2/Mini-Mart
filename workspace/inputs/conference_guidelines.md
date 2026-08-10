# IEEE Conference Paper Writing Guidelines

## Language
All manuscripts must be in English.

## Submission Deadline
August 1, 2026.

The Literature Review Agent should derive cutoff_date = 2026-08-01 from this deadline. Papers published after this date may be cited only as concurrent work, never as prior baselines.

## Page Limit
Paper length is typically 6 to 8 pages in two-column IEEEtran format, excluding references.

## Mandatory Sections
Manuscripts should be structured into standard IEEE sections:
1. Introduction
2. Related Work
3. Proposed Methodology
4. System Implementation
5. Experiments and Results
6. Conclusion and Future Work

## Formatting Rules
- Two-column format using \documentclass[10pt,conference]{IEEEtran}
- Displayed equations should use standard LaTeX equation environment
- Figures should be centered using \centering, include figures/ in paths
- Tables should use booktabs (\toprule, \midrule, \bottomrule) or \hline
- Cross-references should use \cref{...} from the cleveref package
- Citations via \cite{...} commands with IEEEtran.bst bibliography style

## Review Criteria
Reviewers will assess: technical soundness, novelty, clarity of presentation, completeness of experimental evaluation, and reproducibility.

## Domain Context Constraint (Strict)
The application domain of this recommender system is strictly a mini-supermarket chain management system that supports both online and offline retail purchases. You must NEVER use the term "OCOP" (One Commune One Product) or refer to the system as an "OCOP e-commerce platform". Ensure all business use cases, cold-start examples, and system implementations reflect a modern convenience store / mini-supermarket chain environment.

