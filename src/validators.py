"""
Validadores - ECU Remap
Funções de validação robustas
"""

from typing import Dict, Tuple
from .exceptions import ECUValidationError
import logging

logger = logging.getLogger(__name__)


class ECUValidator:
    """Valida integridade e parâmetros da ECU"""
    
    @staticmethod
    def validate_file(ecu_data: bytes) -> bool:
        """Valida arquivo ECU básico"""
        if not ecu_data:
            raise ECUValidationError("Arquivo ECU vazio")
        
        # Tamanhos típicos de ECU
        valid_sizes = [256 * 1024, 512 * 1024, 1024 * 1024, 2048 * 1024]
        
        if len(ecu_data) not in valid_sizes:
            logger.warning(
                f"Tamanho incomum: {len(ecu_data)} bytes. "
                f"Esperado um de: {valid_sizes}"
            )
        
        return True
    
    @staticmethod
    def validate_parameter_range(
        param_name: str,
        value: float,
        min_val: float,
        max_val: float,
        strict: bool = False
    ) -> Tuple[bool, str]:
        """
        Valida se parâmetro está dentro do range
        
        Returns:
            (is_valid, message)
        """
        if value < min_val or value > max_val:
            severity = "ERROR" if strict else "WARNING"
            msg = (
                f"[{severity}] {param_name}: {value} fora do range "
                f"[{min_val}, {max_val}]"
            )
            
            if strict:
                raise ECUValidationError(msg)
            else:
                logger.warning(msg)
                return False, msg
        
        return True, f"OK: {param_name} = {value}"
    
    @staticmethod
    def validate_offset(offset: int, size: int, ecu_size: int) -> bool:
        """Valida se offset é válido"""
        if offset < 0:
            raise ECUValidationError(f"Offset negativo: {offset}")
        
        if offset + size > ecu_size:
            raise ECUValidationError(
                f"Offset {offset} + size {size} excede tamanho da ECU {ecu_size}"
            )
        
        return True
    
    @staticmethod
    def validate_profile(profile_dict: Dict) -> bool:
        """Valida dicionário de perfil"""
        required_fields = ['fuel_boost', 'ignition_advance', 'turbo_pressure', 'rpm_limit']
        
        for field in required_fields:
            if field not in profile_dict:
                raise ECUValidationError(f"Campo obrigatório ausente: {field}")
        
        # Validar ranges
        validations = [
            ('fuel_boost', profile_dict['fuel_boost'], 0, 50),
            ('ignition_advance', profile_dict['ignition_advance'], 0, 15),
            ('rpm_limit', profile_dict['rpm_limit'], 5000, 9000),
        ]
        
        for param_name, value, min_v, max_v in validations:
            if not (min_v <= value <= max_v):
                raise ECUValidationError(
                    f"{param_name} fora do range [{min_v}, {max_v}]: {value}"
                )
        
        return True
    
    @staticmethod
    def validate_checksum(ecu_data: bytes, checksum: bytes) -> bool:
        """Valida checksum do arquivo ECU (se aplicável)"""
        # Diferentes ECUs usam diferentes algoritmos
        # Implementação básica com XOR
        calculated = 0
        for byte in ecu_data:
            calculated ^= byte
        
        return True  # Simplificado para exemplo


class ParameterValidator:
    """Valida parâmetros individuais"""
    
    @staticmethod
    def validate_fuel_boost(value: float) -> bool:
        """Valida boost de combustível"""
        if not (0 <= value <= 50):
            raise ECUValidationError(f"Combustível deve estar entre 0-50%, recebido {value}")
        
        if value > 30:
            logger.warning(f"Combustível muito elevado ({value}%) - risco de motor rico")
        
        return True
    
    @staticmethod
    def validate_ignition_advance(value: float) -> bool:
        """Valida avanço de ignição"""
        if not (0 <= value <= 15):
            raise ECUValidationError(f"Ignição deve estar entre 0-15°, recebido {value}")
        
        if value > 10:
            logger.warning(f"Avanço de ignição agressivo ({value}°) - monitorar batidas")
        
        return True
    
    @staticmethod
    def validate_turbo_pressure(pressure: float, position: str = "low") -> bool:
        """Valida pressão de turbo"""
        if position == "low":
            if not (0.5 <= pressure <= 1.8):
                raise ECUValidationError(
                    f"Turbo pressão baixa deve estar entre 0.5-1.8 bar, recebido {pressure}"
                )
        elif position == "high":
            if not (0.5 <= pressure <= 2.5):
                raise ECUValidationError(
                    f"Turbo pressão alta deve estar entre 0.5-2.5 bar, recebido {pressure}"
                )
        
        if pressure > 1.6:
            logger.warning(f"Pressão de turbo elevada ({pressure} bar) - verificar arrefecimento")
        
        return True
    
    @staticmethod
    def validate_rpm_limit(value: int) -> bool:
        """Valida limite de RPM"""
        if not (5000 <= value <= 9000):
            raise ECUValidationError(f"RPM deve estar entre 5000-9000, recebido {value}")
        
        return True
    
    @staticmethod
    def validate_lambda(value: float) -> bool:
        """Valida razão ar-combustível"""
        if not (0.8 <= value <= 1.2):
            raise ECUValidationError(f"Lambda deve estar entre 0.8-1.2, recebido {value}")
        
        if value < 0.85:
            logger.warning(f"Lambda muito rica ({value}) - risco de combustão ruim")
        
        return True


class SecurityValidator:
    """Validações de segurança"""
    
    @staticmethod
    def check_safety_levels(profile_dict: Dict) -> Dict[str, bool]:
        """Realiza verificações de segurança"""
        checks = {
            'fuel_safe': profile_dict['fuel_boost'] <= 40,
            'ignition_safe': profile_dict['ignition_advance'] <= 12,
            'turbo_safe': profile_dict['turbo_pressure'].get('high', 1.2) <= 1.8,
            'rpm_safe': profile_dict['rpm_limit'] <= 8000,
        }
        
        unsafe = [k for k, v in checks.items() if not v]
        if unsafe:
            logger.warning(f"Validações de segurança falharam: {unsafe}")
        
        return checks
    
    @staticmethod
    def get_safety_score(profile_dict: Dict) -> float:
        """Calcula score de segurança 0-100"""
        score = 100.0
        
        # Deduzir pontos por agressividade
        score -= (profile_dict['fuel_boost'] / 50) * 20
        score -= (profile_dict['ignition_advance'] / 15) * 15
        
        turbo_high = profile_dict['turbo_pressure'].get('high', 1.2)
        score -= ((turbo_high - 1.2) / 0.8) * 25
        
        return max(0, min(100, score))
