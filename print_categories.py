from registers.models import Category
categories = Category.objects.all()
for category in categories:
    print(f'Name: {category.name}, Type: {category.type}')
