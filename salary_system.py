import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import os
import csv
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

DB_FILE = "salary_db.db"

# ---------------------- Helpers ----------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# ---------------------- Database Initialization ----------------------
def init_db():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_FILE) or '.', exist_ok=True)

    with get_db_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin'
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT,
            basic_salary REAL DEFAULT 0,
            allowances REAL DEFAULT 0,
            deductions REAL DEFAULT 0
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS salary_slips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            total_salary REAL,
            slip_date TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
        """)

        # create default admin if not exists
        cur.execute("SELEC+``````````````````````````````````T COUNT(*) FROM users WHERE username='admin'")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", hash_password("admin"), "admin")
            )
        conn.commit()

# ---------------------- DB Operations ----------------------
def fetch_employees(limit=100):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM employees ORDER BY id DESC LIMIT ?", (limit,))
        return [tuple(row) for row in cur.fetchall()]

# ---------------------- PDF / Export ----------------------
def generate_pdf_slip(emp_row, total_salary, slip_date):
    emp_id, name, dept, basic, allow, deduct = emp_row

    filename = f"salary_slip_{emp_id}_{slip_date.replace(':','-').replace(' ','_')}.pdf"
    out_folder = "slips"
    os.makedirs(out_folder, exist_ok=True)
    path = os.path.join(out_folder, filename)

    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w/2, h - 80, "Salary Slip")

    c.setFont("Helvetica", 11)
    c.drawString(50, h - 130, f"Employee ID: {emp_id}")
    c.drawString(50, h - 150, f"Name: {name}")
    c.drawString(50, h - 170, f"Department: {dept}")
    c.drawString(50, h - 190, f"Date: {slip_date}")

    c.line(50, h - 200, w - 50, h - 200)

    y = h - 230
    c.drawString(60, y, "Basic Salary:")
    c.drawRightString(w - 60, y, f"{basic:.2f}")
    y -= 20
    c.drawString(60, y, "Allowances:")
    c.drawRightString(w - 60, y, f"{allow:.2f}")
    y -= 20
    c.drawString(60, y, "Deductions:")
    c.drawRightString(w - 60, y, f"{deduct:.2f}")
    y -= 20
    c.line(50, y, w - 50, y)
    y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "Net Pay:")
    c.drawRightString(w - 60, y, f"{total_salary:.2f}")

    c.save()
    return path

# ---------------------- UI: Login ----------------------
class LoginWindow:
    def __init__(self, master, on_success):
        self.master = master
        self.on_success = on_success

        master.title("Payroll - Login")
        master.geometry("380x240")
        master.resizable(False, False)

        frame = ttk.Frame(master, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Username").grid(row=0, column=0, sticky="w")
        self.username = ttk.Entry(frame)
        self.username.grid(row=0, column=1)

        ttk.Label(frame, text="Password").grid(row=1, column=0, sticky="w")
        self.password = ttk.Entry(frame, show="*")
        self.password.grid(row=1, column=1)

        ttk.Button(frame, text="Login", command=self.try_login).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Label(frame, text="Default: admin / admin", foreground="gray").grid(row=3, column=0, columnspan=2)

    def try_login(self):
        username = self.username.get().strip()
        pwd = self.password.get().strip()
        if not username or not pwd:
            messagebox.showerror("Error", "Enter username and password")
            return

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT password_hash, role FROM users WHERE username=?", (username,))
            row = cur.fetchone()

        if not row:
            messagebox.showerror("Error", "Invalid login credentials")
            return

        if row[0] != hash_password(pwd):
            messagebox.showerror("Error", "Invalid login credentials")
            return

        # success
        self.master.destroy()
        self.on_success(username)

# ---------------------- Main Application ----------------------
class PayrollApp:
    def __init__(self, username):
        self.username = username
        self.root = tk.Tk()
        self.root.title(f"Payroll System - {username}")
        self.root.geometry("1200x760")
        self.root.config(bg="#f4f6f9")

        # top frame
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text=f"Welcome, {username}", font=("Arial", 12, "bold")).pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh_dashboard).pack(side="right")
        ttk.Button(top, text="Reset DB", command=self.reset_database).pack(side="right", padx=6)
        ttk.Button(top, text="Add User", command=self.show_add_user).pack(side="right", padx=6)

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(main)
        right.pack(side="right", fill="y")

        # Employee form
        form = ttk.LabelFrame(left, text="Employee Information", padding=10)
        form.pack(fill="x")

        ttk.Label(form, text="Name:").grid(row=0, column=0, sticky="w")
        self.entry_name = ttk.Entry(form)
        self.entry_name.grid(row=0, column=1, sticky="we", padx=4)

        ttk.Label(form, text="Department:").grid(row=0, column=2, sticky="w")
        self.entry_dept = ttk.Entry(form)
        self.entry_dept.grid(row=0, column=3, sticky="we", padx=4)

        ttk.Label(form, text="Basic:").grid(row=1, column=0, sticky="w")
        self.entry_basic = ttk.Entry(form)
        self.entry_basic.grid(row=1, column=1, sticky="we", padx=4)

        ttk.Label(form, text="Allowances:").grid(row=1, column=2, sticky="w")
        self.entry_allow = ttk.Entry(form)
        self.entry_allow.grid(row=1, column=3, sticky="we", padx=4)

        ttk.Label(form, text="Deductions:").grid(row=2, column=0, sticky="w")
        self.entry_deduct = ttk.Entry(form)
        self.entry_deduct.grid(row=2, column=1, sticky="we", padx=4)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=4, pady=8)

        ttk.Button(btns, text="Add", command=self.add_employee).pack(side="left", padx=5)
        ttk.Button(btns, text="Update", command=self.update_employee).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete_employee).pack(side="left", padx=5)
        ttk.Button(btns, text="Generate Slip", command=self.generate_slip_action).pack(side="left", padx=5)
        ttk.Button(btns, text="Export CSV", command=self.export_employees_csv).pack(side="left", padx=5)

        # Search box
        search_frame = ttk.Frame(left, padding=(0,6))
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        s_ent = ttk.Entry(search_frame, textvariable=self.search_var)
        s_ent.pack(side="left", padx=6)
        ttk.Button(search_frame, text="Go", command=self.search_employees).pack(side="left")
        ttk.Button(search_frame, text="Clear", command=self.load_employees).pack(side="left", padx=6)

        # Employees table
        emp_frame = ttk.LabelFrame(left, text="Employees", padding=8)
        emp_frame.pack(fill="both", expand=True, pady=6)

        columns = ("id", "name", "dept", "basic", "allow", "deduct")
        self.tree = ttk.Treeview(emp_frame, columns=columns, show="headings")
        for c in columns:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Right: slips + chart
        slip_frame = ttk.LabelFrame(right, text="Recent Salary Slips", padding=8)
        slip_frame.pack(fill="both", expand=True)

        self.slips_tree = ttk.Treeview(slip_frame, columns=("id","name","total","date"), show="headings")
        for c in ("id","name","total","date"):
            self.slips_tree.heading(c, text=c.capitalize())
            self.slips_tree.column(c, anchor="center")
        self.slips_tree.pack(fill="both", expand=True)

        chart_frame = ttk.LabelFrame(right, text="Dashboard (Last 10)", padding=8)
        chart_frame.pack(fill="both", expand=True, pady=8)
        self.chart_canvas = None
        self.chart_frame_inner = chart_frame

        # Initial load
        self.load_employees()
        self.load_slips()
        self.refresh_dashboard()

    # ---------------------- Employee CRUD ----------------------
    def add_employee(self):
        name = self.entry_name.get().strip()
        dept = self.entry_dept.get().strip()
        if not name:
            messagebox.showwarning("Required", "Name is required")
            return
        try:
            basic = float(self.entry_basic.get() or 0)
            allow = float(self.entry_allow.get() or 0)
            deduct = float(self.entry_deduct.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "Salary fields must be numeric")
            return

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO employees (name, department, basic_salary, allowances, deductions) VALUES (?, ?, ?, ?, ?)",
                (name, dept, basic, allow, deduct)
            )
            conn.commit()

        self.load_employees()
        self.clear_form()
        messagebox.showinfo("Success", "Employee added")

    def update_employee(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Choose an employee")
            return
        emp_id = self.tree.item(sel[0])["values"][0]
        try:
            basic = float(self.entry_basic.get() or 0)
            allow = float(self.entry_allow.get() or 0)
            deduct = float(self.entry_deduct.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "Salary fields must be numeric")
            return

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE employees SET name=?, department=?, basic_salary=?, allowances=?, deductions=? WHERE id=?",
                (self.entry_name.get().strip(), self.entry_dept.get().strip(), basic, allow, deduct, emp_id)
            )
            conn.commit()

        self.load_employees()
        messagebox.showinfo("Updated", "Employee updated")

    def delete_employee(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Choose an employee")
            return
        emp_id = self.tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Confirm", "Delete selected employee?"):
            return
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM employees WHERE id=?", (emp_id,))
            conn.commit()
        self.load_employees()
        messagebox.showinfo("Deleted", "Employee deleted")

    # ---------------------- Generate Slip ----------------------
    def generate_slip_action(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an employee")
            return
        values = self.tree.item(sel[0])["values"]
        emp_id, name, dept, basic, allow, deduct = values
        total_salary = basic + allow - deduct
        slip_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        emp_row = (emp_id, name, dept, basic, allow, deduct)

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO salary_slips (employee_id, total_salary, slip_date) VALUES (?, ?, ?)",
                (emp_id, total_salary, slip_date)
            )
            conn.commit()

        pdf_path = generate_pdf_slip(emp_row, total_salary, slip_date)
        self.load_slips()
        messagebox.showinfo("Success", f"Slip generated:\n{pdf_path}")

    # ---------------------- Utilities ----------------------
    def load_employees(self):
        # clear
        for row in self.tree.get_children():
            self.tree.delete(row)
        q = self.search_var.get().strip() if hasattr(self, 'search_var') else ''
        with get_db_connection() as conn:
            cur = conn.cursor()
            if q:
                cur.execute("SELECT * FROM employees WHERE name LIKE ? OR department LIKE ? ORDER BY id DESC", (f"%{q}%", f"%{q}%"))
            else:
                cur.execute("SELECT * FROM employees ORDER BY id DESC")
            rows = cur.fetchall()
        for r in rows:
            self.tree.insert("", "end", values=(r['id'], r['name'], r['department'], r['basic_salary'], r['allowances'], r['deductions']))

    def load_slips(self):
        for row in self.slips_tree.get_children():
            self.slips_tree.delete(row)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT s.id, e.name, s.total_salary, s.slip_date FROM salary_slips s JOIN employees e ON s.employee_id=e.id ORDER BY s.id DESC LIMIT 20"
            )
            rows = cur.fetchall()
        for r in rows:
            self.slips_tree.insert("", "end", values=(r[0], r[1], f"{r[2]:.2f}", r[3]))

    def clear_form(self):
        self.entry_name.delete(0, tk.END)
        self.entry_dept.delete(0, tk.END)
        self.entry_basic.delete(0, tk.END)
        self.entry_allow.delete(0, tk.END)
        self.entry_deduct.delete(0, tk.END)

    def on_tree_select(self, e):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, vals[1])
        self.entry_dept.delete(0, tk.END)
        self.entry_dept.insert(0, vals[2])
        self.entry_basic.delete(0, tk.END)
        self.entry_basic.insert(0, vals[3])
        self.entry_allow.delete(0, tk.END)
        self.entry_allow.insert(0, vals[4])
        self.entry_deduct.delete(0, tk.END)
        self.entry_deduct.insert(0, vals[5])

    def search_employees(self):
        self.load_employees()

    def export_employees_csv(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files','*.csv')])
        if not path:
            return
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, department, basic_salary, allowances, deductions FROM employees ORDER BY id DESC")
            rows = cur.fetchall()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id','name','department','basic_salary','allowances','deductions'])
            for r in rows:
                writer.writerow([r['id'], r['name'], r['department'], r['basic_salary'], r['allowances'], r['deductions']])
        messagebox.showinfo('Exported', f'Employees exported to {path}')

    # ---------------------- Dashboard / Chart ----------------------
    def refresh_dashboard(self):
        # simple bar chart for last 10 slips
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT s.id, e.name, s.total_salary FROM salary_slips s JOIN employees e ON s.employee_id=e.id ORDER BY s.id DESC LIMIT 10"
            )
            rows = cur.fetchall()

        ids = [r[0] for r in rows][::-1]
        names = [r[1] for r in rows][::-1]
        totals = [r[2] for r in rows][::-1]

        # clear old canvas
        for child in self.chart_frame_inner.winfo_children():
            for c in child.winfo_children():
                pass
        if self.chart_canvas:
            try:
                self.chart_canvas.get_tk_widget().destroy()
            except Exception:
                pass

        if not totals:
            lbl = ttk.Label(self.chart_frame_inner, text='No data to show')
            lbl.pack()
            return

        fig, ax = plt.subplots(figsize=(4,2.5))
        ax.bar(names, totals)
        ax.set_title('Last 10 Slip Totals')
        ax.set_ylabel('Amount')
        plt.xticks(rotation=30, ha='right')
        fig.tight_layout()

        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame_inner)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill='both', expand=True)

    # ---------------------- Add User ----------------------
    def show_add_user(self):
        win = tk.Toplevel(self.root)
        win.title("Add User")
        win.geometry("360x220")

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Username").grid(row=0, column=0)
        u = ttk.Entry(frame)
        u.grid(row=0, column=1)

        ttk.Label(frame, text="Password").grid(row=1, column=0)
        p = ttk.Entry(frame, show="*")
        p.grid(row=1, column=1)

        ttk.Label(frame, text="Role").grid(row=2, column=0)
        r = ttk.Combobox(frame, values=("admin", "user"), state="readonly")
        r.set("user")
        r.grid(row=2, column=1)

        def save_user():
            username = u.get().strip()
            pwd = p.get().strip()
            role = r.get()
            if not username or not pwd:
                messagebox.showerror("Error", "Fields cannot be empty")
                return
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                        (username, hash_password(pwd), role)
                    )
                    conn.commit()
                messagebox.showinfo("Success", "User added")
                win.destroy()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "User already exists")

        ttk.Button(frame, text="Save", command=save_user).grid(row=3, column=0, columnspan=2, pady=10)

    # ---------------------- Reset DB (danger) ----------------------
    def reset_database(self):
        if not messagebox.askyesno('Reset DB', 'This will DELETE the current database file and recreate it. Continue?'):
            return
        try:
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            init_db()
            messagebox.showinfo('Reset', 'Database reset. Default admin/admin created.')
            self.load_employees()
            self.load_slips()
            self.refresh_dashboard()
        except Exception as e:
            messagebox.showerror('Error', f'Failed to reset DB:\n{e}')

# ---------------------- Run ----------------------
def start():
    try:
        init_db()
    except sqlite3.DatabaseError:
        # if DB corrupted, offer user to remove
        if messagebox.askyesno('Database Error', 'SQLite DB seems corrupted. Delete and recreate?'):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            init_db()
        else:
            return

    login_root = tk.Tk()
    LoginWindow(login_root, lambda user: PayrollApp(user).root.mainloop())
    login_root.mainloop()

if __name__ == '__main__':
    start()
