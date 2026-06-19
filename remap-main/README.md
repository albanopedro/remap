# ECU Remap Tool - Otimização de Veículos

portugues: Um amigo me desafiou a criar um código para reprogramar a ECU do carro, e achei que seria legal compartilhar aqui (os códigos nunca foram testados, é tudo brincadeira, não fiz nenhum teste de verdade, rsrs, não me responsabilizo por explosões ou quaisquer problemas que ocorram no carro se alguém tentar isso).


ingles: A friend challenged me to create a code to remap (reprogram the car's ECU), and I thought it would be cool to share it here (the codes have never been tested, it's all just a joke, I haven't done any real tests lol, I'm not responsible for anything exploding or any problems that occur in the car if someone tries this).
## Recursos

- **Leitura de ECU**: Suporta arquivos binários e hexadecimais
- **Ajuste de Parâmetros**: 
  - Combustível (injeção)
  - Ignição (timing)
  - Pressão do Turbo
  - Limites de RPM
  - Temperatura de funcionamento
- **Validação Automática**: Checksums e limites operacionais
- **Suporte Multimarca**: Framework extensível para diferentes ECUs
- **Backup Automático**: Cria backup antes de modificações
- **Cálculo de Performance**: Estimativas de ganho de potência

## Instalação

```bash
pip install -r requirements.txt
```

## Uso Básico

```python
from ecu_remap import ECURemap, RemapProfile

# Carregar ECU
ecu = ECURemap.load_from_file("dump_ecu.bin")

# Criar perfil de otimização
profile = RemapProfile(
    fuel_boost=15,        # +15% combustível
    ignition_advance=5,   # +5° avanço de ignição
    turbo_pressure={
        "low": 1.2,      # bar
        "high": 1.4      # bar
    },
    rpm_limit=7500
)

# Aplicar modificações
ecu.apply_remap(profile)

# Salvar
ecu.save_to_file("dump_ecu_remapped.bin")
```

## Segurança

⚠️ **IMPORTANTE**: Este software é para fins educacionais e profissionais apenas.
- Sempre faça backup antes de remapear
- Realize testes em ambiente seguro
- Verificar compatibilidade com veículo específico
- Garantir que as modificações estejam dentro dos limites ECU

## Estrutura do Projeto

```
remap/
├── src/
│   ├── ecu_remap.py          # Core da reprogramação
│   ├── ecu_models.py         # Modelos de ECU suportados
│   ├── parameters.py         # Definição de parâmetros
│   ├── validators.py         # Validação de dados
│   └── utils.py              # Utilitários
├── examples/
│   ├── basic_remap.py        # Exemplo básico
│   ├── advanced_tuning.py    # Tuning avançado
│   └── batch_processing.py   # Processar múltiplos arquivos
├── tests/
│   └── test_remap.py         # Testes unitários
├── requirements.txt
└── README.md
```
