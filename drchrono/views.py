from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from social_django.models import UserSocialAuth
from django.http import JsonResponse

from drchrono.endpoints import DoctorEndpoint
from drchrono.endpoints import AppointmentEndpoint
from drchrono.endpoints import PatientEndpoint
from drchrono.endpoints import OfficeEndpoint
from models import Appointment
from models import AppointmentsViewModel
from models import AppointmentViewModel

from datetime import datetime, timedelta
import hashlib
import hmac

def webhook_verify(request):
    secret_token = hmac.new('39b290146bea6ce975c37cfc23', request.GET['msg'], hashlib.sha256).hexdigest()
    return JsonResponse({
        'secret_token': secret_token
    })

# ajax endpoints
def get_token():
    oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
    access_token = oauth_provider.extra_data['access_token']
    return access_token

def getpatientappointments(request, id):
    patientid = id
    access_token = get_token()
    api = AppointmentEndpoint(access_token)

    params = {}
    params['patient'] = patientid
    params['date'] = str(datetime.today().year) + '-' + str(datetime.today().month) + '-' + str(datetime.today().day)
    params['date'] = '2019-11-01'

    appointments = api.list(params=params)
    appointmentList = []

    for a in appointments:
        appointmentList.append(a)

    response = {}
    response['appointments'] = appointmentList

    return JsonResponse(response)

def appointmentcreate(request):
    firstName = request.GET.get('firstName', None)
    lastName = request.GET.get('lastName', None)

    response = {}

    return JsonResponse(response)

def getpatient(request):
    firstName = request.GET.get('firstName', None)
    lastName = request.GET.get('lastName', None)

    access_token = get_token()
    api = PatientEndpoint(access_token)
    params = {}
    params['doctor'] = 252849
    params['first_name'] = firstName
    params['last_name'] = lastName

    response = {}
    patient = api.list(params=params)

    patientData = None

    if patient:
        for p in patient:
            patientData = p

    response['patient'] = patientData
    return JsonResponse(response)

@csrf_exempt
def updatepatient(request, id):
    patientid = id
    address = request.POST.get('address', None)
    gender = request.POST.get('gender', None)

    access_token = get_token()

    api = PatientEndpoint(access_token)
    params = {}
    params['doctor'] = 252849
    params['id'] = patientid
    params['gender'] = gender
    params['address'] = address

    response = {}
    patient = api.update(patientid, params)

    response['data'] = patient

    return JsonResponse(response)

class SetupView(TemplateView):
    """
    The beginning of the OAuth sign-in flow. Logs a user into the kiosk, and saves the token.
    """
    template_name = 'kiosk_setup.html'

class Checkin(TemplateView):
    template_name = "checkin.html"

    def get_token(self):
        """
        Social Auth module is configured to store our access tokens. This dark magic will fetch it for us if we've
        already signed in.
        """
        oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
        access_token = oauth_provider.extra_data['access_token']
        return access_token

    def getPatientByName(self, firstName, lastName):
        access_token = self.get_token()
        api = PatientEndpoint(access_token)
        params = {}
        params['doctor'] = 252849
        params['first_name'] = firstName
        params['last_name'] = lastName

        return api.list(params=params)

