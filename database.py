import psycopg2
import numpy as np


class Database:
    def __init__(self, db_params):
        self.db_params = db_params
        self.connection = psycopg2.connect(**self.db_params)
        self.cursor = self.connection.cursor()
        self.create_table()
        self.create_users_table()

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

    def load_face_encodings_ordered_by_appearances(self):
        select_query = "SELECT face_id, encoding, name, appearances FROM face_dict ORDER BY appearances DESC;"
        self.cursor.execute(select_query)
        rows = self.cursor.fetchall()

        face_dict = {}
        for row in rows:
            face_id, encoding_bytes, name, appearances = row
            encoding_array = np.frombuffer(encoding_bytes, dtype=np.uint8)
            encoding = np.frombuffer(encoding_array, dtype=np.float64)
            face_dict[face_id] = (encoding, name, appearances)

        return face_dict

    def update_face_name(self, face_id, new_name):
        update_query = "UPDATE face_dict SET name = %s WHERE face_id = %s;"
        self.cursor.execute(update_query, (new_name, face_id))
        self.connection.commit()

    def update_face_image(self, face_id, new_image_path):
        update_query = "UPDATE face_dict SET image_path = %s WHERE face_id = %s;"
        self.cursor.execute(update_query, (new_image_path, face_id))
        self.connection.commit()

    def create_users_table(self):
        create_table_query = '''
            CREATE TABLE IF NOT EXISTS users (
                user_id INT PRIMARY KEY,
                username TEXT,
                role TEXT DEFAULT 'user'
            );
        '''
        self.cursor.execute(create_table_query)
        self.connection.commit()

    def insert_user(self, user_id, username, role='user'):
        insert_query = '''
            INSERT INTO users (user_id, username, role) VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING;
        '''
        self.cursor.execute(insert_query, (user_id, username, role))
        self.connection.commit()

    def change_user_role(self, user_id, new_role):
        update_query = '''
            UPDATE users SET role = %s WHERE user_id = %s;
        '''
        self.cursor.execute(update_query, (new_role, user_id))
        self.connection.commit()

    def get_user_role(self, user_id):
        select_query = '''
            SELECT role FROM users WHERE user_id = %s;
        '''
        self.cursor.execute(select_query, (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_all_users(self):
        select_query = '''
            SELECT * FROM users;
        '''
        self.cursor.execute(select_query)
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()
        self.connection.close()
