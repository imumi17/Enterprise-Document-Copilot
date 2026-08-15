from app.chat.messages import is_trading_advice_request


def test_is_trading_advice_request_detects_buy_sell():
    assert is_trading_advice_request("Should we buy or sell NVIDIA?")
    assert not is_trading_advice_request("What did NVIDIA disclose about data center revenue?")
