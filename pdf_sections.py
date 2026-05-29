from reportlab.platypus import Paragraph, Spacer, Image
from reportlab.lib.units import mm
from pdf_styles import PDFStyles
from pdf_helpers import build_table, mm_widths


class HeaderInforme:
    def __init__(self, cfg: dict, styles, logo_path: str = None):
        self.cfg = cfg
        self.styles = styles
        self.logo_path = logo_path

    def flowables(self):
        flows = []
        if self.logo_path:
            try:
                img = Image(self.logo_path, width=20*mm, height=20*mm)
                flows.append(img)
            except Exception:
                pass
        title = Paragraph('INFORME TECNICO DE VERIFICACION - VENTILADOR MECANICO', self.styles['HeaderMain'])
        subtitle = Paragraph(f"Equipo: {self.cfg.get('equipo_id','N/D')}  |  Modelo: {self.cfg.get('modelo','N/D')}", self.styles['Subtitle'])
        flows.append(title)
        flows.append(subtitle)
        flows.append(Spacer(1, PDFStyles.SPACER_MEDIUM))
        return flows


class SeccionAmbiental:
    def __init__(self, params: dict, styles):
        self.params = params
        self.styles = styles

    def flowables(self):
        data = [
            ['Temperatura:', f"{self.params.get('temp','--')} C", 'Humedad relativa:', f"{self.params.get('hum','--')} %"],
            ['Presion barometrica:', f"{self.params.get('prba','--')}", 'Analizador:', 'Fluke VT650'],
        ]
        colw = mm_widths(30, 40, 30, 40)
        tbl = build_table(data, col_widths=colw, style_type='body')
        return [Paragraph('2. Condiciones Ambientales', self.styles['SectionTitle']), tbl]


class TablaResultados:
    def __init__(self, resultados: dict, styles):
        self.resultados = resultados
        self.styles = styles

    def flowables(self):
        header = ['Parametro', 'Unidad', 'N ciclos', 'Media', 'Std', 'Min', 'Max', 'CV%', 'Oscil%', 'Referencia', 'Error%', 'Tolerancia', 'Resultado']
        data = [header]
        for key, r in self.resultados.items():
            data.append([
                r['label'], r['unidad'], str(r['n']),
                f"{r['media']:.2f}", f"{r['std']:.2f}", f"{r['min']:.2f}", f"{r['max']:.2f}",
                f"{r['cv_pct']:.1f}%", f"{r['oscil_pct']:.1f}%",
                f"{r['ref']:.2f}" if r['ref'] is not None else '--',
                f"{r['error_pct']:+.1f}%" if r['error_pct'] is not None else '--',
                r['tol_desc'] or '--',
                'OK' if r['cumple'] is True else ('FALLA' if r['cumple'] is False else '--')
            ])

        colw = mm_widths(30, 10, 10, 10, 10, 10, 10, 10, 10, 12, 12, 15, 12)
        tbl = build_table(data, col_widths=colw, style_type='result')
        return [Paragraph('4. Resultados - Estadisticas por Parametro (ISO 80601-2-12)', self.styles['SectionTitle']), tbl]
