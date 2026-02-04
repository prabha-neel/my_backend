from django.http import JsonResponse
from django_ratelimit.exceptions import Ratelimited

class RatelimitJSONMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Agar error Ratelimit ki wajah se hai, toh HTML nahi, JSON bhejo
        if isinstance(exception, Ratelimited):
            return JsonResponse({
                "success": False,
                "error": "Too Many Requests",
                "message": "Request limit exceeded. Please wait a minute and try again."
            }, status=429)
        return None