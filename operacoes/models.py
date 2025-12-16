from django.db import models


class SessaoUso(models.Model):
    """
    Representa uma 'sessão' iniciada quando o colaborador passa o cartão na Rock Pi.
    Pode envolver várias retiradas e devoluções de ferramentas.
    """
     # só para type hint no editor

    STATUS_CHOICES = [
        ("A", "Em andamento"),
        ("F", "Finalizada"),
        ("C", "Cancelada"),
        ("E", "Expirada / Timeout"),
    ]

    colaborador = models.ForeignKey(
        "usuarios.Colaborador",
        on_delete=models.PROTECT,
        related_name="sessoes"
    )
    cartao = models.ForeignKey(
        "usuarios.CartaoNFC",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="sessoes"
    )

    iniciado_em = models.DateTimeField(auto_now_add=True)
    finalizado_em = models.DateTimeField(blank=True, null=True)

    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default="A"
    )

    # JSON/metadata que veio da Rock Pi na abertura (opcional)
    payload_inicial = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = "Sessão de Uso"
        verbose_name_plural = "Sessões de Uso"

    def __str__(self):
        return f"Sessão #{self.id} - {self.colaborador.nome} - {self.get_status_display()}"


class MovimentacaoFerramenta(models.Model):
    """
    Uma linha para cada retirada ou devolução de uma ferramenta
    dentro de uma sessão de uso.
    """
    TIPO_CHOICES = [
        ("R", "Retirada"),
        ("D", "Devolução"),
    ]

    sessao = models.ForeignKey(
        SessaoUso,
        on_delete=models.CASCADE,
        related_name="movimentacoes"
    )

    ferramenta = models.ForeignKey(
        "inventario.Ferramenta",
        on_delete=models.PROTECT,
        related_name="movimentacoes"
    )

    tipo = models.CharField(
        max_length=1,
        choices=TIPO_CHOICES
    )

    # Snapshot de informação importante
    gaveta_numero = models.PositiveSmallIntegerField(
        help_text="Número da gaveta no momento da operação"
    )

    quantidade = models.PositiveIntegerField(default=1)

    # Integração com visão computacional
    imagem_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Caminho relativo da imagem capturada (se houver)"
    )
    confirmado_visao = models.BooleanField(
        default=False,
        help_text="Se True, a visão computacional confirmou a movimentação"
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimentação de Ferramenta"
        verbose_name_plural = "Movimentações de Ferramenta"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.ferramenta.nome} (sessão {self.sessao_id})"
