"""Real Tk wheel dispatch tests, including nested controls and late dialogs."""
import tkinter as tk
from tkinter import ttk
import unittest
from paperbuilder.ui import ScrollPage, ScrolledText, setup_theme
from paperbuilder.scrolling import install_wheel_scrolling


class WheelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            root = tk.Tk(); root.destroy()
        except tk.TclError as exc:
            raise unittest.SkipTest('A Tk display is required: ' + str(exc))

    def setUp(self):
        self.root = tk.Tk(); self.root.tk.call('tk', 'scaling', 96 / 72)
        self.root.geometry('700x500')
        setup_theme(self.root)
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.page = ScrollPage(self.root); self.page.pack(fill='both', expand=True)
        self.label = ttk.Label(self.page.body, text='Scroll anywhere on this page')
        self.label.pack(anchor='w')
        self.text = ScrolledText(self.page.body, height=4, wrap='none')
        self.text.pack(fill='x')
        self.text.insert('1.0', '\n'.join('Line ' + str(i) for i in range(100)))
        self.tree = ttk.Treeview(self.page.body, height=4); self.tree.pack(fill='x')
        for i in range(100): self.tree.insert('', 'end', text=str(i))
        self.choice = tk.StringVar(value='A')
        self.combo = ttk.Combobox(self.page.body, values=('A', 'B'), textvariable=self.choice, state='readonly')
        self.combo.pack(anchor='w')
        ttk.Frame(self.page.body, height=1200, width=1200).pack()
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.assertEqual(self.errors, [])

    def wheel(self, widget, delta=-120, state=0, sequence='<MouseWheel>'):
        args = dict(x=4, y=4, rootx=widget.winfo_rootx()+4,
                    rooty=widget.winfo_rooty()+4, state=state)
        if 'MouseWheel' in sequence: args['delta'] = delta
        widget.event_generate(sequence, **args)
        self.root.update()

    def test_page_scrolls_over_label_and_shift_scrolls_horizontally(self):
        self.wheel(self.label)
        self.assertGreater(self.page.canvas.yview()[0], 0)
        self.page.canvas.yview_moveto(0); self.root.update()
        self.wheel(self.label, state=1)
        self.assertGreater(self.page.canvas.xview()[0], 0)

    def test_nested_text_scrolls_once_then_parent_at_boundary(self):
        self.text.yview_scroll(3, 'units'); expected = self.text.yview()
        self.text.yview_moveto(0); self.root.update()
        parent = self.page.canvas.yview()
        self.wheel(self.text)
        self.assertEqual(self.text.yview(), expected)
        self.assertEqual(self.page.canvas.yview(), parent)
        self.text.yview_moveto(1); self.root.update()
        self.wheel(self.text)
        self.assertGreater(self.page.canvas.yview()[0], parent[0])

    def test_table_scrolls_without_moving_parent(self):
        self.tree.yview_scroll(3, 'units'); expected = self.tree.yview()
        self.tree.yview_moveto(0); self.root.update()
        parent = self.page.canvas.yview()
        self.wheel(self.tree)
        self.assertEqual(self.tree.yview(), expected)
        self.assertEqual(self.page.canvas.yview(), parent)

    def test_small_deltas_accumulate_without_native_double_scroll(self):
        self.root._qpb_wheel.system = 'win32'
        before = self.page.canvas.yview()
        self.wheel(self.label, delta=-20)
        self.assertEqual(self.page.canvas.yview(), before)
        self.wheel(self.label, delta=-20)
        self.assertGreater(self.page.canvas.yview()[0], before[0])

    def test_linux_wheel_and_selector_value_preservation(self):
        self.wheel(self.label, sequence='<Button-5>')
        self.assertGreater(self.page.canvas.yview()[0], 0)
        self.page.canvas.yview_moveto(0); self.root.update()
        self.wheel(self.combo)
        self.assertEqual(self.choice.get(), 'A')
        self.assertGreater(self.page.canvas.yview()[0], 0)

    def test_dialog_created_later_and_router_installed_once(self):
        router = self.root._qpb_wheel
        self.assertIs(install_wheel_scrolling(self.root), router)
        dialog = tk.Toplevel(self.root); dialog.geometry('400x300')
        page = ScrollPage(dialog); page.pack(fill='both', expand=True)
        label = ttk.Label(page.body, text='New dialog'); label.pack()
        ttk.Frame(page.body, height=1200, width=200).pack()
        dialog.grab_set(); self.root.update()
        self.wheel(label)
        self.assertGreater(page.canvas.yview()[0], 0)
        self.assertEqual(label.bindtags().count(router.tag), 1)
        dialog.destroy(); self.root.update()
