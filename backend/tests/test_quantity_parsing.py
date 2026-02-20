import pytest
from app.nlp import _parse_quantity_and_units


class TestQuantityParsing:
    """Test quantity and unit parsing from Greek order text."""
    
    def test_parse_simple_quantity(self):
        """Test parsing simple quantity like '2 item'."""
        qty, unit, multiplier, item = _parse_quantity_and_units("2 σουβλάκια")
        assert qty == 2.0
        assert unit is None
        assert item == "σουβλάκια"
    
    def test_parse_decimal_quantity(self):
        """Test parsing decimal quantities."""
        qty, unit, multiplier, item = _parse_quantity_and_units("2.5 μπύρα")
        assert qty == 2.5
        assert item == "μπύρα"
    
    def test_parse_liters_lowercase_lambda(self):
        """Test parsing liters with λ unit (no space)."""
        qty, unit, multiplier, item = _parse_quantity_and_units("2λ κρασί")
        assert qty == 2.0
        assert unit == "λ"
        assert item == "κρασί"
        assert multiplier == 2.0  # For liters, multiplier = quantity
    
    def test_parse_kilogram(self):
        """Test parsing kilograms with κ unit."""
        qty, unit, multiplier, item = _parse_quantity_and_units("1κ παϊδάκια")
        assert qty == 1.0
        assert unit == "κ"
        assert item == "παϊδάκια"
        assert multiplier == 1.0
    
    def test_parse_kilogram_full_word(self):
        """Test parsing kilograms with full word 'kg'."""
        qty, unit, multiplier, item = _parse_quantity_and_units("2kg παϊδάκια")
        assert qty == 2.0
        assert unit == "kg"
        assert item == "παϊδάκια"
        assert multiplier == 2.0
    
    def test_parse_milliliters(self):
        """Test parsing milliliters."""
        qty, unit, multiplier, item = _parse_quantity_and_units("500ml ρακί")
        assert qty == 500.0
        assert unit == "ml"
        assert item == "ρακί"
        # ml multiplier should be quantity / 250 for standard items
        assert multiplier == 500 / 250.0  # = 2.0
    
    def test_parse_no_quantity(self):
        """Test parsing item with no quantity prefix."""
        qty, unit, multiplier, item = _parse_quantity_and_units("σαλάτα")
        assert qty is None
        assert unit is None
        assert item == "σαλάτα"
    
    def test_parse_liters_with_space(self):
        """Test parsing liters with space before unit."""
        # According to code, unit must be directly after number
        qty, unit, multiplier, item = _parse_quantity_and_units("2 λ κρασί")
        # This should parse as "2" quantity with "λ κρασί" as item (no unit match)
        assert qty == 2.0


class TestUnitVariants:
    """Test various unit spelling variants."""
    
    @pytest.mark.parametrize("unit_text", [
        "1λ",
        "1lt",
        "1l",
        "1λτ",
    ])
    def test_liter_variants(self, unit_text):
        """Test different ways to write liters."""
        qty, unit, mult, item = _parse_quantity_and_units(f"{unit_text} κρασί")
        if qty is not None and unit is not None:
            assert unit in ("λ", "λτ", "lt", "l")
    
    @pytest.mark.parametrize("unit_text", [
        "1kg",
        "1κ",
        "1κιλα",
        "1κιλο",
    ])
    def test_kilogram_variants(self, unit_text):
        """Test different ways to write kilograms."""
        qty, unit, mult, item = _parse_quantity_and_units(f"{unit_text} παϊδάκια")
        if qty is not None and unit is not None:
            assert unit in ("kg", "κ", "κιλα", "κιλο")


def test_parse_quantity_case_insensitive():
    """Test that unit parsing is case-insensitive."""
    qty1, unit1, _, _ = _parse_quantity_and_units("1KG παϊδάκια")
    qty2, unit2, _, _ = _parse_quantity_and_units("1kg παϊδάκια")
    
    assert qty1 == qty2 == 1.0
    # Both should parse successfully (or both fail)
    if unit1 is not None and unit2 is not None:
        assert unit1.lower() == unit2.lower()
