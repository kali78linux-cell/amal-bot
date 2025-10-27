import requests

BOT_TOKEN = "8365769642:AAFX7oRMPw3GwP0_ZXr95_luJJlLdc8vVKs"
RENDER_URL = "https://amal-bot.onrender.com"

def main():
    # 1. حذف Webhook القديم
    print("🗑️ جاري حذف Webhook القديم...")
    delete_response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    )
    print(f"حذف Webhook: {delete_response.status_code} - {delete_response.json()}")
    
    # 2. تعيين Webhook جديد لـ Render
    print("🔄 جاري تعيين Webhook لـ Render...")
    set_response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": f"{RENDER_URL}/{BOT_TOKEN}"}
    )
    
    print("=" * 50)
    print("نتيجة تعيين Webhook:")
    print("=" * 50)
    print(f"الرابط: {RENDER_URL}")
    print(f"الحالة: {set_response.status_code}")
    
    if set_response.status_code == 200:
        result = set_response.json()
        print(f"النتيجة: {result.get('description', 'Unknown')}")
        print(f"نجاح: {result.get('ok', False)}")
        
        if result.get('ok'):
            print("✅ تم تعيين Webhook لـ Render بنجاح!")
        else:
            print("❌ فشل في تعيين Webhook")
    else:
        print(f"❌ خطأ في الاتصال: {set_response.text}")
    
    # 3. التحقق من معلومات Webhook
    print("\n" + "=" * 50)
    print("معلومات Webhook الحالية:")
    print("=" * 50)
    
    info_response = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    )
    
    if info_response.status_code == 200:
        info = info_response.json()
        if info.get('ok'):
            webhook_info = info.get('result', {})
            print(f"الرابط: {webhook_info.get('url', 'None')}")
            print(f"مضيف: {webhook_info.get('ip_address', 'Unknown')}")
            print(f"لديه شهادة SSL: {webhook_info.get('has_custom_certificate', False)}")
            print(f"عدد التحديثات المنتظرة: {webhook_info.get('pending_update_count', 0)}")
            print(f"آخر خطأ: {webhook_info.get('last_error_message', 'None')}")
            
            if webhook_info.get('url') == f"{RENDER_URL}/{BOT_TOKEN}":
                print("🎯 Webhook مضبوط بشكل صحيح على Render!")
            else:
                print("⚠️ Webhook ليس مضبوطاً على Render!")

if __name__ == "__main__":
    main()