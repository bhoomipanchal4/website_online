from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
import sqlite3
from functools import wraps
import stripe
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash

load_dotenv()
stripe.api_key = os.environ.get("SECRET_KEY")

app = Flask(__name__)

@app.after_request   #if you try to back your browser it will prevent back-cache means not log-in after log-out.
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


app.secret_key = os.environ.get("APP_SECRET_KEY")
app.config["UPLOAD_FOLDER"] = "static/images"

conn = sqlite3.connect("store.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    image TEXT NOT NULL,
    description TEXT,
    has_size BOOLEAN DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")



conn.commit()
conn.close()


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/product")
def product():

    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")

    products = cursor.fetchall()

    conn.close()

    return render_template(
        "products.html",
        products=products
    )

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        subject = request.form["subject"]
        message = request.form["message"]

        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO contact_messages
            (name, email, subject, message)
            VALUES (?, ?, ?, ?)
        """, (name, email, subject, message))

        conn.commit()
        conn.close()

        return render_template(
            "contact.html",
            success="Your message has been sent successfully!"
        )

    return render_template("contact.html")

@app.route("/account")
def account():
    return render_template("account.html")

@app.route("/cart")
def cart():
    return render_template("cart.html")

@app.route("/checkout")
def check_out():
    return render_template("checkout.html")

@app.route("/payment")
def payment():
    return render_template("payment.html")


@app.route("/product-details")
def product_details():

    product_id = request.args.get("id")

    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE id=?",
        (product_id,)
    )

    product = cursor.fetchone()

    conn.close()

    return render_template(
        "product-details.html",
        product=product
    )

@app.route("/order-confirmation")
def order_confirmation():
    return render_template("order-confirmation.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # Temporary admin credentials
        if username == "admin" and password == "12345":

            session["admin_logged_in"] = True

            return redirect(url_for("admin_dashboard"))

        else:

            return render_template(
                "admin_login.html",
                error="Invalid username or password"
            )

    return render_template("admin_login.html")


def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return f(*args, **kwargs)

    return decorated_function


@app.route("/admin")
@admin_required
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    return render_template("admin_dashboard.html")


@app.route("/admin/products")
@admin_required
def admin_products():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")

    products = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_products.html",
        products=products
    )
@app.route("/admin/add-product", methods=["GET", "POST"])
@admin_required
def add_product():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))


    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]

        image = request.files["image"]


        filename = secure_filename(image.filename)

        image.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )


        has_size = 1 if "has_size" in request.form else 0


        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()


        cursor.execute("""
            INSERT INTO products
            (name, price, image, description, has_size)
            VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            price,
            "images/" + filename,
            description,
            has_size
        ))


        conn.commit()
        conn.close()


        return redirect(url_for("admin_products"))


    return render_template("add_product.html")

@app.route("/admin/logout")
@admin_required
def admin_logout():

    session.clear()

    return redirect(url_for("admin_login"))

@app.route("/admin/messages")
@admin_required
def admin_messages():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM contact_messages
        ORDER BY created_at DESC
    """)

    messages = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_messages.html",
        messages=messages
    )

@app.route("/admin/edit_product.html-product/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_product(id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))


    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()


    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        image = request.form["image"]
        description = request.form["description"]

        has_size = 1 if "has_size" in request.form else 0


        cursor.execute("""
            UPDATE products
            SET name=?,
                price=?,
                image=?,
                description=?,
                has_size=?
            WHERE id=?
        """,
        (
            name,
            price,
            image,
            description,
            has_size,
            id
        ))


        conn.commit()
        conn.close()

        return redirect(url_for("admin_products"))



    cursor.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    )

    product = cursor.fetchone()

    conn.close()


    return render_template(
        "edit_product.html",
        product=product
    )



@app.route("/admin/delete-product/<int:id>")
@admin_required
def delete_product(id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))


    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()


    cursor.execute(
        "DELETE FROM products WHERE id=?",
        (id,)
    )


    conn.commit()
    conn.close()


    return redirect(url_for("admin_products"))



@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():

    data = request.get_json()

    cart = data.get("cart", [])

    line_items = []


    for item in cart:

        line_items.append({

            "price_data": {

                "currency": "cad",

                "product_data": {

                    "name": item["name"]

                },

                # Stripe uses cents

                "unit_amount": int(item["price"] * 100)

            },

            "quantity": item["quantity"]

        })


    session = stripe.checkout.Session.create(

        payment_method_types=["card"],

        mode="payment",

        line_items=line_items,

        success_url=url_for("success", _external=True),
        cancel_url=url_for("payment", _external=True)

    )


    return jsonify({

        "url": session.url

    })

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/cancel")
def cancel():
    return "Payment Cancelled!"


@app.route("/register", methods=["POST"])
def register():

    username = request.form["username"]
    email = request.form["email"]
    password = generate_password_hash(request.form["password"])


    conn = sqlite3.connect("store.db")

    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO users (username, email, password)
            VALUES (?, ?, ?)
            """,
            (username, email, password)
        )

        conn.commit()

        session["username"] = username

        return redirect("/")


    except sqlite3.IntegrityError:

        flash("Email already registered. Please use another email.")

        return redirect("/account")


    finally:

        conn.close()

@app.route("/login", methods=["POST"])
def login():

    email = request.form["username"]
    password = request.form["password"]


    conn = sqlite3.connect("store.db")

    cursor = conn.cursor()


    cursor.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    )

    user = cursor.fetchone()

    conn.close()


    if user and check_password_hash(user[3], password):

        session["user_id"] = user[0]
        session["username"] = user[1]

        return redirect("/")


    else:

        return "Invalid email or password"

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


if __name__=="__main__":
    app.run(debug=True)