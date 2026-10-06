"""Gera o projeto Power BI (PBIP: TMDL + PBIR) do dashboard de logística Olist."""
import json, os, shutil, sys

PROJ = r"C:\Users\Pichau\Documents\Projeto_Olist_Logistica"
NOME = "dashboard_logistica_olist"
EXCEL = os.path.join(PROJ, "dados", "olist_logistica_powerbi.xlsx")
SM = os.path.join(PROJ, NOME + ".SemanticModel")
RP = os.path.join(PROJ, NOME + ".Report")

AZUL, LARANJA, CINZA = "#2A78D6", "#EB6834", "#8A8984"
TXT, TXT2, BORDA, FUNDO = "#0B0B0B", "#52514E", "#E6E6E3", "#F4F5F7"
FONTE = "Segoe UI"


def w(path, txt):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)


def wj(path, obj):
    w(path, json.dumps(obj, ensure_ascii=False, indent=2))


for d in (SM, RP):
    if os.path.exists(d):
        shutil.rmtree(d)

# =====================================================================
# PBIP
# =====================================================================
wj(os.path.join(PROJ, NOME + ".pbip"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0",
    "artifacts": [{"report": {"path": NOME + ".Report"}}],
    "settings": {"enableAutoRecovery": True},
})

# =====================================================================
# MODELO SEMÂNTICO (TMDL)
# =====================================================================
wj(os.path.join(SM, "definition.pbism"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
    "version": "4.2",
    "settings": {},
})

w(os.path.join(SM, "definition", "database.tmdl"), "database\n\tcompatibilityLevel: 1600\n\n")

w(os.path.join(SM, "definition", "model.tmdl"), """model Model
\tculture: pt-BR
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tsourceQueryCulture: pt-BR
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

annotation PBI_QueryOrder = ["CaminhoExcel","fato_pedidos","dim_estado","dim_vendedor","dim_categoria"]

annotation __PBI_TimeIntelligenceEnabled = 0

ref table fato_pedidos
ref table dim_estado
ref table dim_vendedor
ref table dim_categoria
ref table dim_calendario
ref table etapa
""")

w(os.path.join(SM, "definition", "expressions.tmdl"),
  f'expression CaminhoExcel = "{EXCEL}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
  '\tannotation PBI_ResultType = Text\n\n')


def m_aba(aba, tipos):
    tl = ", ".join('{"%s", %s}' % (c, t) for c, t in tipos)
    return (
        "let\n"
        "    Fonte = Excel.Workbook(File.Contents(CaminhoExcel), null, true),\n"
        f'    Aba = Fonte{{[Item="{aba}",Kind="Sheet"]}}[Data],\n'
        "    Cabecalhos = Table.PromoteHeaders(Aba, [PromoteAllScalars=true]),\n"
        f"    Tipos = Table.TransformColumnTypes(Cabecalhos, {{{tl}}})\n"
        "in\n"
        "    Tipos"
    )


MAP_M = {"string": "type text", "dateTime": "type date", "int64": "Int64.Type", "double": "type number"}


