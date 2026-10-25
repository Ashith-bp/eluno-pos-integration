import sys
from client import ElunoAPIClient
from calculator import calculate_gst

class POSCashierTerminal:
    def __init__(self):
        self.client = ElunoAPIClient()
        self.location_id = None
        self._initialize_session()

    def _initialize_session(self):
        """Fetch active store location on startup."""
        try:
            locations = self.client.get_locations().get("locations", [])
            if locations:
                self.location_id = locations[0]["id"]
            else:
                print("Warning: No store locations found on server.")
        except Exception as e:
            print(f"Initialization error connecting to server: {e}")

    def run(self):
        """Run interactive CLI menu."""
        while True:
            print("\n========================================")
            print("         ELUNO POS CASHIER DESK         ")
            print("========================================")
            print("1. Browse Catalog & Stock")
            print("2. Search Customer by Phone")
            print("3. Process New Sale (Checkout)")
            print("4. Process Terminal Refund")
            print("5. Exit")
            
            choice = input("\nSelect an option (1-5): ").strip()
            
            if choice == "1":
                self.show_catalog()
            elif choice == "2":
                self.search_customer_flow()
            elif choice == "3":
                self.checkout_flow()
            elif choice == "4":
                self.refund_flow()
            elif choice == "5":
                print("\nExiting POS Terminal. Have a great day!")
                sys.exit(0)
            else:
                print("Invalid option. Please enter a number between 1 and 5.")

    def show_catalog(self):
        """Display available products and variant pricing."""
        print("\n--- PRODUCT CATALOG ---")
        try:
            products = self.client.get_products().get("products", [])
            for p in products:
                print(f"Product ID: {p['id']} | {p['title']} ({p.get('product_type', 'N/A')})")
                for v in p.get("variants", []):
                    print(f"  -> Variant ID: {v['id']} | Title: {v['title']} | Price: ₹{v['price']}")
        except Exception as e:
            print(f"Failed to fetch catalog: {e}")

    def search_customer_flow(self):
        """Interactive customer search."""
        phone = input("Enter customer phone number (e.g., +919876543210): ").strip()
        try:
            res = self.client.search_customers(phone)
            customers = res.get("customers", [])
            if customers:
                c = customers[0]
                print(f"\nFound Customer: {c.get('first_name')} {c.get('last_name')}")
                print(f"Email: {c.get('email')} | Phone: {c.get('phone')} | ID: {c.get('id')}")
            else:
                print("\nNo customer found with that phone number.")
        except Exception as e:
            print(f"Customer search failed: {e}")

    def checkout_flow(self):
        """Process end-to-end sale."""
        if not self.location_id:
            print("Error: Store location not initialized.")
            return

        print("\n--- NEW SALE CHECKOUT ---")
        try:
            products = self.client.get_products().get("products", [])
            if not products:
                print("No products available.")
                return

            # Select first product variant for sale
            product = products[0]
            variant = product["variants"][0]
            gross_price = variant["price"]
            
            print(f"Selected Item: {product['title']} - {variant['title']} (₹{gross_price})")

            # Optional customer attachment
            phone = input("Enter customer phone for loyalty/records (leave blank for guest): ").strip()
            customer_id = None
            if phone:
                cust_res = self.client.search_customers(phone)
                cust_list = cust_res.get("customers", [])
                if cust_list:
                    customer_id = cust_list[0]["id"]
                    print(f"Attached Customer ID: {customer_id}")

            # Terminal Payment (convert price to paise integer)
            amount_paise = int(float(gross_price) * 100)
            order_ref = f"POS-ORD-{amount_paise}"

            print(f"Processing UPI payment of ₹{gross_price}...")
            charge_res = self.client.create_terminal_charge(amount_paise=amount_paise, order_ref=order_ref, method="upi")
            charge_id = charge_res.get("charge_id")
            print(f"Payment Captured! Charge ID: {charge_id}")

            # Calculate GST Tax Lines using calculator.py
            tax_breakdown = calculate_gst(gross_price)

            # Build Shopify-compliant Order Payload
            order_data = {
                "taxes_included": True,
                "line_items": [
                    {
                        "variant_id": variant["id"],
                        "quantity": 1,
                        "price": gross_price,
                        "tax_lines": [
                            {"title": "CGST", "price": tax_breakdown["cgst"], "rate": 0.09},
                            {"title": "SGST", "price": tax_breakdown["sgst"], "rate": 0.09}
                        ]
                    }
                ],
                "transactions": [
                    {
                        "kind": "sale",
                        "status": "success",
                        "amount": gross_price
                    }
                ],
                "inventory_behaviour": "decrement_obeying_policy",
                "location_id": self.location_id
            }

            if customer_id:
                order_data["customer"] = {"id": customer_id}

            order_res = self.client.create_order({"order": order_data}, idempotency_key=order_ref)
            o = order_res.get("order", {})
            print(f"\nSUCCESS! Order #{o.get('order_number')} created successfully.")
            print(f"Financial Status: {o.get('financial_status')} | Total: ₹{o.get('total_price')}")

        except Exception as e:
            print(f"Checkout failed: {e}")

    def refund_flow(self):
        """Process terminal refund."""
        print("\n--- PROCESS REFUND ---")
        charge_id = input("Enter Charge ID to refund (e.g., chg_...): ").strip()
        amount_str = input("Enter amount to refund in INR (e.g., 12998.00): ").strip()
        reason = input("Enter refund reason: ").strip()

        try:
            amount_paise = int(float(amount_str) * 100)
            refund_res = self.client.refund_terminal_charge(
                charge_id=charge_id,
                amount_paise=amount_paise,
                reason=reason or "Customer return"
            )
            print(f"\nSUCCESS! Refund ID: {refund_res.get('refund_id')} | Status: {refund_res.get('status')}")
        except Exception as e:
            print(f"Refund processing failed: {e}")

if __name__ == "__main__":
    terminal = POSCashierTerminal()
    terminal.run()