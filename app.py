from flask import Flask, g, render_template, request, redirect, session 
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

DATABASE = 'pc_parts.db'

app = Flask(__name__)
app.secret_key = "sdjkhf8374hf83hf83hf"

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.before_request
def setup_build():
    if "build" not in session:
        session["build"] = []

@app.route('/')
def home():

    category = request.args.get('category')
    search = request.args.get('search')

    sql = "SELECT * FROM Parts WHERE 1=1"
    values = []

    # Category filter
    if category:
        sql += " AND Category = ?"
        values.append(category)

    # Search filter
    if search:
        sql += " AND Part_Name LIKE ?"
        values.append("%" + search + "%")

    parts = query_db(sql, values)

    build_ids = session.get("build", [])

    build_parts = []
    total = 0

    if build_ids:
        placeholders = ",".join(["?"] * len(build_ids))

        build_parts = query_db(
            f"SELECT * FROM Parts WHERE Part_ID IN ({placeholders})",
            build_ids
        )

        total = sum(p["Price"] for p in build_parts)

    return render_template(
        "home.html",
        parts=parts,
        build_parts=build_parts,
        total=total
    )

@app.route("/part/<int:id>")
def part(id):
    sql = """
        SELECT *
        FROM Parts
        WHERE Part_ID = ?;
    """
    result = query_db(sql, (id,), True)
    return render_template("part.html", part=result)

@app.route("/add/<int:id>")
def add_part(id):

    part = query_db(
        "SELECT * FROM Parts WHERE Part_ID = ?",
        (id,),
        one=True
    )

    if not part:
        return "Part not found"

    build = session.get("build", [])

    existing_parts = []

    if build:
        placeholders = ",".join(["?"] * len(build))
        existing_parts = query_db(
            f"SELECT * FROM Parts WHERE Part_ID IN ({placeholders})",
            build
        )

    single_categories = ["CPU", "GPU", "Motherboard", "PSU"]

    for p in existing_parts:
        if p["Category"] == part["Category"] and part["Category"] in single_categories:
            return "You already added one of this category"

    build.append(id)
    session["build"] = build

    return redirect("/")


@app.route("/remove/<int:id>")
def remove_part(id):
    build = session.get("build", [])
    if id in build:
        build.remove(id)
    session["build"] = build
    return redirect("/")

@app.route("/reset")
def reset():
    session.pop("build", None)
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        db = get_db()

        existing_user = query_db(
            "SELECT * FROM Users WHERE Username = ? OR Email = ?",
            (username, email),
            one=True
        )

        if existing_user:
            return "Username or Email already taken"

        db.execute(
            "INSERT INTO Users (Username, Email, Password) VALUES (?, ?, ?)",
            (username, email, password)
        )
        db.commit()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = query_db("SELECT * FROM Users WHERE Username = ?", (username,), one=True)
        if user and check_password_hash(user["Password"], password):
            session["user_id"] = user["User_ID"]
            session["username"] = user["Username"]
            return redirect("/")
        else:
            return "Invalid login"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    builds = query_db(
        "SELECT * FROM Builds WHERE User_ID = ?",
        (session["user_id"],)
    )

    return render_template("dashboard.html", builds=builds, username=session["username"])

@app.route("/save_build")
def save_build():
    if "user_id" not in session:
        return redirect("/login")

    build_ids = session.get("build", [])

    if not build_ids:
        return "No build to save"

    placeholders = ",".join(["?"] * len(build_ids))

    parts = query_db(
        f"SELECT * FROM Parts WHERE Part_ID IN ({placeholders})",
        build_ids
    )

    total = sum(p["Price"] for p in parts)

    db = get_db()

    # Create build
    cur = db.execute(
        "INSERT INTO Builds (User_ID, Total_Cost) VALUES (?, ?)",
        (session["user_id"], total)
    )
    build_id = cur.lastrowid

    # Insert parts into BuildParts
    for part_id in build_ids:
        db.execute(
            "INSERT INTO BuildParts (Build_ID, Part_ID) VALUES (?, ?)",
            (build_id, part_id)
        )

    db.commit()
    session["build"] = []

    return redirect("/dashboard")

@app.route("/builds")
def builds():
    results = query_db("""
        SELECT Builds.Build_ID, Users.Username, Builds.Total_Cost
        FROM Builds
        JOIN Users ON Users.User_ID = Builds.User_ID
    """)
    
    return render_template("builds.html", results=results)


# ALWAYS LAST
if __name__ == '__main__':
    app.run(debug=True)