def tabela(nome, colunas, extra="", hidden_cols=(), categorias=None):
    """colunas: lista de (nome, tmdl_type, formatString|None, summarizeBy)"""
    categorias = categorias or {}
    out = [f"table {nome}", ""]
    out.append(extra)
    for c, t, fmt, summ in colunas:
        cn = f"'{c}'" if not c.isidentifier() else c
        out.append(f"\tcolumn {cn}")
        out.append(f"\t\tdataType: {t}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        if c in categorias:
            out.append(f"\t\tdataCategory: {categorias[c]}")
        if c in hidden_cols:
            out.append("\t\tisHidden")
        out.append(f"\t\tsummarizeBy: {summ}")
        out.append(f"\t\tsourceColumn: {c}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = Automatic")
        out.append("")
    m = m_aba(nome, [(c, MAP_M[t]) for c, t, _, _ in colunas])
    out.append(f"\tpartition {nome} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out += ["\t\t\t\t" + l for l in m.split("\n")]
    out.append("")
    return "\n".join(out) + "\n"


S, D, I, F = "string", "dateTime", "int64", "double"
DT = "dd/mm/yyyy"
fato_cols = [
    ("id_pedido", S, None, "none"), ("id_cliente", S, None, "none"), ("id_vendedor", S, None, "none"),
    ("categoria", S, None, "none"), ("uf_cliente", S, None, "none"), ("cidade_cliente", S, None, "none"),
    ("uf_vendedor", S, None, "none"), ("status", S, None, "none"),
    ("data_compra", D, DT, "none"), ("data_aprovacao", D, DT, "none"), ("data_postagem", D, DT, "none"),
    ("data_entrega", D, DT, "none"), ("data_prevista", D, DT, "none"),
    ("qtd_itens", I, "0", "sum"), ("qtd_vendedores", I, "0", "sum"),
    ("valor_produtos", F, "#,0.00", "sum"), ("valor_frete", F, "#,0.00", "sum"),
    ("peso_total_kg", F, "#,0.000", "sum"), ("distancia_km", F, "#,0", "average"),
    ("faixa_distancia", S, None, "none"), ("rota", S, None, "none"),
    ("dias_aprovacao", F, "0.0", "average"), ("dias_postagem", F, "0.0", "average"),
    ("dias_transporte", F, "0.0", "average"), ("dias_entrega", F, "0.0", "average"),
    ("dias_prometidos", I, "0", "average"), ("dias_atraso", I, "0", "average"),
    ("entregue", I, "0", "sum"), ("atrasado", I, "0", "sum"), ("postagem_atrasada", I, "0", "sum"),
    ("nota_avaliacao", I, "0", "average"),
]

ENT = "fato_pedidos[entregue] = 1"
medidas = [
    # nome, expressão, formato, pasta
    ("Pedidos entregues", "SUM(fato_pedidos[entregue])", "#,0", "1. Volume"),
    ("Pedidos atrasados", "SUM(fato_pedidos[atrasado])", "#,0", "1. Volume"),
    ("Pedidos entregues (mil)", "DIVIDE([Pedidos entregues], 1000)", '#,0.0" mil"', "1. Volume"),
    ("% Atraso", "DIVIDE([Pedidos atrasados], [Pedidos entregues])", "0.0%", "2. Atraso"),
    ("% Atraso top 10 UF",
     "-- só estados com pelo menos 100 pedidos entregues, para evitar amostras pequenas (ex.: RR)\n"
     "\t\t\tIF(\n\t\t\t\tISINSCOPE(dim_estado[uf]) && [Pedidos entregues] >= 100,\n"
     "\t\t\t\tVAR r = RANKX(FILTER(ALLSELECTED(dim_estado[uf]), [Pedidos entregues] >= 100), [% Atraso], , DESC)\n"
     "\t\t\t\tRETURN IF(r <= 10, [% Atraso])\n\t\t\t)", "0.0%", "2. Atraso"),
    ("% Atraso SP", 'CALCULATE([% Atraso], dim_estado[uf] = "SP")', "0.0%", "2. Atraso"),
    ("Prazo médio real", f"CALCULATE(AVERAGE(fato_pedidos[dias_entrega]), {ENT})", '0.0" dias"', "3. Prazos"),
    ("Prazo médio prometido", f"CALCULATE(AVERAGE(fato_pedidos[dias_prometidos]), {ENT})", '0.0" dias"', "3. Prazos"),
    ("Dias aprovação", f"CALCULATE(AVERAGE(fato_pedidos[dias_aprovacao]), {ENT})", "0.0", "3. Prazos"),
    ("Dias postagem", f"CALCULATE(AVERAGE(fato_pedidos[dias_postagem]), {ENT})", "0.0", "3. Prazos"),
    ("Dias transporte", f"CALCULATE(AVERAGE(fato_pedidos[dias_transporte]), {ENT})", "0.0", "3. Prazos"),
    ("Dias na etapa",
     "SWITCH(\n\t\t\t\tSELECTEDVALUE(etapa[Ordem]),\n"
     "\t\t\t\t1, [Dias aprovação],\n\t\t\t\t2, [Dias postagem],\n\t\t\t\t3, [Dias transporte]\n\t\t\t)",
     "0.0", "3. Prazos"),
    ("% do tempo na etapa",
     "DIVIDE([Dias na etapa], [Dias aprovação] + [Dias postagem] + [Dias transporte])", "0%", "3. Prazos"),
    ("Nota média", f"CALCULATE(AVERAGE(fato_pedidos[nota_avaliacao]), {ENT})", "0.00", "4. Avaliação"),
    ("% Avaliações ruins",
     "DIVIDE(\n\t\t\t\tCALCULATE(COUNTROWS(fato_pedidos), fato_pedidos[nota_avaliacao] <= 2, " + ENT + "),\n"
     "\t\t\t\tCALCULATE(COUNT(fato_pedidos[nota_avaliacao]), " + ENT + ")\n\t\t\t)", "0%", "4. Avaliação"),
    ("Nota média no prazo", 'CALCULATE([Nota média], fato_pedidos[Situação da entrega] = "No prazo")', "0.00", "4. Avaliação"),
    ("Nota média atrasado", 'CALCULATE([Nota média], fato_pedidos[Situação da entrega] = "Atrasado")', "0.00", "4. Avaliação"),
    ("Texto notas",
     '"Nota média: " & FORMAT([Nota média no prazo], "0.00") & " no prazo · " & FORMAT([Nota média atrasado], "0.00") & " com atraso"',
     None, "4. Avaliação"),
    ("Frete / valor dos produtos",
     "DIVIDE(SUM(fato_pedidos[valor_frete]), SUM(fato_pedidos[valor_produtos]))",
     "0.0%", "5. Frete"),
    ("Texto período",
     '"Olist · " & FORMAT([Pedidos entregues (mil)], "0") & " mil pedidos entregues · jan/2017 a ago/2018"',
     None, "6. Textos"),
    ("Pedidos", "COUNTROWS(fato_pedidos)", "#,0", "1. Volume"),
    ("% Postagem atrasada",
     f"DIVIDE(CALCULATE(SUM(fato_pedidos[postagem_atrasada]), {ENT}), [Pedidos entregues])", "0.0%", "2. Atraso"),
    ("% Atraso categoria (mín. 1000)",
     "-- base do Top 15 de categorias: só categorias com pelo menos 1.000 pedidos entregues\n"
     "\t\t\tIF([Pedidos entregues] >= 1000, [% Atraso])", "0.0%", "2. Atraso"),
    ("Frete médio por pedido", f"CALCULATE(AVERAGE(fato_pedidos[valor_frete]), {ENT})", '"R$" #,0.00', "5. Frete"),
    # cores (formatação condicional por valor de campo)
    ("Cor Atraso",
     f'IF([% Atraso] > CALCULATE([% Atraso], ALLSELECTED(dim_categoria)), "{LARANJA}", "{AZUL}")', None, "7. Cores"),
    ("Cor fundo % postagem", f'IF([% Postagem atrasada] > 0.1, "{LARANJA}", "#FFFFFF")', None, "7. Cores"),
    ("Cor texto % postagem", f'IF([% Postagem atrasada] > 0.1, "#FFFFFF", "{TXT}")', None, "7. Cores"),
    ("Cor fundo % atraso", f'IF([% Atraso] > 0.1, "{LARANJA}", "#FFFFFF")', None, "7. Cores"),
    ("Cor texto % atraso", f'IF([% Atraso] > 0.1, "#FFFFFF", "{TXT}")', None, "7. Cores"),
    ("Cor situação", f'IF(SELECTEDVALUE(fato_pedidos[Situação da entrega]) = "Atrasado", "{LARANJA}", "{AZUL}")', None, "7. Cores"),
    ("Cor postagem", f'IF(SELECTEDVALUE(fato_pedidos[Postagem do vendedor]) = "Postou atrasado", "{LARANJA}", "{AZUL}")', None, "7. Cores"),
    ("Cor etapa", f'IF(SELECTEDVALUE(etapa[Ordem]) = 3, "{LARANJA}", "{AZUL}")', None, "7. Cores"),
    ("Cor UF",
     f'IF(RANKX(FILTER(ALLSELECTED(dim_estado[uf]), [Pedidos entregues] >= 100), [% Atraso], , DESC) <= 2, "{LARANJA}", "{AZUL}")', None, "7. Cores"),
]

med_txt = []
for n, e, fmt, pasta in medidas:
    if "\n" in e:
        med_txt.append(f"\tmeasure '{n}' =\n\t\t\t{e}")
    else:
        med_txt.append(f"\tmeasure '{n}' = {e}")
    if fmt:
        med_txt.append(f"\t\tformatString: {fmt}")
    med_txt.append(f"\t\tdisplayFolder: {pasta}")
    med_txt.append("")

calc_cols = """\tcolumn 'Situação da entrega' = IF(fato_pedidos[atrasado] = 1, "Atrasado", "No prazo")
\t\tdataType: string
\t\tsummarizeBy: none

\tcolumn 'Postagem do vendedor' = IF(fato_pedidos[postagem_atrasada] = 1, "Postou atrasado", "Postou no prazo")
\t\tdataType: string
\t\tsummarizeBy: none

"""
w(os.path.join(SM, "definition", "tables", "fato_pedidos.tmdl"),
  tabela("fato_pedidos", fato_cols, "\n".join(med_txt) + "\n" + calc_cols, hidden_cols=("categoria",)))

w(os.path.join(SM, "definition", "tables", "dim_estado.tmdl"),
  tabela("dim_estado", [("uf", S, None, "none"), ("estado", S, None, "none"),
                        ("regiao", S, None, "none"), ("pais", S, None, "none")],
         extra="""\tcolumn Local = dim_estado[estado] & ", Brasil"
\t\tdataType: string
\t\tdataCategory: Place
\t\tsummarizeBy: none

""", categorias={"estado": "StateOrProvince", "pais": "Country"}))
w(os.path.join(SM, "definition", "tables", "dim_vendedor.tmdl"),
  tabela("dim_vendedor", [("id_vendedor", S, None, "none"), ("cidade_vendedor", S, None, "none"),
                          ("uf_vendedor", S, None, "none"), ("regiao_vendedor", S, None, "none")],
         extra="""\tcolumn Vendedor = LEFT(dim_vendedor[id_vendedor], 6)
\t\tdataType: string
\t\tsummarizeBy: none

"""))
w(os.path.join(SM, "definition", "tables", "dim_categoria.tmdl"),
  tabela("dim_categoria", [("categoria", S, None, "none")]))

w(os.path.join(SM, "definition", "tables", "dim_calendario.tmdl"), """table dim_calendario

\tcolumn Date
\t\tdataType: dateTime
\t\tformatString: dd/mm/yyyy
\t\tisKey
\t\tsummarizeBy: none
\t\tisNameInferred
\t\tsourceColumn: [Date]

\tcolumn Ano = YEAR(dim_calendario[Date])
\t\tdataType: int64
\t\tformatString: 0
\t\tsummarizeBy: none

\tcolumn 'Mês Nº' = MONTH(dim_calendario[Date])
\t\tdataType: int64
\t\tformatString: 0
\t\tsummarizeBy: none

\tcolumn Mês = FORMAT(dim_calendario[Date], "mmm")
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsortByColumn: 'Mês Nº'

\tcolumn AnoMesNum = YEAR(dim_calendario[Date]) * 100 + MONTH(dim_calendario[Date])
\t\tdataType: int64
\t\tformatString: 0
\t\tsummarizeBy: none

\tcolumn 'Mês/Ano' = FORMAT(dim_calendario[Date], "mm/yy")
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsortByColumn: AnoMesNum

\tcolumn 'Início do mês' = DATE(YEAR(dim_calendario[Date]), MONTH(dim_calendario[Date]), 1)
\t\tdataType: dateTime
\t\tformatString: mm/yy
\t\tsummarizeBy: none

\tcolumn 'Dia da semana' = FORMAT(dim_calendario[Date], "dddd")
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsortByColumn: 'Dia semana Nº'

\tcolumn 'Dia semana Nº' = WEEKDAY(dim_calendario[Date], 2)
\t\tdataType: int64
\t\tformatString: 0
\t\tsummarizeBy: none

\tpartition dim_calendario = calculated
\t\tmode: import
\t\tsource = CALENDAR(DATE(2017, 1, 1), DATE(2018, 12, 31))

""")

w(os.path.join(SM, "definition", "tables", "etapa.tmdl"), """table etapa

\tcolumn Etapa
\t\tdataType: string
\t\tsummarizeBy: none
\t\tisNameInferred
\t\tsourceColumn: [Etapa]
\t\tsortByColumn: Ordem

\tcolumn Ordem
\t\tdataType: int64
\t\tformatString: 0
\t\tsummarizeBy: none
\t\tisNameInferred
\t\tsourceColumn: [Ordem]

\tpartition etapa = calculated
\t\tmode: import
\t\tsource = DATATABLE("Etapa", STRING, "Ordem", INTEGER, {{"Aprovação", 1}, {"Postagem (vendedor)", 2}, {"Transporte", 3}})

""")

w(os.path.join(SM, "definition", "relationships.tmdl"), """relationship rel_data_compra
\tfromColumn: fato_pedidos.data_compra
\ttoColumn: dim_calendario.Date

relationship rel_data_entrega
\tisActive: false
\tfromColumn: fato_pedidos.data_entrega
\ttoColumn: dim_calendario.Date

relationship rel_estado
\tfromColumn: fato_pedidos.uf_cliente
\ttoColumn: dim_estado.uf

relationship rel_vendedor
\tfromColumn: fato_pedidos.id_vendedor
\ttoColumn: dim_vendedor.id_vendedor

relationship rel_categoria
\tfromColumn: fato_pedidos.categoria
\ttoColumn: dim_categoria.categoria
""")

# =====================================================================
# RELATÓRIO (PBIR)
# =====================================================================
SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
V_SCH = f"{SCH}/visualContainer/2.4.0/schema.json"

wj(os.path.join(RP, "definition.pbir"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {"byPath": {"path": f"../{NOME}.SemanticModel"}},
})
wj(os.path.join(RP, "definition", "version.json"), {
    "$schema": f"{SCH}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})

shutil.copy(os.path.join(PROJ, "tema_olist.json"),
            os.path.join(os.makedirs(os.path.join(RP, "StaticResources", "RegisteredResources"), exist_ok=True)
                         or os.path.join(RP, "StaticResources", "RegisteredResources"), "tema_olist.json"))

wj(os.path.join(RP, "definition", "report.json"), {
    "$schema": f"{SCH}/report/3.0.0/schema.json",
    "themeCollection": {
        "customTheme": {"name": "tema_olist.json",
                        "reportVersionAtImport": {"visual": "2.4.0", "report": "3.0.0", "page": "2.0.0"},
                        "type": "RegisteredResources"}
    },
    "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                          "items": [{"name": "tema_olist.json", "path": "tema_olist.json", "type": "CustomTheme"}]}],
    "settings": {"useStylableVisualContainerHeader": True, "useEnhancedTooltips": True,
                 "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True},
})

PAGINAS = [  # (id, nome exibido, altura)
    ("visao_geral", "Visão geral", 740),
    ("rotas_regioes", "Rotas e regiões", 740),
    ("vendedores_categorias", "Vendedores e categorias", 860),
]
PAGE = PAGINAS[0][0]
wj(os.path.join(RP, "definition", "pages", "pages.json"), {
    "$schema": f"{SCH}/pagesMetadata/1.0.0/schema.json",
    "pageOrder": [p[0] for p in PAGINAS], "activePageName": PAGE})


# ---------- helpers de expressão ----------
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def s(v):  # string literal
    return lit("'" + v.replace("'", "''") + "'")


def b(v):
    return lit("true" if v else "false")


def n(v):
    return lit(f"{v}D")


def cor(hexv):
    return {"solid": {"color": s(hexv)}}


def cor_medida(medida, ent="fato_pedidos"):
    return {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": medida}}}}}


def col(ent, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}


def med(ent, prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}


def proj(field, display=None):
    k = "Column" if "Column" in field else "Measure"
    ent = field[k]["Expression"]["SourceRef"]["Entity"]
    prop = field[k]["Property"]
    p = {"field": field, "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p


for pid, pnome, palt in PAGINAS:
    wj(os.path.join(RP, "definition", "pages", pid, "page.json"), {
        "$schema": f"{SCH}/page/2.0.0/schema.json",
        "name": pid,
        "displayName": pnome,
        "displayOption": "FitToPage",
        "height": palt,
        "width": 1280,
        "objects": {
            "background": [{"properties": {"color": cor(FUNDO), "transparency": n(0)}}],
            "outspace": [{"properties": {"color": cor(FUNDO)}}],
        },
    })


def container(titulo=None, subtitulo=None, subtitulo_medida=None, fundo=True):
    o = {
        "background": [{"properties": {"show": b(fundo), "color": cor("#FFFFFF"), "transparency": n(0)}}],
        "border": [{"properties": {"show": b(fundo), "color": cor(BORDA), "radius": n(8), "width": n(1)}}],
        "dropShadow": [{"properties": {"show": b(False)}}],
        "padding": [{"properties": {"top": n(12), "bottom": n(10), "left": n(16), "right": n(16)}}],
        "visualHeader": [{"properties": {"show": b(False)}}],
    }
    if titulo:
        o["title"] = [{"properties": {"show": b(True), "text": s(titulo), "fontColor": cor(TXT), "fontSize": n(12),
                                      "bold": b(True), "fontFamily": s("'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif")}}]
    else:
        o["title"] = [{"properties": {"show": b(False)}}]
    if subtitulo or subtitulo_medida:
        txt = s(subtitulo) if subtitulo else {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "fato_pedidos"}}, "Property": subtitulo_medida}}}
        o["subTitle"] = [{"properties": {"show": b(True), "text": txt, "fontColor": cor(TXT2), "fontSize": n(9)}}]
    return o


visuais = []


def add(nome, x, y, wd, h, visual, z=None):
    filtros = visual.pop("filterConfig", None)  # filtros ficam no contêiner, não dentro do visual
    cont = {
        "$schema": V_SCH,
        "name": nome,
        "position": {"x": x, "y": y, "z": z if z is not None else len(visuais) * 1000,
                     "width": wd, "height": h, "tabOrder": len(visuais) * 1000},
        "visual": visual,
    }
    if filtros:
        cont["filterConfig"] = filtros
    visuais.append((PAGE, nome, cont))


def textbox(runs_por_paragrafo):
    pars = []
    for runs in runs_por_paragrafo:
        pars.append({"textRuns": [{"value": t, "textStyle": st} for t, st in runs]})
    return {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": pars}}]},
        "visualContainerObjects": {
            "background": [{"properties": {"show": b(False)}}],
            "border": [{"properties": {"show": b(False)}}],
            "visualHeader": [{"properties": {"show": b(False)}}],
            "padding": [{"properties": {"top": n(0), "bottom": n(0), "left": n(0), "right": n(0)}}],
        },
        "drillFilterOtherVisuals": True,
    }


def cartao():
    """Fundo branco, borda cinza e cantos de 8px, sem título (para segmentações)."""
    o = container()
    o["padding"] = [{"properties": {"top": n(4), "bottom": n(4), "left": n(10), "right": n(10)}}]
    return o


def segmentacao(campo, grupo, rotulo):
    return {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [{**proj(campo, rotulo), "active": True}]}}},
        "objects": {
            "data": [{"properties": {"mode": s("Dropdown")}}],
            "header": [{"properties": {"show": b(True), "fontColor": cor(TXT2), "textSize": n(9),
                                       "fontFamily": s("Segoe UI")}}],
            "items": [{"properties": {"fontColor": cor(TXT), "textSize": n(9)}}],
            "selection": [{"properties": {"selectAllCheckboxEnabled": b(True), "singleSelect": b(False)}}],
        },
        "visualContainerObjects": cartao(),
        "syncGroup": {"groupName": grupo, "fieldChanges": True, "filterChanges": True},
        "drillFilterOtherVisuals": True,
    }


