import random
from main_app import default_variables
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.html import strip_tags
from .utils import send_html_email
from django.contrib.auth.hashers import make_password





from django.shortcuts import get_object_or_404, render, redirect
from main_app.forms import *
from .models import *
from datetime import datetime, timedelta
from django.utils import timezone
from main_app.decorators import role_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q, Max
from django.core.paginator import Paginator
from .default_raspberry_entries import create_default_entries_for_user
from .models import default_sensors_values,heatpump_devices_data
from .send_commands_to_pi import send_command_to_raspberry
# Create your views here.


User = get_user_model()

def get_user_raspberry_id(id):
    try:
        get_user_obj = CustomUser.objects.get(id=id).raspberry_id
        return get_user_obj
    except:
        return None
    
def login_view(request):

    if request.method == 'POST':
        
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        error_messages = []

        # Validate inputs
        if not username_or_email and not password:
            error_messages.append("You must have to enter a username or email and password.")
            
        elif not username_or_email:
            error_messages.append("Please enter a username or email.")
            
        elif not password:
            error_messages.append("Please enter a password.")
            

        if error_messages:
            for error in error_messages:
                messages.error(request, error)
            return render(request, "main_app/auth-login-basic.html",{'errors': error_messages})

        # Determine if input is email or username
        if '@' in username_or_email:
            try:
                user_obj = CustomUser.objects.get(email=username_or_email)
                username = user_obj.username  # Retrieve the username for authentication
            except CustomUser.DoesNotExist:
                messages.error(request, "Email does not exist.")
                return render(request, "main_app/auth-login-basic.html")
        else:
            username = username_or_email

        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            error_messages = []
            messages.success(request,f"{username} Logged in Successfully")
            
            return redirect('index')  # Redirect to your desired page
        else:
            error_messages.append("Invalid username, email, or password.")
            return render(request, "main_app/auth-login-basic.html",{'errors': error_messages})
            
            
    return render(request, "main_app/auth-login-basic.html")
    
    




def forgot_view(request):
    
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        if email != "":
            try:
                
                print("req email",email)
                
                user = CustomUser.objects.get(email=email)
                
                otp_number_generated = ''.join(random.choice('0123456789') for _ in range(6))
                
                print("Your otp ",otp_number_generated)
                
                user.otp_number=otp_number_generated
            
                # Update the CustomUser instance
                user.save()
                
                # default_image_path = default_variables.THUMBNAIL_ICON_REACT()
                # default_title_path = default_variables.GMAIL_WEBSITE_TITLE
                # to_email = email
                # subject = f'OTP Sent Successfully! {default_title_path}'
                context = {
                    "username":user.username,
                    "email":email,
                    "otp":otp_number_generated,
                    # "app_name":default_title_path,
                    "current_year":datetime.now().year,  # extracts only  Current year
                    # "logo_url": default_image_path,
                    "create_or_reset":"OTP has been sent"
                }
                html_content = render_to_string('main_app/gmail_otp_sent.html', context)
                
                # send_html_email(to_email, subject, html_content)
                messages.success(request, f"OTP has been sent to your {email}")
                return render(request, "main_app/auth-forgot-otp-confirm.html", context)
            
            except CustomUser.DoesNotExist:

                messages.error(request, f"Email {email} does not exist")
                return render(request, "main_app/auth-forgot-password-basic.html")
        else:
            messages.error(request, "This field should not be Blank.")
            return render(request, "main_app/auth-forgot-password-basic.html")
    
    return render(request, "main_app/auth-forgot-password-basic.html")
    



