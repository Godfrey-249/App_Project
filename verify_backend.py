from database import init_db, get_inventory, add_product_stock, record_sale, get_sales_data
from auth import login_user
from utils import send_supplier_email, get_ai_response
import os

def test_backend():
    print("1. Initializing Database...")
    try:
        init_db()
        print("   ✅ DB Initialized")
    except Exception as e:
        print(f"   ❌ DB Init Failed: {e}")
        return

    print("\n2. Testing Auth...")
    user = login_user("owner", "admin")
    if user and user['role'] == 'Owner':
        print("   ✅ Login Owner Successful")
    else:
        print("   ❌ Login Owner Failed")
    
    user = login_user("attendee1", "user1")
    if user and user['role'] == 'Attendee':
        print("   ✅ Login Attendee Successful")
    else:
        print("   ❌ Login Attendee Failed")

    print("\n3. Testing Database Operations...")
    # Add stock
    print("   - Adding stock...")
    try:
        # Get first product ID
        df = get_inventory()
        if df.empty:
            print("   ❌ Inventory Empty")
            return
        
        pid = int(df.iloc[0]['id'])
        initial_qty = int(df.iloc[0]['quantity'])
        
        add_product_stock(pid, 10, "TestBot")
        
        df_new = get_inventory()
        new_qty = int(df_new[df_new['id'] == pid].iloc[0]['quantity'])
        
        if new_qty == initial_qty + 10:
            print("   ✅ add_product_stock working")
        else:
            print(f"   ❌ Stock mismatch: Expected {initial_qty+10}, got {new_qty}")

        # Record Sale
        print("   - Recording sale...")
        success, msg = record_sale(pid, 5, "TestBot")
        if success:
            df_after_sale = get_inventory()
            qty_after_sale = int(df_after_sale[df_after_sale['id'] == pid].iloc[0]['quantity'])
            if qty_after_sale == new_qty - 5:
                print("   ✅ record_sale working")
            else:
                print(f"   ❌ Sale stock deduction failed: {qty_after_sale} != {new_qty - 5}")
        else:
            print(f"   ❌ Record sale failed: {msg}")

    except Exception as e:
        print(f"   ❌ Database Ops Error: {e}")

    print("\n4. Testing Utils...")
    success, msg = send_supplier_email("test@test.com", "TestDrug", 100, "Owner")
    if success:
        print("   ✅ Email mock working")
    else:
        print("   ❌ Email mock failed")

if __name__ == "__main__":
    test_backend()