def cabecalho(subtitulo, altura):
    add("titulo", 32, 14, 640, 40, textbox([[("Logística de e-commerce: onde a entrega falha",
                                             {"fontFamily": "Segoe UI Semibold", "fontSize": "22pt", "color": TXT})]]))
    add("subtitulo", 32, 52, 640, 26, textbox([[(subtitulo, {"fontFamily": FONTE, "fontSize": "12pt", "color": TXT2})]]))
    add("navegacao", 692, 4, 550, 25, {
        "visualType": "pageNavigator",
        "objects": {
            "fill": [{"properties": {"show": b(True), "fillColor": cor("#FFFFFF"), "transparency": n(0)}},
                     {"properties": {"fillColor": cor(AZUL)}, "selector": {"id": "selected"}}],
            "text": [{"properties": {"fontColor": cor(TXT2), "fontSize": n(10), "fontFamily": s("Segoe UI")}},
                     {"properties": {"fontColor": cor("#FFFFFF"), "bold": b(True)}, "selector": {"id": "selected"}}],
            "outline": [{"properties": {"show": b(True), "lineColor": cor(BORDA), "roundEdge": n(6)}},
                        {"properties": {"lineColor": cor(AZUL)}, "selector": {"id": "selected"}}],
        },
        "visualContainerObjects": {
            "background": [{"properties": {"show": b(False)}}],
            "border": [{"properties": {"show": b(False)}}],
            "visualHeader": [{"properties": {"show": b(False)}}],
            "title": [{"properties": {"show": b(False)}}],
        },
        "drillFilterOtherVisuals": True,
    })
    for i, (nome, campo, grupo, rotulo) in enumerate([
        ("seg_ano", col("dim_calendario", "Ano"), "sync_ano", "Ano"),
        ("seg_regiao", col("dim_estado", "regiao"), "sync_regiao", "Região"),
        ("seg_categoria", col("dim_categoria", "categoria"), "sync_categoria", "Categoria"),
    ]):
        add(nome, 692 + i * 188, 33, 174, 51, segmentacao(campo, grupo, rotulo))
    add("rodape", 840, altura - 23, 410, 20, textbox([[("Fonte: dados públicos Olist (Kaggle) · CC BY-NC-SA 4.0",
                                                       {"fontFamily": FONTE, "fontSize": "8pt", "color": CINZA})]]))


