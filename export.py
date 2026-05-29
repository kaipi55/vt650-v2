from datetime import datetime
from io import BytesIO

try:
    from PySide6.QtPdfWidgets import QPdfView
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtCore import QBuffer, QByteArray
    PDF_VIEW_AVAILABLE = True
except ImportError:
    PDF_VIEW_AVAILABLE = False
    QPdfView = None
    QPdfDocument = None
    QBuffer = None
    QByteArray = None

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QTextEdit, QMessageBox, QFileDialog,
    QDialogButtonBox
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak
)

# PDF helpers and sections
from pdf_styles import PDFStyles
from pdf_helpers import build_table, mm_widths
from pdf_sections import HeaderInforme, SeccionAmbiental, TablaResultados


# ─────────────────────────────────────────────────────────────────
# Generador de informe PDF
# ─────────────────────────────────────────────────────────────────
class GeneradorInforme:
    def __init__(self, analizador, params_dispositivo: dict = None):
        self.analizador  = analizador
        self.params_disp = params_dispositivo or {}

    def generar_pdf(self, ruta: str, observaciones: str = ""):
        cfg = self.analizador.config
        res = self.analizador.resultados
        p = self.params_disp
        doc = SimpleDocTemplate(
            ruta,
            pagesize=A4,
            rightMargin=PDFStyles.MARGIN_RIGHT,
            leftMargin=PDFStyles.MARGIN_LEFT,
            topMargin=PDFStyles.MARGIN_TOP,
            bottomMargin=PDFStyles.MARGIN_BOTTOM
        )

        styles = PDFStyles.get_styles()

        story = []
        # Header
        header = HeaderInforme(cfg, styles, logo_path=cfg.get('logo_path'))
        story.extend(header.flowables())

        # Datos de la prueba
        story.append(Paragraph('1. Datos de la Prueba', styles['SectionTitle']))
        datos_prueba = [
            ['Operador:', cfg.get('operador', 'N/D'), 'Fecha / Hora:', datetime.now().strftime('%d/%m/%Y %H:%M')],
            ['Equipo analizado (ID):', cfg.get('equipo_id', 'N/D'), 'Modelo / Marca:', cfg.get('modelo', 'N/D')],
            ['Ciclos grabados:', str(self.analizador.n_ciclos), 'Gas:', p.get('gas', '--')],
            ['Modo correccion:', p.get('flcm', '--'), 'Notas:', cfg.get('notas', '')],
        ]
        colw = [PDFStyles.COL_MEDIUM, PDFStyles.COL_XLARGE, PDFStyles.COL_MEDIUM, PDFStyles.COL_XLARGE]
        story.append(build_table(datos_prueba, col_widths=colw, style_type='body'))

        # Ambiental
        env = SeccionAmbiental(p, styles)
        story.extend(env.flowables())

        # Parametros referencia
        story.append(Spacer(1, PDFStyles.SPACER_SMALL))
        story.append(Paragraph('3. Parametros Programados en el Respirador (Referencia)', styles['SectionTitle']))
        ref_data = [
            ['BPM', 'Vt (mL)', 'Ti (s)', 'PEEP (cmH2O)', 'PIP (cmH2O)', 'I:E', 'VM (L/min)', 'FIO2 (%)'],
            [
                str(cfg.get('bpm', '--')),
                str(cfg.get('vt', '--')),
                str(cfg.get('ti', '--')),
                str(cfg.get('peep', '--')),
                str(cfg.get('pip', '--')),
                f"1:{cfg.get('ie', '--')}",
                str(cfg.get('mv', '--')),
                str(cfg.get('fio2', '--')),
            ]
        ]
        story.append(build_table(ref_data, col_widths=[PDFStyles.COL_MEDIUM]*8, style_type='body'))

        # Resultados
        tabla_res = TablaResultados(res, styles)
        story.extend(tabla_res.flowables())

        # Diagnostico global
        total    = sum(1 for r in res.values() if r['cumple'] is not None)
        ok_count = sum(1 for r in res.values() if r['cumple'] is True)
        if total > 0:
            pct_ok = ok_count / total * 100
            if pct_ok == 100:
                diag_text = f"DENTRO DE NORMATIVA  -  {ok_count}/{total} parametros conformes (100%)"
            else:
                fuera = [r['label'] for r in res.values() if r['cumple'] is False]
                diag_text = (
                    f"FUERA DE NORMATIVA  -  {ok_count}/{total} conformes ({pct_ok:.0f}%) | "
                    f"No conformes: {', '.join(fuera)}"
                )
        else:
            diag_text = "Sin datos suficientes para evaluar."
        story.append(Spacer(1, PDFStyles.SPACER_MEDIUM))
        story.append(Paragraph('Diagnostico global', styles['SectionTitle']))
        story.append(Paragraph(diag_text, styles['NormalBody']))

        # Observaciones y firma
        story.append(Spacer(1, PDFStyles.SPACER_MEDIUM))
        story.append(Paragraph('5. Observaciones', styles['SectionTitle']))
        story.append(Paragraph(observaciones or '---', styles['NormalBody']))
        story.append(Spacer(1, PDFStyles.SPACER_SMALL))
        story.append(Paragraph('6. Firma del Tecnico', styles['SectionTitle']))
        story.append(Paragraph(f"Nombre: {cfg.get('operador', 'N/D')}", styles['NormalBody']))
        story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Small']))

        # Paginación / footer
        def _footer(canvas, doc):
            canvas.saveState()
            page_num = canvas.getPageNumber()
            footer_text = f"Página {page_num}    Fecha: {datetime.now().strftime('%d/%m/%Y')}    Serial: {cfg.get('equipo_id','N/D')}"
            canvas.setFont("Helvetica", 8)
            canvas.drawString(PDFStyles.MARGIN_LEFT, PDFStyles.MARGIN_BOTTOM/2, footer_text)
            canvas.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


