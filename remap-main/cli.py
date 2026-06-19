#!/usr/bin/env python3
"""
ECU Remap CLI - Interface de Linha de Comando
Ferramenta interativa para remap de ECU automotiva
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ecu_remap import ECURemap, RemapProfile, PRESET_PROFILES


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════╗
║          ECU REMAP - Reprogramação Eletrônica                ║
║         Otimização de Potência e Torque Automotivo           ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def cmd_apply_profile(args):
    """Comando: Aplicar perfil de remap"""
    print(f"\n[➤] Carregando ECU: {args.input}")

    try:
        ecu = ECURemap.load_from_file(args.input, validate=not args.skip_validation)
    except FileNotFoundError:
        print(f"[✗] Arquivo não encontrado: {args.input}")
        return 1
    except Exception as e:
        print(f"[✗] Erro ao carregar ECU: {e}")
        return 1

    if args.profile.lower() not in PRESET_PROFILES:
        print(f"[✗] Perfil '{args.profile}' não encontrado")
        print(f"    Perfis disponíveis: {', '.join(PRESET_PROFILES.keys())}")
        return 1

    profile = PRESET_PROFILES[args.profile.lower()]
    print(f"[✓] Usando perfil predefinido: {profile.name}")

    print(f"\n[➤] Aplicando remap...")
    ecu.apply_remap(profile)

    gains = ecu.calculate_performance_gain(profile)
    sign = '+' if gains['power_gain_percent'] >= 0 else ''
    print(f"\n[✓] Remap aplicado com sucesso!")
    print(f"    Potência estimada: {sign}{gains['power_gain_percent']:.2f}%")
    print(f"    Torque estimado:   {sign}{gains['torque_gain_percent']:.2f}%")

    output_path = args.output or args.input.replace('.bin', '_remapped.bin')
    print(f"\n[➤] Salvando em: {output_path}")
    try:
        ecu.save_to_file(output_path, create_backup=args.backup)
    except Exception as e:
        print(f"[✗] Erro ao salvar ECU: {e}")
        return 1

    if args.report:
        report_path = args.report if args.report != 'auto' else output_path.replace('.bin', '_report.txt')
        try:
            ecu.export_report(report_path)
            print(f"[✓] Relatório exportado: {report_path}")
        except Exception as e:
            print(f"[✗] Erro ao exportar relatório: {e}")
            return 1

    print(f"\n[✓] Operação concluída com sucesso!\n")
    return 0


def cmd_list_profiles(args):
    """Comando: Listar perfis disponíveis"""
    print("\n" + "=" * 70)
    print("PERFIS DE REMAP DISPONÍVEIS")
    print("=" * 70)

    for profile_name, profile in PRESET_PROFILES.items():
        fuel_sign = '+' if profile.fuel_boost >= 0 else ''
        ign_sign = '+' if profile.ignition_advance >= 0 else ''
        print(f"\n{profile_name.upper()}: {profile.name}")
        print(f"  Combustível:  {fuel_sign}{profile.fuel_boost:.1f}%")
        print(f"  Ignição:      {ign_sign}{profile.ignition_advance:.1f}°")
        print(f"  Turbo:        {profile.turbo_pressure['low']:.2f}bar - {profile.turbo_pressure['high']:.2f}bar")
        print(f"  RPM Limite:   {profile.rpm_limit}")
        print(f"  Lambda:       {profile.lambda_target:.2f}")
        gains = ECURemap.calculate_performance_gain(profile)
        sign = '+' if gains['power_gain_percent'] >= 0 else ''
        print(f"  Ganhos:       {sign}{gains['power_gain_percent']:.2f}% potência, "
              f"{sign}{gains['torque_gain_percent']:.2f}% torque")

    print("\n" + "=" * 70 + "\n")
    return 0


def cmd_info(args):
    """Comando: Mostrar informações da ECU"""
    print(f"\n[➤] Carregando ECU: {args.input}")

    try:
        ecu = ECURemap.load_from_file(args.input)
    except FileNotFoundError:
        print(f"[✗] Arquivo não encontrado: {args.input}")
        return 1
    except Exception as e:
        print(f"[✗] Erro ao carregar ECU: {e}")
        return 1

    status = ecu.get_status()

    print(f"\n[✓] Informações da ECU:")
    print(f"    Modelo:            {status['model']}")
    print(f"    Tamanho:           {status['size_bytes']:,} bytes")
    print(f"    Válida:            {'✓ Sim' if status['valid'] else '✗ Não'}")
    print(f"    Hash Original:     {status['original_hash'][:16]}...")
    print(f"    Hash Atual:        {status['current_hash'][:16]}...")
    print(f"    Checksum Original: {status['original_checksum']}")
    print(f"    Checksum Atual:    {status['current_checksum']}")

    print(f"\n[✓] Parâmetros Atuais:")
    for param_name, param_value in status['parameters'].items():
        if param_value is not None:
            print(f"    {param_name:22} {param_value:>10.2f}")

    if status['modifications']:
        print(f"\n[✓] Modificações:")
        for mod in status['modifications']:
            print(f"    • {mod}")
    else:
        print(f"\n[!] Nenhuma modificação aplicada (ECU Stock)")

    print()
    return 0


def cmd_estimate(args):
    """Comando: Estimar ganhos de performance"""
    print("\n[➤] Calculando ganhos de performance...\n")

    if args.profile.lower() not in PRESET_PROFILES:
        print(f"[✗] Perfil não encontrado: {args.profile}")
        print(f"    Perfis disponíveis: {', '.join(PRESET_PROFILES.keys())}")
        return 1

    profile = PRESET_PROFILES[args.profile.lower()]
    ecu = ECURemap(bytearray(512 * 1024), validate=False)
    gains = ecu.calculate_performance_gain(profile)

    fuel_sign = '+' if profile.fuel_boost >= 0 else ''
    ign_sign = '+' if profile.ignition_advance >= 0 else ''
    gain_sign = '+' if gains['power_gain_percent'] >= 0 else ''

    print(f"Perfil: {profile.name}")
    print(f"  Combustível: {fuel_sign}{profile.fuel_boost:.1f}%")
    print(f"  Ignição:     {ign_sign}{profile.ignition_advance:.1f}°")
    print(f"  Turbo:       {profile.turbo_pressure['low']:.2f}bar - {profile.turbo_pressure['high']:.2f}bar")

    print(f"\n[✓] Ganhos Estimados:")
    print(f"    Potência: {gain_sign}{gains['power_gain_percent']:.2f}% ({gains['estimated_power']:.0f}hp base)")
    print(f"    Torque:   {gain_sign}{gains['torque_gain_percent']:.2f}% ({gains['estimated_torque']:.0f}Nm base)")
    print()
    return 0


def cmd_create_backup(args):
    """Comando: Criar backup de ECU"""
    print(f"\n[➤] Criando backup de: {args.input}")

    try:
        ecu = ECURemap.load_from_file(args.input)
    except FileNotFoundError:
        print(f"[✗] Arquivo não encontrado: {args.input}")
        return 1
    except Exception as e:
        print(f"[✗] Erro ao carregar ECU: {e}")
        return 1

    backup_path = args.output or args.input.replace('.bin', '_backup.bin')
    ecu.save_to_file(backup_path, create_backup=False)
    print(f"[✓] Backup criado: {backup_path}\n")
    return 0


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description='ECU Remap - Ferramenta de Reprogramação Eletrônica Automotiva',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos de uso:

  # Aplicar perfil sport
  python cli.py apply dump_ecu.bin --profile sport --output dump_remapped.bin

  # Listar perfis disponíveis
  python cli.py list-profiles

  # Ver informações da ECU
  python cli.py info dump_ecu.bin

  # Estimar ganhos de performance
  python cli.py estimate --profile extreme

  # Criar backup
  python cli.py backup dump_ecu.bin
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')

    # Comando: apply
    apply_parser = subparsers.add_parser('apply', help='Aplicar perfil de remap')
    apply_parser.add_argument('input', help='Arquivo ECU de entrada (.bin)')
    apply_parser.add_argument('--profile', default='sport', help='Perfil a aplicar (padrão: sport)')
    apply_parser.add_argument('-o', '--output', help='Arquivo de saída (padrão: input_remapped.bin)')
    apply_parser.add_argument('--no-backup', dest='backup', action='store_false', default=True,
                              help='Não criar backup automático')
    apply_parser.add_argument('-r', '--report', nargs='?', const='auto',
                              help='Exportar relatório (padrão: auto gera nome)')
    apply_parser.add_argument('--skip-validation', action='store_true', default=False,
                              help='Pular validação de header ECU')
    apply_parser.set_defaults(func=cmd_apply_profile)

    # Comando: list-profiles
    list_parser = subparsers.add_parser('list-profiles', help='Listar perfis disponíveis')
    list_parser.set_defaults(func=cmd_list_profiles)

    # Comando: info
    info_parser = subparsers.add_parser('info', help='Mostrar informações da ECU')
    info_parser.add_argument('input', help='Arquivo ECU (.bin)')
    info_parser.set_defaults(func=cmd_info)

    # Comando: estimate
    estimate_parser = subparsers.add_parser('estimate', help='Estimar ganhos de performance')
    estimate_parser.add_argument('--profile', default='sport', help='Perfil a avaliar (padrão: sport)')
    estimate_parser.set_defaults(func=cmd_estimate)

    # Comando: backup
    backup_parser = subparsers.add_parser('backup', help='Criar backup de ECU')
    backup_parser.add_argument('input', help='Arquivo ECU (.bin)')
    backup_parser.add_argument('-o', '--output', help='Arquivo de backup (padrão: input_backup.bin)')
    backup_parser.set_defaults(func=cmd_create_backup)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[!] Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n[✗] Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
