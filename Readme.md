# Credit Approval System

Django REST API for credit approval based on historical loan data and customer profiles handled using PostgreSQL.

## Features

- Customer registration with automated credit limit calculation
- Credit scoring algorithm based on loan history
- Loan eligibility check with interest rate correction
- Loan creation and management
- Background data ingestion from Excel files

## Tech Stack

- Django 4+ with DRF
- PostgreSQL
- Celery & Redis
- Docker & Docker Compose

## Project Structure

```
credit_approval_system/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── manage.py
├── credit_system/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── loans/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── tasks.py
│   ├── utils.py
│   └── tests.py
└── data/
    ├── customer_data.xlsx
    └── loan_data.xlsx
```

## Models

**Customer**: customer_id, first_name, last_name, age, phone_number, monthly_salary, approved_limit, current_debt

**Loan**: loan_id, customer (FK), loan_amount, tenure, interest_rate, monthly_repayment, emis_paid_on_time, start_date, end_date

## API Endpoints

### POST `/register` - Register Customer
```json
Request: {"first_name": "John", "last_name": "Doe", "age": 30, "monthly_income": 50000, "phone_number": 9876543210}
Response: {"customer_id": 1, "name": "John Doe", "age": 30, "monthly_income": 50000, "approved_limit": 1800000, "phone_number": 9876543210}
```

### POST `/check-eligibility` - Check Loan Eligibility
```json
Request: {"customer_id": 1, "loan_amount": 100000.0, "interest_rate": 8.5, "tenure": 12}
Response: {"customer_id": 1, "approval": true, "interest_rate": 8.5, "corrected_interest_rate": 12.0, "tenure": 12, "monthly_installment": 8884.88}
```

### POST `/create-loan` - Create Loan
```json
Request: {"customer_id": 1, "loan_amount": 100000.0, "interest_rate": 12.0, "tenure": 12}
Response: {"loan_id": 1, "customer_id": 1, "loan_approved": true, "message": "Loan approved", "monthly_installment": 8884.88}
```

### GET `/view-loan/{loan_id}` - View Loan Details
```json
Response: {"loan_id": 1, "customer": {"id": 1, "first_name": "John", "last_name": "Doe", "phone_number": 9876543210, "age": 30}, "loan_amount": 100000.0, "interest_rate": 12.0, "monthly_installment": 8884.88, "tenure": 12}
```

### GET `/view-loans/{customer_id}` - View Customer Loans
```json
Response: [{"loan_id": 1, "loan_amount": 100000.0, "interest_rate": 12.0, "monthly_installment": 8884.88, "repayments_left": 8}]
```

## Credit Scoring

Credit score (0-100) based on:
- Past loan payment history (40%)
- Number of previous loans (20%) 
- Current year loan activity (20%)
- Total approved loan volume (20%)

**Approval Rules:**
- Score > 50: Approve at requested rate
- 30-50: Approve with min 12% interest
- 10-30: Approve with min 16% interest  
- Score ≤ 10: Reject
- Current EMIs > 50% salary: Reject
- Current loans > approved limit: Score = 0

## Installation

### Quick Start with Docker
```bash
git clone <repository-url>
cd credit_approval_system
# Add customer_data.xlsx and loan_data.xlsx to data/ folder
docker-compose up --build
```
API available at: `http://localhost:8000`

### Manual Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
celery -A credit_system worker --loglevel=info &
python manage.py runserver
# Or with Docker
docker-compose up --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py ingest_data
```

## Testing
```bash
python manage.py test
# Or with Docker:
docker-compose exec web python manage.py test
```

###### We can test the APIs using POSTMAN and Django in-built admin page.