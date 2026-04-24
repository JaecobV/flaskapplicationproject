from flask import Flask, g, render_template, request, redirect, session
import sqlite3

DATABASE = 'pc_parts.db'

app = Flask(__name__)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # allows column names
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def home():
    parts = query_db("SELECT * FROM Parts")


    build_ids = session.get("build", [])


    build_parts = []
    total = 0


    if build_ids:
        placeholders = ",".join("?" * len(build_ids))
        build_parts = query_db(f"SELECT * FROM Parts WHERE Part_ID IN ({placeholders})", build_ids)
        total = sum(p["Price"] for p in build_parts)

    return render_template("home.html", parts=parts, build_parts=build_parts, total=total)

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
    build = session.get("build", [])
    build.append(id)
    session["build"] = build
    return redirect("/")

if __name__ == '__main__':
    app.run(debug=True)