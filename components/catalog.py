

# from fastapi import APIRouter, Query
# from components.db import get_connection

# router = APIRouter()


# @router.get("/Select_category")
# def get_categories():
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         query = """
#             SELECT MIN(cat_id) AS cat_id, cat_name
#             FROM category
#             WHERE cat_name IS NOT NULL
#               AND cat_name <> ''
#             GROUP BY cat_name
#             ORDER BY cat_name ASC
#         """
#         cursor.execute(query)
#         result = cursor.fetchall()

#         return {
#             "status": True,
#             "data": result
#         }

#     except Exception as e:
#         return {
#             "status": False,
#             "error": str(e)
#         }

#     finally:
#         cursor.close()
#         conn.close()


# @router.get("/Product_code")
# def get_products(cat_id: int = Query(...)):
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         query = """
#             SELECT DISTINCT product_name, item_code
#             FROM items
#             WHERE cat_id = %s
#               AND product_name IS NOT NULL
#               AND product_name <> ''
#             ORDER BY product_name ASC
#         """
#         cursor.execute(query, (cat_id,))
#         result = cursor.fetchall()

#         return {
#             "status": True,
#             "data": result
#         }

#     except Exception as e:
#         return {
#             "status": False,
#             "error": str(e)
#         }

#     finally:
#         cursor.close()
#         conn.close() 

from fastapi import APIRouter, Query
from components.db import get_connection

router = APIRouter()


@router.get("/Select_category")
def get_categories():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT MIN(cat_id) AS cat_id, cat_name
            FROM category
            WHERE cat_name IS NOT NULL
              AND cat_name <> ''
            GROUP BY cat_name
            ORDER BY cat_name ASC
        """
        cursor.execute(query)
        result = cursor.fetchall()

        return {
            "status": True,
            "data": result
        }

    except Exception as e:
        return {
            "status": False,
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/Product_code")
def get_products(cat_id: int = Query(...)):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT DISTINCT product_name, item_code
            FROM items
            WHERE cat_id = %s
              AND product_name IS NOT NULL
              AND product_name <> ''
            ORDER BY product_name ASC
        """
        cursor.execute(query, (cat_id,))
        result = cursor.fetchall()

        return {
            "status": True,
            "data": result
        }

    except Exception as e:
        return {
            "status": False,
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()