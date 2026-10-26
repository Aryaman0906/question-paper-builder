"""Native desktop design system. No third-party GUI dependencies."""
import tkinter as tk
from tkinter import ttk, font
from tkinter.scrolledtext import ScrolledText as TkScrolledText
from .scrolling import install_wheel_scrolling


BG = '#F4F5FA'
SURFACE = '#FFFFFF'
INK = '#20263D'
MUTED = '#626B82'
LINE = '#DFE3EE'
ACCENT = '#5C4CC4'
NAV = '#171E35'
SOFT = '#EEEAFB'


def size_main_window(root):
    """Use DPI-scaled dimensions, leaving screen space for window borders."""
    scale = max(1.0, root.winfo_fpixels('1i') / 96)
    width = min(round(1280 * scale), max(640, root.winfo_screenwidth() - 40))
    height = min(round(850 * scale), max(480, root.winfo_screenheight() - round(80 * scale)))
    root.geometry(f'{width}x{height}')
    root.minsize(min(width, round(960 * scale)), min(height, round(680 * scale)))


def setup_theme(root):
    available = set(font.families(root))
    family = next((name for name in ('Segoe UI', 'DejaVu Sans', 'Helvetica', 'Arial') if name in available),
                  font.nametofont('TkDefaultFont').actual('family'))
    mono = next((name for name in ('Consolas', 'DejaVu Sans Mono', 'Menlo', 'Courier') if name in available),
                font.nametofont('TkFixedFont').actual('family'))
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
        font.nametofont(name).configure(family=family, size=11)
    font.nametofont('TkFixedFont').configure(family=mono, size=11)
    root.configure(background=BG)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font='TkDefaultFont', background=BG, foreground=INK,
                    bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
    style.configure('TFrame', background=BG)
    style.configure('Card.TFrame', background=SURFACE)
    style.configure('Panel.TFrame', background=SURFACE, borderwidth=1, relief='solid')
    style.configure('Nav.TFrame', background=NAV)
    style.configure('TLabel', background=BG, foreground=INK)
    style.configure('Muted.TLabel', foreground=MUTED)
    style.configure('Heading.TLabel', font=(family, 23, 'bold'))
    style.configure('Section.TLabel', font=(family, 13, 'bold'))
    style.configure('Card.TLabel', background=SURFACE)
    style.configure('CardTitle.TLabel', background=SURFACE, font=(family, 12, 'bold'))
    style.configure('CardMuted.TLabel', background=SURFACE, foreground=MUTED)
    style.configure('Stat.TLabel', background=SURFACE, foreground=ACCENT, font=(family, 25, 'bold'))
    style.configure('Badge.TLabel', background=SOFT, foreground=ACCENT, padding=(10, 5))
    style.configure('Notice.TLabel', background='#FFF3DC', foreground='#79521B', padding=(12, 8))
    style.configure('TButton', padding=(12, 8), background=SURFACE, foreground=INK,
                    borderwidth=1, relief='flat', focusthickness=2, focuscolor=ACCENT)
    style.map('TButton', background=[('disabled', '#EBEDF3'), ('pressed', '#E2DDF7'), ('active', SOFT)],
              foreground=[('disabled', '#7C8395')], bordercolor=[('focus', ACCENT)])
    style.configure('Primary.TButton', background=ACCENT, foreground=SURFACE, bordercolor=ACCENT,
                    font=(family, 11, 'bold'), focuscolor=SURFACE)
    style.map('Primary.TButton', background=[('disabled', '#E4E0F1'), ('pressed', '#413298'), ('active', '#4D3DAC')],
              foreground=[('disabled', '#777089'), ('!disabled', SURFACE)])
    style.configure('Quiet.TButton', background=BG, foreground=MUTED, borderwidth=0)
    style.configure('Link.TButton', background=SURFACE, foreground=ACCENT, borderwidth=0)
    style.configure('Caption.TLabel', foreground=MUTED, font=(family, 10))
    style.configure('Danger.TButton', foreground='#A02E37')
    style.configure('Nav.TButton', background=NAV, foreground='#C3CBDD', anchor='w',
                    borderwidth=0, padding=(16, 13), focuscolor='#C4B9FF')
    style.map('Nav.TButton', background=[('active', '#252E4C'), ('pressed', '#303958')],
              foreground=[('active', SURFACE)])
    style.configure('Active.Nav.TButton', background='#373259', foreground=SURFACE, font=(family, 11, 'bold'))
    style.map('Active.Nav.TButton', background=[('active', '#443B70'), ('!active', '#373259')])
    style.configure('TEntry', padding=(8, 6), fieldbackground=SURFACE, insertcolor=INK)
    style.configure('TCombobox', padding=(8, 6), fieldbackground=SURFACE, arrowsize=14)
    for kind in ('TEntry', 'TCombobox'):
        style.map(kind, bordercolor=[('focus', ACCENT)],
                  fieldbackground=[('readonly', SURFACE), ('disabled', '#EBEDF3')],
                  foreground=[('readonly', INK)])
    style.configure('TCheckbutton', padding=(4, 6), focuscolor=ACCENT)
    style.map('TCheckbutton', background=[('active', SOFT)])
    style.configure('TNotebook', background=BG, borderwidth=0, tabmargins=(0, 0, 0, 6))
    style.configure('TNotebook.Tab', padding=(16, 9), background='#E8EAF2', borderwidth=0)
    style.map('TNotebook.Tab', background=[('selected', SURFACE), ('active', SOFT)],
              foreground=[('selected', ACCENT)])
    style.layout('Workspace.TNotebook.Tab', [])
    style.configure('Workspace.TNotebook', tabmargins=0, borderwidth=0,
                    bordercolor=BG, lightcolor=BG, darkcolor=BG)
    style.configure('TLabelframe', background=SURFACE, borderwidth=1, relief='solid')
    style.configure('TLabelframe.Label', background=SURFACE, font=(family, 11, 'bold'))
    style.configure('Treeview', background=SURFACE, fieldbackground=SURFACE, foreground=INK,
                    rowheight=font.nametofont('TkDefaultFont').metrics('linespace') + 16, borderwidth=0)
    style.configure('Treeview.Heading', background='#EDEFF6', foreground=MUTED,
                    font=(family, 10, 'bold'), padding=(10, 10), relief='flat')
    style.map('Treeview', background=[('selected', SOFT)], foreground=[('selected', '#3F308F')])
    style.map('Treeview.Heading', background=[('active', '#E1DDF3')])
    style.configure('TScrollbar', background='#CBD0DF', troughcolor=BG, borderwidth=0, arrowsize=12)
    style.configure('TPanedwindow', background=BG)
    root.option_add('*TCombobox*Listbox.background', SURFACE)
    root.option_add('*TCombobox*Listbox.foreground', INK)
    root.option_add('*TCombobox*Listbox.selectBackground', SOFT)
    root.option_add('*TCombobox*Listbox.selectForeground', INK)
    install_wheel_scrolling(root)
    return family


