import mysql.connector
import streamlit as st

def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"]
    )

def register_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        return True
    except mysql.connector.Error:
        return False
    finally:
        cursor.close()
        conn.close()

def login_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def save_survey(username, age, genres, actors, year_from, year_to, suggestions):
    conn = get_connection()
    cursor = conn.cursor()
    genres_str = ",".join(genres)
    
    query = """
    INSERT INTO user_surveys (username, age, favorite_genres, favorite_actors, year_from, year_to, suggestions)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    age=%s, favorite_genres=%s, favorite_actors=%s, year_from=%s, year_to=%s, suggestions=%s
    """
    cursor.execute(query, (username, age, genres_str, actors, year_from, year_to, suggestions,
                           age, genres_str, actors, year_from, year_to, suggestions))
    conn.commit()
    cursor.close()
    conn.close()

def get_survey(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, age, favorite_genres, favorite_actors, year_from, year_to, suggestions FROM user_surveys WHERE username = %s", (username,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return data

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(100) PRIMARY KEY,
            password VARCHAR(255) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_surveys (
            username VARCHAR(100) PRIMARY KEY,
            age INT,
            favorite_genres TEXT,
            favorite_actors TEXT,
            year_from INT,
            year_to INT,
            suggestions TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    # Migration: drop old time_period column if it exists
    try:
        cursor.execute("ALTER TABLE user_surveys DROP COLUMN time_period")
    except mysql.connector.Error:
        pass
    # Migration: add new columns if they don't exist
    try:
        cursor.execute("ALTER TABLE user_surveys ADD COLUMN year_from INT")
    except mysql.connector.Error:
        pass
    try:
        cursor.execute("ALTER TABLE user_surveys ADD COLUMN year_to INT")
    except mysql.connector.Error:
        pass
    conn.commit()
    cursor.close()
    conn.close()