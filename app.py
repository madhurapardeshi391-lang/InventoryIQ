from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from config import DB_CONFIG
from datetime import date, timedelta

app = Flask(__name__)


# =========================
# DATABASE CONNECTION
# =========================

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# =========================
# DASHBOARD
# =========================
@app.route("/")
def dashboard():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # ==========================================
        # TOTAL PRODUCTS
        # ==========================================

        cursor.execute("""
            SELECT COUNT(*) AS total_products
            FROM products
        """)

        total_products = cursor.fetchone()["total_products"]


        # ==========================================
        # LOW STOCK
        # ==========================================

        cursor.execute("""
            SELECT COUNT(*) AS low_stock
            FROM products
            WHERE stock <= reorder_level
        """)

        low_stock = cursor.fetchone()["low_stock"]


        # ==========================================
        # TODAY'S SALES
        # ==========================================

        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) AS todays_sales
            FROM sales
            WHERE DATE(created_at) = CURDATE()
        """)

        todays_sales = cursor.fetchone()["todays_sales"]


        # ==========================================
        # TODAY'S PURCHASES
        # ==========================================

        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) AS todays_purchases
            FROM purchases
            WHERE DATE(created_at) = CURDATE()
        """)

        todays_purchases = cursor.fetchone()["todays_purchases"]


        # ==========================================
        # INVENTORY VALUE
        # ==========================================

        cursor.execute("""
            SELECT COALESCE(
                SUM(stock * purchase_price), 0
            ) AS inventory_value
            FROM products
        """)

        inventory_value = cursor.fetchone()["inventory_value"]


        # ==========================================
        # TOTAL SALES TRANSACTIONS
        # ==========================================

        cursor.execute("""
            SELECT COUNT(*) AS total_sales
            FROM sales
        """)

        total_sales = cursor.fetchone()["total_sales"]


        # ==========================================
        # TOTAL REVENUE
        # ==========================================

        cursor.execute("""
            SELECT COALESCE(
                SUM(total_amount), 0
            ) AS total_revenue
            FROM sales
        """)

        total_revenue = cursor.fetchone()["total_revenue"]


        # ==========================================
        # TOTAL PURCHASE VALUE
        # ==========================================

        cursor.execute("""
            SELECT COALESCE(
                SUM(total_amount), 0
            ) AS total_purchase_value
            FROM purchases
        """)

        total_purchase_value = cursor.fetchone()["total_purchase_value"]


        # ==========================================
        # ESTIMATED PROFIT
        # ==========================================

        cursor.execute("""
            SELECT COALESCE(
                SUM(
                    (si.price - p.purchase_price)
                    * si.quantity
                ),
                0
            ) AS estimated_profit
            FROM sale_items si
            INNER JOIN products p
                ON si.product_id = p.id
        """)

        estimated_profit = cursor.fetchone()["estimated_profit"]


        # ==========================================
        # LOW STOCK PRODUCTS
        # ==========================================

        cursor.execute("""
            SELECT
                id,
                name,
                stock,
                reorder_level
            FROM products
            WHERE stock <= reorder_level
            ORDER BY stock ASC
        """)

        low_stock_products = cursor.fetchall()


        # ==========================================
        # RECENT PURCHASES
        # ==========================================

        cursor.execute("""
            SELECT
                pu.id,
                pu.quantity,
                pu.purchase_price,
                pu.total_amount,
                pu.created_at,
                p.name AS product_name
            FROM purchases pu
            INNER JOIN products p
                ON pu.product_id = p.id
            ORDER BY pu.id DESC
            LIMIT 5
        """)

        recent_purchases = cursor.fetchall()


        # ==========================================
        # RECENT SALES
        # ==========================================

        cursor.execute("""
            SELECT
                s.id,
                s.total_amount,
                s.created_at,
                c.name AS customer_name
            FROM sales s
            LEFT JOIN customers c
                ON s.customer_id = c.id
            ORDER BY s.id DESC
            LIMIT 5
        """)

        recent_sales = cursor.fetchall()


        # ==========================================
        # SEND DATA TO DASHBOARD
        # ==========================================

        return render_template(
            "dashboard.html",

            total_products=total_products,

            low_stock=low_stock,

            todays_sales=todays_sales,

            todays_purchases=todays_purchases,

            inventory_value=inventory_value,

            total_sales=total_sales,

            total_revenue=total_revenue,

            total_purchase_value=total_purchase_value,

            estimated_profit=estimated_profit,

            low_stock_products=low_stock_products,

            recent_purchases=recent_purchases,

            recent_sales=recent_sales
        )


    except mysql.connector.Error as error:

        print("Dashboard database error:", error)

        return render_template(
            "dashboard.html",

            total_products=0,

            low_stock=0,

            todays_sales=0,

            todays_purchases=0,

            inventory_value=0,

            total_sales=0,

            total_revenue=0,

            total_purchase_value=0,

            estimated_profit=0,

            low_stock_products=[],

            recent_purchases=[],

            recent_sales=[]
        )


    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# PRODUCTS
