# import os
# import pymysql
# from dotenv import load_dotenv

# load_dotenv()

# def get_connection():
#     return pymysql.connect(
#         host=os.getenv("DB_HOST"),
#         port=int(os.getenv("DB_PORT")),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         database=os.getenv("DB_NAME"),
#         cursorclass=pymysql.cursors.DictCursor
#     ) 

import pymysql

from components.tenant_config import TenantDBConfig


def get_connection(db_config: TenantDBConfig):
    return pymysql.connect(
        host=db_config.host,
        port=int(db_config.port),
        user=db_config.user,
        password=db_config.password,
        database=db_config.database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

