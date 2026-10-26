"""One wheel event scrolls the nearest eligible area beneath the pointer."""
import tkinter as tk
from tkinter import ttk


class WheelRouter:
    def __init__(self, root):
        self.root = root
        self.tag = 'QPBWheel' + str(id(root))
        self.system = root.tk.call('tk', 'windowingsystem')
        self.last_target = None
        self.remainder = 0.0
        for sequence in ('<MouseWheel>', '<Shift-MouseWheel>', '<Button-4>',
                         '<Button-5>', '<Shift-Button-4>', '<Shift-Button-5>'):
            root.bind_class(self.tag, sequence, self.route)
        # Map also catches controls created later inside editor dialogs.
        root.bind_all('<Map>', self.on_map, add='+')
        self.attach_tree(root)

    def attach_tree(self, widget):
        if not isinstance(widget, tk.Misc):
            return  # Tk-managed combobox popdowns may have no Python wrapper.
        tags = widget.bindtags()
        if self.tag not in tags:
            # Run before native class scrolling, preventing double movement.
            widget.bindtags((tags[0], self.tag, *tags[1:]))
        for child in widget.winfo_children():
            self.attach_tree(child)

    def on_map(self, event):
        self.attach_tree(event.widget)

    def route(self, event):
        if event.state & 0x4:  # Leave Ctrl-wheel shortcuts to the host widget.
            return None
        number = getattr(event, 'num', None)
        amount = -3 if number == 4 else 3 if number == 5 else 0
        if not amount:
            delta = getattr(event, 'delta', 0)
            if not delta:
                return None
            amount = -delta if self.system == 'aqua' else -delta / 120 * 3
        axis = 'x' if event.state & 1 else 'y'
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root) or event.widget
            if not isinstance(widget, tk.Misc):
                return None
            grab = self.root.grab_current()
            if grab is not None and grab.winfo_toplevel() != widget.winfo_toplevel():
                return 'break'  # A modal dialog must not scroll the window behind it.
            original = widget
            seen = set()
            while widget is not None:
                target = getattr(widget, 'wheel_target', None)
                if target is None and isinstance(widget, (tk.Text, tk.Listbox, ttk.Treeview)):
                    target = widget
                if target is not None and target._w not in seen:
                    seen.add(target._w)
                    start, end = getattr(target, axis + 'view')()
                    if (amount < 0 and start > 0.00001) or (amount > 0 and end < 0.99999):
                        key = (target._w, axis)
                        if self.last_target != key or amount * self.remainder < 0:
                            self.remainder = 0.0
                        self.last_target = key
                        total = self.remainder + amount
                        units = int(total)
                        self.remainder = total - units
                        if units:
                            getattr(target, axis + 'view_scroll')(units, 'units')
                        return 'break'
                widget = widget.master
            # Scrolling over a closed selector must not silently change a form.
            if isinstance(original, (ttk.Combobox, ttk.Spinbox)):
                return 'break'
        except (tk.TclError, KeyError):
            # A native popdown or a widget destroyed during input keeps its
            # ordinary bindings; no page registry or stale widget references.
            return None
        return None


def install_wheel_scrolling(root):
    if not hasattr(root, '_qpb_wheel'):
        root._qpb_wheel = WheelRouter(root)
    return root._qpb_wheel
