import sqlite3
from datetime import datetime
from typing import List, Dict, Any
import json


class Database:
    """База данных для хранения истории расчетов."""
    
    def __init__(self, db_name: str = 'tank_calculator.db'):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица расчетов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    params TEXT,
                    results TEXT,
                    total_cost REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
    
    def save_user(self, user_id: int, username: str = None, 
                  first_name: str = None, last_name: str = None):
        """Сохранение пользователя."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()
    
    def save_calculation(self, user_id: int, params: Dict, 
                        results: Dict, total_cost: float):
        """Сохранение расчета."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO calculations 
                (user_id, params, results, total_cost)
                VALUES (?, ?, ?, ?)
            ''', (user_id, json.dumps(params), 
                  json.dumps(results), total_cost))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_calculations(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получение истории расчетов пользователя."""
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM calculations 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            calculations = []
            for row in cursor.fetchall():
                calc = dict(row)
                calc['params'] = json.loads(calc['params'])
                calc['results'] = json.loads(calc['results'])
                calculations.append(calc)
            
            return calculations
    
    def get_statistics(self, user_id: int = None) -> Dict[str, Any]:
        """Получение статистики."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Общее количество расчетов
            if user_id:
                cursor.execute(
                    'SELECT COUNT(*) FROM calculations WHERE user_id = ?',
                    (user_id,)
                )
            else:
                cursor.execute('SELECT COUNT(*) FROM calculations')
            stats['total_calculations'] = cursor.fetchone()[0]
            
            # Средняя стоимость
            if user_id:
                cursor.execute(
                    'SELECT AVG(total_cost) FROM calculations WHERE user_id = ?',
                    (user_id,)
                )
            else:
                cursor.execute('SELECT AVG(total_cost) FROM calculations')
            stats['average_cost'] = cursor.fetchone()[0] or 0
            
            # Максимальная стоимость
            if user_id:
                cursor.execute(
                    'SELECT MAX(total_cost) FROM calculations WHERE user_id = ?',
                    (user_id,)
                )
            else:
                cursor.execute('SELECT MAX(total_cost) FROM calculations')
            stats['max_cost'] = cursor.fetchone()[0] or 0
            
            return stats