def forgot_password_update_by_otp(request):

    if request.method == "POST":
        
        try:
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()
            
            otp = request.POST.get('otp', '').strip()
            is_otp = request.POST.get('is_otp', '').strip()

            user = CustomUser.objects.get(email=email)

            
            if otp:
                if otp.isdigit():
                    if user.otp_number == int(otp):
                        print("OTP in database is correct")
                        is_otp = True
                        context = {
                            "username": user.username,
                            "email": email,
                            'is_otp': is_otp,
                            # 'otp': True
                        }
                        messages.success(request, "OTP verified successfully")
                        return render(request, "main_app/auth-forgot-otp-confirm.html", context)
                    else:
                        context = {
                            "username": user.username,
                            "email": email
                            }
                        messages.error(request, "OTP verification failed.")
                        return render(request, "main_app/auth-forgot-otp-confirm.html", context)
                else:
                    context = {
                            "username": user.username,
                            "email": email
                            }
                    
                    messages.error(request, f"Invalid OTP, please enter the correct format.\nThe OTP was entered as a {'String' if isinstance(otp, str) else ''}")
                    return render(request, "main_app/auth-forgot-otp-confirm.html", context)
            
            elif not (otp or is_otp):
                context = {
                        "username": user.username,
                        "email": email,
                }
                messages.error(request, "OTP details are missing. Field should not be blank")
                return render(request, "main_app/auth-forgot-otp-confirm.html", context)
            
            
            if password == "" and confirm_password == "" and is_otp:
                # is_otp = True
                context = {
                        "username": user.username,
                        "email": email,
                        'is_otp' : is_otp,
                        
                }
                messages.error(request, "Password and confirm password both fields are missing, Field should not be blank")
                return render(request, "main_app/auth-forgot-otp-confirm.html", context)
            
            elif password == "" and is_otp:
                is_otp = True
                context = {
                        "username": user.username,
                        "email": email,
                        'is_otp' : is_otp,
                        'confrim_password': confirm_password
                }
                messages.error(request, "Password is missing. Field should not be blank")
                return render(request, "main_app/auth-forgot-otp-confirm.html", context)
            
            elif confirm_password == "" and is_otp:
                is_otp = True
                context = {
                        "username": user.username,
                        "email": email,
                        'is_otp' : is_otp,
                        'password' : password
                }
                messages.error(request, "Confirm Password is missing. Field should not be blank")
                return render(request, "main_app/auth-forgot-otp-confirm.html", context)
            
            elif password and confirm_password and is_otp:
                is_otp = True
                context = {
                    "username": user.username,
                    "email": email,
                    'is_otp' : is_otp,
                    'password' : password,
                    'confrim_password' : confirm_password
                }
                if password == confirm_password:
                    
                    if 6 <= len(password) <= 30:
                        
                        if 'A' <= password[0] <= 'Z':
                            
                            if not ('/' in password or '=' in password or "'" in password or '\"' in password or ' ' in password ):
                                
                                if not 'password' in password.lower():
                                    
                                    user.password = make_password(password)
                                    print(user.password)
                                    
                                    user.otp_number = None  
                                    user.save()
                                    
                                    is_password_reset = True
                                    
                                    print("New password:", password)
                                    print("is reset password:", is_password_reset)

                                    context = {
                                        'is_password_reset' : is_password_reset  
                                    }
                                    messages.success(request, "Your password has been updated successfully.")
                                    return render(request, "main_app/auth-login-basic.html", context)
                                else:
                                    print("Password should not contain 'password' keyword as password")        
                                    messages.error(request, "Password should not contain 'password' keyword as password")
                                    return render(request, "main_app/auth-forgot-otp-confirm.html", context)
                            else:
                                # context = {
                                # "username": user.username,
                                # "email": email,
                                # 'is_otp' : is_otp
                            # }
                                print("Password should not contain /, =, , ', \" or blank spaces")        
                                messages.error(request, "Password should not contain /, =, , ', \" or blank spaces")
                                return render(request, "main_app/auth-forgot-otp-confirm.html", context)
                                
                        else:
                            
                            print("The First letter must be in Uppercase")        
                            messages.error(request, "The First letter must be in Uppercase")
                            return render(request, "main_app/auth-forgot-otp-confirm.html", context)
                            
                    else:
                                                
                        print("The password length should be between 6 and 30 characters.")        
                        messages.error(request, "The password length should be between 6 and 30 characters")
                        return render(request, "main_app/auth-forgot-otp-confirm.html", context)
                    
                else:
                    
                    # context = {
                    #     "username": user.username,
                    #     "email": email,
                    #     'is_otp' : is_otp
                    # }
                    messages.error(request, "The Password and Confirm Password fields do not match.")
                    return render(request, "main_app/auth-forgot-otp-confirm.html", context)

        except CustomUser.DoesNotExist:
            messages.error(request, "Email does not exist.")
            return render(request, "main_app/auth-forgot-password-basic.html")

        return render(request, "main_app/auth-forgot-password-basic.html")


