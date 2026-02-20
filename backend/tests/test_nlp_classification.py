import pytest
from app.nlp import classify_order, _normalize_text_basic, _strip_accents, _greek_stem


class TestNLPNormalization:
    """Test text normalization with Greek characters."""
    
    def test_strip_accents_greek(self):
        """Test removing accents from Greek."""
        assert _strip_accents("μύθος") == "μυθος"
        assert _strip_accents("σαλάτα") == "σαλατα"
        assert _strip_accents("Χοιρινή") == "Χοιρινη"
    
    def test_normalize_basic_greek(self):
        """Test basic normalization of Greek text."""
        result = _normalize_text_basic("Μύθος")
        assert "μυθος" in result.lower()
        
        result = _normalize_text_basic("Σαλάτα Χωριάτικη")
        assert "χωριατικ" in result.lower()
    
    def test_normalize_removes_punctuation(self):
        """Test normalization removes punctuation."""
        result = _normalize_text_basic("Μύθος (χωρίς σάλτσα)")
        # Parentheses content should be removed or handled
        assert "(" not in result


class TestGreekStemming:
    """Test Greek stemming logic."""
    
    def test_stem_plural_ia_ending(self):
        """Test stemming -ια plural to -ι."""
        stem_result = _greek_stem("αρνια")
        assert "αρνι" in stem_result
        
        stem_result = _greek_stem("κατσικια")
        assert "κατσικι" in stem_result
        
        stem_result = _greek_stem("παιδακια")
        assert "παιδακι" in stem_result


class TestClassifyOrder:
    """Test order classification into categories."""
    
    def test_classify_kitchen_item(self):
        """Test kitchen item classification."""
        result = classify_order("1 σαλάτα")
        assert len(result) == 1
        assert result[0]["category"] == "kitchen"
        assert result[0]["text"] == "1 σαλάτα"
    
    def test_classify_grill_item(self):
        """Test grill item classification."""
        result = classify_order("1 μπριζόλα")
        assert len(result) == 1
        assert result[0]["category"] == "grill"
    
    def test_classify_drinks_item(self):
        """Test drinks item classification."""
        result = classify_order("1 μπύρα")
        assert len(result) == 1
        assert result[0]["category"] == "drinks"
    
    def test_classify_multi_line_order(self):
        """Test classifying multi-line order."""
        text = "1 σαλάτα\n1 μπριζόλα\n1 μπύρα"
        result = classify_order(text)
        assert len(result) == 3
        assert result[0]["category"] == "kitchen"
        assert result[1]["category"] == "grill"
        assert result[2]["category"] == "drinks"
    
    def test_classify_preserves_original_text(self):
        """Test that original user text is preserved."""
        text = "2 σουβλάκια με πιτα (χωρίς κρεμμυδι)"
        result = classify_order(text)
        assert result[0]["text"] == text


@pytest.mark.parametrize("greek_text,expected_category", [
    ("σουβλάκι", "grill"),
    ("παϊδάκια", "grill"),
    ("μπριζόλα", "grill"),
    ("σαλάτα", "kitchen"),
    ("μπύρα", "drinks"),
    ("κρασί", "drinks"),
    ("ούζο", "drinks"),
])
def test_classify_greek_items(greek_text, expected_category):
    """Test classifying various Greek menu items."""
    result = classify_order(greek_text)
    assert len(result) == 1
    assert result[0]["category"] == expected_category


def test_classify_unknown_item():
    """Test handling unknown Greek items."""
    result = classify_order("1 αγνωστο πιατο με περίεργο όνομα")
    assert len(result) == 1
    # Should still have category (default to kitchen)
    assert result[0]["category"] in ("kitchen", "grill", "drinks")
    # Should not crash
    assert result[0]["text"] is not None
