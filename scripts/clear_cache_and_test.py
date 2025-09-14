#!/usr/bin/env python
"""
Script to clear cache and test performance after optimizations.
"""

import os
import django
from django.core.cache import cache

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance.settings')
django.setup()

def main():
    print("🧹 Clearing Django cache...")
    cache.clear()
    print("✅ Cache cleared successfully!")
    
    print("\n🚀 Now run the performance test:")
    print("python manage.py measure_performance --iterations=5")
    
    print("\n📝 Expected results after optimization:")
    print("   - Queries: ≤ 5 (down from ~167)")
    print("   - Response time: ≤ 200ms (down from ~50s)")
    print("   - No more recurring_expense N+1 queries")

if __name__ == '__main__':
    main()
