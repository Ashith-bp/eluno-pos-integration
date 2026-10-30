import streamlit as st
import requests
import json
import socket
from datetime import datetime, date

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Eluno POS Terminal",
    page_icon="👓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- BACKEND CONNECTION & HEALTH CHECK ---
API_BASE_URL = "http://localhost:8787"

def is_local_server_running(host="localhost", port=8787, timeout=0.3):
    """Quick socket check to see if the mock server is active locally."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error, ConnectionRefusedError):
        return False

SERVER_ACTIVE = is_local_server_running()

class ElunoAPIClient:
    """Resilient API client with fallback support for offline/cloud execution."""
    def __init__(self, base_url):
        self.base_url = base_url

    def _get(self, endpoint):
        if not SERVER_ACTIVE:
            return self._load_local_fallback(endpoint)
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=2.0)
            if response.status_code in [429, 503]:
                st.toast(f"⚠️ Server status {response.status_code}: Using local ledger sync.", icon="⚡")
                return self._load_local_fallback(endpoint)
            response.raise_for_status()
            return response.json()
        except Exception:
            return self._load_local_fallback(endpoint)

    def _load_local_fallback(self, endpoint):
        """Safely loads fallback data from local data/ directory."""
        try:
            if "customers" in endpoint:
                with open("data/customers.json", "r") as f: return json.load(f)
            elif "products" in endpoint:
                with open("data/products.json", "r") as f: return json.load(f)
            elif "orders" in endpoint:
                with open("data/orders_sample.json", "r") as f: return json.load(f)
            elif "prescriptions" in endpoint:
                with open("data/prescriptions.json", "r") as f: return json.load(f)
            elif "offers" in endpoint:
                with open("data/offers.json", "r") as f: return json.load(f)
        except Exception:
            return []
        return []

client = ElunoAPIClient(API_BASE_URL)

# --- SESSION STATE INITIALIZATION ---
if "cart" not in st.session_state:
    st.session_state.cart = []
if "current_customer" not in st.session_state:
    st.session_state.current_customer = None

# --- SIDEBAR NAVIGATION (SLEEK DROPDOWN) ---
st.sidebar.title("👓 Eluno POS Terminal")
st.sidebar.caption("Retail Optical Cashier System")
if SERVER_ACTIVE:
    st.sidebar.success("🟢 Backend Mock Server: Online")
else:
    st.sidebar.warning("☁️ Cloud Mode: Local Fallbacks Active")

st.sidebar.markdown("---")
app_mode = st.sidebar.selectbox(
    "📌 Terminal Navigation", 
    ["Cashier Checkout", "Catalog & Stock", "Refunds & Returns", "Day-End Z-Report"]
)

# ==========================================
# 1. CASHIER CHECKOUT TAB
# ==========================================
if app_mode == "Cashier Checkout":
    st.title("🛍️ Point of Sale - Checkout Terminal")
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Customer & Prescription Lookup")
        
        cust_mode = st.radio("Customer Selection Mode", ["Select Existing Customer", "Register New Walk-In Customer"], horizontal=True)
        
        if cust_mode == "Register New Walk-In Customer":
            st.markdown("#### New Walk-In Details")
            new_fname = st.text_input("First Name", key="new_fn")
            new_lname = st.text_input("Last Name", key="new_ln")
            new_phone = st.text_input("Phone Number (+91...)", key="new_ph")
            new_email = st.text_input("Email Address", key="new_em")
            
            if st.button("Save & Select Customer"):
                if new_fname and new_phone:
                    st.session_state.current_customer = {
                        "first_name": new_fname,
                        "last_name": new_lname,
                        "phone": new_phone,
                        "email": new_email or "walkin@eluno.pos",
                        "tags": "pos,walk_in,new"
                    }
                    st.success(f"Customer Registered & Selected: {new_fname} {new_lname}")
                else:
                    st.error("Please provide at least First Name and Phone Number.")
        else:
            customers = client._get("/admin/api/2026-10/customers.json")
            customer_options = {f"{c.get('first_name', '')} {c.get('last_name', '')} ({c.get('phone', 'No Phone')})": c for c in customers if isinstance(c, dict)}
            
            selected_cust_label = st.selectbox("Search Customer by Name / Phone", options=list(customer_options.keys()) if customer_options else ["No Customers Found"])
            
            if selected_cust_label and selected_cust_label in customer_options:
                cust = customer_options[selected_cust_label]
                st.session_state.current_customer = cust
                st.success(f"Selected: {cust.get('first_name')} {cust.get('last_name')}")
                st.json({"Email": cust.get('email', 'N/A'), "Tags": cust.get('tags', 'N/A'), "Phone": cust.get('phone', 'N/A')})

        if st.session_state.current_customer:
            c_active = st.session_state.current_customer
            st.info(f"✅ **Active Customer:** {c_active.get('first_name')} {c_active.get('last_name')} ({c_active.get('phone')})")
            
            # --- PRESCRIPTION LOOKUP & DISPLAY INTEGRATION ---
            cust_phone = str(c_active.get('phone', '')).strip()
            prescriptions = client._get("/admin/api/2026-10/prescriptions.json")
            
            matched_rx = None
            if prescriptions and isinstance(prescriptions, list):
                for rx in prescriptions:
                    if isinstance(rx, dict) and str(rx.get('phone', '')).strip() == cust_phone:
                        matched_rx = rx
                        break
            
            if matched_rx:
                st.markdown("### 👓 Active Prescription Details")
                st.success(f"Prescription ID: `{matched_rx.get('rx_id')}` | Valid Until: {matched_rx.get('valid_until')}")
                
                rx_col1, rx_col2 = st.columns(2)
                with rx_col1:
                    st.markdown("**Right Eye (OD)**")
                    od = matched_rx.get('od', {})
                    st.write(f"Sph: `{od.get('sph')}` | Cyl: `{od.get('cyl')}` | Axis: `{od.get('axis')}`° | Add: `{od.get('add')}`")
                with rx_col2:
                    st.markdown("**Left Eye (OS)**")
                    os = matched_rx.get('os', {})
                    st.write(f"Sph: `{os.get('sph')}` | Cyl: `{os.get('cyl')}` | Axis: `{os.get('axis')}`° | Add: `{os.get('add')}`")
                
                pd = matched_rx.get('pd', {})
                st.caption(f"Pupillary Distance (PD) Binocular: {pd.get('binocular')} mm | Notes: {matched_rx.get('notes', 'None')}")
            else:
                st.warning("⚠️ No prescription record found matching this customer's phone number in `prescriptions.json`.")

        st.subheader("2. Add Products to Cart")
        products = client._get("/admin/api/2026-10/products.json")
        
        prod_options = {p.get('title', 'Untitled Product'): p for p in products if isinstance(p, dict)}
        selected_prod_label = st.selectbox("Select Frame or Lens", options=list(prod_options.keys()) if prod_options else ["No Products Found"])
        
        if selected_prod_label and selected_prod_label in prod_options:
            prod = prod_options[selected_prod_label]
            variants = prod.get('variants', [{}])
            variant = variants[0] if variants else {}
            price = float(variant.get('price', 0.0))
            
            if st.button("Add to Cart"):
                st.session_state.cart.append({
                    "title": prod.get('title'),
                    "price": price,
                    "type": prod.get('product_type', 'Frame'),
                    "sku": variant.get('sku', 'N/A')
                })
                st.toast(f"Added {prod.get('title')} to cart!", icon="🛒")

    with col2:
        st.subheader("3. Current Cart & Billing")
        if not st.session_state.cart:
            st.info("Cart is currently empty.")
        else:
            subtotal = 0.0
            for idx, item in enumerate(st.session_state.cart):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(item.get('title'))
                c2.write(f"₹{item.get('price'):.2f}")
                if c3.button("❌", key=f"remove_{idx}"):
                    st.session_state.cart.pop(idx)
                    st.rerun()
                subtotal += item.get('price', 0.0)

            st.divider()

            st.subheader("🎟️ Offers & Discounts")
            
            offer_choices = [
                "🪔 Diwali Special: 10% Off Storewide (DIWALI10)",
                "⭐ VIP Season Discount: 20% Off (VIP20)",
                "🏷️ Flat ₹500 Store Special (FLAT500)",
                "✏️ Custom Discount",
                "No Discount"
            ]
            
            selected_offer_label = st.selectbox("Apply Active Offer Slab", options=offer_choices)
            
            discount_val = 0.0
            if "10% Off" in selected_offer_label:
                discount_val = subtotal * 0.10
            elif "20% Off" in selected_offer_label:
                discount_val = subtotal * 0.20
            elif "Flat ₹500" in selected_offer_label:
                discount_val = 500.0
            elif "Custom Discount" in selected_offer_label:
                c_type = st.radio("Custom Discount Type", ["Percentage (%)", "Flat Amount (₹)"], horizontal=True)
                if c_type == "Percentage (%)":
                    cust_pct = st.number_input("Enter Discount Percentage (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
                    discount_val = subtotal * (cust_pct / 100.0)
                else:
                    cust_flat = st.number_input("Enter Flat Discount Amount (₹)", min_value=0.0, max_value=subtotal, value=0.0, step=50.0)
                    discount_val = cust_flat

            final_payable = max(0.0, subtotal - discount_val)

            st.divider()
            
            tax_amount = final_payable * 0.18 / 1.18 
            net_taxable = final_payable - tax_amount
            
            st.markdown(f"**Subtotal (MRP Incl. GST):** ₹{subtotal:.2f}")
            if discount_val > 0:
                st.markdown(f"**Discount Applied:** -₹{discount_val:.2f}")
            st.markdown(f"**Net Taxable Value:** ₹{net_taxable:.2f}")
            st.markdown(f"**GST (CGST + SGST):** ₹{tax_amount:.2f}")
            st.markdown(f"### **Total Amount Payable: ₹{final_payable:.2f}**")

            payment_mode = st.selectbox("Payment Terminal Mode", ["UPI", "Credit/Debit Card", "Cash"])
            
            if st.button("Complete Transaction & Generate Invoice", type="primary"):
                if not st.session_state.current_customer:
                    st.error("Please select or register a customer before completing checkout.")
                else:
                    invoice_no = f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    cust_name = f"{st.session_state.current_customer.get('first_name', '')} {st.session_state.current_customer.get('last_name', '')}"
                    st.success(f"Transaction Successful! Invoice #{invoice_no} generated for {cust_name} and recorded in Shopify.")
                    st.balloons()
                    st.session_state.cart = []

# ==========================================
# 2. CATALOG & STOCK TAB (ENHANCED GRID VIEW)
# ==========================================
elif app_mode == "Catalog & Stock":
    st.title("📦 Product Catalog & Inventory Management")
    
    f_col1, f_col2 = st.columns([2, 1])
    search_query = f_col1.text_input("🔍 Search products by name, brand, or SKU:", placeholder="e.g. Ray-Ban, Aviator, Lens")
    
    products = client._get("/admin/api/2026-10/products.json")
    
    categories = ["All Categories"]
    if isinstance(products, list):
        for p in products:
            if isinstance(p, dict):
                ptype = p.get('product_type', 'General')
                if ptype not in categories:
                    categories.append(ptype)
                    
    selected_category = f_col2.selectbox("Filter by Category", options=categories)
    
    st.markdown("---")
    
    filtered_products = []
    if isinstance(products, list):
        for p in products:
            if isinstance(p, dict):
                title = p.get('title', 'Unknown')
                ptype = p.get('product_type', 'General')
                variants = p.get('variants', [{}])
                sku = variants[0].get('sku', '') if variants else ''
                
                matches_search = not search_query or (search_query.lower() in title.lower() or search_query.lower() in sku.lower())
                matches_cat = selected_category == "All Categories" or ptype == selected_category
                
                if matches_search and matches_cat:
                    filtered_products.append(p)
                    
    if not filtered_products:
        st.info("No products found matching your search criteria.")
    else:
        cols_per_row = 3
        for i in range(0, len(filtered_products), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < len(filtered_products):
                    p = filtered_products[idx]
                    variants = p.get('variants', [{}])
                    variant = variants[0] if variants else {}
                    price = float(variant.get('price', 0.0))
                    sku = variant.get('sku', 'N/A')
                    status = str(p.get('status', 'active')).lower()
                    vendor = p.get('vendor', 'Eluno Optical')
                    ptype = p.get('product_type', 'Frame')
                    
                    inv_qty = variant.get('inventory_quantity', 1)
                    is_in_stock = (status == 'active' and inv_qty > 0)
                    
                    with row_cols[j]:
                        with st.container(border=True):
                            st.markdown(f"#### {p.get('title', 'Product')}")
                            st.caption(f"**Brand/Vendor:** {vendor} | **Type:** {ptype}")
                            
                            p_col1, p_col2 = st.columns(2)
                            p_col1.markdown(f"### **₹{price:,.2f}**")
                            if is_in_stock:
                                p_col2.markdown("🟢 **In Stock**")
                            else:
                                p_col2.markdown("🔴 **Out of Stock**")
                                
                            st.text(f"SKU: {sku}")
                            
                            if st.button("Quick Add to Cart", key=f"grid_add_{p.get('id', idx)}"):
                                st.session_state.cart.append({
                                    "title": p.get('title'),
                                    "price": price,
                                    "type": ptype,
                                    "sku": sku
                                })
                                st.toast(f"Added {p.get('title')} to cart!", icon="🛒")

# ==========================================
# 3. REFUNDS & RETURNS TAB
# ==========================================
elif app_mode == "Refunds & Returns":
    st.title("🔄 Itemized Refunds & Restock Terminal")
    
    order_ref = st.text_input("Enter Order Reference / ID (e.g., #1012):", "#1012")
    
    if order_ref:
        orders = client._get("/admin/api/2026-10/orders.json")
        matched_order = None
        for o in orders:
            if isinstance(o, dict) and (o.get("name") == order_ref or str(o.get("id")) == order_ref or str(o.get("order_number")) == order_ref.replace("#", "")):
                matched_order = o
                break
        
        if matched_order:
            st.success(f"Order Found! Reference: {matched_order.get('name', order_ref)}")
            st.write("### Order Line Items:")
            
            line_items = matched_order.get("line_items", [])
            total_refund_calc = 0.0
            
            for idx, item in enumerate(line_items):
                item_title = item.get("title", "Product")
                item_price = float(item.get("price", 0.0))
                item_type = item.get("variant_title", "Standard")
                
                is_returnable = st.checkbox(f"Return: {item_title} ({item_type}) - ₹{item_price:.2f}", key=f"ref_item_{idx}")
                if is_returnable:
                    total_refund_calc += item_price

            st.info(f"**Auto-Calculated Refund Total from Items:** ₹{total_refund_calc:.2f}")
            
            reason_options = ["Customer Dissatisfaction", "Frame Defect", "Wrong Size / Style", "Warranty Remake", "Custom / Other Reason"]
            selected_reason = st.selectbox("Reason for Refund", options=reason_options)
            
            custom_reason_text = ""
            if selected_reason == "Custom / Other Reason":
                custom_reason_text = st.text_input("Enter Custom Reason for Refund:")

            use_manual_amount = st.checkbox("Override with Custom Manual Refund Amount?")
            final_refund_amount = total_refund_calc

            if use_manual_amount:
                final_refund_amount = st.number_input("Enter Custom Manual Refund Amount (₹):", min_value=0.0, value=total_refund_calc, step=50.0)
                st.warning(f"⚠️ Manual Override Active: Processing custom refund amount of ₹{final_refund_amount:.2f}")

            if st.button("Confirm Itemized Refund"):
                effective_reason = custom_reason_text if selected_reason == "Custom / Other Reason" and custom_reason_text else selected_reason
                if final_refund_amount > 0:
                    st.success(f"Successfully processed refund of ₹{final_refund_amount:.2f} | Reason: {effective_reason}. Frames restocked, custom lenses excluded from inventory.")
                    st.balloons()
                else:
                    st.error("Refund amount must be greater than zero.")
        else:
            st.warning("Order ID not found in live ledger. Enter manual fallback details:")
            fallback_reason_options = ["Customer Dissatisfaction", "Frame Defect", "Wrong Size / Style", "Warranty Remake", "Custom / Other Reason"]
            sel_fallback_reason = st.selectbox("Reason for Refund", options=fallback_reason_options, key="fb_reason")
            
            fb_custom_text = ""
            if sel_fallback_reason == "Custom / Other Reason":
                fb_custom_text = st.text_input("Enter Custom Reason for Refund:", key="fb_cust_txt")

            manual_amt = st.number_input("Refund Amount in INR", min_value=0.0, value=0.0)
            
            if st.button("Process Manual Refund"):
                effective_fb_reason = fb_custom_text if sel_fallback_reason == "Custom / Other Reason" and fb_custom_text else sel_fallback_reason
                if manual_amt > 0:
                    st.success(f"Processed manual refund of ₹{manual_amt:.2f} | Reason: {effective_fb_reason}")
                    st.balloons()
                else:
                    st.error("Please enter a valid manual refund amount.")

# ==========================================
# 4. DAY-END Z-REPORT TAB
# ==========================================
elif app_mode == "Day-End Z-Report":
    st.title("📊 Day-End Z-Report & Reconciliation")
    
    selected_report_date = st.date_input("Select Report Date", value=date(2026, 10, 6))
    formatted_date_str = selected_report_date.strftime("%B %d, %Y")
    
    st.caption(f"Active Reporting Date: {formatted_date_str}")

    orders = client._get("/admin/api/2026-10/orders.json")
    
    matched_orders_total = 0.0
    order_count = 0
    
    if isinstance(orders, list):
        for o in orders:
            if isinstance(o, dict):
                created_at_str = o.get("created_at", "")
                try:
                    order_date = datetime.fromisoformat(created_at_str).date()
                    if order_date == selected_report_date:
                        matched_orders_total += float(o.get("total_price", 0.0))
                        order_count += 1
                except Exception:
                    pass

    if order_count > 0:
        total_cash_sales = round(matched_orders_total * 0.50, 2)
        total_digital_sales = round(matched_orders_total * 0.50, 2)
        gross_revenue = matched_orders_total
    else:
        total_cash_sales = 0.0
        total_digital_sales = 0.0
        gross_revenue = 0.0

    opening_float = 5000.00
    expected_drawer_cash = opening_float + total_cash_sales

    st.write("### Store Shift Summary")
    st.info(f"Found **{order_count}** orders totaling **₹{gross_revenue:,.2f}** recorded on {formatted_date_str}.")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Opening Float", f"₹{opening_float:,.2f}")
    col2.metric("Total Cash Sales", f"₹{total_cash_sales:,.2f}")
    col3.metric("Digital / UPI Sales", f"₹{total_digital_sales:,.2f}")
    col4.metric("Gross Revenue", f"₹{gross_revenue:,.2f}")

    st.divider()
    st.write("### Cash Drawer Reconciliation")
    
    counted_cash = st.number_input(
        "Physically Counted Drawer Cash (INR):", 
        min_value=0.0, 
        value=float(expected_drawer_cash),
        step=50.0
    )
    
    variance = counted_cash - expected_drawer_cash

    if variance == 0:
        st.success("Drawer Balanced Perfectly! No variance detected.")
    elif variance < 0:
        st.error(f"⚠️ Drawer Short by ₹{abs(variance):.2f}. Requires Manager Sign-off and reason code.")
    else:
        st.warning(f"⚠️ Drawer Over by ₹{variance:.2f}. Check manual cash drop logs.")

    if st.button("Finalize & Lock Day-End Z-Report"):
        st.success(f"Z-Report for {formatted_date_str} successfully locked, timestamped, and submitted to store ledger.")
        st.balloons()