def logout_view(request):
    logout(request)
    return redirect('login')

@role_required(['SuperAdmin', 'Admin', 'Engineer', 'User'])
def index(request):
    start_date = timezone.now() - timedelta(days=189)
    start_date_water_audit = timezone.now() - timedelta(days=60)

    context = {
        'segment'  : 'index',
        #'products' : Product.objects.all()
        
    }
    return render(request, "main_app/index.html", context)

def client_and_users_list(request):
    start_date = timezone.now() - timedelta(days=189)
    start_date_water_audit = timezone.now() - timedelta(days=60)

    context = {
        'segment'  : 'client_and_users_list',
        #'products' : Product.objects.all()
    }
    return render(request, "main_app/client_and_users.html", context)

@role_required(['SuperAdmin'])
def clients_admin_list(request):
    admin_list = CustomUser.objects.get(username=request.user.username)
    admin_list = admin_list.subordinates.all()

    # Add pagination
    paginator = Paginator(admin_list, 20)  # Show 20 admins per page
    page_number = request.GET.get('page')  # Get the current page number from the query parameters
    page_obj = paginator.get_page(page_number)  # Get the paginated objects for the current page


    context = {
        'segment' : 'clients_admin_list',
        'admin_list' : page_obj,
    }
    return render(request, "main_app/clients_admin_list.html", context)

@role_required(['SuperAdmin', 'Admin'])
def clients_engineer_list(request):
    if request.user.role == 'Admin':
        engineer_list = CustomUser.objects.get(username=request.user.username)
        engineer_list = engineer_list.subordinates.all()
        engineer_list = engineer_list.filter(role='Engineer')
    else:
        admin_list = CustomUser.objects.get(username=request.user.username)
        admin_list = admin_list.subordinates.all()
        engineer_list = CustomUser.objects.filter(
            Q(manager__in=admin_list) , Q(role='Engineer')  # Assuming `admin` is the FK field linking subordinates to admins
        )
    
    # Add pagination
    paginator = Paginator(engineer_list, 20)  # Show 20 admins per page
    page_number = request.GET.get('page')  # Get the current page number from the query parameters
    page_obj = paginator.get_page(page_number)  # Get the paginated objects for the current page


    context = {
        'segment'  : 'clients_engineer_list',
        'engineer_list' : page_obj,
    }
    return render(request, "main_app/clients_engineer_list.html", context)

@role_required(['SuperAdmin', 'Admin', 'Engineer'])
def clients_user_list(request):
    if request.user.role == 'Admin' or request.user.role == 'Engineer':
        user_list = CustomUser.objects.get(username=request.user.username)
        if request.user.role == 'Engineer':
            user_list = CustomUser.objects.get(username=user_list.manager.username)
        user_list = user_list.subordinates.all()
        user_list = user_list.filter(role='User')
    else:
        admin_list = CustomUser.objects.get(username=request.user.username)
        admin_list = admin_list.subordinates.all()
        user_list = CustomUser.objects.filter(
            Q(manager__in=admin_list) , Q(role='User')
        )
    
     # Add pagination
    paginator = Paginator(user_list, 20)  # Show 20 admins per page
    page_number = request.GET.get('page')  # Get the current page number from the query parameters
    page_obj = paginator.get_page(page_number)  # Get the paginated objects for the current page


    context = {
        'segment'  : 'clients_user_list',
        'user_list' : page_obj,
    }
    return render(request, "main_app/clients_user_list.html", context)

