"""Run from any working directory: python path/to/main.py."""
import argparse
import json
from pathlib import Path
from paperbuilder.storage import Repository, default_database_path, demo_blueprint
from paperbuilder.validation import availability


def main():
    parser = argparse.ArgumentParser(description='Question Paper Builder 0.1 foundations')
    parser.add_argument('--db', type=Path, help='Optional demo database location')
    parser.add_argument('--check', action='store_true', help='Validate sample data without opening a window')
    args = parser.parse_args()
    repo = Repository(args.db or default_database_path())
    try:
        repo.seed_demo()
        if args.check:
            report = availability(demo_blueprint(), repo.questions(), include_demo=True)
            print(json.dumps(report, indent=2))
            return 0 if report['valid'] else 1
        from paperbuilder.gui import Application
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            print(f'Cannot open a GUI: {exc}\nRun on a desktop with Tkinter, or use --check for data checks.')
            return 2
        Application(root, repo)
        root.mainloop()
        return 0
    finally:
        repo.close()


if __name__ == '__main__':
    raise SystemExit(main())
