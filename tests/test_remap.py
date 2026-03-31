"""
Testes Unitários - ECU Remap
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.parent / 'src')

from ecu_remap import ECURemap, RemapProfile, ECUParameter, PRESET_PROFILES


class TestECUParameter(unittest.TestCase):
    """Testes para classe ECUParameter"""
    
    def setUp(self):
        self.param = ECUParameter(
            name="Test Param",
            offset=0x1000,
            size=2,
            min_val=0,
            max_val=100,
            scale=1.0,
            unit="%"
        )
    
    def test_parameter_creation(self):
        self.assertEqual(self.param.name, "Test Param")
        self.assertEqual(self.param.offset, 0x1000)
        self.assertEqual(self.param.size, 2)
    
    def test_set_value_within_range(self):
        self.param.set_value(50)
        self.assertEqual(self.param.value, 50.0)
    
    def test_set_value_above_max(self):
        self.param.set_value(200)
        self.assertEqual(self.param.value, 100)  # Clamped
    
    def test_set_value_below_min(self):
        self.param.set_value(-50)
        self.assertEqual(self.param.value, 0)  # Clamped
    
    def test_modify_percentage(self):
        self.param.set_value(50)
        new_val = self.param.modify(20)  # +20%
        self.assertAlmostEqual(new_val, 60.0, places=1)
    
    def test_get_raw_value(self):
        self.param.set_value(50)
        raw = self.param.get_raw_value()
        self.assertEqual(raw, 50)


class TestRemapProfile(unittest.TestCase):
    """Testes para classe RemapProfile"""
    
    def test_profile_creation(self):
        profile = RemapProfile(
            name="Test",
            fuel_boost=10,
            ignition_advance=5
        )
        self.assertEqual(profile.name, "Test")
        self.assertEqual(profile.fuel_boost, 10)
        self.assertEqual(profile.ignition_advance, 5)
    
    def test_profile_clamps_values(self):
        profile = RemapProfile(
            fuel_boost=100,  # Deve ser reduzido para max 50
            ignition_advance=20  # Deve ser reduzido para max 15
        )
        self.assertEqual(profile.fuel_boost, 50)
        self.assertEqual(profile.ignition_advance, 15)
    
    def test_profile_to_dict(self):
        profile = RemapProfile(name="Test", fuel_boost=15)
        d = profile.to_dict()
        self.assertIn('name', d)
        self.assertIn('fuel_boost', d)
        self.assertEqual(d['fuel_boost'], 15)
    
    def test_preset_profiles_exist(self):
        self.assertIn('eco', PRESET_PROFILES)
        self.assertIn('sport', PRESET_PROFILES)
        self.assertIn('extreme', PRESET_PROFILES)
        self.assertIn('stock', PRESET_PROFILES)


class TestECURemap(unittest.TestCase):
    """Testes para classe ECURemap"""
    
    def setUp(self):
        self.ecu_data = bytearray(512 * 1024)
        self.ecu_data[0:4] = b'ECU!'
        self.ecu = ECURemap(self.ecu_data)
    
    def test_ecu_creation(self):
        self.assertEqual(len(self.ecu.ecu_data), 512 * 1024)
        self.assertEqual(self.ecu.model, 'generic')
    
    def test_ecu_parameters_initialized(self):
        self.assertIn('fuel_injection', self.ecu.parameters)
        self.assertIn('ignition_timing', self.ecu.parameters)
        self.assertIn('turbo_boost_low', self.ecu.parameters)
        self.assertIn('rpm_limit', self.ecu.parameters)
    
    def test_read_write_parameter(self):
        offset = 0x1000
        size = 2
        test_value = 12345
        
        self.ecu._write_parameter(offset, size, test_value)
        read_value = self.ecu._read_parameter(offset, size)
        
        self.assertEqual(read_value, test_value)
    
    def test_apply_remap(self):
        profile = PRESET_PROFILES['sport']
        original_fuel = self.ecu.parameters['fuel_injection'].value
        
        self.ecu.apply_remap(profile)
        
        # Verificar que o parâmetro foi modificado
        self.assertNotEqual(
            self.ecu.parameters['fuel_injection'].value,
            original_fuel
        )
    
    def test_modifications_log(self):
        profile = PRESET_PROFILES['sport']
        self.ecu.apply_remap(profile)
        
        self.assertGreater(len(self.ecu.modifications_log), 0)
    
    def test_get_status(self):
        profile = PRESET_PROFILES['sport']
        self.ecu.apply_remap(profile)
        
        status = self.ecu.get_status()
        
        self.assertIn('model', status)
        self.assertIn('size_bytes', status)
        self.assertIn('parameters', status)
        self.assertIn('modifications', status)
    
    def test_calculate_performance_gain(self):
        profile = PRESET_PROFILES['sport']
        gains = self.ecu.calculate_performance_gain(profile)
        
        self.assertIn('power_gain_percent', gains)
        self.assertIn('torque_gain_percent', gains)
        self.assertGreater(gains['power_gain_percent'], 0)
    
    def test_hash_changes_after_remap(self):
        hash_before = self.ecu.original_hash
        profile = PRESET_PROFILES['sport']
        self.ecu.apply_remap(profile)
        
        import hashlib
        hash_after = hashlib.sha256(bytes(self.ecu.ecu_data)).hexdigest()
        
        self.assertNotEqual(hash_before, hash_after)


class TestECURemapIntegration(unittest.TestCase):
    """Testes de integração"""
    
    def test_complete_workflow(self):
        """Teste de workflow completo"""
        # 1. Criar ECU
        ecu_data = bytearray(512 * 1024)
        ecu = ECURemap(ecu_data)
        
        # 2. Aplicar remap
        profile = PRESET_PROFILES['extreme']
        ecu.apply_remap(profile)
        
        # 3. Salvar arquivo
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            temp_file = f.name
        
        try:
            ecu.save_to_file(temp_file, create_backup=False)
            
            # 4. Carregar arquivo
            ecu2 = ECURemap.load_from_file(temp_file)
            
            # 5. Verificar integridade
            status = ecu2.get_status()
            self.assertEqual(status['size_bytes'], len(ecu_data))
        
        finally:
            import os
            if Path(temp_file).exists():
                os.remove(temp_file)
    
    def test_multiple_profiles_sequential(self):
        """Teste aplicando múltiplos perfis sequencialmente"""
        ecu = ECURemap(bytearray(512 * 1024))
        
        profiles = [
            PRESET_PROFILES['eco'],
            PRESET_PROFILES['sport'],
            PRESET_PROFILES['extreme']
        ]
        
        for profile in profiles:
            ecu.apply_remap(profile)
            self.assertGreater(len(ecu.modifications_log), 0)


def run_tests():
    """Executa todos os testes"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    print("\n" + "="*70)
    print("EXECUTANDO TESTES UNITÁRIOS - ECU REMAP")
    print("="*70 + "\n")
    
    run_tests()
    
    print("\n" + "="*70)
    print("TESTES CONCLUÍDOS")
    print("="*70 + "\n")