@role_required(['SuperAdmin'])
def add_user_admin(request):
    """
    View to add Admin users. Only accessible to SuperAdmin.
    """
    if request.method == 'POST':
        
        error_messages = None
        username = request.POST.get('username')
        if not username:
            error_messages = "Please enter username"
            
        form = CustomHtmlUserCreationForm(request.POST, user=request.user, default_role='Admin')
        if form.is_valid():
            
            
            
            
            form.save()
            messages.success(request,"Admin Added Successfully")
            return redirect('clients_admin_list')  # Redirect to a user list or success page
    else:
        form = CustomHtmlUserCreationForm(user=request.user, default_role='Admin')

    return render(request, "main_app/add_user.html", {'form': form,'header_name' : 'Add Admin','form_type' : 'Admin'})

@role_required(['SuperAdmin'])
def edit_user_admin(request, user_id):
    """
    View to edit Admin users. Only accessible to SuperAdmin.
    """
    user_obj = get_object_or_404(CustomUser, id=user_id)  # Fetch the user object to be edited

    if request.method == 'POST':
        form = CustomHtmlUserEditForm(request.POST, instance=user_obj, user=request.user, default_role='Admin')

        if form.is_valid():
            form.save()
            messages.success(request, "Admin Updated Successfully.")
            return redirect('clients_admin_list')  # Redirect to the list of admins or success page
    else:
        form = CustomHtmlUserEditForm(instance=user_obj, user=request.user, default_role='Admin')

    return render(request, "main_app/edit_user.html", {
        'form': form,
        'header_name': 'Edit Admin',  # Update header text for clarity
        'form_type': 'Admin',
        'user_id': user_id
    })

@role_required(['SuperAdmin'])
def delete_user_admin(request, user_id):
    """
    View to delete Admin users. Only accessible to SuperAdmin.
    """
    user = get_object_or_404(CustomUser, id=user_id)

    user.delete()
    messages.warning(request, "Admin Deleted Successfully.")
    return redirect('clients_admin_list')  # Redirect to the admin list page after deletion


@role_required(['SuperAdmin', 'Admin'])
def add_user_engineer(request):
    """
    View to add Engineer users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    if request.method == 'POST':
        form = CustomHtmlUserCreationForm(
            request.POST,
            user=request.user,
            default_role='Engineer',
            # show_admins=(request.user.role == 'SuperAdmin')  # Show Admins for SuperAdmin
        )
        if form.is_valid():
            form.save()
            messages.success(request,"Engineer Added Successfully")
            return redirect('clients_engineer_list')  # Redirect to a user list or success page
    else:
        form = CustomHtmlUserCreationForm(
            user=request.user,
            default_role='Engineer',
            # show_admins=(request.user.role == 'SuperAdmin')
        )

    return render(request, "main_app/add_user.html", {'form': form,'header_name' : 'Add Engineer','form_type' : 'Engineer'})

@role_required(['SuperAdmin', 'Admin'])
def edit_user_engineer(request,user_id):
    """
    View to add Engineer users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    user_obj = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = CustomHtmlUserEditForm(request.POST, instance=user_obj, user=request.user, default_role='Engineer')

        if form.is_valid():
            form.save()
            messages.success(request, "Engineer Updated Successfully.")
            return redirect('clients_engineer_list')  # Redirect to a user list or success page
    else:
        form = CustomHtmlUserEditForm(
            instance=user_obj,
            user=request.user,
            default_role='Engineer',
            # show_admins=(request.user.role == 'SuperAdmin')
        )

    return render(request, "main_app/edit_user.html", {'form': form,'header_name' : 'Edit Engineer','form_type' : 'Engineer','user_id': user_id})

