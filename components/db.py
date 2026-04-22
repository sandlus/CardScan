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

