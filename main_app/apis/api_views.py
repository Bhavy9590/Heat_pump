import io
import mimetypes
from wsgiref.util import FileWrapper
import zipfile
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Max,Q
from main_app.models import *
import random
import string
import secrets
import jwt
import os
from django.conf import settings
from datetime import datetime, timedelta, timezone
from ..decorators import authenticate_with_token
import re
from ..utils import send_html_email
from django.template.loader import render_to_string
from main_app import default_variables
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q, Case, When, Value, IntegerField
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage
import requests
from zipfile import ZipFile
from io import BytesIO
import urllib.parse
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
import json
# from django.contrib.auth.tokens import default_token_generator
# from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
# from django.core.mail import send_mail
# from django.utils.encoding import force_bytes, force_text
secret_key_token = 'rHx3e8uaNklG(Zoe.f])b,$V2>{o/{N8_{-LRG94zEw%/e-Iu>'
# def token_expire_check(token,secret_key=secret_key_token):
#     try:
#         decoded_token = jwt.decode(token, secret_key, algorithms=['HS256'])

#         # Access values from the decoded payload
#         user_id = decoded_token.get('user_id')
#         username = decoded_token.get('username')
#         expiration_time = decoded_token.get('exp')
#         # Check if the token is still valid
#         current_time = datetime.utcnow().timestamp()
#         if expiration_time and expiration_time > current_time:
#             return True
#         else:
#             return False
#     except:
#         return False


def extract_token(request_obj):
    auth_header = request_obj.headers.get('Authorization')
    auth_type, token = auth_header.split()
    return token

def render_to_pdf(template_path, context_dict):
    template = get_template(template_path)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename="membership_invoice.pdf"'

    # Use xhtml2pdf to generate PDF from HTML
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')

    return response

def custom_strftime(date):
    suffix = ""
    if 4 <= date.day <= 20 or 24 <= date.day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][date.day % 10 - 1]

    return date.strftime("%B %d{} %Y").format(suffix)

def get_access_token():
    client_id = 'AbTxf_Xmynoa2eNQ74ewAABy-ciEqHTwccupgyc3AKsJtL8NGFWhI2k19s_V7Np_3slkxSsyeN5oZsKN'
    client_secret = 'EJrjzfCplsPlKMDlMb7nGLJX1Uure3xraj8FbCChSh3MDKTvB3BuQ8VJ_gSPzb6vGDSR1B-sVz2pviix'

    # Set up request parameters
    url = 'https://api.sandbox.paypal.com/v1/oauth2/token'
    data = {'grant_type': 'client_credentials'}
    auth = (client_id, client_secret)

    # Make the request
    response = requests.post(url, data=data, auth=auth)

    # Check for errors
    if response.status_code != 200:
        print(f'Request failed with status code: {response.status_code}')
        # Handle the error appropriately

    # Decode the JSON response
    response_data = response.json()

    # Access token will be in response_data['access_token']
    access_token = response_data['access_token']

    # Use access_token in subsequent API requests
    return access_token