class ScrolledText(TkScrolledText):
    """Consistent readable text fields, retaining normal Tk editing semantics."""
    def __init__(self, master=None, **kwargs):
        supplied = kwargs.pop('font', None)
        monospace = isinstance(supplied, tuple) and supplied[0] in ('Consolas', 'Courier')
        defaults = dict(width=1, borderwidth=0, relief='flat', highlightthickness=1,
                        highlightbackground=LINE, highlightcolor=ACCENT, background=SURFACE,
                        foreground=INK, insertbackground=ACCENT, selectbackground=SOFT,
                        selectforeground=INK, padx=14, pady=12, spacing1=2, spacing3=3,
                        font='TkFixedFont' if monospace else 'TkTextFont')
        defaults.update(kwargs)
        super().__init__(master, **defaults)
        # Use the same themed scrollbar as tables and pages, including hover.
        self.vbar.destroy()
        self.vbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.yview)
        self.vbar.pack(side='right', fill='y', before=self._w)
        self.configure(yscrollcommand=self.vbar.set)


def stripe_tree(tree):
    tree.tag_configure('even', background=SURFACE)
    tree.tag_configure('odd', background='#F8F9FC')
    for index, item in enumerate(tree.get_children()):
        tree.item(item, tags=('odd' if index % 2 else 'even',))


class ScrollPage(ttk.Frame):
    """Expand on large screens; expose overflow at small sizes / higher DPI.

    Nested tables/text scroll first; the wheel continues into the containing
    page at their boundary. Focus visibility also keeps form controls reachable.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, background=BG, borderwidth=0, highlightthickness=0,
                                width=1, height=1,
                                xscrollincrement=max(12, round(self.winfo_fpixels('12p'))),
                                yscrollincrement=max(12, round(self.winfo_fpixels('12p'))))
        self.wheel_target = self.canvas
        self.canvas.wheel_target = self.canvas
        self.body = ttk.Frame(self.canvas, padding=(2, 2, 16, 14))
        self.window = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.ybar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.xbar = ttk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.ybar.set, xscrollcommand=self.xbar.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.rowconfigure(0, weight=1); self.columnconfigure(0, weight=1)
        self.canvas.bind('<Configure>', self.resize)
        self.body.bind('<Configure>', self.resize)
        self.bind('<Map>', self.resize)

    def resize(self, _event=None):
        width = max(self.canvas.winfo_width(), self.body.winfo_reqwidth())
        height = max(self.canvas.winfo_height(), self.body.winfo_reqheight())
        self.canvas.itemconfigure(self.window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))
        if self.body.winfo_reqheight() > self.winfo_height():
            self.ybar.grid(row=0, column=1, sticky='ns')
        else:
            self.ybar.grid_remove()
        if self.body.winfo_reqwidth() > self.winfo_width() - (12 if self.ybar.winfo_ismapped() else 0):
            self.xbar.grid(row=1, column=0, sticky='ew')
        else:
            self.xbar.grid_remove()

    def reveal(self, widget):
        if not str(widget).startswith(str(self.body) + '.'):
            return
        x = widget.winfo_rootx() - self.body.winfo_rootx()
        y = widget.winfo_rooty() - self.body.winfo_rooty()
        for start, size, viewport, total, offset, move in (
            (x, widget.winfo_width(), self.canvas.winfo_width(), self.body.winfo_width(), self.canvas.canvasx(0), self.canvas.xview_moveto),
            (y, widget.winfo_height(), self.canvas.winfo_height(), self.body.winfo_height(), self.canvas.canvasy(0), self.canvas.yview_moveto)):
            if start < offset:
                move(max(0, start - 8) / max(1, total))
            elif start + size > offset + viewport:
                move(max(0, start + min(size, viewport) - viewport + 8) / max(1, total))


def decorate_text(widget):
    """Presentation tags only; never rewrite snapshot text or code indentation."""
    widget.tag_configure('heading', font=(font.nametofont('TkDefaultFont').actual('family'), 12, 'bold'), foreground=ACCENT, spacing1=12, spacing3=6)
    widget.tag_configure('warning', foreground='#885C1D', background='#FFF3DC')
    for number, line in enumerate(widget.get('1.0', 'end-1c').splitlines(), 1):
        if line.startswith('Section ') or (line.isupper() and len(line) < 90):
            widget.tag_add('heading', f'{number}.0', f'{number}.end')
        if line.startswith('DEMONSTRATION ONLY'):
            widget.tag_add('warning', f'{number}.0', f'{number}.end')