# ─────────────────────────────────────────────────────────────────
# Dialogo de vista previa e impresion del informe
# ─────────────────────────────────────────────────────────────────
class DialogoInforme(QDialog):
    def __init__(self, generador: GeneradorInforme, parent=None):
        super().__init__(parent)
        self.generador = generador
        self.setWindowTitle("Vista previa del informe tecnico")
        self.resize(1000, 800)
        lay = QVBoxLayout(self)

        barra = QHBoxLayout()
        self.e_obs = QLineEdit()
        self.e_obs.setPlaceholderText("Observaciones adicionales (opcional)...")
        self.e_obs.textChanged.connect(self._actualizar_preview)
        barra.addWidget(QLabel("Obs:")); barra.addWidget(self.e_obs)
        btn_pdf = QPushButton("Exportar PDF"); btn_pdf.setFixedWidth(120)
        btn_pdf.setStyleSheet("background:#1565C0;color:white;font-weight:bold;padding:4px;")
        btn_pdf.clicked.connect(self._exportar_pdf)
        btn_txt = QPushButton("Exportar TXT"); btn_txt.setFixedWidth(110)
        btn_txt.clicked.connect(self._exportar_txt)
        barra.addWidget(btn_txt); barra.addWidget(btn_pdf)
        lay.addLayout(barra)

        # Vista previa: usar QPdfView si está disponible, sino QTextEdit
        if PDF_VIEW_AVAILABLE:
            self.pdf_view = QPdfView()
            self.pdf_doc = QPdfDocument()
            self.pdf_view.setDocument(self.pdf_doc)
            lay.addWidget(self.pdf_view)
        else:
            self.pdf_view = None
            self.browser = QTextEdit()
            self.browser.setReadOnly(True)
            self.browser.setStyleSheet("background:#f0f0f0;font-family:monospace;font-size:10px;")
            lay.addWidget(self.browser)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject); lay.addWidget(bb)
        self._actualizar_preview()

    def _actualizar_preview(self):
        """Genera vista previa del PDF en tiempo real."""
        if PDF_VIEW_AVAILABLE and self.pdf_view:
            try:
                # Generar PDF en BytesIO
                pdf_buffer = BytesIO()
                
                doc = SimpleDocTemplate(
                    pdf_buffer,
                    pagesize=A4,
                    rightMargin=20,
                    leftMargin=20,
                    topMargin=20,
                    bottomMargin=20
                )
                
                styles = getSampleStyleSheet()
                styles.add(ParagraphStyle(
                    name='TitleCenter', alignment=TA_CENTER, fontSize=16, leading=18, spaceAfter=12
                ))
                styles.add(ParagraphStyle(
                    name='Subtitle', alignment=TA_CENTER, fontSize=10, leading=12, textColor=colors.grey
                ))
                styles.add(ParagraphStyle(
                    name='SectionTitle', fontSize=12, leading=14, spaceBefore=12, spaceAfter=6, textColor=colors.darkblue
                ))
                styles.add(ParagraphStyle(
                    name='NormalSmall', fontSize=9, leading=11
                ))
                
                # Generar contenido
                cfg = self.generador.analizador.config
                res = self.generador.analizador.resultados
                p = self.generador.params_disp
                obs = self.e_obs.text()
                
                story = []
                story.append(Paragraph('INFORME TECNICO - VERIFICACION VENTILADOR MECANICO', styles['TitleCenter']))
                story.append(Paragraph('VT650 Monitor v3.0 | ReportLab PDF Preview', styles['Subtitle']))
                story.append(Spacer(1, 12))
                
                story.append(Paragraph('1. Datos de la Prueba', styles['SectionTitle']))
                datos = [
                    ['Operador:', cfg.get('operador', 'N/D'), 'Fecha:', datetime.now().strftime('%d/%m/%Y %H:%M')],
                    ['Equipo ID:', cfg.get('equipo_id', 'N/D'), 'Modelo:', cfg.get('modelo', 'N/D')],
                    ['Ciclos:', str(self.generador.analizador.n_ciclos), 'Gas:', p.get('gas', '--')],
                ]
                tbl = Table(datos, colWidths=[80, 150, 80, 150])
                tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOX', (0, 0), (-1, -1), 0.25, colors.grey),
                ]))
                story.append(tbl)
                
                story.append(Spacer(1, 12))
                story.append(Paragraph('2. Resultados', styles['SectionTitle']))
                
                # Tabla de resultados
                tabla_res = [['Parametro', 'Unidad', 'Media', 'Error%', 'Cumple']]
                for key, r in res.items():
                    cumple_txt = 'OK' if r['cumple'] is True else ('FALLA' if r['cumple'] is False else '--')
                    err_txt = f"{r['error_pct']:+.1f}%" if r['error_pct'] is not None else '--'
                    tabla_res.append([
                        r['label'],
                        r['unidad'],
                        f"{r['media']:.2f}",
                        err_txt,
                        cumple_txt
                    ])
                
                tbl_res = Table(tabla_res, colWidths=[100, 80, 80, 80, 80], repeatRows=1)
                tbl_res.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565C0')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ]))
                story.append(tbl_res)
                
                story.append(Spacer(1, 12))
                story.append(Paragraph('3. Observaciones', styles['SectionTitle']))
                story.append(Paragraph(obs or '(Sin observaciones)', styles['NormalSmall']))
                
                # Construir PDF
                doc.build(story)

                # Cargar en QPdfDocument usando QBuffer (QIODevice)
                pdf_buffer.seek(0)
                data = pdf_buffer.getvalue()
                ba = QByteArray(data)
                qbuf = QBuffer()
                qbuf.setData(ba)
                qbuf.open(QBuffer.ReadOnly)
                # Mantener referencia para que no sea recolectado
                self._preview_qbuffer = qbuf
                self.pdf_doc.load(qbuf)
                
            except Exception as e:
                QMessageBox.warning(self, "Error en preview", f"No se pudo generar preview: {str(e)}")
        else:
            # Fallback: mostrar tabla simple
            if hasattr(self, 'browser'):
                cfg = self.generador.analizador.config
                res = self.generador.analizador.resultados
                html = f"""<html><body style='font-family:Arial;'>
                <h1>INFORME TECNICO - VT650 Monitor</h1>
                <p><b>Operador:</b> {cfg.get('operador', 'N/D')}</p>
                <p><b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><b>Ciclos:</b> {self.generador.analizador.n_ciclos}</p>
                <h2>Resultados</h2>
                <table border=1>
                <tr><th>Parametro</th><th>Media</th><th>Error%</th><th>Cumple</th></tr>
                """
                for key, r in res.items():
                    cumple = 'OK' if r['cumple'] is True else ('FALLA' if r['cumple'] is False else '--')
                    err = f"{r['error_pct']:+.1f}%" if r['error_pct'] is not None else '--'
                    html += f"<tr><td>{r['label']}</td><td>{r['media']:.2f}</td><td>{err}</td><td>{cumple}</td></tr>"
                html += "</table></body></html>"
                self.browser.setHtml(html)

    def _exportar_pdf(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar informe PDF",
            f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF (*.pdf)")
        if not ruta: return
        try:
            self.generador.generar_pdf(ruta, self.e_obs.text())
            QMessageBox.information(self, "PDF generado", f"Guardado en:\n{ruta}")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error al generar PDF", f"{str(e)}\n\n{traceback.format_exc()}")

    def _exportar_txt(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar resumen TXT",
            f"resumen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Texto (*.txt)")
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(self.generador.analizador.resumen_texto())
            QMessageBox.information(self, "Exportado", f"Guardado en:\n{ruta}")
