import os
from dotenv import load_dotenv
from flask import Flask, render_template, session, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
logging.basicConfig(level=logging.DEBUG)


# admin)checks if user is logged in & Checks if user is logged in)
ADMIN_EMAIL = "      "  #enter your own email---

def is_admin():
    if "user_id" not in session:
        return False
    user = User.query.get(session["user_id"])
    return user and user.email == ADMIN_EMAIL


app = Flask(__name__)
app.secret_key = "      "  #enter your own secret---





app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://fooduser:  /    " #enter your own file locstion-----
)


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# MODELS

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime)



class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer)

    product = db.relationship("Product")


# class Product(db.Model):
#     __tablename__ = "products"

#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     price = db.Column(db.Integer)
#     image = db.Column(db.String(255))


class Orders(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    total = db.Column(db.Integer)
    total_amount = db.Column(db.Integer)
    status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='orders')


class OrderItems(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Integer)

    product = db.relationship("Product")

# product
class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    image = db.Column(db.String(255))


    category = db.Column(db.String(50))   # rice, bread, salad, dessert
    type = db.Column(db.String(10))        # veg - non-veg



# ROUTES


@app.route("/")
def index():
    category = request.args.get("category")
    food_type = request.args.get("type")
    print("Category:", category)
    query = Product.query
    if category:
        query = query.filter(Product.category == category)

    if food_type:
        query = query.filter_by(type=food_type)

    products = query.all()
    print("Products count:", len(products))
    return render_template("index.html", products=products)





# ADMIN
# admin dashboard
@app.route("/admin")
def admin_dashboard():
    if not is_admin():
        return "Access Denied", 403

    return render_template("admin/dashboard.html")

# admin-view all users
@app.route("/admin/users")
def admin_users():
    if not is_admin():
        return "Access Denied", 403

    users = User.query.all()
    return render_template("admin/users.html", users=users)


# admin-view all orders
@app.route("/admin/orders")
def admin_orders():
    if not is_admin():
        return "Access Denied", 403

    orders = Orders.query.order_by(Orders.id.desc()).all()
    return render_template("admin/orders.html", orders=orders)

# admin-view order details
@app.route("/admin/orders/<int:order_id>")
def admin_order_detail(order_id):
    if not is_admin():
        return "Access Denied", 403

    order = Orders.query.get_or_404(order_id)
    items = OrderItems.query.filter_by(order_id=order_id).all()

    return render_template(
        "admin/order_detail.html",
        order=order,
        items=items
    )


# Profile
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        user.phone = request.form.get("phone")
        user.address = request.form.get("address")
        db.session.commit()   # ✅ VERY IMPORTANT

        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)







# ADD TO CART (DB)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if "user_id" not in session:
        return {"status": "not_logged_in"}

    data = request.get_json()

    item = CartItem.query.filter_by(
        user_id=session["user_id"],
        product_id=data["product_id"]
    ).first()

    if item:
        item.quantity += data["qty"]
    else:
        item = CartItem(
            user_id=session["user_id"],
            product_id=data["product_id"],
            quantity=data["qty"]
        )
        db.session.add(item)

    db.session.commit()
    return {"status": "success"}



@app.route("/api/cart/increase", methods=["POST"])
def api_cart_increase():
    if "user_id" not in session:
        return {"error": "not_logged_in"}, 401

    data = request.get_json()
    item_id = data.get("item_id")

    item = CartItem.query.get(item_id)

    if not item or item.user_id != session["user_id"]:
        return {"error": "invalid_item"}, 400

    # Increase quantity
    item.quantity += 1
    db.session.commit()
     # Calculate item total (AFTER increment
    item_total = item.product.price * item.quantity
    # Recalculate total
    cart_items = CartItem.query.filter_by(user_id=session["user_id"]).all()
    total = sum(ci.product.price * ci.quantity for ci in cart_items)

    return {
        "quantity": item.quantity,
        "item_total": item_total,
        "total": total
    }


@app.route("/api/cart/decrease", methods=["POST"])
def api_cart_decrease():
    if "user_id" not in session:
        return {"error": "not_logged_in"}, 401

    data = request.get_json()
    item_id = data.get("item_id")

    item = CartItem.query.get(item_id)

    if not item or item.user_id != session["user_id"]:
        return {"error": "invalid_item"}, 400

    if item.quantity > 1:
        item.quantity -= 1
        db.session.commit()
    # Calculate item total (AFTER decrement)
    item_total = item.product.price * item.quantity

    # Recalculate total
    cart_items = CartItem.query.filter_by(user_id=session["user_id"]).all()
    total = sum(ci.product.price * ci.quantity for ci in cart_items)

    return {
        "quantity": item.quantity,
        "item_total": item_total,
        "total": total
    }






# VIEW CART


@app.route('/cart')
def cart():
    if "user_id" not in session:
        return redirect(url_for('login'))

    items = CartItem.query.filter_by(user_id=session["user_id"]).all()
    total = sum(item.product.price * item.quantity for item in items)

    return render_template('cart.html', cart=items, total=total)



# check-out


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if "user_id" not in session:
        return redirect(url_for('login'))

    # Get cart items
    items = CartItem.query.filter_by(user_id=session["user_id"]).all()
    total = sum(item.product.price * item.quantity for item in items)

    # ✅ NEW: get user for profile auto-fill
    user = User.query.get(session["user_id"])

    if request.method == 'POST':
        # 1. Create order
        new_order = Orders(
            user_id=session["user_id"],
            total=total
        )
        db.session.add(new_order)
        db.session.commit()  # needed to get order id

        # 2. Create order items
        for item in items:
            order_item = OrderItems(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_item)

        # 3. Clear cart
        CartItem.query.filter_by(user_id=session["user_id"]).delete()
        db.session.commit()

        # 4. Redirect to success page
        return redirect(url_for('order_success', order_id=new_order.id))

    # ✅ NEW: pass user to template
    return render_template(
        'checkout.html',
        cart=items,
        total=total,
        user=user
    )



