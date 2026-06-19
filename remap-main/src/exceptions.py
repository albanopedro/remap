"""
Exceções Customizadas - ECU Remap
"""


class ECURemapException(Exception):
    """Exceção base para ECU Remap"""
    pass


class ECULoadError(ECURemapException):
    """Erro ao carregar arquivo ECU"""
    pass


class ECUValidationError(ECURemapException):
    """Erro na validação de parâmetros"""
    pass


class ECUParameterError(ECURemapException):
    """Erro ao manipular parâmetro"""
    pass


class InvalidProfileError(ECURemapException):
    """Erro em perfil de remap inválido"""
    pass


class RemapApplicationError(ECURemapException):
    """Erro ao aplicar remap"""
    pass


class IntegrityCheckError(ECURemapException):
    """Erro na verificação de integridade"""
    pass
