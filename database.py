import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = "bookings.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # لتمكين الوصول بالاسم مثل dict
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                service TEXT NOT NULL,
                day TEXT NOT NULL,
                time TEXT NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'قيد الانتظار',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                appointment_datetime TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                booking_id INTEGER,
                stars INTEGER NOT NULL CHECK (stars >= 1 AND stars <= 5),
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(booking_id) REFERENCES bookings(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # SQLite لا يدعم CREATE INDEX IF NOT EXISTS في الإصدارات القديمة
        try:
            cursor.execute("CREATE INDEX idx_bookings_user_id ON bookings(user_id)")
        except sqlite3.OperationalError:
            pass  # الفهرس موجود مسبقًا
        
        try:
            cursor.execute("CREATE INDEX idx_bookings_status ON bookings(status)")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("CREATE INDEX idx_bookings_datetime ON bookings(appointment_datetime)")
        except sqlite3.OperationalError:
            pass

# === الدوال الأخرى (متوافقة مع SQLite) ===
def create_booking(user_id, name, phone, service, day, time, date, booking_type, appointment_datetime=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO bookings 
            (user_id, name, phone, service, day, time, date, type, appointment_datetime, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'قيد الانتظار', datetime('now'))
        """, (user_id, name, phone, service, day, time, date, booking_type, appointment_datetime))
        return cursor.lastrowid

def get_booking(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_bookings():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def update_booking_status(user_id, status):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bookings 
            SET status = ?, updated_at = datetime('now')
            WHERE user_id = ?
        """, (status, user_id))

def delete_booking(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))

def check_time_slot_available(day, time, exclude_user_id=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if exclude_user_id:
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE day = ? AND time = ? AND status NOT IN ('لم يحضر', 'ملغي', 'تم التصوير')
                AND user_id != ?
            """, (day, time, exclude_user_id))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE day = ? AND time = ? AND status NOT IN ('لم يحضر', 'ملغي', 'تم التصوير')
            """, (day, time))
        return cursor.fetchone()[0] == 0

def get_booked_time_slots(day):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT time FROM bookings 
            WHERE day = ? AND status NOT IN ('لم يحضر', 'ملغي', 'تم التصوير')
        """, (day,))
        return [row[0] for row in cursor.fetchall()]

def save_rating(user_id, stars, feedback=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        booking = get_booking(user_id)
        booking_id = booking['id'] if booking else None
        cursor.execute("""
            INSERT INTO ratings (user_id, booking_id, stars, feedback)
            VALUES (?, ?, ?, ?)
        """, (user_id, booking_id, stars, feedback))
        return cursor.lastrowid

def get_ratings():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, b.name, b.phone 
            FROM ratings r
            LEFT JOIN bookings b ON r.booking_id = b.id
            ORDER BY r.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_statistics():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_bookings,
                COUNT(CASE WHEN status = 'قيد الانتظار' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'مؤكد' THEN 1 END) as confirmed,
                COUNT(CASE WHEN status = 'تم التصوير' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'لم يحضر' THEN 1 END) as no_show
            FROM bookings
        """)
        stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT service, COUNT(*) as count 
            FROM bookings 
            GROUP BY service 
            ORDER BY count DESC
        """)
        services = cursor.fetchall()
        
        cursor.execute("SELECT AVG(stars) as avg_rating, COUNT(*) as total_ratings FROM ratings")
        rating_stats = cursor.fetchone()
        
        return {
            'bookings': dict(stats),
            'services': [dict(s) for s in services],
            'ratings': dict(rating_stats) if rating_stats else {'avg_rating': 0, 'total_ratings': 0}
        }

def get_pending_bookings():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM bookings 
            WHERE status = 'قيد الانتظار'
            ORDER BY created_at ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_confirmed_bookings_for_reminders():
    # SQLite لا يدعم INTERVAL، لذا نحسب الوقت في بايثون
    from datetime import timedelta
    now = datetime.now()
    one_hour_later = now + timedelta(hours=1)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    one_hour_later_str = one_hour_later.strftime("%Y-%m-%d %H:%M:%S")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM bookings 
            WHERE status = 'مؤكد' 
            AND appointment_datetime IS NOT NULL
            AND appointment_datetime > ?
            AND appointment_datetime <= ?
            ORDER BY appointment_datetime ASC
        """, (now_str, one_hour_later_str))
        return [dict(row) for row in cursor.fetchall()]

