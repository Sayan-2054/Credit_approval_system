from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import date, timedelta
from decimal import Decimal
import datetime

from .models import Customer, Loan
from .serializers import (
    CustomerRegistrationSerializer, CustomerSerializer,
    LoanEligibilitySerializer, LoanEligibilityResponseSerializer,
    LoanCreationSerializer, LoanCreationResponseSerializer,
    LoanDetailSerializer, CustomerLoanSerializer
)
from .utils import (
    calculate_approved_limit, calculate_monthly_installment,
    calculate_credit_score, get_corrected_interest_rate,
    check_emi_constraint
)

@api_view(['POST'])
def register_customer(request):
    """Register a new customer"""
    serializer = CustomerRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        approved_limit = calculate_approved_limit(data['monthly_income'])
        
        customer = Customer.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            age=data['age'],
            phone_number=data['phone_number'],
            monthly_salary=data['monthly_income'],
            approved_limit=approved_limit
        )
        
        response_serializer = CustomerSerializer(customer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def check_eligibility(request):
    """Check loan eligibility"""
    serializer = LoanEligibilitySerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        
        try:
            customer = Customer.objects.get(customer_id=data['customer_id'])
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        credit_score = calculate_credit_score(customer)
        requested_rate = data['interest_rate']
        corrected_rate = get_corrected_interest_rate(credit_score, requested_rate)
        
        monthly_installment = calculate_monthly_installment(
            data['loan_amount'], 
            corrected_rate or requested_rate, 
            data['tenure']
        )
        
        # Check eligibility conditions
        approval = True
        
        if corrected_rate is None:  # Credit score too low
            approval = False
        elif not check_emi_constraint(customer, monthly_installment):
            approval = False
        
        response_data = {
            'customer_id': data['customer_id'],
            'approval': approval,
            'interest_rate': requested_rate,
            'corrected_interest_rate': corrected_rate or requested_rate,
            'tenure': data['tenure'],
            'monthly_installment': monthly_installment
        }
        
        response_serializer = LoanEligibilityResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def create_loan(request):
    """Process a new loan"""
    serializer = LoanCreationSerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        
        try:
            customer = Customer.objects.get(customer_id=data['customer_id'])
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        credit_score = calculate_credit_score(customer)
        corrected_rate = get_corrected_interest_rate(credit_score, data['interest_rate'])
        
        monthly_installment = calculate_monthly_installment(
            data['loan_amount'], 
            corrected_rate or data['interest_rate'], 
            data['tenure']
        )
        
        # Check eligibility
        loan_approved = True
        message = "Loan approved successfully"
        loan_id = None
        
        if corrected_rate is None:
            loan_approved = False
            message = "Loan not approved due to low credit score"
        elif not check_emi_constraint(customer, monthly_installment):
            loan_approved = False
            message = "Loan not approved: EMIs exceed 50% of monthly salary"
        
        if loan_approved:
            # Create the loan
            start_date = date.today()
            end_date = start_date + timedelta(days=data['tenure'] * 30)  # Approximate
            
            loan = Loan.objects.create(
                customer=customer,
                loan_amount=data['loan_amount'],
                tenure=data['tenure'],
                interest_rate=corrected_rate,
                monthly_repayment=monthly_installment,
                start_date=start_date,
                end_date=end_date
            )
            loan_id = loan.loan_id
        
        response_data = {
            'loan_id': loan_id,
            'customer_id': data['customer_id'],
            'loan_approved': loan_approved,
            'message': message,
            'monthly_installment': monthly_installment
        }
        
        response_serializer = LoanCreationResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def view_loan(request, loan_id):
    """View loan details"""
    loan = get_object_or_404(Loan, loan_id=loan_id)
    serializer = LoanDetailSerializer(loan)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def view_customer_loans(request, customer_id):
    """View all loans for a customer"""
    customer = get_object_or_404(Customer, customer_id=customer_id)
    loans = customer.loans.filter(end_date__gte=date.today())  # Current loans only
    serializer = CustomerLoanSerializer(loans, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
@api_view(['GET'])
def health_check(request):
    """Health check endpoint"""
    from django.db import connection
    
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check Redis connection (optional)
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        cache_status = cache.get('health_check') == 'ok'
        
        return Response({
            'status': 'healthy',
            'database': 'connected',
            'cache': 'connected' if cache_status else 'disconnected',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)