# =====================================================================
# PÁGINA 1 — Visão geral
# =====================================================================
cabecalho("Olist · 96 mil pedidos entregues · jan/2017 a ago/2018", 740)

# ---------- KPIs ----------
kpis = [
    ("kpi_entregues", "Pedidos entregues", "Pedidos entregues (mil)"),
    ("kpi_atraso", "Entregas com atraso", "% Atraso"),
    ("kpi_prazo_real", "Prazo médio real", "Prazo médio real"),
    ("kpi_prazo_prom", "Prazo médio prometido", "Prazo médio prometido"),
    ("kpi_nota", "Nota média", "Nota média"),
    ("kpi_frete", "Frete / valor dos produtos", "Frete / valor dos produtos"),
]
KX, KW, KG, KY, KH = 38, 190, 12.8, 86, 80
for i, (nome, rot, medida) in enumerate(kpis):
    vc = container()
    vc["title"] = [{"properties": {"show": b(True), "text": s(rot), "fontColor": cor(TXT2), "fontSize": n(10),
                                   "bold": b(False), "fontFamily": s("Segoe UI")}}]
    if nome == "kpi_atraso":
        vc["border"] = [{"properties": {"show": b(True), "color": cor(LARANJA), "radius": n(8), "width": n(1)}}]
    add(nome, round(KX + i * (KW + KG), 1), KY, KW, KH, {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [proj(med("fato_pedidos", medida))]}}},
        "objects": {
            "labels": [{"properties": {"color": cor(TXT), "fontSize": n(24), "fontFamily": s("Segoe UI Semibold"),
                                       "labelDisplayUnits": n(1)}}],
            "categoryLabels": [{"properties": {"show": b(False)}}],
        },
        "visualContainerObjects": vc,
        "drillFilterOtherVisuals": True,
    })

