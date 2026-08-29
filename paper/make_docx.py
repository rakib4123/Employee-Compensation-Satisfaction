"""Build the Word version of the compensation-satisfaction proposal.

Pandoc is not available in this environment, so the .docx is constructed
directly rather than converted. Content is identical to main.tex, and the
layout follows the IEEE conference template:

  page      US Letter, margins top 0.75in / bottom 1.0in / sides 0.625in
  columns   two, 3.5in each with a 0.2in gutter; title and authors span
            the full width via a continuous section break
  type      Times New Roman 10pt body, justified, 0.2in first-line indent
  abstract  9pt bold italic, opening "Abstract—"
  headings  section: 10pt centred small caps, roman-numbered
            subsection: 10pt italic, letter-labelled
  floats    figures column-width with 8pt captions below; tables with
            8pt small-caps captions above
  refs      8pt, hanging indent, IEEE numbered [n]

The figures are embedded from PNG (Word cannot embed PDF), rasterised from
the same PDFs the LaTeX build uses. Missing PNGs are regenerated automatically
via pdftoppm, so this script is safe to run from a clean checkout.

Usage:  venv/bin/python paper/make_docx.py
"""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
EDA = HERE / "eda"
OUT = HERE / "main.docx"

# IEEE conference template metrics (US Letter):
#   margins  top 0.75in, bottom 1.0in, left/right 0.625in
#   two columns 3.5in wide with a 0.2in gutter  ->  8.5 - 1.25 = 7.25in
#   body 10pt Times, abstract 9pt bold italic, references 8pt
BODY_FONT = "Times New Roman"
BODY_SIZE = Pt(10)
COLUMN_IN = 3.4          # usable width inside one IEEE column
MUTED = RGBColor(0x52, 0x51, 0x4E)


def set_columns(section, num=2, space_in=0.2):
    """python-docx has no column API; write the w:cols element directly."""
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sectPr.append(cols)
    cols.set(qn("w:num"), str(num))
    cols.set(qn("w:space"), str(int(space_in * 1440)))
    cols.set(qn("w:equalWidth"), "1")


def ieee_margins(section):
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(0.625)
    section.right_margin = Inches(0.625)


def setup(doc):
    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = BODY_SIZE
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.first_line_indent = Inches(0.2)
    style.paragraph_format.line_spacing = 1.0
    for section in doc.sections:
        ieee_margins(section)

    # IEEE section headings: centred, small caps, 10pt, roman-numbered.
    h1 = doc.styles["Heading 1"]
    h1.font.name = BODY_FONT
    h1.font.size = Pt(10)
    h1.font.bold = False
    h1.font.small_caps = True
    h1.font.color.rgb = RGBColor(0, 0, 0)
    h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h1.paragraph_format.space_before = Pt(12)
    h1.paragraph_format.space_after = Pt(4)
    h1.paragraph_format.first_line_indent = Inches(0)

    # IEEE subsections: left, italic, letter-labelled.
    h2 = doc.styles["Heading 2"]
    h2.font.name = BODY_FONT
    h2.font.size = Pt(10)
    h2.font.bold = False
    h2.font.italic = True
    h2.font.color.rgb = RGBColor(0, 0, 0)
    h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h2.paragraph_format.space_before = Pt(8)
    h2.paragraph_format.space_after = Pt(2)
    h2.paragraph_format.first_line_indent = Inches(0)


