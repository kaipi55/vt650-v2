import csv
import threading
import time
import math
from datetime import datetime
from collections import deque

import serial
import numpy as np
from PySide6.QtCore import QTimer, Signal, QObject, QEvent

from config import NORMA


# ─────────────────────────────────────────────────────────────────
# Senales Qt
# ─────────────────────────────────────────────────────────────────
class Signals(QObject):
    nuevo_dato   = Signal(object, object)
    datos_brp    = Signal(object)
    datos_lentos = Signal(object)
    error_serial = Signal(str)
    hz_actual    = Signal(float)


# ─────────────────────────────────────────────────────────────────
# Driver VT650
# ─────────────────────────────────────────────────────────────────
class VT650:
    def __init__(self, port):
        self.port = port; self.ser = None; self.running = False
        self.signals = Signals()
        self._thread_rapido = self._thread_medio = self._thread_lento = None
        self._hz_buf = deque(maxlen=20); self._lock = threading.Lock()
        self.uartfast_activo = False; self.modo_vista = "ambos"

    def conectar(self):
        self.ser = serial.Serial(
            port=self.port, baudrate=115200, bytesize=8,
            parity='N', stopbits=1, rtscts=True,
            timeout=1.0, write_timeout=0.5)
        time.sleep(0.3)
        self._cmd_raw("REMOTE")
        self._cmd_raw("MEAS=AW")
        self._cmd_raw("UVOL=ML")      # Volumen en mL
        self._cmd_raw("UFLAW=LM")     # Flujo en L/min
        self._cmd_raw("UPRAW=CMH2O")  # Presion en cmH2O
        self._cmd_raw("UTMP=C")       # Temperatura en Celsius
        self.uartfast_activo = self._activar_uartfast()

    def _activar_uartfast(self):
        try:
            self.ser.reset_input_buffer(); self.ser.write(b"UARTFAST=TRUE\r")
            time.sleep(0.5); self.ser.read(64); self.ser.close(); time.sleep(0.2)
            self.ser = serial.Serial(
                port=self.port, baudrate=921600, bytesize=8,
                parity='N', stopbits=1, rtscts=True,
                timeout=3.0, write_timeout=1.0)
            t0 = time.time(); a_count = 0
            while time.time() - t0 < 22:
                b = self.ser.read(1)
                if b == b'A':
                    a_count += 1
                    if a_count >= 3: break
            if a_count < 3: return False
            self.ser.reset_input_buffer(); self.ser.write(b"A")
            t0 = time.time(); ack = b""
            while time.time() - t0 < 3.0:
                b = self.ser.read(1)
                if b: ack += b
                if b == b'*': break
            return b'*' in ack
        except Exception: return False

    def desconectar(self):
        self.running = False
        for t in [self._thread_rapido, self._thread_medio, self._thread_lento]:
            if t: t.join(timeout=3)
        try:
            if self.uartfast_activo:
                self.ser.reset_input_buffer(); self.ser.write(b"UARTFAST=FALSE\r")
                time.sleep(0.5); self.ser.read(64); self.ser.close(); time.sleep(0.2)
                self.ser = serial.Serial(
                    port=self.port, baudrate=115200, bytesize=8,
                    parity='N', stopbits=1, rtscts=True,
                    timeout=2.0, write_timeout=1.0)
                t0 = time.time(); a_count = 0
                while time.time() - t0 < 10:
                    b = self.ser.read(1)
                    if b == b'A':
                        a_count += 1
                        if a_count >= 3: break
                if a_count >= 3:
                    self.ser.reset_input_buffer(); self.ser.write(b"A")
                    t0 = time.time(); ack = b""
                    while time.time() - t0 < 3.0:
                        b = self.ser.read(1)
                        if b: ack += b
                        if b == b'*': break
            self._cmd_raw("LOCAL"); time.sleep(0.1); self.ser.close()
        except Exception:
            try: self.ser.close()
            except: pass

    def _cmd_raw(self, cmd):
        self.ser.reset_input_buffer(); self.ser.write((cmd + "\r").encode())
        buf = b""; t0 = time.time()
        while time.time() - t0 < 0.5:
            b = self.ser.read(1)
            if b in (b'\r', b'\n'): break
            buf += b
        return buf.decode("ascii", errors="ignore").strip()

    def _query_float(self, cmd):
        self.ser.reset_input_buffer(); self.ser.write((cmd + "\r").encode())
        buf = b""; t0 = time.time()
        while time.time() - t0 < 0.4:
            b = self.ser.read(1)
            if not b: break
            if b in (b'\r', b'\n'):
                if buf: break
            else: buf += b
        try: return float(buf.decode("ascii", errors="ignore").strip())
        except ValueError: return None

    def _query_brp(self):
        self.ser.reset_input_buffer(); self.ser.write(b"BRP\r")
        lines = []; buf = b""; t0 = time.time()
        while time.time() - t0 < 2.0 and len(lines) < 4:
            b = self.ser.read(1)
            if not b: continue
            if b in (b'\r', b'\n'):
                line = buf.decode("ascii", errors="ignore").strip()
                if line and not line.startswith("!"): lines.append(line)
                buf = b""
            else: buf += b
        return lines

    def _safe_float(self, value):
        try: return float(str(value).strip())
        except: return None

    def _parse_brp(self, lines):
        r = {}
        try:
            if len(lines) >= 1:
                p = [x.strip() for x in lines[0].split(',')]
                keys = ['Ti','Te','TiH','TeH','IE','BPM_b']
                for i, k in enumerate(keys):
                    if i < len(p):
                        r[k] = p[i] if k == 'IE' else self._safe_float(p[i])
            if len(lines) >= 2:
                p = [x.strip() for x in lines[1].split(',')]
                keys = ['PIF','PEF','Vti','Vte','MV']
                for i, k in enumerate(keys):
                    if i < len(p): r[k] = self._safe_float(p[i])
            if len(lines) >= 3:
                p = [x.strip() for x in lines[2].split(',')]
                keys = ['PIP_b','IPP','MAP','PEEP_b']
                for i, k in enumerate(keys):
                    if i < len(p): r[k] = self._safe_float(p[i])
            if len(lines) >= 4:
                p = [x.strip() for x in lines[3].split(',')]
                keys = ['O2','CMPL']
                for i, k in enumerate(keys):
                    if i < len(p): r[k] = self._safe_float(p[i])
        except Exception as e:
            print("BRP parse error:", e)

        # ── FIX: con UVOL=ML el dispositivo reporta MV en mL/min.
        #         Si el valor es > 100 claramente esta en mL/min → convertir a L/min.
        if 'MV' in r and r['MV'] is not None and r['MV'] > 100:
            r['MV'] = r['MV'] / 1000.0

        return r

    def iniciar_polling(self):
        self.running = True
        self._thread_rapido = threading.Thread(target=self._loop_rapido, daemon=True)
        self._thread_medio  = threading.Thread(target=self._loop_medio,  daemon=True)
        self._thread_lento  = threading.Thread(target=self._loop_lento,  daemon=True)
        self._thread_rapido.start(); self._thread_medio.start(); self._thread_lento.start()

    def _loop_rapido(self):
        while self.running:
            t0 = time.perf_counter()
            try:
                with self._lock:
                    modo = self.modo_vista
                    flow = self._query_float("FLAW") if modo != "solo_presion" else None
                    pres = self._query_float("PRAW") if modo != "solo_flujo"   else None
                if flow is not None or pres is not None:
                    self.signals.nuevo_dato.emit(flow, pres)
                dt = time.perf_counter() - t0
                self._hz_buf.append(dt)
                if len(self._hz_buf) == 20:
                    avg = sum(self._hz_buf) / len(self._hz_buf)
                    self.signals.hz_actual.emit(round(1.0 / avg, 1))
            except Exception as e:
                self.signals.error_serial.emit(str(e)); break

    def _loop_medio(self):
        time.sleep(2)
        while self.running:
            try:
                time.sleep(1.5)
                if not self.running: break
                with self._lock:
                    lines = self._query_brp()
                    vol   = self._query_float("VOL")
                brp = self._parse_brp(lines)
                if vol is not None: brp['VOL'] = vol
                if brp: self.signals.datos_brp.emit(brp)
            except: break

    def _loop_lento(self):
        time.sleep(6)
        while self.running:
            try:
                time.sleep(10)
                if not self.running: break
                with self._lock:
                    temp = self._query_float("TEMP")
                    hum  = self._query_float("HUM")
                    prba = self._query_float("PRBA")
                    gas  = self._cmd_raw("QGAS")
                    flcm = self._cmd_raw("QFLCM")
                self.signals.datos_lentos.emit({
                    'temp':temp,'hum':hum,'prba':prba,
                    'gas':gas or '--','flcm':flcm or '--'})
            except: break


