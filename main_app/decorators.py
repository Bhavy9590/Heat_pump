from django.http import HttpResponseForbidden
from functools import wraps
from django.http import JsonResponse
import jwt
from datetime import datetime, timezone
from main_app.models import CustomUser

secret_key_token = 'rHx3e8uaNklG(Zoe.f])b,$V2>{o/{N8_{-LRG94zEw%/e-Iu>'

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("You do not have permission to access this page.")
        return _wrapped_view
    return decorator


def authenticate_with_token(allowed_roles=None):
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            auth_header = request.headers.get('Authorization')

            if not auth_header:
                response_data = {
                    'code': '401',
                    'message': 'Authentication header not found',
                    'data': None
                }
                return JsonResponse(response_data, status=401)

            try:
                auth_type, token = auth_header.split()
                if auth_type.lower() == 'bearer':
                    try:
                        # Decode the token
                        decoded_token = jwt.decode(token, secret_key_token, algorithms=['HS256'])
                        
                        # Check expiration time
                        expiration_time = decoded_token.get('exp')
                        if expiration_time:
                            current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
                            exp_time = datetime.utcfromtimestamp(expiration_time).replace(tzinfo=timezone.utc)
                            if current_time > exp_time:
                                response_data = {
                                    'code': '401',
                                    'message': 'Token has expired',
                                    'data': None
                                }
                                return JsonResponse(response_data, status=401)

                        # Verify the token
                        token_obj = CustomUser.objects.get(remember_token=token)
                        user_role = token_obj.role
                        
                        # Check if user role is allowed
                        if allowed_roles and user_role not in allowed_roles:
                            response_data = {
                                'code': '403',
                                'message': 'Permission denied. Role not allowed.',
                                'data': None
                            }
                            return JsonResponse(response_data, status=403)

                        # Attach user to request
                        request.user = token_obj
                        return view_func(request, *args, **kwargs)

                    except jwt.ExpiredSignatureError:
                        response_data = {
                            'code': '401',
                            'message': 'Token has expired',
                            'data': None
                        }
                        return JsonResponse(response_data, status=401)
                    
                    except CustomUser.DoesNotExist:
                        response_data = {
                            'code': '401',
                            'message': 'Invalid token',
                            'data': None
                        }
                        return JsonResponse(response_data, status=401)

            except (ValueError, jwt.InvalidTokenError) as e:
                print(e)
                response_data = {
                    'code': '401',
                    'message': 'Invalid authentication',
                    'data': None
                }
                return JsonResponse(response_data, status=401)

        return _wrapped_view
    return decorator