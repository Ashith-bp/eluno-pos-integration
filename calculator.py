from decimal import Decimal, ROUND_HALF_UP

def calculate_gst(gross_price_str: str) -> dict:
    """
    Calculates 18% GST (CGST 9% + SGST 9%) from a tax-inclusive gross price
    using Decimal arithmetic and HALF_UP rounding to the nearest paisa (0.01).
    
    Formula:
    Taxable Value = Gross Price / (1 + Tax Rate) = Gross / 1.18
    Total Tax = Gross Price - Taxable Value
    CGST = SGST = Total Tax / 2 (rounded HALF_UP)
    """
    gross = Decimal(str(gross_price_str))
    
    # Taxable value before 18% GST
    taxable_value = gross / Decimal("1.18")
    
    # Total tax amount
    total_tax = gross - taxable_value
    
    # CGST and SGST equal 9% split
    cgst = (total_tax / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sgst = (total_tax / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Re-quantize totals for response formatting
    taxable_value_rounded = taxable_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_tax_rounded = (cgst + sgst).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    return {
        "gross": f"{gross:.2f}",
        "taxable_value": f"{taxable_value_rounded:.2f}",
        "total_tax": f"{total_tax_rounded:.2f}",
        "cgst": f"{cgst:.2f}",
        "sgst": f"{sgst:.2f}"
    }

if __name__ == "__main__":
    # Self-test
    sample = calculate_gst("104.98")
    print("Calculator Self-Test (₹104.98 @ 18% GST):", sample)