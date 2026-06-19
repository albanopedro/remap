"""
ECU Remap - Sistema de Reprogramação Eletrônica Automotiva
Módulo principal para manipulação, análise e modificação de arquivos ECU
"""

import struct
import hashlib
import binascii
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ECU_HEADER = b'ECU!'
ECU_HEADER_SIZE = 4
ECU_MIN_SIZE = 1024

TURBO_BASE = 1.2  # pressão turbo stock de referência

# Importação opcional — models.py pode não estar no path em alguns contextos
try:
    from models import ECU_MODELS, get_model
except ImportError:
    ECU_MODELS = {}
    get_model = lambda x: None


class RemapProfile:
    """Define um perfil de otimização para remap da ECU"""

    def __init__(
        self,
        name: str = "Custom Remap",
        fuel_boost: float = 0,
        ignition_advance: float = 0,
        turbo_pressure: Optional[Dict[str, float]] = None,
        rpm_limit: int = 7500,
        lambda_target: float = 0.9,
        cooling_temp: int = 90,
        safety_margin: float = 0.95
    ):
        self.name = name
        # Permite valores negativos para perfis de economia
        self.fuel_boost = max(-50, min(fuel_boost, 50))
        self.ignition_advance = max(-15, min(ignition_advance, 15))
        self.turbo_pressure = turbo_pressure or {"low": 1.0, "high": 1.2}
        self.rpm_limit = max(5000, min(rpm_limit, 9000))
        self.lambda_target = max(0.8, min(lambda_target, 1.1))
        self.cooling_temp = max(70, min(cooling_temp, 110))
        self.safety_margin = max(0.85, min(safety_margin, 1.0))
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'fuel_boost': self.fuel_boost,
            'ignition_advance': self.ignition_advance,
            'turbo_pressure': self.turbo_pressure,
            'rpm_limit': self.rpm_limit,
            'lambda_target': self.lambda_target,
            'cooling_temp': self.cooling_temp,
            'safety_margin': self.safety_margin,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        sign = '+' if self.fuel_boost >= 0 else ''
        ign_sign = '+' if self.ignition_advance >= 0 else ''
        return (f"RemapProfile({self.name}): "
                f"{sign}{self.fuel_boost}% fuel, "
                f"{ign_sign}{self.ignition_advance}° ign, "
                f"{self.rpm_limit}rpm")


class ECUParameter:
    """Representa um parâmetro individual da ECU"""

    def __init__(
        self,
        name: str,
        offset: int,
        size: int,
        min_val: float,
        max_val: float,
        scale: float = 1.0,
        unit: str = "",
        description: str = ""
    ):
        self.name = name
        self.offset = offset
        self.size = size
        self.min_val = min_val
        self.max_val = max_val
        self.scale = scale
        self.unit = unit
        self.description = description
        self.value = None

    def set_value(self, raw_value: int):
        scaled = raw_value * self.scale
        if self.min_val <= scaled <= self.max_val:
            self.value = scaled
        else:
            logger.warning(
                f"Valor {scaled}{self.unit} fora do range "
                f"[{self.min_val}, {self.max_val}] para {self.name}"
            )
            self.value = max(self.min_val, min(scaled, self.max_val))

    def set_scaled(self, value: float):
        """Define valor já em escala real, com clipagem de range."""
        self.value = max(self.min_val, min(value, self.max_val))

    def get_raw_value(self) -> int:
        if self.value is None:
            return 0
        return int(self.value / self.scale)

    def modify(self, percent_change: float) -> float:
        if self.value is None:
            return self.min_val
        new_value = self.value * (1 + percent_change / 100)
        self.value = max(self.min_val, min(new_value, self.max_val))
        return self.value


