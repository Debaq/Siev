import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="pacientes.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_database()
    
    def init_database(self):
        """Inicializa la base de datos SQLite"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS registros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_paciente TEXT NOT NULL,
                    oido_irrigado TEXT NOT NULL,
                    temperatura REAL NOT NULL,
                    fecha_hora TEXT NOT NULL,
                    archivo_video TEXT,
                    duracion_grabacion INTEGER DEFAULT 0
                )
            ''')
            self.conn.commit()
            print("Base de datos inicializada correctamente")
        except Exception as e:
            print(f"Error inicializando base de datos: {e}")
            raise
    
    def insert_record(self, nombre, oido, temperatura, archivo_video="", duracion=0):
        """Inserta un nuevo registro"""
        try:
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.cursor.execute('''
                INSERT INTO registros (nombre_paciente, oido_irrigado, temperatura, 
                                     fecha_hora, archivo_video, duracion_grabacion)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nombre, oido, temperatura, fecha_hora, archivo_video, duracion))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error insertando registro: {e}")
            return False
    
    def get_all_records(self):
        """Obtiene todos los registros"""
        try:
            self.cursor.execute('SELECT * FROM registros ORDER BY fecha_hora DESC')
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error obteniendo registros: {e}")
            return []
    
    def close(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()