TODOS = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}

# ---------- Linha: % atraso por mês ----------
add("linha_atraso_mes", 38, 178, 582, 206, {
    "visualType": "lineChart",
    "query": {
        "queryState": {
            "Category": {"projections": [{**proj(col("dim_calendario", "Início do mês"), "Mês da compra"), "active": True}]},
            "Y": {"projections": [proj(med("fato_pedidos", "% Atraso"))]},
        },
        "sortDefinition": {"sort": [{"field": col("dim_calendario", "Início do mês"), "direction": "Ascending"}],
                           "isDefaultSort": True},
    },
    "objects": {
        "lineStyles": [{"properties": {"strokeWidth": n(2), "showMarker": b(True), "markerSize": n(4)}}],
        "dataPoint": [{"properties": {"fill": cor(AZUL)}, "selector": {"metadata": "fato_pedidos.% Atraso"}}],
        "categoryAxis": [{"properties": {"showAxisTitle": b(False), "fontSize": n(9), "labelColor": cor(TXT2),
                                         "axisType": s("Scalar"), "gridlineShow": b(False)}}],
        "valueAxis": [{"properties": {"showAxisTitle": b(False), "fontSize": n(9), "labelColor": cor(TXT2),
                                      "start": n(0), "gridlineShow": b(True), "gridlineColor": cor("#ECEDF0"),
                                      "labelDisplayUnits": n(1), "labelPrecision": n(0)}}],
        "legend": [{"properties": {"show": b(False)}}],
        "labels": [{"properties": {"show": b(False)}}],
    },
    "visualContainerObjects": container("% de entregas atrasadas por mês de compra",
                                        "Picos na Black Friday/17 e em fev–mar/18"),
    "drillFilterOtherVisuals": True,
})

