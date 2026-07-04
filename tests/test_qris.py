from utils.qris import qris_with_amount


def test_qris_with_amount_converts_static_qris_to_dynamic_amount_payload():
    static_qris = "0002010102115802ID5904TEST6007JAKARTA6304ABCD"

    result = qris_with_amount(static_qris, 15000)

    assert result.startswith("000201010212")
    assert "5405150005802ID" in result
    assert not result.endswith("ABCD")
    assert result[-8:-4] == "6304"


def test_qris_with_amount_replaces_existing_amount():
    dynamic_qris = "000201010212540410005802ID5904TEST6007JAKARTA6304ABCD"

    result = qris_with_amount(dynamic_qris, 25000)

    assert "540525000" in result
    assert "54041000" not in result


def test_qris_with_amount_leaves_non_qris_payload_unchanged():
    payload = "https://app.pakasir.com/pay/store/15000?order_id=abc"

    assert qris_with_amount(payload, 15000) == payload
