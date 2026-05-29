# VT650 Monitor Mod

Aplicación Python para conectar y monitorear un analizador Fluke VT650, grabar datos de flujo y presión en tiempo real, analizar ciclos respiratorios y generar informes técnicos.

## Resumen funcional

La app se conecta al VT650 vía puerto serial, solicita datos en tres ritmos distintos, muestra gráficos de flujo y presión, guarda muestras y ciclos en CSV, analiza el archivo de ciclos y permite exportar resultados en PDF o TXT.

## Requisitos

- Python 3.8 o superior.
- Recomendado usar entorno virtual.

Dependencias principales (archivo `requirements.txt`):
- `PySide6`
- `pyqtgraph`
- `numpy`
- `pyserial`
- `reportlab`

## Instalación

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

Desde la carpeta `VT650 Monitor Mod`:

```bash
python main.py
```

O desde la raíz del proyecto:

```bash
python "VT650 Monitor Mod/main.py"
```

## Estructura y propósito de los módulos

### `config.py`

Define constantes y valores de referencia.
- Parámetros de buffer y ventana (`BUFFER`, `VEN_MIN`, `VEN_MAX`, `MAX_SW`).
- Umbrales de detección de inicio/fin de inspiración (`INSP_THRESH`, `EXP_THRESH`, `INSP_CONFIRM`).
- Descripciones de gases (`GAS_DESC`) y modos de corrección (`FLCM_DESC`).
- Norma de evaluación (`NORMA`) con etiquetas, unidades, tolerancias absolutas y porcentuales.
- `REF_KEYS`: parámetros programados del respirador que se solicitan al configurar una grabación.

### `template.py`

Archivo legado que contiene una plantilla HTML antigua. La generación actual de informes PDF ya se hace directamente con ReportLab en `export.py`, por lo que este archivo ya no se utiliza.

### `core.py`

Este módulo es el núcleo de la aplicación.

#### `Signals`

Clase Qt que declara señales personalizadas usadas por el driver serial:
- `nuevo_dato`: envía flujo y presión instantáneos.
- `datos_brp`: envía parámetros respiratorios extraídos de `BRP`.
- `datos_lentos`: envía datos ambientales y estado largo.
- `error_serial`: notifica fallas en comunicación.
- `hz_actual`: actualiza la frecuencia de muestreo.

#### `VT650`

Driver para comunicarse con el Fluke VT650.
- `conectar()`: abre el puerto serial, configura el equipo en modo remoto y unidades, e intenta activar `UARTFAST` para alta velocidad.
- `_activar_uartfast()`: cambia el VT650 a 921600 bps si es posible.
- `_cmd_raw()` y `_query_float()`: envían comandos y leen respuestas del equipo.
- `_query_brp()`: solicita y recibe las líneas de estado `BRP`.
- `_parse_brp()`: parsea líneas `BRP` en parámetros respiratorios (`Ti`, `Te`, `Vti`, `Vte`, `MV`, `PIP_b`, `PEEP_b`, etc.).
- `iniciar_polling()`: lanza tres hilos de lectura:
  - `_loop_rapido()`: consulta `FLAW` y `PRAW` continuamente para flujo/presión instantáneos.
  - `_loop_medio()`: consulta `BRP` y `VOL` cada 1.5 segundos.
  - `_loop_lento()`: consulta temperatura, humedad, presión barométrica, gas y modo de corrección cada 10 segundos.
- `desconectar()`: detiene los hilos, restaura el modo local y cierra el puerto.

#### `FiltroRueda`

Filtro de evento Qt para controlar el zoom de la ventana de trazado con la rueda del mouse.

#### `GrabacionManager`

Gestiona la escritura de dos archivos CSV:
- `*_ondas.csv`: muestras individuales de flujo/presión y parámetros actuales.
- `*_ciclos.csv`: registros de ciclo completos cada vez que se detecta una nueva inspiración.

Funciones clave:
- `iniciar(ruta_base, duracion_seg)`: abre archivos, escribe cabeceras y activa la grabación.
- `registrar_muestra(ts, flow, pres, p)`: guarda cada muestra instantánea.
- `registrar_ciclo(ts, p)`: guarda un ciclo completo cuando se detecta inicio de inspiración.
- `detener()`: cierra archivos y retorna la ruta base.
- `duracion_actual`: tiempo transcurrido de la grabación.