# success pagr

@app.route('/order_success/<int:order_id>')
def order_success(order_id):
    return render_template('order_success.html', order_id=order_id)




# INCREASE QTY

@app.route('/increase_qty/<int:item_id>')
def increase_qty(item_id):
    item = CartItem.query.get(item_id)

    if item and item.user_id == session.get("user_id"):
        item.quantity += 1
        db.session.commit()

    return redirect(url_for('cart'))

# DECREASE QTY

@app.route('/decrease_qty/<int:item_id>')
def decrease_qty(item_id):
    item = CartItem.query.get(item_id)

    if item and item.user_id == session.get("user_id") and item.quantity > 1:
        item.quantity -= 1
        db.session.commit()

    return redirect(url_for('cart'))

# add to cart auto
@app.route("/api/cart/set_qty", methods=["POST"])
def api_cart_set_qty():
    if "user_id" not in session:
        return {"status": "not_logged_in"}

    data = request.get_json()
    product_id = data.get("product_id")
    qty = data.get("qty")

    item = CartItem.query.filter_by(
        user_id=session["user_id"],
        product_id=product_id
    ).first()

    # If item exists → update quantity
    if item:
        item.quantity = qty
        db.session.commit()
        return {"status": "updated", "qty": qty}

    # If item does NOT exist → create entry
    else:
        new_item = CartItem(
            user_id=session["user_id"],
            product_id=product_id,
            quantity=qty
        )
        db.session.add(new_item)
        db.session.commit()
        return {"status": "added", "qty": qty}




# ajax for delete of product in the cart

@app.route("/api/cart/delete", methods=["POST"])
def api_cart_delete():
    if "user_id" not in session:
        return {"error": "not_logged_in"}, 401

    data = request.get_json()
    item_id = data.get("item_id")

    item = CartItem.query.get(item_id)

    if not item or item.user_id != session["user_id"]:
        return {"error": "invalid_item"}, 400

    db.session.delete(item)
    db.session.commit()

    # Recalculate total
    cart_items = CartItem.query.filter_by(user_id=session["user_id"]).all()
    total = sum(ci.product.price * ci.quantity for ci in cart_items)

    return {
        "status": "deleted",
        "total": total
    }



# DELETE SINGLE ITEM

@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    item = CartItem.query.get(item_id)

    if item and item.user_id == session.get("user_id"):
        db.session.delete(item)
        db.session.commit()

    return redirect(url_for('cart'))


# CLEAR CART

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    CartItem.query.filter_by(user_id=session["user_id"]).delete()
    db.session.commit()
    return redirect(url_for('cart'))


# product

@app.route('/add_products')
def add_products():
    products = [
        ("Cheese Burger", 159, "products/burger.png"),
        ("Pepperoni Pizza", 199, "products/pizza.png"),
        ("Chicken Biryani", 299, "products/biryani.png"),
        ("White Sauce Pasta", 149, "products/white_pasta.png"),
        ("French Fries", 89, "products/fries.png"),
        ("Chicken Shawarma", 179, "products/shawarma.png"),
        ("Veg Sandwich", 99, "products/sandwich.png"),
        ("Gulab Jamun", 59, "products/gulab_jamun.png"),
        ("Vanilla Ice Cream", 79, "products/ice_cream.png"),
        ("Veg Noodles", 129, "products/noodles.png"),
        ("Green Salad", 99, "products/salad.png"),
        ("Chicken Wings", 249, "products/chicken_wings.png"),
    ]

    for name, price, image in products:
        exists = Product.query.filter_by(name=name).first()
        if not exists:
            db.session.add(Product(name=name, price=price, image=image))

    db.session.commit()
    return "All products added!"


# my order
@app.route('/orders')
def my_orders():
    if "user_id" not in session:
        return redirect(url_for('login'))

    orders = Orders.query.filter_by(user_id=session["user_id"]).order_by(Orders.id.desc()).all()
    return render_template('orders.html', orders=orders)


# order popup

@app.route("/api/order_items", methods=["POST"])
def api_order_items():
    if "user_id" not in session:
        return {"error": "not_logged_in"}

    data = request.get_json()
    order_id = data.get("order_id")

    order = Orders.query.get(order_id)

    # security: prevent access to other users' orders
    if not order or order.user_id != session["user_id"]:
        return {"error": "unauthorized"}

    items = OrderItems.query.filter_by(order_id=order_id).all()

    return {
        "items": [
            {
                "name": i.product.name,
                "qty": i.quantity
            }
            for i in items
        ]
    }




# Order Details
@app.route('/order/<int:order_id>')
def order_details(order_id):
    if "user_id" not in session:
        return redirect(url_for('login'))

    order = Orders.query.get(order_id)

    if not order or order.user_id != session["user_id"]:
        return "Unauthorized Access"

    items = OrderItems.query.filter_by(order_id=order_id).all()

    return render_template('order_details.html', order=order, items=items)


# SIGNUP

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            return "Passwords do not match"

        if User.query.filter_by(email=email).first():
            return "Email already exists"

        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('signup.html')


# LOGIN

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if not user or user.password != password:
            return "Invalid credentials"

        session['user_id'] = user.id
        session['user_name'] = user.name
        return redirect(url_for('index'))

    return render_template('login.html')


# LOGOUT

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# RUN APP

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)

