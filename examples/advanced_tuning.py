"""
Exemplo Avançado - ECU Remap com Tuning Otimizado
Demonstra técnicas avançadas de remap com validação e cálculos complexos
"""

import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, Path(__file__).parent.parent / 'src')

from ecu_remap import ECURemap, RemapProfile


class AdvancedTuningEngine:
    """Motor de tuning avançado com otimizações"""
    
    def __init__(self, ecu: ECURemap):
        self.ecu = ecu
        self.optimization_log: List[str] = []
    
    def optimize_for_target_power(self, target_power_gain: float) -> RemapProfile:
        """Calcula perfil ideal para ganho de potência alvo"""
        self.optimization_log.append(f"Otimizando para +{target_power_gain}% de potência...")
        
        # Fórmula: gain = combustível * ignição * turbo
        # Distribuir uniformemente o ganho entre os três fatores
        factor_per_component = (target_power_gain / 100 + 1) ** (1/3)
        
        fuel_boost = (factor_per_component - 1) * 100
        ignition_advance = (factor_per_component - 1) * 50  # Menos sensível
        turbo_ratio = factor_per_component
        
        turbo_base_low = 1.0
        turbo_base_high = 1.2
        
        profile = RemapProfile(
            name=f"Optimized +{target_power_gain}% Power",
            fuel_boost=min(fuel_boost, 40),
            ignition_advance=min(ignition_advance, 12),
            turbo_pressure={
                'low': min(turbo_base_low * turbo_ratio, 1.8),
                'high': min(turbo_base_high * turbo_ratio, 2.2)
            },
            rpm_limit=7500,
            lambda_target=self._calculate_lambda_for_fuel(fuel_boost),
            cooling_temp=self._calculate_cooling_temp(target_power_gain)
        )
        
        self.optimization_log.append(f"  Combustível: +{profile.fuel_boost:.1f}%")
        self.optimization_log.append(f"  Ignição: +{profile.ignition_advance:.1f}°")
        self.optimization_log.append(f"  Turbo: {profile.turbo_pressure['low']:.2f}bar - {profile.turbo_pressure['high']:.2f}bar")
        
        return profile
    
    def optimize_for_torque(self, target_torque_gain: float) -> RemapProfile:
        """Calcula perfil ideal para ganho de torque"""
        self.optimization_log.append(f"Otimizando para +{target_torque_gain}% de torque...")
        
        # Torque é mais sensível a combustível e turbo, menos à ignição
        fuel_boost = min(target_torque_gain * 0.8, 40)
        ignition_advance = min(target_torque_gain * 0.15, 10)
        
        turbo_ratio = 1 + (target_torque_gain / 100) * 0.5
        
        profile = RemapProfile(
            name=f"Optimized +{target_torque_gain}% Torque",
            fuel_boost=fuel_boost,
            ignition_advance=ignition_advance,
            turbo_pressure={
                'low': 1.1 * turbo_ratio,
                'high': 1.3 * turbo_ratio
            },
            rpm_limit=7200,
            lambda_target=self._calculate_lambda_for_fuel(fuel_boost),
            cooling_temp=self._calculate_cooling_temp(target_torque_gain)
        )
        
        return profile
    
    def optimize_balanced(self) -> RemapProfile:
        """Cria perfil balanceado entre potência e confiabilidade"""
        self.optimization_log.append("Criando perfil balanceado...")
        
        profile = RemapProfile(
            name="Balanced Optimization",
            fuel_boost=18,
            ignition_advance=7,
            turbo_pressure={'low': 1.18, 'high': 1.48},
            rpm_limit=7400,
            lambda_target=0.89,
            cooling_temp=87,
            safety_margin=0.94
        )
        
        return profile
    
    def optimize_aggressive(self) -> RemapProfile:
        """Cria perfil agressivo para máxima performance"""
        self.optimization_log.append("Criando perfil agressivo...")
        
        profile = RemapProfile(
            name="Aggressive Performance",
            fuel_boost=32,
            ignition_advance=11,
            turbo_pressure={'low': 1.35, 'high': 1.75},
            rpm_limit=7800,
            lambda_target=0.85,
            cooling_temp=82,
            safety_margin=0.92
        )
        
        return profile
    
    def optimize_smooth_power_band(self) -> RemapProfile:
        """Otimiza para melhor resposta em toda faixa de RPM"""
        self.optimization_log.append("Otimizando banda de potência...")
        
        profile = RemapProfile(
            name="Smooth Power Band",
            fuel_boost=22,
            ignition_advance=8,
            turbo_pressure={'low': 1.25, 'high': 1.55},
            rpm_limit=7600,
            lambda_target=0.88,
            cooling_temp=86
        )
        
        return profile
    
    @staticmethod
    def _calculate_lambda_for_fuel(fuel_boost: float) -> float:
        """Calcula razão ar-combustível ideal para o boost de combustível"""
        base_lambda = 0.95
        # Quanto mais combustível, mais oxigênio precisa (lambda menor = mais rico)
        adjusted = base_lambda - (fuel_boost / 100) * 0.15
        return max(0.80, min(adjusted, 1.1))
    
    @staticmethod
    def _calculate_cooling_temp(performance_gain: float) -> int:
        """Calcula temperatura de arrefecimento para o ganho de performance"""
        base_temp = 90
        # Mais performance = mais calor = temperatura mais baixa para ativar arrefecimento
        adjusted = base_temp - int(performance_gain * 0.3)
        return max(80, min(adjusted, 100))
    
    def get_optimization_log(self) -> str:
        """Retorna log de otimizações"""
        return '\n'.join(self.optimization_log)


