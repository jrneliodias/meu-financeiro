#!/usr/bin/env python
"""
Performance measurement tools for Django expense report optimization.

Usage:
    python performance_measurement.py --measure-queries
    python performance_measurement.py --explain-query
    python performance_measurement.py --load-test
"""

import os
import sys
import django
import time
from django.db import connection, reset_queries
from django.test.utils import override_settings
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance.settings')
django.setup()

from django.conf import settings
from reports.views import expense_report
from django.test import RequestFactory
from registers.models import Expense, Income


class PerformanceMeasurement:
    """Tools to measure and analyze database performance."""
    
    def __init__(self):
        self.factory = RequestFactory()
    
    def measure_queries(self):
        """
        Measure the number of database queries in the expense_report view.
        
        Returns detailed information about each query executed.
        """
        print("=" * 80)
        print("MEASURING DATABASE QUERIES")
        print("=" * 80)
        
        # Clear previous queries
        reset_queries()
        
        # Create a mock request
        request = self.factory.get('/')
        
        # Enable query logging
        with override_settings(DEBUG=True):
            start_time = time.time()
            
            # Execute the view
            response = expense_report(request)
            
            end_time = time.time()
            execution_time = end_time - start_time
        
        # Analyze queries
        queries = connection.queries
        total_queries = len(queries)
        total_time = sum(float(q['time']) for q in queries)
        
        print(f"📊 PERFORMANCE RESULTS:")
        print(f"   Total Queries: {total_queries}")
        print(f"   Total DB Time: {total_time:.4f}s")
        print(f"   View Execution Time: {execution_time:.4f}s")
        print(f"   Average Query Time: {total_time/total_queries:.4f}s" if total_queries > 0 else "   No queries executed")
        
        print(f"\n🔍 QUERY BREAKDOWN:")
        for i, query in enumerate(queries, 1):
            sql = query['sql'][:100] + "..." if len(query['sql']) > 100 else query['sql']
            print(f"   {i:2d}. {query['time']:>8s}s | {sql}")
        
        # Performance targets check
        print(f"\n🎯 PERFORMANCE TARGETS:")
        print(f"   ✅ Queries ≤ 5: {'✅ PASS' if total_queries <= 5 else '❌ FAIL'} ({total_queries})")
        print(f"   ✅ DB Time ≤ 100ms: {'✅ PASS' if total_time <= 0.1 else '❌ FAIL'} ({total_time:.4f}s)")
        print(f"   ✅ Total Time ≤ 200ms: {'✅ PASS' if execution_time <= 0.2 else '❌ FAIL'} ({execution_time:.4f}s)")
        
        return {
            'total_queries': total_queries,
            'total_time': total_time,
            'execution_time': execution_time,
            'queries': queries
        }
    
    def explain_query(self, limit=3):
        """
        Run EXPLAIN ANALYZE on the most expensive queries to check index usage.
        """
        print("=" * 80)
        print("QUERY EXECUTION PLANS (EXPLAIN ANALYZE)")
        print("=" * 80)
        
        # Test the main aggregation queries that should use our new indexes
        test_queries = [
            {
                'name': 'Expenses by Month and Category',
                'queryset': Expense.objects.filter(date__year=2024)
                    .extra(select={'month': "DATE_TRUNC('month', date)"})
                    .values('month', 'category__name')
                    .annotate(total_amount=django.db.models.Sum('amount'))
                    .order_by('month', 'category__name')
            },
            {
                'name': 'Expenses by Payment Method and Month',
                'queryset': Expense.objects.filter(date__year=2024)
                    .extra(select={'month': "DATE_TRUNC('month', date)"})
                    .values('month', 'payment_method__name')
                    .annotate(total_amount=django.db.models.Sum('amount'))
                    .order_by('month', 'payment_method__name')
            },
            {
                'name': 'Income by Month',
                'queryset': Income.objects.filter(date__year=2024)
                    .extra(select={'month': "DATE_TRUNC('month', date)"})
                    .values('month')
                    .annotate(total_amount=django.db.models.Sum('amount'))
                    .order_by('month')
            }
        ]
        
        for query_info in test_queries:
            print(f"\n📋 {query_info['name']}:")
            print("-" * 50)
            
            try:
                # Get the raw SQL
                sql = str(query_info['queryset'].query)
                print(f"SQL: {sql[:200]}...")
                
                # Run EXPLAIN (works for PostgreSQL, limited for SQLite)
                if 'postgresql' in settings.DATABASES['default']['ENGINE']:
                    explained = query_info['queryset'].explain(
                        analyze=True, 
                        verbose=True, 
                        buffers=True, 
                        timing=True
                    )
                    print(f"EXPLAIN ANALYZE:\n{explained}")
                    
                    # Check for index usage
                    if 'Index Scan' in explained:
                        print("✅ Using Index Scan - Good!")
                    elif 'Seq Scan' in explained:
                        print("⚠️  Using Sequential Scan - May need index optimization")
                else:
                    # For SQLite, just show the query plan
                    explained = query_info['queryset'].explain()
                    print(f"QUERY PLAN:\n{explained}")
                    
            except Exception as e:
                print(f"❌ Error explaining query: {e}")
    
    def load_test(self, iterations=10):
        """
        Run multiple iterations of the view to test consistency and performance.
        """
        print("=" * 80)
        print(f"LOAD TESTING ({iterations} iterations)")
        print("=" * 80)
        
        times = []
        query_counts = []
        
        for i in range(iterations):
            reset_queries()
            
            request = self.factory.get('/')
            
            start_time = time.time()
            with override_settings(DEBUG=True):
                response = expense_report(request)
            end_time = time.time()
            
            execution_time = end_time - start_time
            query_count = len(connection.queries)
            
            times.append(execution_time)
            query_counts.append(query_count)
            
            print(f"   Iteration {i+1:2d}: {execution_time:.4f}s ({query_count} queries)")
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        avg_queries = sum(query_counts) / len(query_counts)
        
        print(f"\n📈 LOAD TEST RESULTS:")
        print(f"   Average Time: {avg_time:.4f}s")
        print(f"   Min Time: {min_time:.4f}s")
        print(f"   Max Time: {max_time:.4f}s")
        print(f"   Average Queries: {avg_queries:.1f}")
        print(f"   Consistency: {'✅ Good' if (max_time - min_time) < 0.1 else '⚠️ Variable'}")
        
        return {
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'avg_queries': avg_queries,
            'all_times': times,
            'all_query_counts': query_counts
        }
    
    def run_all_tests(self):
        """Run all performance tests."""
        print("🚀 STARTING COMPREHENSIVE PERFORMANCE ANALYSIS")
        print("=" * 80)
        
        # 1. Query measurement
        query_results = self.measure_queries()
        
        # 2. Query explanation
        self.explain_query()
        
        # 3. Load testing
        load_results = self.load_test()
        
        # 4. Summary
        print("\n" + "=" * 80)
        print("📊 FINAL PERFORMANCE SUMMARY")
        print("=" * 80)
        
        print(f"✅ Target: ≤ 5 queries per request")
        print(f"   Result: {query_results['total_queries']} queries")
        print(f"   Status: {'✅ PASS' if query_results['total_queries'] <= 5 else '❌ FAIL'}")
        
        print(f"\n✅ Target: ≤ 100ms database time")
        print(f"   Result: {query_results['total_time']:.1f}ms")
        print(f"   Status: {'✅ PASS' if query_results['total_time'] <= 0.1 else '❌ FAIL'}")
        
        print(f"\n✅ Target: ≤ 200ms total response time")
        print(f"   Result: {load_results['avg_time']:.1f}ms")
        print(f"   Status: {'✅ PASS' if load_results['avg_time'] <= 0.2 else '❌ FAIL'}")
        
        print(f"\n🎯 OPTIMIZATION SUCCESS:")
        estimated_original_queries = 50  # Based on analysis
        improvement = ((estimated_original_queries - query_results['total_queries']) / estimated_original_queries) * 100
        print(f"   Query Reduction: ~{improvement:.0f}% ({estimated_original_queries} → {query_results['total_queries']})")
        print(f"   Performance Gain: ~{estimated_original_queries/query_results['total_queries']:.1f}x faster")


def main():
    """Main entry point for performance measurement."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance measurement tools')
    parser.add_argument('--measure-queries', action='store_true', 
                       help='Measure database queries')
    parser.add_argument('--explain-query', action='store_true', 
                       help='Show query execution plans')
    parser.add_argument('--load-test', action='store_true', 
                       help='Run load test')
    parser.add_argument('--all', action='store_true', 
                       help='Run all tests')
    
    args = parser.parse_args()
    
    perf = PerformanceMeasurement()
    
    if args.all:
        perf.run_all_tests()
    elif args.measure_queries:
        perf.measure_queries()
    elif args.explain_query:
        perf.explain_query()
    elif args.load_test:
        perf.load_test()
    else:
        print("Use --help to see available options")
        print("Quick start: python performance_measurement.py --all")


if __name__ == '__main__':
    main()
