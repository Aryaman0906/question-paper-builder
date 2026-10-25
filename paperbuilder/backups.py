"""Validated SQLite backup and transactional restore of application data."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import time
import uuid
from .storage import Repository, ROOT, BankError
from .blueprints import list_blueprints, load_blueprint
from .papers import list_papers, load_paper
from .validation import question_errors, prompt_hash
from .file_output import staged_output

TABLES = ('questions', 'blueprints', 'blueprint_rows', 'papers')
MAX_BYTES = 200 * 1024 * 1024


class BackupError(ValueError):
    pass


def _read_only(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=3)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA trusted_schema=OFF')
    connection.execute('PRAGMA query_only=ON')
    return connection


def _copy(source, destination):
    deadline = time.monotonic() + 10
    page_size = source.execute('PRAGMA page_size').fetchone()[0]
    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise BackupError('Database is busy or the copy took too long. Close other app copies and retry.')
        if total * page_size > MAX_BYTES:
            raise BackupError('Backups larger than 200 MiB are not supported in this release.')
    source.backup(destination, pages=256, progress=progress, sleep=0.05)


def _adapter(connection):
    repo = Repository.__new__(Repository)
    repo.connection = connection
    return repo


def _columns(connection, table):
    return [row['name'] for row in connection.execute('PRAGMA table_info(' + table + ')')]


def _canonical_copy(source):
    """Read only known tables and insert into our own schema; never run backup SQL."""
    clean = sqlite3.connect(':memory:')
    clean.row_factory = sqlite3.Row
    try:
        if source.execute('PRAGMA user_version').fetchone()[0] != 2:
            raise BackupError('Restore requires a schema version 2 backup (Phase 2 or later).')
        if [r[0] for r in source.execute('PRAGMA integrity_check')] != ['ok']:
            raise BackupError('The backup failed SQLite integrity checks.')
        clean.executescript((ROOT / 'paperbuilder' / 'schema.sql').read_text(encoding='utf-8'))
        expected = {(r['type'], r['name'], r['tbl_name']) for r in clean.execute(
            "SELECT type,name,tbl_name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
        actual = {(r['type'], r['name'], r['tbl_name']) for r in source.execute(
            "SELECT type,name,tbl_name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
        if actual != expected:
            raise BackupError('This is not a supported Question Paper Builder database schema.')
        with clean:
            for table in TABLES:
                columns = _columns(clean, table)
                if set(_columns(source, table)) != set(columns):
                    raise BackupError('Unexpected columns in backup table ' + table + '.')
                statement = source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
                if 'VIRTUAL' in statement.upper():
                    raise BackupError('Virtual tables are not supported.')
                names = ','.join(columns)
                clean.executemany('INSERT INTO ' + table + ' (' + names + ') VALUES (' + ','.join('?' for _ in columns) + ')',
                                  source.execute('SELECT ' + names + ' FROM ' + table))
        if clean.execute('PRAGMA foreign_key_check').fetchone():
            raise BackupError('The backup contains orphaned blueprint rows.')
        repo = _adapter(clean)
        for q in repo.questions():
            errors = question_errors(q)
            if errors or type(q['revision']) is not int or q['revision'] < 1 or q['prompt_hash'] != prompt_hash(q['prompt']):
                raise BackupError('Invalid question in backup: ' + q['id'])
        for bp in list_blueprints(repo):
            load_blueprint(repo, bp['id'])
            positions = [r[0] for r in clean.execute('SELECT position FROM blueprint_rows WHERE blueprint_id=? ORDER BY position', (bp['id'],))]
            if positions != list(range(1, len(positions)+1)):
                raise BackupError('Blueprint row positions are not consecutive.')
        parents = {}
        for record in list_papers(repo):
            paper = load_paper(repo, record['id'])
            parents[paper['paper_id']] = paper.get('parent_paper_id')
        for identifier in parents:
            seen = set()
            while identifier:
                if identifier in seen or identifier not in parents:
                    raise BackupError('Saved-paper revision lineage is broken or cyclic.')
                seen.add(identifier); identifier = parents[identifier]
        return clean
    except Exception:
        clean.close()
        raise


def _summary(connection):
    result = {table: connection.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in TABLES}
    result['archived'] = connection.execute('SELECT count(*) FROM questions WHERE active=0').fetchone()[0]
    return result


@contextmanager
def prepare_restore(source_path, active_path):
    """Hold a private validated snapshot so confirmation refers to stable contents."""
    source_path, active_path = Path(source_path).resolve(), Path(active_path).resolve()
    snapshot, clean = None, None
    try:
        if source_path == active_path or (source_path.exists() and active_path.exists() and source_path.samefile(active_path)):
            raise BackupError('Choose a separate backup file, not the active database.')
        if not source_path.is_file() or source_path.stat().st_size > MAX_BYTES:
            raise BackupError('Choose a readable database backup no larger than 200 MiB.')
        source = _read_only(source_path)
        try:
            snapshot = sqlite3.connect(':memory:'); snapshot.row_factory = sqlite3.Row
            _copy(source, snapshot)
        finally:
            source.close()
        clean = _canonical_copy(snapshot)
        yield SimpleNamespace(connection=clean, summary=_summary(clean), source_path=source_path)
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        if isinstance(exc, BackupError):
            raise
        raise BackupError('Cannot use this backup: ' + str(exc)) from exc
    finally:
        if clean is not None: clean.close()
        if snapshot is not None: snapshot.close()


def create_backup(repository, destination):
    """SQLite's backup API includes committed WAL content; raw file copying does not."""
    destination = Path(destination).expanduser().resolve()
    try:
        if destination == repository.path.resolve():
            raise BackupError('A backup must use a different file from the active database.')
        if destination.suffix.lower() not in ('.sqlite3', '.db', '.bak'):
            raise BackupError('Use a .sqlite3, .db or .bak backup filename.')
        if repository.connection.in_transaction:
            raise BackupError('Finish the current database change before backing up.')
        with staged_output(destination) as temporary:
            target = sqlite3.connect(temporary)
            try:
                _copy(repository.connection, target)
                target.row_factory = sqlite3.Row
                checked = _canonical_copy(target)
                try: summary = _summary(checked)
                finally: checked.close()
            finally:
                target.close()
        return summary
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        if isinstance(exc, BackupError): raise
        raise BackupError('Backup was not saved: ' + str(exc)) from exc


