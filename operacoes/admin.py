from django.contrib import admin
from .models import SessaoUso, MovimentacaoFerramenta


class MovimentacaoFerramentaInline(admin.TabularInline):
    model = MovimentacaoFerramenta
    extra = 0


@admin.register(SessaoUso)
class SessaoUsoAdmin(admin.ModelAdmin):
    list_display = ("id", "colaborador", "status", "iniciado_em", "finalizado_em")
    list_filter = ("status", "iniciado_em")
    search_fields = ("colaborador__nome", "colaborador__matricula")
    inlines = [MovimentacaoFerramentaInline]


@admin.register(MovimentacaoFerramenta)
class MovimentacaoFerramentaAdmin(admin.ModelAdmin):
    list_display = (
        "sessao",
        "ferramenta",
        "tipo",
        "gaveta_numero",
        "quantidade",
        "criado_em",
        "confirmado_visao",
    )
    list_filter = ("tipo", "gaveta_numero", "confirmado_visao")
    search_fields = ("ferramenta__nome", "sessao__colaborador__nome")