def example_1_optimize_for_power():
    """Exemplo 1: Otimizar para alvo específico de potência"""
    print("\n" + "="*70)
    print("EXEMPLO 1: Otimizar para +25% de Potência")
    print("="*70)
    
    ecu = ECURemap(bytearray(512 * 1024))
    tuner = AdvancedTuningEngine(ecu)
    
    # Otimizar para 25% de potência
    profile = tuner.optimize_for_target_power(25)
    
    print("\nPerfil Gerado:")
    print(f"  Nome: {profile.name}")
    print(f"  Combustível: +{profile.fuel_boost:.1f}%")
    print(f"  Ignição: +{profile.ignition_advance:.1f}°")
    print(f"  Turbo: {profile.turbo_pressure['low']:.2f}bar - {profile.turbo_pressure['high']:.2f}bar")
    print(f"  RPM Limite: {profile.rpm_limit}")
    print(f"  Lambda: {profile.lambda_target:.2f}")
    print(f"  Temp. Arrefecimento: {profile.cooling_temp}°C")
    
    ecu.apply_remap(profile)
    gains = ecu.calculate_performance_gain(profile)
    
    print(f"\nGanhos Estimados:")
    print(f"  Potência: +{gains['power_gain_percent']:.2f}%")
    print(f"  Torque: +{gains['torque_gain_percent']:.2f}%")
    
    print("\nLog de Otimização:")
    print(tuner.get_optimization_log())


def example_2_optimization_comparison():
    """Exemplo 2: Comparar diferentes estratégias de otimização"""
    print("\n" + "="*70)
    print("EXEMPLO 2: Comparação de Estratégias de Otimização")
    print("="*70)
    
    strategies = {
        'smooth': lambda tuner: tuner.optimize_smooth_power_band(),
        'balanced': lambda tuner: tuner.optimize_balanced(),
        'aggressive': lambda tuner: tuner.optimize_aggressive(),
    }
    
    results = []
    
    for name, strategy in strategies.items():
        ecu = ECURemap(bytearray(512 * 1024))
        tuner = AdvancedTuningEngine(ecu)
        
        profile = strategy(tuner)
        ecu.apply_remap(profile)
        gains = ecu.calculate_performance_gain(profile)
        
        results.append({
            'name': name,
            'profile': profile,
            'gains': gains,
            'log': tuner.get_optimization_log()
        })
    
    # Exibir comparação
    print("\n" + "-"*70)
    print(f"{'Estratégia':<15} {'Combustível':<15} {'Potência':<15} {'Torque':<15}")
    print("-"*70)
    
    for result in results:
        p = result['profile']
        g = result['gains']
        print(
            f"{result['name'].upper():<15} "
            f"+{p.fuel_boost:>6.1f}%        "
            f"+{g['power_gain_percent']:>6.2f}%        "
            f"+{g['torque_gain_percent']:>6.2f}%"
        )
    
    print("\n" + "-"*70)
    print("Recomendações:")
    print("-"*70)
    
    for result in results:
        print(f"\n{result['name'].upper()}:")
        print(result['log'])