@role_required(['SuperAdmin', 'Admin'])
def delete_user_engineer(request, user_id):
    """
    View to delete an Engineer user. Accessible to SuperAdmin and Admin.
    """
    user = get_object_or_404(CustomUser, id=user_id)

    user.delete()
    messages.warning(request, "Engineer Deleted Successfully.")
    return redirect('clients_engineer_list')


@role_required(['SuperAdmin', 'Admin'])
def add_user_user(request):
    """
    View to add User users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    if request.method == 'POST':
        form = CustomHtmlUserCreationForm(
            request.POST,
            user=request.user,
            default_role='User',
        )
        if form.is_valid():
            new_user = form.save()
            messages.success(request,"User Added Successfully")
            create_default_entries_for_user(new_user)
            return redirect('clients_user_list')  # Redirect to a user list or success page
    else:
        form = CustomHtmlUserCreationForm(
            user=request.user,
            default_role='User',
        )

    return render(request, "main_app/add_user.html", {'form': form,'header_name' : 'Add User','form_type' : 'User'})


@role_required(['SuperAdmin','Admin'])
def edit_user_user(request,user_id):
    """
    View to add User users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    user_obj = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = CustomHtmlUserEditForm(request.POST, instance=user_obj, user=request.user, default_role='User')

        if form.is_valid():
            form.save()
            messages.success(request,"User Updated Successfully")
            return redirect('clients_user_list')  
    else:
        form = CustomHtmlUserEditForm(
            instance=user_obj,
            user = request.user,
            default_role = 'User',

        )
    return render(request, "main_app/edit_user.html", {'form': form,'header_name' : 'Edit User','form_type' : 'User','user_id': user_id})


@role_required(['SuperAdmin', 'Admin'])
def delete_user_user(request, user_id):
    """
    View to delete an User user. Accessible to SuperAdmin and Admin.
    """
    user = get_object_or_404(CustomUser, id=user_id)

    user.delete()
    messages.warning(request, "User deleted successfully.")
    return redirect('clients_user_list')


@role_required(['SuperAdmin', 'Admin', 'Engineer', 'User'])
def profile_show(request):
    return render(request,'main_app/profile_show.html')


@role_required(['SuperAdmin', 'Admin', 'Engineer', 'User'])
def profile_edit(request,id):
    user_obj = get_object_or_404(CustomUser, id=id)
    # print(user_obj)
    if request.method == 'POST':
        
        firstname = request.POST.get('firstName')
        lastname = request.POST.get('lastName')
        phonenumber = request.POST.get('phoneNumber')
        address = request.POST.get('address')
        # email = request.POST.get('email')
        # role = request.POST.get('role')
        
        
        user_obj.first_name = firstname
        user_obj.last_name = lastname
        user_obj.phone_number = phonenumber
        user_obj.address = address
        
        user_obj.save()
        
        messages.success(request,"Profile Updated Successfully")
        print("all process done")
        return redirect('profile_show')
    
    else:
        form = ProfileUpdateForm()
    
    return render(request,'main_app/profile_edit.html')

