import pandas as pd, numpy as np

o = pd.read_csv('olist_orders_dataset.csv', parse_dates=['order_purchase_timestamp','order_approved_at',
    'order_delivered_carrier_date','order_delivered_customer_date','order_estimated_delivery_date'])
it = pd.read_csv('olist_order_items_dataset.csv', parse_dates=['shipping_limit_date'])
cu = pd.read_csv('olist_customers_dataset.csv', dtype={'customer_zip_code_prefix': str})
se = pd.read_csv('olist_sellers_dataset.csv', dtype={'seller_zip_code_prefix': str})
rv = pd.read_csv('olist_order_reviews_dataset.csv', parse_dates=['review_answer_timestamp'])
pr = pd.read_csv('olist_products_dataset.csv')
geo = pd.read_csv('olist_geolocation_dataset.csv', dtype={'geolocation_zip_code_prefix': str})
cu['customer_zip_code_prefix'] = cu.customer_zip_code_prefix.str.zfill(5)
se['seller_zip_code_prefix'] = se.seller_zip_code_prefix.str.zfill(5)
geo['geolocation_zip_code_prefix'] = geo.geolocation_zip_code_prefix.str.zfill(5)

# Período completo de dados: jan/2017 a ago/2018
o = o[(o.order_purchase_timestamp >= '2017-01-01') & (o.order_purchase_timestamp < '2018-09-01')]

# ---------- Categoria em português legível ----------
def nome_cat(c):
    if pd.isna(c): return 'Sem categoria'
    fixos = {'cama_mesa_banho':'Cama, mesa e banho','beleza_saude':'Beleza e saúde','esporte_lazer':'Esporte e lazer',
        'informatica_acessorios':'Informática e acessórios','moveis_decoracao':'Móveis e decoração',
        'relogios_presentes':'Relógios e presentes','ferramentas_jardim':'Ferramentas e jardim',
        'malas_acessorios':'Malas e acessórios','consoles_games':'Consoles e games','cool_stuff':'Variedades (cool stuff)',
        'construcao_ferramentas_construcao':'Construção e ferramentas','fashion_bolsas_e_acessorios':'Moda: bolsas e acessórios'}
    if c in fixos: return fixos[c]
    txt = c.replace('_', ' ').strip().lower()
    acentos = {'moveis':'móveis','bebes':'bebês','eletronicos':'eletrônicos','saude':'saúde','relogios':'relógios',
        'decoracao':'decoração','informatica':'informática','acessorios':'acessórios','domesticas':'domésticas',
        'eletrodomesticos':'eletrodomésticos','construcao':'construção','musica':'música','audio':'áudio',
        'climatizacao':'climatização','eletroportateis':'eletroportáteis','iluminacao':'iluminação','seguranca':'segurança',
        'alimentos':'alimentos','bebidas':'bebidas','fotos':'fotos','instrumentos':'instrumentos',
        'servicos':'serviços','industria':'indústria','comercio':'comércio','agro':'agro','cds':'CDs','dvds':'DVDs',
        'pcs':'PCs','portateis':'portáteis','cozinha':'cozinha','jardim':'jardim','artes':'artes','livros':'livros',
        'tecnicos':'técnicos','importados':'importados','interesse':'interesse','geral':'geral','sinalizacao':'sinalização',
        'construcao':'construção','casa':'casa','conforto':'conforto','colchao':'colchão','estofados':'estofados',
        'quarto':'quarto','sala':'sala','jantar':'jantar','escritorio':'escritório','telefonia':'telefonia','fixa':'fixa',
        'artesanato':'artesanato','papelaria':'papelaria','perfumaria':'perfumaria','fraldas':'fraldas','higiene':'higiene',
        'roupa':'roupa','calcados':'calçados','esportes':'esportes','esporte':'esporte','lazer':'lazer','tablets':'tablets',
        'impressao':'impressão','imagem':'imagem','festas':'festas','natal':'natal','flores':'flores','pet':'pet'}
    txt = ' '.join(acentos.get(w, w) for w in txt.split()).replace('cama, mesa', 'cama, mesa')
    return txt[0].upper() + txt[1:]
pr['categoria'] = pr.product_category_name.map(nome_cat)

