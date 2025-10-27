import requests

BOT_TOKEN = "8365769642:AAFX7oRMPw3GwP0_ZXr95_luJJlLdc8vVKs"
WEBHOOK_URL = "https://amal-bot.onrender.com"

response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
    json={"url": f"{WEBHOOK_URL}/{BOT_TOKEN}"}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")