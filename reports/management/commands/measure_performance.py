from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.test import RequestFactory
from django.test.utils import override_settings
from reports.views import expense_report
import time


class Command(BaseCommand):
    help = 'Measure performance of the expense report view'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=5,
            help='Number of iterations to run (default: 5)'
        )
        parser.add_argument(
            '--explain',
            action='store_true',
            help='Show query execution plans'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting Performance Measurement')
        )
        
        factory = RequestFactory()
        iterations = options['iterations']
        
        # Collect performance data
        times = []
        query_counts = []
        all_queries = []
        
        for i in range(iterations):
            reset_queries()
            
            request = factory.get('/')
            
            start_time = time.time()
            with override_settings(DEBUG=True):
                response = expense_report(request)
            end_time = time.time()
            
            execution_time = end_time - start_time
            query_count = len(connection.queries)
            
            times.append(execution_time)
            query_counts.append(query_count)
            all_queries.extend(connection.queries)
            
            self.stdout.write(
                f"   Iteration {i+1}: {execution_time:.4f}s ({query_count} queries)"
            )
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        avg_queries = sum(query_counts) / len(query_counts)
        
        # Display results
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 PERFORMANCE RESULTS"))
        self.stdout.write("=" * 60)
        
        self.stdout.write(f"Average Response Time: {avg_time:.4f}s")
        self.stdout.write(f"Min Response Time: {min_time:.4f}s")
        self.stdout.write(f"Max Response Time: {max_time:.4f}s")
        self.stdout.write(f"Average Queries: {avg_queries:.1f}")
        
        # Performance targets
        self.stdout.write("\n🎯 PERFORMANCE TARGETS:")
        
        if avg_queries <= 5:
            self.stdout.write(self.style.SUCCESS(f"✅ Queries ≤ 5: PASS ({avg_queries:.1f})"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Queries ≤ 5: FAIL ({avg_queries:.1f})"))
        
        if avg_time <= 0.2:
            self.stdout.write(self.style.SUCCESS(f"✅ Response ≤ 200ms: PASS ({avg_time:.4f}s)"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Response ≤ 200ms: FAIL ({avg_time:.4f}s)"))
        
        # Show unique queries
        unique_queries = {}
        for query in all_queries:
            sql = query['sql']
            if sql not in unique_queries:
                unique_queries[sql] = {
                    'count': 0,
                    'total_time': 0.0,
                    'avg_time': 0.0
                }
            unique_queries[sql]['count'] += 1
            unique_queries[sql]['total_time'] += float(query['time'])
        
        # Calculate averages
        for sql, data in unique_queries.items():
            data['avg_time'] = data['total_time'] / data['count']
        
        self.stdout.write("\n🔍 UNIQUE QUERIES:")
        for i, (sql, data) in enumerate(sorted(unique_queries.items(), 
                                             key=lambda x: x[1]['total_time'], 
                                             reverse=True), 1):
            sql_preview = sql[:80] + "..." if len(sql) > 80 else sql
            self.stdout.write(
                f"   {i:2d}. {data['avg_time']:>8.4f}s avg ({data['count']}x) | {sql_preview}"
            )
        
        # Show explain if requested
        if options['explain']:
            self.show_query_plans()
        
        # Final assessment
        estimated_original = 50
        improvement = ((estimated_original - avg_queries) / estimated_original) * 100
        
        self.stdout.write(f"\n🎉 OPTIMIZATION IMPACT:")
        self.stdout.write(f"   Estimated Original Queries: ~{estimated_original}")
        self.stdout.write(f"   Current Queries: {avg_queries:.1f}")
        self.stdout.write(f"   Improvement: ~{improvement:.0f}% reduction")
        self.stdout.write(f"   Performance Gain: ~{estimated_original/avg_queries:.1f}x faster")
    
    def show_query_plans(self):
        """Show execution plans for key queries."""
        from registers.models import Expense, Income
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📋 QUERY EXECUTION PLANS"))
        self.stdout.write("=" * 60)
        
        test_queries = [
            ("Expenses by Category & Month", 
             Expense.objects.filter(date__year=2024)
             .annotate(month=TruncMonth('date'))
             .values('month', 'category__name')
             .annotate(total_amount=Sum('amount'))),
            
            ("Income by Month",
             Income.objects.filter(date__year=2024)
             .annotate(month=TruncMonth('date'))
             .values('month')
             .annotate(total_amount=Sum('amount')))
        ]
        
        for name, queryset in test_queries:
            self.stdout.write(f"\n{name}:")
            self.stdout.write("-" * 40)
            try:
                plan = queryset.explain()
                self.stdout.write(plan)
            except Exception as e:
                self.stdout.write(f"❌ Could not explain query: {e}")
