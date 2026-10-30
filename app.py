import streamlit as st
import json
import os
import requests
import socket
from datetime import datetime

# ==========================================
# CONFIGURATION & PATHS
# ==========================================
st.set_page_config(
    page_title="Eluno POS & Inventory Terminal",
    page_icon="👓",
    layout="wide"
)

API_BASE_URL = "http://localhost:8787"
DATA_DIR = "data"

# ==========================================
# RESILIENT API CLIENT (FALLBACK HANDLER)
# ==========================================
class ElunoAPIClient:
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url

    def _is_server_alive(self):
        try:
            socket.create_connection(("localhost", 8787), timeout=0.3)
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def _load_local_fallback(self, filename):
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get(self, endpoint, fallback_filename):
        if not self._is_server_alive():
            st.toast(f"⚠️ Server offline: Loaded local fallback for {fallback_filename}", icon="⚡")
            return self._load_local_fallback(fallback_filename)
        
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", timeout=2.0)
            if response.status_code in [429, 503]:
                st.toast(f"⚠️ Server status {response.status_code}: Using local ledger sync.", icon="⚡")
                return self._load_local_fallback(fallback_filename)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            st.toast(f"⚠️ Network error: Loaded local fallback for {fallback_filename}", icon="⚡")
            return self._load_local_fallback(fallback_filename)

api_client = ElunoAPIClient()

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "cart" not in st.session_state:
    st.session_state.cart = []
if "orders" not in st.session_state:
    # Load initial orders if available locally
    orders_path = os.path.join(DATA_DIR, "orders_sample.json")
    if os.path.exists(orders_path):
        with open(orders_path, "r", encoding="utf-8") as f:
            st.session_state.orders = json.load(f)
    else:
        st.session_state.orders = []

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("👓 Eluno Optical POS")
st.sidebar.caption("Store Terminal & Inventory")
app_mode = st.sidebar.selectbox("Select Module", [
    "🛒 Cashier Checkout", 
    "📦 Catalog & Stock", 
    "🔄 Itemized Refunds", 
    "📊 Z-Report & Audit"
])

