import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

from schemas import PayrollRun, PayrollResult, SalaryStructure, PayrollConfig

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Payroll API Running"}

# Helper to round to 2 decimals
rd = lambda x: round(float(x or 0), 2)


def compute_payroll(payload: PayrollRun) -> PayrollResult:
    s: SalaryStructure = payload.earnings
    cfg: PayrollConfig = payload.config

    # Earnings gross
    earnings_gross = (
        (s.basic or 0)
        + (s.hra or 0)
        + (s.da or 0)
        + (s.conveyance or 0)
        + (s.special_allowance or 0)
        + (s.overtime or 0)
        + (s.bonus or 0)
        + (s.other_earnings or 0)
    )

    # PF wage (Basic + DA). Cap to statutory ceiling for contributions
    pf_wage = (s.basic or 0) + (s.da or 0)
    pf_wage_capped = min(pf_wage, cfg.epf_wage_ceiling) if cfg.epf_wage_ceiling > 0 else pf_wage

    # Initialize all components
    epf_emp = eps = epf_er = edli = epf_admin = 0.0
    esi_emp = esi_er = 0.0

    # Non-account worker: no PF/ESI
    if not payload.non_account_worker:
        # EPF (Employee), EPS + EPF (Employer split), EDLI, Admin
        epf_emp = rd(pf_wage_capped * cfg.epf_employee_rate)
        eps_base = min(pf_wage, cfg.epf_wage_ceiling)
        eps = rd(eps_base * cfg.eps_employer_rate)
        epf_er = rd(pf_wage_capped * cfg.epf_employer_rate)
        edli = rd(eps_base * cfg.edli_rate)
        epf_admin = rd(eps_base * cfg.epf_admin_rate)

        # ESI (apply if gross within threshold)
        if earnings_gross <= cfg.esi_wage_threshold:
            esi_emp = rd(earnings_gross * cfg.esi_employee_rate)
            esi_er = rd(earnings_gross * cfg.esi_employer_rate)

    # Professional Tax and other deductions
    pt = rd(payload.pt_amount or 0)
    other_deductions = rd(payload.other_deductions or 0)

    statutory_deductions: Dict[str, float] = {
        "EPF": epf_emp,
        "ESI": esi_emp,
        "PT": pt,
        "Other": other_deductions,
    }
    total_deductions = rd(sum(statutory_deductions.values()))

    net_salary = rd(earnings_gross - total_deductions)

    employer_contributions: Dict[str, float] = {
        "EPS": eps,
        "EPF": epf_er,
        "EDLI": edli,
        "Admin": epf_admin,
        "ESI": esi_er,
    }

    employer_cost = rd(earnings_gross + sum(employer_contributions.values()))

    breakdown: Dict[str, float] = {
        "earnings_gross": rd(earnings_gross),
        "pf_wage": rd(pf_wage),
        "pf_wage_capped": rd(pf_wage_capped),
        "total_deductions": total_deductions,
        "net_salary": net_salary,
        "employer_cost": employer_cost,
    }

    return PayrollResult(
        earnings_gross=rd(earnings_gross),
        statutory_deductions=statutory_deductions,
        employer_contributions=employer_contributions,
        net_salary=net_salary,
        employer_cost=employer_cost,
        breakdown=breakdown,
    )


@app.post("/api/payroll/calculate", response_model=PayrollResult)
def calculate_payroll(payload: PayrollRun):
    return compute_payroll(payload)


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        # Try to import database module
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
