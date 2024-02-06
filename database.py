import psycopg2
import numpy as np

class Database:
    def __init__(self, db_params):
        self.db_params = db_params
        self.connection = psycopg2.connect(**self.db_params)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        create_table_query = '''
            CREATE TABLE IF NOT EXISTS face_dict (
                face_id SERIAL PRIMARY KEY,
                encoding BYTEA,
                image_path TEXT,
                name TEXT DEFAULT NULL,
                appearances INT DEFAULT 0
            );
        '''
        self.cursor.execute(create_table_query)
        self.connection.commit()

    def insert_face_dict(self, face_id, encoding, image_path, name=None):
        encoding, _ = encoding
        if encoding.all():
            insert_query = '''
                INSERT INTO face_dict (face_id, encoding, image_path, name, appearances) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (face_id) DO NOTHING;
            '''
            self.cursor.execute(insert_query, (face_id, psycopg2.Binary(encoding.tobytes()), image_path, name, 0))
        self.connection.commit()

    def update_face_encoding(self, face_id, encoding, image_path):
        update_query = "UPDATE face_dict SET encoding = %s, image_path = %s, appearances = appearances + 1 WHERE face_id = %s;"
        self.cursor.execute(update_query, (psycopg2.Binary(encoding.tobytes()), image_path, face_id))
        self.connection.commit()

    def load_face_encodings(self):
        select_query = "SELECT face_id, encoding, name FROM face_dict;"
        self.cursor.execute(select_query)
        rows = self.cursor.fetchall()

        face_dict = {}
        for row in rows:
            face_id, encoding_bytes, name = row
            encoding_array = np.frombuffer(encoding_bytes, dtype=np.uint8)
            encoding = np.frombuffer(encoding_array, dtype=np.float64)
            face_dict[face_id] = (encoding, name)

        return face_dict

    def close(self):
        self.cursor.close()
        self.connection.close()