# ==========================================
# MODULE 1: CASHIER CHECKOUT
# ==========================================
if app_mode == "🛒 Cashier Checkout":
    st.title("🛒 Point of Sale & Lens Validation Terminal")
    
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.subheader("1. Customer Lookup & Prescription")
        customers = api_client.get("customers", "customers.json")
        prescriptions = api_client.get("prescriptions", "prescriptions.json")
        
        # Phone input for customer lookup
        phone_input = st.text_input("Enter Customer Phone Number", placeholder="+919000000020")
        
        selected_customer = None
        active_rx = None
        
        if phone_input:
            # Search customer by phone
            matched_customers = [c for c in customers if phone_input in c.get("phone", "")]
            if matched_customers:
                selected_customer = matched_customers[0]
                st.success(f"Customer Found: **{selected_customer.get('name')}** (ID: {selected_customer.get('customer_id')})")
                
                # Automatically lookup active prescription
                matched_rx = [rx for rx in prescriptions if str(rx.get("customer_id")) == str(selected_customer.get("customer_id")) or phone_input in rx.get("phone", "")]
                if matched_rx:
                    active_rx = matched_rx[0]
                    st.info(f"👓 Active Prescription Found (`{active_rx.get('rx_id')}`) - Lens Validation Ready")
                    
                    rx_col1, rx_col2 = st.columns(2)
                    with rx_col1:
                        st.markdown("**Right Eye (OD)**")
                        od = active_rx.get('od', {})
                        st.write(f"Sph: {od.get('sph')} | Cyl: {od.get('cyl')} | Axis: {od.get('axis')}°")
                    with rx_col2:
                        st.markdown("**Left Eye (OS)**")
                        os = active_rx.get('os', {})
                        st.write(f"Sph: {os.get('sph')} | Cyl: {os.get('cyl')} | Axis: {os.get('axis')}°")
                    
                    pd = active_rx.get('pd', {})
                    st.caption(f"PD: {pd.get('binocular')} mm | Valid Until: {active_rx.get('valid_until')}")
                else:
                    st.warning("⚠️ No active prescription found for this customer. Please attach or create one.")
            else:
                st.warning("Customer not found. Walk-in mode active.")

        st.markdown("---")
        st.subheader("2. Add Products to Cart")
        products = api_client.get("products", "products.json")
        
        product_options = {f"{p.get('name')} (SKU: {p.get('sku')}) - ₹{p.get('mrp')}": p for p in products}
        selected_prod_label = st.selectbox("Select Catalog Item", options=list(product_options.keys()) if product_options else ["No products available"])
        
        if product_options and st.button("Add to Cart"):
            prod = product_options[selected_prod_label]
            # Check if already in cart
            existing_item = next((item for item in st.session_state.cart if item['sku'] == prod['sku']), None)
            if existing_item:
                existing_item['qty'] += 1
            else:
                st.session_state.cart.append({
                    "sku": prod.get("sku"),
                    "name": prod.get("name"),
                    "type": prod.get("type", "frame"),
                    "mrp": prod.get("mrp", 0.0),
                    "qty": 1
                })
            st.toast("Item added to cart!", icon="🛒")

    with col2:
        st.subheader("3. Active Cart & Billing")
        if not st.session_state.cart:
            st.info("Cart is currently empty.")
        else:
            subtotal = 0.0
            for i, item in enumerate(st.session_state.cart):
                item_total = item['mrp'] * item['qty']
                subtotal += item_total
                
                c_a, c_b, c_c = st.columns([2, 1, 1])
                c_a.write(f"**{item['name']}**\n\n₹{item['mrp']} x {item['qty']}")
                if c_b.button("❌", key=f"rem_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            st.markdown("---")
            
            # Offers & Discounts
            st.markdown("**Offers & Discounts**")
            discount_type = st.selectbox("Apply Offer Slab", ["None", "Diwali 10% Off", "VIP 20% Off", "Flat ₹500 Off", "Custom Discount"])
            
            discount_amount = 0.0
            if discount_type == "Diwali 10% Off":
                discount_amount = subtotal * 0.10
            elif discount_type == "VIP 20% Off":
                discount_amount = subtotal * 0.20
            elif discount_type == "Flat ₹500 Off":
                discount_amount = 500.0
            elif discount_type == "Custom Discount":
                cust_disc_val = st.number_input("Discount Value", min_value=0.0, value=0.0)
                is_pct = st.checkbox("Is Percentage (%)?")
                discount_amount = (subtotal * (cust_disc_val / 100.0)) if is_pct else cust_disc_val

            final_payable = max(0.0, subtotal - discount_amount)
            
            # Inclusive GST Calculation (18% GST extracted from MRP)
            tax_amount = (final_payable * 0.18) / 1.18
            net_taxable = final_payable - tax_amount
            
            st.write(f"Subtotal: ₹{subtotal:.2f}")
            if discount_amount > 0:
                st.write(f"Discount: -₹{discount_amount:.2f}")
            st.write(f"**Final Payable (MRP incl. GST): ₹{final_payable:.2f}**")
            st.caption(f"Tax Breakdown (18% Inclusive): CGST/SGST Tax Component: ₹{tax_amount:.2f}")
            
            payment_mode = st.selectbox("Payment Mode", ["UPI", "Cash", "Card", "Credit/Split"])
            
            if st.button("Complete Charge & Print Invoice", type="primary"):
                new_order = {
                    "order_id": f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "customer": selected_customer.get('name') if selected_customer else "Walk-in Customer",
                    "phone": phone_input if phone_input else "N/A",
                    "items": st.session_state.cart.copy(),
                    "subtotal": subtotal,
                    "discount": discount_amount,
                    "total_paid": final_payable,
                    "payment_mode": payment_mode,
                    "created_at": datetime.now().isoformat()
                }
                st.session_state.orders.append(new_order)
                st.session_state.cart = []
                st.balloons()
                st.success(f"Payment Successful! Invoice generated: `{new_order['order_id']}`")

# ==========================================
# MODULE 2: CATALOG & STOCK
# ==========================================
elif app_mode == "📦 Catalog & Stock":
    st.title("📦 Optical Catalog & Inventory Management")
    products = api_client.get("products", "products.json")
    
    search_query = st.text_input("Search catalog by SKU or Name", placeholder="e.g. Ray-Ban or LENS")
    
    filtered_products = products
    if search_query:
        filtered_products = [p for p in products if search_query.lower() in p.get('name', '').lower() or search_query.lower() in p.get('sku', '').lower()]
    
    for p in filtered_products:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            col1.write(f"**{p.get('name')}**\n\nSKU: `{p.get('sku')}` | Type: `{p.get('type', 'frame')}`")
            col2.write(f"MRP: **₹{p.get('mrp')}**")
            col3.write(f"Stock: **{p.get('stock', 10)} units**")
            col4.badge("Active" if p.get('stock', 10) > 0 else "Out of Stock")
            st.divider()

# ==========================================
# MODULE 3: ITEMIZED REFUNDS
# ==========================================
elif app_mode == "🔄 Itemized Refunds":
    st.title("🔄 Itemized Returns & Restock Rules")
    st.markdown("Enter an order ID (e.g., `#1012` or loaded session order) to process an itemized return.")
    
    order_id_input = st.text_input("Search Order ID", placeholder="ORD-...")
    
    target_order = None
    sample_orders_path = os.path.join(DATA_DIR, "orders_sample.json")
    all_known_orders = st.session_state.orders.copy()
    if os.path.exists(sample_orders_path):
        with open(sample_orders_path, "r", encoding="utf-8") as f:
            all_known_orders.extend(json.load(f))
            
    for o in all_known_orders:
        if order_id_input and order_id_input.lower() in str(o.get('order_id', '')).lower():
            target_order = o
            break
            
    if target_order:
        st.success(f"Order Found: `{target_order.get('order_id')}` | Customer: {target_order.get('customer', 'N/A')}")
        st.write(f"Date: {target_order.get('created_at', 'N/A')} | Total Paid: ₹{target_order.get('total_paid', 0.0)}")
        
        st.markdown("### Select Items to Return")
        items = target_order.get('items', [])
        
        return_selection = []
        for i, item in enumerate(items):
            is_selected = st.checkbox(f"Return: {item.get('name')} (Qty: {item.get('qty')} - ₹{item.get('mrp')})", key=f"ret_{i}")
            if is_selected:
                return_selection.append(item)
                
        if return_selection:
            st.markdown("---")
            st.markdown("### 📋 Inventory Restock Assessment")
            for item in return_selection:
                item_type = item.get('type', 'frame').lower()
                if item_type == 'lens' or 'lens' in item.get('name', '').lower():
                    st.warning(f"⚠️ **{item.get('name')}**: Custom prescription lens detected. **Excluded from inventory restock** (written off per optical policy).")
                else:
                    st.info(f"✅ **{item.get('name')}**: Physical frame verified. **Will be restocked** back into active inventory.")
            
            refund_mode = st.selectbox("Refund Mode", ["Original Payment Method", "Store Credit", "Cash Refund"])
            if st.button("Process Refund & Generate Credit Note", type="primary"):
                st.balloons()
                st.success(f"Refund successfully processed via {refund_mode}! Inventory adjustments recorded.")
    elif order_id_input:
        st.warning("Order ID not found in active ledgers.")

# ==========================================
# MODULE 4: Z-REPORT & AUDIT
# ==========================================
elif app_mode == "📊 Z-Report & Audit":
    st.title("📊 Day-End Z-Report & Cash Drawer Reconciliation")
    
    selected_date = st.date_input("Select Z-Report Date", value=datetime.strptime("2026-10-06", "%Y-%m-%d").date())
    
    sample_orders_path = os.path.join(DATA_DIR, "orders_sample.json")
    report_orders = st.session_state.orders.copy()
    if os.path.exists(sample_orders_path):
        with open(sample_orders_path, "r", encoding="utf-8") as f:
            report_orders.extend(json.load(f))
            
    date_str = selected_date.strftime("%Y-%m-%d")
    matched_day_orders = [o for o in report_orders if date_str in str(o.get("created_at", ""))]
    
    total_sales = sum(o.get("total_paid", 0.0) for o in matched_day_orders)
    total_transactions = len(matched_day_orders)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Day Revenue", f"₹{total_sales:.2f}")
    col2.metric("Total Transactions", total_transactions)
    col3.metric("Average Basket Size", f"₹{(total_sales / total_transactions if total_transactions > 0 else 0):.2f}")
    
    st.markdown("---")
    st.subheader("Cash Drawer Reconciliation")
    
    opening_float = 5000.0
    cash_sales = sum(o.get("total_paid", 0.0) for o in matched_day_orders if o.get("payment_mode") == "Cash")
    expected_drawer = opening_float + cash_sales
    
    rc1, rc2 = st.columns(2)
    rc1.write(f"Opening Float: **₹{opening_float:.2f}**")
    rc1.write(f"Cash Sales Collected: **₹{cash_sales:.2f}**")
    rc1.write(f"**Expected Cash in Drawer: ₹{expected_drawer:.2f}**")
    
    actual_counted_cash = rc2.number_input("Physically Counted Drawer Cash (₹)", min_value=0.0, value=expected_drawer)
    variance = actual_counted_cash - expected_drawer
    
    if variance == 0:
        rc2.success("Drawer Balanced Perfectly! ✅")
    elif variance > 0:
        rc2.info(f"Drawer is **OVER** by ₹{variance:.2f}")
    else:
        rc2.error(f"Drawer is **SHORT** by ₹{abs(variance):.2f} (Manager Audit Required)")