class ECURemap:
    """Classe principal para manipulação de arquivos ECU"""

    SUPPORTED_MODELS = list(ECU_MODELS.keys()) or ['generic', 'bosch', 'siemens', 'delco']

    # Valores stock de referência usados quando o arquivo não tem dados
    STOCK_FUEL = 100.0   # 100% de injeção
    STOCK_IGN = 10.0     # 10° de avanço

    def __init__(self, ecu_data: bytes, model: str = "generic", validate: bool = True):
        self.ecu_data = bytearray(ecu_data)
        # Cópia imutável do original para uso no backup
        self._original_data = bytes(ecu_data)
        self.model = model.lower()
        self._model_def = get_model(self.model) or get_model('generic') or {}
        self._byte_order = self._model_def.get('byte_order', 'little')
        self.original_hash = hashlib.sha256(self._original_data).hexdigest()
        self.original_checksum = self._calculate_checksum(self._original_data)
        self.parameters = self._initialize_parameters()
        self.modifications_log: List[str] = []

        if validate:
            self._validate_ecu_file()

        # Avisa sobre parâmetros não verificados em modelos reais
        if self._model_def:
            unverified = [k for k, v in self._model_def.get('parameters', {}).items()
                         if not v.get('verified', True) and v.get('offset', 0) == 0]
            if unverified:
                logger.warning(
                    f"Modelo '{self.model}': offsets não verificados para: "
                    f"{', '.join(unverified)}. Confirme com o binário real antes de gravar na ECU."
                )

        logger.info(
            f"ECU carregada: {len(self.ecu_data)} bytes, "
            f"modelo: {self.model}, checksum: {self.original_checksum}"
        )

    def _calculate_checksum(self, data: bytes = None) -> str:
        target = data if data is not None else bytes(self.ecu_data)
        checksum_type = self._model_def.get('checksum', 'crc32') if self._model_def else 'crc32'
        if checksum_type == 'sum16':
            # Soma simples 16-bit (usada pela Delphi MT35E)
            total = sum(target) & 0xFFFF
            return f"{total:04x}"
        # Padrão: CRC-32
        crc = binascii.crc32(target) & 0xffffffff
        return f"{crc:08x}"

    def _validate_ecu_file(self) -> bool:
        if len(self.ecu_data) < ECU_MIN_SIZE:
            logger.warning(f"Arquivo pequeno demais ({len(self.ecu_data)} bytes)")
            return False

        expected_header = self._model_def.get('header') if self._model_def else ECU_HEADER
        if expected_header is None:
            # Modelo sem header fixo (ex: Delphi MT35E) — valida pelo tamanho
            valid_sizes = self._model_def.get('binary_sizes', []) if self._model_def else []
            if valid_sizes and len(self.ecu_data) not in valid_sizes:
                logger.warning(
                    f"Tamanho inesperado: {len(self.ecu_data)} bytes. "
                    f"Esperado para {self.model}: {valid_sizes}"
                )
                return False
            return True

        header = bytes(self.ecu_data[:ECU_HEADER_SIZE])
        if header != expected_header:
            logger.warning(f"Header inválido: {header.hex()}. Esperado: {expected_header.hex()}")
            return False
        return True

    # ── Nomes descritivos por chave de parâmetro ─────────────────────────
    _PARAM_NAMES = {
        'fuel_injection':   ("Combustível Injeção",    "Percentual de injeção"),
        'ignition_timing':  ("Avanço Ignição",          "Avanço de ignição em graus"),
        'turbo_boost_low':  ("Turbo Pressão Baixa",     "Pressão turbo em baixas RPM"),
        'turbo_boost_high': ("Turbo Pressão Alta",      "Pressão turbo em altas RPM"),
        'rpm_limit':        ("Limite RPM",              "Limite máximo de RPM"),
        'lambda_target':    ("Razão Ar-Combustível",    "Razão ar-combustível alvo"),
        'cooling_temp':     ("Temperatura Arrefecimento","Temperatura de arrefecimento"),
        'fan_activation':   ("Ativação Ventilador",     "Temperatura para ativar ventilador"),
    }

    def _initialize_parameters(self) -> Dict[str, ECUParameter]:
        # Usa definição do modelo se disponível, senão usa genérico embutido
        model_params = (self._model_def or {}).get('parameters')
        if model_params:
            param_defs = model_params
        else:
            # fallback genérico (original, para compatibilidade)
            param_defs = {
                'fuel_injection':  {'offset': 0x1000, 'size': 2, 'scale': 0.5,  'unit': '%',   'min': 0,    'max': 200},
                'ignition_timing': {'offset': 0x1100, 'size': 2, 'scale': 0.1,  'unit': '°',   'min': -20,  'max': 50},
                'turbo_boost_low': {'offset': 0x1200, 'size': 2, 'scale': 0.01, 'unit': 'bar', 'min': 0.5,  'max': 2.0},
                'turbo_boost_high':{'offset': 0x1202, 'size': 2, 'scale': 0.01, 'unit': 'bar', 'min': 0.5,  'max': 2.5},
                'rpm_limit':       {'offset': 0x1300, 'size': 2, 'scale': 1.0,  'unit': 'rpm', 'min': 5000, 'max': 9000},
                'lambda_target':   {'offset': 0x1400, 'size': 2, 'scale': 0.01, 'unit': 'λ',   'min': 0.8,  'max': 1.2},
                'cooling_temp':    {'offset': 0x1500, 'size': 1, 'scale': 1.0,  'unit': '°C',  'min': 70,   'max': 110},
                'fan_activation':  {'offset': 0x1600, 'size': 1, 'scale': 1.0,  'unit': '°C',  'min': 80,   'max': 100},
            }

        params = {}
        for key, d in param_defs.items():
            name, desc = self._PARAM_NAMES.get(key, (key, ""))
            params[key] = ECUParameter(
                name=name,
                offset=d['offset'],
                size=d['size'],
                min_val=d['min'],
                max_val=d['max'],
                scale=d['scale'],
                unit=d['unit'],
                description=desc,
            )

        for param in params.values():
            try:
                # Parâmetros com offset 0x0000 e not verified estão pendentes
                if param.offset == 0 and not (self._model_def or {}).get('parameters', {}).get(
                    next((k for k, p in params.items() if p is param), None), {}).get('verified', True):
                    continue
                raw_value = self._read_parameter(param.offset, param.size)
                if raw_value != 0:
                    param.set_value(raw_value)
            except Exception as e:
                logger.warning(f"Erro ao ler {param.name}: {e}")

        return params

    def _read_parameter(self, offset: int, size: int) -> int:
        if offset + size > len(self.ecu_data):
            raise ValueError(f"Offset {offset} com tamanho {size} fora dos limites")
        data = self.ecu_data[offset:offset + size]
        if size == 1:
            return data[0]
        elif size == 2:
            fmt = '>H' if self._byte_order == 'big' else '<H'
            return struct.unpack(fmt, data)[0]
        elif size == 4:
            fmt = '>I' if self._byte_order == 'big' else '<I'
            return struct.unpack(fmt, data)[0]
        raise ValueError(f"Tamanho não suportado: {size}")

    def _write_parameter(self, offset: int, size: int, value: int):
        if offset + size > len(self.ecu_data):
            raise ValueError(f"Offset {offset} com tamanho {size} fora dos limites")
        if size == 1:
            self.ecu_data[offset] = value & 0xFF
        elif size == 2:
            fmt = '>H' if self._byte_order == 'big' else '<H'
            self.ecu_data[offset:offset + 2] = struct.pack(fmt, value & 0xFFFF)
        elif size == 4:
            fmt = '>I' if self._byte_order == 'big' else '<I'
            self.ecu_data[offset:offset + 4] = struct.pack(fmt, value & 0xFFFFFFFF)
        else:
            raise ValueError(f"Tamanho não suportado: {size}")

    def _write_param(self, key: str):
        """Escreve o valor atual de um parâmetro no bytearray."""
        p = self.parameters[key]
        self._write_parameter(p.offset, p.size, p.get_raw_value())

    def apply_remap(self, profile: RemapProfile) -> None:
        """Aplica um perfil de remap à ECU."""
        logger.info(f"Aplicando perfil: {profile.name}")

        try:
            # Combustível: percentual sobre base stock
            fuel_base = self.parameters['fuel_injection'].value or self.STOCK_FUEL
            fuel_value = fuel_base * (1 + profile.fuel_boost / 100)
            self.parameters['fuel_injection'].set_scaled(fuel_value)
            self._write_param('fuel_injection')
            self.modifications_log.append(
                f"Combustível: {fuel_value:.1f}% ({'+' if profile.fuel_boost >= 0 else ''}{profile.fuel_boost}%)"
            )

            # Ignição: adição direta em graus (não percentual)
            ign_base = self.parameters['ignition_timing'].value or self.STOCK_IGN
            ign_value = ign_base + profile.ignition_advance
            self.parameters['ignition_timing'].set_scaled(ign_value)
            self._write_param('ignition_timing')
            self.modifications_log.append(
                f"Ignição: {ign_value:.1f}° ({'+' if profile.ignition_advance >= 0 else ''}{profile.ignition_advance}°)"
            )

            # Turbo: apenas em modelos que têm turbo
            has_turbo = (self._model_def or {}).get('has_turbo', True)
            if has_turbo and 'turbo_boost_low' in self.parameters:
                turbo_low = profile.turbo_pressure.get('low', 1.0)
                self.parameters['turbo_boost_low'].set_scaled(turbo_low)
                self._write_param('turbo_boost_low')

                turbo_high = profile.turbo_pressure.get('high', 1.2)
                self.parameters['turbo_boost_high'].set_scaled(turbo_high)
                self._write_param('turbo_boost_high')
                self.modifications_log.append(f"Turbo: {turbo_low:.2f}bar – {turbo_high:.2f}bar")

            # RPM Limite
            self.parameters['rpm_limit'].set_scaled(profile.rpm_limit)
            self._write_param('rpm_limit')
            self.modifications_log.append(f"RPM Limite: {profile.rpm_limit}")

            # Lambda
            self.parameters['lambda_target'].set_scaled(profile.lambda_target)
            self._write_param('lambda_target')
            self.modifications_log.append(f"Lambda: {profile.lambda_target:.2f}")

            # Temperatura arrefecimento
            self.parameters['cooling_temp'].set_scaled(profile.cooling_temp)
            self._write_param('cooling_temp')
            self.modifications_log.append(f"Arrefecimento: {profile.cooling_temp}°C")

            logger.info(f"Remap aplicado com sucesso! {len(self.modifications_log)} parâmetros modificados")

        except Exception as e:
            logger.error(f"Erro ao aplicar remap: {e}")
            raise

    @staticmethod
    def calculate_performance_gain(profile: RemapProfile) -> Dict[str, float]:
        """Estima ganho de performance com fórmula linear realista."""
        turbo_high = profile.turbo_pressure.get('high', TURBO_BASE)
        turbo_gain = (turbo_high - TURBO_BASE) / TURBO_BASE * 50

        power_gain = (
            profile.fuel_boost * 0.5 +
            profile.ignition_advance * 1.0 +
            turbo_gain
        )
        torque_gain = power_gain * 1.15

        return {
            'power_gain_percent': round(power_gain, 2),
            'torque_gain_percent': round(torque_gain, 2),
            'estimated_power': round(100 * (1 + power_gain / 100), 2),
            'estimated_torque': round(100 * (1 + torque_gain / 100), 2)
        }

    def get_status(self) -> Dict:
        return {
            'model': self.model,
            'model_name': (self._model_def or {}).get('name', self.model),
            'has_turbo': (self._model_def or {}).get('has_turbo', True),
            'byte_order': self._byte_order,
            'size_bytes': len(self.ecu_data),
            'original_hash': self.original_hash,
            'current_hash': hashlib.sha256(bytes(self.ecu_data)).hexdigest(),
            'original_checksum': self.original_checksum,
            'current_checksum': self._calculate_checksum(),
            'parameters': {name: param.value for name, param in self.parameters.items()},
            'modifications': self.modifications_log,
            'valid': self._validate_ecu_file()
        }

    @staticmethod
    def load_from_file(filepath: str, model: str = 'generic', validate: bool = True) -> 'ECURemap':
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        with open(path, 'rb') as f:
            ecu_data = f.read()
        # Auto-detecta modelo pelo tamanho se não especificado
        if model == 'generic' and ECU_MODELS:
            for model_id, mdef in ECU_MODELS.items():
                sizes = mdef.get('binary_sizes', [])
                if len(ecu_data) in sizes and model_id != 'generic':
                    logger.info(f"Modelo auto-detectado pelo tamanho: {model_id}")
                    model = model_id
                    break
        logger.info(f"ECU carregada de: {filepath} ({len(ecu_data)} bytes)")
        ecu = ECURemap(ecu_data, model=model, validate=validate)
        return ecu

    def save_to_file(self, filepath: str, create_backup: bool = True) -> None:
        path = Path(filepath)

        if create_backup and path.exists():
            backup_path = path.with_stem(
                path.stem + "_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            # Salva os dados ORIGINAIS (antes do remap) no backup
            with open(backup_path, 'wb') as f:
                f.write(self._original_data)
            logger.info(f"Backup do original criado: {backup_path}")

        with open(path, 'wb') as f:
            f.write(self.ecu_data)
        logger.info(f"ECU salva em: {filepath}")

    def export_report(self, filepath: str = "remap_report.txt") -> None:
        report = [
            "=" * 60,
            "RELATÓRIO DE REMAP ECU",
            "=" * 60,
            f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Modelo ECU: {self.model}",
            f"Tamanho: {len(self.ecu_data)} bytes",
            "",
            "PARÂMETROS ATUAIS:",
            "-" * 60
        ]

        for name, param in self.parameters.items():
            if param.value is not None:
                report.append(
                    f"{param.name:30} {param.value:10.2f} {param.unit:10} ({param.description})"
                )

        report.extend(["", "MODIFICAÇÕES REALIZADAS:", "-" * 60])
        for mod in self.modifications_log:
            report.append(f"  • {mod}")

        report.extend([
            "",
            "INTEGRIDADE:",
            "-" * 60,
            f"Hash Original: {self.original_hash}",
            f"Hash Atual:    {hashlib.sha256(bytes(self.ecu_data)).hexdigest()}",
            f"Checksum Original: {self.original_checksum}",
            f"Checksum Atual:    {self._calculate_checksum()}",
            "=" * 60
        ])

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        logger.info(f"Relatório exportado: {filepath}")


# Perfis padrão pré-definidos
PRESET_PROFILES = {
    'eco': RemapProfile(
        name="Eco - Economia",
        fuel_boost=-5,
        ignition_advance=-2,
        turbo_pressure={'low': 0.9, 'high': 1.0},
        rpm_limit=6500,
        lambda_target=1.05
    ),
    'stock': RemapProfile(
        name="Stock - Padrão de Fábrica",
        fuel_boost=0,
        ignition_advance=0,
        turbo_pressure={'low': 1.0, 'high': 1.2},
        rpm_limit=7000,
        lambda_target=0.95
    ),
    'sport': RemapProfile(
        name="Sport - Performance",
        fuel_boost=20,
        ignition_advance=8,
        turbo_pressure={'low': 1.2, 'high': 1.5},
        rpm_limit=7500,
        lambda_target=0.88
    ),
    'extreme': RemapProfile(
        name="Extreme - Máxima Potência",
        fuel_boost=35,
        ignition_advance=12,
        turbo_pressure={'low': 1.4, 'high': 1.8},
        rpm_limit=8000,
        lambda_target=0.85,
        cooling_temp=85
    ),
}
