# Register your models here.
from django.contrib import admin
from .models import Colaborador, CartaoNFC


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ("nome", "matricula", "email", "ativo", "criado_em")
    search_fields = ("nome", "matricula", "email")
    list_filter = ("ativo",)


@admin.register(CartaoNFC)
class CartaoNFCAdmin(admin.ModelAdmin):
    list_display = ("uid", "colaborador", "ativo", "ultimo_uso_em", "criado_em")
    search_fields = ("uid", "colaborador__nome", "colaborador__matricula")
    list_filter = ("ativo",)
