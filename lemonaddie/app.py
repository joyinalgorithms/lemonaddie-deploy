from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, url_for, jsonify, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import random
import string
from datetime import datetime
import base64
import requests
import http.client
import json


app = Flask(__name__)
db = SQL("sqlite:///lemonaddie.db")


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@login_required
def index():
    if "user_id" not in session:
        return redirect(url_for("signup"))
    return render_template("home.html", username=session.get("username"))


@app.route("/search")
@login_required
def search():
    query = request.args.get("query", "").strip()

    products = db.execute(
        "SELECT productid, category, name, description, product_image, is_active FROM products WHERE name LIKE :query AND is_active = 1",
        query=f"%{query}%"
    )

    for product in products:
        default_price_query = db.execute("""
            SELECT price FROM product_variants
            WHERE productid = :productid AND variant_name = '16oz' OR product_variants.variant_name = 'Default'
        """, productid=product['productid'])

        product['default_price'] = default_price_query[0]['price'] if default_price_query else None

    return render_template("search_results.html", products=products, query=query)


@app.route("/aboutus")
@login_required
def aboutus():
    return render_template("aboutus.html", username=session.get("username"))


@app.route("/contactus")
@login_required
def contact():
    return render_template("contact.html", username=session.get("username"))


@app.route("/gallery")
@login_required
def gallery():
    return render_template("gallery.html", username=session.get("username"))


@app.route("/products")
@login_required
def products():
    best_sellers_products = db.execute("SELECT * FROM products WHERE description = 'Best sellers'")
    drinks_products = db.execute("SELECT * FROM products WHERE category = 'Drinks'")
    snacks_products = db.execute("SELECT * FROM products WHERE category = 'Snacks'")
    combo_products = db.execute("SELECT * FROM products WHERE category = 'Combo'")
    mixmatch_products = db.execute("SELECT * FROM products WHERE category = 'MixMatch'")

    for product in drinks_products:
        default_price = db.execute("""
            SELECT price FROM product_variants
            WHERE productid = :productid AND variant_name = '16oz'
        """, productid=product['productid'])
        product['default_price'] = default_price[0]['price'] if default_price else None

    for product in snacks_products:
        default_price = db.execute("""
            SELECT price FROM product_variants
            WHERE productid = :productid AND variant_name = 'Default'
        """, productid=product['productid'])
        product['default_price'] = default_price[0]['price'] if default_price else None

    for product in best_sellers_products:
        default_price = db.execute("""
            SELECT price FROM product_variants
            WHERE productid = :productid AND variant_name = '16oz'
        """, productid=product['productid'])
        product['default_price'] = default_price[0]['price'] if default_price else None

    for product in combo_products:
        default_price = db.execute("""
            SELECT price FROM product_variants
            WHERE productid = :productid AND variant_name = 'Default'
        """, productid=product['productid'])
        product['default_price'] = default_price[0]['price'] if default_price else None

    for product in mixmatch_products:
        default_price = db.execute("""
                SELECT price FROM product_variants
                WHERE productid = :productid AND variant_name = 'Default'
            """, productid=product['productid'])
        product['default_price'] = default_price[0]['price'] if default_price else None

    return render_template("products.html",
                           best_sellers_products=best_sellers_products,
                           drinks_products=drinks_products,
                           snacks_products=snacks_products,
                           combo_products=combo_products,
                           mixmatch_products=mixmatch_products,
                           username=session.get("username"))


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' in session:
        customer_id = int(session['user_id'])
    else:
        return redirect('/login')

    product_id = int(request.form.get('product_id'))
    quantity = request.form.get('quantity')
    session_id = session.sid

    quantity = int(quantity) if quantity else 1

    if quantity <= 0:
        return redirect('/cart')

    try:
        existing_cart_item = db.execute("""
            SELECT quantity FROM cart
            WHERE customerid = ? AND productid = ? AND sessionid = ?
        """, customer_id, product_id, session_id)

        if existing_cart_item:
            existing_cart_item = existing_cart_item[0]

        if existing_cart_item:
            new_quantity = existing_cart_item['quantity'] + quantity
            db.execute("""
                UPDATE cart
                SET quantity = ?
                WHERE customerid = ? AND productid = ? AND sessionid = ?
            """, new_quantity, customer_id, product_id, session_id)
        else:
            db.execute("""
                INSERT INTO cart (customerid, productid, quantity, sessionid)
                VALUES (?, ?, ?, ?)
            """, customer_id, product_id, quantity, session_id)
    except Exception as e:
        print(f"Error handling cart operation: {e}")
        return "Error processing your request", 500

    return redirect('/products')


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect('/login')

    customer_id = session['user_id']

    cart_items_query = """
        SELECT
            cart.productid,
            cart.quantity,
            cart.sessionid,
            products.name,
            products.product_image,
            products.description,
            product_variants.variantid,
            product_variants.variant_name,
            product_variants.price
        FROM cart
        JOIN products ON cart.productid = products.productid
        LEFT JOIN product_variants ON products.productid = product_variants.productid
        WHERE cart.customerid = ?
    """

    rows = db.execute(cart_items_query, (customer_id,))

    cart_items = {}
    for row in rows:
        product_id = row['productid']
        if product_id not in cart_items:
            cart_items[product_id] = {
                'productid': product_id,
                'quantity': row['quantity'],
                'sessionid': row['sessionid'],
                'name': row['name'],
                'product_image': row['product_image'],
                'description': row['description'],
                'variants': []
            }
        if row['variantid'] and row['variant_name']:
            cart_items[product_id]['variants'].append({
                'variantid': row['variantid'],
                'variant_name': row['variant_name'],
                'price': row['price']
            })

    total_cost_of_items = sum(
        item['quantity'] * (item['variants'][0]['price'] if item['variants'] else 0)
        for item in cart_items.values()
    ) if cart_items else 0
    delivery_fee = 10.00
    order_total = total_cost_of_items + delivery_fee

    return render_template(
        'orders.html',
        cart_items=cart_items.values(),
        username=session.get("username"),
        cart_count=sum(item['quantity'] for item in cart_items.values()),
        total_cost_of_items=total_cost_of_items,
        delivery_fee=delivery_fee,
        order_total=order_total
    )


