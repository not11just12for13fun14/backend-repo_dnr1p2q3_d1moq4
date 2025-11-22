"""
Database Schemas for Payroll

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name.
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class Employee(BaseModel):
    code: str = Field(..., description="Employee code")
    name: str = Field(..., description="Full name")
    state: str = Field(..., description="State for Professional Tax")
    pan: Optional[str] = Field(None, description="PAN number")
    uan: Optional[str] = Field(None, description="EPF UAN")
    esic_no: Optional[str] = Field(None, description="ESIC number")
    department: Optional[str] = None
    designation: Optional[str] = None
    regime: str = Field("new", description="Income tax regime: new/old")
    epf_applicable: bool = True
    esi_applicable: bool = True
    pt_applicable: bool = True
    pf_wage_cap: bool = Field(True, description="Cap PF wage at statutory limit (₹15,000)")

class SalaryStructure(BaseModel):
    basic: float = 0.0
    hra: float = 0.0
    da: float = 0.0
    conveyance: float = 0.0
    special_allowance: float = 0.0
    overtime: float = 0.0
    bonus: float = 0.0
    other_earnings: float = 0.0

class PayrollConfig(BaseModel):
    # Statutory rates (defaults based on current norms; keep configurable)
    epf_employee_rate: float = 0.12
    epf_employer_rate: float = 0.0367
    eps_employer_rate: float = 0.0833
    epf_wage_ceiling: float = 15000.0
    edli_rate: float = 0.005  # 0.5%
    epf_admin_rate: float = 0.005  # 0.5%
    esi_employee_rate: float = 0.0075
    esi_employer_rate: float = 0.0325
    esi_wage_threshold: float = 21000.0

class PayrollRun(BaseModel):
    employee_code: str
    month: str = Field(..., description="YYYY-MM")
    earnings: SalaryStructure
    pt_amount: float = 0.0
    other_deductions: float = 0.0
    non_account_worker: bool = Field(False, description="No PF/ESI")
    config: PayrollConfig = PayrollConfig()

class PayrollResult(BaseModel):
    earnings_gross: float
    statutory_deductions: Dict[str, float]
    employer_contributions: Dict[str, float]
    net_salary: float
    employer_cost: float
    breakdown: Dict[str, float]
