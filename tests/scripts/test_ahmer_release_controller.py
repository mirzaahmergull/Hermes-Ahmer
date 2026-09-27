"""A mapped SQLite sidecar must not prevent personal-release recovery."""
from contextlib import closing
import sqlite3

from scripts.ahmer import release


def test_restore_uses_sqlite_backup_with_an_open_wal_reader(tmp_path, monkeypatch):
    live = tmp_path / 'live'
    saved = tmp_path / 'saved'
    live.mkdir()
    saved.mkdir()
    monkeypatch.setattr(release, 'HOME', live)
    (saved / 'config.yaml').write_text('preserved config')
    (live / 'config.yaml').write_text('new config')
    with closing(sqlite3.connect(saved / 'state.db')) as db:
        db.execute('create table messages(text)')
        db.execute("insert into messages values ('preserved message')")
        db.commit()
    with closing(sqlite3.connect(live / 'state.db')) as reader:
        reader.execute('pragma journal_mode=wal')
        reader.execute('create table messages(text)')
        reader.execute("insert into messages values ('new message')")
        reader.commit()
        reader.execute('select * from messages').fetchall()
        assert (live / 'state.db-shm').exists()
        release.restore_home(saved)
        assert reader.execute('select text from messages').fetchall() == [('preserved message',)]
    assert (live / 'config.yaml').read_text() == 'preserved config'
