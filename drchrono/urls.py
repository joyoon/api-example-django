from django.conf.urls import include, url
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib import admin
admin.autodiscover()

import views


urlpatterns = [
    # views
    url(r'^setup/$', views.SetupView.as_view(), name='setup'),
    url(r'^welcome/$', views.DoctorWelcome.as_view(), name='welcome'),
    url(r'^patients/$', views.Patients.as_view(), name='patients'),
    url(r'^checkin/$', views.Checkin.as_view(), name='checkin'),
    url(r'^offices/$', views.Offices.as_view(), name='offices'),
    url(r'^appointments/$', views.Appointments.as_view(), name='appointments'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('social.apps.django_app.urls', namespace='social')),

    #ajax
    url(r'^api/patients$', views.getpatient, name='getpatient'),
    url(r'^api/patients/(?P<id>\d+)/appointments/$', views.getpatientappointments, name='getpatientappointments'),
    url(r'^api/patients/(?P<id>\d+)/$', views.updatepatient, name='updatepatient'),
    url(r'^api/appointmentupdate', views.webhook_verify, name='appointmentupdate')
]