from django.urls import path
from .views import (
    login_user,
    logout_user,
    register_user,
    home,
    add_egg_farm,
    egg_farm_list,
    edit_egg_farm,
    export_egg_farms,
    delete_egg_farm,
    clear_database,
    farm_autocomplete,
    dashboard,
    weekly_production_data,
    dashboard_analytics_data,
    weekly_forecast_data,
    user_list,
    edit_user_password,
    delete_user,
    edit_user,
    create_user,
      import_egg_farms,test_dashboard,
      prophet_forecast_view
)

urlpatterns = [
    # Auth
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('register/', register_user, name='register'),

    # Home / Dashboard
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),

    # Egg Farm CRUD
    path('add/', add_egg_farm, name='add_egg_farm'),
    path('list/', egg_farm_list, name='egg_farm_list'),
    path('edit/<int:pk>/', edit_egg_farm, name='edit_egg_farm'),
    path('delete/<int:pk>/', delete_egg_farm, name='delete_egg_farm'),
    path('export/', export_egg_farms, name='export_egg_farms'),
    path('clear-database/', clear_database, name='clear_database'),

    # Utilities & Autocomplete
    path('farm-autocomplete/', farm_autocomplete, name='farm_autocomplete'),
    path('import/', import_egg_farms, name='import_egg_farms'),


    # Dashboard Data APIs
    path('dashboard/data/weekly-production/', weekly_production_data, name='weekly_production_data'),
    path('dashboard/data/forecast/', weekly_forecast_data, name='weekly_forecast_data'),
    path('dashboard/data/analytics/', dashboard_analytics_data, name='dashboard_analytics_data'),

    # User management
    path('users/', user_list, name='user_list'),  # List all users
    path('create_user/', create_user, name='create_user'),  # Add this line for create_user
    path('edit_user/<int:user_id>/', edit_user, name='edit_user'),  # Edit user details
    path('edit_user_password/<int:user_id>/', edit_user_password, name='edit_user_password'),  # Change password
    path('delete_user/<int:user_id>/', delete_user, name='delete_user'),  # Delete user
    path('dashboard/test/', test_dashboard, name='dashboard_test'),
    path('forecast/prophet/', prophet_forecast_view, name='prophet_forecast'),

    

]
