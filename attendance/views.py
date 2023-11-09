from django.http import HttpResponse, JsonResponse
from attendance.models import SubjectClass, Student, ClassAttendance, GeoLocation, FalseAttempt, ClassAttendanceWithGeoLocation
from django.views.decorators.csrf import csrf_exempt
import json


AVG_LAT = 12.83849392
AVG_LON = 77.66468718

def is_in_class(lat, lon, accuracy):
    # return True
    return accuracy >= 10 and abs(AVG_LAT - lat) < 0.0001 and abs(AVG_LON - lon) < 0.0001

def ping(request):
    return JsonResponse({"message": "pong"})

@csrf_exempt
def index(request):
    data = json.loads(request.body)
    print(data)
    lat = (data['latitutde'])
    lon = (data['longitude'])
    token = data["token"]
    if 'accuracy' not in data:
        return JsonResponse({
            "message": "Please update your app"
        }, status=400)
    accuracy = data['accuracy']

    student = Student.objects.get(token=token)
    if is_in_class(lat, lon, accuracy):
        curr_class = SubjectClass.get_current_class()

        if curr_class == None or not curr_class.is_in_attendance_window():
            return JsonResponse({
                "message": "No class active for attendance"
            }, status=400)

        if ClassAttendance.objects.filter(student = student, subject=curr_class).exists():
            # print(f"Attendance already marked of {student.name} for class {curr_class.name}")
            return JsonResponse({
                "class": curr_class.name,
                "time": curr_class.attendance_start_time
            })

        ClassAttendanceWithGeoLocation.create_with(student, curr_class, lat, lon, accuracy)
        return JsonResponse({
            "class": curr_class.name,
            "time": curr_class.attendance_start_time
        })
    else:
        FalseAttempt.objects.create(student=student, lat=lat, lon=lon, accuracy=accuracy).save()
        return JsonResponse({
            "message": "You are outside the class range"
        }, status=400)

@csrf_exempt
def register(request):
    details = {}
    
    data = json.loads(request.body)
    print(data)

    details['mail'] = data["email"]
    if not (details['mail'].endswith("@sst.scaler.com") or details['mail'].endswith("@scaler.com")):
        return JsonResponse({"message": "mail should end with @sst.scaler.com"}, status=400)
    
    details['token'] = data["uid"]
    details['name'] = data["name"] if 'name' in data else ""
    
    user_object_query = Student.objects.filter(mail=details['mail'])
    if user_object_query.exists():
        user_obj = user_object_query[:1].get()
        if user_obj.token == details['token']:
            details["status"] = "success"
            return JsonResponse(details)
        else:
            # TODO: add to database and report to bsm
            return JsonResponse({"message": "you can loggin in only one device", "status": "error"}, status=400)
    else:
        student = Student.objects.create(name=details['name'], mail=details['mail'], token=details['token'])
        student.save()
    details["status"] = "success"
    return JsonResponse(details)


@csrf_exempt
def geo(request):
    # check if request.body.token
    # print(request.body)
    data = json.loads(request.body)
    token = data['uid']
    lat = str(data['latitutde'])
    lon = str(data['longitude'])
    accuracy = str(data['accuracy'])
    label = int(data['label'])

    student = Student.objects.get(token=token)

    obj = GeoLocation.objects.create(label=label, student = student, lat=lat, lon=lon, accuracy=accuracy)
    obj.save()
    return JsonResponse({})


@csrf_exempt
def get_all_attendance(request):
    data = json.loads(request.body)
    token = data['token']

    student = Student.get_object_with_token(token)
    all_attendances_obj = ClassAttendance.all_subject_attendance(student)

    all_attendances = []
    for subject_class in all_attendances_obj:
        details = {}
        details["name"] = subject_class['name']
        details["class_start_time"] = subject_class['class_start_time']
        details["class_end_time"] = subject_class['class_end_time']
        details["attendance_time"] = subject_class['min_creation_time']
        # print(f"Subject: {name}, Start Time: {start_time}, End Time: {end_time}, Min Creation Time: {min_creation_time}")
        all_attendances.append(details)

    return JsonResponse(all_attendances, safe=False)


@csrf_exempt
def getcurclassattendance(request):
    data = json.loads(request.body)
    token = data['token']

    curr_class = SubjectClass.get_current_class()
    if curr_class == None:
        return JsonResponse(None, safe=False)
    
    details = {}
    details["name"] = curr_class.name
    details["class_start_time"] = curr_class.class_start_time
    details["class_end_time"] = curr_class.class_end_time
    details["attendance_start_time"] = curr_class.attendance_start_time
    details["attendance_end_time"] = curr_class.attendance_end_time

    student = Student.get_object_with_token(token)
    time = ClassAttendance.get_latest_attendance_time(student, curr_class)

    details["attendance_time"] = time

    return JsonResponse(details)