@app.route('/get_cart_totals', methods=['POST'])
def get_cart_totals():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    customer_id = session['user_id']

    cart_items_query = """
        SELECT
            cart.productid,
            cart.quantity,
            product_variants.price
        FROM cart
        LEFT JOIN product_variants ON cart.productid = product_variants.productid
        WHERE cart.customerid = ?
    """
    rows = db.execute(cart_items_query, (customer_id,))

    total_cost_of_items = sum(
        row['quantity'] * (row['price'] if row['price'] else 0)
        for row in rows
    ) if rows else 0
    delivery_fee = 10.00
    order_total = total_cost_of_items + delivery_fee

    return jsonify({
        'total_cost_of_items': total_cost_of_items,
        'order_total': order_total
    })


@app.route('/delete_from_cart', methods=['POST'])
def delete_from_cart():
    if 'user_id' in session:
        customer_id = session['user_id']
    else:
        return redirect('/login')

    product_id = request.form.get('product_id')
    session_id = request.form.get('session_id')

    try:
        db.execute("""
            DELETE FROM cart
            WHERE customerid = :customer_id AND productid = :product_id AND sessionid = :session_id
        """, customer_id=customer_id, product_id=product_id, session_id=session_id)
    except Exception as e:
        print(f"Error deleting item from cart: {e}")
        return "Error processing your request", 500

    return redirect('/cart')


def get_cart_count():
    if 'user_id' not in session:
        return 0

    customer_id = session['user_id']
    cart_count = db.execute("""
        SELECT SUM(quantity) AS total_quantity
        FROM cart
        WHERE customerid = :customer_id
    """, customer_id=customer_id)

    return cart_count[0]['total_quantity'] if cart_count and cart_count[0]['total_quantity'] else 0


@app.context_processor
def inject_cart_count():
    cart_count = get_cart_count()
    return dict(cart_count=cart_count)


@app.route('/get_price', methods=['POST'])
def get_price():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        size = data.get('size')

        if not product_id or not size:
            return jsonify({'error': 'Missing product_id or size'}), 400

        print(f"Received product_id: {product_id}, size: {size}")

        query = '''
            SELECT price
            FROM product_variants
            WHERE productid = ? AND variant_name = ?
        '''
        results = db.execute(query, product_id, size)

        if not results:
            return jsonify({'error': 'Price not found'}), 404

        price = results[0]['price']
        print(price)
        return jsonify({'price': price})

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500


