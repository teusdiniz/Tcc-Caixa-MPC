from django.contrib import admin
from .models import Gaveta, Ferramenta


@admin.register(Gaveta)
class GavetaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nome", "ativa", "criado_em")
    list_filter = ("ativa",)
    search_fields = ("nome", "descricao")


@admin.register(Ferramenta)
class FerramentaAdmin(admin.ModelAdmin):
    list_display = ("nome", "gaveta", "posicao", "quantidade", "ativa")
    list_filter = ("gaveta", "ativa")
    search_fields = ("nome", "codigo", "descricao")
