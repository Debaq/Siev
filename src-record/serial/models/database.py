import sqlite3
import os

class Database:
    def __init__(self, db_path="pacientes.db"):
        self.db_path = db_path
        try:
            self.conn = sqlite3.connect(db_path)
            self.create_table()
        except Exception as e:
            print(f"Error conectando a la base de datos: {e}")
            raise

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            identificacion TEXT NOT NULL UNIQUE,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        try:
            self.conn.execute(query)
            self.conn.commit()
        except Exception as e:
            print(f"Error creando tabla: {e}")
            raise

    def insert_paciente(self, nombre, identificacion):
        query = "INSERT INTO pacientes (nombre, identificacion) VALUES (?, ?)"
        try:
            self.conn.execute(query, (nombre, identificacion))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("Ya existe un paciente con esta identificación")
        except Exception as e:
            print(f"Error insertando paciente: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()