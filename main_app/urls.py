from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from . import views
from .apis import api_views

urlpatterns = [
    path('login/', views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('forgot/', views.forgot_view, name='forgot'),
    path('forgot_password_update_by_otp/', views.forgot_password_update_by_otp, name='forgot_password_update_by_otp'),
    
    path('client_and_users_list/', views.client_and_users_list, name='client_and_users_list'),
    path('clients_admin_list/', views.clients_admin_list, name='clients_admin_list'),
    path('clients_engineer_list/', views.clients_engineer_list, name='clients_engineer_list'),
    path('clients_user_list/', views.clients_user_list, name='clients_user_list'),
    path('add_user_admin/', views.add_user_admin, name='add_user_admin'),
    path('add_user_engineer/', views.add_user_engineer, name='add_user_engineer'),
    path('add_user_user/', views.add_user_user, name='add_user_user'),
    path('profile_edit/<int:id>/', views.profile_edit, name='profile_edit'),
    path('profile_show/', views.profile_show, name='profile_show'),
    path('devices_and_sensors/<int:id>/',views.devices_and_sensors,name='devices_and_sensors'),
    path('edit_temprature/<int:id>/',views.edit_temprature,name='edit_temprature'),
    path('edit_voltage/<int:id>/',views.edit_voltage,name='edit_voltage'),
    path('edit_watt/<int:id>/',views.edit_watt,name='edit_watt'),
    path('devices_and_sensors/<int:id>/<slug:type>/',views.device_start_stop,name='device_start_stop'),
    
    path('bypass_sensors/<int:id>/',views.bypass_sensors,name='bypass_sensors'),
    path('reset_default_sensors/<int:id>/',views.reset_default_sensors,name='reset_default_sensors'),    

    path('edit_user_admin/<int:user_id>/', views.edit_user_admin, name='edit_user_admin'),
    path('delete_user_admin/<int:user_id>/', views.delete_user_admin, name='delete_user_admin'),
     
    path('edit_user_engineer/<int:user_id>/', views.edit_user_engineer, name='edit_user_engineer'),
    path('delete_user_engineer/<int:user_id>/', views.delete_user_engineer, name='delete_user_engineer'),

    path('edit_user_user/<int:user_id>/', views.edit_user_user, name='edit_user_user'),
    #path('delete_user/<int:user_id>/', views.delete_user_user, name='delete_user_user'),
    path('delete_user_user/<int:user_id>/', views.delete_user_user, name='delete_user_user'),

    # path('live_data/<int:id>/',views.live_data,name='live_data'),
    path('live-data/<int:id>/', views.live_data, name='live_data'),



    path('api/signup/', api_views.user_register),
    path('api/login/', api_views.user_login),
    path('api/user-forgot-password/', api_views.forgot_password),
    path('api/user-forgot-password-otp/', api_views.forgot_password_update_by_otp),
    path('api/logout/', api_views.logout_view),
    path('api/user-reset-password/', api_views.reset_password),
    path('api/user-profile-info/',api_views.user_profile_info),
    path('api/user-profile-info-update/',api_views.user_profile_info_update),
    path('api/edit_temperature/',api_views.edit_temperature),


# All api's
    path('api/signup/', api_views.user_register),                                           # done
    path('api/login/', api_views.user_login),                                               # done
    path('api/user-forgot-password/', api_views.forgot_password),                           # done
    path('api/user-forgot-password-otp/', api_views.forgot_password_update_by_otp),         # done
    path('api/logout/', api_views.logout_view),                                             # done
    path('api/user-reset-password/', api_views.reset_password),                             # done 
    path('api/user-profile-info/',api_views.user_profile_info),                             # done  
    path('api/user-profile-info-update/',api_views.user_profile_info_update),               # done
    path('api/edit_temperature/',api_views.edit_temperature),                               # done
    path('api/user_admin_list/',api_views.user_admin_list),                                 # done
    path('api/clients_user_list/',api_views.clients_user_list),                             # done
    
    path('api/edit_voltage/',api_views.edit_voltage),                               # done
    path('api/edit_watt/',api_views.edit_watt),    
    
    path('api/by_pass_sensors/',api_views.by_pass_sensors),

    path('api/reset_default_sensors/',api_views.reset_default_sensors),

    path('api/edit_user_engineer/',api_views.edit_user_engineer),                            

    path('api/clients_user_list/',api_views.clients_user_list),                             # done    
    path('api/client-and-users-list/',api_views.client_and_users_list),
    path('api/clients-engineer-list/',api_views.clients_engineer_list),
    path('api/devices-and-sensors/',api_views.devices_and_sensors),
    path('api/edit_user_admin/',api_views.edit_user_admin),
    path('api/edit_user/',api_views.edit_user),
    path('api/add_user/',api_views.add_user),
    path('api/delete_user/',api_views.delete_user),
    path('api/delete_user_admin/',api_views.delete_user_admin),


    path('api/manager_list/',api_views.manager_list),


    path('', views.index,  name='index'),
    ]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)