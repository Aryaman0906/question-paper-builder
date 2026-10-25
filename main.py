"""Run from any working directory: python path/to/main.py."""
import argparse
import json
import sqlite3
from pathlib import Path
from paperbuilder.storage import Repository, default_database_path, demo_blueprint
from paperbuilder.validation import availability


def main():
    parser = argparse.ArgumentParser(description='Question Paper Builder 0.5.1 PDF export and backups')
    parser.add_argument('--db', type=Path, help='Optional demo database location')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--generate-demo', action='store_true', help='Generate a checked demo paper as JSON without opening a window')
    parser.add_argument('--seed', type=int, help='Optional reproducible selection seed for --generate-demo')
    mode.add_argument('--check', action='store_true', help='Validate sample data without opening a window')
    args = parser.parse_args()
    if args.seed is not None and not args.generate_demo:
        parser.error('--seed requires --generate-demo')
    try:
        repo = Repository(args.db or default_database_path())
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f'Cannot open the question bank: {exc}')
        return 2
    try:
        if repo.is_new:
            repo.seed_demo()
        if args.generate_demo:
            from paperbuilder.generation import generate_paper
            print(json.dumps(generate_paper(demo_blueprint(), repo.questions(), include_demo=True, seed=args.seed), indent=2))
            return 0
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
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f'Cannot use the question bank: {exc}')
        return 2
    finally:
        repo.close()


if __name__ == '__main__':
    raise SystemExit(main())