# --- إضافة دالة لحساب الأيام المستقبلية المتاحة ---
def get_available_days_for_booking():
    """
    Returns a list of day names starting from today, considering the current time.
    This helps in generating the list of days for the user to choose from.
    """
    now = datetime.now()
    current_weekday = now.weekday() # Monday is 0, Sunday is 6
    current_time_str = now.strftime("%H:%M") # Current time in HH:MM format

    # Map weekday numbers to Arabic names
    weekday_names = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

    # Generate the list of next 7 days starting from today
    available_days = []
    for i in range(7): # Next 7 days including today
        day_offset = timedelta(days=i)
        future_date = now + day_offset
        future_weekday_num = future_date.weekday()
        future_day_name = weekday_names[future_weekday_num]
        future_date_str = future_date.strftime("%d/%m/%Y")

        # Check if it's today, then filter based on time slots
        if i == 0: # Today
            # Get booked slots for today
            booked_slots_today = set(get_booked_time_slots(future_day_name))
            # Define all possible time slots
            all_time_slots = [
                "9:00 صباحاً", "10:00 صباحاً", "11:00 صباحاً",
                "12:00 ظهراً", "1:00 مساءً", "2:00 مساءً",
                "3:00 مساءً", "4:00 مساءً", "5:00 مساءً",
                "6:00 مساءً", "7:00 مساءً", "8:00 مساءً"
            ]

            # Find the first available slot today after current time
            first_available_slot_today = None
            for slot in all_time_slots:
                # Convert slot time to comparable format (HH:MM)
                slot_hour_min = slot.split(" ")[0] # e.g., "9:00"
                # Determine if AM or PM for comparison if needed, but for this logic, we assume PM starts at 12:00 PM and onwards until 8:00 PM
                # For simplicity in this check, we just compare the HH:MM string if AM/PM is consistent or convert properly.
                # A more robust way is to create datetime objects for the slot times of 'today'
                slot_time_obj = datetime.strptime(f"{future_date_str} {slot_hour_min}", "%d/%m/%Y %H:%M")
                if slot_time_obj.time() > now.time() and slot not in booked_slots_today:
                     first_available_slot_today = slot
                     break

            # If there's an available slot today, include the day
            if first_available_slot_today:
                available_days.append(future_day_name)
        else: # Not today, just add the day name
            available_days.append(future_day_name)

    return available_days

# --- إضافة دالة لحساب الأوقات المتاحة لليوم المحدد، مع مراعاة الوقت الحالي ---
def get_available_time_slots_for_day(day_name, exclude_user_id=None):
    """
    Returns a list of available time slots for a given day name.
    Filters out booked slots and, if the day is today, filters out slots before the current time.
    """
    now = datetime.now()
    current_weekday = now.weekday()
    weekday_names = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    today_name = weekday_names[current_weekday]
    current_time_str = now.strftime("%H:%M")

    all_time_slots = [
        "9:00 صباحاً", "10:00 صباحاً", "11:00 صباحاً",
        "12:00 ظهراً", "1:00 مساءً", "2:00 مساءً",
        "3:00 مساءً", "4:00 مساءً", "5:00 مساءً",
        "6:00 مساءً", "7:00 مساءً", "8:00 مساءً"
    ]

    booked_slots = set(get_booked_time_slots(day_name))

    available_slots = []
    for slot in all_time_slots:
        slot_hour_min = slot.split(" ")[0] # e.g., "9:00"
        slot_time_obj = datetime.strptime(f"{now.strftime('%d/%m/%Y')} {slot_hour_min}", "%d/%m/%Y %H:%M")

        is_available = check_time_slot_available(day_name, slot, exclude_user_id)
        is_after_current_time = True # Assume true for future days

        if day_name == today_name: # If it's today, check time
            is_after_current_time = slot_time_obj.time() > now.time()

        if is_available and is_after_current_time:
            available_slots.append(slot)

    return available_slots
