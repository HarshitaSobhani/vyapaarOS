from app.services.inventory import StockStatus, assess_stock


def test_critical_with_recommended_order():
    a = assess_stock(37, 0, 186, reorder_level=50, reorder_quantity=100)   # 6.2/day
    assert a.average_daily_sales == 6.2
    assert a.stock_coverage_days == 6.0
    assert a.status is StockStatus.critical
    assert a.recommended_order_quantity == 200      # 30d target (186) - 37 = 149 -> packs of 100


def test_healthy_needs_no_order():
    a = assess_stock(500, 0, 60, 50, 100)
    assert a.status is StockStatus.healthy and a.recommended_order_quantity == 0


def test_low_by_coverage_and_reorder_level():
    assert assess_stock(100, 0, 240, 10, 50).status is StockStatus.low           # 12.5 days cover
    assert assess_stock(40, 0, 3, 50, 50).status is StockStatus.low              # below reorder level


def test_reserved_stock_reduces_availability():
    a = assess_stock(100, 90, 300, 5, 20)
    assert a.available_quantity == 10 and a.status is StockStatus.critical


def test_no_sales_history_has_undefined_coverage():
    a = assess_stock(80, 0, 0, 20, 50)
    assert a.stock_coverage_days is None and a.status is StockStatus.healthy


def test_stocked_out():
    assert assess_stock(0, 0, 0, 10, 20).status is StockStatus.critical
