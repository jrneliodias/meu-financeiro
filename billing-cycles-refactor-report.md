# Ciclos de Cobrança por Meio de Pagamento - Relatório de Refatoração

## Diagnóstico do Estado Atual

• **Hardcoded logic**: O `BillingPeriodCalculator` tem lógica hardcoded com datas específicas para Nubank (linha 74-99), sem flexibilidade para mudanças futuras

• **Acoplamento forte**: O calculator tem dados específicos do Nubank embutidos no código, violando o princípio da responsabilidade única (SRP)

• **Falta de versionamento**: Não há suporte para alterações históricas - mudanças de `start_billing_day` afetariam retrospectivamente todos os cálculos

• **Timezone inconsistente**: Settings usa `America/Sao_Paulo` mas o prompt especifica `America/Belem` - pode causar inconsistências

• **Campo único no PaymentMethod**: O campo `start_billing_day` é único e global, não suporta mudanças temporais

• **Snapshot model subutilizado**: O modelo `BillingPeriod` existe mas parece ser usado apenas para caching, não para histórico imutável

• **Cálculos distribuídos**: Lógica de billing está espalhada entre `BillingPeriodCalculator`, `ExpenseService` e utilitários em `registers/utils.py`

• **Testes incompletos**: Testes apenas cobrem cenários hardcoded específicos, não cobrem edge cases como anos bissextos ou mudanças de política

• **Anti-pattern DIP**: Calculator não usa dependency injection, dificultando testes e extensibilidade

• **Inconsistência de domínio**: Mistura conceitos de "billing day" fixo com períodos calculados dinamicamente

## Solução A — Política Efetiva por Período (Effective-Dated Policy)

### Descrição

Implementa o padrão "effective-dated policy" onde cada mudança de configuração de ciclo gera uma nova política com vigência definida, preservando o histórico imutável.

### Modelos Django

```python
class PaymentCyclePolicy(models.Model):
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    start_day = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    valid_from = models.DateField(help_text="Data de início da vigência (inclusive)")
    valid_to = models.DateField(null=True, blank=True, help_text="Data de fim da vigência (inclusive). NULL = vigente")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['payment_method', 'valid_from'],
                name='unique_policy_per_payment_method_date'
            ),
            models.CheckConstraint(
                check=models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=models.F('valid_from')),
                name='valid_to_after_valid_from'
            )
        ]
        indexes = [
            models.Index(fields=['payment_method', 'valid_from', 'valid_to']),
            models.Index(fields=['payment_method', '-valid_from'])
        ]

# Remove start_billing_day from PaymentMethod
class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    # start_billing_day removed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Pseudocódigo do Resolver

```python
class CycleResolver:
    def __init__(self, policy_repository: CyclePolicyRepository):
        self.policy_repository = policy_repository

    def resolve_cycle(self, payment_method_id: int, data_referencia: date) -> CycleRange:
        # 1. Buscar política vigente na data de referência
        policy = self.policy_repository.get_effective_policy(
            payment_method_id,
            data_referencia
        )

        if not policy:
            # Default: ciclo mensal padrão (1 ao último dia)
            return self._calculate_default_cycle(data_referencia)

        # 2. Calcular período baseado no start_day da política
        if policy.start_day == 1:
            return self._calculate_calendar_month_cycle(data_referencia)
        else:
            return self._calculate_custom_cycle(data_referencia, policy.start_day)

    def _calculate_custom_cycle(self, data_referencia: date, start_day: int) -> CycleRange:
        # Encontrar o ciclo que contém a data de referência
        # Lógica similar ao BillingPeriodCalculator atual mas parametrizada

        # Para data 2025-09-10 com start_day=3:
        # Ciclo atual: 2025-09-03 a 2025-10-02

        # 1. Verificar se data_referencia >= start_day do mês atual
        if data_referencia.day >= start_day:
            cycle_start = date(data_referencia.year, data_referencia.month, start_day)
            next_month = data_referencia.month + 1 if data_referencia.month < 12 else 1
            next_year = data_referencia.year if data_referencia.month < 12 else data_referencia.year + 1
            cycle_end = date(next_year, next_month, start_day - 1)
        else:
            # Data está no início do mês, pertence ao ciclo anterior
            prev_month = data_referencia.month - 1 if data_referencia.month > 1 else 12
            prev_year = data_referencia.year if data_referencia.month > 1 else data_referencia.year - 1
            cycle_start = date(prev_year, prev_month, start_day)
            cycle_end = date(data_referencia.year, data_referencia.month, start_day - 1)

        return CycleRange(
            period_start=cycle_start,
            period_end=cycle_end,
            timezone=timezone('America/Belem')
        )

