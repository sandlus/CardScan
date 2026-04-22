# # import pymysql
# # from fastapi import APIRouter, Depends, HTTPException, Query, Request

# # from components.db import get_connection
# # from components.tenant_resolver import get_tenant_by_slug, resolve_tenant_slug_from_request

# # router = APIRouter()


# # @router.get("/Select_category")
# # def get_categories(
# #     request: Request,
# #     tenant_slug: str = Depends(resolve_tenant_slug_from_request)
# # ):
# #     conn = None
# #     cursor = None

# #     try:
# #         tenant = get_tenant_by_slug(tenant_slug)
# #         conn = get_connection(tenant.db)
# #         cursor = conn.cursor(pymysql.cursors.DictCursor)

# #         query = """
# #             SELECT cat_id, cat_name
# #             FROM category
# #             WHERE cat_name IS NOT NULL
# #               AND TRIM(cat_name) <> ''
# #             ORDER BY cat_name ASC
# #         """

# #         cursor.execute(query)
# #         result = cursor.fetchall()

# #         return {
# #             "status": True,
# #             "tenant": tenant.slug,
# #             "data": result
# #         }

# #     except Exception as e:
# #         print("CATEGORY ERROR:", e)
# #         raise HTTPException(status_code=500, detail=str(e))

# #     finally:
# #         if cursor:
# #             cursor.close()
# #         if conn:
# #             conn.close()


# # @router.get("/Product_code")
# # def get_products(
# #     request: Request,
# #     cat_id: int = Query(...),
# #     tenant_slug: str = Depends(resolve_tenant_slug_from_request)
# # ):
# #     conn = None
# #     cursor = None

# #     try:
# #         tenant = get_tenant_by_slug(tenant_slug)
# #         conn = get_connection(tenant.db)
# #         cursor = conn.cursor(pymysql.cursors.DictCursor)

# #         query = """
# #             SELECT item_id, product_name
# #             FROM item
# #             WHERE cat_id = %s
# #               AND product_name IS NOT NULL
# #               AND TRIM(product_name) <> ''
# #             ORDER BY product_name ASC
# #         """

# #         cursor.execute(query, (cat_id,))
# #         result = cursor.fetchall()

# #         return {
# #             "status": True,
# #             "tenant": tenant.slug,
# #             "data": result
# #         }

# #     except Exception as e:
# #         print("PRODUCT ERROR:", e)
# #         raise HTTPException(status_code=500, detail=str(e))

# #     finally:
# #         if cursor:
# #             cursor.close()
# #         if conn:
# #             conn.close() 

# import pymysql
# from fastapi import APIRouter, Depends, HTTPException, Query, Request

# from components.db import get_connection
# from components.tenant_resolver import get_tenant_by_slug, resolve_tenant_slug_from_request

# router = APIRouter()


# @router.get("/Select_category")
# def get_categories(
#     request: Request,
#     tenant_slug: str = Depends(resolve_tenant_slug_from_request)
# ):
#     conn = None
#     cursor = None

#     try:
#         tenant = get_tenant_by_slug(tenant_slug)
#         conn = get_connection(tenant.db)
#         cursor = conn.cursor(pymysql.cursors.DictCursor)

#         query = """
#             SELECT cat_id, cat_name
#             FROM category
#             WHERE cat_name IS NOT NULL
#               AND TRIM(cat_name) <> ''
#             ORDER BY cat_name ASC
#         """

#         cursor.execute(query)
#         result = cursor.fetchall()

#         return {
#             "status": True,
#             "tenant": tenant.slug,
#             "data": result
#         }

#     except Exception as e:
#         print("CATEGORY ERROR:", e)
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# @router.get("/Product_code")
# def get_products(
#     request: Request,
#     cat_id: int = Query(...),
#     tenant_slug: str = Depends(resolve_tenant_slug_from_request)
# ):
#     conn = None
#     cursor = None

#     try:
#         tenant = get_tenant_by_slug(tenant_slug)
#         conn = get_connection(tenant.db)
#         cursor = conn.cursor(pymysql.cursors.DictCursor)

#         query = """
#             SELECT item_id, cat_id, product_name
#             FROM item
#             WHERE cat_id = %s
#               AND product_name IS NOT NULL
#               AND TRIM(product_name) <> ''
#             ORDER BY product_name ASC
#         """

#         cursor.execute(query, (cat_id,))
#         result = cursor.fetchall()

#         return {
#             "status": True,
#             "tenant": tenant.slug,
#             "data": result
#         }

#     except Exception as e:
#         print("PRODUCT ERROR:", e)
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()  

import pymysql
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from components.db import get_connection
from components.tenant_resolver import get_tenant_by_slug, resolve_tenant_slug_from_request

router = APIRouter()


@router.get("/Select_category")
def get_categories(
    request: Request,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT cat_id, cat_name
            FROM category
            WHERE cat_name IS NOT NULL
              AND TRIM(cat_name) <> ''
            ORDER BY cat_name ASC
        """

        cursor.execute(query)
        result = cursor.fetchall()

        return {
            "status": True,
            "tenant": tenant.slug,
            "data": result,
        }

    except Exception as e:
        print("CATEGORY ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/Product_code")
def get_products(
    request: Request,
    cat_id: int = Query(...),
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT item_id, cat_id, product_name
            FROM item
            WHERE cat_id = %s
              AND product_name IS NOT NULL
              AND TRIM(product_name) <> ''
            ORDER BY product_name ASC
        """

        cursor.execute(query, (cat_id,))
        result = cursor.fetchall()

        return {
            "status": True,
            "tenant": tenant.slug,
            "data": result,
        }

    except Exception as e:
        print("PRODUCT ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()