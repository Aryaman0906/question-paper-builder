"""Stage complete output beside its destination; preserve prior files on failures."""
from contextlib import contextmanager
from pathlib import Path
import os
import tempfile


@contextmanager
def staged_output(destination, overwrite=False):
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and not overwrite:
        raise FileExistsError('Choose a new filename; this file already exists.')
    fd, name = tempfile.mkstemp(prefix='.qpb-', suffix='.tmp', dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    reservation = None
    try:
        yield temporary
        # Windows _commit/FlushFileBuffers requires a writable handle.
        # r+b retains all bytes produced by the PDF/SQLite writer (unlike wb).
        with temporary.open('r+b') as stream:
            os.fsync(stream.fileno())
        if not overwrite:
            # Reserve exclusively; works on Windows and removable drives without hard links.
            fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            reservation = os.fstat(fd)
            os.close(fd)
        os.replace(temporary, destination)
        reservation = None
    finally:
        temporary.unlink(missing_ok=True)
        if reservation is not None:
            try:
                current = destination.stat()
                if (current.st_dev, current.st_ino) == (reservation.st_dev, reservation.st_ino):
                    destination.unlink()
            except FileNotFoundError:
                pass
