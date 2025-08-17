
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
import enum

DATABASE_URL = "sqlite:///./leave_mgmt.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

DEFAULT_ANNUAL_BALANCE = 20

class LeaveStatus(str, enum.Enum):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    department = Column(String, nullable=False)
    joining_date = Column(Date, nullable=False)
    balance = Column(Integer, default=DEFAULT_ANNUAL_BALANCE, nullable=False)
    leaves = relationship("Leave", back_populates="employee", cascade="all, delete-orphan")

class Leave(Base):
    __tablename__ = "leaves"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Integer, nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.Pending, nullable=False)
    employee = relationship("Employee", back_populates="leaves")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini Leave Management System", version="1.0.0")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- Schemas ----
class EmployeeIn(BaseModel):
    name: str = Field(..., example="Asha")
    email: EmailStr = Field(..., example="asha@example.com")
    department: str = Field(..., example="Engineering")
    joining_date: date = Field(..., example="2025-04-01")

class EmployeeOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    department: str
    joining_date: date
    balance: int
    class Config:
        orm_mode = True

class LeaveIn(BaseModel):
    start_date: date
    end_date: date

class LeaveOut(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    days: int
    status: LeaveStatus
    class Config:
        orm_mode = True

# ---- Helpers ----
def calculate_days(start: date, end: date) -> int:
    return (end - start).days + 1

# ---- Employee Endpoints ----
@app.post("/employees", response_model=EmployeeOut, status_code=201)
def add_employee(emp: EmployeeIn, db: Session = Depends(get_db)):
    e = Employee(
        name=emp.name,
        email=emp.email,
        department=emp.department,
        joining_date=emp.joining_date,
        balance=DEFAULT_ANNUAL_BALANCE,
    )
    try:
        db.add(e)
        db.commit()
        db.refresh(e)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists or invalid data")
    return e

@app.get("/employees", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return db.query(Employee).all()

@app.get("/employees/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: int, db: Session = Depends(get_db)):
    e = db.get(Employee, emp_id)
    if not e:
        raise HTTPException(status_code=404, detail="Employee not found")
    return e

@app.get("/employees/{emp_id}/balance")
def get_balance(emp_id: int, db: Session = Depends(get_db)):
    e = db.get(Employee, emp_id)
    if not e:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"employee_id": emp_id, "leave_balance": e.balance}

# ---- Leave Endpoints ----
@app.post("/employees/{emp_id}/leaves", response_model=LeaveOut, status_code=201)
def apply_leave(emp_id: int, req: LeaveIn, db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if req.end_date < req.start_date:
        raise HTTPException(status_code=400, detail="End date must be on/after start date")
    if req.start_date < emp.joining_date:
        raise HTTPException(status_code=400, detail="Cannot apply leave before joining date")
    days = calculate_days(req.start_date, req.end_date)
    if days <= 0:
        raise HTTPException(status_code=400, detail="Invalid date range")
    if days > emp.balance:
        raise HTTPException(status_code=400, detail="Insufficient leave balance")
    leave = Leave(employee_id=emp_id, start_date=req.start_date, end_date=req.end_date, days=days, status=LeaveStatus.Pending)
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave

@app.get("/employees/{emp_id}/leaves", response_model=List[LeaveOut])
def list_leaves(emp_id: int, db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp.leaves

@app.post("/leaves/{leave_id}/approve")
def approve_leave(leave_id: int, db: Session = Depends(get_db)):
    leave = db.get(Leave, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    emp = db.get(Employee, leave.employee_id)
    if leave.status != LeaveStatus.Pending:
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    if emp.balance < leave.days:
        raise HTTPException(status_code=400, detail="Not enough balance to approve")
    emp.balance -= leave.days
    leave.status = LeaveStatus.Approved
    db.commit()
    return {"message": "Leave approved", "remaining_balance": emp.balance}

@app.post("/leaves/{leave_id}/reject")
def reject_leave(leave_id: int, db: Session = Depends(get_db)):
    leave = db.get(Leave, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    if leave.status != LeaveStatus.Pending:
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")
    leave.status = LeaveStatus.Rejected
    db.commit()
    return {"message": "Leave rejected"}

# Health check
@app.get("/health")
def health():
    return {"status": "ok"}