@swagger_auto_schema(method='post', operation_description="User for create new user", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'username': openapi.Schema(type=openapi.TYPE_STRING, description='User Name'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First Name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last Name'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address'),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                            'address': openapi.Schema(type=openapi.TYPE_STRING, description='Address'),
                            'role': openapi.Schema(type=openapi.TYPE_STRING, description='Role of User'),
                            'manager': openapi.Schema(type=openapi.TYPE_INTEGER, description='manager of User'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([])  # Disable permission checks for this specific view
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin'])
def user_register(request):
    username = request.data['username']
    first_name = request.data['first_name']
    last_name = request.data['last_name']
    email = request.data['email']
    phone_number = request.data['phone_number']
    address = request.data['address']
    role = request.data['role']
    manager = int(request.data['manager'])

    min_username_length = 3
    min_name_length = 2
    max_name_length = 50 

    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    if not email_pattern.match(email):
        response_data = {
            'code' : '400',
            'message': 'Please Enter Valid Email Address.',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
    

    if request.user.role == role or (request.user.role == 'Admin' and role == 'SuperAdmin'):
        response_data = {
            'code' : '400',
            'message': 'Creating This Role is Not Permitted.',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
    try:
        fk_manager_obj = CustomUser.objects.get(id=manager)
        is_manager_true = True
    except:
        is_manager_true = False
    if not is_manager_true:
        response_data = {
            'code' : '400',
            'message': 'Manager is Not Found.',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
    
    # phone_number_pattern = re.compile(r'^\(\d{3}\) \d{3}-\d{4}$')
    # if not phone_number_pattern.match(phone_number):
    if not len(phone_number) == 10:
        response_data = {
            'code' : '400',
            'message': 'Please Enter Valid Mobile Number.',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
    if not (min_username_length <= len(username) <= max_name_length) or \
   not (min_name_length <= len(first_name) <= max_name_length) or \
   not (min_name_length <= len(last_name) <= max_name_length):
        response_data = {
            'code' : '400',
            'message': 'username, first_name, last_name should be 2 to 50 character long.',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    # Check if the username and email already exist
    if CustomUser.objects.filter(username=username).exists() or CustomUser.objects.filter(email=email).exists():
        response_data = {
            'code' : '400',
            'message': 'Username or Email Already Exists',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    # Generate a random password
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    encrypt_password = make_password(password)
    # length = 128
    # bytes_needed = (length * 3 + 3) // 4
    # Generate a token of sufficient length
    # token_generated = secrets.token_urlsafe(bytes_needed)

    # Create an CustomUser instance
    user_data = CustomUser(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        address=address,
        phone_number=phone_number,
        password=encrypt_password,
        role=role,
        manager=fk_manager_obj,
    )
    
    # Save the CustomUser instance
    user_data.save()

    default_image_path = default_variables.THUMBNAIL_ICON_REACT()
    default_title_path = default_variables.GMAIL_WEBSITE_TITLE
    to_email = email
    subject = f'Account Created Successfully! {default_title_path}'
    context = {
        "username":username,
        "first_name":first_name,
        "last_name":last_name,
        "email":email,
        "password":password,
        "app_name":default_title_path,
        "current_year":2024,
        "logo_url": default_image_path,
        "create_or_reset":"account has been registered"
    }
    html_content = render_to_string('main_app/gmail_send.html', context)

    send_html_email(to_email, subject, html_content)

    response_data = {
        'code' : '201',
        'message': 'User registered successfully',
        'data': []
    }

    return JsonResponse(response_data, status=status.HTTP_201_CREATED)

@swagger_auto_schema(method='post', operation_description="User for login", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'username': openapi.Schema(type=openapi.TYPE_STRING, description='User Name'),
                            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([])  # Disable permission checks for this specific view
def user_login(request):
    username = request.data['username']
    entered_password = request.data['password']

    # Check if the username and password match in CustomUser
    try:
        user = CustomUser.objects.get(Q(username=username) | Q(email=username))
        print(entered_password, user.password)
        if not check_password(entered_password, user.password):
            response_data = {
                'code' : '401',
                'message': 'Invalid credentials.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        secret_key = secret_key_token
        payload = {
            'user_id': user.id,
            'username': user.username,
            # Add other claims as needed
            'exp': datetime.utcnow() + timedelta(hours=24)  # Set expiration time to 24 hours from now
        }

        # Generate the JWT token
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        user.remember_token = token
        user.otp_number = None
        user.save()
        
        response_data = {
            'code' : '200',
            'message': 'Login successful',
            'data': {
                'token':token,
            }
        }
        return JsonResponse(response_data, status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        response_data = {
            'code' : '401',
            'message': 'Invalid credentials',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    
@swagger_auto_schema(method='post', operation_description="User who forgot their password", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([])  # Disable permission checks for this specific view
def forgot_password(request):
    email = request.data['email']  

    # Check if the email exists in CustomUser
    try:
        user = CustomUser.objects.get(email=email)
        # Generate a 6-digit random number
        otp_number_generated = ''.join(random.choice('0123456789') for _ in range(6))

        user.otp_number=otp_number_generated
        # Update the CustomUser instance
        user.save()

        default_image_path = default_variables.THUMBNAIL_ICON_REACT()
        default_title_path = default_variables.GMAIL_WEBSITE_TITLE
        to_email = email
        subject = f'OTP Sent Successfully! {default_title_path}'
        context = {
            "username":user.username,
            "email":email,
            "otp":otp_number_generated,
            "app_name":default_title_path,
            "current_year":datetime.now().year,  # extracts only  Current year
            "logo_url": default_image_path,
            "create_or_reset":"OTP has been sent"
        }
        html_content = render_to_string('main_app/gmail_otp_sent.html', context)

        send_html_email(to_email, subject, html_content)

        response_data = {
            'code' : '201',
            'message': 'OTP Sent Successfully.',
            'data': []
        }

        return JsonResponse(response_data, status=status.HTTP_201_CREATED)
    except CustomUser.DoesNotExist:
        response_data = {
            'code' : '404',
            'message': 'User not found',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(method='post', operation_description="User who forgot their password update using OTP", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address'),
                            'otp': openapi.Schema(type=openapi.TYPE_INTEGER, description='OTP number'),
                            'confirm': openapi.Schema(type=openapi.TYPE_STRING, description='password'),
                            'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description='confirm password'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([])  # Disable permission checks for this specific view
def forgot_password_update_by_otp(request):
    email = request.data['email']
    otp = request.data['otp']
    password = request.data['password']
    confirm_password = request.data['confirm_password']  

    # Check if the email exists in CustomUser
    try:
        user = CustomUser.objects.get(email=email)

        if user.otp_number == otp:
            if password == confirm_password:
                user.password = password
                user.otp_number = None
                user.save()
                response_data = {
                    'code' : '201',
                    'message': 'Password Updated Successfully',
                    'data': []
                }

                return JsonResponse(response_data, status=status.HTTP_201_CREATED)
            else:
                response_data = {
                    'code' : '404',
                    'message': 'password and confirm_password not matching.',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
        else:
            response_data = {
                'code' : '404',
                'message': 'OTP for user not found or not match.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

    except CustomUser.DoesNotExist:
        response_data = {
            'code' : '404',
            'message': 'User not found',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)  

@swagger_auto_schema(
    method='get',
    operation_description="User Info",
    tags=['app-user'],
    responses={200: 'OK'},
)
@api_view(['GET'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token()
def logout_view(request):
    if request.method == 'GET':
        token_get = extract_token(request)
        # token_get = request.data['token']  # You might use email or any other identifier

        # Check if the username exists in CustomUser
        try:
            user = CustomUser.objects.get(remember_token=token_get)
            user.remember_token = ""
            user.otp_number = None
            # Update the CustomUser instance
            user.save()
            response_data = {
                'code' : '201',
                'message': 'Logout Successfully',
                'data': []
            }

            return JsonResponse(response_data, status=status.HTTP_201_CREATED)
        except CustomUser.DoesNotExist:
            response_data = {
                'code' : '404',
                'message': 'User not found',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
        
@swagger_auto_schema(method='post', operation_description="User who forgot their password", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address'),
                            'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='New Password'),
                            'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description='Confirm Password'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token()
def reset_password(request):
    token_get = extract_token(request)
    new_password = request.data['new_password']
    confirm_password = request.data['new_password']

    # Check if the username exists in CustomUser
    try:
        user = CustomUser.objects.get(remember_token=token_get)
    except CustomUser.DoesNotExist:
        response_data = {
            'code' : '404',
            'message': 'User not found',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

    # # Check if the answer to the security question is correct
    # if user.security_answer != answer:
    #     return JsonResponse({'error': 'Incorrect answer to security question'}, status=status.HTTP_401_UNAUTHORIZED)

    if new_password == confirm_password:
        user.password = new_password
        user.otp_number = None
        user.save()
        response_data = {
            'code' : '201',
            'message': 'Password Reset Successfully',
            'data': []
        }

        return JsonResponse(response_data, status=status.HTTP_201_CREATED)
    else:
        response_data = {
            'code' : '404',
            'message': 'new_password and confirm_password not matching.',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

#client and user list page
@swagger_auto_schema(
    method='get',
    operation_description="Client and Users list",
    tags=['app-user'],
    responses={200: 'OK'},
)
@api_view(['GET'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin','Engineer'])
def client_and_users_list(request):
    if request.method == 'GET':
        # Extract token from request
        token_get = extract_token(request)

        # Validate token existence
        if not token_get:
            return JsonResponse({
                'code': '401',
                'message': 'Authentication token missing or invalid',
                'data': []
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Assuming the token corresponds to a valid user (use remember_token or any other method)
        try:
            #extracting logged in user's data
            user = CustomUser.objects.get(remember_token=token_get)

            # If user found, return the role
            response_data = {
                'code': '200',
                'message': "Logged in user's role",
                'data': {
                    'role': user.role
                }
            }
            return JsonResponse(response_data, status=status.HTTP_200_OK)
        
        except CustomUser.DoesNotExist:
            # Handle case where user is not found with the given token
            return JsonResponse({
                'code': '404',
                'message': 'User not found',
                'data': []
            }, status=status.HTTP_404_NOT_FOUND)
        
    else:
        # Handle invalid HTTP methods
        return JsonResponse({
            "code": "422",
            "message": "Please try with a valid request method",
            "data": []
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

#Engineer display list page
@swagger_auto_schema(
    method='get',
    operation_description="Engineers list",
    tags=['app-user'],
    responses={200: 'OK'},
)
@api_view(['GET'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin','Admin'])
def clients_engineer_list(request):
    if request.method == 'GET':
        # Extract token from request
        # user_get  = request.data.get("id",None)
        token_get = extract_token(request)
        print(token_get)
        # Validate token existence
        if not token_get:
            return JsonResponse({
                'code': '401',
                'message': 'Authentication token missing or invalid',
                'data': []
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Assuming the token corresponds to a valid user (use remember_token or any other method)
        
        try:
            user_obj = CustomUser.objects.get(remember_token=token_get) 
            
            if user_obj.role == "SuperAdmin":
                admin_list = CustomUser.objects.get(role="Admin",manager=user_obj.id)        
                Engineers = CustomUser.objects.filter(role='Engineer' , manager=admin_list.id)
                show_admin = admin_list.username   # for message that shown while successfull search

            
            elif user_obj.role == "Admin":
                Engineers = CustomUser.objects.filter(role='Engineer' , manager=user_obj.id)
                show_admin = user_obj.username 
            
            Engineer_data = [
                {
                'id':Engineer.id,
                'user_name': Engineer.username,
                'first_name': Engineer.first_name,
                'last_name': Engineer.last_name,
                'email': Engineer.email,
                'is_active':Engineer.is_active
                }
                for Engineer in Engineers   #list comprehension
            ]
        # If user found, return the role
            response_data = {
                'code': '200',
                'message': f"all of the Engineers records added by Admin -- {show_admin}",
                'data': Engineer_data
                
            }
            return JsonResponse(response_data, status=status.HTTP_200_OK)
            
        
        except CustomUser.DoesNotExist:
            # Handle case where user is not found with the given token
            return JsonResponse({
                'code': '404',
                'message': 'User not found',
                'data': []
            }, status=status.HTTP_404_NOT_FOUND)
        
    else:
        # Handle invalid HTTP methods
        return JsonResponse({
            "code": "422",
            "message": "Please try with a valid request method",
            "data": []
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

#devices and sensors display list page
@swagger_auto_schema(
    method='post',
    operation_description="Engineers list",
    tags=['app-user'],
    responses={200: 'OK'},
)
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin','Admin','User','Engineer'])
def devices_and_sensors(request):
    if request.method == 'POST':
        # Extract token and id from request
        token_get = extract_token(request)
        user_id = request.data.get('id', None)
        # Validate token existence
        if not token_get:
            return JsonResponse({
                'code': '401',
                'message': 'Authentication token missing or invalid',
                'data': []
            }, status=status.HTTP_401_UNAUTHORIZED)
        #requested user's object
        requested_user_obj=CustomUser.objects.get(id=user_id)
        #object of the user who is logged in
        user_obj = CustomUser.objects.get(remember_token=token_get)
        #making validations as per the role of requesting user's goal
        if requested_user_obj.role == 'User':
            if user_obj.role == 'User': #done
                if user_id != user_obj.id:
                    response_data={
                    'code':'403',
                    'message':"you can't access other user's data",
                    'data':''
                    }
                    return JsonResponse(response_data,status=status.HTTP_403_FORBIDDEN)
            elif user_obj.role == 'Engineer':
                if user_obj.manager.id != requested_user_obj.manager.id:
                    response_data={
                        'code':'403',
                        'message':"You don't have authority to access this value",
                        'data':''
                    } 
                    return JsonResponse(response_data,status=status.HTTP_403_FORBIDDEN)
            elif user_obj.role == 'Admin':
                if user_obj.id != requested_user_obj.manager.id:
                    response_data={
                        'code':'403',
                        'message':"You don't have authority to access this value",
                        'data':''
                    }
                    return JsonResponse(response_data,status=status.HTTP_403_FORBIDDEN)
            elif user_obj.role == 'SuperAdmin':
                admin_obj = CustomUser.objects.get(id=requested_user_obj.manager.id)
                if user_obj.id != admin_obj.manager.id:
                    response_data={
                        'code':'403',
                        'message':"You don't have authority to access this value",
                        'data':''
                    }
                    return JsonResponse(response_data,status=status.HTTP_403_FORBIDDEN)
        else:
            response_data={
                'code':'403',
                'message':"You don't have authority to access this value",
                'data':''
            }
            return JsonResponse(response_data,status=status.HTTP_403_FORBIDDEN)
        try:
            
            
            # Fetch devices and sensors data for the logged-in user
            heatpump_devices_obj = heatpump_devices_info.objects.filter(fk_user=user_id)
            heatpump_sensors_status_obj = default_sensors_values.objects.filter(fk_user=user_id)

            rasp_id_by_user = get_object_or_404(CustomUser, id=user_id)
            latest_sensors_data = sensors_data.objects.filter(
                fk_heatpump_sensor__fk_user=user_id
            ).values('fk_heatpump_sensor').annotate(
                latest_id=Max('id')
            ).values_list('latest_id', flat=True)

            heatpump_sensors_data_obj = sensors_data.objects.filter(pk__in=latest_sensors_data)

            # Initialize dictionaries for devices and sensors
            heatpump_devices_dict = {
                'fan': False,
                'pump': False,
                'compressor': False,
                'heater': False,
            }

            heatpump_sensors_dict = {
                'temperature': 0,
                'voltage': 0,
                'watt': 0,
                'high_pressure': 0,
                'low_pressure': 0,
            }

            heatpump_sensors_current_status_dict = {
                'temperature': 0,
                'voltage': 0,
                'watt': 0,
                'high_pressure': 0,
                'low_pressure': 0,
            }

            # Populate dictionaries with data
            for sensor_data in heatpump_sensors_data_obj:
                heatpump_sensors_dict[sensor_data.fk_heatpump_sensor.sensor] = sensor_data.data

            for device in heatpump_devices_obj:
                heatpump_devices_dict[device.device] = device.status

            for sensor_status in heatpump_sensors_status_obj:
                heatpump_sensors_current_status_dict[sensor_status.sensor] = sensor_status.current_value

            # Prepare response
            context = {
                'user_id': user_id,
                'heatpump_devices_dict': heatpump_devices_dict,
                'heatpump_sensors_dict': heatpump_sensors_dict,
                'heatpump_sensors_current_status_dict': heatpump_sensors_current_status_dict,
                'rasp_id_by_user': rasp_id_by_user.raspberry_id,
            }

            response_data = {
                'code': '200',
                'message': 'Successfully fetched devices and sensors records',
                'data': context
            }
            return JsonResponse(response_data, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            # Handle case where user is not found
            return JsonResponse({
                'code': '404',
                'message': 'User not found',
                'data': []
            }, status=status.HTTP_404_NOT_FOUND)

    else:
        # Handle invalid HTTP methods
        return JsonResponse({
            "code": "422",
            "message": "Please try with a valid request method",
            "data": []
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

@swagger_auto_schema(
    method='get',
    operation_description="User Info",
    tags=['app-user'],
    responses={200: 'OK'},
)
@api_view(['GET'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token()
def user_profile_info(request):
    if request.method == 'GET':
        token_get = extract_token(request)

        # Check if the user exists in CustomUser
        try:
            user = CustomUser.objects.get(remember_token=token_get)
            
        except CustomUser.DoesNotExist:
            response_data = {
                'code': '404',
                'message': 'User not found',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
        
        profile_image = user.profile_image.url if user.profile_image else None

        response_data = {
            'code': '200',
            'message': 'User Info.',
            'data': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'email': user.email,
                'phone_number': user.phone_number,
                'address': user.address,
                'profile_image': profile_image
            }
        }
        return JsonResponse(response_data, status=status.HTTP_200_OK)
    else:
        response_data = {
            "code": 422,
            "message": "Please try with valid request method",
            "data": []
        }

        return JsonResponse(response_data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
@swagger_auto_schema(method='post', operation_description="Update user profile", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First Name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last Name'),
                            'role': openapi.Schema(type=openapi.TYPE_STRING, description='Role'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                            'address': openapi.Schema(type=openapi.TYPE_STRING, description='Address'),
                            'profile_image': openapi.Schema(type=openapi.TYPE_STRING, description='Image'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token()
def user_profile_info_update(request):
    firstname_get = request.data.get('first_name', None)
    lastname_get = request.data.get('last_name', None)
    # email_get = request.data.get('email', None)
    # role_get = request.data.get('role', None)
    phone_get = request.data.get('phone_number', None)
    address_get = request.data.get('address', None)
    profile_image = request.FILES.get('profile_image', None)

    # Validation and data retrieval
    min_name_length = 10
    max_name_length = 60
    token_get = extract_token(request)
    user = CustomUser.objects.get(remember_token=token_get)

    if phone_get:
        # Validate phone number format
        phone_number_pattern = re.compile(r'^\(\d{3}\) \d{3}-\d{4}$')
        if not phone_number_pattern.match(phone_get):
            response_data = {
                'code': '400',
                'message': 'Please Enter Valid Mobile Number.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    else:
        phone_get = str(user.phone_number)

    # Populate missing data with existing user data
    firstname_get = firstname_get if firstname_get is not None else str(user.first_name)
    lastname_get = lastname_get if lastname_get is not None else str(user.last_name)
    # email_get = email_get if email_get is not None else str(user.email)
    # role_get = role_get if role_get is not None else str(user.role)
    phone_number_get = phone_get if phone_get is not None else str(user.phone_number)
    address_get = address_get if address_get is not None else str(user.address)

    # Validate name lengths
    if not (min_name_length <= len(firstname_get) <= max_name_length) or \
       not (min_name_length <= len(lastname_get) <= max_name_length):
        response_data = {
            'code': '400',
            'message': 'firstname, lastname should be 2 to 60 characters long.',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

    # Update user profile
    user.first_name = firstname_get
    user.last_name = lastname_get
    # user.email = email_get
    # user.role = role_get
    user.phone_number = phone_number_get
    user.address = address_get
    if profile_image:
        user.profile_image = profile_image

    # Save the changes
    user.save()

    profile_image_url_send = user.profile_image.url if user.profile_image else ''

    default_image_path = default_variables.THUMBNAIL_ICON_REACT()
    default_title_path = default_variables.GMAIL_WEBSITE_TITLE
    to_email = user.email
    subject = f'Account Updated Successfully! {default_title_path}'
    context = {
        "username": user.username,
        "firstname": user.first_name,
        "lastname": user.last_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "address": user.address,
        "app_name": default_title_path,
        "current_year": 2024,
        "logo_url": default_image_path,
        "profile_image_url": profile_image_url_send
    }
    html_content = render_to_string('main_app/profile_edit.html', context)

    send_html_email(to_email, subject, html_content)

    response_data = {
        'code': '201',
        'message': 'Profile updated successfully',
        'data': []
    }

    return JsonResponse(response_data, status=status.HTTP_201_CREATED)
'#'
   
@swagger_auto_schema(method='post', operation_description="Update Temperature", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'temperature': openapi.Schema(type=openapi.TYPE_NUMBER, description='Temperature'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token()
def edit_temperature(request):
    
    current_temperature = request.data.get('current_temperature', None)
    max_temperature = request.data.get('max_temperature', None)

    # print(current_temperature, max_temperature)
    
    if current_temperature == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter Current Temperature',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

    elif max_temperature == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter Max Temperature',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    else:
    
        try:
            user_id = request.data.get('user_id', None)
            token_get = extract_token(request)
            request_user_obj = CustomUser.objects.get(id=user_id)
            if not request_user_obj.role == "User":
                response_data = {
                    'code': '400',
                    'message': f'User Does Not Exist. Please check entered USER ID ',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            user_obj = CustomUser.objects.get(remember_token=token_get)
            if user_obj.role == 'User':
                if user_obj.id != user_id:
                    response_data = {
                        'code': '400',
                        'message': 'User has not permission to update this user.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
                
            elif user_obj.role == 'Engineer':
                if user_obj.manager.id != request_user_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': 'User has not permission to update this user.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif user_obj.role == 'Admin':
                if user_obj.id != request_user_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': 'User has not permission to update this user.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif user_obj.role == 'SuperAdmin':
                admin_obj = CustomUser.objects.get(id=request_user_obj.manager.id)
                if user_obj.id != admin_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': 'User has not permission to update this user.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
                
                user = CustomUser.objects.get(id=user_id)
                temperature_obj = default_sensors_values.objects.get(sensor='temperature',fk_user=user)

                temperature_obj.current_value = current_temperature
                temperature_obj.max_current_value = max_temperature
                temperature_obj.save()
                return Response({"message": "Temperature updated successfully"}, status=200)
        
        except CustomUser.DoesNotExist:
            response_data = {
            'code' : '404',
            'message': 'User Does Not Exist. Please check entered USER ID',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
        # return JsonResponse({'message': 'Temperature updated successfully'}, status=status.HTTP_200_OK)
    


#***********************************************************************************************************
#admin display list page
@swagger_auto_schema(
    method='get',
    operation_description="Admin list",
    tags=['app-user'],
    responses={200: 'OK'},
)
@api_view(['GET'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin'])
def user_admin_list(request):
    if request.method == 'GET':
        # Extract token from request
        
        token_get = extract_token(request)
        
        # Validate token existence
        if not token_get:
            return JsonResponse({
                'code': '401',
                'message': 'Authentication token missing or invalid',
                'data': []
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Assuming the token corresponds to a valid user (use remember_token or any other method)
        try:
            
            user_obj = CustomUser.objects.get(remember_token=token_get)
            # print("user_obj",user_obj.role)
            # print(token_get)    
            # print("*" * 80)    
            # print(user_obj.remember_token)    
            
            user = CustomUser.objects.filter(role='Admin',manager=user_obj)

            admin_data = [
                {
                'id':users.id,
                'user_name': users.username,
                'first_name': users.first_name,
                'last_name': users.last_name,
                'email': users.email,
                'is_active':users.is_active
                }
                for users in user   #list comprehension
            ]
            # If user found, return the role
            response_data = {
                'code': '200',
                'status': 'success',
                'message': "all of the admin records",
                'data': admin_data
                
            }
            return JsonResponse(response_data, status=status.HTTP_200_OK)
        
        except CustomUser.DoesNotExist:
            # Handle case where user is not found with the given token
            return JsonResponse({
                'code': '404',
                'message': 'Admin not found',
                'data': []
            }, status=status.HTTP_404_NOT_FOUND)
        
    else:
        # Handle invalid HTTP methods
        return JsonResponse({
            "code": "422",
            "message": "Please try with a valid request method",
            "data": []
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


# User display list
@swagger_auto_schema(
    method='get',
    operation_description="All Users list",
    tags=['app-user'],
    responses={200: 'OK'},
)
@api_view(['GET'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin', 'Engineer'])
def clients_user_list(request):
    if request.method == 'GET':
        token_get = extract_token(request)
        if not token_get:
            response_data = {
                'code': '401',
                'message': 'Authentication token missing or invalid', 
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)

        #get logged in user's details
        user_obj = CustomUser.objects.get(remember_token=token_get)
        if user_obj.role == 'Engineer':
            user = CustomUser.objects.filter(role='User',manager=user_obj.manager.id)
        elif user_obj.role == 'Admin':
            user = CustomUser.objects.filter(role='User',manager=user_obj.id)
        elif user_obj.role == 'SuperAdmin':
            admin_obj = CustomUser.objects.get(manager=user_obj.id)
            user = CustomUser.objects.filter(role='User',manager=admin_obj.id)
        try:
            
            users_data = [
                {
                    'id':users.id,
                    'user_name': users.username,
                    'first_name': users.first_name,
                    'last_name': users.last_name,
                    'email': users.email,
                    'is_active':users.is_active
                }
                for users in user   #list comprehension
            ]
            
        except CustomUser.DoesNotExist:
            response_data = {
                'code' : '404',
                'message': 'User not found',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
        
        
        
        # if user.image:
        #     user_profile = user.image.url
        # else:
        #     user_profile = None




        response_data = {
            'code' : '200',
            'status' : 'success',
            'message': "Client's User Info.",
            'data': users_data,
        }
        return JsonResponse(response_data, status=status.HTTP_200_OK)
    else:
        response_data = {
        "code": 422,
        "message": "Please try with valid request method",
        "data": []
        }

        return JsonResponse(response_data,status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# update in Engineer by Id
@swagger_auto_schema(method='post', operation_description="Update Enginner profile", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            #  "id" : openapi.Schema(type=openapi.TYPE_STRING, description='id'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First Name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last Name'),
                            'role': openapi.Schema(type=openapi.TYPE_STRING, description='Role'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                            'address': openapi.Schema(type=openapi.TYPE_STRING, description='Address'),
                            'profile_image': openapi.Schema(type=openapi.TYPE_STRING, description='Image'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin'])
def edit_user_engineer(request):
    # todo: reomove this api and make  a common user_edit api where superadmin can edit admin and further and admin can edit engineer and further
    
    engineer_id_get = request.data.get("id",None)
    firstname_get = request.data.get('first_name', None)
    lastname_get = request.data.get('last_name', None)
    # email_get = request.data.get('email', None)
    # role_get = request.data.get('role', None)
    phone_get = request.data.get('phone_number', None)
    address_get = request.data.get('address', None)
    profile_image = request.FILES.get('profile_image', None)

    # Validation and data retrieval
    min_name_length = 10
    max_name_length = 60
    token_get = extract_token(request)
    if not token_get:
        return JsonResponse({'code': '401', 'message': 'Authentication token missing or invalid', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
    
    #logged in user details 
    user_obj = CustomUser.objects.get(remember_token=token_get)
    #engineer details
    engineer_obj = CustomUser.objects.get(id=engineer_id_get)
    #check engineer role
    if engineer_obj.role == 'Engineer':
        #check user role
        if user_obj.role == 'Admin':
            #check user id and engineer manager id
            if user_obj.id != engineer_obj.manager.id:
                return JsonResponse({'code': '401', 'message': 'User does not have permission to update this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                user = CustomUser.objects.get(role='Engineer',manager=user_obj.id,id=engineer_id_get)
        elif user_obj.role == 'SuperAdmin':
            #extract admin manager id
            admin_obj = CustomUser.objects.get(id = engineer_obj.manager.id)
            #check SuperAdmin id and admin manager id are the same or not
            if user_obj.id != admin_obj.manager.id:
                return JsonResponse({'code': '401', 'message': 'User does not have permission to update this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                user = CustomUser.objects.get(role='Engineer',manager=admin_obj.id,id=engineer_id_get)
    else:
        return JsonResponse({'code': '401', 'message': 'You cant edit user details this is only for engineer', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
    
    if phone_get:
        if not len(phone_get) == 10:   
            response_data = {
                'code': '400',
                'message': 'Mobile Number Should be 10 Digit.(Not include +91)',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
        # Validate phone number format
        
        mobile_number_pattern = re.compile(r'^\(\d{3}\) \d{3}-\d{4}$')
        
        if not mobile_number_pattern.match(phone_get):
        
            response_data = {
                'code': '400',
                'message': 'Please Enter Valid Mobile Number.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
        
    else:
        phone_get = str(user.phone_number)
        

    # Populate missing data with existing user data
    firstname_get = firstname_get if firstname_get is not None else str(user.first_name)
    lastname_get = lastname_get if lastname_get is not None else str(user.last_name)
    # email_get = email_get if email_get is not None else str(user.email)
    #role_get = role_get if role_get is not None else str(user.role)
    phone_number_get = phone_get if phone_get is not None else str(user.phone_number)
    address_get = address_get if address_get is not None else str(user.address)

    # Validate name lengths
    if not (min_name_length <= len(firstname_get) <= max_name_length) or \
       not (min_name_length <= len(lastname_get) <= max_name_length):
        response_data = {
            'code': '400',
            'message': 'firstname, lastname should be 2 to 60 characters long.',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    
    # Update user profile
    user.first_name = firstname_get
    user.last_name = lastname_get
    # user.email = email_get
    #user.role = role_get
    user.phone_number = phone_number_get
    user.address = address_get
    if profile_image:
        user.profile_image = profile_image

    # Save the changes
    user.save()

    # profile_image_url_send = user.profile_image.url if user.profile_image else ''

    # default_image_path = default_variables.THUMBNAIL_ICON_REACT()
    # default_title_path = default_variables.GMAIL_WEBSITE_TITLE
    # to_email = user.email
    # subject = f'Engineer Profile Updated Successfully! {default_title_path}'
    # context = {
    #     "username": user.username,
    #     "firstname": user.first_name,
    #     "lastname": user.last_name,
    #     "email": user.email,
    #     "phone_number": user.phone_number,
    #     "address": user.address,
    #     "app_name": default_title_path,
    #     "current_year": 2024,
    #     "logo_url": default_image_path,
    #     "profile_image_url": profile_image_url_send
    # }
    # html_content = render_to_string('main_app/profile_edit.html', context)

    # send_html_email(to_email, subject, html_content)

    response_data = {
        'code': '201',
        'message': "Engineer's Profile updated successfully",
        'data': []
    }

    return JsonResponse(response_data, status=status.HTTP_201_CREATED)


#########################################################################################################
@swagger_auto_schema(
    method='delete',
    operation_description="Delete Admin User",
    tags=['app-user'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
        },
        required=['id']
    )
)
@api_view(['DELETE'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([])
@authenticate_with_token(allowed_roles=['SuperAdmin'])
def delete_user_admin(request):
    # Extract the ID from the request
    id = request.data.get('id', None)
    
    # Validate the input ID
    if not id:
        return JsonResponse({
            'code': '400',
            'message': 'ID is required to delete a user.',
            'data': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Find the user by ID
        user = CustomUser.objects.get(id=id)
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'code': '404',
            'message': 'User not found.',
            'data': []
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Delete the user
    user.delete()
    
    # Success response
    return JsonResponse({
        'code': '200',
        'message': 'User deleted successfully.',
        'data': {'id': id}
    }, status=status.HTTP_200_OK)


##########################################################################################################


######common api for deleting all users ######################################################################
@swagger_auto_schema(
    method='delete',
    operation_description="common api for deleting users",
    tags=['app-user'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
        },
        required=['id']
    )
)
@api_view(['DELETE'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([])
@authenticate_with_token(allowed_roles=['SuperAdmin','Admin'])
def delete_user(request):
    user_id = request.data.get('id',None)
    token_get = extract_token(request)
    if not token_get:
        return JsonResponse({'code': '401', 'message': 'Authentication token missing or invalid', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
    if not user_id:
        return JsonResponse({'code': '400', 'message': 'User ID is required to delete a user.', 'data': []}, status=status.HTTP_400_BAD_REQUEST)
    
    #logged in user's object
    user_obj = CustomUser.objects.get(remember_token=token_get)
    #requested user's object
    requested_user_obj = CustomUser.objects.get(id=user_id)

    if not user_obj.id:
        response_data = {
            'code': '401',
            'message': 'User not found.',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)

    match user_obj.role:
        case 'SuperAdmin':
            match requested_user_obj.role:
                case 'User':
                    admin_obj = CustomUser.objects.get(id = requested_user_obj.manager.id)
                    if user_obj.id != admin_obj.manager.id:
                        response_data = {
                            'code': '401',
                            'message': 'User does not have permission to delete this user.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        requested_user_obj.delete()
                        response_data = {
                            'code': '200',
                            'message': 'User deleted successfully.',
                            'data': {'id': user_id}
                        }
                        return JsonResponse(response_data, status=status.HTTP_200_OK)
                case 'Engineer':
                    admin_obj = CustomUser.objects.get(id = requested_user_obj.manager.id)
                    if user_obj.id != admin_obj.manager.id:
                        response_data = {
                            'code': '401',
                            'message': 'User does not have permission to delete this user.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        requested_user_obj.delete()
                        response_data = {
                            'code': '200',
                            'message': 'User deleted successfully.',
                            'data': {'id': user_id}
                        }
                        return JsonResponse(response_data, status=status.HTTP_200_OK)
                case 'Admin':
                    if user_obj.id != requested_user_obj.manager.id:
                        response_data = {
                            'code': '401',
                            'message': 'User does not have permission to delete this user.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        requested_user_obj.delete()
                        response_data = {
                            'code': '200',
                            'message': 'User deleted successfully.',
                            'data': {'id': user_id}
                        }
                        return JsonResponse(response_data, status=status.HTTP_200_OK)
                case _:
                    response_data = {
                        'code': '401',
                        'message': 'User does not have permission to delete this user.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        case 'Admin':
            match requested_user_obj.role:
                case 'User':
                    if user_obj.id != requested_user_obj.manager.id:
                        response_data = {
                            'code': '401',
                            'message': 'User does not have permission to delete this user.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        requested_user_obj.delete()
                        response_data = {
                            'code': '200',
                            'message': 'User deleted successfully.',
                            'data': {'id': user_id}
                        }
                        return JsonResponse(response_data, status=status.HTTP_200_OK)
                case 'Engineer':
                    if user_obj.id != requested_user_obj.manager.id:
                        response_data = {
                            'code': '401',
                            'message': 'User does not have permission to delete this user.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        requested_user_obj.delete()
                        response_data = {
                            'code': '200',
                            'message': 'User deleted successfully.',
                            'data': {'id': user_id}
                        }
                        return JsonResponse(response_data, status=status.HTTP_200_OK)
                case _:
                    response_data = {
                        'code': '401',
                        'message': 'User does not have permission to delete this user.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        case _:
            response_data = {
                'code': '401',
                'message': 'User does not have permission to delete this user.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        

# @swagger_auto_schema(
#     method='delete',
#     operation_description="common api for deleting users",
#     tags=['app-user'],
#     request_body=openapi.Schema(
#         type=openapi.TYPE_OBJECT,
#         properties={
#             'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
#         },
#         required=['id']
#     )
# )
# @api_view(['DELETE'])
# @authentication_classes([])  # Disable authentication for this specific view
# @permission_classes([])
# @authenticate_with_token(allowed_roles=['SuperAdmin','Admin'])
# def delete_user(request):
#     user_id = request.data.get('id', None)
#     token_get = extract_token(request)

#     if not token_get:
#         return JsonResponse({'code': '401', 'message': 'Authentication token missing or invalid', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)

#     if not user_id:
#         return JsonResponse({'code': '400', 'message': 'User ID is required to delete a user.', 'data': []}, status=status.HTTP_400_BAD_REQUEST)

#     # Logged-in user's object
#     user_obj = CustomUser.objects.get(remember_token=token_get)

#     # Requested user's object
#     requested_user_obj = CustomUser.objects.get(id=user_id)

#     if not user_obj.id:
#         return JsonResponse({'code': '401', 'message': 'User not found.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)

#     if user_obj.role == 'SuperAdmin':
#         if requested_user_obj.role == 'User':
#             admin_obj = CustomUser.objects.get(id=requested_user_obj.manager.id)
#             if user_obj.id != admin_obj.manager.id:
#                 return JsonResponse({'code': '401', 'message': 'User does not have permission to delete this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
#             else:
#                 requested_user_obj.delete()
#                 return JsonResponse({'code': '200', 'message': 'User deleted successfully.', 'data': {'id': user_id}}, status=status.HTTP_200_OK)

#         elif requested_user_obj.role == 'Engineer':
#             admin_obj = CustomUser.objects.get(id=requested_user_obj.manager.id)
#             if user_obj.id != admin_obj.manager.id:
#                 return JsonResponse({'code': '401', 'message': 'User does not have permission to delete this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
#             else:
#                 requested_user_obj.delete()
#                 return JsonResponse({'code': '200', 'message': 'User deleted successfully.', 'data': {'id': user_id}}, status=status.HTTP_200_OK)

#         elif requested_user_obj.role == 'Admin':
#             if user_obj.id != requested_user_obj.manager.id:
#                 return JsonResponse({'code': '401', 'message': 'User does not have permission to delete this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
#             else:
#                 requested_user_obj.delete()
#                 return JsonResponse({'code': '200', 'message': 'User deleted successfully.', 'data': {'id': user_id}}, status=status.HTTP_200_OK)

#         else:
#             return JsonResponse({'code': '401', 'message': 'User does not have permission to delete this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)

#     elif user_obj.role == 'Admin':
#         if requested_user_obj.role == 'User':
#             if user_obj.id != requested_user_obj.manager.id:
#                 return JsonResponse({'code': '401', 'message': 'User does not have permission to delete this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
#             else:
#                 requested_user_obj.delete()
#                 return JsonResponse({'code': '200', 'message': 'User deleted successfully.', 'data': {'id': user_id}}, status=status.HTTP_200_OK)

#         elif requested_user_obj.role == 'Engineer':
#             if user_obj.id != requested_user_obj.manager.id:
#                 return JsonResponse({'code': '401', 'message': 'User does not have permission to delete this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)
#             else:
#                 requested_user_obj.delete()
#                 return JsonResponse({'code': '200', 'message': 'User deleted successfully.', 'data': {'id': user_id}}, status=status.HTTP_200_OK)

#         else:
#             return JsonResponse({'code': '401', 'message': 'User does not have permission to delete this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)

#     else:
#         return JsonResponse({'code': '401', 'message': 'User does not have permission to delete this user.', 'data': []}, status=status.HTTP_401_UNAUTHORIZED)

##########################################################################################################

#########common api for editing all users ################################################################
@swagger_auto_schema(method='post', operation_description="common api for editing users", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            #  "id" : openapi.Schema(type=openapi.TYPE_STRING, description='id'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First Name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last Name'),
                            'role': openapi.Schema(type=openapi.TYPE_STRING, description='Role'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                            'address': openapi.Schema(type=openapi.TYPE_STRING, description='Address'),
                            'profile_image': openapi.Schema(type=openapi.TYPE_STRING, description='Image'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin'])
def edit_user(request):
    #getting data from request
    id_get = request.data.get('id',None)
    first_name_get = request.data.get('first_name',None)
    last_name_get = request.data.get('last_name',None)
    phone_number_get = request.data.get('phone_number',None)
    email_get = request.data.get('email', None)
    role_get = request.data.get('role', None)
    manager_id_get = request.data.get('manager_id',None)
    address_get = request.data.get('address',None)
    profile_image_get = request.FILES.get('profile_image', None)


    min_name_length = 10
    max_name_length = 60
    #extracting token
    token_get = extract_token(request)
    if not token_get:
        response_data = {
            'code': '401',
            'message': 'Authentication token missing or invalid', 
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    
    #logged in user's object
    user_obj = CustomUser.objects.get(remember_token=token_get)

    #requested user's object
    requested_user_obj = CustomUser.objects.get(id=id_get)


    match requested_user_obj.role:
        case 'User':
            match user_obj.role:
                case 'Admin':#completely working
                    admin_obj = CustomUser.objects.get(id=manager_id_get)
                    if admin_obj.id == user_obj.id:
                        user = CustomUser.objects.get(id=id_get)
                    else:
                        response_data = {
                            'code': '401',
                            'message': 'you dont have authority to assign this admin',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                case 'SuperAdmin':#completely working
                    admin_obj = CustomUser.objects.filter(manager=user_obj.id).values_list('id',flat=True)
                    if manager_id_get not in admin_obj:
                        response_data = {
                            'code': '401',
                            'message': 'as a superadmin you cant assign admin of other superadmin.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        user = CustomUser.objects.get(id=id_get)
        case 'Engineer':
            match user_obj.role:
                case 'Admin':#done
                    admin_obj = CustomUser.objects.get(id=manager_id_get)
                    print("admin_obj:::",admin_obj.id)
                    print("user_obj:::",user_obj.id)
                    if admin_obj.id != user_obj.id:
                        response_data = {
                            'code': '401',
                            'message': 'as an admin you cant assign engineer of other admin.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        user = CustomUser.objects.get(id=id_get)
                case 'SuperAdmin':#done
                    admin_obj = CustomUser.objects.filter(role='Admin',manager=user_obj.id).values_list('id',flat=True)
                    print("admin_obj:::",admin_obj)
                    if manager_id_get not in admin_obj:
                        response_data = {
                            'code': '401',
                            'message': 'as a superadmin you cant assign admin of other superadmin.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        user = CustomUser.objects.get(id=id_get)
        case 'Admin':
            match user_obj.role:
                case 'SuperAdmin':#done
                    if manager_id_get != user_obj.id:
                        response_data = {
                            'code': '401',
                            'message': 'as a superadmin you cant assign admin to other superadmin.',
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        user = CustomUser.objects.get(id=id_get)
                case _:
                    response_data = {
                        'code': '401',
                        'message': 'User does not have permission to update this user.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        case _:
            response_data = {
                'code': '401',
                'message': 'you cant edit this user.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    






    #using switch case to handle requests as per role
    # match requested_user_obj.role:
    #     case 'User':
    #         if user_obj.role == 'Admin':
    #             if user_obj.id != requested_user_obj.manager.id:
    #                 response_data = {
    #                     'code': '401',
    #                     'message': 'User does not have permission to update this user.',
    #                     'data': [] 
    #                 }
    #                 return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    #             else:
    #                 user = CustomUser.objects.get(id=id_get)
    #         elif user_obj.role == 'SuperAdmin':
    #             admin_obj = CustomUser.objects.get(id=requested_user_obj.manager.id)
    #             if user_obj.id != admin_obj.manager.id:
    #                 response_data = {
    #                     'code': '401',
    #                     'message': 'User does not have permission to update this user.',
    #                     'data': []
    #                 }
    #                 return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    #             else:
    #                 user = CustomUser.objects.get(id=id_get)
    #     case 'Engineer':
    #         if user_obj.role == 'Admin':
    #             if user_obj.id != requested_user_obj.manager.id:
    #                 response_data = {
    #                     'code': '401',
    #                     'message': 'User does not have permission to update this user.',
    #                     'data': []
    #                 }
    #                 return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    #             else:
    #                 user = CustomUser.objects.get(id=id_get)
    #         elif user_obj.role == 'SuperAdmin':
    #             admin_obj = CustomUser.objects.get(id=requested_user_obj.manager.id)
    #             if user_obj.id != admin_obj.manager.id:
    #                 response_data = {
    #                     'code': '401',
    #                     'message': 'User does not have permission to update this user.',
    #                     'data': []
    #                 }
    #                 return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    #             else:
    #                 user = CustomUser.objects.get(id=id_get)
    #     case 'Admin':
    #         if user_obj.role == 'SuperAdmin':
    #             if user_obj.id != requested_user_obj.manager.id:
    #                 response_data = {
    #                     'code': '401',
    #                     'message': 'User does not have permission to update this user.',
    #                     'data': []
    #                 }
    #                 return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    #             else:
    #                 user = CustomUser.objects.get(id=id_get)
    #         else:
    #             response_data = {
    #                 'code': '401',
    #                 'message': 'User does not have permission to update this user.',
    #                 'data': []
    #             }
    #             return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    #     case _:
    #         response_data = {
    #             'code': '401',
    #             'message': 'User does not have permission to update this user.',
    #             'data': []
    #         }
    #         return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
 
    #validating phone number
    if not len(phone_number_get) == 10:   
        response_data = {
            'code': '400',
            'message': 'Mobile Number Should be of 10 Digit.',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    

    #populating missing data
    first_name_get = first_name_get if first_name_get is not None else str(user.first_name)
    last_name_get = last_name_get if last_name_get is not None else str(user.last_name)
    phone_number_get = phone_number_get if phone_number_get is not None else str(user.phone_number)
    address_get = address_get if address_get is not None else str(user.address) 
    email_get = email_get if email_get is not None else str(user.email)
    role_get = role_get if role_get is not None else str(user.role)

    #validating first_name and last_name length 
    if not (min_name_length <= len(first_name_get+last_name_get) <= max_name_length):
        response_data = {
            'code': '400',
            'message': 'firstname, lastname should be 2 to 60 characters long.',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    
    #updating user profile
    user.first_name = first_name_get
    user.last_name = last_name_get
    user.phone_number = phone_number_get
    user.address = address_get
    user.email = email_get
    user.role = role_get
    if profile_image_get:
        user.profile_image = profile_image_get

    #saving changes
    user.save()

    response_data = {
        'code': '201',
        'message': "User's Profile updated successfully",
        'data': []
    }

    return JsonResponse(response_data, status=status.HTTP_201_CREATED)

#########################################################################################################
############ manager list api ###########################################################################
@swagger_auto_schema(
    method='get',
    operation_description="get manager list",
    tags=['app-user'],
    responses={200: 'OK'},
)
@api_view(['get'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin'])
def manager_list(request):
    token_get = extract_token(request)
    if not token_get:
        response_data = {
            'code': '401',
            'message': 'Authentication token missing or invalid', 
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    #logged in user's object
    user_obj = CustomUser.objects.get(remember_token=token_get)

    if not user_obj:
        response_data = {
            'code': '401',
            'message': 'User not found', 
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)

    match user_obj.role:
        case 'SuperAdmin':
            managers = CustomUser.objects.filter(role='Admin',manager=user_obj.id)
            json_data=[
                {
                    'admin_id': manager.id,
                    'admin_username': manager.username,
                }
                for manager in managers
            ]
            response_data = {
                'code': '200',
                'message': "Admin's list",
                'data': json_data
            }
            return JsonResponse(response_data, status=status.HTTP_200_OK)
        case 'Admin':
            managers = CustomUser.objects.get(id=user_obj.id)
            json_data=[
                {
                    'admin_id': managers.id,
                    'admin_username': managers.username,
                }
            ]
            response_data = {
                'code': '200',
                'message': "Admin's data",
                'data': json_data
            }
            return JsonResponse(response_data, status=status.HTTP_200_OK)
        

##########################################################################################################

##########common api for adding all users ################################################################
@swagger_auto_schema(method='post', operation_description="Edit Admin profile", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            # 'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First Name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last Name'),
                            'role': openapi.Schema(type=openapi.TYPE_STRING, description='Role'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                            'address': openapi.Schema(type=openapi.TYPE_STRING, description='Address'),
                            'manager_id': openapi.Schema(type=openapi.TYPE_STRING, description='Manager ID'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin'])
def add_user(request):

    token_get = extract_token(request)
    #logged in user's object
    user_obj = CustomUser.objects.get(remember_token=token_get)
    
    if not token_get:
        response_data = {
            'code': '401',
            'message': 'Authentication token missing or invalid', 
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user_obj:
        response_data = {
            'code': '401',
            'message': 'User not found', 
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
    
    #extracting data from form
    form_type=request.data.get('form_type',None)
    username = request.data.get('username',None)
    first_name = request.data.get('first_name',None)
    last_name = request.data.get('last_name',None)
    email = request.data.get('email',None)
    phone_number = request.data.get('phone_number',None)
    address = request.data.get('address',None)
    manager = int(request.data.get('manager',None))
    password = request.data.get('password',None)

    min_username_length = 3
    min_name_length = 2
    max_name_length = 50 

    #checking username and first,last name length
    if not len(phone_number) == 10:
        response_data = {
            'code' : '400',
            'message': 'Please Enter Valid Mobile Number.',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
    if not (min_username_length <= len(username) <= max_name_length) or \
   not (min_name_length <= len(first_name) <= max_name_length) or \
   not (min_name_length <= len(last_name) <= max_name_length):
        response_data = {
            'code' : '400',
            'message': 'username, first_name, last_name should be 2 to 50 character long.',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    # Check if the username and email already exist
    if CustomUser.objects.filter(username=username).exists() or CustomUser.objects.filter(email=email).exists():
        response_data = {
            'code' : '400',
            'message': 'Username or Email Already Exists',
            'data': []
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    # Generate a random password
    encrypt_password = make_password(password)
    try:
        requested_manager_obj = CustomUser.objects.get(id=manager)  #taking the object of the manager who is being assiegned in the manager field
        # print("requested_manager_obj:::",requested_manager_obj)
        # print("user_obj:::",user_obj.id)
        is_manager_true = True
    except:
        is_manager_true = False
        if not is_manager_true:
            response_data = {
                'code' : '400',
                'message': 'Manager is Not Found.',
                'data': []
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
    print("requested_manager_obj.role:::",requested_manager_obj.role)

    match user_obj.role:
        case 'SuperAdmin':
            match form_type:
                case 'Admin':
                    user_data = CustomUser(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        address=address,
                        phone_number=phone_number,
                        password=encrypt_password,
                        role=form_type,
                        manager=user_obj, #passing the manager object to the manager field
                    )
                    # Save the CustomUser instance
                    user_data.save()

                    response_data = {
                        'code': '201',
                        'message': "Admin Added Successfully",
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_201_CREATED)

                case 'Engineer':
                    #these are the admins who have the same manager id (superadmin's id)
                    admins = CustomUser.objects.filter(role='Admin',manager=user_obj.id).values_list('id', flat=True)
                    print("admins:::",admins)#list of admins
                    print("requested_manager_obj.id:::",requested_manager_obj.id) #here the requested manager is the superadmin
                    if requested_manager_obj.id in admins:
                        user_data = CustomUser(
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            address=address,
                            phone_number=phone_number,
                            password=encrypt_password,
                            role=form_type,
                            manager=requested_manager_obj,
                        )
                        # Save the CustomUser instance
                        user_data.save()

                        response_data = {
                            'code': '201',
                            'message': "Engineer Added Successfully",
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_201_CREATED)
                    else:
                        response_data = {
                            'code': '401',
                            'message': "invalid admin id to add engineer",
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
                case 'User':
                    admins = CustomUser.objects.filter(manager=user_obj.id).values_list('id',flat=True)
                    print("admins:::",admins)
                    print("requested_manager_obj.id:::",requested_manager_obj.id)
                    if requested_manager_obj.id in admins:
                        user_data = CustomUser(
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            address=address,
                            phone_number=phone_number,
                            password=encrypt_password,
                            role=form_type,
                            manager=requested_manager_obj,
                        )
                        user_data.save()

                        response_data = {
                            'code': '201',
                            'message': "User Added Successfully",
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_201_CREATED)
                    else:
                        response_data = {
                            'code': '401',
                            'message': "couldn't add user because of invalid admin id",
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED) 
                case _:
                    response_data = {
                        'code': '401',
                        'message': "invalid form type or role",
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        case 'Admin':
            match form_type:
                case 'Engineer':
                    user_data = CustomUser(
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            address=address,
                            phone_number=phone_number,
                            password=encrypt_password,
                            role=form_type,
                            manager=user_obj,
                        )   
                    user_data.save()
                    response_data = {
                            'code': '201',
                            'message': "User Added Successfully",
                            'data': []
                        }
                    return JsonResponse(response_data, status=status.HTTP_201_CREATED)

                case 'User':
                        user_data = CustomUser(
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            address=address,
                            phone_number=phone_number,
                            password=encrypt_password,
                            role=form_type,
                            manager=user_obj,
                        )   
                        user_data.save()
                        response_data = {
                            'code': '201',
                            'message': "User Added Successfully",
                            'data': []
                        }
                        return JsonResponse(response_data, status=status.HTTP_201_CREATED)
                case _:
                    response_data = {
                        'code': '401',
                        'message': "invalid form type or role",
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        case _:
            response_data = {
                'code': '401',
                'message': 'User does not have authority to add user.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
   
   

#***********************************************************************************************************
# @swagger_auto_schema(
#     method='get',
#     operation_description="Get slider images",
#     tags=['app-user'],
#     responses={200: 'OK'},
# )
# @api_view(['GET'])
# def get_slider_images(request):


#     response_data = {
#         'code': '201',
#         'message': 'Temprature updated successfully',
#         'data': []
#     }

#     return JsonResponse(response_data, status=status.HTTP_201_CREATED)



# @api_view(['GET'])
# def get_terms_and_condition(request):

#     response_data = {
#         'code' : '200',
#         'message': 'Terms and condition.',
#         'data': {}
#     }
#     all_slider_obj = heatpump_devices_info.objects.all().last()
#     plans_data_save = {
#         'title':all_slider_obj.title,
#         'description':all_slider_obj.description
#     }
#     response_data['data'] = plans_data_save

#     return JsonResponse(response_data, status=status.HTTP_200_OK)
"##############################################################################################"
@swagger_auto_schema(method='post', operation_description="Edit Admin profile", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            # 'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First Name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last Name'),
                            'role': openapi.Schema(type=openapi.TYPE_STRING, description='Role'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                            'address': openapi.Schema(type=openapi.TYPE_STRING, description='Address'),
                            'manager_id': openapi.Schema(type=openapi.TYPE_STRING, description='Manager ID'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin'])
def edit_user_admin(request):
    id = request.data.get('id', None)
    firstname_get = request.data.get('first_name', None)
    lastname_get = request.data.get('last_name', None)
    email_get = request.data.get('email', None)
    role_get = request.data.get('role', None)
    phone_get = request.data.get('phone_number', None)
    address_get = request.data.get('address', None)
    manager_id_get = request.data.get('manager_id', None)

    # Validation and data retrieval
    min_name_length = 2  # Changed from 10 to more reasonable length
    max_name_length = 60
    
    # try:
        
    #     super_admin = CustomUser.objects
        
    token_get = extract_token(request)

    # Validate token existence
    if not token_get:
        return JsonResponse({
            'code': '401',
            'message': 'Authentication token missing or invalid',
            'data': []
        }, status=status.HTTP_401_UNAUTHORIZED)

        # Assuming the token corresponds to a valid user (use remember_token or any other method)
        
    try:
        user_obj = CustomUser.objects.get(remember_token=token_get)
        requested_user_obj = CustomUser.objects.get(id=id)

        if requested_user_obj.role != 'Admin':
            response_data = {
                'code': '401',
                'message': 'User does not have permission to update this user.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        else:
            if user_obj.id != requested_user_obj.manager.id:
                response_data = {
                    'code': '401',
                    'message': 'User does not have permission to update this user.',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
            else:
                user = CustomUser.objects.get(id=id)
        
        
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'code': '404',
            'message': 'User not found',
            'data': []
        }, status=status.HTTP_404_NOT_FOUND)

    if phone_get:
        # Validate phone number format
        phone_number_pattern = re.compile(r'^\(\d{3}\) \d{3}-\d{4}$')
        if not phone_number_pattern.match(phone_get):
            response_data = {
                'code': '400',
                'message': 'Please Enter Valid Mobile Number.',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    else:
        phone_get = str(user.phone_number)

    # Populate missing data with existing user data
    firstname_get = firstname_get if firstname_get is not None else str(user.first_name)
    lastname_get = lastname_get if lastname_get is not None else str(user.last_name)
    email_get = email_get if email_get is not None else str(user.email)
    role_get = role_get if role_get is not None else str(user.role)
    phone_number_get = phone_get if phone_get is not None else str(user.phone_number)
    address_get = address_get if address_get is not None else str(user.address)
    manager_id_get = manager_id_get if manager_id_get is not None else str(user.manager_id)

    # Validate name lengths
    if not (min_name_length <= len(firstname_get) <= max_name_length) or \
       not (min_name_length <= len(lastname_get) <= max_name_length):
        response_data = {
            'code': '400',
            'message': f'First name and last name should be {min_name_length} to {max_name_length} characters long.',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

    # Validate email format
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_get):
        return JsonResponse({
            'code': '400',
            'message': 'Invalid email format',
            'data': []
        }, status=status.HTTP_400_BAD_REQUEST)

    # Update user profile
    user.first_name = firstname_get
    user.last_name = lastname_get
    user.email = email_get
    user.role = role_get
    user.phone_number = phone_number_get
    user.address = address_get
    user.manager_id = manager_id_get

    # Save the changes
    user.save()

    response_data = {
        'code': '200',  # Changed from 201 to 200 since this is an update
        'message': 'Profile updated successfully',
        'data': {
            'id': id,
            'first_name': firstname_get,
            'last_name': lastname_get,
            'email': email_get,
            'role': role_get,
            'phone_number': phone_number_get,
            'address': address_get,
            'manager_id': manager_id_get
        }
    }

    return JsonResponse(response_data, status=status.HTTP_200_OK)


# Edit Voltage
@swagger_auto_schema(method='post', operation_description="Update Voltage", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'voltage': openapi.Schema(type=openapi.TYPE_NUMBER, description='Voltage'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin', 'Engineer'])
def edit_voltage(request):
    
    current_voltage = request.data.get('current_voltage', None)
    max_voltage = request.data.get('max_voltage', None)
    user_id = request.data.get('user_id', None)

    print(current_voltage, max_voltage)
    
    if current_voltage == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter Current Voltage',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

    elif max_voltage == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter Max Voltage',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    elif user_id == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter User ID',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    else:
    
        try:
            token_get = extract_token(request)
            request_user_obj = CustomUser.objects.get(id=user_id)
            if not request_user_obj.role == "User":
                response_data = {
                    'code': '400',
                    'message': f'User Does Not Exist. Please check entered USER ID ',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            user_obj = CustomUser.objects.get(remember_token=token_get)
            if user_obj.role == 'User':
                if user_obj.id != user_id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            elif user_obj.role == 'Engineer':
                if user_obj.manager.id != request_user_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            elif user_obj.role == 'Admin':
                if user_obj.id != request_user_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif user_obj.role == 'SuperAdmin':
                admin_obj = CustomUser.objects.get(id=request_user_obj.manager.id)
                if user_obj.id != admin_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
                
                user = CustomUser.objects.get(id=user_id)
                voltage_obj = default_sensors_values.objects.get(sensor='voltage',fk_user=user)

                voltage_obj.current_value = current_voltage
                voltage_obj.max_current_value = max_voltage
                voltage_obj.save()
                return Response({"message": "Voltage updated successfully"}, status=200)
    
        except CustomUser.DoesNotExist:
            response_data = {
            'code' : '404',
            'message': 'User Does Not Exist. Please check entered USER ID',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
    


    # return JsonResponse({'message': 'Voltage updated successfully'}, status=status.HTTP_200_OK)






# Edit Watt
@swagger_auto_schema(method='post', operation_description="Update Watt", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'watt': openapi.Schema(type=openapi.TYPE_NUMBER, description='Watt'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin', 'Engineer'])
def edit_watt(request):
    
    current_watt = request.data.get('current_watt', None)
    max_watt = request.data.get('max_watt', None)
    user_id = request.data.get('user_id', None)
    
    # print(current_watt,max_watt)
    if current_watt == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter Current Watt',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

    elif max_watt == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter Max watt',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    elif user_id == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter USER ID',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    else:
        try:
            token_get = extract_token(request)
            request_user_obj = CustomUser.objects.get(id=user_id)
            if not request_user_obj.role == "User" :
                response_data = {
                    'code': '400',
                    'message': f'User Does Not Exist. Please check entered USER ID ',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            user_obj = CustomUser.objects.get(remember_token=token_get)
            
            if user_obj.role == 'User':
                if user_obj.id != user_id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            elif user_obj.role == 'Engineer':
                if user_obj.manager.id != request_user_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            elif user_obj.role == 'Admin':
                if user_obj.id != request_user_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif user_obj.role == 'SuperAdmin':
                admin_obj = CustomUser.objects.get(id=request_user_obj.manager.id)
                if user_obj.id != admin_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

                user = CustomUser.objects.get(id=user_id)
                voltage_obj = default_sensors_values.objects.get(sensor='watt',fk_user=user)

                voltage_obj.current_value = current_watt
                voltage_obj.max_current_value = max_watt
                voltage_obj.save()
                return Response({"message": "Watt updated successfully"}, status=200)
        
        except CustomUser.DoesNotExist:
            response_data = {
            'code' : '404',
            'message': 'User Does Not Exist. Please check entered USER ID',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
    
    # return JsonResponse({'message': 'Watt updated successfully'}, status=status.HTTP_200_OK)



# BY PASS SENSORS
@swagger_auto_schema(method='post', operation_description="BY PASS SENSORS", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'by_pass_sensors': openapi.Schema(type=openapi.TYPE_NUMBER, description='By Pass Sensors'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin', 'Engineer'])
def by_pass_sensors(request):
    user_id = request.data.get('user_id', None)
    voltage = request.data.get('voltage',0)  
    watt = request.data.get('watt',0)
    high_pressure = request.data.get('high_pressure', 0)
    low_pressure = request.data.get('low_pressure', 0)
    
    
    selected_sensors = {
            
            "voltage": voltage ,
            "watt": watt,
            "high_pressure": high_pressure,
            "low_pressure": low_pressure,
        }
    
    if voltage == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter Current Watt',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

    elif watt == None:
            response_data = {
                'code': '400',
                'message': '',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    elif high_pressure == None:
            response_data = {
                'code': '400',
                'message': '',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
        
    elif low_pressure == None:
            response_data = {
                'code': '400',
                'message': '',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
        
    elif user_id == None:
            response_data = {
                'code': '400',
                'message': 'Please Enter User ID',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
    else:
        try:
            token_get = extract_token(request)
            
            request_user_obj = CustomUser.objects.get(id=user_id)
            
            if not request_user_obj.role == "User":
                response_data = {
                    'code': '400',
                    'message': f'User Does Not Exist. Please check entered USER ID ',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            user_obj = CustomUser.objects.get(remember_token=token_get)
            
            if user_obj.role == 'User':
                if user_obj.id != user_id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            elif user_obj.role == 'Engineer':
                if user_obj.manager.id != request_user_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            elif user_obj.role == 'Admin':
                if user_obj.id != request_user_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif user_obj.role == 'SuperAdmin':
                admin_obj = CustomUser.objects.get(id=request_user_obj.manager.id)
                if user_obj.id != admin_obj.manager.id:
                    response_data = {
                        'code': '400',
                        'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                        'data': []
                    }
                    return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
                
                user = CustomUser.objects.get(id=user_id)
                by_pass_sensors = default_sensors_values.objects.filter(fk_user=user)
                bypassed_sensor_name = []
                for Sensor in by_pass_sensors:
                    
                    sensor_name = Sensor.sensor  
                    
                    if sensor_name in selected_sensors:
                    
                        Sensor.bypass_status = selected_sensors[sensor_name]
                        if Sensor.bypass_status:
                            bypassed_sensor_name.append(sensor_name.capitalize())
                            
                    else:
                        Sensor.bypass_status = False 
                                        
                    Sensor.save()
                
                print(bypassed_sensor_name)
                
                return Response({"message": f"{", ".join(bypassed_sensor_name)} Sensors have been bypassed successfully"}, status=200)
            
        except CustomUser.DoesNotExist:
            response_data = {
            'code' : '404',
            'message': 'User Does Not Exist. Please check entered USER ID',
            'data': []
        }
        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
    
    # return JsonResponse({'message': 'Sensors By Passed successfully'}, status=status.HTTP_200_OK)





# (RESET SENSORS) RESET ALL SENSORS TO DEFAULT
@swagger_auto_schema(method='post', operation_description="RESET SENSORS", tags=['app-user'],
                     request_body=openapi.Schema(
                         type=openapi.TYPE_OBJECT,
                         properties={
                            'reset_sensors': openapi.Schema(type=openapi.TYPE_NUMBER, description='Reset Sensors'),
                         }
                     ))
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this specific view
@permission_classes([]) 
@authenticate_with_token(allowed_roles=['SuperAdmin', 'Admin', 'Engineer'])
def reset_default_sensors(request):
    try:
        user_id = request.data.get('user_id', None)
        token_get = extract_token(request)
        
        request_user_obj = CustomUser.objects.get(id=user_id)
        user_obj = CustomUser.objects.get(remember_token=token_get)
        
        if not request_user_obj.role == "User":
            response_data = {
                'code': '400',
                'message': f'User Does Not Exist. Please check entered USER ID',
                'data': []
            }
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

        if user_obj.role == 'User':
            if user_obj.id != user_id:
                response_data = {
                    'code': '400',
                    'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        elif user_obj.role == 'Engineer':
            if user_obj.manager.id != request_user_obj.manager.id:
                response_data = {
                    'code': '400',
                    'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        elif user_obj.role == 'Admin':

            if user_obj.id != request_user_obj.manager.id:
                response_data = {
                    'code': '400',
                    'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
        elif user_obj.role == 'SuperAdmin':

            admin_obj = CustomUser.objects.get(id=request_user_obj.manager.id)

            if user_obj.id != admin_obj.manager.id:
                response_data = {
                    'code': '400',
                    'message': f'{user_obj.username} does not have permission to update {request_user_obj.username}.',
                    'data': []
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
            
            user = CustomUser.objects.get(id=user_id)
            
            by_pass_sensors = default_sensors_values.objects.filter(fk_user=user)
            
            for Sensor in by_pass_sensors:
                Sensor.current_value = Sensor.default_value
                Sensor.max_current_value = Sensor.max_default_value
                Sensor.bypass_status = 0
                Sensor.save()
            return Response({"message": "All Sensors are RESET Successfully"}, status=200)
    
    except CustomUser.DoesNotExist:
        response_data = {
        'code' : '404',
        'message': f'User Does Not Exist. Please check entered USER ID',
        'data': []
    }
    return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)



# "####%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
# @swagger_auto_schema(method='post', operation_description="Add New Playlist", tags=['app-user'],
#                      request_body=openapi.Schema(
#                          type=openapi.TYPE_OBJECT,
#                          properties={
#                             'name': openapi.Schema(type=openapi.TYPE_INTEGER, description='name of playlist'),
#                          }
#                      ))    
# @api_view(['POST'])
# @authenticate_with_token
# def add_playlist_api(request):
#     token_get = extract_token(request)
#     user = CustomUser.objects.get(remember_token=token_get)
#     playlist_name = request.data.get('name','')
#     if not playlist_name:
#         response_data = {
#             "code": 200,
#             "message": "'name' not found.",
#             "data":{}
#         }
#         return JsonResponse(response_data)
#     if_exist_splash = heatpump_devices_info.objects.filter(user_id=user.id,name=playlist_name).first()
#     if if_exist_splash:
#         response_data = {
#             "code": 200,
#             "message": "Playlist already exist.",
#             "data":{
#                 "playlist_id": if_exist_splash.id,
#                 "name":if_exist_splash.name
#             }
#         }
#         return JsonResponse(response_data)
#     else:
#         new_save_obj = heatpump_devices_info(user_id=user,name=playlist_name)
#         new_save_obj.save()

#         response_data = {
#             "code": 200,
#             "message": "Playlist saved successfully.",
#             "data":{
#                 "playlist_id": new_save_obj.id,
#                 "name":playlist_name
#             }
#         }
#     return JsonResponse(response_data)

# @swagger_auto_schema(method='post', operation_description="Remove Playlist", tags=['app-user'],
#                      request_body=openapi.Schema(
#                          type=openapi.TYPE_OBJECT,
#                          properties={
#                             'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='id of playlist'),
#                          }
#                      ))    
# @api_view(['POST'])
# @authenticate_with_token
# def remove_playlist_api(request):
#     token_get = extract_token(request)
#     user = CustomUser.objects.get(remember_token=token_get)
#     playlist_id_get = int(request.data.get('id',0))
#     if not playlist_id_get:
#         response_data = {
#             "code": 200,
#             "message": "'id' not found.",
#             "data":{}
#         }
#         return JsonResponse(response_data)
#     if_exist_splash = heatpump_devices_info.objects.filter(id=playlist_id_get,user_id=user.id).first()
#     if if_exist_splash:
#         response_data = {
#             "code": 200,
#             "message": "Playlist deleted successfully.",
#             "data":{
#                 "playlist_id": if_exist_splash.id,
#                 "name":if_exist_splash.name
#             }
            
#         }
#         if_exist_splash.delete()
#         return JsonResponse(response_data)
#     else:
#         response_data = {
#             "code": 200,
#             "message": "Playlist not found.",
#             "data":{}
#         }
#     return JsonResponse(response_data)
    
# @swagger_auto_schema(method='post', operation_description="Get Users Playlist", tags=['app-user'],
#                      request_body=openapi.Schema(
#                          type=openapi.TYPE_OBJECT,
#                          properties={
#                             'page': openapi.Schema(type=openapi.TYPE_NUMBER, description='Page'),
#                             'limit': openapi.Schema(type=openapi.TYPE_NUMBER, description='Limit Per Page'),
#                          }
#                      ))
# @api_view(['POST'])
# @authenticate_with_token
# def user_playlist_api(request):
#     token_get = extract_token(request)
#     user = CustomUser.objects.get(remember_token=token_get)
#     page = int(request.data.get('page', 1))
#     limit = int(request.data.get('limit', 20))

#     if_exist_splash_all = heatpump_devices_info.objects.filter(user_id=user.id)
#     paginator = Paginator(if_exist_splash_all, limit)##3
#     total_pages = paginator.num_pages
#     response_data = {
#         'code' : '200',
#         'message': 'Available Playlist listing.',
#         'playlist_count': len(if_exist_splash_all),
#         'data': [],
#         'per_page':limit,
#         'current_page':page,
#         'last_page':total_pages
#     }
#     try:
#         # Get the specified page
#         current_page_data = paginator.page(page)
#     except EmptyPage:
#         # If the page is out of range, return an empty response or handle as needed
#         return JsonResponse(response_data)
#     # Now, current_page_data contains the data for the requested page
#     # data = current_page_data.object_list

#     user_playlist_obj = heatpump_devices_info.objects.all()
#     for if_exist_splash in current_page_data:
#         songs_length = len(user_playlist_obj.filter(playlist_id=if_exist_splash,user_id=user.id))
#         response_data["data"].append( {
#             "playlist_id": if_exist_splash.id,
#             "name":if_exist_splash.name,
#             "total_song":songs_length,
#             "created_at":if_exist_splash.created_at.strftime("%b %dth, %Y %I:%M %p")
#         })
#     return JsonResponse(response_data)

# @swagger_auto_schema(method='post', operation_description="Get Songs By Search", tags=['app-user'],
#                      request_body=openapi.Schema(
#                          type=openapi.TYPE_OBJECT,
#                          properties={
#                             'page': openapi.Schema(type=openapi.TYPE_NUMBER, description='Page'),
#                             'limit': openapi.Schema(type=openapi.TYPE_NUMBER, description='Limit Per Page'),
#                             'albums_id': openapi.Schema(type=openapi.TYPE_NUMBER, description='Album ID'),
#                             'search_key': openapi.Schema(type=openapi.TYPE_NUMBER, description='Search Keyword'),
#                          }
#                      ))
# @api_view(['POST'])
# @authenticate_with_token 
# def get_songs_by_search_list(request):
#     if request.method == 'POST':
#         page = int(request.data.get('page', 1))
#         limit = int(request.data.get('limit', 15))
#         try:
#             albums_id_get = int(request.data.get('albums_id',None))
#         except:
#             albums_id_get = None
#         search_key = request.data.get('search_key','')
#         if albums_id_get:
#             search_keyword = heatpump_devices_info.objects.filter(fk_albums=albums_id_get)
#             all_songs_obj = heatpump_devices_info.objects.filter(
#                 Q(id__in=search_keyword.values_list('fk_songs', flat=True).distinct()) & (Q(name__icontains=search_key) | Q(artist__icontains=search_key))
#             ).annotate(
#                 custom_position=Case(
#                     *[When(id=song_id, then=Value(position)) for song_id, position in search_keyword.values_list('fk_songs_id', 'position')],
#                     default=Value(0),
#                     output_field=IntegerField(),
#                 )
#             ).order_by('custom_position').values()
#         else:
#             all_songs_obj = heatpump_devices_info.objects.filter(Q(name__icontains=search_key) | Q(artist__icontains=search_key)).order_by('position').values()

        

#         paginator = Paginator(all_songs_obj, limit)
#         total_pages = paginator.num_pages

#         response_data = {
#             'code' : '200',
#             'message': 'All Songs List.',
#             'songs_count': len(all_songs_obj),
#             'data': [],
#             'per_page':limit,
#             'current_page':page,
#             'last_page':int(total_pages)
#         }
#         try:
#             # Get the specified page
#             current_page_data = paginator.page(page)
#         except EmptyPage:
#             # If the page is out of range, return an empty response or handle as needed
#             return JsonResponse(response_data)
#         # Now, current_page_data contains the data for the requested page
#         data = current_page_data.object_list

#         # Update data as needed (e.g., thumbnail image paths)
#         for item in data:
#             if item['thumbnail_image']:
#                 thumbnail_image_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, item['thumbnail_image']))
#                 item['thumbnail_image'] = thumbnail_image_url
#             else:
#                 item['thumbnail_image'] = ''
#             if item['url']:
#                 item_song = item['url']
#             else:
#                 item_song = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, item['file']))

#             response_data["data"].append(
#                 {
#                     "song_id": item['id'],
#                     "title": item['name'],
#                     "artist": item['artist'],
#                     "poster": item['thumbnail_image'],
#                     "mp3": item_song,
#                     "duration": item['duration'],
#                     "file_size": item['file_size'],
#                     "file_type": str(item_song).split('.')[-1],
#                     "total_played": item['total_played'],
#                     "total_shared": item['total_shared'],
#                     "total_like": item['likes'],
#                     "total_download": item['total_download']
#                 }
#             )

#         return JsonResponse(response_data, status=status.HTTP_200_OK)
#     else:
#         response_data = {
#         "code": 422,
#         "message": "Please try with valid request method",
#         "data": []
#         }

#         return JsonResponse(response_data,status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    