# ─────────────────────────────────────────────────────────────────
# Filtro rueda
# ─────────────────────────────────────────────────────────────────
class FiltroRueda(QObject):
    def __init__(self, cb): super().__init__(); self._cb = cb
    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.Wheel:
            self._cb(ev.angleDelta().y()); return True
        return False


# ─────────────────────────────────────────────────────────────────
# Gestor de grabacion
# ─────────────────────────────────────────────────────────────────
class GrabacionManager(QObject):
    timeout_signal = Signal()

    def __init__(self):
        super().__init__()
        self.activa = False
        self._ruta_base  = ""
        self._f_ondas    = None; self._w_ondas  = None
        self._f_ciclos   = None; self._w_ciclos = None
        self.contador_ondas  = 0
        self.contador_ciclos = 0
        self._timer_dur = QTimer(self)
        self._timer_dur.setSingleShot(True)
        self._timer_dur.timeout.connect(self.timeout_signal)
        self.t_inicio = None

    def iniciar(self, ruta_base: str, duracion_seg: int = 0):
        self._ruta_base = ruta_base
        self.t_inicio   = datetime.now()
        self._f_ondas   = open(ruta_base + "_ondas.csv",  "w", newline="", encoding="utf-8")
        self._w_ondas   = csv.writer(self._f_ondas)
        self._w_ondas.writerow([
            "timestamp","flow_lmin","pres_cmh2o",
            "Ti","Te","TiH","TeH","IE","BPM",
            "PIF","PEF","Vti","Vte","MV",
            "PIP","IPP","MAP","PEEP","O2","CMPL","VOL",
            "temp_c","hum_pct","prba","gas","flcm"])
        self._f_ciclos  = open(ruta_base + "_ciclos.csv", "w", newline="", encoding="utf-8")
        self._w_ciclos  = csv.writer(self._f_ciclos)
        self._w_ciclos.writerow([
            "timestamp","num_ciclo",
            "Ti","Te","TiH","TeH","IE","BPM_b",
            "PIF","PEF","Vti","Vte","MV",
            "PIP_b","IPP","MAP","PEEP_b","O2","CMPL","VOL",
            "temp_c","hum_pct","prba","gas","flcm"])
        self.contador_ondas = 0; self.contador_ciclos = 0
        self.activa = True
        if duracion_seg > 0:
            self._timer_dur.start(duracion_seg * 1000)

    def _fval(self, p, k, d=1):
        v = p.get(k)
        if v is None: return ""
        if isinstance(v, str): return v
        try: return f"{float(v):.{d}f}"
        except: return str(v)

    def registrar_muestra(self, ts: datetime, flow, pres, p: dict):
        if not self.activa: return
        f = self._fval
        self._w_ondas.writerow([
            ts.strftime("%H:%M:%S.%f")[:-3],
            f"{flow:.4f}" if flow is not None else "",
            f"{pres:.4f}" if pres is not None else "",
            f(p,'Ti',2), f(p,'Te',2), f(p,'TiH',2), f(p,'TeH',2),
            f(p,'IE',2), f(p,'BPM_b',0),
            f(p,'PIF',2), f(p,'PEF',2),
            f(p,'Vti',2), f(p,'Vte',2),
            f(p,'MV',3),
            f(p,'PIP_b',1), f(p,'IPP',1), f(p,'MAP',1), f(p,'PEEP_b',1),
            f(p,'O2',1), f(p,'CMPL',1), f(p,'VOL',2),
            f(p,'temp',1), f(p,'hum',1), f(p,'prba',2),
            p.get('gas',''), p.get('flcm','')])
        self.contador_ondas += 1
        if self.contador_ondas % 50 == 0: self._f_ondas.flush()

    def registrar_ciclo(self, ts: datetime, p: dict):
        if not self.activa: return
        self.contador_ciclos += 1
        f = self._fval
        self._w_ciclos.writerow([
            ts.strftime("%H:%M:%S.%f")[:-3], self.contador_ciclos,
            f(p,'Ti',3), f(p,'Te',3), f(p,'TiH',3), f(p,'TeH',3),
            f(p,'IE',2), f(p,'BPM_b',0),
            f(p,'PIF',3), f(p,'PEF',3),
            f(p,'Vti',2), f(p,'Vte',2),
            f(p,'MV',3),
            f(p,'PIP_b',2), f(p,'IPP',2), f(p,'MAP',2), f(p,'PEEP_b',2),
            f(p,'O2',2), f(p,'CMPL',2), f(p,'VOL',2),
            f(p,'temp',1), f(p,'hum',1), f(p,'prba',2),
            p.get('gas',''), p.get('flcm','')])
        self._f_ciclos.flush()

    def detener(self):
        self._timer_dur.stop()
        self.activa = False
        for fh in [self._f_ondas, self._f_ciclos]:
            if fh:
                try: fh.flush(); fh.close()
                except: pass
        self._f_ondas = self._f_ciclos = None
        return self._ruta_base

    @property
    def duracion_actual(self) -> float:
        if self.t_inicio is None: return 0.0
        return (datetime.now() - self.t_inicio).total_seconds()


