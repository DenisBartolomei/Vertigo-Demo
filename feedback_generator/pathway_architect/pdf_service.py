# In feedback_generator/pathway_architect/pdf_service.py

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import navy, black, gray
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
from .architect import FinalReportContent
import os
import base64
from io import BytesIO
import re

def create_feedback_pdf(report_content: FinalReportContent, output_path: str, **kwargs):
    """
    Crea un file PDF completo, con tutte le sezioni, i grafici Base64
    e la formattazione corretta dei titoli.
    """
    print(f"Creazione del file PDF completo: {output_path}...")
    doc = SimpleDocTemplate(output_path, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    
    # Definizione degli stili
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('Header', fontName='Helvetica', fontSize=10, textColor=gray, alignment=TA_CENTER)
    h1_style = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=16, spaceAfter=14, textColor=navy, spaceBefore=20)
    body_style = styles['BodyText']
    body_style.spaceAfter = 12
    body_style.leading = 14
    course_title_style = ParagraphStyle('CourseTitle', fontName='Helvetica-Bold', fontSize=12, spaceBefore=10, spaceAfter=4)

    story = []

    # --- Sezioni 1-4: Contenuto Principale ---
    fixed_intro = "Il report di seguito, e le analisi che in esso sono sintetizzate, si basano sul contenuto del materiale di candidatura unito all'analisi della risoluzione del Case, effettuata durante apposito colloquio virtuale."
    story.append(Paragraph(fixed_intro, styles['Italic']))
    story.append(Spacer(1, 0.5*inch))

    date_str = datetime.now().strftime("%d %B %Y")
    header_text = f"<b>Candidato:</b> {report_content.candidate_name}<br/><b>Posizione Target:</b> {report_content.target_role}<br/><b>Data:</b> {date_str}"
    story.append(Paragraph(header_text, header_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", color=gray, thickness=0.5))
    story.append(Spacer(1, 0.3*inch))

    # 1. Profilo Sintetico
    story.append(Paragraph("Sintesi del Profilo", h1_style))
    story.append(Paragraph(report_content.profile_summary.replace('\n', '<br/>'), body_style))

    # 2. Esito Analisi CV
    story.append(Paragraph("Esito Analisi CV", h1_style))
    story.append(Paragraph(report_content.cv_analysis_outcome.replace('\n', '<br/>'), body_style))

    # 3. Esito Colloquio
    story.append(Paragraph("Esito Colloquio", h1_style))
    story.append(Paragraph(report_content.interview_outcome.replace('\n', '<br/>'), body_style))

    # 4. Percorso di Upskilling
    if report_content.suggested_pathway:
        story.append(Paragraph("Percorso di Upskilling Suggerito", h1_style))
        story.append(Paragraph("Per supportare la tua crescita, abbiamo delineato un possibile percorso formativo basato sulle aree di miglioramento identificate:", body_style))

        for i, course in enumerate(report_content.suggested_pathway):
            story.append(Paragraph(f"<b>{i+1}. {course.course_name}</b>", course_title_style))
            story.append(Paragraph(f"<b>Obiettivo:</b> {course.justification}", body_style))
            story.append(Paragraph(f"<i>Livello: {course.level} | Durata: ~{course.duration_hours} ore | <a href='{course.url}' color='blue'><u>Vai al corso</u></a></i>", body_style))

    # --- Sezione 5: Benchmark di Mercato ---
    story.append(Paragraph("Benchmark di Mercato", h1_style))
    
    # Recupera i dati passati come keyword arguments
    benchmark_text_raw = kwargs.get("market_benchmark_text") or ""
    ##chart_cat_base64 = kwargs.get("market_chart_categories_base64")
    ##market_skills_list = kwargs.get("market_skills_list")
    
    if benchmark_text_raw:
        cleaned_text = benchmark_text_raw.replace('**', '')
        parts = re.split(r'(###\s*.*)', cleaned_text)

        for part in parts:
            part = part.strip()
            if not part: continue

            if part.startswith('###'):
                title_text = part.replace('###', '').strip()
                story.append(Paragraph(title_text, course_title_style))
                story.append(Spacer(1, 0.1 * inch))
            else:
                body_text = part.replace('\n', '<br/>')
                story.append(Paragraph(body_text, body_style))
    else:
        story.append(Paragraph("Dati di benchmark non disponibili.", body_style))

    ##def add_image_from_base64(b64_string, story_list):
    ##    if not b64_string: return
    ##    try:
    ##        story_list.append(Spacer(1, 0.2 * inch))
    ##        image_data = base64.b64decode(b64_string)
    ##        image_stream = BytesIO(image_data)
    ##        img = Image(image_stream, width=6.0 * inch, height=4.0 * inch)
    ##        img.hAlign = 'CENTER'
    ##        story_list.append(img)
    ##    except Exception as e:
    ##        print(f"Avviso: impossibile inserire il grafico da Base64: {e}")

    ### Aggiunta della casella di testo richiesta prima della prima immagine
    ##story.append(Spacer(1, 0.2 * inch))
    ##story.append(Paragraph("Nella figura sottostante è riportata la percentuale delle occorrenze relative alle mansioni svolte da profili in linea con la posizione in esame.", body_style))
    ##
    ### Aggiungi il primo grafico (categorie) se presente
    ##add_image_from_base64(chart_cat_base64, story)
    ##
    ### Aggiunge la frase e l'elenco di skill, invece del secondo grafico
    ##if market_skills_list:
    ##    story.append(Spacer(1, 0.3 * inch)) # Spazio per separare dal contenuto precedente
    ##    intro_text = "Di seguito, infine, una lista di competenze più comuni derivanti dall'analisi di mercato per la posizione in esame:"
    ##    story.append(Paragraph(intro_text, body_style))
    ##    
    ##    # Unisce le skill in una stringa separata da virgola e la aggiunge al PDF
    ##    skills_as_text = ", ".join(market_skills_list)
    ##    story.append(Paragraph(skills_as_text, body_style))

    # --- Costruzione Finale del PDF ---
    try:
        doc.build(story)
        print(f"PDF creato con successo in '{output_path}'")
    except Exception as e:
        print(f"Errore durante la creazione del PDF: {e}")