#### `AnalizadorDatos`

Carga y analiza el CSV de ciclos.
- `cargar()`: lee el archivo `*_ciclos.csv` y almacena filas válidas.
- `_columna(nombre)`: extrae una columna numérica del CSV.
- `analizar()`: calcula estadísticos para parámetros clave (`BPM_b`, `Vti`, `Vte`, `Ti`, `PIP_b`, `PEEP_b`, `MV`).
- Aplica criterios de `NORMA` para decidir cumplimiento.
- Devuelve resultados con media, desviación estándar, oscilación, coeficiente de variación, error porcentual y cumplimiento.
- `resumen_texto()`: genera un reporte plano en texto con datos resumidos.

### `export.py`

Genera informes técnicos y muestra la vista previa directamente con ReportLab.

#### `GeneradorInforme`

- `generar_pdf(ruta, observaciones)`: crea un PDF con `ReportLab` usando:
  - `HeaderInforme`
  - `SeccionAmbiental`
  - `TablaResultados`
  - diagnóstico global y observaciones.
- Incluye footer con número de página y datos de equipo.

#### `DialogoInforme`

- Muestra una ventana con vista previa del informe.
- Si `PySide6.QtPdfWidgets` está disponible, usa `QPdfView` para mostrar el PDF generado en memoria.
- Si no, muestra una vista HTML simple en un `QTextEdit`.
- Permite exportar PDF y TXT directamente.

### `pdf_helpers.py`

Funciones utilitarias para PDF:
- `mm_widths()`: convierte milímetros a puntos para ReportLab.
- `build_table()`: crea tablas con estilos de `PDFTableStyles`.

### `pdf_sections.py`

Define secciones reutilizables del informe:
- `HeaderInforme`: encabezado con logo opcional, título y subtítulo.
- `SeccionAmbiental`: tabla de condiciones ambientales y analizador.
- `TablaResultados`: tabla detallada de resultados con estado `OK`/`FALLA`.

### `pdf_styles.py`

Centraliza estilos y tamaños para PDF:
- `PDFStyles`: márgenes, colores, estilos de párrafo y tamaños de columna.
- `PDFTableStyles`: estilos para encabezados, cuerpo y tablas de resultados.

### `ui.py`

Contiene toda la interfaz gráfica y la lógica de interacción.

#### `DialogConfigGrabacion`

Diálogo para capturar:
- datos del operador, equipo y modelo.
- duración de grabación (0=manual).
- parámetros de referencia del respirador (`BPM`, `Vt`, `Ti`, `PEEP`, `PIP`, `I:E`, `VM`, `FIO2`).

#### `VentanaAnalisis`

Muestra resultados una vez que se cierra la grabación.
- pestaña `Resumen / Diagnostico`: tabla con valores estadísticos, referencias y cumplimiento.
- pestaña `Graficos de parametros`: curvas para `BPM`, `Vti`, `PIP_b`, `PEEP_b`, `MV`, `Ti`.
- destaca visualmente si la prueba está dentro o fuera de normativa.

#### `VentanaPrincipal`

La UI principal controla toda la experiencia:
- Selección de puerto COM y conexión al dispositivo.
- Conexión y polling del VT650.
- Visualización en tiempo real de flujo y presión.
- Cambio de vista entre `Flujo+Pres`, `Solo Flujo` y `Solo Presión`.
- Ajuste de ventana de trazado (6s, 12s, 24s) y zoom con rueda de mouse.
- Grabación de datos y ciclos en CSV.
- Detección automática de nuevos ciclos respiratorios mediante umbrales de flujo.
- Actualización de valores de parámetros respiratorios y ambientales.
- Al terminar grabación, abre el análisis estadístico y pregunta si desea generar informe.

## Flujo de funcionamiento

1. `main.py` arranca la aplicación y muestra `VentanaPrincipal`.
2. El usuario selecciona un puerto COM y conecta el VT650.
3. El driver `VT650` arranca tres hilos:
   - lectura rápida de flujo/presión,
   - lectura intermedia de parámetros BRP,
   - lectura lenta de datos ambientales.