@role_required(['SuperAdmin', 'Admin', 'Engineer', 'User'])
def devices_and_sensors(request,id):
    heatpump_devices_obj = heatpump_devices_info.objects.filter(fk_user=id)
    heatpump_sensors_status_obj = default_sensors_values.objects.filter(fk_user=id)
    
    user_sensors = default_sensors_values.objects.filter(fk_user=id)
    
    rasp_id_by_user = get_object_or_404(CustomUser, id=id)
    # print(rasp_id_by_user.raspberry_id)
    # heatpump_sensors_obj = default_sensors_values.objects.filter(fk_user=id)
    # heatpump_sensors_data_obj = sensors_data.objects.filter(fk_heatpump_sensor__in = heatpump_sensors_obj)
    latest_sensors_data = sensors_data.objects.filter(
        fk_heatpump_sensor__fk_user=id
    ).values('fk_heatpump_sensor').annotate(
        latest_id=Max('id')
    ).values_list('latest_id', flat=True)

    # Fetch the actual objects
    heatpump_sensors_data_obj = sensors_data.objects.filter(pk__in=latest_sensors_data)
    heatpump_devices_dict = {
        'fan': False,
        'pump':False,
        'compressor':False,
        'heater':False,
    }

    heatpump_sensors_dict = {
        'temperature': 0,
        'voltage':0,
        'watt':0,
        'high_pressure':0,
        'low_pressure':0,
    }

    heatpump_sensors_current_status_dict = {
        'temperature': 0,
        'voltage':0,
        'watt':0,
        'high_pressure':0,
        'low_pressure':0,
    }

    for singal_obj in heatpump_sensors_data_obj:
        heatpump_sensors_dict[singal_obj.fk_heatpump_sensor.sensor] = singal_obj.data

    for singal_obj in heatpump_devices_obj:
        heatpump_devices_dict[singal_obj.device] = singal_obj.status

    for singal_obj in heatpump_sensors_status_obj:
        heatpump_sensors_current_status_dict[singal_obj.sensor] = singal_obj.current_value

    heatpump_sensors_errors_obj = heatpump_devices_errors.objects.filter(fk_user=id, status=False).order_by("-id")[:10]
    # print(user_sensors)
    context = {
        'user_id' : id,
        'heatpump_devices_dict' : heatpump_devices_dict,
        'heatpump_sensors_dict' : heatpump_sensors_dict,
        'heatpump_sensors_current_status_dict' : heatpump_sensors_current_status_dict,
        'rasp_id_by_user' : rasp_id_by_user.raspberry_id,
        'rasp_active_status' : rasp_id_by_user.raspberry_is_active,
        'bypass_sensors': user_sensors,
        'heatpump_sensors_errors_obj': heatpump_sensors_errors_obj,

    }
    return render(request,'main_app/devices_and_sensors.html', context )

@role_required(['SuperAdmin', 'Admin', 'Engineer', 'User'])
def edit_temprature(request,id):
    """
    View to add User users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    user_obj = get_object_or_404(default_sensors_values,fk_user = id, sensor = 'temperature')
    if request.method == 'POST':
            temperature = request.POST.get('current_value')
            max_temperature = request.POST.get('max_temperature')
            user_obj.current_value = temperature
            user_obj.max_current_value = max_temperature
            user_obj.save()
            data = {
                'update_temperature': temperature,
                'update_max_temperature': max_temperature
            }
            get_raspberry_id = get_user_raspberry_id(id)
            if get_raspberry_id:
                send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Update_Temperature',data=data)
                messages.success(request,"Temprature Updated Successfully")
            else:
                messages.error(request,"Temprature Updates Failed")
            return redirect('devices_and_sensors' , id)  
    else:
        pass
    return render(request, "main_app/edit_temprature.html", {'current_temperature' : user_obj.current_value,'max_temperature':user_obj.max_current_value,'user_id': id})




@role_required(['SuperAdmin', 'Admin', 'Engineer'])
def edit_voltage(request,id):
    """
    View to add User users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    print(request.user.id)
    user_obj = get_object_or_404(default_sensors_values,fk_user = id, sensor = 'voltage')
    if request.method == 'POST':
            voltage = request.POST.get('current_value')
            max_voltage = request.POST.get('max_voltage')
            user_obj.current_value = voltage
            user_obj.max_current_value = max_voltage
            user_obj.save()
            data = {
                'update_voltage': voltage,
                'update_max_voltage': max_voltage
            }
            get_raspberry_id = get_user_raspberry_id(id)
            if get_raspberry_id:
                send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Update_Voltage',data=data)
                messages.success(request,"Voltage Updated Successfully")
            else:
                messages.error(request,"Voltage Updates Failed")
            return redirect('devices_and_sensors' , id)  
    else:
        pass
    return render(request, "main_app/edit_voltage.html", {'current_voltage' : user_obj.current_value, 'max_voltage':user_obj.max_current_value,'user_id': id})




