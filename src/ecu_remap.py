"""
ECU Remap - Sistema de Reprogramação Eletrônica Automotiva
Módulo principal para manipulação, análise e modificação de arquivos ECU
"""

import struct
import hashlib
import binascii
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes
ECU_HEADER = b'ECU!'
ECU_HEADER_SIZE = 4
ECU_MIN_SIZE = 1024  # Tamanho mínimo de um arquivo ECU (1KB)


class RemapProfile:
    """Define um perfil de otimização para remap da ECU"""
    
    def __init__(
        self,
        name: str = "Custom Remap",
        fuel_boost: float = 0,      # % boost (0-50)
        ignition_advance: float = 0, # graus (0-15)
        turbo_pressure: Optional[Dict[str, float]] = None,  # bar
        rpm_limit: int = 7500,
        lambda_target: float = 0.9,  # Razão ar-combustível
        cooling_temp: int = 90,      # °C
        safety_margin: float = 0.95  # 95% dos limites
    ):
        self.name = name
        self.fuel_boost = max(0, min(fuel_boost, 50))
        self.ignition_advance = max(0, min(ignition_advance, 15))
        self.turbo_pressure = turbo_pressure or {"low": 1.0, "high": 1.2}
        self.rpm_limit = max(5000, min(rpm_limit, 9000))
        self.lambda_target = max(0.8, min(lambda_target, 1.1))
        self.cooling_temp = max(70, min(cooling_temp, 110))
        self.safety_margin = max(0.85, min(safety_margin, 1.0))
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Converte perfil para dicionário"""
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
        return f"RemapProfile({self.name}): +{self.fuel_boost}% fuel, +{self.ignition_advance}° ign, {self.rpm_limit}rpm"


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
        """Define valor bruto e converte para valor real"""
        scaled = raw_value * self.scale
        if self.min_val <= scaled <= self.max_val:
            self.value = scaled
        else:
            logger.warning(f"Valor {scaled}{self.unit} fora do range [{self.min_val}, {self.max_val}] para {self.name}")
            self.value = max(self.min_val, min(scaled, self.max_val))
    
    def get_raw_value(self) -> int:
        """Retorna valor em formato bruto para ECU"""
        return int(self.value / self.scale)
    
    def modify(self, percent_change: float) -> float:
        """Modifica parâmetro por percentual e retorna novo valor"""
        if self.value is None:
            return self.min_val
        
        new_value = self.value * (1 + percent_change / 100)
        self.value = max(self.min_val, min(new_value, self.max_val))
        return self.value


class ECURemap:
    """Classe principal para manipulação de arquivos ECU"""
    
    # Modelos suportados e seus parâmetros
    SUPPORTED_MODELS = ['generic', 'bosch', 'siemens', 'delco']
    
    def __init__(self, ecu_data: bytes, model: str = "generic", validate: bool = True):
        self.ecu_data = bytearray(ecu_data)
        self.model = model.lower() if model.lower() in self.SUPPORTED_MODELS else "generic"
        self.original_hash = hashlib.sha256(self.ecu_data).hexdigest()
        self.original_checksum = self._calculate_checksum()
        self.parameters = self._initialize_parameters()
        self.modifications_log: List[str] = []
        logger.info(f"ECU carregada: {len(self.ecu_data)} bytes, modelo: {self.model}, checksum: {self.original_checksum}")
    
    def _calculate_checksum(self) -> str:
        """Calcula checksum CRC-32 dos dados da ECU"""
        crc = binascii.crc32(self.ecu_data) & 0xffffffff
        return f"{crc:08x}"
    
    def _validate_ecu_file(self) -> bool:
        """Valida se é um arquivo ECU válido"""
        if len(self.ecu_data) < ECU_MIN_SIZE:
            logger.warning(f"Arquivo pequeno demais ({len(self.ecu_data)} bytes)")
            return False
        
        # Verificar header ECU
        header = bytes(self.ecu_data[:ECU_HEADER_SIZE])
        if header != ECU_HEADER:
            logger.warning(f"Header inválido: {header.hex()}. Esperado: {ECU_HEADER.hex()}")
            return False
        
        return True
    
    def _initialize_parameters(self) -> Dict[str, ECUParameter]:
        """Inicializa parâmetros conhecidos da ECU"""
        params = {
            'fuel_injection': ECUParameter(
                "Combustível Injeção", 0x1000, 2, 0, 200, 0.5, "%", "Percentual de injeção"
            ),
            'ignition_timing': ECUParameter(
                "Avanço Ignição", 0x1100, 2, -20, 50, 0.1, "°", "Avanço de ignição em graus"
            ),
            'turbo_boost_low': ECUParameter(
                "Turbo Pressão Baixa", 0x1200, 2, 0.5, 2.0, 0.01, "bar", "Pressão turbo em baixas RPM"
            ),
            'turbo_boost_high': ECUParameter(
                "Turbo Pressão Alta", 0x1202, 2, 0.5, 2.5, 0.01, "bar", "Pressão turbo em altas RPM"
            ),
            'rpm_limit': ECUParameter(
                "Limite RPM", 0x1300, 2, 5000, 9000, 1.0, "rpm", "Limite máximo de RPM"
            ),
            'lambda_target': ECUParameter(
                "Razão Ar-Combustível", 0x1400, 2, 0.8, 1.2, 0.01, "λ", "Razão ar-combustível alvo"
            ),
            'cooling_temp': ECUParameter(
                "Temperatura Arrefecimento", 0x1500, 1, 70, 110, 1.0, "°C", "Temperatura de arrefecimento"
            ),
            'fan_activation': ECUParameter(
                "Ativação Ventilador", 0x1600, 1, 80, 100, 1.0, "°C", "Temperatura para ativar ventilador"
            ),
        }
        
        # Carregar valores atuais do arquivo ECU
        for param in params.values():
            try:
                raw_value = self._read_parameter(param.offset, param.size)
                param.set_value(raw_value)
            except Exception as e:
                logger.warning(f"Erro ao ler {param.name}: {e}")
        
        return params
    
    def _read_parameter(self, offset: int, size: int) -> int:
        """Lê valor bruto da ECU em um offset específico"""
        if offset + size > len(self.ecu_data):
            raise ValueError(f"Offset {offset} com tamanho {size} fora dos limites")
        
        data = self.ecu_data[offset:offset + size]
        if size == 1:
            return data[0]
        elif size == 2:
            return struct.unpack('<H', data)[0]
        elif size == 4:
            return struct.unpack('<I', data)[0]
        else:
            raise ValueError(f"Tamanho não suportado: {size}")
    
    def _write_parameter(self, offset: int, size: int, value: int):
        """Escreve valor bruto na ECU em um offset específico"""
        if offset + size > len(self.ecu_data):
            raise ValueError(f"Offset {offset} com tamanho {size} fora dos limites")
        
        if size == 1:
            self.ecu_data[offset] = value & 0xFF
        elif size == 2:
            data = struct.pack('<H', value & 0xFFFF)
            self.ecu_data[offset:offset + 2] = data
        elif size == 4:
            data = struct.pack('<I', value & 0xFFFFFFFF)
            self.ecu_data[offset:offset + 4] = data
        else:
            raise ValueError(f"Tamanho não suportado: {size}")
    
    def apply_remap(self, profile: RemapProfile) -> None:
        """Aplica um perfil de remap à ECU"""
        logger.info(f"Aplicando perfil: {profile.name}")
        
        try:
            # Combustível
            self.parameters['fuel_injection'].modify(profile.fuel_boost)
            self._write_parameter(
                self.parameters['fuel_injection'].offset,
                self.parameters['fuel_injection'].size,
                self.parameters['fuel_injection'].get_raw_value()
            )
            self.modifications_log.append(f"Combustível: +{profile.fuel_boost}%")
            
            # Ignição (CORREÇÃO: graus direto, não dividir por 100)
            self.parameters['ignition_timing'].modify(profile.ignition_advance)
            self._write_parameter(
                self.parameters['ignition_timing'].offset,
                self.parameters['ignition_timing'].size,
                self.parameters['ignition_timing'].get_raw_value()
            )
            self.modifications_log.append(f"Ignição: +{profile.ignition_advance}°")
            
            # Turbo - Pressão Baixa
            turbo_low = profile.turbo_pressure.get('low', 1.0)
            self.parameters['turbo_boost_low'].value = turbo_low
            self._write_parameter(
                self.parameters['turbo_boost_low'].offset,
                self.parameters['turbo_boost_low'].size,
                self.parameters['turbo_boost_low'].get_raw_value()
            )
            
            # Turbo - Pressão Alta
            turbo_high = profile.turbo_pressure.get('high', 1.2)
            self.parameters['turbo_boost_high'].value = turbo_high
            self._write_parameter(
                self.parameters['turbo_boost_high'].offset,
                self.parameters['turbo_boost_high'].size,
                self.parameters['turbo_boost_high'].get_raw_value()
            )
            self.modifications_log.append(f"Turbo: {turbo_low}bar - {turbo_high}bar")
            
            # RPM Limit
            self.parameters['rpm_limit'].value = profile.rpm_limit
            self._write_parameter(
                self.parameters['rpm_limit'].offset,
                self.parameters['rpm_limit'].size,
                self.parameters['rpm_limit'].get_raw_value()
            )
            self.modifications_log.append(f"RPM Limite: {profile.rpm_limit}")
            
            # Lambda target
            self.parameters['lambda_target'].value = profile.lambda_target
            self._write_parameter(
                self.parameters['lambda_target'].offset,
                self.parameters['lambda_target'].size,
                self.parameters['lambda_target'].get_raw_value()
            )
            self.modifications_log.append(f"Lambda: {profile.lambda_target}")
            
            # Temperatura arrefecimento
            self.parameters['cooling_temp'].value = profile.cooling_temp
            self._write_parameter(
                self.parameters['cooling_temp'].offset,
                self.parameters['cooling_temp'].size,
                int(profile.cooling_temp)
            )
            self.modifications_log.append(f"Arrefecimento: {profile.cooling_temp}°C")
            
            logger.info(f"Remap aplicado com sucesso! {len(self.modifications_log)} parâmetros modificados")
        
        except Exception as e:
            logger.error(f"Erro ao aplicar remap: {e}")
            raise
    
    def calculate_performance_gain(self, profile: RemapProfile) -> Dict[str, float]:
        """Estima ganho de performance"""
        base_power = 100  # Potência base relativa
        
        fuel_factor = 1 + (profile.fuel_boost / 100)
        ignition_factor = 1 + (profile.ignition_advance / 100)
        turbo_factor = profile.turbo_pressure.get('high', 1.2) / 1.0
        
        power_gain = (fuel_factor * ignition_factor * turbo_factor - 1) * 100
        torque_gain = power_gain * 1.1  # Torque tipicamente aumenta mais
        
        return {
            'power_gain_percent': round(power_gain, 2),
            'torque_gain_percent': round(torque_gain, 2),
            'estimated_power': round(base_power * (1 + power_gain / 100), 2),
            'estimated_torque': round(100 * (1 + torque_gain / 100), 2)
        }
    
    def get_status(self) -> Dict:
        """Retorna status current da ECU"""
        return {
            'model': self.model,
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
    def load_from_file(filepath: str, validate: bool = True) -> 'ECURemap':
        """Carrega arquivo ECU e valida integridade"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        with open(path, 'rb') as f:
            ecu_data = f.read()
        
        logger.info(f"ECU carregada de: {filepath} ({len(ecu_data)} bytes)")
        
        ecu = ECURemap(ecu_data, validate=False)
        
        if validate:
            if not ecu._validate_ecu_file():
                logger.warning(f"Arquivo ECU inválido: {filepath}")
        
        return ecu
    
    def save_to_file(self, filepath: str, create_backup: bool = True) -> None:
        """Salva arquivo ECU remapeado"""
        path = Path(filepath)
        
        # Criar backup do original se solicitado
        if create_backup and path.exists():
            backup_path = path.with_stem(path.stem + "_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
            with open(backup_path, 'wb') as f:
                f.write(self.ecu_data)
            logger.info(f"Backup criado: {backup_path}")
        
        with open(path, 'wb') as f:
            f.write(self.ecu_data)
        
        logger.info(f"ECU salva em: {filepath}")
    
    def export_report(self, filepath: str = "remap_report.txt") -> None:
        """Exporta relatório de modificações"""
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
                report.append(f"{param.name:30} {param.value:10.2f} {param.unit:10} ({param.description})")
        
        report.extend([
            "",
            "MODIFICAÇÕES REALIZADAS:",
            "-" * 60
        ])
        
        for mod in self.modifications_log:
            report.append(f"  • {mod}")
        
        report.extend([
            "",
            "INTEGRIDADE:",
            "-" * 60,
            f"Hash Original: {self.original_hash}",
            f"Hash Atual:    {hashlib.sha256(bytes(self.ecu_data)).hexdigest()}",
            f"Checksum Original: {self.original_checksum}",
            f"Checksum Atual: {self._calculate_checksum()}",
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
        rpm_limit=6500
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
    'stock': RemapProfile(
        name="Stock - Padrão de Fábrica",
        fuel_boost=0,
        ignition_advance=0,
        turbo_pressure={'low': 1.0, 'high': 1.2},
        rpm_limit=7000
    )
}
