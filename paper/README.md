# Compensation Satisfaction — Research Proposal (IEEE format)

## Files
- `main.tex`        — the paper (IEEEtran conference class), 5 pages
- `references.bib`  — 5 references, every DOI verified against Crossref
- `main.pdf`        — compiled output
- `main.docx`       — Word version, IEEE two-column layout
- `make_docx.py`    — rebuilds main.docx (needs python-docx)
- `Makefile`        — `make` to rebuild, `make clean` to remove aux files
- `eda/`            — exploratory data analysis
  - `survey_analysis.csv`  parsed/typed view of the 13 raw responses
  - `make_figures.py`      regenerates all four figures
  - `fig1..fig4 .pdf`      the figures embedded in the paper

## Regenerating the figures
    venv/bin/python eda/make_figures.py
Palette validated for colourblind separation; every figure carries a
non-colour encoding (marker shape, hatching, printed values) so it survives
greyscale printing.

## Headline EDA finding
r(salary, satisfaction) = -0.58 across all 11 usable responses, but -0.02
once three implausible salary entries (300k-500k BDT/month) are excluded.
The apparent inverse relationship is an artefact of three data points.
Strongest positive correlate of satisfaction is the manager rating
(Spearman +0.70), not salary.

## Rebuilding
    make
or manually:
    pdflatex main && bibtex main && pdflatex main && pdflatex main

Requires a TeX distribution with the IEEEtran class (TeX Live, MiKTeX, TinyTeX).

## References — all verified
| Key | DOI |
|---|---|
| adams1963inequity     | 10.1037/h0040968 |
| heneman1985pay        | 10.1080/00207598508247727 |
| williams2006meta      | 10.1037/0021-9010.91.2.392 |
| murugan2025retention  | 10.1007/s12232-025-00507-9 |
| herzberg1959motivation | book, no DOI |

## Pilot data behind the Probable Results section
n = 13. Mean satisfaction 3.38 / 5, median 3, mode 3.
Satisfied (rating >= 4): 5 of 13 = 38.5%.
Ages 21-26 (mean 23.5), 1-5 years experience (mean 3.0).
Source: `ml/data/survey_raw.tsv` in the parent repository.
