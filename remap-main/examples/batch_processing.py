"""
Exemplo: Processamento em Lote (Batch Processing)
Processa múltiplos arquivos ECU com diferentes perfis
"""

import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from ecu_remap import ECURemap, RemapProfile, PRESET_PROFILES


class BatchProcessor:
    """Processa múltiplos arquivos ECU em lote"""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.results: List[Dict] = []
    
    def process_batch(self, profile_name: str = 'sport') -> None:
        """Processa todos os arquivos .bin no diretório"""
        
        print(f"\n" + "="*70)
        print(f"PROCESSAMENTO EM LOTE - Perfil: {profile_name.upper()}")
        print("="*70)
        
        if profile_name.lower() not in PRESET_PROFILES:
            print(f"[✗] Perfil não encontrado: {profile_name}")
            return
        
        profile = PRESET_PROFILES[profile_name.lower()]
        
        # Encontrar todos os arquivos .bin
        ecu_files = list(self.input_dir.glob('*.bin'))
        
        if not ecu_files:
            print(f"[!] Nenhum arquivo .bin encontrado em: {self.input_dir}")
            return
        
        print(f"\n[➤] Encontrados {len(ecu_files)} arquivo(s) ECU\n")
        
        # Processar cada arquivo
        for idx, ecu_file in enumerate(ecu_files, 1):
            print(f"[{idx}/{len(ecu_files)}] Processando: {ecu_file.name}")
            
            try:
                # Carregar
                ecu = ECURemap.load_from_file(str(ecu_file))
                
                # Remapear
                ecu.apply_remap(profile)
                
                # Calcular ganhos
                gains = ecu.calculate_performance_gain(profile)
                
                # Salvar
                output_file = self.output_dir / ecu_file.name.replace('.bin', f'_{profile_name}.bin')
                self.output_dir.mkdir(parents=True, exist_ok=True)
                ecu.save_to_file(str(output_file))
                
                # Exportar relatório
                report_file = output_file.with_suffix('.txt')
                ecu.export_report(str(report_file))
                
                result = {
                    'file': ecu_file.name,
                    'status': 'OK',
                    'profile': profile_name,
                    'power_gain': gains['power_gain_percent'],
                    'torque_gain': gains['torque_gain_percent'],
                    'output': str(output_file)
                }
                
                print(f"  ✓ OK | +{gains['power_gain_percent']:.2f}% potência")
                
            except Exception as e:
                result = {
                    'file': ecu_file.name,
                    'status': 'ERROR',
                    'error': str(e)
                }
                print(f"  ✗ ERRO: {e}")
            
            self.results.append(result)
        
        self._print_summary()
    
    def process_multiple_profiles(self, file_path: str) -> None:
        """Aplica múltiplos perfis ao mesmo arquivo"""
        
        print(f"\n" + "="*70)
        print(f"PROCESSAMENTO - MÚLTIPLOS PERFIS")
        print("="*70)
        
        ecu_file = Path(file_path)
        
        if not ecu_file.exists():
            print(f"[✗] Arquivo não encontrado: {file_path}")
            return
        
        print(f"\n[➤] Arquivo: {ecu_file.name}\n")
        
        # Processar com cada perfil
        for profile_name in PRESET_PROFILES.keys():
            print(f"[➤] Aplicando perfil: {profile_name.upper()}")
            
            try:
                # Carregar
                ecu = ECURemap.load_from_file(str(ecu_file))
                
                # Remapear
                profile = PRESET_PROFILES[profile_name]
                ecu.apply_remap(profile)
                
                # Calcular ganhos
                gains = ecu.calculate_performance_gain(profile)
                
                # Salvar
                output_file = ecu_file.parent / ecu_file.name.replace('.bin', f'_{profile_name}.bin')
                ecu.save_to_file(str(output_file), create_backup=False)
                
                result = {
                    'profile': profile_name,
                    'status': 'OK',
                    'power_gain': gains['power_gain_percent'],
                    'torque_gain': gains['torque_gain_percent']
                }
                
                pw = gains['power_gain_percent']
                tq = gains['torque_gain_percent']
                print(f"  ✓ {profile_name:10} | {'+' if pw >= 0 else ''}{pw:6.2f}% pot | {'+' if tq >= 0 else ''}{tq:6.2f}% torque")
                
            except Exception as e:
                result = {
                    'profile': profile_name,
                    'status': 'ERROR',
                    'error': str(e)
                }
                print(f"  ✗ {profile_name:10} | Erro: {e}")
            
            self.results.append(result)
    
    def _print_summary(self) -> None:
        """Imprime resumo dos resultados"""
        if not self.results:
            return
        
        print(f"\n" + "="*70)
        print("RESUMO DOS RESULTADOS")
        print("="*70)
        
        successful = sum(1 for r in self.results if r['status'] == 'OK')
        failed = sum(1 for r in self.results if r['status'] == 'ERROR')
        
        print(f"\nTotal: {len(self.results)} | Sucesso: {successful} | Erro: {failed}")
        
        if any(r['status'] == 'OK' for r in self.results):
            print(f"\nGanhos Médios:")
            OK_results = [r for r in self.results if r['status'] == 'OK']
            avg_power = sum(r['power_gain'] for r in OK_results) / len(OK_results)
            avg_torque = sum(r['torque_gain'] for r in OK_results) / len(OK_results)
            print(f"  Potência: +{avg_power:.2f}%")
            print(f"  Torque: +{avg_torque:.2f}%")
        
        print()


