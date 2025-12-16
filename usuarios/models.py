from django.db import models


class Colaborador(models.Model):
    nome = models.CharField(max_length=150)
    matricula = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código interno / matrícula do colaborador"
    )
    email = models.EmailField(blank=True, null=True)
    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"

    def __str__(self):
        return f"{self.nome} ({self.matricula})"


class CartaoNFC(models.Model):
    uid = models.CharField(
        "UID do cartão",
        max_length=32,
        unique=True,
        help_text="UID lido pelo RC522 (enviado via MQTT pela Rock Pi)"
    )
    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="cartoes"
    )
    apelido = models.CharField(
        max_length=50,
        blank=True,
        help_text="Opcional: apelido do cartão (ex: 'Capacete', 'Cartão reserva')"
    )
    ativo = models.BooleanField(
        default=True,
        help_text="Se desmarcado, o cartão não autoriza uso da caixa"
    )

    ultimo_uso_em = models.DateTimeField(
        blank=True,
        null=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cartão NFC"
        verbose_name_plural = "Cartões NFC"

    def __str__(self):
        return f"{self.uid} - {self.colaborador.nome}"