class CyclePolicyRepository:
    def get_effective_policy(self, payment_method_id: int, reference_date: date) -> PaymentCyclePolicy:
        return PaymentCyclePolicy.objects.filter(
            payment_method_id=payment_method_id,
            valid_from__lte=reference_date,
            Q(valid_to__isnull=True) | Q(valid_to__gte=reference_date)
        ).order_by('-valid_from').first()
```

### Exemplo Prático

**Nubank:**
- Política 1: valid_from=2024-01-01, valid_to=2025-08-31, start_day=24
- Política 2: valid_from=2025-09-01, valid_to=null, start_day=3

**Consultas:**
- `resolve_cycle(nubank_id, date(2025, 8, 25))` → início=2025-08-24, fim=2025-09-23
- `resolve_cycle(nubank_id, date(2025, 9, 10))` → início=2025-09-03, fim=2025-10-02

**Inter:**
- Política única: valid_from=2024-01-01, valid_to=null, start_day=7
- `resolve_cycle(inter_id, date(2025, 2, 10))` → início=2025-02-07, fim=2025-03-06

### Migrations

```python
# 0001_create_payment_cycle_policy.py
class Migration(migrations.Migration):
    dependencies = [('registers', '0008_add_performance_indexes')]

    operations = [
        migrations.CreateModel(
            name='PaymentCyclePolicy',
            fields=[...] # Conforme modelo acima
        ),
        # Migrar dados existentes
        migrations.RunPython(migrate_existing_billing_days),
    ]

def migrate_existing_billing_days(apps, schema_editor):
    PaymentMethod = apps.get_model('registers', 'PaymentMethod')
    PaymentCyclePolicy = apps.get_model('registers', 'PaymentCyclePolicy')

    for payment_method in PaymentMethod.objects.all():
        PaymentCyclePolicy.objects.create(
            payment_method=payment_method,
            start_day=payment_method.start_billing_day,
            valid_from=date(2024, 1, 1),  # Data histórica segura
            valid_to=None  # Vigente indefinidamente
        )
```

### Prós
- **História imutável**: Mudanças não afetam cálculos passados
- **Flexibilidade total**: Suporta qualquer mudança de start_day em qualquer data
- **Domínio claro**: Separação entre PaymentMethod (entidade) e CyclePolicy (regra temporal)
- **Testabilidade**: Dependency injection facilita testes unitários
- **Performance**: Índices otimizados para consultas temporais
- **Auditoria**: Preserva quem e quando mudou cada política

### Contras
- **Complexidade inicial**: Requer refatoração significativa do código existente
- **Overhead de storage**: Múltiplas linhas por payment method
- **Gestão de sobreposição**: Necessita validação rigorosa para evitar políticas conflitantes
- **Curva de aprendizado**: Desenvolvedores precisam entender o padrão effective-dated

### Impacto na Arquitetura Atual
- **Quebra**: `PaymentMethod.start_billing_day` removido
- **Nova dependência**: Services precisam injetar `CycleResolver`
- **Repositórios**: `CyclePolicyRepository` novo
- **Testes**: Todos os testes de billing precisam ser reescritos

### Plano de Migração
1. Criar modelo `PaymentCyclePolicy` sem quebrar existente
2. Migrar dados de `start_billing_day` para políticas com `valid_from` histórico
3. Implementar `CycleResolver` e `CyclePolicyRepository`
4. Atualizar services para usar novo resolver (feature flag)
5. Remover campo antigo após validação completa

### Plano de Testes
- **Unitários**: `CycleResolver` com mock repository
- **Integração**: Cenários completos Nubank/Inter com mudanças temporais
- **Edge cases**: Anos bissextos, start_day > dias do mês, sobreposições
- **Performance**: Benchmark consultas com múltiplas políticas

## Solução B — Snapshot por Mês (BillingCycleInstance)

### Descrição

Materializa e congela um snapshot de cada ciclo de cobrança quando ele é criado/usado pela primeira vez, garantindo imutabilidade através de dados pré-calculados.

### Modelos Django

```python
class BillingCycleInstance(models.Model):
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    year_month = models.CharField(max_length=7, help_text="YYYY-MM do mês de cobrança")
    period_start = models.DateField()
    period_end = models.DateField()
    computed_from_start_day = models.IntegerField(help_text="start_day usado no cálculo")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[('open', 'Open'), ('closed', 'Closed')], default='open')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['payment_method', 'year_month'],
                name='unique_cycle_per_payment_method_month'
            )
        ]
        indexes = [
            models.Index(fields=['payment_method', 'year_month']),
            models.Index(fields=['payment_method', 'period_start', 'period_end']),
            models.Index(fields=['status'])
        ]

