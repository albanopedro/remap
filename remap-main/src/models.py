"""
Definições de modelos de ECU suportados.

Para usar com uma ECU real, os offsets precisam ser verificados com o
binário original usando WinOLS, TunerPro RTi ou um editor hexadecimal.
Offsets errados NÃO causam dano imediato (só corrompem o .bin), mas
gravar um .bin corrompido na ECU pode inutilizá-la.

Como descobrir os offsets:
  1. Abra o .bin no WinOLS (modo demo é suficiente para leitura)
  2. Para RPM limit: busque o valor ~6500 em big-endian (0x1964) no range
     0x10000–0x3FFFF. Mude para 7000 (0x1B58) para confirmar.
  3. Para temperatura de acionamento do fan: busque valores ~98 (0x62) 1-byte.
  4. Comunidades: GmmPlus.com.br, TuningBrazil — têm .xdf prontos para MT35E.
"""

from typing import Dict, Any, Optional

# Cada parâmetro define:
#   offset    : endereço no binário (int)
#   size      : bytes (1, 2 ou 4)
#   scale     : multiplicador para converter raw -> valor real
#   unit      : unidade de exibição
#   min/max   : limites físicos do parâmetro
#   verified  : True se o offset foi confirmado com binário real
#   byte_order: 'little' (x86) ou 'big' (Motorola/Delphi)