@role_required(['SuperAdmin', 'Admin', 'Engineer'])
def edit_watt(request,id):
    """
    View to add User users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    print(request.user.id)
    user_obj = get_object_or_404(default_sensors_values,fk_user = id, sensor = 'watt')
    if request.method == 'POST':
            watt = request.POST.get('current_value')
            max_watt = request.POST.get('max_watt')
            user_obj.current_value = watt
            user_obj.max_current_value = max_watt
            user_obj.save()
            data = {
                'update_watt': watt,
                'update_max_watt': max_watt
            }
            get_raspberry_id = get_user_raspberry_id(id)
            if get_raspberry_id:
                send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Update_Watt',data=data)
                messages.success(request,"Watt Updated Successfully")
            else:
                messages.error(request,"Watt Updates Failed")
            return redirect('devices_and_sensors' , id)  
    else:
        pass
    return render(request, "main_app/edit_watt.html", {'current_watt' : user_obj.current_value, 'max_watt':user_obj.max_current_value,'user_id': id})



@role_required(['SuperAdmin', 'Admin', 'Engineer'])
def device_start_stop(request,id,type):
    """
    View to add User users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    type = str(type).capitalize()
    if not type in ['Start','Stop','Reboot']:
        messages.error(request,f"Device {type} Failed")
        return redirect('devices_and_sensors' , id)
    user_obj = get_object_or_404(CustomUser,id = id)
    restart_by_obj = get_object_or_404(CustomUser,id = request.user.id)
    is_valid_user = False

    if restart_by_obj.role == 'SuperAdmin' and user_obj.manager.manager.id == restart_by_obj.id:
        is_valid_user = True
    elif restart_by_obj.role == 'Admin' and user_obj.manager.id == restart_by_obj.id:
        is_valid_user = True
    elif restart_by_obj.role == 'Engineer' and user_obj.manager.id == restart_by_obj.manager.id:
        is_valid_user = True
    
    if is_valid_user:
        create_obj = raspberry_devices_start_stop_info(fk_user=user_obj,restart_by=restart_by_obj.id,type=type)
        create_obj.save()

        data = {
            'restart_by': restart_by_obj.id,
            'type': type
        }
        get_raspberry_id = get_user_raspberry_id(id)
        if get_raspberry_id:
            send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Device_Start_Stop',data=data)
            messages.info(request,f"Device {type} Successfully")
            return redirect('devices_and_sensors' , id)  
        else:
            messages.error(request,f"Device {type} Failed")
            return redirect('devices_and_sensors' , id)
    else:
        messages.error(request,f"Device {type} Failed")
        return redirect('devices_and_sensors' , id)




