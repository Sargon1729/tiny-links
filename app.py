import os
import sqlite3
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
DB = os.environ.get("DB_PATH", "/data/links.db")
PASSWORD = os.environ.get("APP_PASSWORD", "changeme")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        parent_id INTEGER REFERENCES folders(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        folder_id INTEGER REFERENCES folders(id) ON DELETE CASCADE
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM folders").fetchone()[0] == 0:
        conn.execute("INSERT INTO folders(name, parent_id) VALUES('Bookmarks', NULL)")
    conn.commit()
    conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def folder_tree(parent_id=None):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM folders WHERE parent_id IS ? ORDER BY name COLLATE NOCASE",
        (parent_id,)
    ).fetchall()
    conn.close()
    return rows

def breadcrumbs(folder_id):
    conn = db()
    result = []
    current = folder_id
    while current:
        row = conn.execute("SELECT * FROM folders WHERE id=?", (current,)).fetchone()
        if not row:
            break
        result.append(row)
        current = row["parent_id"]
    conn.close()
    return list(reversed(result))

@app.context_processor
def common():
    def tree_children(parent_id):
        return folder_tree(parent_id)

    def tree_links(folder_id):
        conn = db()
        rows = conn.execute(
            "SELECT * FROM links WHERE folder_id=? ORDER BY name COLLATE NOCASE",
            (folder_id,)
        ).fetchall()
        conn.close()
        return rows

    return {
        "all_folders": folder_tree(None),
        "tree_children": tree_children,
        "tree_links": tree_links,
    }

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect(request.args.get("next") or url_for("index"))
        flash("Wrong password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    conn = db()
    root = conn.execute("SELECT * FROM folders WHERE parent_id IS NULL LIMIT 1").fetchone()
    conn.close()
    return redirect(url_for("folder", folder_id=root["id"]))

@app.route("/folder/<int:folder_id>")
@login_required
def folder(folder_id):
    conn = db()
    current = conn.execute("SELECT * FROM folders WHERE id=?", (folder_id,)).fetchone()
    if not current:
        abort(404)
    children = conn.execute(
        "SELECT * FROM folders WHERE parent_id=? ORDER BY name COLLATE NOCASE", (folder_id,)
    ).fetchall()
    links = conn.execute(
        "SELECT * FROM links WHERE folder_id=? ORDER BY name COLLATE NOCASE", (folder_id,)
    ).fetchall()
    conn.close()
    return render_template(
        "folder.html", current=current, children=children, links=links,
        breadcrumbs=breadcrumbs(folder_id)
    )

@app.post("/folder")
@login_required
def add_folder():
    name = request.form.get("name", "").strip()
    parent_id = request.form.get("parent_id", type=int)
    if name and parent_id:
        conn = db()
        conn.execute("INSERT INTO folders(name,parent_id) VALUES(?,?)", (name, parent_id))
        conn.commit()
        conn.close()
    return redirect(url_for("folder", folder_id=parent_id))

@app.post("/folder/<int:folder_id>/rename")
@login_required
def rename_folder(folder_id):
    name = request.form.get("name", "").strip()
    if name:
        conn = db()
        conn.execute("UPDATE folders SET name=? WHERE id=?", (name, folder_id))
        parent = conn.execute("SELECT parent_id FROM folders WHERE id=?", (folder_id,)).fetchone()
        conn.commit()
        conn.close()
        return redirect(url_for("folder", folder_id=folder_id))
    return redirect(url_for("folder", folder_id=folder_id))

@app.post("/folder/<int:folder_id>/delete")
@login_required
def delete_folder(folder_id):
    conn = db()
    row = conn.execute("SELECT parent_id FROM folders WHERE id=?", (folder_id,)).fetchone()
    if not row or row["parent_id"] is None:
        flash("The root folder cannot be deleted.")
        conn.close()
        return redirect(url_for("folder", folder_id=folder_id))
    parent = row["parent_id"]
    conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("folder", folder_id=parent))

@app.post("/link")
@login_required
def add_link():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    folder_id = request.form.get("folder_id", type=int)
    parsed = urlparse(url)
    if name and folder_id and parsed.scheme in ("http", "https") and parsed.netloc:
        conn = db()
        conn.execute("INSERT INTO links(name,url,folder_id) VALUES(?,?,?)", (name, url, folder_id))
        conn.commit()
        conn.close()
    else:
        flash("Enter a name and a valid http(s) URL.")
    return redirect(url_for("folder", folder_id=folder_id))

@app.post("/link/<int:link_id>/delete")
@login_required
def delete_link(link_id):
    conn = db()
    row = conn.execute("SELECT folder_id FROM links WHERE id=?", (link_id,)).fetchone()
    if row:
        folder_id = row["folder_id"]
        conn.execute("DELETE FROM links WHERE id=?", (link_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("folder", folder_id=folder_id))
    conn.close()
    return redirect(url_for("index"))

@app.post("/link/<int:link_id>/edit")
@login_required
def edit_link(link_id):
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    parsed = urlparse(url)
    conn = db()
    row = conn.execute("SELECT folder_id FROM links WHERE id=?", (link_id,)).fetchone()
    if not row:
        conn.close()
        abort(404)
    folder_id = row["folder_id"]
    if name and parsed.scheme in ("http", "https") and parsed.netloc:
        conn.execute("UPDATE links SET name=?, url=? WHERE id=?", (name, url, link_id))
        conn.commit()
    else:
        flash("Enter a name and a valid http(s) URL.")
    conn.close()
    return redirect(url_for("folder", folder_id=folder_id))

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
