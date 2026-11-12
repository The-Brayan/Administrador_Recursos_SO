import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import main

class Seguridad(unittest.TestCase):
    def test_root_rechazado(self):
        with self.assertRaises(PermissionError):
            main.validar_entorno('linux', 0)

    def test_sistema_no_linux(self):
        with self.assertRaises(RuntimeError):
            main.validar_entorno('win32', 1000)

    def test_usuario_actual_visible(self):
        self.assertTrue(main.visible_para_usuario(1000, 1000))

    def test_otro_usuario_oculto(self):
        self.assertFalse(main.visible_para_usuario(1001, 1000))

    def test_ampliacion_de_alcance(self):
        self.assertTrue(main.visible_para_usuario(1001, 1000, True))

    def test_permisos_auditoria(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = main.configurar_auditoria(Path(tmp) / 'auditoria')
            path = Path(tmp) / 'auditoria' / 'auditoria.log'
            self.assertEqual(os.stat(path.parent).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            logger.info('PRUEBA')

if __name__ == '__main__':
    unittest.main()
