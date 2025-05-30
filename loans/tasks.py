import pandas as pd
from celery import shared_task
from django.conf import settings
from .models import Customer, Loan
from datetime import datetime
import os

@shared_task
def ingest_customer_data():
    """Ingest customer data from Excel file"""
    file_path = os.path.join(settings.BASE_DIR, 'data', 'customer_data.xlsx')
    
    try:
        df = pd.read_excel(file_path)
        
        for _, row in df.iterrows():
            Customer.objects.get_or_create(
                customer_id=row['customer_id'],
                defaults={
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'age':row['age'],
                    'phone_number': str(row['phone_number']),
                    'monthly_salary': row['monthly_salary'],
                    'approved_limit': row['approved_limit'],
                    'current_debt': row.get('current_debt', 0),
                }
            )
        
        return f"Successfully ingested {len(df)} customer records"
    
    except Exception as e:
        return f"Error ingesting customer data: {str(e)}"

@shared_task
def ingest_loan_data():
    """Ingest loan data from Excel file"""
    file_path = os.path.join(settings.BASE_DIR, 'data', 'loan_data.xlsx')
    
    try:
        df = pd.read_excel(file_path)
        
        for _, row in df.iterrows():
            try:
                customer = Customer.objects.get(customer_id=row['customer_id'])
                
                Loan.objects.get_or_create(
                    loan_id=row['loan_id'],
                    defaults={
                        'customer': customer,
                        'loan_amount': row['loan_amount'],
                        'tenure': row['tenure'],
                        'interest_rate': row['interest_rate'],
                        'monthly_repayment': row['monthly_repayment'],
                        'emis_paid_on_time': row['emis_paid_on_time'],
                        'start_date': pd.to_datetime(row['start_date']).date(),
                        'end_date': pd.to_datetime(row['end_date']).date(),
                    }
                )
            except Customer.DoesNotExist:
                continue
        
        return f"Successfully ingested {len(df)} loan records"
    
    except Exception as e:
        return f"Error ingesting loan data: {str(e)}"