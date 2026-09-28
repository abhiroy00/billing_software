from decimal import Decimal

from services import gst_service


def test_determine_tax_type_same_state_is_intra():
    assert gst_service.determine_tax_type("Karnataka", "Karnataka") == "intra"
    assert gst_service.determine_tax_type("karnataka", "KARNATAKA") == "intra"


def test_determine_tax_type_different_state_is_inter():
    assert gst_service.determine_tax_type("Karnataka", "Maharashtra") == "inter"


def test_section_40_example_calculation():
    """Course = 10,000; Discount = 1,000; GST 18% -> CGST 810, SGST 810,
    Grand Total 10,620 (exact spec example)."""
    calc = gst_service.calculate_line_item(
        rate=Decimal("10000"), quantity=Decimal("1"), discount=Decimal("1000"),
        tax_percentage=Decimal("18"), tax_type="intra",
    )
    assert calc.taxable_amount == Decimal("9000.00")
    assert calc.cgst_amount == Decimal("810.00")
    assert calc.sgst_amount == Decimal("810.00")
    assert calc.igst_amount == Decimal("0.00")
    assert calc.total_amount == Decimal("10620.00")

    totals = gst_service.calculate_invoice_totals(
        [{"rate": "10000", "quantity": "1", "discount": "1000", **calc.__dict__}]
    )
    assert totals.subtotal == Decimal("10000.00")
    assert totals.discount_total == Decimal("1000.00")
    assert totals.cgst_total == Decimal("810.00")
    assert totals.sgst_total == Decimal("810.00")
    assert totals.round_off == Decimal("0.00")
    assert totals.grand_total == Decimal("10620.00")


def test_inter_state_uses_igst_only():
    calc = gst_service.calculate_line_item(
        rate=Decimal("1000"), quantity=Decimal("1"), discount=Decimal("0"),
        tax_percentage=Decimal("18"), tax_type="inter",
    )
    assert calc.cgst_amount == Decimal("0.00")
    assert calc.sgst_amount == Decimal("0.00")
    assert calc.igst_amount == Decimal("180.00")
    assert calc.total_amount == Decimal("1180.00")


def test_quantity_multiplies_rate():
    calc = gst_service.calculate_line_item(
        rate=Decimal("500"), quantity=Decimal("3"), discount=Decimal("0"),
        tax_percentage=Decimal("0"), tax_type="intra",
    )
    assert calc.taxable_amount == Decimal("1500.00")
    assert calc.total_amount == Decimal("1500.00")


def test_discount_exceeding_amount_raises():
    import pytest

    with pytest.raises(ValueError):
        gst_service.calculate_line_item(
            rate=Decimal("100"), quantity=Decimal("1"), discount=Decimal("200"),
            tax_percentage=Decimal("18"), tax_type="intra",
        )


def test_round_off_applied_to_nearest_rupee():
    calc = gst_service.calculate_line_item(
        rate=Decimal("100"), quantity=Decimal("1"), discount=Decimal("0"),
        tax_percentage=Decimal("12.5"), tax_type="intra",
    )
    # taxable=100, cgst=6.25, sgst=6.25 -> total 112.50
    totals = gst_service.calculate_invoice_totals(
        [{"rate": "100", "quantity": "1", "discount": "0", **calc.__dict__}]
    )
    pre_round = totals.subtotal - totals.discount_total + totals.cgst_total + totals.sgst_total + totals.igst_total
    assert pre_round == Decimal("112.50")
    assert totals.grand_total == Decimal("113")
    assert totals.round_off == Decimal("0.50")


def test_zero_gst_rate():
    calc = gst_service.calculate_line_item(
        rate=Decimal("500"), quantity=Decimal("1"), discount=Decimal("0"),
        tax_percentage=Decimal("0"), tax_type="intra",
    )
    assert calc.cgst_amount == Decimal("0.00")
    assert calc.sgst_amount == Decimal("0.00")
    assert calc.total_amount == Decimal("500.00")
