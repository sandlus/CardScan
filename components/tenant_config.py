
import json
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class TenantDBConfig(BaseModel):
    host: str
    port: int = 3306
    user: str
    password: str
    database: str

class TenantConfig(BaseModel):
    slug: str
    allowed_hosts: List[str] = Field(default_factory=list)
    frontend_paths: List[str] = Field(default_factory=list)

    client_domain: Optional[str] = None
    branding_api: Optional[str] = None

    requires_login: bool = False

    db: TenantDBConfig


def load_tenants() -> Dict[str, TenantConfig]:
    raw_json = os.getenv("TENANT_CONFIG_JSON", "").strip()

    if not raw_json:
        raise RuntimeError("TENANT_CONFIG_JSON is missing in environment")

    try:
        raw_data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid TENANT_CONFIG_JSON: {exc}")

    tenants: Dict[str, TenantConfig] = {}
    for slug, config in raw_data.items():
        tenants[slug.lower()] = TenantConfig(**config)

    return tenants


TENANTS = load_tenants()
