from rest_framework import generics, permissions
from .models import ClinicalRecord
from .serializers import ClinicalRecordSerializer


class IsHospitalStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_hospital_staff()


class ClinicalRecordListCreateView(generics.ListCreateAPIView):
    """
    API alternative to the admin panel, for a future mobile/web hospital
    interface. GET lists records entered by the logged-in staff member;
    POST creates a new one (entered_by is set automatically).
    """
    serializer_class = ClinicalRecordSerializer
    permission_classes = [IsHospitalStaff]

    def get_queryset(self):
        return ClinicalRecord.objects.filter(entered_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)
