# ─────────────────────────────────────────────────────────────────
# Estilos y configuración centralizada para PDF con ReportLab
# ─────────────────────────────────────────────────────────────────

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.units import mm

class PDFStyles:
    """Centraliza todos los estilos para los PDFs."""
    
    # Colores institucionales
    COLOR_PRIMARY = colors.HexColor('#1565C0')
    COLOR_SECONDARY = colors.HexColor('#1A237E')
    COLOR_ACCENT = colors.HexColor('#00BCD4')
    COLOR_SUCCESS = colors.HexColor('#1B5E20')
    COLOR_DANGER = colors.HexColor('#B71C1C')
    COLOR_WARN = colors.HexColor('#FB8C00')
    
    # Márgenes en mm
    MARGIN_TOP = 15 * mm
    MARGIN_BOTTOM = 15 * mm
    MARGIN_LEFT = 12 * mm
    MARGIN_RIGHT = 12 * mm
    
    # Anchos de columna en mm
    COL_NARROW = 12 * mm
    COL_SMALL = 18 * mm
    COL_MEDIUM = 25 * mm
    COL_WIDE = 40 * mm
    COL_XLARGE = 60 * mm
    
    # Espaciado
    SPACER_SMALL = 6 * mm
    SPACER_MEDIUM = 10 * mm
    SPACER_LARGE = 15 * mm
    
    @staticmethod
    def get_styles():
        """Retorna diccionario de estilos personalizados."""
        styles = getSampleStyleSheet()
        
        # Encabezado principal
        styles.add(ParagraphStyle(
            name='HeaderMain',
            fontSize=18,
            leading=22,
            textColor=PDFStyles.COLOR_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
            fontName='Helvetica-Bold'
        ))
        
        # Subtítulo
        styles.add(ParagraphStyle(
            name='Subtitle',
            fontSize=10,
            leading=12,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=10 * mm
        ))
        
        # Sección
        styles.add(ParagraphStyle(
            name='SectionTitle',
            fontSize=12,
            leading=14,
            textColor=PDFStyles.COLOR_PRIMARY,
            fontName='Helvetica-Bold',
            spaceBefore=8 * mm,
            spaceAfter=6 * mm,
            borderColor=PDFStyles.COLOR_SECONDARY,
            borderWidth=0.5
        ))
        
        # Subsección
        styles.add(ParagraphStyle(
            name='SubsectionTitle',
            fontSize=11,
            leading=13,
            textColor=PDFStyles.COLOR_SECONDARY,
            fontName='Helvetica-Bold',
            spaceBefore=6 * mm,
            spaceAfter=4 * mm
        ))
        
        # Texto normal
        styles.add(ParagraphStyle(
            name='NormalBody',
            fontSize=9,
            leading=11,
            alignment=TA_LEFT,
            spaceAfter=4 * mm
        ))
        
        # Texto pequeño (pies de página)
        styles.add(ParagraphStyle(
            name='Small',
            fontSize=8,
            leading=10,
            textColor=colors.grey,
            alignment=TA_LEFT
        ))
        
        # Tabla header
        styles.add(ParagraphStyle(
            name='TableHeader',
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=colors.white,
            alignment=TA_CENTER,
            valign='MIDDLE',
            wordWrap='CJK'
        ))
        
        # Tabla body
        styles.add(ParagraphStyle(
            name='TableCell',
            fontSize=7.5,
            alignment=TA_CENTER,
            valign='MIDDLE',
            wordWrap='CJK'
        ))
        
        return styles


class PDFTableStyles:
    """Estilos predefinidos para tablas."""
    
    @staticmethod
    def get_header_style(num_cols):
        """Retorna TableStyle para encabezado."""
        from reportlab.platypus import TableStyle
        return TableStyle([
            ('BACKGROUND', (0, 0), (num_cols - 1, 0), PDFStyles.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (num_cols - 1, 0), colors.white),
            ('FONTNAME', (0, 0), (num_cols - 1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (num_cols - 1, 0), 8),
            ('ALIGN', (0, 0), (num_cols - 1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (num_cols - 1, 0), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (num_cols - 1, 0), 6),
        ])
    
    @staticmethod
    def get_body_style(num_rows, num_cols):
        """Retorna TableStyle para cuerpo con filas alternadas."""
        from reportlab.platypus import TableStyle
        styles = [
            ('ALIGN', (0, 1), (num_cols - 1, num_rows - 1), 'CENTER'),
            ('VALIGN', (0, 0), (num_cols - 1, num_rows - 1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (num_cols - 1, num_rows - 1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (num_cols - 1, num_rows - 1), 7),
            ('LEFTPADDING', (0, 1), (num_cols - 1, num_rows - 1), 4),
            ('RIGHTPADDING', (0, 1), (num_cols - 1, num_rows - 1), 4),
            ('TOPPADDING', (0, 1), (num_cols - 1, num_rows - 1), 3),
            ('BOTTOMPADDING', (0, 1), (num_cols - 1, num_rows - 1), 3),
        ]
        
        # Filas alternadas
        for row in range(1, num_rows):
            if row % 2 == 0:
                styles.append(('BACKGROUND', (0, row), (num_cols - 1, row), colors.HexColor('#f5f5f5')))
        
        # Grid
        styles.append(('WORDWRAP', (0, 0), (num_cols - 1, num_rows - 1), 'CJK'))
        styles.append(('BOX', (0, 0), (num_cols - 1, num_rows - 1), 0.5, colors.grey))
        styles.append(('INNERGRID', (0, 0), (num_cols - 1, num_rows - 1), 0.25, colors.lightgrey))
        
        return TableStyle(styles)
    
    @staticmethod
    def get_result_style(num_rows, num_cols):
        """Retorna TableStyle para tabla de resultados con colores OK/FAIL."""
        from reportlab.platypus import TableStyle
        styles = [
            ('BACKGROUND', (0, 0), (num_cols - 1, 0), PDFStyles.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (num_cols - 1, 0), colors.white),
            ('FONTNAME', (0, 0), (num_cols - 1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (num_cols - 1, 0), 7.5),
            ('ALIGN', (0, 0), (num_cols - 1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, num_rows - 1), 'LEFT'),
            ('ALIGN', (1, 1), (num_cols - 1, num_rows - 1), 'CENTER'),
            ('VALIGN', (0, 0), (num_cols - 1, num_rows - 1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (num_cols - 1, num_rows - 1), 'CJK'),
            ('BOX', (0, 0), (num_cols - 1, num_rows - 1), 0.5, colors.grey),
            ('INNERGRID', (0, 0), (num_cols - 1, num_rows - 1), 0.25, colors.lightgrey),
        ]
        return TableStyle(styles)
