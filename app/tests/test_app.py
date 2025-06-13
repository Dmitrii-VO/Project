# test_imports.py
try:
    import flask
    print(f"✅ Flask {flask.__version__}")
except ImportError as e:
    print(f"❌ Flask: {e}")

try:
    import requests
    print(f"✅ Requests {requests.__version__}")
except ImportError as e:
    print(f"❌ Requests: {e}")

try:
    import cryptography
    print(f"✅ Cryptography {cryptography.__version__}")
except ImportError as e:
    print(f"❌ Cryptography: {e}")

try:
    import telegram
    print(f"✅ python-telegram-bot {telegram.__version__}")
except ImportError as e:
    print(f"❌ python-telegram-bot: {e}")

print("Тест завершен!")