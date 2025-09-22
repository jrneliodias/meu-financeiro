# PROMPT PARA O AGENTE — “Ciclos de cobrança por meio de pagamento (com histórico imutável)”

## Contexto

Tenho um sistema de gestão financeira (Django + Python) que calcula despesas por **ciclos de cobrança** (mês de pagamento).
Regra padrão: para PIX (e como default), o ciclo vai do dia **1** ao **último dia do mês** (28/29/30/31).
Alguns meios de pagamento (ex.: cartões) têm **dias de início customizados** e **podem mudar ao longo do tempo**, sem **alterar meses passados** (histórico imutável).

Exemplos:

* Nubank: de **2024-01** até **2025-08**, ciclo inicia no **dia 24** e termina no **dia 23** do mês seguinte.
  A partir de **2025-09**, alterei o início para **dia 3** (termina dia 2 do mês seguinte).
  Isso **não** deve reabrir/recalcular meses anteriores.
* Inter: inicia **dia 7** e termina **dia 6** do mês seguinte (até que seja alterado futuramente).

Quero **refatorar/implementar** para suportar isso de forma limpa, coesa, testável e compatível com SOLID.

> Timezone relevante: `America/Belem`.

## O que analisar no repositório

1. Modelos/entidades relacionadas a “meios de pagamento”, “lançamentos” e “ciclos” (ex.: `PaymentMethod`, `Transaction`, `Expense`, `Invoice`, `BillingCycle`, etc.).
2. Onde o ciclo é calculado (serviços/úteis/queries).
3. Dependências e acoplamentos (service layer, repositórios, signals, tasks).
4. Pontos de persistência (migrations, constraints e índices).
5. Testes existentes (unitários/integrados) para cálculo de ciclos.
6. Pontos que podem quebrar com **alterações retroativas** hoje.

## Entregáveis obrigatórios

1. **Diagnóstico do estado atual** (máximo 10 bullets):

   * Onde está o cálculo do ciclo, anticorpos a SOLID, riscos de regressão, lacunas de testes.
2. **Duas soluções alternativas de arquitetura** (A e B), cada uma com:

   * **Descrição** (como funciona, classes novas/alteradas, relações).
   * **Pseudocódigo** da função “resolver ciclo”:

     * Entrada: `{payment_method_id, data_referencia (date)}`
     * Saída: `{inicio (date), fim (date)}`
   * **Esboço Django models/migrations** necessários (nomes e campos essenciais).
   * **Fluxo de leitura/escrita** (quem decide o ciclo, quando e onde persiste).
   * **Prós** (manutenibilidade, testabilidade, clareza de domínio, performance).
   * **Contras** (complexidade, custo de migração, trade-offs).
   * **Impacto na arquitetura atual** (o que muda, o que permanece).
   * **Plano de migração de dados** (passo a passo, idempotente).
   * **Plano de testes** (unitários, integrados e casos de borda).
3. **Critérios de aceitação** cobrindo:

   * Nubank: 2024-01→2025-08 (inicio=24), e a partir de 2025-09 (inicio=3) **sem alterar meses passados**.
   * Inter: inicio=7 (até mudança futura).
   * PIX: 1→último dia do mês, incluindo fev/ano bissexto.
   * Fechamentos que atravessam o mês (ex.: início 24 → fim 23 do próximo).
   * Mudanças futuras de dia não reabrirem períodos já consolidados.
4. **Checklist SOLID**: como cada solução respeita SRP, OCP, LSP, ISP, DIP.

## Regras e restrições

* **Não** reprocessar meses passados ao alterar o “dia de início” de um meio de pagamento.
* Preferir **imutabilidade** do histórico (ex.: criar novas “políticas vigentes” em vez de editar registros antigos).
* Evitar “spaghetti” em helpers utilitários; preferir **serviços/coordenadores** com dependências explícitas.
* Ser explícito sobre **timezone**, **último dia do mês** e **ano bissexto**.
* Explicar **índices** e **constraints** que evitam registros vigentes sobrepostos.

## Direcionadores das duas soluções (o agente deve desenvolver em detalhes)

