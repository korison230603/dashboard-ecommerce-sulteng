
from django.db import models

class Lokasi(models.Model):
    nama = models.CharField(max_length=100)
    def __str__(self):
        return self.nama

class Kategori(models.Model):
    nama = models.CharField(max_length=100)
    def __str__(self):
        return self.nama

class Pedagang(models.Model):
    nama = models.CharField(max_length=200)
    lokasi = models.ForeignKey(Lokasi, on_delete=models.CASCADE)
    kategori = models.ForeignKey(Kategori, on_delete=models.CASCADE)
    is_valid = models.BooleanField(default=True)
    alasan_tidak_valid = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama
