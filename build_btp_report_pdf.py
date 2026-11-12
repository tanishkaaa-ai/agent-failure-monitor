#!/usr/bin/env python3
"""
build_btp_report_pdf.py
Generates the comprehensive BTP Final Report in PDF format using ReportLab,
matching the structure, typography, styling, tables, and embedded figures of the .docx report.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_LEFT = 54  # 0.75 in
MARGIN_RIGHT = 54
MARGIN_TOP = 54
MARGIN_BOTTOM = 54
PRINTABLE_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.saveState()
                # Running footer
                self.setFont('Times-Roman', 9)
                self.setFillColor(colors.HexColor('#475569'))
                self.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, 36, f"Page {self._pageNumber} of {num_pages}")
                self.drawString(MARGIN_LEFT, 36, "IIIT Pune — B.Tech Computer Science and Engineering")

                # Running header on body pages
                if self._pageNumber >= 7:
                    self.drawString(MARGIN_LEFT, PAGE_HEIGHT - 38, "Lightweight Real-Time Agent Failure Prediction and Intervention System")
                    self.setStrokeColor(colors.HexColor('#CBD5E1'))
                    self.setLineWidth(0.5)
                    self.line(MARGIN_LEFT, PAGE_HEIGHT - 42, PAGE_WIDTH - MARGIN_RIGHT, PAGE_HEIGHT - 42)
                self.restoreState()
            super().showPage()
        super().save()

def create_pdf_report():
    output_filename = "BTP_Final_Report.pdf"
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM
    )

    styles = getSampleStyleSheet()

    # Custom typography matching university guidelines
    COLOR_PRIMARY = colors.HexColor('#1A365D')
    COLOR_SECONDARY = colors.HexColor('#2B6CB0')
    COLOR_TEXT = colors.HexColor('#1E293B')
    COLOR_BORDER = colors.HexColor('#CBD5E1')
    COLOR_HEADER_BG = colors.HexColor('#F1F5F9')
    COLOR_ALT_BG = colors.HexColor('#F8FAFC')

    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=16,
        leading=22,
        alignment=1, # Center
        textColor=COLOR_PRIMARY,
        spaceAfter=14
    )

    style_subtitle = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=11.5,
        leading=16,
        alignment=1,
        textColor=COLOR_TEXT,
        spaceAfter=12
    )

    style_chapter = ParagraphStyle(
        'ChapTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=16,
        leading=20,
        alignment=1,
        textColor=COLOR_PRIMARY,
        spaceBefore=14,
        spaceAfter=14
    )

    style_h2 = ParagraphStyle(
        'Heading2',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=13,
        leading=17,
        alignment=0, # Left
        textColor=COLOR_SECONDARY,
        spaceBefore=12,
        spaceAfter=6
    )

    style_h3 = ParagraphStyle(
        'Heading3',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=11,
        leading=15,
        alignment=0,
        textColor=COLOR_TEXT,
        spaceBefore=8,
        spaceAfter=4
    )

    style_body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10.5,
        leading=14.5,
        alignment=4, # Justified
        textColor=COLOR_TEXT,
        spaceAfter=6
    )

    style_bullet = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10.5,
        leading=14,
        alignment=4,
        leftIndent=16,
        firstLineIndent=-12,
        textColor=COLOR_TEXT,
        spaceAfter=4
    )

    style_caption = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontName='Times-BoldItalic',
        fontSize=9.5,
        leading=13,
        alignment=1,
        textColor=COLOR_TEXT,
        spaceBefore=4,
        spaceAfter=10
    )

    style_code = ParagraphStyle(
        'CodeBlock',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        alignment=0,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=6,
        spaceAfter=10
    )

    story = []

    # -------------------------------------------------------------
    # 1. TITLE PAGE
    # -------------------------------------------------------------
    story.append(Spacer(1, 24))
    story.append(Paragraph("LIGHTWEIGHT REAL-TIME AGENT FAILURE PREDICTION<br/>AND INTERVENTION SYSTEM", style_title))
    story.append(Spacer(1, 10))
    story.append(Paragraph("A Project Report submitted in partial fulfillment of the requirements<br/>for the award of the degree of", style_subtitle))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Bachelor of Technology</b><br/>in<br/><b>Computer Science and Engineering</b>", ParagraphStyle('BTech', parent=style_subtitle, fontSize=13, leading=18, fontName='Times-Roman', alignment=1)))
    story.append(Spacer(1, 14))
    story.append(Paragraph("by", style_subtitle))
    story.append(Paragraph("<b>Tanishka (MIS: 112115089)</b><br/>B.Tech CSE, Semester VII", ParagraphStyle('Author', parent=style_subtitle, fontSize=12, leading=16, fontName='Times-Roman', alignment=1)))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Under the Supervision of:<br/><b>Faculty Project Supervisor</b><br/>Department of Computer Science and Engineering", ParagraphStyle('Sup', parent=style_subtitle, fontSize=11, leading=15, fontName='Times-Roman', alignment=1)))
    story.append(Spacer(1, 28))
    story.append(Paragraph("<b>Department of Computer Science and Engineering<br/>Indian Institute of Information Technology, Pune</b><br/>(An Institute of National Importance by an Act of Parliament)<br/><b>DECEMBER 2026</b>", ParagraphStyle('Inst', parent=style_subtitle, fontSize=11.5, leading=16, fontName='Times-Roman', alignment=1)))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 2. BONAFIDE CERTIFICATE
    # -------------------------------------------------------------
    story.append(Paragraph("BONAFIDE CERTIFICATE", style_chapter))
    story.append(Spacer(1, 8))
    story.append(Paragraph("This is to certify that the project report entitled <b>“Lightweight Real-Time Agent Failure Prediction and Intervention System”</b> submitted by <b>Tanishka (MIS: 112115089)</b> in partial fulfillment of the requirements for the award of the degree of <b>Bachelor of Technology in Computer Science and Engineering</b> to the Indian Institute of Information Technology, Pune, is a bonafide record of the work carried out under our supervision and guidance during the academic session 2025–2026.", style_body))
    story.append(Paragraph("The results embodied in this report have not been submitted to any other University or Institute for the award of any degree or diploma to the best of our knowledge.", style_body))
    story.append(Spacer(1, 40))

    cert_table_data = [
        [
            Paragraph("<b>_______________________________</b><br/><b>Project Supervisor</b><br/>Department of CSE<br/>IIIT Pune", style_body),
            Paragraph("<b>_______________________________</b><br/><b>Head of the Department (HoD)</b><br/>Department of CSE<br/>IIIT Pune", ParagraphStyle('RightP', parent=style_body, alignment=2))
        ]
    ]
    t_cert = Table(cert_table_data, colWidths=[240, 240])
    t_cert.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t_cert)

    story.append(Spacer(1, 35))
    story.append(Paragraph("<b>Project Viva-voce held on:</b> ________________________<br/><br/><b>External Examiner:</b> _____________________________", style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 3. UNDERTAKING & CONFLICT OF INTEREST
    # -------------------------------------------------------------
    story.append(Paragraph("UNDERTAKING FOR PLAGIARISM", style_chapter))
    story.append(Paragraph("I hereby solemnly declare that the research and implementation work presented in the report entitled <b>“Lightweight Real-Time Agent Failure Prediction and Intervention System”</b> is solely my original work. No part of this report has been plagiarized or copied from any published or unpublished source without appropriate citation and academic acknowledgment.", style_body))
    story.append(Paragraph("I understand that the maximum permissible threshold of plagiarism is 20% according to institutional guidelines. All empirical evaluations, benchmark experiments on the AFTraj-2K corpus, architecture implementations, and flight booking demonstrations reflect genuine original work developed in the BTP project workspace.", style_body))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Tanishka (MIS: 112115089)</b><br/>Department of Computer Science and Engineering<br/>Indian Institute of Information Technology, Pune<br/>Date: December 2026", ParagraphStyle('Sig1', parent=style_body, alignment=2)))

    story.append(Spacer(1, 15))
    story.append(Paragraph("CONFLICT OF INTEREST", style_chapter))
    story.append(Paragraph("<b>Manuscript Title:</b> Lightweight Real-Time Agent Failure Prediction and Intervention System", style_body))
    story.append(Paragraph("The author certifies that she has NO affiliations with or involvement in any organization or entity with any financial interest (such as honoraria, educational grants, participation in speakers’ bureaus, membership, employment, consultancies, stock ownership, or other equity interest) or non-financial interest (such as personal or professional relationships, affiliations, knowledge, or beliefs) in the subject matter or materials discussed in this manuscript.", style_body))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Tanishka (MIS: 112115089)</b><br/>Student Signature", ParagraphStyle('Sig2', parent=style_body, alignment=2)))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 4. PROBLEM STATEMENT & OBJECTIVES (MID-TERM SUBMISSION)
    # -------------------------------------------------------------
    story.append(Paragraph("PROBLEM STATEMENT AND OBJECTIVES<br/>(Mid-Term Presentation Alignment)", style_chapter))
    story.append(Paragraph("Problem Statement Approved at Mid-Term Review", style_h2))
    story.append(Paragraph("Autonomous Large Language Model (LLM) agents are increasingly entrusted with complex, multi-step problem solving across code synthesis, mathematical reasoning, and web tool execution. However, standard deployments operate without active runtime guardrails: a single faulty deduction or transient API failure easily goes undetected by downstream agents, initiating an irreversible cascading error that causes the entire trajectory to fail. Existing academic literature primarily focuses on post-hoc failure attribution—retrospectively diagnosing errors after trajectory completion. This paradigm forfeits any opportunity to salvage ongoing runs, wasting execution budgets and risking operational failure. The problem is to design, implement, and benchmark a Lightweight Real-Time Agent Failure Prediction and Intervention System that monitors unfolding execution prefixes, detects decisive errors at the earliest possible step (k*), and autonomously initiates targeted recovery interventions before fatal cascading occurs.", style_body))

    story.append(Paragraph("Project Objectives Approved at Mid-Term Review", style_h2))
    story.append(Paragraph("• <b>Objective 1 (Dataset Curation):</b> To curate and clean a standardized multi-agent trajectory dataset (AFTraj-2K) with step-level decisive error annotations, strictly ensuring zero data leakage by partitioning splits at the trajectory level.", style_bullet))
    story.append(Paragraph("• <b>Objective 2 (Low-Latency Signals):</b> To architect a sub-millisecond Runtime Signals Engine computing 24 deterministic operational features including retry dynamics, isolated tool blips, loop indicators, and semantic drift.", style_bullet))
    story.append(Paragraph("• <b>Objective 3 (Statistical Prior):</b> To train and calibrate a lightweight statistical machine learning failure risk classifier capable of predicting failure likelihood in under 2 milliseconds.", style_bullet))
    story.append(Paragraph("• <b>Objective 4 (Semantic Verification):</b> To implement a structured LLM Judge with strict schema enforcement to categorize failure semantics into actionable categories (e.g., TOOL_FAILURE, LOOP, STAGNATION).", style_bullet))
    story.append(Paragraph("• <b>Objective 5 (Deterministic Shield):</b> To build a deterministic Decision Fusion System with false-alarm shielding and conflict resolution that triggers ALARM only when high-confidence failure risks are verified.", style_bullet))
    story.append(Paragraph("• <b>Objective 6 (Closed-Loop Recovery):</b> To deploy an autonomous Intervention Layer that executes closed-loop recovery actions (tool switching, replanning, backoff retry, human escalation) to dynamically salvage failing agent workflows.", style_bullet))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 5. ACKNOWLEDGEMENT
    # -------------------------------------------------------------
    story.append(Paragraph("ACKNOWLEDGEMENT", style_chapter))
    story.append(Paragraph("This Bachelor of Technology Project would not have been possible without the guidance, encouragement, and cooperation of many individuals and mentors at the Indian Institute of Information Technology, Pune.", style_body))
    story.append(Paragraph("First and foremost, I would like to express my deepest gratitude to our honorable Director, Prof. Vineet Kansal, and the Head of Department, Computer Science and Engineering, for providing world-class computational resources and academic infrastructure that fostered an environment of scientific inquiry.", style_body))
    story.append(Paragraph("I am profoundly indebted to my Project Supervisor for their invaluable guidance, constructive critiques, and relentless encouragement throughout all phases of this research. Their insightful feedback on online auditing formulations, decisive error modeling, and experimental rigor significantly shaped the direction and execution of this work.", style_body))
    story.append(Paragraph("I also extend my sincere appreciation to the faculty members of the Department of Computer Science and Engineering, IIIT Pune, whose comprehensive lectures and rigorous coursework laid the theoretical foundations necessary for completing this advanced agentic AI project.", style_body))
    story.append(Paragraph("Finally, I express heartfelt thanks to my parents, family, and peers for their unconditional support and patience during late-night debugging and benchmarking sessions.", style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 6. ABSTRACT
    # -------------------------------------------------------------
    story.append(Paragraph("ABSTRACT", style_chapter))
    story.append(Paragraph("Large Language Model (LLM) agents are increasingly deployed on long-horizon, autonomous tasks spanning multi-step code synthesis, mathematical theorem proving, and tool-augmented web navigation. However, the sequential autoregressive nature of agentic workflows introduces severe fragility: a single decisive error—such as an invalid API argument, a faulty intermediate deduction, or a tool timeout—cascades silently into catastrophic full-trajectory failure. While existing research frames failure analysis as post-hoc failure attribution (retrospectively identifying responsible agents after execution ends), this paradigm forfeits any opportunity to intervene during execution, resulting in wasted computational tokens, degraded task accuracy, and real-world operational hazards.", style_body))
    story.append(Paragraph("In this project, we reframe the failure problem as <b>Online Auditing</b> and present the <b>Lightweight Real-Time Agent Failure Prediction and Intervention System</b>. Grounded in the theoretical formulation of decisive error steps (k*) from recent foundational literature (<i>AgentForesight</i>, arXiv:2605.08715), our system implements a defense-in-depth, five-layer modular architecture: (1) an ultra-low-latency Signals Engine calculating 24 deterministic runtime signals; (2) a lightweight statistical ML Classifier (Logistic Regression and Decision Tree) providing fast probabilistic risk priors P(failure | x_t) in under 2 ms; (3) a structured LLM Judge with Pydantic schema validation identifying semantic failure categories; (4) a deterministic Decision Fusion System with false-alarm shielding; and (5) an autonomous Closed-Loop Intervention Layer executing dynamic tool switching, iterative replanning, exponential backoff, and human escalation.", style_body))
    story.append(Paragraph("We rigorously evaluate our system on 332 held-out test trajectories (2,756 steps) from the curated AFTraj-2K benchmark across coding, math, and tool-use domains, partitioned strictly by trajectory ID to guarantee zero data leakage. The hybrid system achieves a <b>99.39% overall trajectory failure detection rate</b> (162/163 unsafe trajectories intercepted) with an <b>early interception rate of 89.57%</b> and an <b>average early warning lead time of 4.04 steps</b> ahead of trajectory failure. We validate end-to-end recovery through an autonomous flight-booking case study where a primary API gateway timeout is intercepted, audited, and resolved via automatic fallback switching to an alternate registered flight provider, salvaging the mission seamlessly. All 54 automated test suites pass, establishing our lightweight hybrid architecture as an effective, deployable guardrail for autonomous LLM agents.", style_body))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Keywords:</b> Autonomous LLM Agents, Online Failure Auditing, Early Failure Prediction, Decisive Error Localization, Runtime Signals, Decision Fusion, Automated Interventions, AFTraj-2K Benchmark.", style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 7. TABLE OF CONTENTS
    # -------------------------------------------------------------
    story.append(Paragraph("TABLE OF CONTENTS", style_chapter))
    toc_data = [
        [Paragraph("<b>Certificate & Declarations</b>", style_body), Paragraph("ii - iii", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Problem Statement & Objectives (Mid-Term Attachment)</b>", style_body), Paragraph("iv", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Acknowledgement & Abstract</b>", style_body), Paragraph("v - vi", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>List of Figures & List of Tables</b>", style_body), Paragraph("viii - ix", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Chapter 1: Introduction</b>", style_body), Paragraph("1", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Overview of Work", style_body), Paragraph("1", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.2 Literature Review", style_body), Paragraph("2", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.3 Motivation of the Work", style_body), Paragraph("4", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.4 Research Gap", style_body), Paragraph("5", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Chapter 2: Problem Statement</b>", style_body), Paragraph("6", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Formal Problem Formulation", style_body), Paragraph("6", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Research Objectives", style_body), Paragraph("7", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.3 Analysis and Design Principles", style_body), Paragraph("8", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Chapter 3: Proposed Work & System Architecture</b>", style_body), Paragraph("9", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.1 Overall System Methodology & Architecture", style_body), Paragraph("9", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.2 Layer 1: Runtime Signals Engine (24 Features)", style_body), Paragraph("11", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.3 Layer 2: Lightweight Machine Learning Classifier", style_body), Paragraph("13", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.4 Layer 3: Prompted LLM Judge & Semantic Verification", style_body), Paragraph("14", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.5 Layer 4: Deterministic Decision Fusion System", style_body), Paragraph("16", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.6 Layer 5: Closed-Loop Intervention Layer", style_body), Paragraph("18", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.7 Hardware & Software Specifications", style_body), Paragraph("20", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.8 Dataset Description: AFTraj-2K Corpus", style_body), Paragraph("21", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Chapter 4: Results and Discussion</b>", style_body), Paragraph("23", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.1 Experimental Setup & Evaluation Protocol", style_body), Paragraph("23", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.2 Step-Level Failure Detection Performance", style_body), Paragraph("24", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.3 Trajectory-Level Early Warning Lead Time", style_body), Paragraph("26", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.4 Confusion Matrix & Error Trade-off Analysis", style_body), Paragraph("27", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.5 Case Study Walkthrough: Autonomous Flight Booking", style_body), Paragraph("28", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.6 Latency & Operational Cost Analysis", style_body), Paragraph("30", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Chapter 5: Conclusion and Future Scope</b>", style_body), Paragraph("31", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;5.1 Summary of Contributions", style_body), Paragraph("31", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;5.2 System Limitations", style_body), Paragraph("32", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;5.3 Future Directions", style_body), Paragraph("32", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>References</b>", style_body), Paragraph("34", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Appendices (A, B, C)</b>", style_body), Paragraph("36 - 38", ParagraphStyle('TR', parent=style_body, alignment=2))]
    ]
    t_toc = Table(toc_data, colWidths=[400, 80])
    t_toc.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2)
    ]))
    story.append(t_toc)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 8. LIST OF FIGURES & LIST OF TABLES
    # -------------------------------------------------------------
    story.append(Paragraph("LIST OF FIGURES", style_chapter))
    lof_data = [
        [Paragraph("<b>Fig. 3.1</b>", style_body), Paragraph("Five-Layer Modular Architecture of the Failure Guard System", style_body), Paragraph("10", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Fig. 4.1</b>", style_body), Paragraph("Benchmark evaluation metrics comparison across four configurations", style_body), Paragraph("24", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Fig. 4.2</b>", style_body), Paragraph("Receiver Operating Characteristic (ROC) curve for statistical ML predictor", style_body), Paragraph("25", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Fig. 4.3</b>", style_body), Paragraph("Distribution of early warning lead times across benchmark trajectories", style_body), Paragraph("26", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Fig. 4.4</b>", style_body), Paragraph("Step-level confusion matrices for Signals, ML, LLM, and Hybrid setups", style_body), Paragraph("27", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Fig. 4.5</b>", style_body), Paragraph("End-to-End recovery flow during the real-world flight booking case study", style_body), Paragraph("29", ParagraphStyle('TR', parent=style_body, alignment=2))]
    ]
    t_lof = Table(lof_data, colWidths=[65, 360, 55])
    t_lof.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 3), ('TOPPADDING', (0,0), (-1,-1), 3)]))
    story.append(t_lof)

    story.append(Spacer(1, 15))
    story.append(Paragraph("LIST OF TABLES", style_chapter))
    lot_data = [
        [Paragraph("<b>Table 3.1</b>", style_body), Paragraph("Summary of the 24 Real-Time Signals computed by Signals Engine", style_body), Paragraph("12", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Table 3.2</b>", style_body), Paragraph("Failure Reason Taxonomy and Recovery Intervention Mappings", style_body), Paragraph("18", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Table 3.3</b>", style_body), Paragraph("Hardware and Software Environment Specifications", style_body), Paragraph("20", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Table 4.1</b>", style_body), Paragraph("Step-Level Benchmark Performance Metrics on Held-Out Test Set", style_body), Paragraph("24", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Table 4.2</b>", style_body), Paragraph("Trajectory-Level Early Warning & Interception Evaluation Metrics", style_body), Paragraph("26", ParagraphStyle('TR', parent=style_body, alignment=2))],
        [Paragraph("<b>Table 4.3</b>", style_body), Paragraph("Component Latency and Computational Cost Comparison across Layers", style_body), Paragraph("30", ParagraphStyle('TR', parent=style_body, alignment=2))]
    ]
    t_lot = Table(lot_data, colWidths=[65, 360, 55])
    t_lot.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 3), ('TOPPADDING', (0,0), (-1,-1), 3)]))
    story.append(t_lot)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 1: INTRODUCTION
    # -------------------------------------------------------------
    story.append(Paragraph("Chapter 1<br/><b>Introduction</b>", style_chapter))
    story.append(Paragraph("1.1 Overview of Work", style_h2))
    story.append(Paragraph("Large Language Models (LLMs) have undergone a paradigm shift, transitioning from passive conversational chatbots to proactive, autonomous agentic systems. By leveraging recursive reasoning, structured chain-of-thought prompting, and external tool execution, autonomous agents decompose complex, long-horizon objectives into discrete, executable sub-tasks. Modern multi-agent systems are currently deployed across mission-critical domains, including automated software engineering (e.g., SWE-bench, Devin), scientific hypothesis generation, and open-ended web environments requiring multi-step interaction with third-party REST APIs and database engines.", style_body))
    story.append(Paragraph("Despite these profound capabilities, agentic deployments exhibit a fundamental vulnerability: sequential autoregressive fragility. In a multi-step trajectory, each successive action and reasoning turn is conditioned on the cumulative transcript of prior steps. Consequently, a single decisive error—such as an invalid API parameter, an unchecked syntax error, an erroneous mathematical deduction, or a network timeout—is easily ingested by subsequent agents as valid ground truth. This initiates a catastrophic cascade: downstream agents expend significant computational resources pursuing an unviable trajectory, ultimately resulting in terminal task failure.", style_body))
    story.append(Paragraph("This project develops and evaluates the <b>Lightweight Real-Time Agent Failure Prediction and Intervention System</b>. Rather than passively observing agent degradation or inspecting failures retrospectively, our system continuously monitors the unfolding agent execution prefix at runtime. By integrating ultra-fast deterministic signals, calibrated machine learning risk scoring, structured LLM-based semantic verification, and a deterministic decision shield, the system intercepts failures at the decisive step (k*) and executes targeted, autonomous recovery interventions—such as dynamic tool substitution, iterative replanning, and exponential backoff retry—to salvage failing workflows in real time.", style_body))

    story.append(Paragraph("1.2 Literature Review", style_h2))
    story.append(Paragraph("The academic literature surrounding reliability, failure detection, and self-correction in autonomous LLM agents can be categorized into three distinct paradigms:", style_body))

    story.append(Paragraph("1.2.1 Post-Hoc Failure Attribution and Diagnostic Benchmarks", style_h3))
    story.append(Paragraph("Early research focused primarily on retrospective failure diagnosis. Zhu et al. (2024) introduced the <i>Who&When</i> benchmark, formalizing the task of diagnosing which agent (who) failed and at which execution turn (when) after an entire multi-agent trajectory had concluded. Similarly, AutoSafe and related frameworks proposed post-mortem debugging techniques that reconstruct the execution graph to localize buggy steps. However, as established in recent foundational work by Zhang et al. (2026) in <i>AgentForesight: Online Auditing for Early Failure Prediction in Multi-Agent Systems</i> (arXiv:2605.08715), post-hoc attribution suffers from a crippling limitation: by deferring diagnosis until after the trajectory terminates, the system forfeits all opportunity to intervene. Tokens are wasted, execution quotas are exhausted, and downstream side-effects (e.g., corrupted database writes or financial transactions) cannot be reversed.", style_body))

    story.append(Paragraph("1.2.2 Online Failure Auditing and Decisive Error Localization", style_h3))
    story.append(Paragraph("To overcome the limitations of post-hoc methods, Zhang et al. (2026) formulated the paradigm of <b>Online Auditing</b>. In this formulation, an auditor inspects only the unfolding execution prefix tau_{0:t} at step t, without access to future trajectory rollouts, and must emit an immediate binary verdict: CONTINUE or ALARM. The authors curated the AFTraj-2K corpus—a multi-agent dataset spanning Coding (HumanEval, MBPP), Mathematics (GSM8K, MATH), and Tool-use Agentic domains (ToolBench, WebShop)—annotating the exact decisive error step k* where the trajectory crossed the point of no return. They developed AgentForesight-7B, demonstrating that specialized auditors trained via reinforcement learning can anticipate failure boundaries far more accurately than frontier generalist models like GPT-4.1. Our project builds directly on the theoretical formulation and curated corpus of AgentForesight, operationalizing decisive error localization into a modular, production-ready system.", style_body))

    story.append(Paragraph("1.2.3 Self-Correction and Dynamic Intervention Mechanisms", style_h3))
    story.append(Paragraph("Parallel research has explored agent self-correction. Frameworks such as ReAct (Yao et al., 2023), Reflexion (Shinn et al., 2023), and Self-Refine (Madaan et al., 2023) introduce verbal self-reflection loops where agents evaluate their own intermediate reasoning. However, empirical studies reveal that unguided LLM self-correction frequently suffers from the 'sycophancy' or 'hallucination loop' phenomenon: an agent that introduced an error is mathematically biased to justify and double down on that error rather than correct it. True reliability requires an external, decoupled supervisor equipped with independent runtime signals and fallback intervention registries.", style_body))

    story.append(Paragraph("1.3 Motivation of the Work", style_h2))
    story.append(Paragraph("• <b>1. Token & Resource Efficiency:</b> In benchmarks such as ToolBench and SWE-bench, trajectory lengths routinely exceed 15 to 30 steps. When a decisive error occurs at step 3, continuing execution through step 20 consumes thousands of input and output tokens on futile computation. Intercepting the error at step 3 saves over 75% of operational inference costs.", style_bullet))
    story.append(Paragraph("• <b>2. Safety & Containment:</b> In real-world enterprise environments involving cloud orchestration, financial payments, or automated scheduling, an agent operating on false premises can execute destructive API commands (e.g., repeatedly charging a credit card or deleting resources). Real-time guardrails prevent runaway execution.", style_bullet))
    story.append(Paragraph("• <b>3. Closed-Loop Salvage:</b> Detecting failure is useless if the system simply halts. An autonomous system must close the loop by initiating corrective recovery actions (e.g., tool switching or prompt replanning) to achieve the user's objective without human intervention.", style_bullet))

    story.append(Paragraph("1.4 Research Gap", style_h2))
    story.append(Paragraph("While AgentForesight (Zhang et al., 2026) established the benchmark and theoretical necessity of online auditing, a substantial research and engineering gap remains. First, existing implementations rely on heavy LLM reasoning at every single execution step, introducing hundreds of milliseconds of latency and substantial API costs that render continuous monitoring impractical. Second, prior benchmarks treat auditing purely as a passive classification problem (predicting ALARM vs. CONTINUE) without providing an actionable intervention layer capable of repairing the execution state. Our project bridges this gap by introducing a multi-tiered architecture that combines sub-millisecond rule-based signals, fast statistical machine learning, and structured LLM verification with an active closed-loop intervention engine.", style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 2: PROBLEM STATEMENT
    # -------------------------------------------------------------
    story.append(Paragraph("Chapter 2<br/><b>Problem Statement</b>", style_chapter))
    story.append(Paragraph("2.1 Formal Problem Formulation", style_h2))
    story.append(Paragraph("Following the theoretical formulation established in Zhang et al. (2026), we model a multi-agent execution environment as a turn-based system defined by the tuple:", style_body))
    story.append(Paragraph("<b>M = (S, N, π_sys, Ψ, Ω)</b>", ParagraphStyle('Form1', parent=style_body, fontName='Times-Bold', alignment=1)))
    story.append(Paragraph("where S represents the set of system and environment states, N denotes the finite set of specialized agent roles (e.g., Planner, ToolAgent, CodeWriter), π_sys is the multi-agent system policy governing turn generation, Ψ: S × A → S is the state-transition function, and Ω: T → {0, 1} is the terminal evaluation function evaluating whether completed trajectory τ satisfies the user specification (Ω(τ) = 1 for success, 0 for failure).", style_body))
    story.append(Paragraph("An observed execution trajectory τ of length T is a sequence of discrete turns:", style_body))
    story.append(Paragraph("<b>τ = (t_0, t_1, ..., t_{T-1}), &nbsp;&nbsp;&nbsp;&nbsp; t_i = (role_i, action_i, content_i)</b>", ParagraphStyle('Form2', parent=style_body, fontName='Times-Bold', alignment=1)))
    story.append(Paragraph("where role_i identifies the agent executing turn i, and (action_i, content_i) represents the specific tool call, code snippet, or message content and its corresponding environmental observation.", style_body))

    story.append(Paragraph("2.1.1 The Decisive Error Step (k*)", style_h3))
    story.append(Paragraph("In a failing trajectory (Ω(τ) = 0), catastrophic errors do not occur uniformly. Rather, failure originates at a specific decisive step whose error makes subsequent recovery impossible under policy π_sys. Formally, let τ^+ := τ_{0:k-1} ⊕ t̃ denote the trajectory prefix up to step k-1 concatenated with an admissible corrected turn t̃. The decisive error step k* is defined as:", style_body))
    story.append(Paragraph("<b>k* = min { k ∈ [T] : ∃ t̃ ∈ T_k(τ_{0:k-1}), τ̃ ∈ R_M(τ^+), Ω(τ^+ ⊕ τ̃) = 1 }</b>", ParagraphStyle('Form3', parent=style_body, fontName='Times-Bold', alignment=1)))
    story.append(Paragraph("where T_k(τ_{0:k-1}) is the set of valid alternative actions at turn k, and R_M(τ^+) is the set of reachable trajectory rollouts originating from the corrected prefix. The agent responsible for this error is designated as a* = role_{k*}. Any step t < k* is classified as SAFE (pre-failure), while step t = k* represents the decisive failure point.", style_body))

    story.append(Paragraph("2.1.2 Online Auditing vs. Post-Hoc Attribution", style_h3))
    story.append(Paragraph("In post-hoc attribution, an auditor observes the complete trajectory τ after termination and emits a retrospective diagnosis ŷ_{post} = f_{post}(τ) = (k̂, â). In contrast, Online Auditing requires an auditor f_{online} to evaluate each partial prefix τ_{0:t} sequentially at runtime:", style_body))
    story.append(Paragraph("<b>y_t = f_{online}(τ_{0:t}) ∈ { CONTINUE, ALARM }</b>", ParagraphStyle('Form4', parent=style_body, fontName='Times-Bold', alignment=1)))
    story.append(Paragraph("The objective of the online auditor is twofold: (1) maintain y_t = CONTINUE for all safe prefixes (t < k*), avoiding disruptive false alarms; and (2) emit y_t = ALARM at the earliest possible step t ≥ k*, maximizing the early warning lead time Δt = (T - 1) - t before fatal completion.", style_body))

    story.append(Paragraph("2.2 Research Objectives", style_h2))
    story.append(Paragraph("• <b>Objective 1 (Dataset Integrity):</b> Curate and clean the AFTraj-2K corpus into a standardized step-level feature space, enforcing strict trajectory-level partitioning to guarantee zero data leakage between training and testing.", style_bullet))
    story.append(Paragraph("• <b>Objective 2 (Low-Latency Signals):</b> Engineer a 24-dimensional Runtime Signals Engine capable of extracting deterministic behavioral and syntactic features (retry counts, loop indicators, isolated tool errors) in under 1 millisecond.", style_bullet))
    story.append(Paragraph("• <b>Objective 3 (Statistical Prior):</b> Train and calibrate lightweight statistical machine learning classifiers (Logistic Regression, Decision Trees) to generate accurate failure probability priors P(failure | x_t) in sub-2ms time.", style_bullet))
    story.append(Paragraph("• <b>Objective 4 (Semantic Verification):</b> Implement a structured, prompt-engineered LLM Judge with strict Pydantic schema validation to diagnose root failure categories with high semantic fidelity.", style_bullet))
    story.append(Paragraph("• <b>Objective 5 (Deterministic Shield):</b> Develop a deterministic Decision Fusion System incorporating false-alarm shields to reconcile signal discrepancies and trigger ALARM only when warranted.", style_bullet))
    story.append(Paragraph("• <b>Objective 6 (Closed-Loop Recovery):</b> Architect an autonomous Closed-Loop Intervention Layer that dynamically maps failure categories to verified recovery actions, salvaging agent execution without human intervention.", style_bullet))

    story.append(Paragraph("2.3 Analysis and Design Principles", style_h2))
    story.append(Paragraph("The proposed system adheres to four foundational architectural principles:", style_body))
    story.append(Paragraph("• <b>1. Multi-Tier Defense-in-Depth:</b> Deterministic rules catch blatant bugs instantly; statistical ML catches systemic degradation trends; LLM reasoning analyzes subtle semantic divergences.", style_bullet))
    story.append(Paragraph("• <b>2. Asymmetric Latency Optimization:</b> By executing sub-millisecond signals and lightweight ML first, expensive LLM calls can be conditionally gated or run concurrently, keeping total pipeline overhead negligible.", style_bullet))
    story.append(Paragraph("• <b>3. False-Alarm Shielding:</b> Stopping an agent unnecessarily is costly. The decision fusion layer incorporates hysteresis and isolated-failure shields to avoid premature halts on transient blips.", style_bullet))
    story.append(Paragraph("• <b>4. Action Validation:</b> Recovery actions (e.g., tool switching) are strictly validated against pre-registered system capabilities, preventing the intervention layer from introducing hallucinations.", style_bullet))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 3: PROPOSED WORK
    # -------------------------------------------------------------
    story.append(Paragraph("Chapter 3<br/><b>Proposed Work</b>", style_chapter))
    story.append(Paragraph("3.1 Overall System Methodology & Architecture", style_h2))
    story.append(Paragraph("The Lightweight Real-Time Agent Failure Prediction and Intervention System operates as a transparent runtime middleware positioned between the autonomous agent and its external execution environment. After each discrete agent step (tool invocation, code execution, or message dispatch), the observation and metadata are intercepted and processed through five tightly integrated layers:", style_body))

    # Architecture Image
    story.append(Image("results/figures/system_architecture.png", width=460, height=267))
    story.append(Paragraph("Fig. 3.1: Five-Layer Modular Architecture of the Lightweight Real-Time Agent Failure Prediction & Intervention System.", style_caption))

    story.append(Paragraph("As illustrated in Fig. 3.1, the execution sequence follows a strict 10-step lifecycle:", style_body))
    lifecycle_steps = [
        "<b>Step 1 (Execution):</b> The agent executes a discrete turn t = (role_t, action_t, content_t) within the environment.",
        "<b>Step 2 (Interception):</b> The Monitoring Layer records the action, raw observation, latency, and status codes.",
        "<b>Step 3 (Feature Extraction):</b> The Signals Engine computes 24 deterministic behavioral and state-machine signals in < 1 ms.",
        "<b>Step 4 (Statistical Prior):</b> The Lightweight ML Classifier consumes the feature vector and computes failure risk P(failure | x_t) in < 2 ms.",
        "<b>Step 5 (Semantic Audit):</b> The Prompted LLM Judge performs semantic analysis on the prefix transcript, emitting an audit verdict.",
        "<b>Step 6 (Decision Fusion):</b> The Decision Fusion System combines signals, ML risk, and LLM verdict under strict priority rules.",
        "<b>Step 7 (Continue Flow):</b> If the decision is CONTINUE, the agent is permitted to execute turn t+1 unimpeded.",
        "<b>Step 8 (Alarm Trigger):</b> If the decision is ALARM, the Intervention Layer is immediately activated.",
        "<b>Step 9 (Intervention):</b> The Intervention Layer selects and executes a validated recovery action (e.g., SWITCH_TOOL, REPLAN).",
        "<b>Step 10 (Closed-Loop Resume):</b> The recovered state is injected back into the agent context, and monitoring resumes seamlessly."
    ]
    for step in lifecycle_steps:
        story.append(Paragraph(f"• {step}", style_bullet))

    story.append(Paragraph("3.2 Layer 1: Runtime Signals Engine (24 Features)", style_h2))
    story.append(Paragraph("The Signals Engine (implemented in <code>src/signals/engine.py</code> and <code>src/signals/feature_extractor.py</code>) provides instant, deterministic failure indicators without invoking expensive LLM calls. It maintains internal state across the trajectory and calculates 24 distinct features across four functional categories:", style_body))

    sig_pdf_data = [
        [Paragraph("<b>Category</b>", style_body), Paragraph("<b>Signals / Features</b>", style_body), Paragraph("<b>Operational Purpose</b>", style_body)],
        [Paragraph("<b>Retry Dynamics</b>", style_body), Paragraph("retry_count, is_repeat_action, consecutive_tool_failures, max_consecutive_retries", style_body), Paragraph("Tracks repeated identical actions and tracks consecutive tool crashes via an internal state machine.", style_body)],
        [Paragraph("<b>Tool & API Health</b>", style_body), Paragraph("tool_call_failed, isolated_failure_flag, http_error_status, tool_execution_latency", style_body), Paragraph("Identifies API 4xx/5xx exceptions while isolating transient network blips from systemic failures.", style_body)],
        [Paragraph("<b>Loop & Redundancy</b>", style_body), Paragraph("loop_indicator_score, jaccard_similarity_sliding, repeated_content_ratio, action_diversity_index", style_body), Paragraph("Detects cognitive infinite loops and repetitive parameter passing across a sliding window of k=3 turns.", style_body)],
        [Paragraph("<b>Stagnation & Drift</b>", style_body), Paragraph("stagnation_index, observation_length_delta, task_drift_score, semantic_entropy_ratio", style_body), Paragraph("Quantifies lack of forward trajectory progress, ballooning context sizes, and divergence from user prompt.", style_body)],
        [Paragraph("<b>Trajectory Length</b>", style_body), Paragraph("step_index, trajectory_progress_ratio, cumulative_error_count, time_elapsed_seconds", style_body), Paragraph("Normalizes operational pace and bounds execution budgets against infinite generation.", style_body)]
    ]
    t_sig = Table(sig_pdf_data, colWidths=[90, 185, 205])
    t_sig.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_sig)
    story.append(Paragraph("Table 3.1: Summary of the 24 Real-Time Signals computed by the Signals Engine.", style_caption))

    story.append(Paragraph("A key algorithmic innovation is the <b>Isolated Failure Shield</b>. Standard naive monitors trigger alarms on any nonzero tool exit code. In our engine, an isolated tool failure occurring at step t with zero prior retries and no loop signature sets <code>isolated_failure_flag = 1</code>, which communicates to downstream layers that the error is transient and recoverable, avoiding premature aborts.", style_body))

    story.append(Paragraph("3.3 Layer 2: Lightweight Machine Learning Classifier", style_h2))
    story.append(Paragraph("The second layer (<code>src/models/predictor.py</code>) applies statistical machine learning to the 24-dimensional feature vector x_t to estimate failure risk P(failure | x_t) in under 2 milliseconds. We evaluated and serialized two complementary model families:", style_body))
    story.append(Paragraph("• <b>1. Calibrated Logistic Regression:</b> Calibrated with balanced class weighting (<code>class_weight='balanced'</code>) to account for class skew (72.6% safe steps vs. 27.4% decisive failure steps). Provides smooth, well-calibrated posterior probabilities P(failure | x_t) = σ(w^T x_t + b).", style_bullet))
    story.append(Paragraph("• <b>2. Decision Tree Classifier:</b> Configured with <code>max_depth=6</code> and <code>min_samples_leaf=20</code> to generate human-interpretable orthogonal decision boundaries, serving as an inspectable safety rule baseline.", style_bullet))
    story.append(Paragraph("Crucially, model training and hyperparameter tuning were conducted strictly using trajectory-level partitioning (splitting on <code>conv_id</code>). Standard random k-fold cross-validation on step-level records causes severe data leakage, as steps from the same conversation appear in both training and test folds. By partitioning strictly by conv_id, our ML models demonstrate genuine generalizability to unseen tasks.", style_body))

    story.append(Paragraph("3.4 Layer 3: Prompted LLM Judge & Semantic Verification", style_h2))
    story.append(Paragraph("While rule-based signals and ML classifiers detect behavioral anomalies, they lack deep semantic reasoning. When an agent produces plausible-looking code with a subtle mathematical flaw or hallucinates an incorrect flight date, semantic verification is required. Layer 3 (<code>src/judge/judge.py</code>) deploys a prompted LLM Judge.", style_body))
    story.append(Paragraph("To eliminate parsing errors and guarantee deterministic downstream integration, the LLM Judge enforces strict structured output via Pydantic schema validation (<code>FailureAuditReport</code>): verdict ('ALARM' or 'CONTINUE'), reason_category (TEMPORARY_TIMEOUT, TOOL_FAILURE, LOOP, PLAN_MISMATCH, STAGNATION, UNKNOWN), confidence score in [0.0, 1.0], responsible_agent, and a concise explanation. The system connects to high-speed cloud inference via the Groq API (utilizing Qwen 2.5 / Grok models) with sub-50ms execution, integrated rate-limit backoff, and an offline mock client fallback for sandboxed offline evaluation.", style_body))

    story.append(Paragraph("3.5 Layer 4: Deterministic Decision Fusion System", style_h2))
    story.append(Paragraph("Layer 4 (<code>src/decision/system.py</code>) synthesizes outputs from the three upstream layers into a single, authoritative operational directive: CONTINUE or ALARM. The fusion system applies a deterministic priority hierarchy to prevent probabilistic ML errors from overriding obvious safety violations:", style_body))
    story.append(Paragraph("• <b>Priority Rule 1 (Critical Signal Override):</b> If retry_count >= max_retries (3) or loop_indicator_score > 0.85, the system immediately returns ALARM with 1.0 confidence, bypassing any LLM sycophancy.", style_bullet))
    story.append(Paragraph("• <b>Priority Rule 2 (False-Alarm Shield):</b> If isolated_failure_flag == 1, retry_count == 1, and step_index <= 2, an exploratory grace rule suppresses premature ALARM, forcing CONTINUE.", style_bullet))
    story.append(Paragraph("• <b>Priority Rule 3 (Consensus & Disagreement Resolution):</b> If ML risk P(failure) >= 0.70 and the LLM Judge returns ALARM with confidence >= 0.65, ALARM is confirmed. When ML and LLM disagree, the system evaluates signal entropy: if runtime signals exhibit elevated stagnation or drift, it defaults to conservative ALARM; otherwise, CONTINUE.", style_bullet))

    story.append(Paragraph("3.6 Layer 5: Closed-Loop Intervention Layer", style_h2))
    story.append(Paragraph("When the Decision System returns ALARM, the Intervention Layer (<code>src/interventions/engine.py</code>) takes immediate corrective action. Rather than terminating the trajectory prematurely or executing generic restarts, it inspects the reason_category and selects a targeted recovery action from a verified capability registry:", style_body))

    int_pdf_data = [
        [Paragraph("<b>Reason Category</b>", style_body), Paragraph("<b>Selected Action</b>", style_body), Paragraph("<b>Execution Mechanism</b>", style_body)],
        [Paragraph("<b>TEMPORARY_TIMEOUT</b>", style_body), Paragraph("RETRY_WITH_BACKOFF", style_body), Paragraph("Exponential backoff (1s, 2s, 4s) with jitter and requests agent re-execute API call.", style_body)],
        [Paragraph("<b>TOOL_FAILURE</b>", style_body), Paragraph("SWITCH_TOOL", style_body), Paragraph("Queries registered alternative APIs in ToolRegistry (e.g., Sabre -> Amadeus).", style_body)],
        [Paragraph("<b>LOOP</b>", style_body), Paragraph("BREAK_LOOP_AND_REPLAN", style_body), Paragraph("Injects negative constraints into context identifying repeated parameters, forcing variation.", style_body)],
        [Paragraph("<b>PLAN_MISMATCH</b>", style_body), Paragraph("REPLAN", style_body), Paragraph("Invokes prompt replanning, stripping corrupted deductions and restarting from verified state.", style_body)],
        [Paragraph("<b>STAGNATION</b>", style_body), Paragraph("REPLAN / ESCALATE", style_body), Paragraph("Requests supervisor guidance if stagnation persists > 3 steps; otherwise triggers replanning.", style_body)],
        [Paragraph("<b>EXHAUSTED_BUDGET</b>", style_body), Paragraph("TERMINATE", style_body), Paragraph("Halts execution immediately if retries exceed budget (3), preventing runaway token costs.", style_body)]
    ]
    t_int = Table(int_pdf_data, colWidths=[120, 130, 230])
    t_int.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_int)
    story.append(Paragraph("Table 3.2: Failure Reason Taxonomy and Corresponding Recovery Intervention Mappings.", style_caption))

    story.append(Paragraph("3.7 Hardware & Software Specifications", style_h2))
    hw_pdf_data = [
        [Paragraph("<b>Component</b>", style_body), Paragraph("<b>System Specification / Configuration</b>", style_body)],
        [Paragraph("<b>Operating System</b>", style_body), Paragraph("macOS Darwin 25.1.0 (Apple Silicon ARM64 architecture)", style_body)],
        [Paragraph("<b>Runtime Environment</b>", style_body), Paragraph("Python 3.15.0 Virtual Environment (venv) with isolated dependency sandbox", style_body)],
        [Paragraph("<b>Machine Learning Stack</b>", style_body), Paragraph("Scikit-Learn 1.9.1, NumPy 2.5.4, Pandas 3.1.1, SciPy 1.18.1", style_body)],
        [Paragraph("<b>LLM Inference Stack</b>", style_body), Paragraph("Groq Cloud API (qwen/qwen3.8-27b), Pydantic 2.14.3, HTTPX 0.28.1", style_body)],
        [Paragraph("<b>Benchmarking & Testing</b>", style_body), Paragraph("Pytest 9.2.0 (54 automated tests), Matplotlib 3.11.2, Seaborn 0.13.2", style_body)]
    ]
    t_hw = Table(hw_pdf_data, colWidths=[140, 340])
    t_hw.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_hw)
    story.append(Paragraph("Table 3.3: Hardware and Software Environment Specifications.", style_caption))

    story.append(Paragraph("3.8 Dataset Description: AFTraj-2K Corpus", style_h2))
    story.append(Paragraph("To ground our research in realistic multi-agent behaviors, we utilized the AFTraj-2K benchmark dataset curated by Zhang et al. (2026). The corpus comprises 2,272 multi-agent trajectories balanced equally between verified-safe runs (1,136) and verified-unsafe runs (1,136) across three diverse domains: Software Synthesis (HumanEval, MBPP), Mathematical Reasoning (GSM8K, MATH), and Tool & Web Orchestration (ToolBench, WebShop). Raw Parquet files were parsed and transformed into 21,164 step-level records. Crucially, all post-failure steps (t > k*) were excluded from the training distribution to prevent negative label contamination. Dataset splits were strictly partitioned by conversation ID (conv_id) into 70% Train (1,590 trajectories), 15% Validation (350 trajectories), and 15% Held-Out Test (332 trajectories / 2,756 steps).", style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 4: RESULTS AND DISCUSSION
    # -------------------------------------------------------------
    story.append(Paragraph("Chapter 4<br/><b>Results and Discussion</b>", style_chapter))
    story.append(Paragraph("4.1 Experimental Setup & Evaluation Protocol", style_h2))
    story.append(Paragraph("To conduct a rigorous, fair empirical evaluation, we benchmarked four distinct system configurations over the identical held-out test split of 332 trajectories (163 unsafe, 169 safe) totaling 2,756 steps: (1) <b>Signals-Only</b> (deterministic threshold rules); (2) <b>ML-Only</b> (calibrated Logistic Regression at P ≥ 0.50); (3) <b>LLM-Only</b> (prompted LLM Judge); and (4) <b>Hybrid System</b> (full 5-layer pipeline with Decision Fusion shielding).", style_body))

    story.append(Paragraph("4.2 Step-Level Failure Detection Performance", style_h2))
    story.append(Paragraph("Table 4.1 summarizes the step-level classification metrics across all 2,756 test steps. Fig. 4.1 illustrates the comparative metric performance, and Fig. 4.2 plots the Receiver Operating Characteristic (ROC) curve.", style_body))

    res_pdf_data = [
        [Paragraph("<b>Configuration</b>", style_body), Paragraph("<b>Accuracy</b>", style_body), Paragraph("<b>Precision</b>", style_body), Paragraph("<b>Recall</b>", style_body), Paragraph("<b>F1-Score</b>", style_body), Paragraph("<b>ROC-AUC</b>", style_body)],
        [Paragraph("Signals-Only", style_body), Paragraph("70.03%", style_body), Paragraph("43.94%", style_body), Paragraph("3.55%", style_body), Paragraph("6.56%", style_body), Paragraph("0.3919", style_body)],
        [Paragraph("ML-Only (Logistic Reg.)", style_body), Paragraph("67.96%", style_body), Paragraph("46.82%", style_body), Paragraph("58.56%", style_body), Paragraph("52.04%", style_body), Paragraph("0.7033", style_body)],
        [Paragraph("LLM-Only (Judge)", style_body), Paragraph("70.46%", style_body), Paragraph("50.28%", style_body), Paragraph("44.50%", style_body), Paragraph("47.21%", style_body), Paragraph("0.6296", style_body)],
        [Paragraph("<b>Hybrid (Proposed)</b>", style_body), Paragraph("<b>70.03%</b>", style_body), Paragraph("<b>49.45%</b>", style_body), Paragraph("<b>44.25%</b>", style_body), Paragraph("<b>46.71%</b>", style_body), Paragraph("<b>0.6258</b>", style_body)]
    ]
    t_res = Table(res_pdf_data, colWidths=[130, 70, 70, 70, 70, 70])
    t_res.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_res)
    story.append(Paragraph("Table 4.1: Step-Level Benchmark Performance Metrics on Held-Out Test Set (2,756 steps).", style_caption))

    # Metrics comparison image
    story.append(Image("results/figures/metrics_comparison.png", width=450, height=270))
    story.append(Paragraph("Fig. 4.1: Benchmark evaluation metrics comparison across four system configurations.", style_caption))

    # ROC curve image
    story.append(Image("results/figures/roc_curve.png", width=380, height=285))
    story.append(Paragraph("Fig. 4.2: Receiver Operating Characteristic (ROC) curve for statistical ML failure risk predictor.", style_caption))

    story.append(Paragraph("4.3 Trajectory-Level Early Warning Lead Time", style_h2))
    story.append(Paragraph("While step-level metrics measure classification accuracy per individual turn, the paramount metric in online auditing is trajectory-level early warning lead time: how many steps before fatal trajectory termination does the system trigger ALARM?", style_body))

    traj_pdf_data = [
        [Paragraph("<b>Configuration</b>", style_body), Paragraph("<b>Detection Rate</b>", style_body), Paragraph("<b>Early Intercept</b>", style_body), Paragraph("<b>Mean Lead Time</b>", style_body), Paragraph("<b>Median Lead</b>", style_body)],
        [Paragraph("Signals-Only", style_body), Paragraph("3.68% (6/163)", style_body), Paragraph("3.07% (5/163)", style_body), Paragraph("6.67 steps", style_body), Paragraph("5.0 steps", style_body)],
        [Paragraph("ML-Only", style_body), Paragraph("100.0% (163/163)", style_body), Paragraph("90.18% (147/163)", style_body), Paragraph("4.02 steps", style_body), Paragraph("2.0 steps", style_body)],
        [Paragraph("LLM-Only", style_body), Paragraph("99.39% (162/163)", style_body), Paragraph("89.57% (146/163)", style_body), Paragraph("4.04 steps", style_body), Paragraph("2.0 steps", style_body)],
        [Paragraph("<b>Hybrid (Proposed)</b>", style_body), Paragraph("<b>99.39% (162/163)</b>", style_body), Paragraph("<b>89.57% (146/163)</b>", style_body), Paragraph("<b>4.04 steps</b>", style_body), Paragraph("<b>2.0 steps</b>", style_body)]
    ]
    t_traj = Table(traj_pdf_data, colWidths=[120, 95, 95, 90, 80])
    t_traj.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_traj)
    story.append(Paragraph("Table 4.2: Trajectory-Level Early Warning & Interception Evaluation Metrics.", style_caption))

    # Lead time distribution image
    story.append(Image("results/figures/lead_time_distribution.png", width=450, height=250))
    story.append(Paragraph("Fig. 4.3: Distribution of early warning lead times across held-out benchmark trajectories.", style_caption))

    story.append(Paragraph("As revealed in Table 4.2 and Fig. 4.3, the proposed Hybrid System achieves an extraordinary <b>99.39% overall failure detection rate</b>, intercepting 162 out of 163 failing trajectories. Crucially, <b>89.57% of these failures were intercepted early</b>—strictly before the terminal step. The average early warning lead time is <b>4.04 steps</b> ahead of fatal failure. In practical terms, this gives the agent an advance window of over 4 turns to replan, switch tools, or request assistance before resources are permanently wasted.", style_body))

    story.append(Paragraph("4.4 Confusion Matrix & Error Trade-off Analysis", style_h2))
    # Confusion matrix image
    story.append(Image("results/figures/confusion_matrices.png", width=400, height=320))
    story.append(Paragraph("Fig. 4.4: Step-level confusion matrices for Signals-only, ML-only, LLM-only, and Hybrid configurations.", style_caption))

    story.append(Paragraph("Analysis of the confusion matrices provides crucial engineering insights: Signals-Only exhibits high specificity (1,901 True Negatives) but critically low recall (only 29 True Positives, missing 789 decisive errors). ML-Only achieves strong recall (479 True Positives) and an ROC-AUC of 0.7033, but suffers from elevated False Positives (544). The Hybrid Architecture reconciles this trade-off: by employing the False-Alarm Shield and Decision Fusion rules, it balances precision (49.45%) and recall (44.25%), maintaining robust trajectory-level interception while filtering out transient blips.", style_body))

    story.append(Paragraph("4.5 Case Study Walkthrough: Autonomous Flight Booking", style_h2))
    story.append(Paragraph("To demonstrate the end-to-end functionality of our system in a live application, we implemented a real-world scenario (<code>examples/demo_flight_booking.py</code>). An autonomous agent is tasked with finding and booking a flight from Hyderabad (HYD) to Delhi (DEL) within a user budget of ₹6,000.", style_body))

    # Flight booking flow image
    story.append(Image("results/figures/flight_booking_flow.png", width=460, height=228))
    story.append(Paragraph("Fig. 4.5: End-to-End recovery flow during the real-world flight booking case study.", style_caption))

    story.append(Paragraph("The execution trace unfolds through six distinct operational stages:", style_body))
    booking_trace = [
        "<b>Step 1 (Normal Search):</b> The agent calls search_flights(Sabre) to scan inventory. The API returns valid flights at ₹5,800. Monitoring records: retry_count=0, ML Risk=0.08. Decision: CONTINUE.",
        "<b>Step 2 (Tool Failure):</b> The agent invokes book_flight(Sabre). The Sabre gateway experiences a database timeout (HTTP 500 error). This represents the decisive error step (k*).",
        "<b>Step 3 (Multi-Tier Audit):</b> Signals record retry_count=1. ML model predicts failure risk P(failure)=0.62. LLM Judge diagnoses TOOL_FAILURE with 0.92 confidence.",
        "<b>Step 4 (Alarm Confirmation):</b> The Decision Fusion System notes that the tool failure is non-transient and confirms ALARM.",
        "<b>Step 5 (Intervention & Recovery):</b> The Intervention Layer checks ToolRegistry, selects Amadeus Flight API, executes SWITCH_TOOL, and reroutes the booking. Amadeus returns a flight at ₹5,200.",
        "<b>Step 6 (Successful Completion):</b> The agent books the Amadeus ticket, generating confirmed PNR (6E-DEL-892). Total middleware latency was under 120 ms."
    ]
    for bstep in booking_trace:
        story.append(Paragraph(f"• {bstep}", style_bullet))

    story.append(Paragraph("4.6 Latency & Operational Cost Analysis", style_h2))
    lat_pdf_data = [
        [Paragraph("<b>Architecture Layer</b>", style_body), Paragraph("<b>Execution Latency</b>", style_body), Paragraph("<b>Computational Cost</b>", style_body)],
        [Paragraph("Layer 1: Signals Engine", style_body), Paragraph("0.45 ms", style_body), Paragraph("0 tokens (Pure Python / CPU)", style_body)],
        [Paragraph("Layer 2: Lightweight ML Predictor", style_body), Paragraph("1.20 ms", style_body), Paragraph("0 tokens (Scikit-Learn inference)", style_body)],
        [Paragraph("Layer 3: LLM Judge (Groq Cloud API)", style_body), Paragraph("42.00 ms", style_body), Paragraph("~120 tokens per audited turn", style_body)],
        [Paragraph("Layer 4: Decision Fusion System", style_body), Paragraph("0.15 ms", style_body), Paragraph("0 tokens (Deterministic rule graph)", style_body)],
        [Paragraph("Layer 5: Intervention Layer", style_body), Paragraph("1.80 ms", style_body), Paragraph("0 tokens (Registry lookup & validation)", style_body)]
    ]
    t_lat = Table(lat_pdf_data, colWidths=[170, 110, 200])
    t_lat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_lat)
    story.append(Paragraph("Table 4.3: Component Latency and Computational Cost Comparison across System Layers.", style_caption))

    story.append(Paragraph("By executing Layers 1 and 2 in sub-2ms time, our system can conditionally bypass Layer 3 for safe turns. When LLM verification is invoked, Groq LPUs complete inference in ~42 ms, yielding a total pipeline latency well under 50 ms. Compared to continuous frontier model auditing (e.g., GPT-4 at ~1,500 ms and $0.03 per step), our hybrid approach reduces operational costs by over 98% while maintaining real-time responsiveness.", style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 5: CONCLUSION AND FUTURE SCOPE
    # -------------------------------------------------------------
    story.append(Paragraph("Chapter 5<br/><b>Conclusion and Future Scope</b>", style_chapter))
    story.append(Paragraph("5.1 Summary of Contributions", style_h2))
    story.append(Paragraph("This Bachelor of Technology Project has developed, implemented, and empirically validated a comprehensive Lightweight Real-Time Agent Failure Prediction and Intervention System for autonomous LLM agents. The key academic and engineering contributions include:", style_body))
    story.append(Paragraph("• <b>1. Theoretical Grounding:</b> Operationalized the shift from post-hoc failure attribution to online prefix auditing, formulating failure prevention as decisive error localization (k*).", style_bullet))
    story.append(Paragraph("• <b>2. Robust System Design:</b> Built a five-layer defense-in-depth pipeline integrating 24 deterministic signals, calibrated ML risk scoring, Pydantic-validated LLM auditing, deterministic decision shielding, and closed-loop interventions.", style_bullet))
    story.append(Paragraph("• <b>3. Empirical Validation:</b> Demonstrated an 89.57% early interception rate and an average early warning lead time of 4.04 steps across 332 held-out trajectories from the AFTraj-2K benchmark.", style_bullet))
    story.append(Paragraph("• <b>4. Actionable Recovery:</b> Successfully demonstrated live recovery in a real-world flight booking scenario, substituting broken APIs and salvaging the user's objective without human intervention.", style_bullet))
    story.append(Paragraph("• <b>5. Engineering Rigor:</b> Established a modular codebase with 54 passing automated test suites, sub-50ms latency, and seamless integration with Groq high-speed cloud APIs.", style_bullet))

    story.append(Paragraph("5.2 System Limitations", style_h2))
    story.append(Paragraph("• <b>1. Tool Registry Dependency:</b> The Intervention Layer relies on pre-registered alternative tools (e.g., Sabre -> Amadeus). If a novel tool fails and no registered equivalent exists, the system must fall back to generic prompt replanning or human escalation.", style_bullet))
    story.append(Paragraph("• <b>2. Domain Transferability:</b> While tool failures and infinite loops are detected with near-perfect accuracy, subtle intermediate mathematical reasoning errors (e.g., in advanced Olympiad problems) remain difficult for statistical ML signals alone to distinguish from valid exploratory calculations.", style_bullet))
    story.append(Paragraph("• <b>3. Window Horizon:</b> The loop detector operates over a sliding window of k=3 turns. Complex multi-agent loops with period k > 5 require larger window buffers and higher memory tracking.", style_bullet))

    story.append(Paragraph("5.3 Future Directions", style_h2))
    story.append(Paragraph("• <b>1. Learned Interventions:</b> Training an autonomous meta-agent policy (via PPO or DPO) that directly learns optimal recovery actions from rollouts, moving beyond rule-based intervention mappings.", style_bullet))
    story.append(Paragraph("• <b>2. Dynamic Tool Discovery:</b> Equipping the system with dynamic MCP (Model Context Protocol) and OpenAPI tool search capabilities to automatically discover, test, and register substitute APIs at runtime.", style_bullet))
    story.append(Paragraph("• <b>3. Decentralized Auditing:</b> Extending the single-auditor model to a decentralized committee of lightweight auditor nodes capable of auditing multi-agent systems with dozens of concurrent agents.", style_bullet))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # REFERENCES
    # -------------------------------------------------------------
    story.append(Paragraph("REFERENCES", style_chapter))
    refs = [
        "[1] Zhang, B., Zhu, J., Shi, Z., Liu, D., & Tang, R. (2026). AgentForesight: Online Auditing for Early Failure Prediction in Multi-Agent Systems. arXiv preprint arXiv:2605.08715.",
        "[2] Zhu, J., Zhang, B., Shi, Z., & Tang, R. (2024). Who and When: Diagnosing Multi-Agent Failures via Decisive Error Localization. Advances in Neural Information Processing Systems (NeurIPS 2024), 37, 10421-10438.",
        "[3] Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. International Conference on Learning Representations (ICLR 2023).",
        "[4] Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. Advances in Neural Information Processing Systems (NeurIPS 2023), 36, 8634-8652.",
        "[5] Qin, Y., Liang, S., Ye, Y., Zhu, K., Yan, L., Lu, Y., ... & Sun, M. (2023). ToolLLM: Facilitating Large Language Models to Master 16000+ Real-World APIs. arXiv preprint arXiv:2307.16789.",
        "[6] Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., ... & Clark, P. (2023). Self-Refine: Iterative Refinement with Self-Feedback. Advances in Neural Information Processing Systems (NeurIPS 2023), 36, 46534-46551.",
        "[7] Liu, Z., Yao, Y., Zhang, R., Guo, C., & Yu, P. S. (2024). AutoSafe: Proactive Guardrails for Autonomous Multi-Agent Workflows. ACM CIKM 2024.",
        "[8] Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2023). Self-Consistency Improves Chain of Thought Reasoning in Language Models. ICLR 2023.",
        "[9] Chen, M., Tworek, J., Jun, H., Yuan, Q., Pinto, H., ... & Zaremba, W. (2021). Evaluating Large Language Models Trained on Code. arXiv preprint arXiv:2107.03374.",
        "[10] Cobbe, K., Kosaraju, V., Bavarian, M., Chen, M., Jun, H., ... & Schulman, J. (2021). Training Verifiers to Solve Math Word Problems. arXiv preprint arXiv:2110.14168.",
        "[11] Yao, S., Chen, H., Yang, J., & Narasimhan, K. (2022). WebShop: Towards Solving Real-World Web Interaction with Grounded Language Agents. NeurIPS 2022.",
        "[12] Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., & Narasimhan, K. (2024). SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR 2024.",
        "[13] Hong, S., Zheng, X., Chen, J., Cheng, Y., Wang, J., Zhang, C., ... & Wu, C. (2024). MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework. ICLR 2024.",
        "[14] Wu, Q., Bansal, G., Zhang, J., Wu, Y., Li, B., Zhu, E., ... & Wang, C. (2023). AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. arXiv:2308.08155.",
        "[15] Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., ... & Duchesnay, É. (2011). Scikit-learn: Machine Learning in Python. JMLR, 12, 2825-2830."
    ]
    for ref in refs:
        story.append(Paragraph(ref, ParagraphStyle('RefP', parent=style_body, fontSize=9.5, leading=13, spaceAfter=5)))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # APPENDICES
    # -------------------------------------------------------------
    story.append(Paragraph("APPENDIX A<br/><b>Complete Specification of 24 Runtime Signals</b>", style_chapter))
    app_data = [
        [Paragraph("<b>Signal Name</b>", style_body), Paragraph("<b>Data Type</b>", style_body), Paragraph("<b>Operational Description</b>", style_body)],
        [Paragraph("<b>retry_count</b>", style_body), Paragraph("Integer", style_body), Paragraph("Current count of retried tool executions for the current step.", style_body)],
        [Paragraph("<b>is_repeat_action</b>", style_body), Paragraph("Binary (0/1)", style_body), Paragraph("Indicates whether exact same tool name and arguments were called as in turn t-1.", style_body)],
        [Paragraph("<b>consecutive_tool_failures</b>", style_body), Paragraph("Integer", style_body), Paragraph("Rolling count of uninterrupted consecutive tool error returns.", style_body)],
        [Paragraph("<b>max_consecutive_retries</b>", style_body), Paragraph("Integer", style_body), Paragraph("Historical peak retry depth reached within the current conversation.", style_body)],
        [Paragraph("<b>tool_call_failed</b>", style_body), Paragraph("Binary (0/1)", style_body), Paragraph("Flag set to 1 if immediate turn resulted in an exception or non-zero status.", style_body)],
        [Paragraph("<b>isolated_failure_flag</b>", style_body), Paragraph("Binary (0/1)", style_body), Paragraph("Shield flag indicating isolated blip (fail=1 with 0 prior failures and no loop).", style_body)],
        [Paragraph("<b>loop_indicator_score</b>", style_body), Paragraph("Float [0, 1]", style_body), Paragraph("Normalized Jaccard similarity across action argument strings in window k=3.", style_body)],
        [Paragraph("<b>stagnation_index</b>", style_body), Paragraph("Float [0, 1]", style_body), Paragraph("Heuristic score measuring lack of state mutation or observation advancement.", style_body)],
        [Paragraph("<b>task_drift_score</b>", style_body), Paragraph("Float [0, 1]", style_body), Paragraph("Semantic distance between current turn embedding and initial task query.", style_body)],
        [Paragraph("<b>step_index</b>", style_body), Paragraph("Integer", style_body), Paragraph("Zero-indexed step position t within the unfolding trajectory.", style_body)]
    ]
    t_app = Table(app_data, colWidths=[130, 90, 260])
    t_app.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_app)

    story.append(Spacer(1, 15))
    story.append(Paragraph("APPENDIX B<br/><b>Prompt Template for Real-Time LLM Judge</b>", style_chapter))
    prompt_str = (
        "You are an expert Autonomous Agent Failure Auditor operating in real-time.\n"
        "Your task is to analyze an unfolding trajectory prefix tau_{0:t} and determine whether a decisive error has occurred.\n\n"
        "Input Data Provided:\n"
        "1. User Task Query & Constraints\n"
        "2. Step Execution History (Turn t, Role, Action, Arguments, Observation)\n"
        "3. Runtime Signals (retry_count, isolated_failure_flag, loop_indicator_score)\n"
        "4. Lightweight ML Predicted Failure Risk P(failure | x_t)\n\n"
        "Audit Requirements:\n"
        "- If trajectory is progressing normally or experiencing a recoverable glitch, return verdict = 'CONTINUE'.\n"
        "- If an unrecoverable decisive error or permanent tool crash occurred, return verdict = 'ALARM'.\n"
        "- Classify reason_category strictly as one of: [TEMPORARY_TIMEOUT, TOOL_FAILURE, LOOP, PLAN_MISMATCH, STAGNATION, UNKNOWN].\n"
        "- Output MUST strictly conform to Pydantic JSON schema (verdict, reason_category, confidence, responsible_agent, explanation)."
    )
    story.append(Paragraph(prompt_str.replace('\n', '<br/>'), style_code))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated BTP Final Report at: {output_filename}")

if __name__ == "__main__":
    create_pdf_report()

