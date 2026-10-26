"""Windows API contracts tested with mocks; these are not native Windows runs."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest
from paperbuilder.display import enable_windows_dpi_awareness


class DpiTests(unittest.TestCase):
    def test_non_windows_does_not_load_windows_libraries(self):
        with patch('paperbuilder.display.sys.platform', 'linux'), patch('paperbuilder.display.ctypes.WinDLL', create=True) as load:
            self.assertEqual(enable_windows_dpi_awareness(), 'not-windows')
            load.assert_not_called()

    def test_modern_api_requests_system_aware_context(self):
        context = Mock(return_value=1)
        with patch('paperbuilder.display.sys.platform', 'win32'), patch('paperbuilder.display.ctypes.WinDLL', create=True, return_value=SimpleNamespace(SetProcessDpiAwarenessContext=context)):
            self.assertEqual(enable_windows_dpi_awareness(), 'system-aware')
        self.assertEqual(context.call_args.args[0].value, __import__('ctypes').c_void_p(-2).value)

    def test_existing_host_awareness_is_respected(self):
        library = SimpleNamespace(SetProcessDpiAwarenessContext=Mock(return_value=0))
        with patch('paperbuilder.display.sys.platform', 'win32'), patch('paperbuilder.display.ctypes.WinDLL', create=True, return_value=library) as load, patch('paperbuilder.display.ctypes.get_last_error', create=True, return_value=5):
            self.assertEqual(enable_windows_dpi_awareness(), 'already-configured')
            self.assertEqual(load.call_count, 1)

    def test_windows_81_fallback(self):
        awareness = Mock(return_value=0)
        with patch('paperbuilder.display.sys.platform', 'win32'), patch('paperbuilder.display.ctypes.WinDLL', create=True, side_effect=[SimpleNamespace(), SimpleNamespace(SetProcessDpiAwareness=awareness)]):
            self.assertEqual(enable_windows_dpi_awareness(), 'system-aware')
        awareness.assert_called_once_with(1)

    def test_legacy_fallback_and_unavailable_api(self):
        with patch('paperbuilder.display.sys.platform', 'win32'), patch('paperbuilder.display.ctypes.WinDLL', create=True, side_effect=[SimpleNamespace(), OSError(), SimpleNamespace(SetProcessDPIAware=Mock(return_value=1))]):
            self.assertEqual(enable_windows_dpi_awareness(), 'system-aware')
        with patch('paperbuilder.display.sys.platform', 'win32'), patch('paperbuilder.display.ctypes.WinDLL', create=True, side_effect=OSError()):
            self.assertEqual(enable_windows_dpi_awareness(), 'unavailable')

    def test_awareness_is_set_before_any_tk_window(self):
        import main
        order = []
        repository = Mock(is_new=False)
        root = Mock()
        with patch('sys.argv', ['main.py']), patch('main.Repository', return_value=repository), \
             patch('main.enable_windows_dpi_awareness', side_effect=lambda: order.append('dpi')), \
             patch('tkinter.Tk', side_effect=lambda: order.append('tk') or root), \
             patch('paperbuilder.gui.Application', side_effect=lambda *_: order.append('app')):
            self.assertEqual(main.main(), 0)
        self.assertEqual(order, ['dpi', 'tk', 'app'])
        repository.close.assert_called_once()
