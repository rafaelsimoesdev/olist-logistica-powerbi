# Medidas DAX da versão manual

As 29 medidas criadas à mão no Power BI, agrupadas pelo que respondem. Todas ficam na tabela `_Medidas`.

## Tabela calendário

```dax
dim_calendario =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2017, 1, 1 ), DATE ( 2018, 12, 31 ) ),
    "Ano", YEAR ( [Date] ),
    "Mês Nº", MONTH ( [Date] ),
    "Mês/Ano", FORMAT ( [Date], "mmm/yy" ),
    "AnoMesNum", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "Trimestre", "T" & QUARTER ( [Date] ),
    "Dia da semana", FORMAT ( [Date], "ddd" ),
    "Dia semana Nº", WEEKDAY ( [Date], 2 )
)
```

## Volume e prazo

```dax
Pedidos = COUNTROWS ( fato_pedidos )
Pedidos Entregues = CALCULATE ( [Pedidos], fato_pedidos[entregue] = 1 )
Pedidos Atrasados = CALCULATE ( [Pedidos], fato_pedidos[atrasado] = 1 )
% Atraso = DIVIDE ( [Pedidos Atrasados], [Pedidos Entregues] )
% No Prazo = DIVIDE ( [Pedidos Entregues] - [Pedidos Atrasados], [Pedidos Entregues] )
Prazo Médio Real = CALCULATE ( AVERAGE ( fato_pedidos[dias_entrega] ), fato_pedidos[entregue] = 1 )
Prazo Médio Prometido = CALCULATE ( AVERAGE ( fato_pedidos[dias_prometidos] ), fato_pedidos[entregue] = 1 )
Folga Média de Prazo = [Prazo Médio Prometido] - [Prazo Médio Real]
Dias Médios de Atraso = CALCULATE ( AVERAGE ( fato_pedidos[dias_atraso] ), fato_pedidos[atrasado] = 1 )
```

## Etapas do lead time

```dax
Tempo Aprovação = CALCULATE ( AVERAGE ( fato_pedidos[dias_aprovacao] ), fato_pedidos[entregue] = 1 )
Tempo Postagem = CALCULATE ( AVERAGE ( fato_pedidos[dias_postagem] ), fato_pedidos[entregue] = 1 )
Tempo Transporte = CALCULATE ( AVERAGE ( fato_pedidos[dias_transporte] ), fato_pedidos[entregue] = 1 )

% Tempo em Transporte =
DIVIDE ( [Tempo Transporte], [Tempo Aprovação] + [Tempo Postagem] + [Tempo Transporte] )

% Postagem Atrasada =
DIVIDE (
    CALCULATE ( [Pedidos], fato_pedidos[postagem_atrasada] = 1 ),
    CALCULATE ( [Pedidos], NOT ISBLANK ( fato_pedidos[data_postagem] ) )
)

% Atraso - Postagem no Prazo = CALCULATE ( [% Atraso], fato_pedidos[postagem_atrasada] = 0 )
% Atraso - Postagem Atrasada = CALCULATE ( [% Atraso], fato_pedidos[postagem_atrasada] = 1 )
```

## Cliente e custo

```dax
Nota Média = CALCULATE ( AVERAGE ( fato_pedidos[nota_avaliacao] ), fato_pedidos[entregue] = 1 )
Nota Média - No Prazo = CALCULATE ( [Nota Média], fato_pedidos[atrasado] = 0 )
Nota Média - Atrasado = CALCULATE ( [Nota Média], fato_pedidos[atrasado] = 1 )

% Avaliações Ruins =
DIVIDE (
    CALCULATE ( COUNT ( fato_pedidos[nota_avaliacao] ), fato_pedidos[nota_avaliacao] <= 2, fato_pedidos[entregue] = 1 ),
    CALCULATE ( COUNT ( fato_pedidos[nota_avaliacao] ), fato_pedidos[entregue] = 1 )
)

Faturamento = SUM ( fato_pedidos[valor_produtos] )
Frete Total = SUM ( fato_pedidos[valor_frete] )
Frete Médio por Pedido = AVERAGE ( fato_pedidos[valor_frete] )
% Frete sobre Produtos = DIVIDE ( [Frete Total], [Faturamento] )
```

## Tempo e formatação condicional

```dax
% Atraso Mês Anterior = CALCULATE ( [% Atraso], DATEADD ( dim_calendario[Date], -1, MONTH ) )
Variação Atraso (p.p.) = ( [% Atraso] - [% Atraso Mês Anterior] ) * 100

Entregas na Data =
CALCULATE ( [Pedidos Entregues], USERELATIONSHIP ( dim_calendario[Date], fato_pedidos[data_entrega] ) )

Meta % Atraso = 0.05
Cor Atraso = IF ( [% Atraso] > [Meta % Atraso], "#EB6834", "#2A78D6" )
```