@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'Invalid input'}), 400

        order_items = data.get('order_items', [])
        delivery_address = data.get('delivery_address', '').strip()
        delivery_date = data.get('delivery_date', '').strip()
        order_notes = data.get('order_notes', '').strip()

        customer_id = session.get('user_id')
        if not customer_id:
            return jsonify({'success': False, 'message': 'User not logged in'}), 401

        session_id = session.sid
        tracking_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        if not order_items:
            return jsonify({'success': False, 'message': 'No order items provided'}), 400
        if not delivery_address:
            return jsonify({'success': False, 'message': 'Delivery address is required'}), 400
        if not delivery_date:
            return jsonify({'success': False, 'message': 'Delivery date is required'}), 400

        order_id = db.execute("""
            INSERT INTO orders (
                customerid, orderdate, deliverydate, totalamount, status,
                order_tracking_id, delivery_address, order_notes, confirmation_date
            )
            VALUES (?, CURRENT_TIMESTAMP, ?, 0, 'pending', ?, ?, ?, CURRENT_TIMESTAMP)
        """, customer_id, delivery_date, tracking_id, delivery_address, order_notes)

        total_amount = 0
        for item in order_items:
            product_id = item.get('product_id')
            size = item.get('size')
            quantity = item.get('quantity', 1)
            add_on = item.get('add_on', '')
            add_on_price = item.get('add_on_price', 0.0)

            variant = db.execute("""
                SELECT variantid, price
                FROM product_variants
                WHERE productid = ? AND variant_name = ?
            """, product_id, size)

            if not variant:
                return jsonify({'success': False, 'message': f"Invalid variant for product {product_id}"}), 400

            variant_id = variant[0]['variantid']
            unit_price = variant[0]['price']

            subtotal = (unit_price + add_on_price) * quantity
            total_amount += subtotal

            db.execute("""
                    INSERT INTO orderdetails (
                        orderid, productid, variantid, quantity, unitprice, addson, subtotal, add_on_price
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, order_id, product_id, variant_id, quantity, unit_price, add_on, subtotal, add_on_price)

        delivery_fee = 10
        total_amount += delivery_fee
        db.execute("""
            UPDATE orders
            SET totalamount = ?
            WHERE orderid = ?
        """, total_amount, order_id)

        db.execute("""
            DELETE FROM cart
            WHERE customerid = ? AND sessionid = ?
        """, customer_id, session_id)

        return jsonify({'success': True, 'message': 'Order placed successfully', 'order_id': order_id})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500


@app.route("/termsconditions")
@login_required
def terms():
    return render_template("terms.html", username=session.get("username"))


@app.route("/privacynotice")
@login_required
def privacy():
    return render_template("privacy.html", username=session.get("username"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        username = request.form.get("username")
        email = request.form.get("email")
        address = request.form.get("address")
        phone_number = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm-password")

        if password != confirm_password:
            error_message = "Passwords do not match!"
            return render_template("signup.html", error_message=error_message)

        hashedpassword = generate_password_hash(password)

        try:
            db.execute("""
                INSERT INTO customers (firstname, lastname, username, email, hashedpassword, address, phone_number)
                VALUES (:firstname, :lastname, :username, :email, :hashedpassword, :address, :phone_number)
            """, firstname=firstname, lastname=lastname, username=username, email=email,
                       hashedpassword=hashedpassword, address=address, phone_number=phone_number)

            return redirect(url_for('login'))
        except Exception as e:
            error_message = "Username or email already exists!"
            return render_template("signup.html", error_message=error_message)

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = db.execute("SELECT * FROM customers WHERE username = :username", username=username)

        if len(user) != 1 or not check_password_hash(user[0]["hashedpassword"], password):
            error_message = "Invalid username or password."
            return render_template("login.html", error_message=error_message)

        session["user_id"] = user[0]["customerid"]
        session["username"] = user[0]["username"]
        print(session)
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/reviews")
def reviews():
    return render_template("reviews.html")


@app.route("/submit_review", methods=["POST"])
@login_required
def submit_review():
    """Handle review submissions."""
    if request.method == "POST":
        feedback = request.form.get("feedback").strip()
        customer_id = session["user_id"]

        if not feedback:
            return jsonify({"error": "Feedback cannot be empty"}), 400

        try:
            db.execute("""
                INSERT INTO reviews (customerid, feedback)
                VALUES (?, ?)
            """, customer_id, feedback)
            return redirect(url_for("index"))
        except Exception as e:
            print(f"Error inserting review: {e}")
            return jsonify({"error": "An error occurred while saving your review"}), 500


@app.route("/forgotpwd")
def forgotpwd():
    return render_template("forgotpwd.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/adminlog", methods=["GET", "POST"])
def adminlog():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin = db.execute("SELECT * FROM admin WHERE username = :username", username=username)

        if admin and check_password_hash(admin[0]['password'], password):
            session['admin_logged_in'] = True
            session['admin_username'] = admin[0]['username']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('adminlog.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('adminlog'))
    return render_template('admin.html')


@app.route('/api/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_products():
    if request.method == 'GET':
        products = db.execute("SELECT * FROM products")
        return jsonify(products)
    elif request.method == 'POST':
        data = request.json
        db.execute("INSERT INTO products (name, category, description, product_image) VALUES (?, ?, ?, ?)",
                   data['name'], data['category'], data['description'], data['product_image'])
        return jsonify({'success': True})
    elif request.method == 'PUT':
        data = request.json
        db.execute("UPDATE products SET name = ?, category = ?, description = ?, product_image = ? WHERE productid = ?",
                   data['name'], data['category'], data['description'], data['product_image'], data['productid'])
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        productid = request.json['productid']
        db.execute("DELETE FROM products WHERE productid = ?", productid)
        return jsonify({'success': True})


@app.route('/api/employees', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_employees():
    if request.method == 'GET':
        employees = db.execute("""
            SELECT employeeid, firstname, lastname, username, email, address, phone_number
            FROM employees
        """)
        return jsonify(employees)

    elif request.method == 'POST':
        data = request.json
        try:
            db.execute("""
                INSERT INTO employees (firstname, lastname, username, email, hashedpassword, address, phone_number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                       data['firstname'], data['lastname'], data['username'], data['email'],
                       generate_password_hash(data['hashedpassword']), data['address'], data['phone_number'])
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error adding employee: {e}")
            return jsonify({'success': False, 'error': str(e)})

    elif request.method == 'PUT':
        data = request.json
        try:
            db.execute("""
                UPDATE employees
                SET firstname = ?, lastname = ?, username = ?, email = ?, address = ?, phone_number = ?
                WHERE employeeid = ?
            """,
                       data['firstname'], data['lastname'], data['username'], data['email'],
                       data['address'], data['phone_number'], data['employeeid'])
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error updating employee: {e}")
            return jsonify({'success': False, 'error': str(e)})

    elif request.method == 'DELETE':
        employeeid = request.json['employeeid']
        try:
            db.execute("DELETE FROM employees WHERE employeeid = ?", employeeid)
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error deleting employee: {e}")
            return jsonify({'success': False, 'error': str(e)})


@app.route('/api/reviews', methods=['GET', 'DELETE'])
def manage_reviews():
    if request.method == 'GET':
        reviews = db.execute("SELECT reviewid, customerid, feedback FROM reviews")
        return jsonify(reviews)
    elif request.method == 'DELETE':
        review_id = request.json['reviewid']
        db.execute("DELETE FROM reviews WHERE reviewid = ?", review_id)
        return jsonify({'success': True})


@app.route("/api/orders")
def get_orders():
    orders = db.execute("""
        SELECT
            o.orderid, o.orderdate, o.totalamount, o.delivery_address,
            o.order_notes, o.status, od.productid, od.variantid,
            od.quantity, od.unitprice, od.addson, od.subtotal,
            p.name AS product_name, pv.variant_name
        FROM orders o
        JOIN orderdetails od ON o.orderid = od.orderid
        JOIN products p ON od.productid = p.productid
        LEFT JOIN product_variants pv ON od.variantid = pv.variantid
        WHERE o.status = 'pending'  -- Filter only Pending orders
        ORDER BY o.orderdate DESC
    """)
    grouped_orders = {}
    for order in orders:
        orderid = order["orderid"]
        if orderid not in grouped_orders:
            grouped_orders[orderid] = {
                "orderid": orderid,
                "orderdate": order["orderdate"],
                "totalamount": order["totalamount"],
                "delivery_address": order["delivery_address"],
                "order_notes": order["order_notes"],
                "status": order["status"],
                "products": []
            }
        grouped_orders[orderid]["products"].append({
            "name": order["product_name"],
            "quantity": order["quantity"],
            "variant_name": order["variant_name"],
            "addons": order["addson"],
            "subtotal": order["subtotal"]
        })

    return jsonify(list(grouped_orders.values()))


@app.route("/api/orders/<int:order_id>/complete", methods=["POST"])
def complete_order(order_id):
    try:
        print(f"Attempting to mark order {order_id} as completed.")

        existing_order = db.execute("SELECT 1 FROM orders WHERE orderid = ?", order_id)
        if not existing_order:
            return jsonify({"message": "Order not found"}), 404

        result = db.execute("UPDATE orders SET status = 'completed' WHERE orderid = ?", order_id)

        print(f"Rows affected: {result}")

        if result == 0:
            return jsonify({"message": "Order not found"}), 404

        return jsonify({"message": "Order marked as completed"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "An error occurred", "error": str(e)}), 500
