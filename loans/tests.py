from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from .models import Customer, Loan
from .utils import calculate_credit_score, calculate_approved_limit

class CustomerTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_customer_registration(self):
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'age': 30,
            'monthly_income': 50000,
            'phone_number': '1234567890'
        }
        response = self.client.post('/api/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['approved_limit'], 1800000)  # 36 * 50000

    def test_loan_eligibility_check(self):
        # Create a customer first
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            age=30,
            phone_number='1234567890',
            monthly_salary=50000,
            approved_limit=1800000
        )
        
        data = {
            'customer_id': customer.customer_id,
            'loan_amount': 100000,
            'interest_rate': 10.0,
            'tenure': 12
        }
        response = self.client.post('/api/check-eligibility/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class UtilsTestCase(TestCase):
    def test_calculate_approved_limit(self):
        limit = calculate_approved_limit(Decimal('50000'))
        self.assertEqual(limit, 1800000)  # Rounded to nearest lakh

    def test_calculate_credit_score_new_customer(self):
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            age=30,
            phone_number='1234567890',
            monthly_salary=50000,
            approved_limit=1800000
        )
        score = calculate_credit_score(customer)
        self.assertEqual(score, 50)  # Default score for new customers