@role_required(['SuperAdmin', 'Admin', 'Engineer'])
def bypass_sensors(request,id):
    """
    View to add User users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    
    
    user_obj = default_sensors_values.objects.filter(fk_user=id)
    # print(user_obj)
    selected_sensors = {} 
        

    if request.method == 'POST':
        
        voltage = request.POST.get('voltage', 0)  # Default to 0 if not present
        watt = request.POST.get('watt', 0)
        high_pressure = request.POST.get('high_pressure', 0)
        low_pressure = request.POST.get('low_pressure', 0)
        
        
        selected_sensors = {
            # "voltage": str(voltage) ,
            # "watt": str(watt),
            # "high_pressure": str(high_pressure),
            # "low_pressure": str(low_pressure),
            "voltage": voltage ,
            "watt": watt,
            "high_pressure": high_pressure,
            "low_pressure": low_pressure,
        }

        bypassed_sensors_name = []

        
        for Sensor in user_obj:
            
            sensor_name = Sensor.sensor  
            
            if sensor_name in selected_sensors:
            
                Sensor.bypass_status = selected_sensors[sensor_name]
                if Sensor.bypass_status:
                    bypassed_sensors_name.append(sensor_name.capitalize())
            
            else:
                Sensor.bypass_status = False 
            
            Sensor.save()
        
            
        get_raspberry_id = get_user_raspberry_id(id)
        if get_raspberry_id:
            send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Update_Bypass_Status',data=selected_sensors)
            messages.success(request,f"{", ".join(bypassed_sensors_name)} Sensors have been  BY PASS successfully")
            return redirect('devices_and_sensors' , id)  
        else:
            messages.error(request,f"Sensor By Pass Failed")
            return redirect('devices_and_sensors' , id)
        
        
    
        
    else:
        pass
    
    return render(request, "main_app/bypass_sensors.html", {'user_id': id,'user_obj': user_obj})




@role_required(['SuperAdmin', 'Admin', 'Engineer'])
def reset_default_sensors(request,id):
    """
    View to add User users. Accessible to SuperAdmin and Admin.
    SuperAdmin selects Admin as manager, Admin is default manager.
    """
    
    
    user_obj = default_sensors_values.objects.filter(fk_user=id)
    
    temperature = 0
    voltage = 0
    watt = 0
    high_pressure = 0
    low_pressure = 0
    
    max_temperature = 0
    max_voltage = 0
    max_watt = 0
    max_high_pressure = 0
    max_low_pressure = 0
    
    
    for Sensor in user_obj:
        
        print(Sensor.default_value)
        print(Sensor.current_value)
        Sensor.current_value = Sensor.default_value
        Sensor.max_current_value = Sensor.max_default_value
        Sensor.bypass_status = 0
        Sensor.save()
        
        if Sensor.sensor == "temperature":
            temperature = Sensor.current_value
            max_temperature = Sensor.max_current_value
        elif Sensor.sensor == "voltage":
            voltage = Sensor.current_value
            max_voltage = Sensor.max_current_value
        elif Sensor.sensor == "watt":
            watt = Sensor.current_value
            max_watt = Sensor.max_current_value
        elif Sensor.sensor == "high_pressure":
            high_pressure = Sensor.current_value
            max_high_pressure = Sensor.max_current_value
        elif Sensor.sensor == "low_pressure":
            low_pressure = Sensor.current_value
            max_low_pressure = Sensor.max_current_value
    
    
    selected_sensors = {
            
            "voltage": 0,
            "watt": 0,
            "high_pressure": 0,
            "low_pressure": 0,
            
        }
    data = {
            'update_watt': watt,
            'update_max_watt': max_watt
        }
    data_voltage = {
            'update_voltage': voltage,
            'update_max_voltage': max_voltage
        }
    data_temperature = {
        'update_temperature': temperature,
        'update_max_temperature': max_temperature
        }
            
    get_raspberry_id = get_user_raspberry_id(id)
    if get_raspberry_id:
        send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Update_Bypass_Status',data=selected_sensors)
        send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Update_Watt',data=data)
        send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Update_Voltage',data=data_voltage)  
        send_command_to_raspberry(raspberry_id=get_raspberry_id,command_type='Update_Temperature',data=data_temperature)                 
        messages.success(request,f"Sensors Reset Successfully")
        return redirect('devices_and_sensors' , id)  
    else:
        messages.error(request,f"Sensors Reset Failed")
        return redirect('devices_and_sensors' , id)






def live_data(request, id):
    try:
        
        live_sensors_data = default_sensors_values.objects.filter(fk_user_id__id=id)
        live_device_data = heatpump_devices_info.objects.filter(fk_user_id__id=id)

        
        # print("Live Sensor Data:", live_sensors_data.values())
        # print("Live Device Data:", live_device_data.values())

        
        return JsonResponse({
            "live_sensor_data": list(live_sensors_data.values()), 
            "live_device_data": list(live_device_data.values())
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)  