def example_1_batch_single_profile():
    """Exemplo 1: Processar múltiplos arquivos com um perfil"""
    print("\n" + "█"*70)
    print("  EXEMPLO 1: Batch Processing - Um Perfil")
    print("█"*70)
    
    # Criar diretório temporário com arquivos ECU de exemplo
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Criar alguns arquivos ECU fake
        input_dir = os.path.join(tmpdir, 'input')
        output_dir = os.path.join(tmpdir, 'output')
        os.makedirs(input_dir)
        
        for i in range(3):
            ecu_data = bytearray(256 * 1024)  # 256KB
            ecu_data[0:4] = b'ECU!'
            filename = os.path.join(input_dir, f'car_{i+1}_original.bin')
            with open(filename, 'wb') as f:
                f.write(ecu_data)
        
        # Processar
        processor = BatchProcessor(input_dir, output_dir)
        processor.process_batch('sport')
        
        # Listar resultados
        print("\nArquivos gerados:")
        for f in Path(output_dir).glob('*'):
            print(f"  • {f.name}")


def example_2_multiple_profiles():
    """Exemplo 2: Aplicar múltiplos perfis ao mesmo arquivo"""
    print("\n" + "█"*70)
    print("  EXEMPLO 2: Múltiplos Perfis no Mesmo Arquivo")
    print("█"*70)
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Criar arquivo ECU
        ecu_file = Path(tmpdir) / 'ecu_example.bin'
        ecu_data = bytearray(256 * 1024)
        ecu_data[0:4] = b'ECU!'
        
        with open(ecu_file, 'wb') as f:
            f.write(ecu_data)
        
        # Processar com múltiplos perfis
        processor = BatchProcessor(tmpdir, tmpdir)
        processor.process_multiple_profiles(str(ecu_file))


def example_3_advanced_batch():
    """Exemplo 3: Batch avançado com logging detalhado"""
    print("\n" + "█"*70)
    print("  EXEMPLO 3: Batch Avançado com Análise")
    print("█"*70)
    
    print("\nSimulando processamento de 10 veículos com diferentes perfis...\n")
    
    vehicles = [
        ('Honda_Civic_2020.bin', ['sport', 'extreme']),
        ('BMW_320i_2019.bin', ['balanced', 'extreme']),
        ('Ford_Focus_2021.bin', ['eco', 'sport']),
    ]
    
    print("-"*70)
    print(f"{'Veículo':<30} {'Perfil':<15} {'Ganhos':<20}")
    print("-"*70)
    
    for vehicle, profiles in vehicles:
        ecu = ECURemap(bytearray(256 * 1024))
        
        for profile_name in profiles:
            if profile_name in PRESET_PROFILES:
                profile = PRESET_PROFILES[profile_name]
                gains = ecu.calculate_performance_gain(profile)
                
                gains_str = f"+{gains['power_gain_percent']:.1f}% / +{gains['torque_gain_percent']:.1f}%"
                print(f"{vehicle:<30} {profile_name:<15} {gains_str:<20}")


if __name__ == "__main__":
    print("\n" + "█"*70)
    print("  ECU REMAP - BATCH PROCESSING")
    print("█"*70)
    
    try:
        example_1_batch_single_profile()
        example_2_multiple_profiles()
        example_3_advanced_batch()
        
        print("\n" + "█"*70)
        print("  ✓ Exemplos executados com sucesso!")
        print("█"*70 + "\n")
        
    except Exception as e:
        print(f"\n[✗] Erro: {e}")
        import traceback
        traceback.print_exc()
