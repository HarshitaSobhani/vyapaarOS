from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser
from app.repositories.inventory import products_with_stock
from app.schemas.misc import ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(db: DB, _: CurrentUser,
                  q: Annotated[str | None, Query(max_length=100)] = None) -> list[ProductOut]:
    out = []
    for p, inv in products_with_stock(db):
        if q and q.lower() not in p.name.lower() and q.lower() not in p.sku.lower():
            continue
        out.append(ProductOut(
            id=p.id, sku=p.sku, name=p.name, category=p.category, unit=p.unit,
            purchase_price=p.purchase_price, selling_price=p.selling_price, gst_rate=p.gst_rate,
            reorder_level=p.reorder_level, reorder_quantity=p.reorder_quantity,
            supplier_name=p.supplier_name, current_quantity=inv.current_quantity if inv else 0,
            reserved_quantity=inv.reserved_quantity if inv else 0))
    return out