# ---------- Itens: agregação por pedido ----------
it = it.merge(pr[['product_id','categoria','product_weight_g']], on='product_id', how='left')
it = it.sort_values(['order_id','price'], ascending=[True, False])
agg = it.groupby('order_id').agg(
    qtd_itens=('order_item_id','count'),
    valor_produtos=('price','sum'),
    valor_frete=('freight_value','sum'),
    peso_total_kg=('product_weight_g', lambda s: s.sum()/1000),
    qtd_vendedores=('seller_id','nunique'),
    prazo_limite_postagem=('shipping_limit_date','max'),
).reset_index()
principal = it.groupby('order_id').first()[['seller_id','categoria']].reset_index()  # item de maior valor
agg = agg.merge(principal, on='order_id')

# ---------- Review: a mais recente por pedido ----------
rv = rv.sort_values('review_answer_timestamp').groupby('order_id').last()[['review_score']].reset_index()

# ---------- Distância vendedor x cliente (centroide do CEP) ----------
g = geo[(geo.geolocation_lat.between(-34, 6)) & (geo.geolocation_lng.between(-74, -34))]
g = g.groupby('geolocation_zip_code_prefix')[['geolocation_lat','geolocation_lng']].mean()

f = (o.merge(cu[['customer_id','customer_zip_code_prefix','customer_city','customer_state']], on='customer_id')
      .merge(agg, on='order_id', how='inner')
      .merge(se[['seller_id','seller_zip_code_prefix','seller_state']], on='seller_id', how='left')
      .merge(rv, on='order_id', how='left'))

def coords(prefix):
    return g.reindex(prefix)
cc = coords(f.customer_zip_code_prefix); sc = coords(f.seller_zip_code_prefix)
lat1, lon1, lat2, lon2 = map(np.radians, [cc.geolocation_lat.values, cc.geolocation_lng.values,
                                          sc.geolocation_lat.values, sc.geolocation_lng.values])
a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
f['distancia_km'] = np.round(6371*2*np.arcsin(np.sqrt(a)), 0)

# ---------- Métricas de prazo (em dias) ----------
d = lambda a, b: (f[b] - f[a]).dt.total_seconds() / 86400
f['dias_aprovacao']   = d('order_purchase_timestamp','order_approved_at').round(2)
f['dias_postagem']    = d('order_approved_at','order_delivered_carrier_date').round(2)
f['dias_transporte']  = d('order_delivered_carrier_date','order_delivered_customer_date').round(2)
f['dias_entrega']     = d('order_purchase_timestamp','order_delivered_customer_date').round(2)
f['dias_prometidos']  = (f.order_estimated_delivery_date.dt.normalize() - f.order_purchase_timestamp.dt.normalize()).dt.days
atraso = (f.order_delivered_customer_date.dt.normalize() - f.order_estimated_delivery_date.dt.normalize()).dt.days
f['dias_atraso'] = atraso.clip(lower=0)
entregue = f.order_status.eq('delivered') & f.order_delivered_customer_date.notna()
f['entregue'] = np.where(entregue, 1, 0)
f['atrasado'] = np.where(entregue & (atraso > 0), 1, 0)
f['postagem_atrasada'] = np.where(f.order_delivered_carrier_date.notna() &
                                  (f.order_delivered_carrier_date > f.prazo_limite_postagem), 1, 0)
f['mesmo_estado'] = np.where(f.customer_state == f.seller_state, 'Mesmo estado', 'Interestadual')

def faixa(km):
    if pd.isna(km): return 'Sem informação'
    if km <= 100: return '1. Até 100 km'
    if km <= 500: return '2. 101 a 500 km'
    if km <= 1000: return '3. 501 a 1.000 km'
    if km <= 2000: return '4. 1.001 a 2.000 km'
    return '5. Acima de 2.000 km'
f['faixa_distancia'] = f.distancia_km.map(faixa)

# Inconsistências óbvias (datas negativas) viram vazio
for c in ['dias_aprovacao','dias_postagem','dias_transporte','dias_entrega']:
    f.loc[f[c] < 0, c] = np.nan

status_pt = {'delivered':'Entregue','shipped':'Enviado','canceled':'Cancelado','unavailable':'Indisponível',
             'invoiced':'Faturado','processing':'Em processamento','created':'Criado','approved':'Aprovado'}
f['status'] = f.order_status.map(status_pt)

