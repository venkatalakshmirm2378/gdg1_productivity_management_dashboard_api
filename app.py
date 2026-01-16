from flask import Flask, request, jsonify
import sqlite3
import logging
from datetime import datetime

app = Flask(__name__)


logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def get_db_connection():
    conn = sqlite3.connect("productivity.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT CHECK(priority IN ('Low','Medium','High')),
            status TEXT CHECK(status IN ('Pending','In Progress','Completed')),
            deadline TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


def validate_task(data):
    required_fields = ["title", "priority", "status", "deadline"]

    for field in required_fields:
        if field not in data or not data[field]:
            return f"{field} is required"

    if data["priority"] not in ["Low", "Medium", "High"]:
        return "Invalid priority"

    if data["status"] not in ["Pending", "In Progress", "Completed"]:
        return "Invalid status"

    try:
        datetime.strptime(data["deadline"], "%Y-%m-%d")
    except ValueError:
        return "Deadline must be YYYY-MM-DD"

    return None



@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    error = validate_task(data)

    if error:
        logging.error(f"Validation error: {error}")
        return jsonify({"error": error}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tasks (title, description, priority, status, deadline, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["title"],
            data.get("description", ""),
            data["priority"],
            data["status"],
            data["deadline"],
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        logging.info("Task created successfully")
        return jsonify({"message": "Task created"}), 201

    except Exception as e:
        logging.error(f"Create task failed: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500



@app.route("/tasks", methods=["GET"])
def get_tasks():
    try:
        conn = get_db_connection()
        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        conn.close()

        return jsonify([dict(task) for task in tasks]), 200

    except Exception as e:
        logging.error(f"Fetch tasks failed: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500



@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    conn = get_db_connection()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()

    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify(dict(task)), 200



@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    error = validate_task(data)

    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET title=?, description=?, priority=?, status=?, deadline=?
        WHERE id=?
    """, (
        data["title"],
        data.get("description", ""),
        data["priority"],
        data["status"],
        data["deadline"],
        task_id
    ))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"error": "Task not found"}), 404

    logging.info(f"Task {task_id} updated")
    return jsonify({"message": "Task updated"}), 200



@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Task not found"}), 404

    logging.info(f"Task {task_id} deleted")
    return jsonify({"message": "Task deleted"}), 200



if __name__ == "__main__":
    app.run(debug=True)

 
