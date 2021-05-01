from django.contrib import admin

# Register your models here.
from .models import Product, ContactUsMessage, Order, OrderUpdate

admin.site.register(Product)
admin.site.register(ContactUsMessage)
admin.site.register(Order)
admin.site.register(OrderUpdate)