4. La interfaz recibe señales y actualiza los paneles de datos y gráficos.
5. Al iniciar grabación, `GrabacionManager` escribe muestras en `*_ondas.csv` y ciclos en `*_ciclos.csv`.
6. Cuando finaliza la grabación, `AnalizadorDatos` carga los ciclos y calcula estadísticas.
7. `VentanaAnalisis` muestra resultados; luego se puede generar un informe PDF o TXT.

## Archivos generados

- `*_ondas.csv`: fila por muestra instantánea con flujo, presión, parámetros respiratorios y ambientales.
- `*_ciclos.csv`: fila por ciclo respiratorio con estadísticos de ciclo.
- PDF/TXT opcionales con resumen analítico.

## Personalización de los PDFs

Los archivos de generación de PDF están modularizados para permitir fácil personalización. A continuación se explica cómo modificar colores, tamaños, márgenes y disposición de elementos.

### Cambiar colores y estilos globales

Archivo: `pdf_styles.py`

Este archivo centraliza todos los estilos visuales. Para cambiar colores, edita la clase `PDFStyles`:

```python
class PDFStyles:
    # Colores institucionales (formato HexColor)
    COLOR_PRIMARY = colors.HexColor('#1565C0')      # Azul principal
    COLOR_SECONDARY = colors.HexColor('#1A237E')    # Azul oscuro
    COLOR_ACCENT = colors.HexColor('#00BCD4')       # Cyan
    COLOR_SUCCESS = colors.HexColor('#1B5E20')      # Verde (OK)
    COLOR_DANGER = colors.HexColor('#B71C1C')       # Rojo (FALLA)
    COLOR_WARN = colors.HexColor('#FB8C00')         # Naranja
```

**Ejemplo**: Cambiar el color primario a rojo corporativo:

```python
COLOR_PRIMARY = colors.HexColor('#D32F2F')  # Rojo
```

### Cambiar márgenes de página

En `pdf_styles.py`, modifica los márgenes (en milímetros):

```python
MARGIN_TOP = 15 * mm       # Cambiar a 20 * mm para más espacio arriba
MARGIN_BOTTOM = 15 * mm
MARGIN_LEFT = 12 * mm
MARGIN_RIGHT = 12 * mm
```

### Cambiar tamaños de fuente y espaciado

En `pdf_styles.py`, dentro del método `get_styles()`, edita los estilos de párrafo:

```python
styles.add(ParagraphStyle(
    name='HeaderMain',
    fontSize=18,           # Aumentar a 20 para títulos más grandes
    leading=22,           # Espacio entre líneas
    textColor=PDFStyles.COLOR_PRIMARY,
    alignment=TA_CENTER,
    spaceAfter=3 * mm,    # Espacio después del título
    fontName='Helvetica-Bold'
))
```

### Cambiar disposición de tablas y anchos de columnas

Archivo: `pdf_sections.py`

Cada sección (Ambientales, Resultados, etc.) define sus propios anchos de columna usando la función `mm_widths()`:

#### Sección "2. Condiciones Ambientales"

```python
def flowables(self):
    data = [
        ['Temperatura:', f"{self.params.get('temp','--')} C", ...],
        ...
    ]
    colw = mm_widths(30, 40, 30, 40)  # [col1, col2, col3, col4] en mm
    tbl = build_table(data, col_widths=colw, style_type='body')
```

Para hacer más ancha la columna de temperatura (primera), cambia el primer valor:

```python
colw = mm_widths(40, 30, 30, 40)  # Primera columna más ancha
```

#### Sección "4. Resultados - Estadísticas"

```python
colw = mm_widths(30, 10, 10, 10, 10, 10, 10, 10, 10, 12, 12, 15, 12)
```

Los valores están en orden: `[Parametro, Unidad, N_ciclos, Media, Std, Min, Max, CV%, Oscil%, Referencia, Error%, Tolerancia, Resultado]`

**Ejemplo**: Aumentar el ancho de "Parametro" a 40mm:

```python
colw = mm_widths(40, 10, 10, 10, 10, 10, 10, 10, 10, 12, 12, 15, 12)
```

