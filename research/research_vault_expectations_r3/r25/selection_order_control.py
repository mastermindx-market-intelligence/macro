"""Selected-SQL control; not execution of either full upstream module."""
import json, sqlite3
c=sqlite3.connect(':memory:')
c.execute('CREATE TABLE papers(blob_id TEXT,status TEXT,published_at TEXT,local_priority_score INTEGER)')
c.executemany('INSERT INTO papers VALUES(?,?,?,?)',[
    ('older_high_score','DISCOVERED','2026-09-10T12:00:00+00:00',1000),
    ('fresh_lower_score','DISCOVERED','2026-09-19T11:00:00+00:00',10)])
report=c.execute("SELECT blob_id FROM papers WHERE status IN (?,?) ORDER BY COALESCE(local_priority_score, 0) DESC, published_at DESC",('DISCOVERED','BLOB_FOUND')).fetchall()
actual_first=c.execute("SELECT blob_id FROM papers WHERE status IN (?,?) AND published_at IS NOT NULL AND published_at >= ? ORDER BY COALESCE(local_priority_score, 0) DESC, published_at DESC LIMIT 1",('DISCOVERED','BLOB_FOUND','2026-09-17T12:00:00+00:00')).fetchone()
assert report[0][0]=='older_high_score'
assert actual_first[0]=='fresh_lower_score'
print(json.dumps({'scope':'Selected upstream SQL with two synthetic rows; no full upstream module executed',
 'source_commit':'a1334a1a6c154b9b49664ee892d9710742fc6018',
 'report_first':report[0][0],'allocator_first':actual_first[0],
 'meaning':'Global-score backlog export is not the new-window-first runtime execution order.'},indent=2))
c.close()