fato = pd.DataFrame({
    'id_pedido': f.order_id,
    'id_cliente': f.customer_id,
    'id_vendedor': f.seller_id,
    'categoria': f.categoria,
    'uf_cliente': f.customer_state,
    'cidade_cliente': f.customer_city.str.title(),
    'uf_vendedor': f.seller_state,
    'status': f.status,
    'data_compra': f.order_purchase_timestamp.dt.date,
    'data_aprovacao': f.order_approved_at.dt.date,
    'data_postagem': f.order_delivered_carrier_date.dt.date,
    'data_entrega': f.order_delivered_customer_date.dt.date,
    'data_prevista': f.order_estimated_delivery_date.dt.date,
    'qtd_itens': f.qtd_itens,
    'qtd_vendedores': f.qtd_vendedores,
    'valor_produtos': f.valor_produtos.round(2),
    'valor_frete': f.valor_frete.round(2),
    'peso_total_kg': f.peso_total_kg.round(3),
    'distancia_km': f.distancia_km,
    'faixa_distancia': f.faixa_distancia,
    'rota': f.mesmo_estado,
    'dias_aprovacao': f.dias_aprovacao,
    'dias_postagem': f.dias_postagem,
    'dias_transporte': f.dias_transporte,
    'dias_entrega': f.dias_entrega,
    'dias_prometidos': f.dias_prometidos,
    'dias_atraso': f.dias_atraso,
    'entregue': f.entregue,
    'atrasado': f.atrasado,
    'postagem_atrasada': f.postagem_atrasada,
    'nota_avaliacao': f.review_score,
})
for c in ['data_compra','data_aprovacao','data_postagem','data_entrega','data_prevista']:
    fato[c] = pd.to_datetime(fato[c])

regioes = {'Norte':['AC','AP','AM','PA','RO','RR','TO'],'Nordeste':['AL','BA','CE','MA','PB','PE','PI','RN','SE'],
           'Centro-Oeste':['DF','GO','MT','MS'],'Sudeste':['ES','MG','RJ','SP'],'Sul':['PR','RS','SC']}
nomes = {'AC':'Acre','AL':'Alagoas','AP':'Amapá','AM':'Amazonas','BA':'Bahia','CE':'Ceará','DF':'Distrito Federal',
 'ES':'Espírito Santo','GO':'Goiás','MA':'Maranhão','MT':'Mato Grosso','MS':'Mato Grosso do Sul','MG':'Minas Gerais',
 'PA':'Pará','PB':'Paraíba','PR':'Paraná','PE':'Pernambuco','PI':'Piauí','RJ':'Rio de Janeiro','RN':'Rio Grande do Norte',
 'RS':'Rio Grande do Sul','RO':'Rondônia','RR':'Roraima','SC':'Santa Catarina','SP':'São Paulo','SE':'Sergipe','TO':'Tocantins'}
dim_estado = pd.DataFrame([{'uf':u,'estado':nomes[u],'regiao':r,'pais':'Brasil'} for r,us in regioes.items() for u in us]).sort_values('uf')

dim_vend = se[se.seller_id.isin(fato.id_vendedor)].rename(columns={'seller_id':'id_vendedor','seller_city':'cidade_vendedor','seller_state':'uf_vendedor'})
dim_vend['cidade_vendedor'] = dim_vend.cidade_vendedor.str.title()
dim_vend = dim_vend[['id_vendedor','cidade_vendedor','uf_vendedor']]
dim_vend = dim_vend.merge(dim_estado[['uf','regiao']].rename(columns={'uf':'uf_vendedor','regiao':'regiao_vendedor'}), on='uf_vendedor', how='left')

dim_cat = pd.DataFrame({'categoria': sorted(fato.categoria.unique())})

fato.to_pickle('fato.pkl')
with pd.ExcelWriter('olist_logistica_powerbi.xlsx', engine='openpyxl', datetime_format='DD/MM/YYYY') as w:
    fato.to_excel(w, sheet_name='fato_pedidos', index=False)
    dim_estado.to_excel(w, sheet_name='dim_estado', index=False)
    dim_vend.to_excel(w, sheet_name='dim_vendedor', index=False)
    dim_cat.to_excel(w, sheet_name='dim_categoria', index=False)
print(fato.shape, dim_vend.shape, dim_cat.shape)
print(fato.isna().sum()[lambda s: s>0])
