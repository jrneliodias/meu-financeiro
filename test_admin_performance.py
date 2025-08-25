#!/usr/bin/env python
"""
Test Django Admin performance optimization.
"""

import os
import django
from django.db import connection, reset_queries
from django.test.utils import override_settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance.settings')
django.setup()

from registers.admin import ExpenseAdmin
from registers.models import Expense
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

def test_admin_queryset_performance():
    """Test the performance of Django Admin queryset."""
    print("🔍 Testing Django Admin Performance...")
    
    # Create mock request and admin
    factory = RequestFactory()
    request = factory.get('/admin/registers/expense/')
    request.user = None  # Mock user
    
    site = AdminSite()
    admin = ExpenseAdmin(Expense, site)
    
    # Clear previous queries
    reset_queries()
    
    print("\n📊 Testing OPTIMIZED Admin Queryset:")
    with override_settings(DEBUG=True):
        # Get the optimized queryset
        queryset = admin.get_queryset(request)
        
        # Force evaluation by converting to list (simulates Django Admin behavior)
        expenses = list(queryset[:40])  # First 40 items like admin pagination
        
        # Access related objects (simulates admin template access)
        for expense in expenses:
            # These accesses would normally cause N+1 queries
            category_name = expense.category.name if expense.category else "No Category"
            payment_name = expense.payment_method.name if expense.payment_method else "No Payment"
            recurring = str(expense.reccurring_expense) if expense.reccurring_expense else "No Recurring"
    
    # Analyze queries
    queries = connection.queries
    total_queries = len(queries)
    total_time = sum(float(q['time']) for q in queries)
    
    print(f"✅ OPTIMIZED RESULTS:")
    print(f"   Total Queries: {total_queries}")
    print(f"   Total DB Time: {total_time:.4f}s")
    print(f"   Expenses Processed: {len(expenses)}")
    print(f"   Average Time per Query: {total_time/total_queries:.4f}s" if total_queries > 0 else "   No queries")
    
    print(f"\n🔍 QUERY BREAKDOWN:")
    for i, query in enumerate(queries, 1):
        sql = query['sql'][:100] + "..." if len(query['sql']) > 100 else query['sql']
        print(f"   {i:2d}. {query['time']:>8s}s | {sql}")
    
    # Performance assessment
    print(f"\n🎯 PERFORMANCE ASSESSMENT:")
    if total_queries <= 10:
        print(f"   ✅ Excellent: {total_queries} queries (target: ≤ 10)")
    elif total_queries <= 20:
        print(f"   ⚠️  Good: {total_queries} queries (could be better)")
    else:
        print(f"   ❌ Poor: {total_queries} queries (needs optimization)")
    
    if total_time <= 0.5:
        print(f"   ✅ Fast: {total_time:.3f}s (target: ≤ 0.5s)")
    elif total_time <= 1.0:
        print(f"   ⚠️  Acceptable: {total_time:.3f}s")
    else:
        print(f"   ❌ Slow: {total_time:.3f}s (needs optimization)")
    
    print(f"\n🎉 IMPROVEMENT ESTIMATE:")
    original_queries = 120  # From your example
    improvement = ((original_queries - total_queries) / original_queries) * 100
    print(f"   Original Queries: ~{original_queries}")
    print(f"   Optimized Queries: {total_queries}")
    print(f"   Improvement: ~{improvement:.0f}% reduction")
    print(f"   Performance Gain: ~{original_queries/total_queries:.1f}x faster")

def test_unoptimized_comparison():
    """Test unoptimized queryset for comparison."""
    print("\n" + "="*60)
    print("📊 COMPARISON: Unoptimized vs Optimized")
    print("="*60)
    
    # Test unoptimized (standard Django queryset)
    reset_queries()
    
    print("\n❌ Testing UNOPTIMIZED Standard Queryset:")
    with override_settings(DEBUG=True):
        # Standard queryset without select_related
        unoptimized_queryset = Expense.objects.all().order_by('-date')[:40]
        expenses = list(unoptimized_queryset)
        
        # Access related objects (this will cause N+1 queries)
        for expense in expenses:
            category_name = expense.category.name if expense.category else "No Category"
            payment_name = expense.payment_method.name if expense.payment_method else "No Payment"
            recurring = str(expense.reccurring_expense) if expense.reccurring_expense else "No Recurring"
    
    unoptimized_queries = len(connection.queries)
    unoptimized_time = sum(float(q['time']) for q in connection.queries)
    
    print(f"❌ UNOPTIMIZED RESULTS:")
    print(f"   Total Queries: {unoptimized_queries}")
    print(f"   Total DB Time: {unoptimized_time:.4f}s")
    
    # Now test optimized again for direct comparison
    test_admin_queryset_performance()

if __name__ == '__main__':
    print("🚀 DJANGO ADMIN PERFORMANCE TEST")
    print("="*60)
    
    # Test both unoptimized and optimized
    test_unoptimized_comparison()
    
    print(f"\n✨ SUMMARY:")
    print("The Django Admin optimization should reduce queries from ~120 to ~5-10")
    print("This represents a 90-95% improvement in database performance!")
    print("\n🎯 Next steps:")
    print("1. Test in your Django Admin: /admin/registers/expense/")
    print("2. Compare before/after performance")
    print("3. Apply similar optimizations to other admin classes")
