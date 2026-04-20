import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    ) 

# import os
# import pymysql
# from dotenv import load_dotenv

# load_dotenv()


# def get_connection(tenant: str = "default"):
#     DB_MAP = {
#         "client_a": {
#             "host": "localhost",
#             "user": "root",
#             "password": "",
#             "database": "db_a"
#         },
#         "client_b": {
#             "host": "localhost",
#             "user": "root",
#             "password": "",
#             "database": "db_b"
#         },
#         "default": {
#             "host": os.getenv("DB_HOST"),
#             "user": os.getenv("DB_USER"),
#             "password": os.getenv("DB_PASSWORD"),
#             "database": os.getenv("DB_NAME")
#         }
#     }

#     config = DB_MAP.get(tenant)

#     if not config:
#         raise Exception(f"Invalid tenant: {tenant}")

#     print("🔌 Connecting to DB for:", tenant)

#     return pymysql.connect(
#         host=config["host"],
#         port=int(os.getenv("DB_PORT", 3306)),
#         user=config["user"],
#         password=config["password"],
#         database=config["database"],
#         cursorclass=pymysql.cursors.DictCursor,
#         autocommit=True
#     )