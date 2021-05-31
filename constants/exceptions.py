# HTTP_500_INTERNAL_SERVER_ERROR = 500
# HTTP_403_FORBIDDEN = 403
# HTTP_404_NOT_FOUND = 404
# HTTP_400_BAD_REQUEST = 400
# 
# class APIException(Exception):
#     status_code = HTTP_500_INTERNAL_SERVER_ERROR
#     message = ''
# 
#     def __init__(self, message=None, status_code=None):
#         Exception.__init__(self)
#         if message is not None:
#             self.message = message
#         if status_code is not None:
#             self.status_code = status_code
# 
#     def __str__(self):
#         return self.message
# 
#     def to_dict(self):
#         response = {"message": self.message}
#         return response
# 
# class BadRequest(APIException):
#     status_code = HTTP_400_BAD_REQUEST
#     message = 'Malformed request.'
# 
# class PermissionDenied(APIException):
#     status_code = HTTP_403_FORBIDDEN
#     message = 'You do not have permission to perform this action.'
# 
# class NotFound(APIException):
#     status_code = HTTP_404_NOT_FOUND
#     message = 'This resource does not exist.'


# class InvalidInputError(BadRequest):
#     #default message
#     message = 'Whoops! Invalid input.'
# 
# class InvalidFileType(BadRequest):
#     #default message
#     message = 'Whoops! Invalid file type.'

############################################



# System errors
class BadPhoneNumberError(Exception): pass
class UnknownCohortError(Exception): pass
class UnknownPhoneNumberError(Exception): pass
class BadPasswordException(Exception): pass

# Twilio errors
class TwilioDeliveryException(Exception): pass

# Analytics exceptions
class InvalidUpdateError(Exception): pass

# Twilio Phone Purchasing specific exceptions
class PhoneNumberPurchaseException(Exception): pass
class PhoneSearchException(Exception): pass

# old/dynamic_surveys.py
class NoValidQuestionsError(Exception): pass
