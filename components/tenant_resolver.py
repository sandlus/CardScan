from urllib.parse import urlparse

from fastapi import Header, HTTPException, Query, Request

from components.tenant_config import TENANTS, TenantConfig


def _clean_host(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(":")[0].strip().lower()


def resolve_tenant_slug_from_request(
    request: Request,
    tenant_slug: str | None = Query(default=None),
    x_tenant_id: str | None = Header(default=None)
) -> str:
    # 1. explicit query param
    if tenant_slug:
        slug = tenant_slug.strip().lower()
        if slug in TENANTS:
            return slug

    # 2. explicit header
    if x_tenant_id:
        slug = x_tenant_id.strip().lower()
        if slug in TENANTS:
            return slug

    # 3. from path like /client/futuretech
    parts = [p for p in request.url.path.split("/") if p]
    if len(parts) >= 2 and parts[0].lower() == "client":
        slug = parts[1].lower()
        if slug in TENANTS:
            return slug

    # 4. from host / origin / referer
    candidates = []

    host = _clean_host(request.headers.get("host"))
    origin = (
        _clean_host(urlparse(request.headers.get("origin", "")).netloc)
        if request.headers.get("origin")
        else None
    )
    referer = (
        _clean_host(urlparse(request.headers.get("referer", "")).netloc)
        if request.headers.get("referer")
        else None
    )

    if host:
        candidates.append(host)
    if origin:
        candidates.append(origin)
    if referer:
        candidates.append(referer)

    for slug, tenant in TENANTS.items():
        allowed = [h.lower() for h in tenant.allowed_hosts]
        for candidate in candidates:
            if candidate in allowed:
                return slug

    raise HTTPException(
        status_code=400,
        detail="Unable to resolve tenant. Pass tenant_slug in query or x-tenant-id header."
    )


def get_tenant_by_slug(slug: str) -> TenantConfig:
    tenant = TENANTS.get(slug.lower())
    if not tenant:
        raise HTTPException(status_code=400, detail=f"Invalid tenant: {slug}")
    return tenant