# PaymentMethod mantém start_billing_day para novos cálculos
class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    start_billing_day = models.IntegerField(help_text="Dia atual para novos ciclos")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Pseudocódigo do Resolver

```python
class CycleSnapshotResolver:
    def __init__(self, cycle_repository: CycleInstanceRepository, payment_method_repository):
        self.cycle_repository = cycle_repository
        self.payment_method_repository = payment_method_repository

    def resolve_cycle(self, payment_method_id: int, data_referencia: date) -> CycleRange:
        # 1. Determinar year_month baseado na data de referência
        billing_month = self._determine_billing_month(payment_method_id, data_referencia)

        # 2. Buscar snapshot existente
        cycle_instance = self.cycle_repository.get_cycle_instance(
            payment_method_id,
            billing_month
        )

        if cycle_instance:
            return CycleRange(
                period_start=cycle_instance.period_start,
                period_end=cycle_instance.period_end,
                timezone=timezone('America/Belem')
            )

        # 3. Criar novo snapshot se não existir
        return self._create_cycle_snapshot(payment_method_id, billing_month, data_referencia)

    def _create_cycle_snapshot(self, payment_method_id: int, billing_month: str, data_referencia: date) -> CycleRange:
        payment_method = self.payment_method_repository.get_by_id(payment_method_id)

        # Usar start_billing_day ATUAL do payment method
        year, month = map(int, billing_month.split('-'))

        if payment_method.start_billing_day == 1:
            period_start = date(year, month, 1)
            period_end = date(year, month, calendar.monthrange(year, month)[1])
        else:
            # Lógica de cálculo customizado
            period_start, period_end = self._calculate_custom_period(
                year, month, payment_method.start_billing_day
            )

        # Materializar snapshot
        cycle_instance = BillingCycleInstance.objects.create(
            payment_method_id=payment_method_id,
            year_month=billing_month,
            period_start=period_start,
            period_end=period_end,
            computed_from_start_day=payment_method.start_billing_day,
            status='open'
        )

        return CycleRange(
            period_start=period_start,
            period_end=period_end,
            timezone=timezone('America/Belem')
        )

class CycleInstanceRepository:
    def get_cycle_instance(self, payment_method_id: int, year_month: str) -> BillingCycleInstance:
        return BillingCycleInstance.objects.filter(
            payment_method_id=payment_method_id,
            year_month=year_month
        ).first()
```

### Exemplo Prático

**Cenário Nubank - Mudança em setembro:**

1. **Agosto 2025**: Primeira consulta cria snapshot com `start_day=24`
   - Instance: year_month="2025-08", period_start="2025-08-24", period_end="2025-09-23", computed_from_start_day=24

2. **Setembro 2025**: Admin altera PaymentMethod.start_billing_day para 3
   - Instance: year_month="2025-09", period_start="2025-09-03", period_end="2025-10-02", computed_from_start_day=3

3. **Consultas futuras**:
   - `resolve_cycle(nubank_id, date(2025, 8, 25))` → usa snapshot existente (24-23)
   - `resolve_cycle(nubank_id, date(2025, 9, 10))` → usa snapshot existente (03-02)

### Migrations

```python
# 0001_create_billing_cycle_instance.py
class Migration(migrations.Migration):
    dependencies = [('reports', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='BillingCycleInstance',
            fields=[...] # Conforme modelo acima
        ),
        # Opcional: migrar BillingPeriod existente para BillingCycleInstance
        migrations.RunPython(migrate_existing_billing_periods),
    ]
```