class Appointments(TemplateView):
    template_name = 'appointments.html'

    def get_token(self):
        """
        Social Auth module is configured to store our access tokens. This dark magic will fetch it for us if we've
        already signed in.
        """
        oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
        access_token = oauth_provider.extra_data['access_token']
        return access_token

    def getAppointments(self):
        """
        Use the token we have stored in the DB to make an API request and get doctor details. If this succeeds, we've
        proved that the OAuth setup is working
        """
        # We can create an instance of an endpoint resource class, and use it to fetch details
        access_token = self.get_token()
        api = AppointmentEndpoint(access_token)

        date = datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d')\
            if self.request.GET.get('date') else None
        start = datetime.strptime(self.request.GET.get('start'), '%Y-%m-%d')\
            if self.request.GET.get('start') else None
        end = datetime.strptime(self.request.GET.get('end'), '%Y-%m-%d')\
            if self.request.GET.get('end') else None

        appointments = api.list(date=date, start=start, end=end)
        appointmentsList = []

        for a in appointments:
            appointmentsList.append(a)

        return appointmentsList

    def createAppointment(self):
        access_token = self.get_token()
        api = AppointmentEndpoint(access_token)
        params = {}
        params['doctor'] = 252849
        params['duration'] = 1
        params['exam_room'] = 1
        params['office'] = 269267
        params['patient'] = 84394833
        today = datetime.date.today()

        params['scheduled_time'] = today.strftime('%Y-%m-%dT%H:%M:%S')

        api.create(data=params)

    # def __init__(self):
    #     self.createAppointment()

    def get_context_data(self, **kwargs):
        kwargs = super(Appointments, self).get_context_data(**kwargs)
        # Hit the API using one of the endpoints just to prove that we can
        # If this works, then your oAuth setup is working correctly.
        appointments = self.getAppointments()

        # appointment dictionary
        # key: hour interval, value: appointment
        appointmentLookup = {}

        # populate dictionary
        for a in appointments:
            if a['status'] != 'Cancelled':
                scheduledTime = datetime.strptime(a['scheduled_time'], '%Y-%m-%dT%H:%M:%S')
                key = str(scheduledTime.hour) + ":" + str(scheduledTime.minute)
                appointmentLookup[key] = Appointment(a['patient'], a['duration'], a['exam_room'], scheduledTime, a['status'])

        appointmentsViewModel = None
        scheduleData = []
        date = datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d')
        appointmentDate = datetime(date.year, date.month, date.day)
        hourIntervals = self.getHourIntervals(appointmentDate)

        for i in range(0, len(hourIntervals)):
            intervalData = None
            interval = hourIntervals[i]
            key = str(interval.hour) + ":" + str(interval.minute)

            # check if there is an appointment at the scheduled time
            if key not in appointmentLookup:
                # check previous interval
                if i - 1 >= 0:
                    prevInterval = scheduleData[i - 1]

                    if prevInterval.appointment and\
                        prevInterval.appointment.scheduledtime + timedelta(minutes=prevInterval.appointment.duration)\
                            > interval:
                                key = str(prevInterval.appointment.scheduledtime.hour) + ":" + str(prevInterval.appointment.scheduledtime.minute)
                                intervalData = AppointmentViewModel(interval, appointmentLookup[key])

                    else:
                        intervalData = AppointmentViewModel(interval, None)

                else:
                    intervalData = AppointmentViewModel(interval, None)

            else:
                intervalData = AppointmentViewModel(interval, appointmentLookup[key])

            scheduleData.append(intervalData)

        appointmentsViewModel = AppointmentsViewModel(scheduleData)

        kwargs['scheduledata'] = scheduleData
        kwargs['appointmentlookup'] = appointmentLookup
        kwargs['model'] = appointmentsViewModel
        return kwargs

    def getHourIntervals(self, day):
        hourIntervals = []

        appointmentDate = day

        for i in range(9, 12):
            hourIntervals.append(appointmentDate + timedelta(hours=i))

            hourIntervals.append(appointmentDate + timedelta(hours=i) + timedelta(minutes=15))

            hourIntervals.append(appointmentDate + timedelta(hours=i) + timedelta(minutes=30))

            hourIntervals.append(appointmentDate + timedelta(hours=i) + timedelta(minutes=45))

        hourIntervals.append(appointmentDate + timedelta(hours=12))
        hourIntervals.append(appointmentDate + timedelta(hours=12) + timedelta(minutes=15))
        hourIntervals.append(appointmentDate + timedelta(hours=12) + timedelta(minutes=30))
        hourIntervals.append(appointmentDate + timedelta(hours=12) + timedelta(minutes=45))

        for i in range(13, 17):
            hourIntervals.append(appointmentDate + timedelta(hours=i))

            hourIntervals.append(appointmentDate + timedelta(hours=i) + timedelta(minutes=15))

            hourIntervals.append(appointmentDate + timedelta(hours=i) + timedelta(minutes=30))

            hourIntervals.append(appointmentDate + timedelta(hours=i) + timedelta(minutes=45))

        hourIntervals.append(appointmentDate + timedelta(hours=17))
        return hourIntervals

