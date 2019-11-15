from django.db import models

# Add your models here
class AppointmentsViewModel(object):

    def __init__(self, scheduleData):
        self.scheduleData = scheduleData

class AppointmentViewModel(object):

    def __init__(self, hourInterval, appointment):
        self.hourInterval = hourInterval
        self.appointment = appointment

class Appointment(object):

    def __init__(self, patient, duration, examroom, scheduledtime, status):
        self.patient = patient
        self.duration = duration
        self.examroom = examroom
        self.scheduledtime = scheduledtime
        self.status = status