from fastapi import APIRouter, Query
from components.db import get_connection

router = APIRouter()


# =========================
# 1. CATEGORY DROPDOWN
# =========================
@router.get("/Select_category")
def get_categories():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT DISTINCT cat_id, cat_name
            FROM category
            WHERE cat_name IS NOT NULL
              AND TRIM(cat_name) <> ''
            ORDER BY cat_name ASC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        result = [
            {"cat_id": r[0], "cat_name": r[1]}
            for r in rows
        ]

        return {"status": True, "data": result}

    except Exception as e:
        return {"status": False, "error": str(e)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================
# 2. PRODUCT DROPDOWN
# =========================
@router.get("/Product_code")
def get_products(cat_id: int = Query(...)):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT DISTINCT product_name
            FROM item
            WHERE cat_id = %s
              AND product_name IS NOT NULL
              AND TRIM(product_name) <> ''
            ORDER BY product_name ASC
        """

        cursor.execute(query, (cat_id,))
        rows = cursor.fetchall()

        result = [
            {"product_name": r[0]}
            for r in rows
        ]

        return {"status": True, "data": result}

    except Exception as e:
        return {"status": False, "error": str(e)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()