from reportlab.platypus import Table, Paragraph
from reportlab.lib.units import mm
from pdf_styles import PDFStyles, PDFTableStyles


def mm_widths(*cols_mm):
    """Convierte una lista de anchos en mm a puntos (ReportLab usa puntos)."""
    return [ (c * mm) for c in cols_mm ]


def build_table(data, col_widths=None, style_type='body', wrap=True):
    """Construye una `Table` con estilos centralizados.

    - `col_widths`: lista de anchos en puntos (no en mm) o None.
    - `style_type`: 'body', 'result' o 'header'.
    - `wrap`: si es True, convierte el contenido en Paragraph para habilitar el ajuste de texto.
    """
    num_rows = len(data)
    num_cols = max(len(row) for row in data) if num_rows else 0

    if wrap:
        styles = PDFStyles.get_styles()
        cell_style = styles['TableCell']
        wrapped_data = []
        for row in data:
            wrapped_row = []
            for cell in row:
                if isinstance(cell, str):
                    wrapped_row.append(Paragraph(cell, cell_style))
                else:
                    wrapped_row.append(cell)
            wrapped_data.append(wrapped_row)
    else:
        wrapped_data = data

    tbl = Table(wrapped_data, colWidths=col_widths, repeatRows=1 if num_rows>1 else 0)

    if style_type == 'result':
        tbl.setStyle(PDFTableStyles.get_result_style(num_rows, num_cols))
    elif style_type == 'header':
        tbl.setStyle(PDFTableStyles.get_header_style(num_cols))
    else:
        tbl.setStyle(PDFTableStyles.get_body_style(num_rows, num_cols))

    return tbl
