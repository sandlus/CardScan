import pymysql
from fastapi import APIRouter, Query, HTTPException
from components.db import get_connection

router = APIRouter()


@router.get("/Select_category")
def get_categories():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)  # ✅ FIX

        query = """
            SELECT cat_id, cat_name
            FROM category
            WHERE cat_name IS NOT NULL
              AND TRIM(cat_name) <> ''
            ORDER BY cat_name ASC
        """

        cursor.execute(query)
        result = cursor.fetchall()

        return {"status": True, "data": result}

    except Exception as e:
        print("CATEGORY ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

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
        cursor = conn.cursor(pymysql.cursors.DictCursor)  # ✅ FIX

        query = """
            SELECT DISTINCT product_name, item_code
            FROM item
            WHERE cat_id = %s
              AND product_name IS NOT NULL
              AND TRIM(product_name) <> ''
            ORDER BY product_name ASC
        """

        cursor.execute(query, (cat_id,))
        result = cursor.fetchall()

        return {"status": True, "data": result}

    except Exception as e:
        print("PRODUCT ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()