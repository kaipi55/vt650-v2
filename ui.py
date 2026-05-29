from datetime import datetime
import serial.tools.list_ports
import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGroupBox, QGridLayout,
    QMessageBox, QFileDialog, QStackedWidget, QFrame, QDialog,
    QDialogButtonBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QLineEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QTextEdit
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QColor, QTextDocument, QPageSize, QPageLayout

from config import (
    BUFFER, VEN_MIN, VEN_MAX, MAX_SW, INSP_THRESH, EXP_THRESH,
    INSP_CONFIRM, GAS_DESC, FLCM_DESC, NORMA, REF_KEYS
)
from core import FiltroRueda, GrabacionManager, AnalizadorDatos, VT650
from export import GeneradorInforme, DialogoInforme


# ─────────────────────────────────────────────────────────────────
# Dialogo de configuracion de grabacion
# ─────────────────────────────────────────────────────────────────
class DialogConfigGrabacion(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Grabacion"); self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        g_info = QGroupBox("Informacion de la prueba"); fl = QFormLayout(g_info)
        self.e_operador  = QLineEdit(); fl.addRow("Operador:",          self.e_operador)
        self.e_equipo_id = QLineEdit(); fl.addRow("ID equipo (serie):", self.e_equipo_id)
        self.e_modelo    = QLineEdit(); fl.addRow("Modelo respirador:", self.e_modelo)
        self.e_notas     = QLineEdit(); fl.addRow("Notas:",             self.e_notas)
        lay.addWidget(g_info)
        g_dur = QGroupBox("Duracion de la grabacion"); fl2 = QFormLayout(g_dur)
        self.sp_duracion = QSpinBox()
        self.sp_duracion.setRange(0, 3600); self.sp_duracion.setValue(0)
        self.sp_duracion.setSuffix(" s   (0 = manual)"); fl2.addRow("Duracion:", self.sp_duracion)
        lay.addWidget(g_dur)
        g_ref = QGroupBox("Parametros programados en el respirador"); fl3 = QFormLayout(g_ref)
        self._spins = {}
        for key, label, unidad, mn, mx, paso, defv in REF_KEYS:
            sp = QDoubleSpinBox(); sp.setRange(mn, mx); sp.setSingleStep(paso); sp.setValue(defv)
            sp.setSuffix(f"  {unidad}" if unidad else "")
            sp.setDecimals(1 if paso < 1 else 0)
            fl3.addRow(label + ":", sp); self._spins[key] = sp
        lay.addWidget(g_ref)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def get_config(self) -> dict:
        cfg = {
            'operador' : self.e_operador.text().strip()  or "N/D",
            'equipo_id': self.e_equipo_id.text().strip() or "N/D",
            'modelo'   : self.e_modelo.text().strip()    or "N/D",
            'notas'    : self.e_notas.text().strip(),
            'duracion_seg': self.sp_duracion.value(),
        }
        for key, sp in self._spins.items(): cfg[key] = sp.value()
        return cfg


# ─────────────────────────────────────────────────────────────────
# Ventana de analisis estadistico
# ─────────────────────────────────────────────────────────────────
class VentanaAnalisis(QDialog):
    COLOR_OK   = QColor("#1B5E20")
    COLOR_FAIL = QColor("#B71C1C")
    COLOR_NA   = QColor("#37474F")

    def __init__(self, analizador: AnalizadorDatos, parent=None):
        super().__init__(parent)
        self.analizador = analizador
        self.setWindowTitle("Analisis de grabacion  -  VT650 Monitor")
        self.resize(1100, 700)
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._tab_resumen(),  "Resumen / Diagnostico")
        tabs.addTab(self._tab_graficos(), "Graficos de parametros")
        lay.addWidget(tabs)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject); lay.addWidget(bb)

    def _tab_resumen(self):
        w = QWidget(); lay = QVBoxLayout(w)
        res = self.analizador.resultados; cfg = self.analizador.config
        info = QLabel(
            f"<b>Operador:</b> {cfg.get('operador','--')} &nbsp;&nbsp;"
            f"<b>Equipo:</b> {cfg.get('equipo_id','--')} &nbsp;&nbsp;"
            f"<b>Modelo:</b> {cfg.get('modelo','--')} &nbsp;&nbsp;"
            f"<b>Ciclos:</b> {self.analizador.n_ciclos} &nbsp;&nbsp;"
            f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        info.setStyleSheet("background:#1A237E;color:#E8EAF6;padding:6px;border-radius:4px;")
        lay.addWidget(info)
        ref_txt = (
            f"BPM={cfg.get('bpm','--')} | Vt={cfg.get('vt','--')} mL | "
            f"Ti={cfg.get('ti','--')} s | PEEP={cfg.get('peep','--')} cmH2O | "
            f"PIP={cfg.get('pip','--')} cmH2O | I:E=1:{cfg.get('ie','--')} | "
            f"MV={cfg.get('mv','--')} L/min | FIO2={cfg.get('fio2','--')}%")
        lbl_ref = QLabel(f"Referencia: {ref_txt}")
        lbl_ref.setStyleSheet("color:#B0BEC5;font-size:11px;padding:4px;")
        lbl_ref.setWordWrap(True); lay.addWidget(lbl_ref)
        cols = ["Parametro","Unidad","N ciclos","Media","Std","Min","Max",
                "CV%","Oscil%","Referencia","Error%","Tolerancia","Cumple"]
        tabla = QTableWidget(len(res), len(cols))
        tabla.setHorizontalHeaderLabels(cols)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        tabla.setAlternatingRowColors(True)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setStyleSheet("QTableWidget{background:#1E1E1E;color:#ECEFF1;}"
                            "QHeaderView::section{background:#263238;color:#80CBC4;}")
        for row, (key, r) in enumerate(res.items()):
            cumple = r['cumple']
            bg = self.COLOR_OK if cumple is True else (
                 self.COLOR_FAIL if cumple is False else self.COLOR_NA)
            for col, txt in enumerate([
                r['label'], r['unidad'], r['n'],
                f"{r['media']:.2f}", f"{r['std']:.2f}",
                f"{r['min']:.2f}", f"{r['max']:.2f}",
                f"{r['cv_pct']:.1f}%", f"{r['oscil_pct']:.1f}%",
                f"{r['ref']:.2f}" if r['ref'] is not None else "--",
                f"{r['error_pct']:+.1f}%" if r['error_pct'] is not None else "--",
                r['tol_desc'] or "--",
                "OK" if cumple is True else ("FALLA" if cumple is False else "--"),
            ]):
                it = QTableWidgetItem(str(txt))
                it.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                it.setBackground(bg); tabla.setItem(row, col, it)
        lay.addWidget(tabla)
        total    = sum(1 for r in res.values() if r['cumple'] is not None)
        ok_count = sum(1 for r in res.values() if r['cumple'] is True)
        fuera    = [r['label'] for r in res.values() if r['cumple'] is False]
        if total > 0:
            pct_ok = ok_count / total * 100
            if pct_ok == 100:
                msg = f"DENTRO DE NORMATIVA  -  {ok_count}/{total} parametros OK  ({pct_ok:.0f}%)"
                st  = "background:#1B5E20;color:#C8E6C9;font-size:14px;font-weight:bold;padding:8px;border-radius:4px;"
            else:
                msg = (f"FUERA DE NORMATIVA  -  {ok_count}/{total} OK  ({pct_ok:.0f}%) | "
                       f"Fuera: {', '.join(fuera)}")
                st  = "background:#B71C1C;color:#FFCDD2;font-size:14px;font-weight:bold;padding:8px;border-radius:4px;"
            lbl = QLabel(msg); lbl.setStyleSheet(st); lbl.setWordWrap(True)
            lay.addWidget(lbl)
        return w

    def _tab_graficos(self):
        w = QWidget(); lay = QVBoxLayout(w)
        pg.setConfigOption('background','#1e1e1e'); pg.setConfigOption('foreground','#cccccc')
        series = [
            ('BPM_b', '#FB8C00','BPM'),
            ('Vti',   '#00ACC1','Vt inspirado (mL)'),
            ('PIP_b', '#E53935','PIP (cmH2O)'),
            ('PEEP_b','#43A047','PEEP (cmH2O)'),
            ('MV',    '#9C27B0','VM (L/min)'),
            ('Ti',    '#81C784','Ti (s)'),
        ]
        res    = self.analizador.resultados
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        inner  = QWidget(); inner_lay = QVBoxLayout(inner)
        for key, color, titulo in series:
            r = res.get(key)
            if r is None or not r['serie']: continue
            x  = list(range(1, len(r['serie']) + 1))
            y  = r['serie']
            pw = pg.PlotWidget(title=titulo); pw.setFixedHeight(180)
            pw.showGrid(x=True, y=True, alpha=0.3)
            pw.setLabel('left', titulo); pw.setLabel('bottom', "Ciclo #")
            pw.getViewBox().setMouseEnabled(x=False, y=True)
            pw.plot(x, y, pen=pg.mkPen(color, width=1.5),
                    symbol='o', symbolSize=4, symbolBrush=color)
            ref = r.get('ref')
            if ref is not None:
                pw.addLine(y=ref, pen=pg.mkPen('#FFFFFF', width=1, style=Qt.DashLine))
            pw.addLine(y=r['media'], pen=pg.mkPen(color, width=1, style=Qt.DotLine))
            inner_lay.addWidget(pw)
        scroll.setWidget(inner); lay.addWidget(scroll)
        return w


# ─────────────────────────────────────────────────────────────────
# Ventana principal
# ─────────────────────────────────────────────────────────────────
class VentanaPrincipal(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VT650 Monitor  v3.0"); self.resize(1200, 820)
        self.vt650     = None
        self.grabacion = GrabacionManager()
        self._config_grabacion: dict = {}
        self._ts_buf   = __import__('collections').deque(maxlen=BUFFER)
        self._flow_buf = __import__('collections').deque(maxlen=BUFFER)
        self._pres_buf = __import__('collections').deque(maxlen=BUFFER)
        self._n = 0
        self._params = {
            'flow':None,'pres':None,
            'Ti':None,'Te':None,'TiH':None,'TeH':None,
            'IE':None,'BPM_b':None,'PIF':None,'PEF':None,
            'Vti':None,'Vte':None,'MV':None,
            'PIP_b':None,'IPP':None,'MAP':None,'PEEP_b':None,
            'O2':None,'CMPL':None,'VOL':None,
            'temp':None,'hum':None,'prba':None,'gas':'--','flcm':'--'
        }
        self._brp_pendiente  = {}
        self._slow_pendiente = {}
        self._cycle_state    = "exp"
        self._insp_count     = 0
        self._ventana_seg    = 6
        self._modo_vista     = "ambos"
        self._sw_curr_x=[]; self._sw_curr_f=[]; self._sw_curr_p=[]
        self._sw_prev_x=[]; self._sw_prev_f=[]; self._sw_prev_p=[]
        self._sw_last_x = -1.0; self._sw_cur_x = 0.0
        self.grabacion.timeout_signal.connect(self._on_grabacion_timeout)
        self._construir_ui()

    # ─────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────
    def _construir_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setSpacing(4)

        barra = QHBoxLayout()
        self.combo_port = QComboBox(); self.combo_port.setMinimumWidth(100)
        self._actualizar_puertos()
        barra.addWidget(QLabel("Puerto:")); barra.addWidget(self.combo_port)
        b = QPushButton("Refresh"); b.setFixedWidth(58)
        b.clicked.connect(self._actualizar_puertos); barra.addWidget(b)
        self.btn_conectar = QPushButton("Conectar"); self.btn_conectar.setFixedWidth(100)
        self.btn_conectar.clicked.connect(self._toggle_conexion); barra.addWidget(self.btn_conectar)
        barra.addSpacing(12)
        self.btn_grab = QPushButton("Grabar"); self.btn_grab.setFixedWidth(90)
        self.btn_grab.setEnabled(False); self.btn_grab.clicked.connect(self._iniciar_grabacion)
        barra.addWidget(self.btn_grab)
        self.btn_stop = QPushButton("Detener"); self.btn_stop.setFixedWidth(90)
        self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self._detener_grabacion)
        barra.addWidget(self.btn_stop)
        self.lbl_rec = QLabel("REC")
        self.lbl_rec.setStyleSheet("color:#F44336;font-weight:bold;")
        self.lbl_rec.setVisible(False); barra.addWidget(self.lbl_rec)
        self.lbl_dur = QLabel(""); self.lbl_dur.setFixedWidth(55)
        self.lbl_dur.setStyleSheet("color:#80CBC4;font-family:monospace;")
        barra.addWidget(self.lbl_dur)
        barra.addStretch()
        barra.addWidget(QLabel("Modo:"))
        self.btn_pag_g = QPushButton("Graficos"); self.btn_pag_g.setFixedWidth(80)
        self.btn_pag_d = QPushButton("Datos");    self.btn_pag_d.setFixedWidth(80)
        for b2 in [self.btn_pag_g, self.btn_pag_d]:
            b2.setCheckable(True); barra.addWidget(b2)
        self.btn_pag_g.setChecked(True)
        self.btn_pag_g.clicked.connect(lambda: self._cambiar_pagina(0))
        self.btn_pag_d.clicked.connect(lambda: self._cambiar_pagina(1))
        barra.addSpacing(16)
        self.lbl_hz = QLabel("-- Hz"); barra.addWidget(self.lbl_hz)
        root.addLayout(barra)

        badge = QHBoxLayout()
        self.lbl_gas_badge  = QLabel("GAS: --")
        self.lbl_flcm_badge = QLabel("MODO: --")
        self.lbl_ciclo = QLabel("ciclo")
        self.lbl_ciclo.setStyleSheet(
            "background:#1B5E20;color:#A5D6A7;padding:3px 8px;border-radius:4px;font-size:11px;")
        self.lbl_ciclo.setVisible(False)
        self._ciclo_timer = QTimer(); self._ciclo_timer.setSingleShot(True)
        self._ciclo_timer.timeout.connect(lambda: self.lbl_ciclo.setVisible(False))
        for lbl in [self.lbl_gas_badge, self.lbl_flcm_badge]:
            lbl.setStyleSheet("background:#263238;color:#80CBC4;padding:3px 10px;"
                              "border-radius:4px;font-size:11px;")
        badge.addWidget(self.lbl_gas_badge); badge.addSpacing(8)
        badge.addWidget(self.lbl_flcm_badge); badge.addSpacing(8)
        badge.addWidget(self.lbl_ciclo); badge.addStretch()
        root.addLayout(badge)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._construir_pagina_graficos())
        self.stack.addWidget(self._construir_pagina_datos())
        root.addWidget(self.stack)

        self._timer = QTimer(); self._timer.setInterval(33)
        self._timer.timeout.connect(self._refrescar_graficos); self._timer.start()
        self._timer_dur_ui = QTimer(); self._timer_dur_ui.setInterval(1000)
        self._timer_dur_ui.timeout.connect(self._actualizar_lbl_dur)

    # ─────────────────────────────────────────────────────────────
    # Pagina graficos
    # ─────────────────────────────────────────────────────────────
    def _construir_pagina_graficos(self):
        pag = QWidget(); lay = QVBoxLayout(pag); lay.setSpacing(4)
        grupo = QGroupBox("Parametros del ciclo anterior  (actualizados al inicio de cada inspiracion)")
        grid  = QGridLayout(grupo); grid.setSpacing(10)
        fv = QFont("Consolas", 20); fl = QFont(); fl.setPointSize(9)
        def met(titulo, color):
            t = QLabel(titulo); t.setFont(fl); t.setAlignment(Qt.AlignCenter)
            v = QLabel("---");  v.setFont(fv); v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f"color:{color}"); return t, v
        t, self.g_flow = met("Flujo (L/min)",   "#2979FF"); grid.addWidget(t,0,0); grid.addWidget(self.g_flow,1,0)
        t, self.g_pres = met("Presion (cmH2O)", "#E53935"); grid.addWidget(t,0,1); grid.addWidget(self.g_pres,1,1)
        t, self.g_pip  = met("PIP (cmH2O)",     "#E53935"); grid.addWidget(t,0,2); grid.addWidget(self.g_pip, 1,2)
        t, self.g_peep = met("PEEP (cmH2O)",    "#43A047"); grid.addWidget(t,0,3); grid.addWidget(self.g_peep,1,3)
        t, self.g_bpm  = met("BPM",             "#FB8C00"); grid.addWidget(t,0,4); grid.addWidget(self.g_bpm, 1,4)
        t, self.g_temp = met("Temp (C)",         "#00BCD4"); grid.addWidget(t,0,5); grid.addWidget(self.g_temp,1,5)
        t, self.g_hum  = met("Hum (%)",          "#9C27B0"); grid.addWidget(t,0,6); grid.addWidget(self.g_hum, 1,6)
        lay.addWidget(grupo)
        ctrl = QHBoxLayout(); ctrl.addWidget(QLabel("Vista:"))
        self.btn_va = QPushButton("Flujo+Pres"); self.btn_vf = QPushButton("Solo Flujo")
        self.btn_vp = QPushButton("Solo Pres")
        for b in [self.btn_va, self.btn_vf, self.btn_vp]:
            b.setFixedWidth(90); b.setCheckable(True); ctrl.addWidget(b)
        self.btn_va.setChecked(True)
        self.btn_va.clicked.connect(lambda: self._cambiar_vista("ambos"))
        self.btn_vf.clicked.connect(lambda: self._cambiar_vista("solo_flujo"))
        self.btn_vp.clicked.connect(lambda: self._cambiar_vista("solo_presion"))
        ctrl.addSpacing(20); ctrl.addWidget(QLabel("Ventana:"))
        self.btn_6s = QPushButton("6s"); self.btn_12s = QPushButton("12s")
        self.btn_24s = QPushButton("24s")
        for b in [self.btn_6s, self.btn_12s, self.btn_24s]:
            b.setFixedWidth(44); b.setCheckable(True); ctrl.addWidget(b)
        self.btn_6s.setChecked(True)
        self.btn_6s.clicked.connect(lambda:  self._cambiar_ventana(6))
        self.btn_12s.clicked.connect(lambda: self._cambiar_ventana(12))
        self.btn_24s.clicked.connect(lambda: self._cambiar_ventana(24))
        self.lbl_ven = QLabel("6 s"); self.lbl_ven.setFixedWidth(32)
        self.lbl_ven.setStyleSheet("color:#888;font-size:11px")
        ctrl.addWidget(self.lbl_ven); ctrl.addStretch()
        lay.addLayout(ctrl)
        pg.setConfigOption('background','#1e1e1e'); pg.setConfigOption('foreground','#cccccc')
        self.plot_flow = pg.PlotWidget(title="Flujo (L/min)")
        self.plot_pres = pg.PlotWidget(title="Presion (cmH2O)")
        self.plot_flow.setYRange(-60, 60, padding=0)
        self.plot_pres.setYRange(-5,  35, padding=0)
        for plot, u in [(self.plot_flow,"L/min"), (self.plot_pres,"cmH2O")]:
            plot.setLabel('left', u); plot.setLabel('bottom', "Tiempo (s)")
            plot.showGrid(x=True, y=True, alpha=0.3)
            vb = plot.getViewBox(); vb.setMouseEnabled(x=False, y=False); vb.setMenuEnabled(False)
        self.plot_flow.addLine(y=0, pen=pg.mkPen('#444', width=1, style=Qt.DashLine))
        self._aplicar_rango_x()
        self.curve_flow_curr = self.plot_flow.plot(pen=pg.mkPen('#2979FF', width=1.5))
        self.curve_flow_prev = self.plot_flow.plot(pen=pg.mkPen('#0D3A7A', width=1.0))
        self.curve_pres_curr = self.plot_pres.plot(pen=pg.mkPen('#E53935', width=1.5))
        self.curve_pres_prev = self.plot_pres.plot(pen=pg.mkPen('#6A1010', width=1.0))
        cur_pen = pg.mkPen('#ffffff', width=2)
        self._cur_flow = pg.InfiniteLine(angle=90, movable=False, pen=cur_pen)
        self._cur_pres = pg.InfiniteLine(angle=90, movable=False, pen=cur_pen)
        self.plot_flow.addItem(self._cur_flow); self.plot_pres.addItem(self._cur_pres)
        filtro = FiltroRueda(self._on_rueda)
        self.plot_flow.installEventFilter(filtro)
        self.plot_pres.installEventFilter(filtro)
        self._filtro_rueda = filtro
        lay.addWidget(self.plot_flow, stretch=2)
        lay.addWidget(self.plot_pres, stretch=2)
        return pag

    # ─────────────────────────────────────────────────────────────
    # Pagina datos
    # ─────────────────────────────────────────────────────────────
    def _construir_pagina_datos(self):
        pag = QWidget(); pag.setStyleSheet("background:#121212;")
        lay = QVBoxLayout(pag); lay.setSpacing(8)
        hdr = QHBoxLayout()
        self.d_gas_lbl  = QLabel("GAS: --"); self.d_flcm_lbl = QLabel("MODO: --")
        for lbl in [self.d_gas_lbl, self.d_flcm_lbl]:
            lbl.setStyleSheet("background:#1A237E;color:#E8EAF6;padding:6px 16px;"
                              "border-radius:6px;font-size:13px;font-weight:bold;")
        hdr.addWidget(self.d_gas_lbl); hdr.addSpacing(12)
        hdr.addWidget(self.d_flcm_lbl); hdr.addStretch()
        lay.addLayout(hdr)
        grid = QGridLayout(); grid.setSpacing(6); self._casillas = {}
        def fila(params, row):
            for col, (nombre, unidad, color) in enumerate(params):
                frame, lbl_val = self._crear_casilla(nombre, unidad, color)
                grid.addWidget(frame, row, col); self._casillas[nombre] = lbl_val
        fila([("FLUJO","L/min","#2979FF"),("PRESION","cmH2O","#E53935"),
              ("VOLUMEN","mL","#00ACC1"),("TEMP","C","#00BCD4"),
              ("HUMEDAD","%","#9C27B0"),("P.BARO","","#607D8B")], 0)
        fila([("Ti","s","#81C784"),("Te","s","#81C784"),
              ("TiH","s","#A5D6A7"),("TeH","s","#A5D6A7"),
              ("I:E","","#FFD54F"),("BPM","br/min","#FB8C00")], 1)
        fila([("PIF","L/min","#64B5F6"),("PEF","L/min","#64B5F6"),
              ("Vti","mL","#4DB6AC"),("Vte","mL","#4DB6AC"),
              ("MV","L/min","#80CBC4"),("O2","%","#B0BEC5")], 2)
        fila([("PIP","cmH2O","#EF9A9A"),("IPP","cmH2O","#FFAB91"),
              ("MAP","cmH2O","#FFCC80"),("PEEP","cmH2O","#A5D6A7"),
              ("CMPL","mL/cmH2O","#CE93D8")], 3)
        lay.addLayout(grid); lay.addStretch()
        return pag

    def _crear_casilla(self, nombre, unidad, color):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background:#1E1E1E;border:1px solid #333;border-radius:6px;}")
        vlay = QVBoxLayout(frame); vlay.setSpacing(2); vlay.setContentsMargins(8,6,8,6)
        ln = QLabel(nombre); ln.setAlignment(Qt.AlignCenter)
        ln.setStyleSheet("color:#888;font-size:11px;border:none;background:none;")
        lv = QLabel("---"); lv.setAlignment(Qt.AlignCenter); lv.setFont(QFont("Consolas", 22))
        lv.setStyleSheet(f"color:{color};border:none;background:none;")
        lu = QLabel(unidad); lu.setAlignment(Qt.AlignCenter)
        lu.setStyleSheet("color:#555;font-size:10px;border:none;background:none;")
        vlay.addWidget(ln); vlay.addWidget(lv); vlay.addWidget(lu)
        return frame, lv

    def _cambiar_pagina(self, idx):
        self.stack.setCurrentIndex(idx)
        self.btn_pag_g.setChecked(idx == 0); self.btn_pag_d.setChecked(idx == 1)

    # ─────────────────────────────────────────────────────────────
    # Deteccion de ciclo
    # ─────────────────────────────────────────────────────────────
    def _detectar_ciclo(self, flow: float) -> bool:
        nuevo = False
        if self._cycle_state == "exp":
            if flow > INSP_THRESH:
                self._insp_count += 1
                if self._insp_count >= INSP_CONFIRM:
                    self._cycle_state = "insp"; self._insp_count = 0; nuevo = True
            else:
                self._insp_count = 0
        elif self._cycle_state == "insp":
            if flow < EXP_THRESH:
                self._cycle_state = "exp"; self._insp_count = 0
        return nuevo

    def _on_ciclo_nuevo(self):
        self.lbl_ciclo.setVisible(True); self._ciclo_timer.start(400)
        if self._brp_pendiente:
            self._aplicar_brp_pantalla(self._brp_pendiente.copy())
            if self.grabacion.activa:
                self.grabacion.registrar_ciclo(datetime.now(), self._params)
            self._brp_pendiente = {}
        if self._slow_pendiente:
            self._aplicar_slow_pantalla(self._slow_pendiente.copy())
            self._slow_pendiente = {}

    # ─────────────────────────────────────────────────────────────
    # Actualizacion pantalla
    # ─────────────────────────────────────────────────────────────
    def _aplicar_brp_pantalla(self, brp: dict):
        self._params.update(brp)
        def fmt(k, d=1):
            v = brp.get(k)
            if v is None: return "--"
            try: return f"{float(v):.{d}f}"
            except: return str(v)
        if 'PIP_b'  in brp: self.g_pip.setText(fmt('PIP_b',  1))
        if 'PEEP_b' in brp: self.g_peep.setText(fmt('PEEP_b', 1))
        if 'BPM_b'  in brp: self.g_bpm.setText(str(brp['BPM_b']))
        if 'VOL'    in brp: self._casillas["VOLUMEN"].setText(fmt('VOL',   2))
        if 'Ti'     in brp: self._casillas["Ti"].setText(fmt('Ti',      3))
        if 'Te'     in brp: self._casillas["Te"].setText(fmt('Te',      3))
        if 'TiH'    in brp: self._casillas["TiH"].setText(fmt('TiH',    3))
        if 'TeH'    in brp: self._casillas["TeH"].setText(fmt('TeH',    3))
        if 'IE'     in brp:
            ie = str(brp['IE']).strip()
            self._casillas["I:E"].setText(ie if ie else "--")
        if 'BPM_b'  in brp: self._casillas["BPM"].setText(str(brp['BPM_b']))
        if 'PIF'    in brp: self._casillas["PIF"].setText(fmt('PIF',    3))
        if 'PEF'    in brp: self._casillas["PEF"].setText(fmt('PEF',    3))
        if 'Vti'    in brp: self._casillas["Vti"].setText(fmt('Vti',    2))
        if 'Vte'    in brp: self._casillas["Vte"].setText(fmt('Vte',    2))
        if 'MV'     in brp: self._casillas["MV"].setText(fmt('MV',     3))
        if 'PIP_b'  in brp: self._casillas["PIP"].setText(fmt('PIP_b',  2))
        if 'IPP'    in brp: self._casillas["IPP"].setText(fmt('IPP',    2))
        if 'MAP'    in brp: self._casillas["MAP"].setText(fmt('MAP',    2))
        if 'PEEP_b' in brp: self._casillas["PEEP"].setText(fmt('PEEP_b',2))
        if 'O2'     in brp: self._casillas["O2"].setText(fmt('O2',     2))
        if 'CMPL'   in brp: self._casillas["CMPL"].setText(fmt('CMPL',  2))

    def _aplicar_slow_pantalla(self, env: dict):
        self._params.update(env)
        temp = env.get('temp'); hum = env.get('hum'); prba = env.get('prba')
        gas  = env.get('gas', '--'); flcm = env.get('flcm', '--')
        if temp is not None:
            self.g_temp.setText(f"{temp:.1f}"); self._casillas["TEMP"].setText(f"{temp:.1f}")
        if hum is not None:
            self.g_hum.setText(f"{hum:.1f}");   self._casillas["HUMEDAD"].setText(f"{hum:.1f}")
        if prba is not None:
            self._casillas["P.BARO"].setText(f"{prba:.2f}")
        gas_txt  = GAS_DESC.get(gas,  gas)
        flcm_txt = FLCM_DESC.get(flcm, flcm)
        self.lbl_gas_badge.setText(f"GAS: {gas}  -  {gas_txt}")
        self.lbl_flcm_badge.setText(f"MODO: {flcm}  -  {flcm_txt}")
        self.d_gas_lbl.setText(f"GAS: {gas}  -  {gas_txt}")
        self.d_flcm_lbl.setText(f"MODO: {flcm}  -  {flcm_txt}")

    # ─────────────────────────────────────────────────────────────
    # Slots
    # ─────────────────────────────────────────────────────────────
    def _on_dato(self, flow, pres):
        now = datetime.now()
        self._ts_buf.append(now); self._flow_buf.append(flow)
        self._pres_buf.append(pres); self._n += 1
        if flow is not None and self._detectar_ciclo(flow):
            self._on_ciclo_nuevo()
        self._sw_add(flow, pres)
        self._params['flow'] = flow; self._params['pres'] = pres
        if flow is not None:
            self.g_flow.setText(f"{flow:+.2f}"); self._casillas["FLUJO"].setText(f"{flow:+.2f}")
        if pres is not None:
            self.g_pres.setText(f"{pres:.2f}"); self._casillas["PRESION"].setText(f"{pres:.2f}")
        if self.grabacion.activa:
            self.grabacion.registrar_muestra(now, flow, pres, self._params)

    def _on_datos_brp(self, brp: dict):
        self._brp_pendiente.update(brp)

    def _on_datos_lentos(self, env: dict):
        self._slow_pendiente.update(env)

    def _on_error(self, msg: str):
        self.statusBar().showMessage(f"Error: {msg}"); self._desconectar()

    # ─────────────────────────────────────────────────────────────
    # Barrido ECG
    # ─────────────────────────────────────────────────────────────
    def _sw_reset(self):
        self._sw_curr_x = []; self._sw_curr_f = []; self._sw_curr_p = []
        self._sw_prev_x = []; self._sw_prev_f = []; self._sw_prev_p = []
        self._sw_last_x = -1.0; self._sw_cur_x = 0.0

    def _sw_add(self, flow, pres):
        t_cycle = datetime.now().timestamp() % self._ventana_seg
        if self._sw_last_x >= 0 and t_cycle < self._sw_last_x - self._ventana_seg * 0.1:
            self._sw_prev_x = self._sw_curr_x[:]; self._sw_prev_f = self._sw_curr_f[:]
            self._sw_prev_p = self._sw_curr_p[:]
            self._sw_curr_x = []; self._sw_curr_f = []; self._sw_curr_p = []
        self._sw_curr_x.append(t_cycle)
        self._sw_curr_f.append(flow if flow is not None else np.nan)
        self._sw_curr_p.append(pres if pres is not None else np.nan)
        self._sw_last_x = t_cycle; self._sw_cur_x = t_cycle
        if len(self._sw_curr_x) > MAX_SW:
            self._sw_curr_x = self._sw_curr_x[-MAX_SW:]
            self._sw_curr_f = self._sw_curr_f[-MAX_SW:]
            self._sw_curr_p = self._sw_curr_p[-MAX_SW:]

    def _on_rueda(self, delta):
        paso  = 1 if delta < 0 else -1
        nueva = max(VEN_MIN, min(VEN_MAX, self._ventana_seg + paso))
        if nueva != self._ventana_seg: self._cambiar_ventana(nueva)

    def _actualizar_botones_ventana(self):
        v = self._ventana_seg
        self.btn_6s.setChecked(v == 6); self.btn_12s.setChecked(v == 12)
        self.btn_24s.setChecked(v == 24); self.lbl_ven.setText(f"{v} s")

    def _cambiar_ventana(self, seg):
        self._ventana_seg = seg; self._sw_reset()
        self._aplicar_rango_x(); self._actualizar_botones_ventana()

    def _aplicar_rango_x(self):
        for plot in [self.plot_flow, self.plot_pres]:
            plot.setXRange(0, self._ventana_seg, padding=0)
        self.plot_flow.setYRange(-60, 60, padding=0)
        self.plot_pres.setYRange(-5,  35, padding=0)

    def _cambiar_vista(self, modo):
        self._modo_vista = modo
        self.btn_va.setChecked(modo == "ambos")
        self.btn_vf.setChecked(modo == "solo_flujo")
        self.btn_vp.setChecked(modo == "solo_presion")
        self.plot_flow.setVisible(modo in ("ambos", "solo_flujo"))
        self.plot_pres.setVisible(modo in ("ambos", "solo_presion"))
        if self.vt650: self.vt650.modo_vista = modo

    def _refrescar_graficos(self):
        if self.stack.currentIndex() != 0 or self._n == 0: return
        cur_x = self._sw_cur_x; gap = max(0.3, self._ventana_seg * 0.02)
        xc = np.array(self._sw_curr_x) if self._sw_curr_x else np.array([])
        fc = np.array(self._sw_curr_f) if self._sw_curr_f else np.array([])
        pc = np.array(self._sw_curr_p) if self._sw_curr_p else np.array([])
        if self._sw_prev_x:
            xp = np.array(self._sw_prev_x); fp = np.array(self._sw_prev_f)
            pp = np.array(self._sw_prev_p)
            mask = xp > cur_x + gap; xp = xp[mask]; fp = fp[mask]; pp = pp[mask]
        else: xp = fp = pp = np.array([])
        if self.plot_flow.isVisible():
            self.curve_flow_curr.setData(xc, fc); self.curve_flow_prev.setData(xp, fp)
            self._cur_flow.setValue(cur_x)
        if self.plot_pres.isVisible():
            self.curve_pres_curr.setData(xc, pc); self.curve_pres_prev.setData(xp, pp)
            self._cur_pres.setValue(cur_x)
        self.plot_flow.setXRange(0, self._ventana_seg, padding=0)
        self.plot_pres.setXRange(0, self._ventana_seg, padding=0)
        self.plot_flow.setYRange(-60, 60, padding=0)
        self.plot_pres.setYRange(-5,  35, padding=0)

    # ─────────────────────────────────────────────────────────────
    # Conexion
    # ─────────────────────────────────────────────────────────────
    def _actualizar_puertos(self):
        self.combo_port.clear()
        puertos = [p.device for p in serial.tools.list_ports.comports()]
        self.combo_port.addItems(puertos if puertos else ["(sin puertos)"])

    def _toggle_conexion(self):
        if self.vt650 is None: self._conectar()
        else: self._desconectar()

    def _conectar(self):
        port = self.combo_port.currentText()
        if not port or port == "(sin puertos)":
            QMessageBox.warning(self, "Error", "Selecciona un puerto COM."); return
        try:
            self.vt650 = VT650(port); self.vt650.modo_vista = self._modo_vista
            self.vt650.signals.nuevo_dato.connect(self._on_dato)
            self.vt650.signals.datos_brp.connect(self._on_datos_brp)
            self.vt650.signals.datos_lentos.connect(self._on_datos_lentos)
            self.vt650.signals.error_serial.connect(self._on_error)
            self.vt650.signals.hz_actual.connect(lambda hz: self.lbl_hz.setText(f"{hz} Hz"))
            self.vt650.conectar(); self.vt650.iniciar_polling()
            self.btn_conectar.setText("Desconectar"); self.btn_grab.setEnabled(True)
            modo = "921600 UARTFAST" if self.vt650.uartfast_activo else "115200"
            self.statusBar().showMessage(f"Conectado {port}  -  {modo}")
        except Exception as e:
            self.vt650 = None; QMessageBox.critical(self, "Error de conexion", str(e))

    def _desconectar(self):
        if self.grabacion.activa: self._detener_grabacion()
        if self.vt650: self.vt650.desconectar(); self.vt650 = None
        self.btn_conectar.setText("Conectar"); self.btn_grab.setEnabled(False)
        self.btn_stop.setEnabled(False); self.lbl_hz.setText("-- Hz")
        self.lbl_ciclo.setVisible(False); self.statusBar().showMessage("Desconectado")

    # ─────────────────────────────────────────────────────────────
    # Grabacion
    # ─────────────────────────────────────────────────────────────
    def _iniciar_grabacion(self):
        dlg = DialogConfigGrabacion(self)
        if dlg.exec() != QDialog.Accepted: return
        cfg = dlg.get_config(); self._config_grabacion = cfg
        ruta_dir, _ = QFileDialog.getSaveFileName(
            self, "Prefijo de archivos de grabacion",
            f"vt650_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "Prefijo (*)")
        if not ruta_dir: return
        if ruta_dir.endswith(".csv"): ruta_dir = ruta_dir[:-4]
        self.grabacion.iniciar(ruta_dir, cfg.get('duracion_seg', 0))
        self.btn_grab.setEnabled(False); self.btn_stop.setEnabled(True)
        self.lbl_rec.setVisible(True); self._timer_dur_ui.start()
        dur = cfg.get('duracion_seg', 0)
        dur_txt = f"{dur}s" if dur > 0 else "manual"
        self.statusBar().showMessage(
            f"Grabando -> {ruta_dir}_ondas.csv  |  _ciclos.csv  [{dur_txt}]")

    def _detener_grabacion(self):
        self._timer_dur_ui.stop()
        ruta_base = self.grabacion.detener()
        self.btn_grab.setEnabled(True); self.btn_stop.setEnabled(False)
        self.lbl_rec.setVisible(False); self.lbl_dur.setText("")
        self.statusBar().showMessage(f"Grabacion detenida -> {ruta_base}_ciclos.csv")
        self._abrir_analisis(ruta_base + "_ciclos.csv")

    def _on_grabacion_timeout(self):
        self._detener_grabacion()

    def _actualizar_lbl_dur(self):
        if self.grabacion.activa:
            s = int(self.grabacion.duracion_actual)
            self.lbl_dur.setText(f"{s//60:02d}:{s%60:02d}")

    def _abrir_analisis(self, ruta_ciclos: str):
        try:
            analizador = AnalizadorDatos(ruta_ciclos, self._config_grabacion)
            analizador.cargar()
            if analizador.n_ciclos < 3:
                QMessageBox.warning(self, "Analisis",
                    f"Solo {analizador.n_ciclos} ciclos grabados. "
                    "Se necesitan al menos 3 para analizar."); return
            analizador.analizar()
            dlg_analisis = VentanaAnalisis(analizador, self)
            dlg_analisis.exec()
            resp = QMessageBox.question(
                self, "Informe tecnico",
                "Desea generar el informe tecnico en PDF?",
                QMessageBox.Yes | QMessageBox.No)
            if resp == QMessageBox.Yes:
                gen     = GeneradorInforme(analizador, self._params)
                dlg_inf = DialogoInforme(gen, self)
                dlg_inf.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error en analisis", str(e))

    def closeEvent(self, event):
        self._desconectar(); event.accept()