### Cambiar estilos de celdas de tabla

Archivo: `pdf_styles.py`, clase `PDFTableStyles`

Para cambiar cómo se ven las filas alternadas:

```python
@staticmethod
def get_body_style(num_rows, num_cols):
    ...
    for row in range(1, num_rows):
        if row % 2 == 0:
            # Cambiar color de fondo de filas pares
            styles.append(('BACKGROUND', (0, row), (num_cols - 1, row), 
                          colors.HexColor('#E3F2FD')))  # Azul muy claro
```

### Cambiar alineación y relleno de celdas

En `pdf_styles.py`, dentro de `get_body_style()`:

```python
styles = [
    ('ALIGN', (0, 1), (num_cols - 1, num_rows - 1), 'CENTER'),  # 'LEFT', 'CENTER', 'RIGHT'
    ('VALIGN', (0, 0), (num_cols - 1, num_rows - 1), 'MIDDLE'),  # 'TOP', 'MIDDLE', 'BOTTOM'
    ('LEFTPADDING', (0, 1), (num_cols - 1, num_rows - 1), 4),     # Espacio izquierdo
    ('RIGHTPADDING', (0, 1), (num_cols - 1, num_rows - 1), 4),
    ('TOPPADDING', (0, 1), (num_cols - 1, num_rows - 1), 3),
    ('BOTTOMPADDING', (0, 1), (num_cols - 1, num_rows - 1), 3),
]
```

### Cambiar el grid y bordes de tablas

En `pdf_styles.py`:

```python
# Bordes más gruesos
styles.append(('BOX', (0, 0), (num_cols - 1, num_rows - 1), 1.0, colors.black))

# Grid interior más visible
styles.append(('INNERGRID', (0, 0), (num_cols - 1, num_rows - 1), 0.5, colors.grey))
```

### Cambiar la estructura del informe PDF

La generación de informes se hace directamente con ReportLab en `export.py` y las secciones PDF definidas en `pdf_sections.py`.

Si quieres modificar el contenido, edita las secciones de `HeaderInforme`, `SeccionAmbiental` y `TablaResultados` en `pdf_sections.py`, o cambia estilos globales en `pdf_styles.py`.

### Cambiar encabezado e integrar logo

En `export.py`, método `generar_pdf()`:

```python
header = HeaderInforme(cfg, styles, logo_path=cfg.get('logo_path'))
```

Para usar un logo, agrega a la configuración:

```python
cfg['logo_path'] = '/ruta/al/logo.png'
```

El logo se mostrará en la parte superior del informe (20mm x 20mm).

### Ejemplo completo: Cambiar tema corporativo a tonos verdes

1. En `pdf_styles.py`:

```python
COLOR_PRIMARY = colors.HexColor('#2E7D32')        # Verde oscuro
COLOR_SECONDARY = colors.HexColor('#558B2F')      # Verde secundario
COLOR_SUCCESS = colors.HexColor('#00C853')        # Verde brillante
COLOR_DANGER = colors.HexColor('#D32F2F')         # Rojo (mantener para fallos)
```

2. En `pdf_sections.py`, cambiar anchos de tabla de resultados:

```python
colw = mm_widths(35, 12, 10, 10, 10, 10, 10, 10, 10, 12, 12, 15, 12)  # Parametro más ancho
```

3. Regenerar el PDF y verá el nuevo tema aplicado.

## Consejos de uso

- Usar al menos 3 ciclos grabados para análisis válido.
- Verificar que el VT650 responda correctamente antes de grabar.
- Si el informe PDF no se muestra, la aplicación aún puede exportar TXT.
- Para cambios complejos en la estructura del PDF, revisa la [documentación de ReportLab](https://www.reportlab.com/docs/reportlab-userguide.pdf).

## Observaciones

Esta versión de `VT650 Monitor Mod` combina captura en tiempo real, grabación de datos y análisis de cumplimiento con normas de respiradores. El código está organizado para separar:
- comunicación serial y muestreo (`core.py`),
- interfaz y eventos de usuario (`ui.py`),
- análisis de resultados (`core.py`),
- generación de informes (`export.py`, `pdf_helpers.py`, `pdf_sections.py`, `pdf_styles.py`).