def example_3_stepwise_tuning():
    """Exemplo 3: Tuning progressivo - aumentar ganho gradualmente"""
    print("\n" + "="*70)
    print("EXEMPLO 3: Tuning Progressivo (Stepwise)")
    print("="*70)
    
    ecu = ECURemap(bytearray(512 * 1024))
    tuner = AdvancedTuningEngine(ecu)
    
    targets = [10, 15, 20, 25, 30]
    
    print("\nProgessão de Ganho de Potência:")
    print("-"*90)
    print(f"{'Alvo':<8} {'Combustível':<15} {'Ignição':<15} {'Turbo':<25} {'Ganho Real':<15}")
    print("-"*90)
    
    for target in targets:
        ecu_temp = ECURemap(bytearray(512 * 1024))
        tuner_temp = AdvancedTuningEngine(ecu_temp)
        
        profile = tuner_temp.optimize_for_target_power(target)
        ecu_temp.apply_remap(profile)
        gains = ecu_temp.calculate_performance_gain(profile)
        
        turbo_str = f"{profile.turbo_pressure['low']:.2f}-{profile.turbo_pressure['high']:.2f}bar"
        
        print(
            f"{target:>6}% "
            f"+{profile.fuel_boost:>6.1f}%        "
            f"+{profile.ignition_advance:>6.1f}°        "
            f"{turbo_str:<25} "
            f"+{gains['power_gain_percent']:>6.2f}%"
        )


def example_4_diagnosticos():
    """Exemplo 4: Diagnósticos e análise de qualidade"""
    print("\n" + "="*70)
    print("EXEMPLO 4: Diagnósticos e Análise")
    print("="*70)
    
    ecu = ECURemap(bytearray(512 * 1024))
    tuner = AdvancedTuningEngine(ecu)
    
    profile = tuner.optimize_aggressive()
    ecu.apply_remap(profile)
    
    print("\nAnálise de Segurança:")
    print("-"*70)
    
    checks = {
        'Lambda (0.80-1.1)': (profile.lambda_target, 0.80, 1.1),
        'Combustível (0-50%)': (profile.fuel_boost, 0, 50),
        'Ignição (0-15°)': (profile.ignition_advance, 0, 15),
        'RPM Limite (5000-9000)': (profile.rpm_limit, 5000, 9000),
        'Temp Arrefecimento (70-110°C)': (profile.cooling_temp, 70, 110),
    }
    
    all_safe = True
    for check_name, (value, min_val, max_val) in checks.items():
        is_safe = min_val <= value <= max_val
        status = "✓ OK" if is_safe else "✗ AVISO"
        if not is_safe:
            all_safe = False
        print(f"  {check_name:<30} {value:>8} {status}")
    
    print(f"\nStatus Geral: {'✓ SEGURO' if all_safe else '✗ VERIFICAR'}")
    
    print("\nRecomendações:")
    print("-"*70)
    if profile.fuel_boost > 30:
        print("  ⚠ Combustível muito elevado - considerar reduzir para maior confiabilidade")
    if profile.ignition_advance > 10:
        print("  ⚠ Avanço de ignição agressivo - monitorar batidas de motor")
    if profile.turbo_pressure.get('high', 1.2) > 1.6:
        print("  ⚠ Pressão de turbo elevada - verificar sistema de arrefecimento")
    print("  • Fazer teste em dinamômetro após aplicar remap")
    print("  • Monitorar temperatura e pressão em uso real")


if __name__ == "__main__":
    print("\n" + "█"*70)
    print("  ECU REMAP - EXEMPLOS AVANÇADOS")
    print("█"*70)
    
    try:
        example_1_optimize_for_power()
        example_2_optimization_comparison()
        example_3_stepwise_tuning()
        example_4_diagnosticos()
        
        print("\n" + "█"*70)
        print("  ✓ Todos os exemplos executados com sucesso!")
        print("█"*70 + "\n")
        
    except Exception as e:
        print(f"\n[✗] Erro: {e}")
        import traceback
        traceback.print_exc()
