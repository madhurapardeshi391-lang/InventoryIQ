import mysql.connector
from config import DB_CONFIG

try:
    connection = mysql.connector.connect(**DB_CONFIG)

    if connection.is_connected():
        print("MySQL connection successful!")
        print("Database:", DB_CONFIG["database"])

    connection.close()

except mysql.connector.Error as error:
    print("MySQL connection failed:")
    print(error)