# ─────────────────────────────────────────────────────────────────
# Analizador de datos
# ─────────────────────────────────────────────────────────────────
class AnalizadorDatos:
    def __init__(self, ruta_ciclos: str, config: dict):
        self.ruta   = ruta_ciclos
        self.config = config
        self.filas  = []; self.header = []
        self.resultados = {}; self.n_ciclos = 0

    def cargar(self):
        with open(self.ruta, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            self.header = next(reader)
            self.filas  = [row for row in reader if any(r.strip() for r in row)]
        self.n_ciclos = len(self.filas)

    def _columna(self, nombre: str):
        try: idx = self.header.index(nombre)
        except ValueError: return np.array([])
        vals = []
        for row in self.filas:
            try:
                v = float(row[idx])
                if not math.isnan(v): vals.append(v)
            except: pass
        return np.array(vals)

    def _columna_ts(self):
        try:
            idx = self.header.index("timestamp")
            return [row[idx] for row in self.filas]
        except: return []

    def analizar(self) -> dict:
        parametros = {
            'BPM_b' : ('BPM_b',  'bpm'),
            'Vti'   : ('Vti',    'vt'),
            'Vte'   : ('Vte',    'vt'),
            'Ti'    : ('Ti',     'ti'),
            'PIP_b' : ('PIP_b',  'pip'),
            'PEEP_b': ('PEEP_b', 'peep'),
            'MV'    : ('MV',     'mv'),
        }
        for key, (col, ref_key) in parametros.items():
            arr = self._columna(col)
            if arr.size == 0: continue
            ref_val = self.config.get(ref_key)
            norma   = NORMA.get(key, {})
            media = float(np.mean(arr)); std = float(np.std(arr))
            minv  = float(np.min(arr));  maxv = float(np.max(arr))
            oscil_pct = (maxv - minv) / media * 100 if media != 0 else 0
            cv_pct    = std / media * 100            if media != 0 else 0
            error_pct = None
            if ref_val is not None and ref_val != 0:
                error_pct = (media - ref_val) / ref_val * 100
            cumple = None; detalle_cumple = ""
            if ref_val is not None and norma:
                tipo    = norma.get('tipo', 'pct')
                tol_pct = norma.get('tol')
                tol_abs = norma.get('abs')
                if tipo == 'pct' and tol_pct is not None:
                    cumple = abs(error_pct) <= tol_pct if error_pct is not None else None
                    detalle_cumple = f"+-{tol_pct}%"
                elif tipo == 'abs' and tol_abs is not None:
                    cumple = abs(media - ref_val) <= tol_abs
                    detalle_cumple = f"+-{tol_abs} {norma.get('unidad','')}"
                elif tipo == 'max_pct_abs' and tol_pct is not None and tol_abs is not None:
                    tol_ef = max(abs(ref_val) * tol_pct / 100, tol_abs)
                    cumple = abs(media - ref_val) <= tol_ef
                    detalle_cumple = f"max(+-{tol_pct}%, +-{tol_abs})"
            self.resultados[key] = {
                'label':norma.get('label',key), 'unidad':norma.get('unidad',''),
                'n':len(arr), 'media':media, 'std':std, 'min':minv, 'max':maxv,
                'oscil_pct':oscil_pct, 'cv_pct':cv_pct, 'ref':ref_val,
                'error_pct':error_pct, 'cumple':cumple, 'tol_desc':detalle_cumple,
                'serie':arr.tolist(), 'timestamps':self._columna_ts(),
            }
        return self.resultados

    def resumen_texto(self) -> str:
        lineas = ["="*60,
                  "  RESUMEN DE PRUEBA  -  VT650 Monitor v3.0", "="*60,
                  f"  Archivo ciclos : {self.ruta}",
                  f"  Ciclos grabados: {self.n_ciclos}"]
        cfg = self.config
        lineas += [f"  Operador       : {cfg.get('operador','--')}",
                   f"  Equipo (ID)    : {cfg.get('equipo_id','--')}",
                   f"  Modelo/Serie   : {cfg.get('modelo','--')}",
                   f"  Fecha          : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ""]
        lineas.append("  PARAMETROS DE REFERENCIA")
        lineas.append(
            f"    BPM={cfg.get('bpm','--')}  Vt={cfg.get('vt','--')} mL  "
            f"Ti={cfg.get('ti','--')} s  PEEP={cfg.get('peep','--')} cmH2O")
        lineas.append(
            f"    PIP={cfg.get('pip','--')} cmH2O  I:E=1:{cfg.get('ie','--')}  "
            f"MV={cfg.get('mv','--')} L/min  FIO2={cfg.get('fio2','--')}%")
        lineas.append("")
        lineas.append("  ESTADISTICAS POR PARAMETRO  (ISO 80601-2-12)")
        lineas.append(f"  {'Param':<10}{'Ref':>7}{'Media':>9}{'Std':>7}{'Min':>7}"
                      f"{'Max':>7}{'Error%':>8}{'Oscil%':>8}{'Cumple':>8}  Tolerancia")
        lineas.append("  " + "-"*80)
        for key, r in self.resultados.items():
            ref_s = f"{r['ref']:.1f}" if r['ref'] is not None else "--"
            err_s = f"{r['error_pct']:+.1f}%" if r['error_pct'] is not None else "--"
            cum_s = "OK" if r['cumple'] else ("FALLA" if r['cumple'] is False else "--")
            lineas.append(
                f"  {r['label']:<10}{ref_s:>7}{r['media']:>9.2f}{r['std']:>7.2f}"
                f"{r['min']:>7.2f}{r['max']:>7.2f}{err_s:>8}{r['oscil_pct']:>7.1f}%"
                f"  {cum_s:<7}  {r['tol_desc']}")
        total    = sum(1 for r in self.resultados.values() if r['cumple'] is not None)
        ok_count = sum(1 for r in self.resultados.values() if r['cumple'] is True)
        lineas.append("")
        if total > 0:
            pct_ok = ok_count / total * 100
            lineas.append(f"  CUMPLIMIENTO: {ok_count}/{total} parametros ({pct_ok:.0f}%)")
            if pct_ok == 100:
                lineas.append("  RESULTADO: DENTRO DE NORMATIVA  OK")
            else:
                fuera = [r['label'] for r in self.resultados.values() if r['cumple'] is False]
                lineas.append("  RESULTADO: FUERA DE NORMATIVA")
                lineas.append(f"  Parametros fuera: {', '.join(fuera)}")
        lineas.append("="*60)
        return "\n".join(lineas)