def para(doc, text, *, align=WD_ALIGN_PARAGRAPH.JUSTIFY, italic=False, bold=False,
         size=None, space_after=None, center=False, indent=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else align
    run = p.add_run(text)
    run.italic = italic
    run.bold = bold
    if size:
        run.font.size = Pt(size)
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    if indent is not None:
        p.paragraph_format.first_line_indent = Inches(indent)
    return p


def labelled(doc, label, text, size=9, italic_body=True, indent=0):
    """Abstract / declaration entry: bold label, then the sentence.
    IEEE sets the abstract 9pt bold italic; declarations reuse the shape at
    body size."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.first_line_indent = Inches(indent)
    run = p.add_run(f"{label} ")
    run.bold = True
    run.italic = italic_body
    run.font.size = Pt(size)
    body = p.add_run(text)
    body.bold = italic_body        # IEEE abstract is bold italic throughout
    body.italic = italic_body
    body.font.size = Pt(size)
    return p


def figure(doc, image, caption, width=COLUMN_IN):
    """Figures are column-width in IEEE; captions are 8pt, centred, below."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Inches(0)
    p.paragraph_format.space_before = Pt(6)
    p.add_run().add_picture(str(image), width=Inches(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.LEFT
    c.paragraph_format.first_line_indent = Inches(0)
    c.paragraph_format.space_after = Pt(10)
    run = c.add_run(caption)
    run.font.size = Pt(8)


def table(doc, headers, rows, caption):
    """IEEE tables: caption ABOVE in small caps, 8pt body, column width."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Inches(0)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(caption)
    run.font.size = Pt(8)
    run.font.small_caps = True

    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.autofit = True
    for cell, text in zip(t.rows[0].cells, headers):
        cell.text = ""
        cp = cell.paragraphs[0]
        cp.paragraph_format.first_line_indent = Inches(0)
        r = cp.add_run(text)
        r.bold = True
        r.font.size = Pt(8)
        r.font.name = BODY_FONT
    for row in rows:
        cells = t.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = ""
            cp = cell.paragraphs[0]
            cp.paragraph_format.first_line_indent = Inches(0)
            r = cp.add_run(str(text))
            r.font.size = Pt(8)
            r.font.name = BODY_FONT
    tail = doc.add_paragraph()
    tail.paragraph_format.space_after = Pt(8)
    tail.paragraph_format.first_line_indent = Inches(0)


FIGURES = ["fig1_satisfaction", "fig2_salary_scatter",
           "fig3_correlation", "fig4_data_quality"]


def ensure_pngs():
    """Word embeds raster images only. Rasterise any figure PDF whose PNG is
    absent, so a clean checkout builds without a manual step."""
    import subprocess
    for name in FIGURES:
        png, pdf = EDA / f"{name}.png", EDA / f"{name}.pdf"
        if png.exists():
            continue
        if not pdf.exists():
            raise SystemExit(f"missing {pdf}; run: venv/bin/python paper/eda/make_figures.py")
        subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                        str(pdf), str(EDA / name)], check=True)
        print(f"  rasterised {png.name}")


def build():
    ensure_pngs()
    doc = Document()
    setup(doc)

    # --- front matter: single column across the full page ----------------
    set_columns(doc.sections[0], num=1)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.paragraph_format.first_line_indent = Inches(0)
    t.paragraph_format.space_after = Pt(10)
    r = t.add_run("Are Employees Satisfied With Their Compensation?\n"
                  "A Mixed-Methods Research Proposal for Measuring Pay Satisfaction "
                  "and Perceived Fairness Among Early-Career Technology Professionals")
    r.font.size = Pt(20)          # IEEE title is 24pt; 20 keeps a 3-line title on one page

    for text, size, italic, after in [
        ("Md. Rakib Hossain", 11, False, 0),
        ("Department of Computer Science and Engineering", 10, True, 0),
        ("American International University–Bangladesh, Dhaka, Bangladesh", 10, True, 0),
        ("000.mdrakibhossain@gmail.com", 10, True, 14),
    ]:
        p = para(doc, text, center=True, size=size, italic=italic,
                 space_after=after, indent=0)

    # --- body: two columns, IEEE gutter ----------------------------------
    body = doc.add_section(WD_SECTION.CONTINUOUS)
    ieee_margins(body)
    set_columns(body, num=2, space_in=0.2)

    labelled(doc, "Abstract—Purpose:", "This proposal sets out a study to measure how satisfied "
             "early-career technology professionals are with their compensation, and to "
             "identify which factors shape that judgement.")
    labelled(doc, "Research question:", "To what extent are early-career technology "
             "professionals satisfied with their current compensation, and what "
             "attributes explain variation in that satisfaction?")
    labelled(doc, "Hypothesis:", "H1 — pay satisfaction is driven less by absolute "
             "salary than by perceived fairness relative to role, responsibility, and "
             "market rate; H0 — pay satisfaction varies only with absolute salary level.")
    labelled(doc, "Methodology:", "A cross-sectional mixed-methods design combines a "
             "structured questionnaire with semi-structured follow-up interviews. "
             "Quantitative responses are summarised descriptively and triangulated "
             "against coded qualitative accounts.")
    labelled(doc, "Research participants:", "Approximately 120 salaried technology "
             "professionals aged 21–30 with up to five years of professional experience, "
             "recruited from software, data, and design roles in Dhaka.")
    labelled(doc, "Research tools:", "A fifteen-item questionnaire adapted from the Pay "
             "Satisfaction Questionnaire, a semi-structured interview guide, and a "
             "structured literature review.")
    labelled(doc, "Probable result:", "A pilot of thirteen respondents returned a mean "
             "satisfaction of 3.38 on a five-point scale, with only 38.5% rating four or "
             "above and the modal response at neutral. The full study is therefore "
             "expected to find predominantly neutral rather than positive compensation "
             "satisfaction, with dissatisfaction concentrated in perceptions of fairness "
             "rather than in salary magnitude.")
    labelled(doc, "Conclusion and recommendation:", "If confirmed, the finding implies "
             "that employers cannot resolve compensation dissatisfaction through pay "
             "increases alone; transparent pay structures and explicit role-to-pay "
             "mapping are likely to matter more. The instrument and analysis plan "
             "described here are offered as a replicable basis for that assessment.")

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.first_line_indent = Inches(0)
    r = p.add_run("Keywords—")
    r.bold = True
    r.italic = True
    r.font.size = Pt(9)
    k = p.add_run("compensation satisfaction, pay satisfaction, perceived fairness, "
                  "equity theory, employee retention, mixed-methods research")
    k.bold = True
    k.italic = True
    k.font.size = Pt(9)

    # --- I. Introduction -------------------------------------------------
    doc.add_heading("I. Introduction", level=1)
    para(doc, "Compensation is the most direct exchange between an employer and an "
         "employee, yet satisfaction with it is not a simple function of amount. Two "
         "people paid identically may evaluate their pay very differently depending on "
         "what they believe they contribute, what they believe others receive, and what "
         "they believe the market rate to be. This gap between the objective figure and "
         "the subjective judgement is what makes compensation satisfaction worth "
         "measuring separately from compensation itself.")
    para(doc, "The distinction matters practically. Organisations that treat "
         "dissatisfaction as a pricing problem respond with across-the-board increases, "
         "which are expensive and, if the underlying grievance concerns fairness rather "
         "than magnitude, ineffective. A study that separates the two allows a more "
         "targeted response.")
    para(doc, "This proposal describes a study designed to make that separation. It "
         "states the research question and hypotheses, specifies the population and "
         "sampling frame, details the three instruments, and reports pilot data that "
         "motivate the design. The pilot is small and its limitations are stated plainly; "
         "it is presented as evidence that the instrument functions and that the "
         "phenomenon is worth studying at scale, not as a finding in its own right.")

    # --- II. Literature Review -------------------------------------------
    doc.add_heading("II. Literature Review", level=1)
    para(doc, "Research on pay satisfaction has consistently treated it as a judgement of "
         "relative rather than absolute standing. Adams's equity theory frames the "
         "employee as comparing a ratio of personal inputs to outcomes against the "
         "corresponding ratio of a referent other; inequity in either direction produces "
         "tension and a motivation to restore balance [1]. On this account, an employee "
         "paid well in absolute terms may still report dissatisfaction if the comparison "
         "is unfavourable.")
    para(doc, "Herzberg's two-factor theory positions salary as a hygiene factor: its "
         "absence produces dissatisfaction, but its presence does not proportionally "
         "produce satisfaction [2]. The practical implication is asymmetric — "
         "underpayment reliably harms, while overpayment does not reliably help.")
    para(doc, "The measurement literature refined the construct further. Heneman and "
         "Schwab demonstrated that pay satisfaction is multidimensional rather than "
         "unitary, and developed the Pay Satisfaction Questionnaire to separate "
         "satisfaction with pay level, benefits, raises, and pay structure and "
         "administration [3]. Treating pay satisfaction as a single score, as much survey "
         "practice still does, therefore risks collapsing distinct judgements that may "
         "move independently.")
    para(doc, "The largest synthesis of this work is the meta-analysis by Williams, "
         "McDaniel, and Nguyen, covering 240 samples drawn from 203 studies. It reports "
         "that pay level satisfaction correlates with a broad set of antecedents and "
         "outcomes, and that its relationship with actual pay, while positive, is far "
         "from deterministic [4]. This supports the design decision taken here to collect "
         "perceptual measures alongside reported salary rather than to infer satisfaction "
         "from salary.")
    para(doc, "More recent work situates these mechanisms in the technology sector "
         "specifically. Murugan and Philimis find that compensation, recognition, and "
         "work environment jointly determine retention among information technology "
         "employees, with compensation acting alongside rather than independently of the "
         "other two [5]. Their finding motivates the inclusion of qualitative interviews "
         "in the present design, since a purely numerical instrument cannot capture "
         "recognition effects.")
    para(doc, "Two gaps follow from this review. First, the pay satisfaction literature "
         "is dominated by samples from large Western organisations, leaving early-career "
         "professionals in South Asian technology firms under-represented. Second, few "
         "studies pair a quantitative satisfaction measure with open qualitative accounts "
         "from the same respondents, which is what would be needed to distinguish a "
         "magnitude complaint from a fairness complaint. This study addresses both.")

    # --- III. Methodology -------------------------------------------------
    doc.add_heading("III. Research Methodology", level=1)

    doc.add_heading("A. Scope and Area", level=2)
    para(doc, "The study falls within human resource management, specifically the "
         "measurement of compensation satisfaction and perceived pay fairness. It is "
         "empirical and cross-sectional. It does not evaluate compensation policy, model "
         "salary determination, or track satisfaction over time; each would require a "
         "different design.")

    doc.add_heading("B. Class and Social Specification", level=2)
    para(doc, "The target population is salaried early-career technology professionals "
         "employed in Dhaka, Bangladesh. Socially, this group is urban, "
         "university-educated, and employed in the formal private sector. It is "
         "economically heterogeneous despite its educational homogeneity: entry salaries "
         "in the sector span roughly BDT 15,000 to BDT 120,000 per month, which is wide "
         "enough for equity comparisons to arise within a single peer group. That "
         "internal spread is precisely what makes the population suitable for testing a "
         "relative-comparison hypothesis.")

    doc.add_heading("C. Research Participants", level=2)
    para(doc, "The full study targets approximately 120 participants, a sample size "
         "chosen to support subgroup comparison across role and experience band while "
         "remaining feasible for a single researcher. Participants must be aged 21–30, "
         "hold a completed undergraduate degree, and be in paid employment with no more "
         "than five years of professional experience.")
    para(doc, "The pilot reported here recruited 13 participants. Their characteristics "
         "are given in Table 1. All held technology or technology-adjacent roles — "
         "software engineering, data analysis, and graphic design — and all reported an "
         "academic background in computer science or a closely related field.")
    table(doc, ["Attribute", "Value"], [
        ["Age range", "21–26 years"],
        ["Mean age", "23.5 years"],
        ["Professional experience", "1–5 years (mean 3.0)"],
        ["Highest qualification", "BSc 10, MSc 2, other 1"],
        ["Role: Software Engineer", "6"],
        ["Role: Data Analyst", "4"],
        ["Role: Graphic Designer", "1"],
        ["Role: Other (self-specified)", "2"],
        ["Reported monthly salary", "BDT 15,000–120,000"],
    ], "Table 1. Pilot participant characteristics (n = 13)")

    doc.add_heading("D. Research Tools", level=2)
    para(doc, "Three instruments are used, each addressing a different limitation of the "
         "others.")
    para(doc, "Questionnaire. A fifteen-item structured questionnaire collects "
         "demographic attributes, professional attributes (experience, qualifications, "
         "publications, projects led, training completed), reported monthly salary, and a "
         "five-point compensation satisfaction rating. The satisfaction item and its "
         "framing are adapted from the Pay Satisfaction Questionnaire [3]. The instrument "
         "is self-administered and distributed electronically.")
    para(doc, "Semi-structured interview. A subset of respondents is invited to a "
         "follow-up interview built around one open prompt — what would make your "
         "compensation feel more fair — with probes for role comparison, market "
         "awareness, and recognition. The interview exists to recover the reasoning "
         "behind a numerical rating, which the questionnaire cannot capture. In the pilot "
         "this prompt was administered in written form, and its yield is discussed in "
         "Section V.")
    para(doc, "Literature review. A structured review establishes the theoretical frame, "
         "supplies the validated constructs the questionnaire adapts, and provides the "
         "comparison base against which the study's findings are interpreted.")

    doc.add_heading("E. Data Analysis", level=2)
    para(doc, "Quantitative responses are analysed descriptively: frequency distribution, "
         "mean, median, and mode of the satisfaction rating, reported overall and "
         "disaggregated by role and experience band. Given the intended sample size, "
         "inferential testing is planned only for the full study, and only where subgroup "
         "counts permit.")
    para(doc, "Qualitative responses are analysed by thematic coding. Open-text answers "
         "are coded inductively, codes are grouped into themes, and theme frequency is "
         "compared against satisfaction ratings from the same respondents. The comparison "
         "is the mechanism by which the hypothesis is tested: if dissatisfaction is a "
         "magnitude problem, low ratings should co-occur with requests for a specific "
         "increase; if it is a fairness problem, low ratings should co-occur with "
         "comparison language.")

    doc.add_heading("F. Ethical Considerations", level=2)
    para(doc, "Participation is voluntary and informed. No names, employer identifiers, "
         "or contact details are collected. Salary data is stored separately from any "
         "identifying attribute, and reported only in aggregate or in bands. Respondents "
         "may withdraw at any point before analysis. Submission timestamps were removed "
         "from the pilot dataset before archiving, since they were quasi-identifying "
         "within a small cohort and served no analytical purpose.")

    # --- IV. EDA ----------------------------------------------------------
    doc.add_heading("IV. Exploratory Data Analysis of the Pilot", level=1)
    para(doc, "Before the pilot responses are used to anticipate anything, they are "
         "profiled for structure, completeness, and internal plausibility. The exercise "
         "is reported here rather than confined to an appendix because one of its "
         "findings changes how the pilot may be read.")

    doc.add_heading("A. Completeness", level=2)
    para(doc, "Figure 1 summarises missingness across the fields used in analysis. Three "
         "patterns emerge. The conditional other job title field is empty for 69.2% of "
         "responses, which is expected — only respondents who select “Other” complete it "
         "— and is reported for completeness rather than flagged as a defect. Salary is "
         "missing for 15.4%: two respondents entered a literal zero, values treated as "
         "non-responses rather than as earnings of zero. Experience and projects led are "
         "each missing one value.")
    figure(doc, EDA / "fig4_data_quality.png",
           "Figure 1. Missing values by field. Thresholds at 5% and 30% mark the warn and "
           "fail bands. The 69.2% gap in other job title is a conditional field, not a "
           "data-quality failure.")

    doc.add_heading("B. Distributions and Outliers", level=2)
    para(doc, "An interquartile-range screen flags outliers in four fields. Publications "
         "is the most extreme: the distribution is strongly right-skewed (skew = 1.99, "
         "mean 6.69, maximum 30), and the three highest values — 10, 26, and 30 — come "
         "from respondents aged 22 to 25 with four to five years of experience. A "
         "publication count of thirty at that career stage is not credible, and the most "
         "likely explanation is that respondents interpreted the question more broadly "
         "than intended. The item requires rewording before the full study.")
    para(doc, "Reported salary is similarly distorted. Its standard deviation "
         "(BDT 167,276) exceeds its mean (BDT 153,182), with a maximum of BDT 500,000 per "
         "month against a median of BDT 70,000. For the roles reported, the three highest "
         "values are implausible as monthly figures and may be annual amounts entered in "
         "a monthly field.")
    para(doc, "One further observation concerns the department field. After normalising "
         "case and spelling variants, it collapses to a single distinct value: every "
         "respondent reported a computer-science department. The field therefore has zero "
         "variance and can discriminate nothing. This confirms the homogeneity noted in "
         "Section III-C and is the reason the full study recruits across firms rather "
         "than through one academic network.")

    doc.add_heading("C. The Salary–Satisfaction Relationship", level=2)
    para(doc, "The pilot's most consequential finding concerns the association between "
         "pay and satisfaction, shown in Figure 2. Across all eleven respondents who "
         "reported a usable salary, the correlation is moderately negative (r = −0.58 "
         "Pearson, ρ = −0.54 Spearman) — higher earners appear less satisfied.")
    para(doc, "That result does not survive scrutiny. Restricting the calculation to the "
         "eight respondents whose salary is plausible for their stated role eliminates it "
         "entirely (r = −0.02). The apparent inverse relationship is an artefact of three "
         "suspect data points, not a property of the population.")
    figure(doc, EDA / "fig2_salary_scatter.png",
           "Figure 2. Reported salary against satisfaction. Triangles mark the three "
           "entries above BDT 200,000 per month judged implausible for the stated role. "
           "The correlation across all points (r = −0.58) collapses to r = −0.02 once "
           "they are excluded. “×2” marks two coincident respondents.")
    para(doc, "The methodological lesson is worth stating plainly, because it would have "
         "been easy to report the headline figure and stop. A correlation computed over "
         "eleven observations can be driven almost entirely by three of them. Had the "
         "negative coefficient been reported without the plausibility screen, the paper "
         "would have claimed an inverse pay–satisfaction relationship on the strength of "
         "three probable data-entry errors.")
    para(doc, "The screened result still bears on the hypothesis, but through absence "
         "rather than through sign: within this cohort, salary and satisfaction are "
         "essentially unrelated. That is consistent with H1 — satisfaction tracking "
         "perceived fairness rather than magnitude — and inconsistent with H0, which "
         "requires satisfaction to rise with pay.")

    doc.add_heading("D. What Does Covary With Satisfaction", level=2)
    para(doc, "Figure 3 gives the Spearman correlation matrix. The strongest positive "
         "correlate of satisfaction is not salary but the manager performance rating "
         "(ρ = +0.70), followed by self-rated skill (ρ = +0.50). Both are recognition "
         "measures rather than pay measures, which is the association Murugan and "
         "Philimis report for information technology employees [5].")
    figure(doc, EDA / "fig3_correlation.png",
           "Figure 3. Spearman rank correlations among pilot variables. The diverging "
           "scale is symmetric about zero with a neutral midpoint; cell values are "
           "printed so the matrix reads without colour.")
    para(doc, "At n = 13 none of these coefficients is statistically meaningful, and none "
         "is reported with a p-value for that reason. They are recorded as directions "
         "worth testing at scale, not as findings.")

    # --- V. Probable Results ---------------------------------------------
    doc.add_heading("V. Probable Results", level=1)
    para(doc, "The pilot provides a basis for anticipating the full study's outcome. "
         "Table 2 and Figure 4 report the observed distribution.")
    table(doc, ["Rating", "Count", "Share"], [
        ["5 — Very satisfied", "3", "23.1%"],
        ["4 — Satisfied", "2", "15.4%"],
        ["3 — Neutral", "6", "46.2%"],
        ["2 — Dissatisfied", "1", "7.7%"],
        ["1 — Very dissatisfied", "1", "7.7%"],
        ["Mean", "3.38", "—"],
        ["Median / Mode", "3 / 3", "—"],
        ["Satisfied (≥ 4)", "5", "38.5%"],
    ], "Table 2. Pilot compensation satisfaction distribution (n = 13)")
    figure(doc, EDA / "fig1_satisfaction.png",
           "Figure 4. Compensation satisfaction in the pilot (n = 13). The modal response "
           "is the neutral midpoint; fewer than two respondents in five rate their "
           "compensation at 4 or above.")
    para(doc, "Three patterns are expected to persist at scale.")
    para(doc, "First, the central tendency is neutral, not positive. Fewer than two in "
         "five pilot respondents rated their compensation satisfaction at four or above, "
         "and the modal response was the midpoint. The full study is therefore expected "
         "to find that early-career technology professionals are predominantly neutral "
         "about their compensation rather than satisfied with it.")
    para(doc, "Second, the qualitative responses point to fairness rather than magnitude. "
         "Where respondents elaborated, they described compensation that should reflect "
         "“role, responsibilities, workload, and market standard,” asked for “fair "
         "evaluation,” and tied increases to “responsibilities and performance.” Only one "
         "response named a specific figure. This is the pattern equity theory predicts [1] "
         "and is consistent with salary operating as a hygiene factor [2]. It is the "
         "primary reason H1 is favoured over H0.")
    para(doc, "Third, satisfaction is not a function of reported salary. As Section IV-C "
         "established, the screened association is effectively zero, while the manager "
         "rating shows the strongest positive relationship in the matrix. This is what "
         "the meta-analytic evidence would lead one to expect [4], and it is the "
         "observation that most justifies collecting perceptual data rather than "
         "inferring satisfaction from payroll records.")
    para(doc, "These are anticipations, not findings. The pilot is too small to establish "
         "any of them.")

    # --- VI. Limitations --------------------------------------------------
    doc.add_heading("VI. Limitations", level=1)
    para(doc, "The pilot has four limitations that constrain what may be claimed from it, "
         "and that the full study is designed to address.")
    para(doc, "Sample size is the principal constraint. Thirteen responses support "
         "description only. No significance test is reported here because none would be "
         "meaningful at this n, and no proportion given above should be read as an "
         "estimate of a population parameter.")
    para(doc, "Sampling was non-probabilistic and homogeneous. The exploratory analysis "
         "quantified this: after normalisation the department field held one distinct "
         "value across all thirteen responses. The pilot therefore describes a single "
         "narrow cohort and cannot speak to compensation satisfaction in other sectors, "
         "age groups, or educational backgrounds. The full study widens recruitment "
         "across firms rather than through one academic network, though it remains a "
         "convenience sample.")
    para(doc, "Self-reported measures were unverified, and two proved unreliable. Salary "
         "contained entries inconsistent with the stated role by an order of magnitude "
         "plus two zeros; the full instrument replaces the free-text field with banded "
         "options, reducing both entry error and disclosure reluctance. Publication "
         "counts reached thirty for a respondent with five years of experience, "
         "indicating that the question was read more broadly than intended; it requires "
         "rewording with an explicit definition.")
    para(doc, "The satisfaction measure was single-item. Since pay satisfaction is "
         "established as multidimensional [3], a single rating conflates satisfaction "
         "with pay level, raises, benefits, and administration. The full study replaces "
         "it with a multi-item scale separating those dimensions.")

    # --- VII. Conclusion --------------------------------------------------
    doc.add_heading("VII. Conclusion and Recommendations", level=1)
    para(doc, "This proposal has set out a mixed-methods design for measuring "
         "compensation satisfaction among early-career technology professionals, "
         "combining a structured questionnaire, semi-structured interviews, and a "
         "literature review. Pilot evidence from thirteen respondents indicates "
         "predominantly neutral satisfaction, with elaborated complaints concentrated on "
         "fairness rather than on salary magnitude.")
    para(doc, "Three recommendations follow, each contingent on the full study confirming "
         "the pilot pattern.")
    para(doc, "For employers, compensation dissatisfaction should not be treated as "
         "solely a pricing problem. If the grievance concerns the relationship between "
         "pay and responsibility rather than the figure itself, an across-the-board "
         "increase is an expensive response to a mis-diagnosed cause. Publishing "
         "role-to-band mappings and the criteria governing progression addresses the "
         "stated concern more directly.")
    para(doc, "For practitioners designing compensation reviews, the asymmetry between "
         "magnitude and fairness complaints is measurable and should be measured. Pairing "
         "a satisfaction rating with one open question about fairness costs little and "
         "distinguishes the two.")
    para(doc, "For researchers, the under-representation of South Asian early-career "
         "technology cohorts in the pay satisfaction literature is worth addressing. The "
         "instrument described here is offered as a replicable starting point, with the "
         "caveat that its single-item satisfaction measure requires replacement by a "
         "multidimensional scale before any inferential claim is attempted.")

    # --- Declarations -----------------------------------------------------
    doc.add_heading("Declarations", level=1)
    for label, text in [
        ("Data Availability.", "The anonymised pilot dataset and the processing scripts "
         "supporting this proposal are available in the project repository. Submission "
         "timestamps were removed prior to archiving. Individual-level records containing "
         "identifying attributes are not distributed."),
        ("Ethics.", "Pilot participation was voluntary. No names, employer identifiers, "
         "or contact details were collected. As a course-level pilot conducted without "
         "institutional funding, the study did not undergo formal ethics board review; "
         "the full study will be submitted for review before data collection begins."),
        ("Author Contributions (CRediT).", "Md. Rakib Hossain — Conceptualization, "
         "Methodology, Investigation, Data Curation, Formal Analysis, Writing (original "
         "draft), Writing (review and editing)."),
        ("Conflict of Interest.", "The author declares no competing interests."),
        ("Funding.", "This research received no external funding."),
        ("AI Usage Disclosure.", "An AI assistant (Claude, Anthropic) was used to assist "
         "with drafting and structuring this manuscript, to compute descriptive "
         "statistics from the pilot dataset, and to verify bibliographic metadata against "
         "Crossref. All cited references were checked against Crossref DOI records. The "
         "author reviewed and is responsible for all content, including the "
         "interpretation of results and the conclusions drawn."),
    ]:
        labelled(doc, label, text, size=10, italic_body=False, indent=0.2)

    # --- References -------------------------------------------------------
    doc.add_heading("References", level=1)
    refs = [
        "J. S. Adams, “Towards an understanding of inequity,” The Journal of Abnormal and "
        "Social Psychology, vol. 67, no. 5, pp. 422–436, 1963, doi: 10.1037/h0040968.",
        "F. Herzberg, B. Mausner, and B. B. Snyderman, The Motivation to Work, 2nd ed. "
        "New York, NY, USA: John Wiley and Sons, 1959.",
        "H. G. Heneman and D. P. Schwab, “Pay satisfaction: Its multidimensional nature "
        "and measurement,” International Journal of Psychology, vol. 20, no. 1, "
        "pp. 129–141, 1985, doi: 10.1080/00207598508247727.",
        "M. L. Williams, M. A. McDaniel, and N. T. Nguyen, “A meta-analysis of the "
        "antecedents and consequences of pay level satisfaction,” Journal of Applied "
        "Psychology, vol. 91, no. 2, pp. 392–413, 2006, doi: 10.1037/0021-9010.91.2.392.",
        "K. P. Murugan and J. Philimis, “Determinants of employee retention in the IT "
        "sector: An empirical study on the impact of recognition, compensation, and work "
        "environment,” International Review of Economics, vol. 72, no. 2, 2025, "
        "doi: 10.1007/s12232-025-00507-9.",
    ]
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.22)
        p.paragraph_format.first_line_indent = Inches(-0.22)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"[{i}] {ref}")
        run.font.size = Pt(8)

    doc.save(OUT)
    print(f"wrote {OUT}")
    return doc


if __name__ == "__main__":
    build()