def restore_backup(repository, prepared):
    """Replace rows in one transaction, retaining the open connection and DB schema."""
    # Recheck prepared contents before the write lock. GUI cannot edit this private snapshot.
    checked = None
    recovery = repository.path.with_name(repository.path.name + '.before-restore-' +
                datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.bak')
    try:
        checked = _canonical_copy(prepared.connection)
        with repository._write():
            # The reserved writer lock prevents changes between recovery copy and restore.
            # A separate reader sees committed old contents and avoids backing up a writer transaction.
            reader = _read_only(repository.path)
            try:
                with staged_output(recovery) as temporary:
                    target = sqlite3.connect(temporary)
                    try: _copy(reader, target)
                    finally: target.close()
            finally:
                reader.close()
            for table in reversed(TABLES):
                repository.connection.execute('DELETE FROM ' + table)
            for table in TABLES:
                columns = _columns(checked, table)
                names = ','.join(columns)
                repository.connection.executemany('INSERT INTO ' + table + ' (' + names + ') VALUES (' + ','.join('?' for _ in columns) + ')',
                                                 checked.execute('SELECT ' + names + ' FROM ' + table))
            if repository.connection.execute('PRAGMA foreign_key_check').fetchone():
                raise BackupError('Restored database failed foreign-key checks.')
        return recovery
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        detail = f' Recovery copy: {recovery}' if recovery.exists() else ''
        raise BackupError('Restore failed; database changes were rolled back. ' + str(exc) + detail) from exc
    finally:
        if checked is not None: checked.close()
