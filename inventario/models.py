from django.db import models


class Gaveta(models.Model):
    numero = models.PositiveSmallIntegerField(
        unique=True,
        help_text="Número físico da gaveta (ex: 1, 2, 3...)"
    )
    nome = models.CharField(
        max_length=50,
        blank=True,
        help_text="Nome amigável (ex: Chaves, Alicates, Soquetes)"
    )
    descricao = models.TextField(blank=True)
    ativa = models.BooleanField(
        default=True,
        help_text="Se desmarcado, a gaveta não é usada pelo sistema"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "Gaveta"
        verbose_name_plural = "Gavetas"

    def __str__(self):
        return self.nome or f"Gaveta {self.numero}"


class Ferramenta(models.Model):
    nome = models.CharField(max_length=100)
    codigo = models.CharField(
        max_length=50,
        blank=True,
        help_text="Código interno / patrimonial (opcional)"
    )
    descricao = models.TextField(blank=True)

    gaveta = models.ForeignKey(
        Gaveta,
        on_delete=models.PROTECT,
        related_name="ferramentas"
    )

    posicao = models.PositiveSmallIntegerField(
        help_text="Posição/slot na gaveta (linkado com o índice de ROI da visão)"
    )

    quantidade = models.PositiveIntegerField(
        default=1,
        help_text="Quantidade dessa ferramenta (se houver mais de uma igual)"
    )

    ativa = models.BooleanField(
        default=True,
        help_text="Se desmarcado, não aparece como disponível para retirada"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("gaveta", "posicao")
        ordering = ["gaveta", "posicao", "nome"]
        verbose_name = "Ferramenta"
        verbose_name_plural = "Ferramentas"

    def __str__(self):
        return f"{self.nome} (Gaveta {self.gaveta.numero}, slot {self.posicao})"
