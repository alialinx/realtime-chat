import psycopg2

from app.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from psycopg2.extras import RealDictCursor

def get_db():

    conn = psycopg2.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASSWORD)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cur


def close_db(conn, cur):
    cur.close()
    conn.close()