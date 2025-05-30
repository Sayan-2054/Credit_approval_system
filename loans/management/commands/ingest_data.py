from django.core.management.base import BaseCommand
from loans.tasks import ingest_customer_data, ingest_loan_data

class Command(BaseCommand):
    help = 'Ingest customer and loan data from Excel files'

    def handle(self, *args, **options):
        self.stdout.write('Starting data ingestion...')
        
        # Ingest customer data
        customer_result = ingest_customer_data()
        self.stdout.write(customer_result)
        
        # Ingest loan data
        loan_result = ingest_loan_data()
        self.stdout.write(loan_result)
        
        self.stdout.write(
            self.style.SUCCESS('Data ingestion completed successfully')
        )