# ---------- Barras: avaliações ruins no prazo x atrasado ----------
add("barras_avaliacoes", 633, 178, 609, 206, {
    "visualType": "clusteredBarChart",
    "query": {
        "queryState": {
            "Category": {"projections": [{**proj(col("fato_pedidos", "Situação da entrega")), "active": True}]},
            "Y": {"projections": [proj(med("fato_pedidos", "% Avaliações ruins"))]},
        },
        "sortDefinition": {"sort": [{"field": col("fato_pedidos", "Situação da entrega"), "direction": "Ascending"}]},
    },
    "objects": {
        "dataPoint": [{"properties": {"fill": cor_medida("Cor situação")}, "selector": TODOS}],
        "categoryAxis": [{"properties": {"showAxisTitle": b(False), "fontSize": n(10), "labelColor": cor(TXT2),
                                         "innerPadding": n(45)}}],
        "valueAxis": [{"properties": {"show": b(False), "gridlineShow": b(False), "start": n(0)}}],
        "labels": [{"properties": {"show": b(True), "fontSize": n(12), "color": cor(TXT), "labelPosition": s("OutsideEnd")}}],
        "legend": [{"properties": {"show": b(False)}}],
    },
    "visualContainerObjects": container("Avaliações ruins (nota 1 ou 2): no prazo × atrasado",
                                        subtitulo_medida="Texto notas"),
    "drillFilterOtherVisuals": True,
})

# ---------- Barras: % atraso por UF (top 10) ----------
add("barras_uf", 38, 396, 392, 318, {
    "visualType": "clusteredBarChart",
    "query": {
        "queryState": {
            "Category": {"projections": [{**proj(col("dim_estado", "uf")), "active": True}]},
            "Y": {"projections": [proj(med("fato_pedidos", "% Atraso top 10 UF"), "% atraso")]},
            "Tooltips": {"projections": [proj(med("fato_pedidos", "Pedidos entregues"))]},
        },
        "sortDefinition": {"sort": [{"field": med("fato_pedidos", "% Atraso top 10 UF"), "direction": "Descending"}]},
    },
    "objects": {
        "dataPoint": [{"properties": {"fill": cor_medida("Cor UF")}, "selector": TODOS}],
        "categoryAxis": [{"properties": {"showAxisTitle": b(False), "fontSize": n(8), "labelColor": cor(TXT2),
                                         "innerPadding": n(18), "minCategoryWidth": n(12)}}],
        "valueAxis": [{"properties": {"show": b(False), "gridlineShow": b(False), "start": n(0)}}],
        "labels": [{"properties": {"show": b(True), "fontSize": n(9), "color": cor(TXT), "labelPrecision": n(1)}}],
        "legend": [{"properties": {"show": b(False)}}],
    },
    "visualContainerObjects": container("% de atraso por estado (maiores)", "Estado do cliente (mín. 100 pedidos) · São Paulo: 4,5%"),
    "drillFilterOtherVisuals": True,
})

# ---------- Barras: onde o tempo vai ----------
add("barras_etapas", 444, 396, 392, 318, {
    "visualType": "clusteredBarChart",
    "query": {
        "queryState": {
            "Category": {"projections": [{**proj(col("etapa", "Etapa")), "active": True}]},
            "Y": {"projections": [proj(med("fato_pedidos", "Dias na etapa"), "Dias (média)")]},
            "Tooltips": {"projections": [proj(med("fato_pedidos", "% do tempo na etapa"))]},
        },
        "sortDefinition": {"sort": [{"field": col("etapa", "Etapa"), "direction": "Ascending"}]},
    },
    "objects": {
        "dataPoint": [{"properties": {"fill": cor_medida("Cor etapa")}, "selector": TODOS}],
        "categoryAxis": [{"properties": {"showAxisTitle": b(False), "fontSize": n(10), "labelColor": cor(TXT2),
                                         "innerPadding": n(40), "maxMarginFactor": n(45)}}],
        "valueAxis": [{"properties": {"show": b(False), "gridlineShow": b(False), "start": n(0)}}],
        "labels": [{"properties": {"show": b(True), "fontSize": n(10), "color": cor(TXT), "labelPrecision": n(1)}}],
        "legend": [{"properties": {"show": b(False)}}],
    },
    "visualContainerObjects": container("Onde o tempo vai (média em dias)",
                                        "Transporte = 74% do prazo · postagem do vendedor = 22%"),
    "drillFilterOtherVisuals": True,
})

# ---------- Colunas: chance de atrasar ----------
add("colunas_postagem", 850, 396, 392, 318, {
    "visualType": "clusteredColumnChart",
    "query": {
        "queryState": {
            "Category": {"projections": [{**proj(col("fato_pedidos", "Postagem do vendedor")), "active": True}]},
            "Y": {"projections": [proj(med("fato_pedidos", "% Atraso"), "Chance de atraso")]},
        },
        "sortDefinition": {"sort": [{"field": col("fato_pedidos", "Postagem do vendedor"), "direction": "Descending"}]},
    },
    "objects": {
        "dataPoint": [{"properties": {"fill": cor_medida("Cor postagem")}, "selector": TODOS}],
        "categoryAxis": [{"properties": {"showAxisTitle": b(False), "fontSize": n(10), "labelColor": cor(TXT2),
                                         "innerPadding": n(40)}}],
        "valueAxis": [{"properties": {"show": b(False), "gridlineShow": b(False), "start": n(0)}}],
        "labels": [{"properties": {"show": b(True), "fontSize": n(13), "color": cor(TXT), "labelPrecision": n(1),
                                   "fontFamily": s("Segoe UI Semibold")}}],
        "legend": [{"properties": {"show": b(False)}}],
    },
    "visualContainerObjects": container("Chance de atrasar a entrega", "Conforme o vendedor postou no prazo-limite ou não"),
    "drillFilterOtherVisuals": True,
})

# ---------- helpers de filtro de visual ----------
def src(alias, prop, kind="Column"):
    return {kind: {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}}


def filtro_excluir(nome, ent, coluna, valores):
    return {
        "name": nome, "field": col(ent, coluna), "type": "Categorical", "howCreated": "User",
        "filter": {"Version": 2, "From": [{"Name": "t", "Entity": ent, "Type": 0}],
                   "Where": [{"Condition": {"Not": {"Expression": {"In": {
                       "Expressions": [src("t", coluna)],
                       "Values": [[{"Literal": {"Value": "'" + v + "'"}}] for v in valores]}}}}}]},
    }


