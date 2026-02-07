import streamlit as st
import pandas as pd
import plotly.express as px
from database import (
    init_db, 
    get_inventory, 
    add_product_stock, 
    record_sale, 
    get_sales_data, 
    get_low_stock_products,
    schedule_delivery,
    get_scheduled_deliveries,
    confirm_delivery,
    get_profit_data,
    get_all_deliveries
)
from auth import login_user, logout_user
from utils import send_supplier_email

# Page Config
st.set_page_config(
    page_title="PharmaLink Pro",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    
    # Custom CSS for Dark Sidebar Text
    st.markdown("""
        <style>
            [data-testid="stSidebar"] p, 
            [data-testid="stSidebar"] span, 
            [data-testid="stSidebar"] label, 
            [data-testid="stSidebar"] div,
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] small {
                color: #FFFFFF !important;
            }
        </style>
    """, unsafe_allow_html=True)

try:
    local_css("css/style.css")
except FileNotFoundError:
    st.warning("Style file not found. Please check css/style.css")

# Initialize DB
init_db()

# Session State for Cart
if "cart" not in st.session_state:
    st.session_state.cart = []

def main():
    # Authentication Check
    if 'user' not in st.session_state:
        show_login()
    else:
        user = st.session_state['user']
        # Sidebar with User Info and Logout
        with st.sidebar:
            st.title("💊 PharmaLink")
            st.write(f"Welcome, **{user['name']}**")
            st.caption(f"Role: {user['role']}")
            st.divider()
            if st.button("Logout", type="secondary"):
                logout_user()
                st.rerun()

        # Routing based on Role
        if user['role'] == "Owner":
            show_owner_dashboard(user)
        elif user['role'] == "Attendee":
            show_attendee_dashboard(user)

def show_login():
    st.markdown("<div style='text-align: center;'><h1>💊 PharmaLink Access</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                user = login_user(username, password)
                if user:
                    st.session_state['user'] = user
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
        
        with st.expander("Demo Credentials"):
            st.write("Owner: `owner` / `admin`")
            st.write("Attendee: `attendee1` / `user1`")

def show_owner_dashboard(user):
    st.title("Owner Dashboard 📊")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Inventory", "Supplier Actions", "Market Search", "Summary"])
    
    # --- Tab 1: Overview & Analytics ---
    with tab1:
        st.header("Business Overview")
        
        # Metrics
        inventory_df = get_inventory()
        sales_data = get_sales_data()
        low_stock = get_low_stock_products()
        
        total_revenue, total_expenses = get_profit_data()
        net_profit = total_revenue - total_expenses
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Revenue", f"${total_revenue:,.2f}")
        m2.metric("Total Expenses", f"${total_expenses:,.2f}")
        m3.metric("Net Profit", f"${net_profit:,.2f}", delta_color="normal")
        m4.metric("Low Stock Items", len(low_stock), delta_color="inverse")
        
        st.divider()
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Sales Trends")
            if not sales_data.empty:
                # Group by date/product for better chart
                # Simple bar chart of sales by product
                fig_sales = px.bar(sales_data, x='name', y='total_price', color='name', title="Revenue by Product")
                st.plotly_chart(fig_sales, use_container_width=True)
            else:
                st.info("No sales data available yet.")
        
        with c2:
            st.subheader("Inventory Distribution")
            if not inventory_df.empty:
                fig_stock = px.pie(inventory_df, values='quantity', names='name', title="Stock Distribution")
                st.plotly_chart(fig_stock, use_container_width=True)
            else:
                st.info("Inventory is empty.")

    # --- Tab 2: Inventory Management ---
    with tab2:
        st.header("Current Inventory")
        st.dataframe(inventory_df, use_container_width=True)
        
        if not low_stock.empty:
            st.error("⚠️ The following items are low in stock:")
            st.table(low_stock[['name', 'brand', 'quantity', 'min_stock_level']])
        else:
            st.success("All stock levels are healthy.")

    # --- Tab 3: Supplier Actions ---
    with tab3:
        st.header("Contact Suppliers 📧")
        
        with st.form("supplier_email_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                supplier_email = st.text_input("Supplier Email")
                # Create a lookup for product IDs
                inv_map = {row['name']: row['id'] for _, row in inventory_df.iterrows()} if not inventory_df.empty else {}
                product_name = st.selectbox("Select Product to Restock", list(inv_map.keys()) if inv_map else [])
            with col_b:
                quantity = st.number_input("Quantity Required", min_value=1, value=50)
                target_price = st.number_input("Target Buy Price (Per Unit)", min_value=0.0, value=5.0, step=0.5, format="%.2f")
            
            submit_email = st.form_submit_button("Send Restock Request")
            
            if submit_email:
                if supplier_email and product_name:
                    success, msg = send_supplier_email(supplier_email, product_name, quantity, user['name'])
                    if success:
                        # Schedule the delivery in specific status
                        product_id = inv_map[product_name]
                        schedule_delivery(product_id, quantity, user['name'], cost_price=target_price)
                        st.success(f"Request sent! scheduled delivery of {quantity} x {product_name} created (Est. Cost: ${target_price * quantity}).")
                    else:
                        st.error(msg)
                else:
                    st.warning("Please fill in all fields.")

        st.divider()
        st.subheader("📦 Supplies History")
        
        # New: Get and display all confirmation/scheduled supplies
        from database import get_all_deliveries # Local import or move to top if preferred. Moving to top is cleaner but this works for snippet.
        
        supplies_df = get_all_deliveries()
        if not supplies_df.empty:
            st.dataframe(supplies_df, use_container_width=True)
        else:
            st.info("No supplies history available.")

    # --- Tab 4: Market Search (Replaces AI) ---
    with tab4:
        st.header("Market Search 🔍")
        st.caption("Search Google for market prices, drug interactions, or inventory tips.")
        
        search_query = st.text_input("Enter search query", placeholder="e.g., Paracetamol wholesale price Kenya")
        
        if st.button("Search Google", type="primary"):
            if search_query:
                url = f"https://www.google.com/search?q={search_query}"
                st.markdown(f"**[Click here to see results for '{search_query}']({url})**", unsafe_allow_html=True)
            else:
                st.warning("Please enter a query.")

    # --- Tab 5: Consolidated Summary & P&L ---
    with tab5:
        st.header("Business Summary & P&L Statement")
        
        # 1. P&L Statement Section
        st.subheader("Profit & Loss Statement")
        total_revenue, total_expenses = get_profit_data()
        gross_profit = total_revenue - total_expenses
        
        # Using a fancy container for P&L
        with st.container(border=True):
            pl_col1, pl_col2 = st.columns(2)
            with pl_col1:
                st.write("**Revenue Items**")
                st.write(f"- Total Sales Revenue: `${total_revenue:,.2f}`")
                st.write("---")
                st.write(f"**Total Revenue: `${total_revenue:,.2f}`**")
            
            with pl_col2:
                st.write("**Expense Items**")
                st.write(f"- Cost of Goods (Deliveries): `${total_expenses:,.2f}`")
                st.write("---")
                st.write(f"**Total Expenses: `${total_expenses:,.2f}`**")
            
            st.divider()
            profit_color = "green" if gross_profit >= 0 else "red"
            st.markdown(f"### Net Profit: <span style='color:{profit_color}'>${gross_profit:,.2f}</span>", unsafe_allow_html=True)

        st.divider()
        
        # 2. Detailed Entries Section
        st.subheader("Historical Transaction Logs")
        
        log_tab1, log_tab2 = st.tabs(["📊 Sales Entries", "📦 Delivery Entries"])
        
        with log_tab1:
            sales_df = get_sales_data()
            if not sales_df.empty:
                st.dataframe(sales_df, use_container_width=True)
            else:
                st.info("No sales entries found.")
                
        with log_tab2:
            deliveries_df = get_all_deliveries()
            if not deliveries_df.empty:
                st.dataframe(deliveries_df, use_container_width=True)
            else:
                st.info("No delivery entries found.")

def show_attendee_dashboard(user):
    st.title("Attendee Dashboard 📋")
    
    st.info(f"Logged in as: {user['name']}")
    
    tab1, tab2 = st.tabs(["📝 Sales Cart", "📦 Confirmed Deliveries"])
    
    inventory_df = get_inventory()
    
    # --- Tab 1: Sales Cart ---
    with tab1:
        st.subheader("Sell Products")
        if inventory_df.empty:
            st.warning("No products in inventory.")
        else:
            c_left, c_right = st.columns([1, 1])
            
            with c_left:
                with st.form("add_to_cart_form"):
                    st.write("##### Add Item")
                    # Create a dictionary for lookup
                    product_map = dict(zip(inventory_df['name'], inventory_df['id']))
                    
                    selected_product_name = st.selectbox("Select Product", inventory_df['name'].unique())
                    quantity = st.number_input("Quantity", min_value=1, value=1)
                    
                    add_submit = st.form_submit_button("Add to Cart 🛒")
                    
                    if add_submit:
                        # find price
                        price = inventory_df.loc[inventory_df['name'] == selected_product_name, 'price'].values[0]
                        
                        item = {
                            "name": selected_product_name,
                            "id": product_map[selected_product_name],
                            "quantity": quantity,
                           "price": price,
                           "total": price * quantity
                        }
                        st.session_state.cart.append(item)
                        st.success(f"Added {selected_product_name}")
            
            with c_right:
                st.write("##### Current Cart 🛒")
                if st.session_state.cart:
                    cart_df = pd.DataFrame(st.session_state.cart)
                    st.dataframe(cart_df[['name', 'quantity', 'price', 'total']], use_container_width=True)
                    
                    total_val = cart_df['total'].sum()
                    st.markdown(f"**Total Transaction Value: ${total_val:,.2f}**")
                    
                    col_conf, col_clear = st.columns(2)
                    
                    if col_conf.button("✅ Complete Transaction", type="primary"):
                        # Process all items
                        errors = []
                        for item in st.session_state.cart:
                            success, msg = record_sale(item['id'], item['quantity'], user['name'])
                            if not success:
                                errors.append(f"{item['name']}: {msg}")
                        
                        if errors:
                            st.error("Some items failed:")
                            for e in errors:
                                st.write(e)
                            # Only clear if completely successful? Or just clear successful ones?
                            # Prototype simplicity: Clear only if all good, or warn. 
                            # Let's keep cart if error.
                        else:
                            st.success("Transaction Completed Successfully!")
                            st.session_state.cart = [] # Clear cart
                            st.rerun()
                            
                    if col_clear.button("🗑️ Clear Cart"):
                        st.session_state.cart = []
                        st.rerun()
                else:
                    st.info("Cart is empty.")
    
    # --- Tab 2: Register Delivery ---
    with tab2:
        st.header("Incoming Deliveries")
        
        # 1. Scheduled Deliveries Section
        st.subheader("⏳ Scheduled Deliveries")
        scheduled = get_scheduled_deliveries()
        
        if not scheduled.empty:
            # Display as a clean list/table with actions
            for index, row in scheduled.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 1, 2, 1.5])
                    c1.markdown(f"**{row['name']}**")
                    c2.markdown(f"Qty: `{row['quantity']}`")
                    c3.caption(f"Scheduled by: {row['scheduler']}")
                    
                    if c4.button("✅ Confirm", key=f"conf_{row['id']}"):
                        success, msg = confirm_delivery(row['id'], user['name'])
                        if success:
                            st.success(f"Confirmed {row['quantity']} {row['name']}!")
                            st.rerun()
                        else:
                            st.error(msg)
                    st.divider()
        else:
            st.info("No scheduled deliveries pending.")

        st.markdown("---")
        
        # 2. Manual Entry Section
        with st.expander("Register Unscheduled Delivery (Direct Entry)"):
            if inventory_df.empty:
                st.warning("No products initialized.")
            else:
                with st.form("delivery_form"):
                    product_map = dict(zip(inventory_df['name'], inventory_df['id']))
                    
                    selected_product_name = st.selectbox("Select Product", inventory_df['name'].unique())
                    quantity = st.number_input("Quantity Received", min_value=1, value=50)
                    cost_price = st.number_input("Cost Price (Per Unit)", min_value=0.0, value=5.0, step=0.5)
                    
                    delivery_submit = st.form_submit_button("Register Delivery")
                    
                    if delivery_submit:
                        product_id = product_map[selected_product_name]
                        add_product_stock(product_id, quantity, user['name'], cost_price=cost_price)
                        st.success(f"Added {quantity} x {selected_product_name} to inventory!")


if __name__ == "__main__":
    main()
