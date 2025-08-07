from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import navy, black, gray
from datetime import datetime
from .architect import FinalReportContent

def create_feedback_pdf(report_content: FinalReportContent, output_path: str):
    """
    Crea un file PDF con la nuova struttura del report, separando gli esiti
    dell'analisi del CV da quelli del colloquio.
    """
    print(f"Creazione del file PDF con nuovo layout: {output_path}...")
    doc = SimpleDocTemplate(output_path, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    
    # Stili personalizzati
    header_style = ParagraphStyle('Header', fontName='Helvetica', fontSize=10, textColor=gray, alignment=1)
    h1_style = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=16, spaceAfter=14, textColor=navy, spaceBefore=10)
    body_style = styles['BodyText']
    body_style.spaceAfter = 12
    body_style.leading = 14
    
    story = []
    
    # Frase fissa iniziale
    fixed_intro = "Il report di seguito, e le analisi che in esso sono sintetizzate, si basano sul contenuto del materiale di candidatura unito all'analisi della risoluzione del Case, effettuata durante apposito colloquio virtuale."
    story.append(Paragraph(fixed_intro, styles['Italic']))
    story.append(Spacer(1, 0.5*inch))
    
    # Intestazione
    date_str = datetime.now().strftime("%d %B %Y")
    header_text = f"<b>Candidato:</b> {report_content.candidate_name}<br/><b>Posizione Target:</b> {report_content.target_role}<br/><b>Data:</b> {date_str}"
    story.append(Paragraph(header_text, header_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", color=gray, thickness=0.5))
    story.append(Spacer(1, 0.3*inch))
    
    # --- INIZIO MODIFICHE AL LAYOUT ---
    
    # 1. Profilo Sintetico (Invariato)
    story.append(Paragraph("Sintesi del Profilo", h1_style))
    story.append(Paragraph(report_content.profile_summary.replace('\n', '<br/>'), body_style))
    
    # 2. Esito Analisi CV (Nuovo Paragrafo)
    story.append(Paragraph("Esito Analisi CV", h1_style))
    story.append(Paragraph(report_content.cv_analysis_outcome.replace('\n', '<br/>'), body_style))
    
    # 3. Esito Colloquio (Nuovo Paragrafo)
    story.append(Paragraph("Esito Colloquio", h1_style))
    story.append(Paragraph(report_content.interview_outcome.replace('\n', '<br/>'), body_style))
    
    # 4. Percorso di Upskilling (Logica invariata, cambia solo la numerazione)
    if report_content.suggested_pathway:
        story.append(Paragraph("Percorso di Upskilling Suggerito", h1_style))
        story.append(Paragraph("Per supportare la tua crescita, abbiamo delineato un possibile percorso formativo basato sulle aree di miglioramento identificate:", body_style))
        
        for i, course in enumerate(report_content.suggested_pathway):
            course_title_style = ParagraphStyle('CourseTitle', fontName='Helvetica-Bold', fontSize=12, spaceBefore=10, spaceAfter=4)
            story.append(Paragraph(f"<b>{i+1}. {course.course_name}</b>", course_title_style))
            story.append(Paragraph(f"<b>Obiettivo:</b> {course.justification}", body_style))
            story.append(Paragraph(f"<i>Livello: {course.level} | Durata: ~{course.duration_hours} ore | <a href='{course.url}' color='blue'><u>Vai al corso</u></a></i>", body_style))
            
    # 5. Benchmark di Mercato (Nuovo Paragrafo con placeholder)
    story.append(Paragraph("Benchmark di Mercato", h1_style))
    story.append(Paragraph(report_content.market_benchmark, body_style))
    
    # --- FINE MODIFICHE AL LAYOUT ---
        
    try:
        doc.build(story)
        print(f"PDF creato con successo in '{output_path}'")
    except Exception as e:
        print(f"Errore durante la creazione del PDF: {e}")