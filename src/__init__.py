"""
ECU Remap - Reprogramação Eletrônica Automotiva
Ferramenta profissional para otimização de performance
"""

__version__ = "1.0.0"
__author__ = "ECU Remap Team"
__description__ = "Ferramenta de reprogramação eletrônica (remap) de ECU automotiva"

from .ecu_remap import ECURemap, RemapProfile, ECUParameter, PRESET_PROFILES
from .exceptions import (
    ECURemapException,
    ECULoadError,
    ECUValidationError,
    ECUParameterError,
    InvalidProfileError,
    RemapApplicationError,
    IntegrityCheckError
)
from .validators import ECUValidator, ParameterValidator, SecurityValidator

__all__ = [
    'ECURemap',
    'RemapProfile', 
    'ECUParameter',
    'PRESET_PROFILES',
    'ECURemapException',
    'ECULoadError',
    'ECUValidationError',
    'ECUParameterError',
    'InvalidProfileError',
    'RemapApplicationError',
    'IntegrityCheckError',
    'ECUValidator',
    'ParameterValidator',
    'SecurityValidator',
]