### Solução A — “Política efetiva por período (effective-dated policy)”

* **Ideia**: criar uma entidade `CyclePolicy` (ou `PaymentCyclePolicy`) com **faixa de vigência** (`valid_from`, `valid_to` opcional), **payment\_method** e **start\_day**.
* O cálculo de um ciclo para uma data usa a **policy vigente** naquela data.
* Histórico garantido por **novas linhas** (nunca mutar políticas antigas).
* Sugestão de modelos (esqueleto que o agente deve detalhar):

  ```text
  PaymentMethod(id, name, type, ...)

  PaymentCyclePolicy(
    id,
    payment_method (FK),
    start_day (1..28/29/30/31),
    valid_from (date),  -- inclusive
    valid_to   (date?)  -- inclusive ou null => vigente
    UNIQUE(payment_method, valid_from) / constraint anti-sobreposição
  )
  ```
* **Quando** persistir `BillingCycle` materializado? (opcional)

  * Lazy (calcular on-the-fly) vs. eager (snapshot mensal após fechamento).
* O agente deve discutir trade-offs e propor **índices** e **queries**.

### Solução B — “Instância de ciclo (snapshot) por mês”

* **Ideia**: materializar e **congelar** um `BillingCycleInstance` **por mês** e **meio de pagamento** (ex.: no fechamento ou no primeiro lançamento do período).
* Mudou o dia em 2025-09? A partir de **2025-09** criam-se novas instâncias com a nova regra; as instâncias antigas continuam intactas.
* Sugestão de modelos:

  ```text
  BillingCycleInstance(
    id,
    payment_method (FK),
    year_month (YYYYMM ou primeiro dia do ciclo),
    period_start (date),
    period_end   (date),
    computed_from_policy_id (FK opcional),
    status (open|closed),
    UNIQUE(payment_method, year_month)
  )
  ```
* O agente deve explicar o **coordenador** que decide quando criar/fechar o snapshot e como recalcular apenas enquanto **status=open**.

## Casos de borda (obrigatório cobrir)

* Meses com 28/29/30/31 dias; **fevereiro bissexto**.
* Ciclo que começa no fim do mês (ex.: 30 ou 31) e meses seguintes com menos dias.
* Mudança de `start_day` em uma data intermediária (ex.: mudança em **2025-09-15** — qual a data efetiva recomendada? **Padrão: primeiro dia do próximo ciclo**, documentar).
* Timezone `America/Belem` (não variar fronteiras por UTC).
* Idempotência da migração.
* Overlaps de políticas (impedir via constraint/validação).

## Saída final (formato)

* **Relatório estruturado** em Markdown com as seções:
  `Diagnóstico`, `Solução A`, `Solução B`, `Comparativo A vs B`, `Plano de Migração`, `Plano de Testes`, `Critérios de Aceitação`, `Checklist SOLID`, `Riscos & Mitigações`.
* Em cada solução, incluir:

  * **Pseudocódigo** de `resolve_cycle(payment_method_id, data_referencia)`
  * **Exemplo prático** (Nubank e Inter) demonstrando datas de início/fim para **2025-08** e **2025-09**.
  * **Sugestão de Migrations** (DDL ou `models.py` esqueleto) e **índices**.

## Dicas de implementação (o agente deve validar no código atual)

* Encapsular cálculo de ciclo em um **serviço/coordenador** (ex.: `CycleResolver`) injetando um **CyclePolicyRepository** (DIP).
* `resolve_cycle` retorna um **Value Object** imutável (`CycleRange`) com `period_start`, `period_end`.
* Para “último dia do mês”, usar calendário local (sem UTC shift).
* Cobrir unidade + integração com fixtures:

  * `Nubank / data=2025-08-25` → início=2025-08-24, fim=2025-09-23
  * `Nubank / data=2025-09-10` → início=2025-09-03, fim=2025-10-02
  * `Inter / data=2025-02-10` (ano bissexto) → validar fim correto.

---

> **Instrução final ao agente:**
> Gere o relatório completo conforme solicitado. Seja específico no código/pseudocódigo e nos planos de migração/testes. Não omita prós/cons nem riscos.
