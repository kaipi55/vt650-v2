# ─────────────────────────────────────────────────────────────────
# Plantilla HTML del informe
# ─────────────────────────────────────────────────────────────────

PLANTILLA_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body  { font-family:Arial,sans-serif; font-size:11px; color:#1a1a1a; margin:20px; }
  h1    { font-size:16px; color:#0D47A1; margin-bottom:2px; }
  h2    { font-size:13px; color:#1565C0; border-bottom:2px solid #1565C0;
          padding-bottom:4px; margin-top:16px; margin-bottom:6px; }
  .hbox { background:#E3F2FD; border:1px solid #90CAF9; border-radius:4px;
          padding:10px 14px; margin-bottom:12px; }
  .hbox h1 { margin:0 0 4px 0; }
  .sub  { color:#555; font-size:10px; }
  table { width:100%; border-collapse:collapse; margin-bottom:10px; }
  th    { background:#1565C0; color:white; padding:5px 8px;
          text-align:center; font-size:10px; }
  td    { padding:4px 8px; border:1px solid #ddd;
          text-align:center; font-size:10px; }
  tr:nth-child(even) { background:#F5F5F5; }
  .ok   { background:#C8E6C9 !important; font-weight:bold; color:#1B5E20; }
  .fail { background:#FFCDD2 !important; font-weight:bold; color:#B71C1C; }
  .na   { color:#9E9E9E; }
  .rbox { padding:10px 14px; border-radius:4px; font-size:13px;
          font-weight:bold; margin:10px 0; }
  .rok  { background:#C8E6C9; color:#1B5E20; border:1px solid #4CAF50; }
  .rfail{ background:#FFCDD2; color:#B71C1C; border:1px solid #F44336; }
  .ig   { display:table; width:100%; }
  .ir   { display:table-row; }
  .ic   { display:table-cell; padding:3px 6px; border:1px solid #E0E0E0;
          width:25%; font-size:10px; }
  .ilbl { font-weight:bold; color:#555; }
  .fbox { border:1px solid #ccc; height:60px; margin-top:4px; border-radius:4px; }
  .foot { margin-top:20px; font-size:9px; color:#888; text-align:center;
          border-top:1px solid #ddd; padding-top:6px; }
</style>
</head>
<body>
<div class="hbox">
  <h1>INFORME TECNICO DE VERIFICACION - VENTILADOR MECANICO</h1>
  <span class="sub">VT650 Monitor v3.0 &nbsp;|&nbsp; Fluke VT650 Gas Flow Analyzer
  &nbsp;|&nbsp; Protocolo: ISO 80601-2-12</span>
</div>

<h2>1. Datos de la Prueba</h2>
<div class="ig">
  <div class="ir">
    <div class="ic"><span class="ilbl">Operador:</span><br>{{OPERADOR}}</div>
    <div class="ic"><span class="ilbl">Fecha / Hora:</span><br>{{FECHA}}</div>
    <div class="ic"><span class="ilbl">Equipo analizado (ID):</span><br>{{EQUIPO_ID}}</div>
    <div class="ic"><span class="ilbl">Modelo / Marca:</span><br>{{MODELO}}</div>
  </div>
  <div class="ir">
    <div class="ic"><span class="ilbl">Ciclos grabados:</span><br>{{N_CICLOS}}</div>
    <div class="ic"><span class="ilbl">Gas:</span><br>{{GAS}}</div>
    <div class="ic"><span class="ilbl">Modo correccion:</span><br>{{FLCM}}</div>
    <div class="ic"><span class="ilbl">Notas:</span><br>{{NOTAS}}</div>
  </div>
</div>

<h2>2. Condiciones Ambientales</h2>
<div class="ig">
  <div class="ir">
    <div class="ic"><span class="ilbl">Temperatura:</span><br>{{TEMP}} C</div>
    <div class="ic"><span class="ilbl">Humedad relativa:</span><br>{{HUM}} %</div>
    <div class="ic"><span class="ilbl">Presion barometrica:</span><br>{{PRBA}}</div>
    <div class="ic"><span class="ilbl">Analizador:</span><br>Fluke VT650</div>
  </div>
</div>

<h2>3. Parametros Programados en el Respirador (Referencia)</h2>
<table>
<tr>
  <th>BPM</th><th>Vt (mL)</th><th>Ti (s)</th><th>PEEP (cmH2O)</th>
  <th>PIP (cmH2O)</th><th>I:E</th><th>VM (L/min)</th><th>FIO2 (%)</th>
</tr>
<tr>
  <td>{{REF_BPM}}</td><td>{{REF_VT}}</td><td>{{REF_TI}}</td>
  <td>{{REF_PEEP}}</td><td>{{REF_PIP}}</td><td>1:{{REF_IE}}</td>
  <td>{{REF_MV}}</td><td>{{REF_FIO2}}</td>
</tr>
</table>

<h2>4. Resultados - Estadisticas por Parametro (ISO 80601-2-12)</h2>
<table>
<tr>
  <th>Parametro</th><th>Unidad</th><th>N ciclos</th>
  <th>Media</th><th>Std</th><th>Min</th><th>Max</th>
  <th>CV%</th><th>Oscilacion%</th>
  <th>Referencia</th><th>Error%</th><th>Tolerancia</th><th>Resultado</th>
</tr>
{{FILAS_TABLA}}
</table>

<div class="rbox {{CLASE_RESULTADO}}">{{DIAGNOSTICO_GLOBAL}}</div>

<h2>5. Observaciones</h2>
<p style="min-height:60px;border:1px solid #ddd;padding:6px;
          border-radius:4px;font-size:11px;">{{OBSERVACIONES}}</p>

<h2>6. Firma del Tecnico</h2>
<table style="width:70%">
<tr>
  <td style="width:50%;padding:6px;">
    <b>Nombre:</b> {{OPERADOR}}<br>
    <b>Fecha:</b> {{FECHA}}<br><br>
    <div class="fbox"></div>
    <center style="font-size:9px;color:#888;">Firma y sello</center>
  </td>
  <td style="width:50%;padding:6px;">
    <b>Proximo servicio:</b><br><br>
    <div class="fbox"></div>
    <center style="font-size:9px;color:#888;">Observaciones de seguimiento</center>
  </td>
</tr>
</table>

<div class="foot">
  Generado por VT650 Monitor v3.0 &nbsp;|&nbsp;
  Fluke VT650 Gas Flow Analyzer &nbsp;|&nbsp; {{FECHA}}
</div>
</body>
</html>"""
