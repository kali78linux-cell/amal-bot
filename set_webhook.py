import requests
import json

# بيانات البوت
BOT_TOKEN = "8365769642:AAFX7oRMPw3GwP0_ZXr95_luJJlLdc8vVKs"
WEBHOOK_URL = "https://kandy-excessive-mizzly.ngrok-free.dev"

def set_webhook():
    """تعيين Webhook للبوت"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    
    payload = {
        "url": WEBHOOK_URL,
        "max_connections": 100,
        "allowed_updates": ["message", "callback_query"]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        print("=" * 50)
        print("نتيجة تعيين Webhook:")
        print("=" * 50)
        print(f"الرابط: {WEBHOOK_URL}")
        print(f"الحالة: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"النتيجة: {result.get('description', 'Unknown')}")
            print(f"نجاح: {result.get('ok', False)}")
            
            if result.get('ok'):
                print("✅ تم تعيين Webhook بنجاح!")
            else:
                print("❌ فشل في تعيين Webhook")
        else:
            print(f"❌ خطأ في الاتصال: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ خطأ في الاتصال بالإنترنت: {e}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")

def get_webhook_info():
    """الحصول على معلومات Webhook الحالية"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        
        print("\n" + "=" * 50)
        print("معلومات Webhook الحالية:")
        print("=" * 50)
        
        if response.status_code == 200:
            info = response.json()
            if info.get('ok'):
                webhook_info = info.get('result', {})
                print(f"الرابط: {webhook_info.get('url', 'None')}")
                print(f"مضيف: {webhook_info.get('ip_address', 'Unknown')}")
                print(f"لديه شهادة SSL: {webhook_info.get('has_custom_certificate', False)}")
                print(f"عدد التحديثات المنتظرة: {webhook_info.get('pending_update_count', 0)}")
                print(f"آخر خطأ: {webhook_info.get('last_error_message', 'None')}")
                print(f"آخر وقت خطأ: {webhook_info.get('last_error_date', 'Never')}")
            else:
                print("❌ فشل في الحصول على المعلومات")
        else:
            print(f"❌ خطأ في الاتصال: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ خطأ في الاتصال بالإنترنت: {e}")

if __name__ == "__main__":
    print("جاري تعيين Webhook للبوت...")
    set_webhook()
    get_webhook_info()
