import os
import sqlite3


SCHEMA = """
CREATE TABLE ZCLOUDRECORDING (
    Z_PK INTEGER,
    ZUNIQUEID TEXT,
    ZPATH TEXT,
    ZENCRYPTEDTITLE TEXT,
    ZCUSTOMLABEL TEXT,
    ZDATE,
    ZDURATION,
    ZEVICTIONDATE
)
"""


def create_database(directory, rows=(), schema=SCHEMA):
    db_path = os.path.join(directory, "CloudRecordings.db")
    conn = sqlite3.connect(db_path)
    conn.execute(schema)
    if rows:
        conn.executemany(
            """
            INSERT INTO ZCLOUDRECORDING
                (Z_PK, ZUNIQUEID, ZPATH, ZENCRYPTEDTITLE, ZCUSTOMLABEL,
                 ZDATE, ZDURATION, ZEVICTIONDATE)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    conn.commit()
    conn.close()
    return db_path


def create_audio(recordings_dir, rel_path, content=b"audio"):
    path = os.path.join(recordings_dir, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as audio_file:
        audio_file.write(content)
    return path
