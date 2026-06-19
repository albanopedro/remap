"""
Exemplo Básico - ECU Remap
Demonstra como usar a ferramenta para fazer remap simples
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from ecu_remap import ECURemap, RemapProfile, PRESET_PROFILES


def example_1_basic_remap():
    print("\n" + "=" * 60)
    print("EXEMPLO 1: Remap Básico com Perfil Sport")
    print("=" * 60)

    ecu_data = bytearray(512 * 1024)
    ecu_data[0:4] = b'ECU!'

    ecu = ECURemap(ecu_data)
    print("\n[✓] ECU carregada com sucesso")
    print(f"    Modelo: {ecu.model}")
    print(f"    Tamanho: {len(ecu_data)} bytes")

    profile = PRESET_PROFILES['sport']
    print(f"\n[✓] Aplicando perfil: {profile.name}")
    ecu.apply_remap(profile)

    print("\n[✓] Status após remap:")
    print(f"    Combustível: {ecu.parameters['fuel_injection'].value:.2f}%")
    print(f"    Ignição: {ecu.parameters['ignition_timing'].value:.2f}°")
    print(f"    Turbo: {ecu.parameters['turbo_boost_low'].value:.2f}bar - {ecu.parameters['turbo_boost_high'].value:.2f}bar")
    print(f"    RPM Limite: {int(ecu.parameters['rpm_limit'].value)}rpm")

    output_dir = Path(__file__).parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "ecu_sport_remapped.bin"
    ecu.save_to_file(str(output_file), create_backup=False)
    print(f"\n[✓] ECU remapeada salva em: {output_file}")


def example_2_custom_profile():
    print("\n" + "=" * 60)
    print("EXEMPLO 2: Perfil Customizado Balanceado")
    print("=" * 60)

    ecu_data = bytearray(512 * 1024)
    ecu = ECURemap(ecu_data, validate=False)

    custom_profile = RemapProfile(
        name="Balanced Tuning",
        fuel_boost=15,
        ignition_advance=6,
        turbo_pressure={'low': 1.15, 'high': 1.45},
        rpm_limit=7200,
        lambda_target=0.90,
        cooling_temp=88
    )

    print(f"\n[✓] Perfil criado: {custom_profile.name}")
    print(f"    Combustível: +{custom_profile.fuel_boost}%")
    print(f"    Ignição: +{custom_profile.ignition_advance}°")
    print(f"    Turbo: {custom_profile.turbo_pressure['low']}bar - {custom_profile.turbo_pressure['high']}bar")

    ecu.apply_remap(custom_profile)

    gains = ecu.calculate_performance_gain(custom_profile)
    print(f"\n[✓] Ganhos de Performance Estimados:")
    print(f"    Potência: +{gains['power_gain_percent']}%")
    print(f"    Torque: +{gains['torque_gain_percent']}%")
    print(f"    Potência Estimada: {gains['estimated_power']}hp")
    print(f"    Torque Estimado: {gains['estimated_torque']}Nm")


def example_3_comparar_perfis():
    print("\n" + "=" * 60)
    print("EXEMPLO 3: Comparação de Perfis")
    print("=" * 60)

    profiles_to_compare = ['eco', 'stock', 'sport', 'extreme']
    ecu = ECURemap(bytearray(512 * 1024), validate=False)

    print("\nComparação de Características:")
    print("-" * 80)
    print(f"{'Perfil':<20} {'Combustível':<15} {'Ignição':<12} {'Turbo (bar)':<20} {'RPM':<10}")
    print("-" * 80)

    for profile_name in profiles_to_compare:
        profile = PRESET_PROFILES[profile_name]
        fuel_sign = '+' if profile.fuel_boost >= 0 else ''
        ign_sign = '+' if profile.ignition_advance >= 0 else ''
        turbo_str = f"{profile.turbo_pressure['low']:.1f}-{profile.turbo_pressure['high']:.1f}"
        print(
            f"{profile_name:<20} {fuel_sign}{profile.fuel_boost:>6.1f}%        "
            f"{ign_sign}{profile.ignition_advance:>6.1f}°       {turbo_str:<20} {profile.rpm_limit:<10}"
        )

    print("\n" + "=" * 60)
    print("Ganhos de Performance Estimados:")
    print("=" * 60)

    for profile_name in profiles_to_compare:
        profile = PRESET_PROFILES[profile_name]
        gains = ecu.calculate_performance_gain(profile)
        sign = '+' if gains['power_gain_percent'] >= 0 else ''
        print(
            f"{profile_name.upper():<15} "
            f"Potência: {sign}{gains['power_gain_percent']:>6.2f}%  "
            f"Torque: {sign}{gains['torque_gain_percent']:>6.2f}%"
        )


def example_4_salvar_relatorio():
    print("\n" + "=" * 60)
    print("EXEMPLO 4: Exportar Relatório")
    print("=" * 60)

    ecu_data = bytearray(512 * 1024)
    ecu = ECURemap(ecu_data, validate=False)

    profile = PRESET_PROFILES['sport']
    ecu.apply_remap(profile)

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
