from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from .models import Customer, Loan
import logging

logger = logging.getLogger(__name__)

def calculate_approved_limit(monthly_salary):
    """Calculate approved limit based on salary"""
    limit = Decimal(str(36)) * Decimal(str(monthly_salary))
    # Round to nearest lakh (100,000)
    lakh = Decimal('100000')
    return (limit / lakh).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * lakh

def calculate_monthly_installment(loan_amount, interest_rate, tenure):
    """Calculate monthly installment using compound interest formula"""
    try:
        P = Decimal(str(loan_amount))
        r = Decimal(str(interest_rate)) / Decimal('100') / Decimal('12')  # Monthly rate
        n = Decimal(str(tenure))
        
        if r == 0:
            return P / n
        
        # EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        power_term = (1 + r) ** int(n)
        emi = P * r * power_term / (power_term - 1)
        
        return emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
    except Exception as e:
        logger.error(f"Error calculating EMI: {e}")
        return Decimal('0')

def calculate_credit_score(customer):
    """Enhanced credit score calculation with detailed logging"""
    try:
        loans = Loan.objects.filter(customer=customer)
        
        if not loans.exists():
            logger.info(f"New customer {customer.customer_id}, default score: 50")
            return 50
        
        score = Decimal('0')
        current_date = date.today()
        current_year = current_date.year
        
        # Component 1: Payment history (35% weight - 35 points)
        total_emis_due = sum(loan.tenure for loan in loans)
        total_emis_paid_on_time = sum(loan.emis_paid_on_time for loan in loans)
        
        if total_emis_due > 0:
            payment_ratio = Decimal(str(total_emis_paid_on_time)) / Decimal(str(total_emis_due))
            payment_score = payment_ratio * Decimal('35')
            score += payment_score
            logger.info(f"Payment history score: {payment_score} (ratio: {payment_ratio})")
        
        # Component 2: Credit utilization (30% weight - 30 points)
        current_loans = loans.filter(end_date__gte=current_date)
        total_current_debt = sum(loan.loan_amount for loan in current_loans)
        
        if customer.approved_limit > 0:
            utilization_ratio = total_current_debt / customer.approved_limit
            if utilization_ratio <= Decimal('0.3'):
                utilization_score = Decimal('30')
            elif utilization_ratio <= Decimal('0.5'):
                utilization_score = Decimal('20')
            elif utilization_ratio <= Decimal('0.7'):
                utilization_score = Decimal('15')
            elif utilization_ratio <= Decimal('1.0'):
                utilization_score = Decimal('10')
            else:
                utilization_score = Decimal('0')
            
            score += utilization_score
            logger.info(f"Utilization score: {utilization_score} (ratio: {utilization_ratio})")
        
        # Component 3: Credit history length (15% weight - 15 points)
        if loans.exists():
            oldest_loan = loans.order_by('start_date').first()
            account_age_years = (current_date - oldest_loan.start_date).days / 365.25
            
            if account_age_years >= 7:
                history_score = Decimal('15')
            elif account_age_years >= 5:
                history_score = Decimal('12')
            elif account_age_years >= 3:
                history_score = Decimal('10')
            elif account_age_years >= 1:
                history_score = Decimal('7')
            else:
                history_score = Decimal('3')
            
            score += history_score
            logger.info(f"History score: {history_score} (age: {account_age_years} years)")
        
        # Component 4: Recent credit activity (10% weight - 10 points)
        recent_loans = loans.filter(start_date__year=current_year)
        recent_loan_count = recent_loans.count()
        
        if recent_loan_count == 0:
            activity_score = Decimal('10')
        elif recent_loan_count <= 2:
            activity_score = Decimal('8')
        elif recent_loan_count <= 4:
            activity_score = Decimal('5')
        else:
            activity_score = Decimal('2')
        
        score += activity_score
        logger.info(f"Activity score: {activity_score} (recent loans: {recent_loan_count})")
        
        # Component 5: Loan diversity (10% weight - 10 points)
        loan_count = loans.count()
        if 2 <= loan_count <= 5:
            diversity_score = Decimal('10')
        elif loan_count == 1:
            diversity_score = Decimal('7')
        elif 6 <= loan_count <= 10:
            diversity_score = Decimal('5')
        else:
            diversity_score = Decimal('2')
        
        score += diversity_score
        logger.info(f"Diversity score: {diversity_score} (total loans: {loan_count})")
        
        # Final score validation
        final_score = min(100, max(0, int(score)))
        
        # Override: If current debt > approved limit, score = 0
        if total_current_debt > customer.approved_limit:
            final_score = 0
            logger.warning(f"Score overridden to 0: debt {total_current_debt} > limit {customer.approved_limit}")
        
        logger.info(f"Final credit score for customer {customer.customer_id}: {final_score}")
        return final_score
        
    except Exception as e:
        logger.error(f"Error calculating credit score for customer {customer.customer_id}: {e}")
        return 0

def get_corrected_interest_rate(credit_score, requested_rate):
    """Get corrected interest rate based on credit score with validation"""
    try:
        requested_rate = Decimal(str(requested_rate))
        
        if credit_score > 50:
            return requested_rate
        elif 30 < credit_score <= 50:
            return max(requested_rate, Decimal('12.0'))
        elif 10 < credit_score <= 30:
            return max(requested_rate, Decimal('16.0'))
        else:
            return None  # Loan not approved
            
    except Exception as e:
        logger.error(f"Error correcting interest rate: {e}")
        return None

def check_emi_constraint(customer, new_monthly_installment):
    """Check if total EMIs exceed 50% of monthly salary"""
    try:
        current_date = date.today()
        current_loans = customer.loans.filter(end_date__gte=current_date)
        current_emis = sum(loan.monthly_repayment for loan in current_loans)
        
        total_emis = current_emis + Decimal(str(new_monthly_installment))
        salary_threshold = customer.monthly_salary * Decimal('0.5')
        
        constraint_met = total_emis <= salary_threshold
        
        logger.info(f"EMI constraint check: current={current_emis}, new={new_monthly_installment}, "
                   f"total={total_emis}, threshold={salary_threshold}, met={constraint_met}")
        
        return constraint_met
        
    except Exception as e:
        logger.error(f"Error checking EMI constraint: {e}")
        return False

def validate_loan_request(customer_id, loan_amount, interest_rate, tenure):
    """Validate loan request parameters"""
    errors = []
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        errors.append("Customer not found")
        return errors, None
    
    # Validate loan amount
    if loan_amount <= 0:
        errors.append("Loan amount must be positive")
    elif loan_amount > customer.approved_limit:
        errors.append(f"Loan amount exceeds approved limit of {customer.approved_limit}")
    
    # Validate interest rate
    if interest_rate < 0 or interest_rate > 50:
        errors.append("Interest rate must be between 0% and 50%")
    
    # Validate tenure
    if tenure < 1 or tenure > 360:  # Max 30 years
        errors.append("Tenure must be between 1 and 360 months")
    
    return errors, customer