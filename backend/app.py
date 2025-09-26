from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, select, func
from sqlalchemy.orm import declarative_base, Session
from datetime import datetime
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'expenses.db')
os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={"check_same_thread": False})
Base = declarative_base()

class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

app = Flask(__name__, static_folder='static', static_url_path='/')
CORS(app)

# Serve frontend
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# API: add expense
@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.json
    description = data.get('description')
    category = data.get('category')
    amount = float(data.get('amount'))
    created_at = data.get('created_at')
    if created_at:
        created_at = datetime.fromisoformat(created_at)
    else:
        created_at = datetime.utcnow()
    with Session(engine) as session:
        e = Expense(description=description, category=category, amount=amount, created_at=created_at)
        session.add(e)
        session.commit()
        session.refresh(e)
        return jsonify({"id": e.id, "description": e.description, "category": e.category, "amount": e.amount, "created_at": e.created_at.isoformat()})

# API: list / filter / sort
@app.route('/api/expenses', methods=['GET'])
def list_expenses():
    # Query params: start, end (ISO date), category, sort (amount_asc, amount_desc, date_asc, date_desc)
    start = request.args.get('start')
    end = request.args.get('end')
    category = request.args.get('category')
    sort = request.args.get('sort')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 100))

    stmt = select(Expense)
    if start:
        try:
            start_dt = datetime.fromisoformat(start)
            stmt = stmt.where(Expense.created_at >= start_dt)
        except:
            pass
    if end:
        try:
            end_dt = datetime.fromisoformat(end)
            stmt = stmt.where(Expense.created_at <= end_dt)
        except:
            pass
    if category:
        stmt = stmt.where(Expense.category == category)

    if sort == 'amount_asc':
        stmt = stmt.order_by(Expense.amount.asc())
    elif sort == 'amount_desc':
        stmt = stmt.order_by(Expense.amount.desc())
    elif sort == 'date_asc':
        stmt = stmt.order_by(Expense.created_at.asc())
    else:
        # default: newest first
        stmt = stmt.order_by(Expense.created_at.desc())

    with Session(engine) as session:
        total = session.scalar(select(func.count()).select_from(stmt.subquery()))
        results = session.execute(stmt.offset((page-1)*per_page).limit(per_page)).scalars().all()
        data = [{"id": e.id, "description": e.description, "category": e.category, "amount": e.amount, "created_at": e.created_at.isoformat()} for e in results]
        return jsonify({"total": total, "page": page, "per_page": per_page, "data": data})

# API: summary (total, by category)
@app.route('/api/summary', methods=['GET'])
def summary():
    start = request.args.get('start')
    end = request.args.get('end')
    stmt = select(func.sum(Expense.amount).label('total'))
    cat_stmt = select(Expense.category, func.sum(Expense.amount).label('amount')).group_by(Expense.category)

    if start:
        try:
            start_dt = datetime.fromisoformat(start)
            stmt = stmt.where(Expense.created_at >= start_dt)
            cat_stmt = cat_stmt.where(Expense.created_at >= start_dt)
        except:
            pass
    if end:
        try:
            end_dt = datetime.fromisoformat(end)
            stmt = stmt.where(Expense.created_at <= end_dt)
            cat_stmt = cat_stmt.where(Expense.created_at <= end_dt)
        except:
            pass

    with Session(engine) as session:
        total = session.execute(stmt).first()[0] or 0.0
        by_cat = session.execute(cat_stmt).all()
        categories = [{"category": r[0], "amount": r[1]} for r in by_cat]
        return jsonify({"total": total, "by_category": categories})

# API: delete expense
@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    with Session(engine) as session:
        e = session.get(Expense, expense_id)
        if not e:
            return jsonify({"error": "Not found"}), 404
        session.delete(e)
        session.commit()
        return jsonify({"deleted": expense_id})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
