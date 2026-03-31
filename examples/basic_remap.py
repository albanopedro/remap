"""
Exemplo Básico - ECU Remap
Demonstra como usar a ferramenta para fazer remap simples
"""

import sys
from pathlib import Path

# Adicionar caminho do src
sys.path.insert(0, Path(__file__).parent.parent / 'src')

from ecu_remap import ECURemap, RemapProfile, PRESET_PROFILES


def example_1_basic_remap():
    """Exemplo 1: Remap básico com perfil predefinido"""
    print("\n" + "="*60)
    print("EXEMPLO 1: Remap Básico com Perfil Sport")
    print("="*60)
    
    # ✓ Nota: Em produção, você usaria um arquivo ECU real
    # Criar dados ECU simulados (512KB)
    ecu_data = bytearray(512 * 1024)
    ecu_data[0:4] = b'ECU!'  # Header
    
    # Carregar ECU
    ecu = ECURemap(ecu_data)
    print("\n[✓] ECU carregada com sucesso")
    print(f"    Modelo: {ecu.model}")
    print(f"    Tamanho: {len(ecu_data)} bytes")
    
    # Aplicar perfil Sport
    profile = PRESET_PROFILES['sport']
    print(f"\n[✓] Aplicando perfil: {profile.name}")
    ecu.apply_remap(profile)
    
    # Mostrar resultados
    status = ecu.get_status()
    print("\n[✓] Status após remap:")
    print(f"    Combustível: {ecu.parameters['fuel_injection'].value:.2f}%")
    print(f"    Ignição: {ecu.parameters['ignition_timing'].value:.2f}°")
    print(f"    Turbo: {ecu.parameters['turbo_boost_low'].value:.2f}bar - {ecu.parameters['turbo_boost_high'].value:.2f}bar")
    print(f"    RPM Limite: {int(ecu.parameters['rpm_limit'].value)}rpm")
    
    # Salvar
    output_dir = Path(__file__).parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "ecu_sport_remapped.bin"
    ecu.save_to_file(str(output_file), create_backup=False)
    print(f"\n[✓] ECU remapeada salva em: {output_file}")


def example_2_custom_profile():
    """Exemplo 2: Criar perfil customizado"""
    print("\n" + "="*60)
    print("EXEMPLO 2: Perfil Customizado Balanceado")
    print("="*60)
    
    # Criar ECU
    ecu_data = bytearray(512 * 1024)
    ecu = ECURemap(ecu_data)
    
    # Criar perfil customizado
    custom_profile = RemapProfile(
        name="Balanced Tuning",
        fuel_boost=15,               # +15% de combustível
        ignition_advance=6,          # +6° de avanço
        turbo_pressure={
            'low': 1.15,             # 1.15 bar em baixas RPM
            'high': 1.45              # 1.45 bar em altas RPM
        },
        rpm_limit=7200,
        lambda_target=0.90,
        cooling_temp=88              # Temperatura mais agressiva
    )
    
    print(f"\n[✓] Perfil criado: {custom_profile.name}")
    print(f"    Combustível: +{custom_profile.fuel_boost}%")
    print(f"    Ignição: +{custom_profile.ignition_advance}°")
    print(f"    Turbo: {custom_profile.turbo_pressure['low']}bar - {custom_profile.turbo_pressure['high']}bar")
    
    # Aplicar
    ecu.apply_remap(custom_profile)
    
    # Calcular ganhos estimados
    gains = ecu.calculate_performance_gain(custom_profile)
    print(f"\n[✓] Ganhos de Performance Estimados:")
    print(f"    Potência: +{gains['power_gain_percent']}%")
    print(f"    Torque: +{gains['torque_gain_percent']}%")
    print(f"    Potência Estimada: {gains['estimated_power']}hp")
    print(f"    Torque Estimado: {gains['estimated_torque']}Nm")


def example_3_comparar_perfis():
    """Exemplo 3: Comparar diferentes perfis de remap"""
    print("\n" + "="*60)
    print("EXEMPLO 3: Comparação de Perfis")
    print("="*60)
    
    profiles_to_compare = ['eco', 'stock', 's
    ecu = ECURemap(bytearray(512 * 1024), validate=False)port', 'extreme']
    
    print("\nComparação de Características:")
    print("-" * 80)
    print(f"{'Perfil':<20} {'Combustível':<15} {'Ignição':<12} {'Turbo (bar)':<20} {'RPM':<10}")
    print("-" * 80)
    
    for profile_name in profiles_to_compare:
        profile = PRESET_PROFILES[profile_name]
        turbo_str = f"{profile.turbo_pressure['low']:.1f}-{profile.turbo_pressure['high']:.1f}"
        print(
            f"{profile_name:<20} +{profile.fuel_boost:>6.1f}%        "
            f"+{profile.ignition_advance:>6.1f}°       {turbo_str:<20} {profile.rpm_limit:<10}"
        )
    
    print("\n" + "="*60)
    print("Ganhos de Performance Estimados:")
    print("="*60)
    
    ecu = ECURemap(bytearray(512 * 1024))
    
    for profile_name in profiles_to_compare:
        profile = PRESET_PROFILES[profile_name]
        gains = ecu.calculate_performance_gain(profile)
        print(
            f"{profile_name.upper():<15} "
            f"Potência: +{gains['power_gain_percent']:>6.2f}%  "
            f"Torque: +{gains['torque_gain_percent']:>6.2f}%"
        )


def example_4_salvar_relatorio():
    """Exemplo 4: Gerar relatório de modificações"""
    print("\n" + "="*60)
    print("EXEMPLO 4: Exportar Relatório")
    print("="*60)
    
    # Criar e remapear
    ecu_data = bytearray(512 * 1024)
    ecu = ECURemap(ecu_data)
    
    profile = PRESET_PROFILES['sport']
    ecu.apply_remap(profile)
    
    # Exportar relatório
    report_file = "/tmp/remap_report.txt"
    ecu.export_report(report_file)
    
    print(f"\n[✓] Relatório exportado: {report_file}")
    print("\nConteúdo do relatório:")
    print("-" * 60)
    
    with open(report_file, 'r', encoding='utf-8') as f:
        print(f.read())


if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("  ECU REMAP - EXEMPLOS DE USO")
    print("█" * 60)
    
    try:
        example_1_basic_remap()
        example_2_custom_profile()
        example_3_comparar_perfis()
        example_4_salvar_relatorio()
        
        print("\n" + "█" * 60)
        print("  ✓ Todos os exemplos executados com sucesso!")
        print("█" * 60 + "\n")
        
    except Exception as e:
        print(f"\n[✗] Erro: {e}")
        import traceback
        traceback.print_exc()
