from fastapi import APIRouter, Query
from components.db import get_connection

router = APIRouter()

# ==============================
# 1. GET UNIQUE CATEGORIES
# ==============================
@router.get("/Select_category")
def get_categories():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT DISTINCT cat_id, cat_name
            FROM category
            ORDER BY cat_name ASC
        """
        cursor.execute(query)
        result = cursor.fetchall()

        return {
            "status": True,
            "data": result
        }

    except Exception as e:
        return {"status": False, "error": str(e)}

    finally:
        cursor.close()
        conn.close()


# ==============================
# 2. GET PRODUCTS BY CATEGORY
# ==============================
@router.get("/Product_code")
def get_products(cat_id: int = Query(...)):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT DISTINCT product_name, item_code
            FROM items
            WHERE cat_id = %s
            ORDER BY product_name ASC
        """
        cursor.execute(query, (cat_id,))
        result = cursor.fetchall()

        return {
            "status": True,
            "data": result
        }

    except Exception as e:
        return {"status": False, "error": str(e)}

    finally:
        cursor.close()
        conn.close()