ECU_MODELS: Dict[str, Dict[str, Any]] = {

    # ─────────────────────────────────────────────────────────────────────
    # GENÉRICO — offsets fictícios para demonstração/testes
    # ─────────────────────────────────────────────────────────────────────
    'generic': {
        'name':         'Generic (Demo)',
        'binary_sizes': [256 * 1024, 512 * 1024],
        'byte_order':   'little',
        'header':       b'ECU!',
        'has_turbo':    True,
        'checksum':     'crc32',
        'vehicles':     ['Demo / Testes'],
        'parameters': {
            'fuel_injection':  {'offset': 0x1000, 'size': 2, 'scale': 0.5,  'unit': '%',   'min': 0,    'max': 200,  'verified': True},
            'ignition_timing': {'offset': 0x1100, 'size': 2, 'scale': 0.1,  'unit': '°',   'min': -20,  'max': 50,   'verified': True},
            'turbo_boost_low': {'offset': 0x1200, 'size': 2, 'scale': 0.01, 'unit': 'bar', 'min': 0.5,  'max': 2.0,  'verified': True},
            'turbo_boost_high':{'offset': 0x1202, 'size': 2, 'scale': 0.01, 'unit': 'bar', 'min': 0.5,  'max': 2.5,  'verified': True},
            'rpm_limit':       {'offset': 0x1300, 'size': 2, 'scale': 1.0,  'unit': 'rpm', 'min': 5000, 'max': 9000, 'verified': True},
            'lambda_target':   {'offset': 0x1400, 'size': 2, 'scale': 0.01, 'unit': 'λ',   'min': 0.8,  'max': 1.2,  'verified': True},
            'cooling_temp':    {'offset': 0x1500, 'size': 1, 'scale': 1.0,  'unit': '°C',  'min': 70,   'max': 110,  'verified': True},
            'fan_activation':  {'offset': 0x1600, 'size': 1, 'scale': 1.0,  'unit': '°C',  'min': 80,   'max': 100,  'verified': True},
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # DELPHI MT35E
    # Veículos: Corsa Classic 1.0/1.4, Celta 1.0  (2003–2012)
    #
    # ATENÇÃO: offsets abaixo marcados verified=False precisam ser
    # confirmados com SEU arquivo .bin. Versões de firmware diferentes
    # têm offsets diferentes. Use WinOLS ou TunerPro + .xdf da comunidade.
    #
    # Byte order: big-endian (Motorola). Motor aspirado — sem turbo.
    # Comunicação: ISO 9141-2 K-Line (pino 7 do OBD-II).
    # ─────────────────────────────────────────────────────────────────────
    'delphi_mt35e': {
        'name':         'Delphi MT35E',
        'binary_sizes': [256 * 1024],
        'byte_order':   'big',
        'header':       None,      # sem header fixo; verificado pelo tamanho
        'has_turbo':    False,     # Corsa 1.0/1.4 é motor aspirado
        'checksum':     'sum16',   # soma simples 16-bit sobre seção de calibração
        'vehicles': [
            'Chevrolet Corsa Classic 1.0 8v 2003–2012',
            'Chevrolet Corsa Classic 1.4 8v 2003–2012',
            'Chevrolet Celta 1.0 8v 2003–2012',
        ],
        # ── Offsets: PRECISAM ser verificados com o binário real ──────────
        # Para encontrá-los: abra o .bin no WinOLS, veja a região de
        # calibração (geralmente 0x10000–0x3FFFF) e procure os valores
        # conhecidos do stock (ex: RPM limit ~6500 = 0x1964 big-endian).
        # Após confirmar, mude verified para True e atualize o offset.
        'parameters': {
            'fuel_injection':  {'offset': 0x0000, 'size': 2, 'scale': 0.1,  'unit': '%',   'min': 0,    'max': 150,  'verified': False},
            'ignition_timing': {'offset': 0x0000, 'size': 2, 'scale': 0.1,  'unit': '°',   'min': -10,  'max': 45,   'verified': False},
            'rpm_limit':       {'offset': 0x0000, 'size': 2, 'scale': 1.0,  'unit': 'rpm', 'min': 4000, 'max': 7500, 'verified': False},
            'lambda_target':   {'offset': 0x0000, 'size': 2, 'scale': 0.001,'unit': 'λ',   'min': 0.75, 'max': 1.15, 'verified': False},
            'cooling_temp':    {'offset': 0x0000, 'size': 1, 'scale': 1.0,  'unit': '°C',  'min': 85,   'max': 108,  'verified': False},
            'fan_activation':  {'offset': 0x0000, 'size': 1, 'scale': 1.0,  'unit': '°C',  'min': 90,   'max': 105,  'verified': False},
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # DELPHI MT20U2
    # Veículos: Corsa 1.0/1.4 gasolina 2000–2003 (pré-flex)
    # ─────────────────────────────────────────────────────────────────────
    'delphi_mt20u2': {
        'name':         'Delphi MT20U2',
        'binary_sizes': [128 * 1024],
        'byte_order':   'big',
        'header':       None,
        'has_turbo':    False,
        'checksum':     'sum16',
        'vehicles': [
            'Chevrolet Corsa 1.0/1.4 gasolina 2000–2003',
        ],
        'parameters': {
            'fuel_injection':  {'offset': 0x0000, 'size': 2, 'scale': 0.1,  'unit': '%',   'min': 0,    'max': 150,  'verified': False},
            'ignition_timing': {'offset': 0x0000, 'size': 2, 'scale': 0.1,  'unit': '°',   'min': -10,  'max': 45,   'verified': False},
            'rpm_limit':       {'offset': 0x0000, 'size': 2, 'scale': 1.0,  'unit': 'rpm', 'min': 4000, 'max': 7000, 'verified': False},
            'lambda_target':   {'offset': 0x0000, 'size': 2, 'scale': 0.001,'unit': 'λ',   'min': 0.75, 'max': 1.15, 'verified': False},
            'cooling_temp':    {'offset': 0x0000, 'size': 1, 'scale': 1.0,  'unit': '°C',  'min': 85,   'max': 108,  'verified': False},
            'fan_activation':  {'offset': 0x0000, 'size': 1, 'scale': 1.0,  'unit': '°C',  'min': 90,   'max': 105,  'verified': False},
        },
    },

}


def get_model(model_id: str) -> Optional[Dict[str, Any]]:
    return ECU_MODELS.get(model_id)


def list_models() -> Dict[str, str]:
    """Retorna {id: nome} de todos os modelos."""
    return {k: v['name'] for k, v in ECU_MODELS.items()}


def unverified_params(model_id: str):
    """Retorna lista de parâmetros ainda não verificados para um modelo."""
    m = ECU_MODELS.get(model_id, {})
    return [k for k, v in m.get('parameters', {}).items() if not v.get('verified', True)]