# =========================

@app.route("/products")
def products():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                p.id,
                p.name,
                p.purchase_price,
                p.selling_price,
                p.stock,
                p.reorder_level,
                c.name AS category_name
            FROM products p
            LEFT JOIN categories c
                ON p.category_id = c.id
            ORDER BY p.id DESC
        """)

        product_list = cursor.fetchall()

        return render_template(
            "products.html",
            products=product_list
        )

    except mysql.connector.Error as error:

        print("Products database error:", error)

        return render_template(
            "products.html",
            products=[]
        )

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# ADD PRODUCT
# =========================

@app.route("/products/add", methods=["GET", "POST"])
def add_product():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":

            cursor.execute("""
                SELECT id, name
                FROM categories
                ORDER BY name
            """)

            categories = cursor.fetchall()

            return render_template(
                "add_product.html",
                categories=categories
            )

        name = request.form["name"]
        category_id = request.form["category_id"]
        purchase_price = request.form["purchase_price"]
        selling_price = request.form["selling_price"]
        stock = request.form["stock"]
        reorder_level = request.form["reorder_level"]

        cursor.execute("""
            INSERT INTO products
            (
                name,
                category_id,
                purchase_price,
                selling_price,
                stock,
                reorder_level
            )
            VALUES
            (%s, %s, %s, %s, %s, %s)
        """, (
            name,
            category_id,
            purchase_price,
            selling_price,
            stock,
            reorder_level
        ))

        connection.commit()

        print("Product added successfully!")

        return redirect(url_for("products"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Add product database error:", error)

        return "Database error. Check the terminal."

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# EDIT PRODUCT
# =========================

@app.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":

            cursor.execute("""
                SELECT *
                FROM products
                WHERE id = %s
            """, (product_id,))

            product = cursor.fetchone()

            if not product:
                return "Product not found.", 404

            cursor.execute("""
                SELECT id, name
                FROM categories
                ORDER BY name
            """)

            categories = cursor.fetchall()

            return render_template(
                "edit_product.html",
                product=product,
                categories=categories
            )

        name = request.form["name"]
        category_id = request.form["category_id"]
        purchase_price = request.form["purchase_price"]
        selling_price = request.form["selling_price"]
        stock = request.form["stock"]
        reorder_level = request.form["reorder_level"]

        cursor.execute("""
            UPDATE products
            SET
                name = %s,
                category_id = %s,
                purchase_price = %s,
                selling_price = %s,
                stock = %s,
                reorder_level = %s
            WHERE id = %s
        """, (
            name,
            category_id,
            purchase_price,
            selling_price,
            stock,
            reorder_level,
            product_id
        ))

        connection.commit()

        return redirect(url_for("products"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Edit product database error:", error)

        return "Database error. Check the terminal."

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# DELETE PRODUCT
# =========================

@app.route("/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            DELETE FROM products
            WHERE id = %s
        """, (product_id,))

        connection.commit()

        return redirect(url_for("products"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Delete product database error:", error)

        return "Database error. Check the terminal."

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# SALES
# =========================

@app.route("/sales")
def sales():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                s.id,
                s.total_amount,
                s.created_at,
                c.name AS customer_name
            FROM sales s
            LEFT JOIN customers c
                ON s.customer_id = c.id
            ORDER BY s.id DESC
        """)

        sales_list = cursor.fetchall()

        return render_template(
            "sales.html",
            sales=sales_list
        )

    except mysql.connector.Error as error:

        print("Sales database error:", error)

        return render_template(
            "sales.html",
            sales=[]
        )

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# ADD SALE
# =========================

@app.route("/sales/add", methods=["GET", "POST"])
def add_sale():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":

            cursor.execute("""
                SELECT id, name
                FROM customers
                ORDER BY name
            """)

            customers_list = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    name,
                    selling_price,
                    stock
                FROM products
                WHERE stock > 0
                ORDER BY name
            """)

            products_list = cursor.fetchall()

            return render_template(
                "add_sale.html",
                customers=customers_list,
                products=products_list
            )

        customer_id = request.form.get("customer_id")
        product_id = request.form["product_id"]
        quantity = int(request.form["quantity"])

        cursor.execute("""
            SELECT
                id,
                selling_price,
                stock
            FROM products
            WHERE id = %s
        """, (product_id,))

        product = cursor.fetchone()

        if not product:
            return "Product not found.", 404

        if quantity <= 0:
            return "Quantity must be greater than zero.", 400

        if quantity > product["stock"]:
            return (
                f"Not enough stock. Available stock: "
                f"{product['stock']}"
            ), 400

        total_amount = product["selling_price"] * quantity

        cursor.execute("""
            INSERT INTO sales
            (
                customer_id,
                total_amount
            )
            VALUES (%s, %s)
        """, (
            customer_id if customer_id else None,
            total_amount
        ))

        sale_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO sale_items
            (
                sale_id,
                product_id,
                quantity,
                price
            )
            VALUES (%s, %s, %s, %s)
        """, (
            sale_id,
            product_id,
            quantity,
            product["selling_price"]
        ))

        cursor.execute("""
            UPDATE products
            SET stock = stock - %s
            WHERE id = %s
        """, (
            quantity,
            product_id
        ))

        connection.commit()

        print("Sale added successfully!")

        return redirect(url_for("sales"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Add sale database error:", error)

        return "Database error. Check the terminal."

    except ValueError:

        if connection:
            connection.rollback()

        return "Invalid quantity.", 400

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# CUSTOMERS
# =========================

@app.route("/customers")
def customers():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                name,
                phone
            FROM customers
            ORDER BY id DESC
        """)

        customer_list = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) AS total_customers
            FROM customers
        """)

        total_customers = cursor.fetchone()["total_customers"]

        return render_template(
            "customers.html",
            customers=customer_list,
            total_customers=total_customers
        )

    except mysql.connector.Error as error:

        print("Customers database error:", error)

        return render_template(
            "customers.html",
            customers=[],
            total_customers=0
        )

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# ADD CUSTOMER
# =========================

@app.route("/customers/add", methods=["GET", "POST"])
def add_customer():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        if request.method == "GET":

            return render_template(
                "add_customer.html"
            )

        name = request.form["name"].strip()
        phone = request.form["phone"].strip()

        if not name:
            return "Customer name is required.", 400

        cursor.execute("""
            INSERT INTO customers
            (
                name,
                phone
            )
            VALUES
            (%s, %s)
        """, (
            name,
            phone if phone else None
        ))

        connection.commit()

        print("Customer added successfully!")

        return redirect(url_for("customers"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Add customer database error:", error)

        return "Database error. Check the terminal."

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# EDIT CUSTOMER
# =========================

@app.route("/customers/edit/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":

            cursor.execute("""
                SELECT
                    id,
                    name,
                    phone
                FROM customers
                WHERE id = %s
            """, (customer_id,))

            customer = cursor.fetchone()

            if not customer:
                return "Customer not found.", 404

            return render_template(
                "edit_customer.html",
                customer=customer
            )

        name = request.form["name"].strip()
        phone = request.form["phone"].strip()

        if not name:
            return "Customer name is required.", 400

        cursor.execute("""
            UPDATE customers
            SET
                name = %s,
                phone = %s
            WHERE id = %s
        """, (
            name,
            phone if phone else None,
            customer_id
        ))

        connection.commit()

        print("Customer updated successfully!")

        return redirect(url_for("customers"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Edit customer database error:", error)

        return "Database error. Check the terminal."

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# DELETE CUSTOMER
# =========================

@app.route("/customers/delete/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            DELETE FROM customers
            WHERE id = %s
        """, (customer_id,))

        connection.commit()

        print("Customer deleted successfully!")

        return redirect(url_for("customers"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Delete customer database error:", error)

        if error.errno == 1451:
            return (
                "This customer cannot be deleted because "
                "sales records are linked to this customer."
            ), 400

        return "Database error. Check the terminal.", 500

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# PURCHASES
# =========================

@app.route("/purchases")
def purchases():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Purchase history
        cursor.execute("""
            SELECT
                p.id,
                p.quantity,
                p.purchase_price,
                p.total_amount,
                p.created_at,
                pr.name AS product_name
            FROM purchases p
            INNER JOIN products pr
                ON p.product_id = pr.id
            ORDER BY p.id DESC
        """)

        purchase_list = cursor.fetchall()

        # Purchase summary
        cursor.execute("""
            SELECT
                COUNT(*) AS total_purchases,
                COALESCE(SUM(quantity), 0) AS total_items_purchased,
                COALESCE(SUM(total_amount), 0) AS total_purchase_value
            FROM purchases
        """)

        summary = cursor.fetchone()

        return render_template(
            "purchases.html",
            purchases=purchase_list,
            total_purchases=summary["total_purchases"],
            total_items_purchased=summary["total_items_purchased"],
            total_purchase_value=summary["total_purchase_value"]
        )

    except mysql.connector.Error as error:

        print("Purchases database error:", error)

        return render_template(
            "purchases.html",
            purchases=[],
            total_purchases=0,
            total_items_purchased=0,
            total_purchase_value=0
        )

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# ADD PURCHASE
# =========================

@app.route("/purchases/add", methods=["GET", "POST"])
def add_purchase():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # SHOW ADD PURCHASE PAGE
        if request.method == "GET":

            cursor.execute("""
                SELECT
                    id,
                    name,
                    stock
                FROM products
                ORDER BY name
            """)

            product_list = cursor.fetchall()

            return render_template(
                "add_purchase.html",
                products=product_list
            )

        # GET FORM DATA
        product_id = request.form["product_id"]
        quantity = int(request.form["quantity"])

        purchase_price = float(
            request.form["purchase_price"]
        )

        # VALIDATION
        if quantity <= 0:
            return "Quantity must be greater than zero.", 400

        if purchase_price < 0:
            return "Purchase price cannot be negative.", 400

        # CHECK PRODUCT
        cursor.execute("""
            SELECT
                id,
                name,
                stock
            FROM products
            WHERE id = %s
        """, (product_id,))

        product = cursor.fetchone()

        if not product:
            return "Product not found.", 404

        # CALCULATE TOTAL
        total_amount = quantity * purchase_price

        # INSERT PURCHASE
        cursor.execute("""
            INSERT INTO purchases
            (
                product_id,
                quantity,
                purchase_price,
                total_amount
            )
            VALUES
            (%s, %s, %s, %s)
        """, (
            product_id,
            quantity,
            purchase_price,
            total_amount
        ))

        # INCREASE STOCK
        cursor.execute("""
            UPDATE products
            SET stock = stock + %s
            WHERE id = %s
        """, (
            quantity,
            product_id
        ))

        connection.commit()

        print("Purchase added successfully!")

        return redirect(url_for("purchases"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Add purchase database error:", error)

        return "Database error. Check the terminal.", 500

    except (ValueError, TypeError):

        if connection:
            connection.rollback()

        return "Invalid purchase details.", 400

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# DELETE PURCHASE
# =========================

@app.route("/purchases/delete/<int:purchase_id>", methods=["POST"])
def delete_purchase(purchase_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # FIND PURCHASE
        cursor.execute("""
            SELECT
                id,
                product_id,
                quantity
            FROM purchases
            WHERE id = %s
        """, (purchase_id,))

        purchase = cursor.fetchone()

        if not purchase:
            return "Purchase not found.", 404

        # CHECK CURRENT STOCK
        cursor.execute("""
            SELECT
                stock
            FROM products
            WHERE id = %s
        """, (purchase["product_id"],))

        product = cursor.fetchone()

        if not product:
            return "Product not found.", 404

        # Prevent stock from becoming negative
        if product["stock"] < purchase["quantity"]:
            return (
                "This purchase cannot be deleted because "
                "the current stock is lower than the purchased quantity."
            ), 400

        # REDUCE STOCK
        cursor.execute("""
            UPDATE products
            SET stock = stock - %s
            WHERE id = %s
        """, (
            purchase["quantity"],
            purchase["product_id"]
        ))

        # DELETE PURCHASE
        cursor.execute("""
            DELETE FROM purchases
            WHERE id = %s
        """, (purchase_id,))

        connection.commit()

        print("Purchase deleted successfully!")

        return redirect(url_for("purchases"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Delete purchase database error:", error)

        return "Database error. Check the terminal.", 500

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================
# ANALYTICS
# =========================

@app.route("/analytics")
def analytics():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Total sales
        cursor.execute("""
            SELECT COUNT(*) AS total_sales
            FROM sales
        """)

        total_sales = cursor.fetchone()["total_sales"]

        # Total revenue
        cursor.execute("""
            SELECT
                COALESCE(SUM(total_amount), 0) AS total_revenue
            FROM sales
        """)

        total_revenue = cursor.fetchone()["total_revenue"]

        # Low stock
        cursor.execute("""
            SELECT COUNT(*) AS low_stock
            FROM products
            WHERE stock <= reorder_level
        """)

        low_stock = cursor.fetchone()["low_stock"]

        # Last 90 days
        cursor.execute("""
            SELECT
                DATE(created_at) AS sale_date,
                COALESCE(SUM(total_amount), 0) AS daily_sales
            FROM sales
            WHERE DATE(created_at)
                >= CURDATE() - INTERVAL 89 DAY
            GROUP BY DATE(created_at)
            ORDER BY sale_date
        """)

        sales_rows = cursor.fetchall()

        sales_dict = {}

        for row in sales_rows:

            sale_date = row["sale_date"]

            sales_dict[sale_date] = float(
                row["daily_sales"] or 0
            )

        # Create 90 days
        sales_dates = []
        sales_values = []

        for i in range(89, -1, -1):

            current_date = date.today() - timedelta(days=i)

            sales_dates.append(
                current_date.strftime("%d %b")
            )

            sales_values.append(
                sales_dict.get(current_date, 0)
            )

        return render_template(
            "analytics.html",
            total_sales=total_sales,
            total_revenue=total_revenue,
            low_stock=low_stock,
            sales_dates=sales_dates,
            sales_values=sales_values
        )

    except mysql.connector.Error as error:

        print("Analytics database error:", error)

        return render_template(
            "analytics.html",
            total_sales=0,
            total_revenue=0,
            low_stock=0,
            sales_dates=[],
            sales_values=[]
        )

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
# =========================
# SETTINGS
# =========================

@app.route("/settings", methods=["GET", "POST"])
def settings():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # =========================
        # LOAD SETTINGS
        # =========================

        if request.method == "GET":

            cursor.execute("""
                SELECT
                    id,
                    store_name,
                    phone,
                    email,
                    address,
                    currency,
                    default_reorder_level,
                    low_stock_alert
                FROM settings
                WHERE id = 1
            """)

            settings_data = cursor.fetchone()

            # Create default settings if missing
            if not settings_data:

                cursor.execute("""
                    INSERT INTO settings
                    (
                        id,
                        store_name,
                        currency,
                        default_reorder_level,
                        low_stock_alert
                    )
                    VALUES
                    (1, 'InventoryIQ', '₹', 10, TRUE)
                """)

                connection.commit()

                cursor.execute("""
                    SELECT
                        id,
                        store_name,
                        phone,
                        email,
                        address,
                        currency,
                        default_reorder_level,
                        low_stock_alert
                    FROM settings
                    WHERE id = 1
                """)

                settings_data = cursor.fetchone()

            return render_template(
                "settings.html",
                settings=settings_data
            )

        # =========================
        # GET FORM DATA
        # =========================

        store_name = request.form.get(
            "store_name", ""
        ).strip()

        phone = request.form.get(
            "phone", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()

        address = request.form.get(
            "address", ""
        ).strip()

        currency = request.form.get(
            "currency", "₹"
        ).strip()

        reorder_level = request.form.get(
            "default_reorder_level", "10"
        )

        low_stock_alert = (
            1 if request.form.get("low_stock_alert")
            else 0
        )

        # =========================
        # VALIDATION
        # =========================

        if not store_name:
            return "Store name is required.", 400

        try:
            reorder_level = int(reorder_level)

        except ValueError:
            return "Invalid reorder level.", 400

        if reorder_level < 0:
            return "Reorder level cannot be negative.", 400

        if not currency:
            currency = "₹"

        # =========================
        # UPDATE SETTINGS
        # =========================

        cursor.execute("""
            UPDATE settings
            SET
                store_name = %s,
                phone = %s,
                email = %s,
                address = %s,
                currency = %s,
                default_reorder_level = %s,
                low_stock_alert = %s
            WHERE id = 1
        """, (
            store_name,
            phone if phone else None,
            email if email else None,
            address if address else None,
            currency,
            reorder_level,
            low_stock_alert
        ))

        connection.commit()

        return redirect(url_for("settings"))

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        print("Settings database error:", error)

        return "Database error. Check the terminal.", 500

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":
    app.run(debug=True)