def filtro_topn(nome, ent, coluna, medida, top):
    return {
        "name": nome, "field": col(ent, coluna), "type": "TopN", "howCreated": "User",
        "filter": {"Version": 2,
                   "From": [{"Name": "subquery", "Type": 2, "Expression": {"Subquery": {"Query": {
                       "Version": 2,
                       "From": [{"Name": "d", "Entity": ent, "Type": 0}, {"Name": "f", "Entity": "fato_pedidos", "Type": 0}],
                       "Select": [{**src("d", coluna), "Name": "field"}],
                       "OrderBy": [{"Direction": 2, "Expression": src("f", medida, "Measure")}],
                       "Top": top}}}},
                       {"Name": "d", "Entity": ent, "Type": 0}],
                   "Where": [{"Condition": {"In": {"Expressions": [src("d", coluna)],
                                                   "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
    }


def filtro_medida_min(nome, medida, minimo):
    return {
        "name": nome, "field": med("fato_pedidos", medida), "type": "Advanced", "howCreated": "User",
        "filter": {"Version": 2, "From": [{"Name": "f", "Entity": "fato_pedidos", "Type": 0}],
                   "Where": [{"Condition": {"Comparison": {"ComparisonKind": 2,
                                                           "Left": src("f", medida, "Measure"),
                                                           "Right": {"Literal": {"Value": f"{minimo}L"}}}}}]},
    }


EIXO_OFF = [{"properties": {"show": b(False), "gridlineShow": b(False), "start": n(0)}}]

# =====================================================================
# PÁGINA 2 — Rotas e regiões
# =====================================================================
PAGE = "rotas_regioes"
cabecalho("Rotas e regiões · como a distância afeta a entrega", 740)

add("mapa_atraso", 38, 96, 590, 618, {
    "visualType": "filledMap",
    "query": {"queryState": {
        "Category": {"projections": [{**proj(col("dim_estado", "Local"), "Estado"), "active": True}]},
        "Tooltips": {"projections": [proj(med("fato_pedidos", "% Atraso")),
                                     proj(med("fato_pedidos", "Prazo médio real")),
                                     proj(med("fato_pedidos", "Pedidos entregues"))]},
    }},
    "objects": {
        # cor do preenchimento por gradiente de % Atraso (formatação condicional "fx")
        "dataPoint": [{"properties": {"fill": {"solid": {"color": {"expr": {"FillRule": {
            "Input": med("fato_pedidos", "% Atraso"),
            "FillRule": {"linearGradient2": {
                "min": {"color": {"Literal": {"Value": "'#FCE3D8'"}}},
                "max": {"color": {"Literal": {"Value": f"'{LARANJA}'"}}},
                "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
            "selector": TODOS}],
        "mapStyles": [{"properties": {"mapTheme": s("canvasLight")}}],
        "legend": [{"properties": {"show": b(False)}}],
    },
    "visualContainerObjects": container("Atraso se concentra no Norte e Nordeste",
                                        "% de entregas atrasadas · Nordeste 12,8% e Norte 8,6% contra 6,1% no Sudeste"),
    "drillFilterOtherVisuals": True,
})

add("matriz_distancia", 642, 96, 600, 282, {
    "visualType": "pivotTable",
    "query": {
        "queryState": {
            "Rows": {"projections": [{**proj(col("fato_pedidos", "faixa_distancia"), "Distância vendedor → cliente"),
                                      "active": True}]},
            "Values": {"projections": [proj(med("fato_pedidos", "Prazo médio real"), "Prazo médio real"),
                                       proj(med("fato_pedidos", "% Atraso"), "% Atraso"),
                                       proj(med("fato_pedidos", "Frete médio por pedido"), "Frete médio")]},
        },
        "sortDefinition": {"sort": [{"field": col("fato_pedidos", "faixa_distancia"), "direction": "Ascending"}]},
    },
    "objects": {
        "columnFormatting": [{"properties": {"dataBars": {
            "positiveColor": cor(LARANJA), "negativeColor": cor(LARANJA), "axisColor": cor("#FFFFFF"),
            "reverseDirection": b(False), "hideText": b(False)}},
            "selector": {"metadata": "fato_pedidos.% Atraso"}}],
        "columnHeaders": [{"properties": {"fontColor": cor(TXT2), "fontSize": n(10), "backColor": cor("#FFFFFF"),
                                          "wordWrap": b(True)}}],
        "rowHeaders": [{"properties": {"fontColor": cor(TXT), "fontSize": n(10)}}],
        "values": [{"properties": {"fontColor": cor(TXT), "fontSize": n(10), "backColorSecondary": cor("#FFFFFF")}}],
        "total": [{"properties": {"fontColor": cor(TXT), "fontSize": n(10), "backColor": cor(FUNDO)}}],
        "grid": [{"properties": {"rowPadding": n(6), "gridHorizontal": b(True), "gridHorizontalColor": cor("#ECEDF0"),
                                 "gridVertical": b(False), "outlineColor": cor(BORDA)}}],
    },
    "visualContainerObjects": container("Distância aumenta prazo, frete e atraso",
                                        "Acima de 2.000 km: 21,2 dias e 12,1% de atraso, contra 6,5 dias e 4,5% até 100 km"),
    "filterConfig": {"filters": [filtro_excluir("excluir_sem_info", "fato_pedidos", "faixa_distancia", ["Sem informação"])]},
    "drillFilterOtherVisuals": True,
})

add("dispersao_uf", 642, 392, 600, 322, {
    "visualType": "scatterChart",
    "query": {"queryState": {
        "Category": {"projections": [{**proj(col("dim_estado", "uf"), "UF"), "active": True}]},
        "X": {"projections": [proj(med("fato_pedidos", "Frete médio por pedido"), "Frete médio por pedido")]},
        "Y": {"projections": [proj(med("fato_pedidos", "Prazo médio real"), "Prazo médio real")]},
        "Size": {"projections": [proj(med("fato_pedidos", "Pedidos entregues"), "Pedidos entregues")]},
    }},
    "objects": {
        "dataPoint": [{"properties": {"fill": cor(AZUL), "fillTransparency": n(25)}}],
        "categoryLabels": [{"properties": {"show": b(True), "color": cor(TXT2), "fontSize": n(8)}}],
        "categoryAxis": [{"properties": {"showAxisTitle": b(True), "titleText": s("Frete médio por pedido (R$)"),
                                         "titleFontSize": n(9), "titleColor": cor(TXT2), "fontSize": n(9),
                                         "labelColor": cor(TXT2), "gridlineShow": b(False)}}],
        "valueAxis": [{"properties": {"showAxisTitle": b(True), "titleText": s("Prazo médio real (dias)"),
                                      "titleFontSize": n(9), "titleColor": cor(TXT2), "fontSize": n(9),
                                      "labelColor": cor(TXT2), "gridlineShow": b(True), "gridlineColor": cor("#ECEDF0")}}],
        "legend": [{"properties": {"show": b(False)}}],
        "bubbles": [{"properties": {"bubbleSize": n(-10)}}],
    },
    "visualContainerObjects": container("Estados distantes têm frete e prazo mais altos",
                                        "Cada bolha é um estado, do tamanho do volume · SP: R$ 17 e 8,7 dias; RR: R$ 49 e 29,9 dias"),
    "drillFilterOtherVisuals": True,
})

# =====================================================================
# PÁGINA 3 — Vendedores e categorias
# =====================================================================
PAGE = "vendedores_categorias"
cabecalho("Vendedores e categorias · onde está o gargalo", 860)

FUNDO_COND = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}
add("tabela_vendedores", 38, 96, 1204, 330, {
    "visualType": "tableEx",
    "query": {
        "queryState": {"Values": {"projections": [
            proj(col("dim_vendedor", "Vendedor"), "Vendedor"),
            proj(col("dim_vendedor", "cidade_vendedor"), "Cidade"),
            proj(col("dim_vendedor", "uf_vendedor"), "UF"),
            proj(med("fato_pedidos", "Pedidos"), "Pedidos"),
            proj(med("fato_pedidos", "% Postagem atrasada"), "% Postagem atrasada"),
            proj(med("fato_pedidos", "% Atraso"), "% Atraso"),
            proj(med("fato_pedidos", "Nota média"), "Nota média"),
        ]}},
        "sortDefinition": {"sort": [{"field": med("fato_pedidos", "% Postagem atrasada"), "direction": "Descending"}]},
    },
    "objects": {
        "values": [
            {"properties": {"fontColor": cor(TXT), "fontSize": n(10), "backColorSecondary": cor("#FFFFFF")}},
            {"properties": {"backColor": cor_medida("Cor fundo % postagem"), "fontColor": cor_medida("Cor texto % postagem")},
             "selector": {**FUNDO_COND, "metadata": "fato_pedidos.% Postagem atrasada"}},
            {"properties": {"backColor": cor_medida("Cor fundo % atraso"), "fontColor": cor_medida("Cor texto % atraso")},
             "selector": {**FUNDO_COND, "metadata": "fato_pedidos.% Atraso"}},
        ],
        "columnHeaders": [{"properties": {"fontColor": cor(TXT2), "fontSize": n(10), "backColor": cor("#FFFFFF")}}],
        "total": [{"properties": {"totals": b(False)}}],
        "grid": [{"properties": {"rowPadding": n(2), "gridHorizontal": b(True), "gridHorizontalColor": cor("#ECEDF0"),
                                 "gridVertical": b(False), "outlineColor": cor(BORDA)}}],
    },
    "visualContainerObjects": container("Vendedores com mais atrasos na postagem",
                                        "Os 20 maiores vendedores em pedidos · laranja = acima de 10% (média geral de postagem atrasada: 8,9%)"),
    "filterConfig": {"filters": [filtro_topn("top20_vendedores", "dim_vendedor", "Vendedor", "Pedidos", 20)]},
    "drillFilterOtherVisuals": True,
})

add("barras_categorias", 38, 440, 1204, 396, {
    "visualType": "clusteredBarChart",
    "query": {
        "queryState": {
            "Category": {"projections": [{**proj(col("dim_categoria", "categoria"), "Categoria"), "active": True}]},
            "Y": {"projections": [proj(med("fato_pedidos", "% Atraso"), "% Atraso")]},
            "Tooltips": {"projections": [proj(med("fato_pedidos", "Pedidos entregues"))]},
        },
        "sortDefinition": {"sort": [{"field": med("fato_pedidos", "% Atraso"), "direction": "Descending"}]},
    },
    "objects": {
        "dataPoint": [{"properties": {"fill": cor_medida("Cor Atraso")}, "selector": TODOS}],
        "categoryAxis": [{"properties": {"showAxisTitle": b(False), "fontSize": n(9), "labelColor": cor(TXT2),
                                         "innerPadding": n(20), "maxMarginFactor": n(30)}}],
        "valueAxis": EIXO_OFF,
        "labels": [{"properties": {"show": b(True), "fontSize": n(9), "color": cor(TXT), "labelPrecision": n(1)}}],
        "legend": [{"properties": {"show": b(False)}}],
    },
    "visualContainerObjects": container("Categorias com maior taxa de atraso",
                                        "Categorias com 1.000+ pedidos · variação pequena (6,5% a 8,1%): o gargalo está na rota e no vendedor, não no produto"),
    "filterConfig": {"filters": [
        filtro_medida_min("min_1000_pedidos", "Pedidos entregues", 1000),
        filtro_topn("top15_categorias", "dim_categoria", "categoria", "% Atraso categoria (mín. 1000)", 15),
    ]},
    "drillFilterOtherVisuals": True,
})

for pagina, nome, v in visuais:
    wj(os.path.join(RP, "definition", "pages", pagina, "visuals", nome, "visual.json"), v)

w(os.path.join(PROJ, ".gitignore"), "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
print("OK:", len(visuais), "visuais")
