from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('',                            views.main_dashboard,      name='main'),

    # Inventory
    path('inventory/',                  views.inventory,           name='inventory'),
    path('inventory/add/',              views.product_add,         name='product_add'),
    path('inventory/<int:pk>/edit/',    views.product_edit,        name='product_edit'),
    path('inventory/<int:pk>/delete/',  views.product_delete,      name='product_delete'),

    # AI Assistant
    path('ai/',                         views.ai_assistant,        name='ai_assistant'),
    path('ai/api/',                     views.ai_chat_api,         name='ai_chat_api'),
    path('ai/new/',                     views.ai_new_chat,         name='ai_new_chat'),
    path('ai/session/<uuid:session_id>/',        views.ai_switch_session,   name='ai_switch_session'),
    path('ai/session/<uuid:session_id>/delete/', views.ai_delete_session,   name='ai_delete_session'),

    # Sales
    path('sales/',                      views.sales,               name='sales'),

    # Analytics
    path('analytics/',                  views.analytics,           name='analytics'),

    # Suppliers (replaces Customers)
    path('suppliers/',                          views.suppliers,                   name='suppliers'),
    path('suppliers/add/',                      views.supplier_add,                name='supplier_add'),
    path('suppliers/<int:pk>/',                 views.supplier_detail,             name='supplier_detail'),
    path('suppliers/<int:pk>/order/',           views.supplier_order_add,          name='supplier_order_add'),
    path('suppliers/order/<int:order_pk>/status/', views.supplier_order_update_status, name='supplier_order_status'),

    # Legacy redirect
    path('customers/',                  views.customers,           name='customers'),
]
