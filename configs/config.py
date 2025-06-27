import pyodbc

class Config:
    SQL_SERVER = '10.30.0.18,1433'
    SQL_DATABASE = 'DV_DATA_LAKE'
    SQL_USER = 'sa'
    SQL_PASSWORD = 'greenland@VN'
    SQL_DRIVER = '{ODBC Driver 17 for SQL Server}'
    
    @staticmethod
    def get_db_connection():
        conn = pyodbc.connect(
            f'DRIVER={Config.SQL_DRIVER};'
            f'SERVER={Config.SQL_SERVER};'
            f'DATABASE={Config.SQL_DATABASE};'
            f'UID={Config.SQL_USER};'
            f'PWD={Config.SQL_PASSWORD}'
        )
        return conn