### Prós
- **Simplicidade conceitual**: Um snapshot = um período imutável
- **Performance excelente**: Dados pré-calculados, sem computação em runtime
- **Compatibilidade**: PaymentMethod mantém estrutura atual
- **Debugabilidade**: Fácil visualizar todos os períodos materializados
- **Rollback simples**: Pode deletar snapshots problemáticos
- **Caching natural**: Dados ficam persistidos automaticamente

### Contras
- **Storage crescente**: Um registro por mês por payment method
- **Lazy loading**: Dependência de primeira consulta para criar snapshot
- **Gestão de status**: Necessita coordenador para abrir/fechar ciclos
- **Inconsistência temporal**: Snapshot criado hoje com regra de hoje, mesmo para mês passado
- **Complexidade de invalidação**: Como tratar mudanças de regra para meses futuros já calculados

### Impacto na Arquitetura Atual
- **Mínimo**: PaymentMethod mantém interface atual
- **Extensão**: Adiciona camada de snapshot sem quebrar existente
- **Migração suave**: Pode coexistir com código atual durante transição

### Plano de Migração
1. Criar `BillingCycleInstance` sem impactar código existente
2. Implementar `CycleSnapshotResolver` como alternativa opcional
3. Migrar services gradualmente via feature flag
4. Povoar snapshots históricos baseados em dados existentes
5. Deprecar código antigo após validação completa

### Plano de Testes
- **Criação de snapshots**: Primeiro acesso cria corretamente
- **Imutabilidade**: Mudanças de start_day não afetam snapshots existentes
- **Status management**: Ciclos abertos vs fechados
- **Performance**: Benchmark criação vs consulta de snapshots

## Comparativo A vs B

| Critério | Solução A (Effective-Dated) | Solução B (Snapshot) |
|----------|----------------------------|----------------------|
| **Flexibilidade** | ⭐⭐⭐⭐⭐ Total - qualquer mudança em qualquer data | ⭐⭐⭐ Boa - mudanças afetam apenas futuros snapshots |
| **Performance** | ⭐⭐⭐ Boa - consulta + cálculo | ⭐⭐⭐⭐⭐ Excelente - dados pré-calculados |
| **Complexidade** | ⭐⭐ Alta - padrão avançado | ⭐⭐⭐⭐ Baixa - conceito simples |
| **Storage** | ⭐⭐⭐⭐ Baixo - apenas políticas | ⭐⭐ Alto - snapshot por mês |
| **Auditoria** | ⭐⭐⭐⭐⭐ Completa - histórico de mudanças | ⭐⭐⭐ Básica - apenas resultado final |
| **Debugabilidade** | ⭐⭐⭐ Média - precisa recalcular | ⭐⭐⭐⭐⭐ Excelente - dados visíveis |
| **Migração** | ⭐⭐ Difícil - refatoração grande | ⭐⭐⭐⭐ Fácil - extensão incremental |
| **Manutenibilidade** | ⭐⭐⭐⭐ Boa - padrão conhecido | ⭐⭐⭐⭐ Boa - lógica direta |

## Plano de Migração Recomendado (Solução B)

### Fase 1: Preparação (1-2 semanas)
1. Criar modelo `BillingCycleInstance` com migration
2. Implementar `CycleSnapshotResolver` e repositories
3. Adicionar feature flag `USE_CYCLE_SNAPSHOTS`
4. Criar testes unitários e de integração

### Fase 2: Implementação (2-3 semanas)
1. Atualizar `ExpenseCalculator` para usar novo resolver quando flag ativa
2. Implementar coordenador para gestão de status (open/closed)
3. Criar management command para povoar snapshots históricos
4. Executar migration de dados em staging

### Fase 3: Validação (1-2 semanas)
1. Ativar feature flag em ambiente de teste
2. Executar bateria completa de testes
3. Validar performance com dados reais
4. Ajustar índices se necessário

### Fase 4: Deploy (1 semana)
1. Deploy em produção com flag desabilitada
2. Executar povoamento de snapshots históricos
3. Ativar flag gradualmente (por payment method)
4. Monitorar métricas e logs

