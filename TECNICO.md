# Documentação Técnica - ECU Remap

## Índice
1. [Conceitos Fundamentais](#conceitos-fundamentais)
2. [Arquitetura da Solução](#arquitetura-da-solução)
3. [Parâmetros ECU](#parâmetros-ecu)
4. [Perfis de Remap](#perfis-de-remap)
5. [Cálculos de Performance](#cálculos-de-performance)
6. [Validação e Segurança](#validação-e-segurança)
7. [Exemplos de Uso](#exemplos-de-uso)

---

## Conceitos Fundamentais

### O que é ECU (Engine Control Unit)?

A ECU é o "computador" do motor. Ela controla:
- **Injeção de Combustível**: Quanto combustível é injetado a cada cilindro
- **Ignição**: Quando a vela faz a centelha no cilindro
- **Turbo**: Pressão de ar comprimido do turbo
- **Ar**: Quantidade de ar admitida pelo motor
- **Temperatura**: Monitoramento e controle de temperaturas

### O que é Remap?

Remap (reprogramação) é a modificação dos parâmetros da ECU para aumentar performance, mantendo confiabilidade e dentro dos limites do motor.

**Objetivo**: Aumentar potência e torque ajustando:
- ✓ Combustível (mais injeção = mais potência)
- ✓ Ignição (avanço de ignição = ignição mais rápida)
- ✓ Turbo (maior pressão = mais ar = melhor combustão)

---

## Arquitetura da Solução

### Estrutura de Classes

```
ECURemap             - Classe principal de manipulação da ECU
  ├─ ecu_data       - Dados brutos do arquivo (bytearray)
  ├─ parameters     - Dict de ECUParameter
  └─ modifications  - Log de alterações

RemapProfile         - Define um perfil de otimização
  ├─ fuel_boost     - % de aumento de combustível
  ├─ ignition_advance - ° de avanço de ignição
  └─ turbo_pressure - Pressão de turbo em bar

ECUParameter         - Representa um parâmetro individual
  ├─ offset         - Posição no arquivo (em bytes)
  ├─ size           - Tamanho (1, 2 ou 4 bytes)
  ├─ value          - Valor atual
  └─ scale          - Fator de conversão
```

### Fluxo de Dados

```
1. Carregar ECU
   arquivo.bin → ECURemap.load_from_file() → objeto ECURemap

2. Ler Parâmetros
   bytearray[offset:offset+size] → _read_parameter() → valor real (com scale)

3. Aplicar Remap
   RemapProfile → apply_remap() → modifica parâmetros → escreve em bytearray

4. Salvar
   bytearray → _write_parameter() → arquivo.bin
```

---

## Parâmetros ECU

### Parâmetros Ajustaveis

#### 1. Injeção de Combustível (0x1000)
- **Range**: 0 a 200%
- **Escala**: 0.5
- **Impacto**: Direto na potência
- **Risco**: Muito fuel = motor rico demais

#### 2. Avanço de Ignição (0x1100)
- **Range**: -20° a +50°
- **Escala**: 0.1°
- **Impacto**: Melhora resposta e potência
- **Risco**: Muito avanço = batida no motor

#### 3. Pressão Turbo - Baixa RPM (0x1200)
- **Range**: 0.5 a 2.0 bar
- **Escala**: 0.01 bar
- **Impacto**: Performance em baixas RPM
- **Risco**: Pode danificar turbo

#### 4. Pressão Turbo - Alta RPM (0x1202)
- **Range**: 0.5 a 2.5 bar
- **Escala**: 0.01 bar
- **Impacto**: Performance em altas RPM
- **Risco**: Soperboosting

#### 5. Limite RPM (0x1300)
- **Range**: 5000 a 9000 rpm
- **Escala**: 1.0 rpm
- **Impacto**: RPM máxima do motor
- **Risco**: Quebra do motor

#### 6. Razão Ar-Combustível - Lambda (0x1400)
- **Range**: 0.8 a 1.2 λ
- **Escala**: 0.01
- **Base**: 1.0 = proporção perfeita (14.7:1)
- **Rich**: < 1.0 (mais combustível, mais potência)
- **Lean**: > 1.0 (menos combustível, economia)

#### 7. Temperatura Arrefecimento (0x1500)
- **Range**: 70 a 110 °C
- **Escala**: 1.0 °C
- **Impacto**: Ponto de operação ideal do motor

#### 8. Ativação Ventilador (0x1600)
- **Range**: 80 a 100 °C
- **Escala**: 1.0 °C
- **Impacto**: Quando o ventilador liga

---

## Perfis de Remap

### Perfil ECO (Economia)
```
Combustível:  -5%
Ignição:      -2°
Turbo:        0.9 - 1.0 bar
Lambda:       1.05 (lean)
Objetivo:     Menor consumo, menos potência
```

### Perfil STOCK (Padrão Fábrica)
```
Combustível:  0%
Ignição:      0°
Turbo:        1.0 - 1.2 bar
Lambda:       0.95
Objetivo:     Configuração de fábrica, balanceada
```

### Perfil SPORT (Performance Diária)
```
Combustível:  +20%
Ignição:      +8°
Turbo:        1.2 - 1.5 bar
Lambda:       0.88
RPM Limite:   7500 rpm
Objetivo:     Melhor resposta, mais potência
Ganho Est:    ~30% potência, ~35% torque
```

### Perfil EXTREME (Máxima Potência)
```
Combustível:  +35%
Ignição:      +12°
Turbo:        1.4 - 1.8 bar
Lambda:       0.85 (muito rico)
RPM Limite:   8000 rpm
Objetivo:     Máxima performance
Ganho Est:    ~50% potência, ~55% torque
Risco:        Alto, requer manutenção frequente
```

---

## Cálculos de Performance

### Fórmula de Ganho de Potência

```
Ganho Power = (fuel_factor × ignition_factor × turbo_factor) - 1

Onde:
  fuel_factor = 1 + (fuel_boost / 100)
  ignition_factor = 1 + (ignition_advance / 100)
  turbo_factor = turbo_pressure_high / turbo_pressure_base

Exemplo (SPORT):
  fuel_factor = 1 + (20 / 100) = 1.20
  ignition_factor = 1 + (8 / 100) = 1.08
  turbo_factor = 1.5 / 1.2 = 1.25
  
  Ganho = (1.20 × 1.08 × 1.25) - 1 = 0.62 = 62% ❌ ERRADO
```

### Fórmula Corrigida (Mais Realista)

```
Power = Base × (1 + fuel_boost% × 0.35 + ignition° × 0.08 + (turbo_pressure - base) × 0.4)

Exemplo (SPORT):
  Power = 100 × (1 + 20×0.35 + 8×0.08 + (1.5-1.2)×0.4)
  Power = 100 × (1 + 7.0 + 0.64 + 0.12)
  Power = 100 × 1.876 = 187.6 hp (~+87.6%)  ❌ OTIMISTA DEMAIS

Fórmula Mais Realista:
  Power = Base × (1 + fuel_boost% × 0.25 + ignition° × 0.05 + (turbo_pressure - base) × 0.25)

Exemplo (SPORT):
  Power = 100 × (1 + 20×0.25 + 8×0.05 + (1.5-1.2)×0.25)
  Power = 100 × (1 + 5.0 + 0.4 + 0.075)
  Power = 100 × 1.475 = 147.5 hp (~+47.5%)
```

### Ganho de Torque

```
Torque = Power × 1.15  (Torque tipicamente cresce mais que potência)

Exemplo (SPORT):
  Power Gain = 47.5%
  Torque Gain = 47.5 × 1.15 ≈ 54.6%
```

---

## Validação e Segurança

### Limites de Segurança

```python
Validações Implementadas:
  ✓ Combustível: 0-50% (acima disso = risco motor rico)
  ✓ Ignição: 0-15° (acima = batida no motor)
  ✓ Turbo Baixa: 0.5-1.8 bar
  ✓ Turbo Alta: 0.5-2.2 bar
  ✓ Lambda: 0.80-1.20 (fora = combustão ruim)
  ✓ RPM: 5000-9000 (limites do motor)
  ✓ Temperatura: 70-110°C
  
Checksums & Integridade:
  ✓ Hash SHA-256 antes e depois
  ✓ Backup automático (opcional)
  ✓ Log de modificações
```

### Avisos e Restrições

```
⚠️  Avisos Durante Remap:
  • Se fuel_boost > 30% → "Combustível muito elevado"
  • Se ignition_advance > 10° → "Monitorar batidas"
  • Se turbo_high > 1.6 bar → "Arrefecimento crítico"
  
❌ Remaos Bloqueados:
  • Valores fora dos limites automáticamente ajustados
  • Motor recusa valores inválidos
```

---

## Exemplos de Uso

### Uso Básico em Python

```python
from ecu_remap import ECURemap, RemapProfile, PRESET_PROFILES

# 1. Carregar ECU
ecu = ECURemap.load_from_file("dump_ecu.bin")

# 2. Aplicar perfil predefido
profile = PRESET_PROFILES['sport']
ecu.apply_remap(profile)

# 3. Salvar
ecu.save_to_file("dump_ecu_sport.bin")

# 4. Obter relatório
ecu.export_report("relatorio.txt")
```

### Perfil Customizado

```python
# Criar perfil customizado
custom_profile = RemapProfile(
    name="Meu Remap",
    fuel_boost=18,
    ignition_advance=7,
    turbo_pressure={'low': 1.15, 'high': 1.45},
    rpm_limit=7200,
    lambda_target=0.89
)

# Aplicar
ecu.apply_remap(custom_profile)

# Estimar ganhos
gains = ecu.calculate_performance_gain(custom_profile)
print(f"Potência: +{gains['power_gain_percent']:.2f}%")
```

### Uso CLI

```bash
# Aplicar perfil sport
python cli.py apply dump_ecu.bin --profile sport -o dump_remapped.bin

# Ver perfis disponíveis
python cli.py list-profiles

# Informações da ECU
python cli.py info dump_ecu.bin

# Estimar performance
python cli.py estimate --profile extreme

# Criar backup
python cli.py backup dump_ecu.bin
```

---

## Manutenção e Cuidados

### Antes do Remap

- ✓ Fazer backup do arquivo original
- ✓ Verificar model do carro/ECU
- ✓ Confirmar arquivo é legítimo
- ✓ Testar em ambiente de laboratório primeiro

### Depois do Remap

- ✓ Testar em dinamômetro
- ✓ Monitorar temperatura do motor
- ✓ Verificar pressão de óleo
- ✓ Acompanhar consumo de combustível
- ✓ Fazer manutenção mais frequente

### Revertendo Remap

```python
# Opção 1: Usar arquivo backup
ecu_original = ECURemap.load_from_file("dump_ecu_backup.bin")
ecu_original.save_to_file("dump_ecu.bin")

# Opção 2: Aplicar perfil STOCK
profile_stock = PRESET_PROFILES['stock']
ecu.apply_remap(profile_stock)
```

---

## Troubleshooting

### Problema: "Arquivo ECU não é reconhecido"
- ✓ Verificar formato (.bin esperado)
- ✓ Verificar tamanho (tipicamente 256KB, 512KB, 1MB)
- ✓ Confirmar arquivo não corrompido

### Problema: "Valores fora do range"
- ✓ Sistema automaticamente ajusta para limites máximos/mínimos
- ✓ Ver logs para valores reais aplicados

### Problema: "Motor não liga após remap"
- ✓ Revertir para backup original imediatamente
- ✓ Contactar técnico especializado
- ✓ Não ligar sem diagnóstico

---

## Referências

- [OBD-II Protocol](https://en.wikipedia.org/wiki/On-board_diagnostics)
- [ECU Tuning Basics](https://www.tuningbox.com)
- [Engine Control Unit](https://en.wikipedia.org/wiki/Engine_control_unit)
- SAE J1850 (Vehicle Communication Standard)

---

**Última atualização**: Março 2026  
**Versão**: 1.0.0  
**Desenvolvedor**: ECU Remap Team