class DoctorWelcome(TemplateView):
    """
    The doctor can see what appointments they have today.
    """
    template_name = 'doctor_welcome.html'

    def get_token(self):
        """
        Social Auth module is configured to store our access tokens. This dark magic will fetch it for us if we've
        already signed in.
        """
        oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
        access_token = oauth_provider.extra_data['access_token']
        return access_token

    def make_api_request(self):
        """
        Use the token we have stored in the DB to make an API request and get doctor details. If this succeeds, we've
        proved that the OAuth setup is working
        """
        # We can create an instance of an endpoint resource class, and use it to fetch details
        access_token = self.get_token()
        api = DoctorEndpoint(access_token)
        # Grab the first doctor from the list; normally this would be the whole practice group, but your hackathon
        # account probably only has one doctor in it.
        return next(api.list())

    def get_context_data(self, **kwargs):
        kwargs = super(DoctorWelcome, self).get_context_data(**kwargs)
        # Hit the API using one of the endpoints just to prove that we can
        # If this works, then your oAuth setup is working correctly.
        doctor_details = self.make_api_request()
        kwargs['date'] = datetime.today()
        kwargs['doctor'] = doctor_details
        return kwargs

class Offices(TemplateView):
    template_name = "base.html"

    def get_token(self):
        """
        Social Auth module is configured to store our access tokens. This dark magic will fetch it for us if we've
        already signed in.
        """
        oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
        access_token = oauth_provider.extra_data['access_token']
        return access_token

    def make_api_request(self):
        """
        Use the token we have stored in the DB to make an API request and get doctor details. If this succeeds, we've
        proved that the OAuth setup is working
        """
        # We can create an instance of an endpoint resource class, and use it to fetch details
        access_token = self.get_token()
        api = OfficeEndpoint(access_token)
        # Grab the first doctor from the list; normally this would be the whole practice group, but your hackathon
        # account probably only has one doctor in it.
        return next(api.list())

    def get_context_data(self, **kwargs):
        kwargs = super(Offices, self).get_context_data(**kwargs)
        # Hit the API using one of the endpoints just to prove that we can
        # If this works, then your oAuth setup is working correctly.
        offices = self.make_api_request()
        kwargs['offices'] = offices
        return kwargs

class Patients(TemplateView):
    template_name = 'patients.html'

    def get_token(self):
        """
        Social Auth module is configured to store our access tokens. This dark magic will fetch it for us if we've
        already signed in.
        """
        oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
        access_token = oauth_provider.extra_data['access_token']
        return access_token

    def createPatient(self):
        """
        Use the token we have stored in the DB to make an API request and get doctor details. If this succeeds, we've
        proved that the OAuth setup is working
        """
        # We can create an instance of an endpoint resource class, and use it to fetch details
        access_token = self.get_token()
        api = PatientEndpoint(access_token)
        params = {}
        params['doctor'] = 252849
        params['gender'] = 'Male'
        params['first_name'] = 'Joe'
        params['last_name'] = 'Blow'

        return api.create(data=params)

    def getPatients(self):
        access_token = self.get_token()
        api = PatientEndpoint(access_token)
        params = {}
        params['doctor'] = 252849
        # params['first_name'] = firstName
        # params['last_name'] = lastName

        return api.list(params=params)

    def get_context_data(self, **kwargs):
        kwargs = super(Patients, self).get_context_data(**kwargs)
        # Hit the API using one of the endpoints just to prove that we can
        # If this works, then your oAuth setup is working correctly.
        patients = self.getPatients()
        patientList = []

        for p in patients:
            patientList.append(p)

        kwargs['patients'] = patientList
        return kwargs