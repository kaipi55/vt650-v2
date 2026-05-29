# ─────────────────────────────────────────────────────────────────
# Constantes y Configuración
# ─────────────────────────────────────────────────────────────────

BUFFER       = 2000
VEN_MIN      = 6
VEN_MAX      = 24
MAX_SW       = 2000
INSP_THRESH  =  2.0
EXP_THRESH   = -1.0
INSP_CONFIRM =  3

GAS_DESC = {
    'AIR':'Aire','N2':'Nitrogeno','O2':'Oxigeno','AR':'Argon',
    'CO2':'CO2','N2O':'Oxido Nitroso','HELIOX':'Heliox',
    'O2BALN2O':'O2 Bal N2O','O2BALHE':'O2 Bal He','O2BALN2':'O2 Bal N2'
}

FLCM_DESC = {
    'ATP'   :'Temp.Ambiente / Pres.Ambiente / Humedad Real',
    'ATPD'  :'Temp.Ambiente / Pres.Ambiente / Humedad Seca',
    'ATPS'  :'Temp.Ambiente / Pres.Ambiente / Humedad Saturada',
    'STP20' :'Temp.Estandar 20C / Pres.1ATM / Humedad Real',
    'STP21' :'Temp.Estandar 21C / Pres.1ATM / Humedad Real',
    'STPD0' :'Temp.Estandar 0C / Pres.1ATM / Humedad Seca',
    'STPD20':'Temp.Estandar 20C / Pres.1ATM / Humedad Seca',
    'STPD21':'Temp.Estandar 21C / Pres.1ATM / Humedad Seca',
    'BTPS'  :'Temp.Corporal 37C / Pres.Ambiente / Humedad Saturada',
    'BTPD'  :'Temp.Corporal 37C / Pres.Ambiente / Humedad Seca',
}

NORMA = {
    'BPM_b' : {'label':'BPM',    'unidad':'br/min','tol':10, 'abs':2,   'tipo':'max_pct_abs'},
    'Vti'   : {'label':'Vt insp','unidad':'mL',    'tol':10, 'abs':4,   'tipo':'max_pct_abs'},
    'Vte'   : {'label':'Vt esp', 'unidad':'mL',    'tol':10, 'abs':4,   'tipo':'max_pct_abs'},
    'Ti'    : {'label':'Ti',     'unidad':'s',     'tol':10, 'abs':None,'tipo':'pct'},
    'PIP_b' : {'label':'PIP',    'unidad':'cmH2O', 'tol':10, 'abs':2,   'tipo':'max_pct_abs'},
    'PEEP_b': {'label':'PEEP',   'unidad':'cmH2O', 'tol':None,'abs':1,  'tipo':'abs'},
    'MV'    : {'label':'VM',     'unidad':'L/min', 'tol':10, 'abs':None,'tipo':'pct'},
    'IE'    : {'label':'I:E',    'unidad':'',      'tol':10, 'abs':None,'tipo':'pct'},
}

REF_KEYS = [
    ('bpm',  'BPM programado',        'br/min', 4,    60,   1,  12),
    ('vt',   'Vt programado',          'mL',    50,  2000,  1, 400),
    ('ti',   'Ti programado',          's',    0.1,   5.0, 0.1, 1.0),
    ('peep', 'PEEP programado',        'cmH2O', 0,    30,   1,   5),
    ('pip',  'PIP/PC programado',      'cmH2O', 5,    80,   1,  15),
    ('ie',   'Relacion I:E (divisor)', '',      1,    10,  0.1, 4.0),
    ('mv',   'VM programado',          'L/min', 0.5,  30,  0.1, 5.0),
    ('fio2', 'FIO2 programado',        '%',     21,  100,   1, 100),
]