### Fase 5: Limpeza (1 semana)
1. Remover código antigo após validação
2. Limpar feature flags
3. Otimizar índices finais
4. Documentar nova arquitetura

## Critérios de Aceitação

### AC1: Nubank - Mudança Temporal
- ✅ Período 2024-01 a 2025-08: início=24, fim=23 do mês seguinte
- ✅ Período 2025-09 em diante: início=3, fim=2 do mês seguinte
- ✅ Consulta para agosto 2025 retorna 2025-08-24 a 2025-09-23
- ✅ Consulta para setembro 2025 retorna 2025-09-03 a 2025-10-02
- ✅ Mudança não afeta cálculos anteriores a setembro

### AC2: Inter - Política Contínua
- ✅ início=7, fim=6 do mês seguinte até mudança futura
- ✅ Consulta para qualquer mês retorna início no dia 7

### AC3: PIX - Mês Calendário
- ✅ início=1, fim=último dia do mês
- ✅ Fevereiro 2024 (bissexto): início=2024-02-01, fim=2024-02-29
- ✅ Fevereiro 2025 (normal): início=2025-02-01, fim=2025-02-28

### AC4: Ciclos Cross-Month
- ✅ Nubank setembro 2025: início=2025-09-03, fim=2025-10-02
- ✅ Inter fevereiro: início=2025-02-07, fim=2025-03-06

### AC5: Imutabilidade Histórica
- ✅ Alterar start_day de payment method não reprocessa meses fechados
- ✅ Snapshots já criados permanecem inalterados
- ✅ Apenas novos períodos usam nova configuração

## Checklist SOLID

### Single Responsibility Principle (SRP)
- ✅ **Solução A**: `CycleResolver` apenas resolve ciclos, `CyclePolicyRepository` apenas acessa políticas
- ✅ **Solução B**: `CycleSnapshotResolver` apenas resolve/cria snapshots, `CycleInstanceRepository` apenas acessa dados

### Open/Closed Principle (OCP)
- ✅ **Solução A**: Novas políticas podem ser adicionadas sem modificar resolver
- ✅ **Solução B**: Novos tipos de snapshot podem ser criados via extensão

### Liskov Substitution Principle (LSP)
- ✅ **Ambas**: `CycleRange` retornado é consistente independente da implementação

### Interface Segregation Principle (ISP)
- ✅ **Solução A**: `CyclePolicyRepository` interface específica para políticas
- ✅ **Solução B**: `CycleInstanceRepository` interface específica para snapshots

### Dependency Inversion Principle (DIP)
- ✅ **Ambas**: Resolvers dependem de abstrações (repositories), não implementações concretas
- ✅ **Testabilidade**: Mocking de repositories facilita testes isolados

## Riscos & Mitigações

### Risco: Inconsistência de Timezone
- **Problema**: Settings usa `America/Sao_Paulo`, prompt especifica `America/Belem`
- **Mitigação**: Padronizar timezone no settings e documentar explicitamente

### Risco: Data Integrity
- **Problema**: Snapshots criados com regras incorretas
- **Mitigação**: Validação rigorosa antes de materializar + rollback strategy

### Risco: Performance Degradation
- **Problema**: Consultas podem ficar lentas com múltiplos snapshots
- **Mitigação**: Índices otimizados + monitoring + paginação

### Risco: Edge Cases Não Cobertos
- **Problema**: start_day=31 em meses com menos dias
- **Mitigação**: Lógica específica + testes abrangentes + fallback para último dia

### Risco: Migration Data Loss
- **Problema**: Perda de dados durante migração
- **Mitigação**: Backup completo + migration reversa + validação pós-migração

## Recomendação Final

**Recomendo a Solução B (Snapshot)** pelos seguintes motivos:

1. **Menor risco**: Migração incremental sem quebrar sistema atual
2. **Performance superior**: Dados pré-calculados eliminam computação em runtime
3. **Simplicidade conceitual**: Mais fácil para equipe entender e manter
4. **Debugging facilitado**: Snapshots visíveis facilitam troubleshooting
5. **Compatibilidade**: Preserva interface atual do PaymentMethod

A Solução A seria ideal para sistemas com mudanças muito frequentes de políticas, mas para o contexto atual (mudanças ocasionais), a Solução B oferece melhor custo-benefício.