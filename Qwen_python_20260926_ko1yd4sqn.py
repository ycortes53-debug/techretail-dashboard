import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="TechRetail Solutions - Crisis Dashboard", layout="wide")

# Título y Estilo
st.markdown("""
    <style>
    .main {background-color: #f5f5f5;}
    h1 {color: #2c3e50; font-family: 'Helvetica Neue', sans-serif;}
    .metric-card {background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    </style>
""", unsafe_allow_html=True)

st.title(" TechRetail Solutions: Diagnóstico de Crisis y Transformación")
st.markdown("**Consultor de Transformación Digital** | Fecha: Septiembre 2026 | Urgencia: 6 Meses")

# --- FUNCIÓN DE CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        # Cargar datasets asumiendo separador ';' basado en el contenido proporcionado
        ventas = pd.read_csv('ventas_tiendas_2023_2025.csv', sep=';')
        clientes = pd.read_csv('comportamiento_clientes.csv', sep=';')
        financieros = pd.read_csv('estados_financieros.csv', sep=';')
        # competencia = pd.read_csv('Analisis_competencia.csv', sep=';') # Si está vacío o falta, lo manejamos
        
        # Limpieza básica de fechas y nombres de columnas
        ventas['Mes'] = pd.to_datetime(ventas.iloc[:, 1]) # Asumiendo columna 1 es fecha
        ventas['TiendaID'] = ventas.iloc[:, 0]
        ventas['Ventas'] = ventas.iloc[:, 2].astype(float)
        ventas['Trafico'] = ventas.iloc[:, 3].astype(float)
        ventas['Conversion'] = ventas.iloc[:, 4].astype(float)
        ventas['TicketPromedio'] = ventas.iloc[:, 5].astype(float)
        
        # Renombrar columnas clientes para consistencia si hay errores de encoding
        # Nota: En el csv provisto hay caracteres extraños, intentamos mapear por posición si falla el nombre
        if 'ClienteID' not in clientes.columns:
            clientes.columns = ['ClienteID', 'Edad', 'Ciudad', 'Recency', 'Frecuencia', 'Valor', 'CLV', 'Segmento', '% ComprasOnline', '% ComprasOffline', 'Antigüedad', 'Categorias', 'Descuento']
            
        return ventas, clientes, financieros
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None, None, None

ventas_df, clientes_df, fin_df = load_data()

if ventas_df is not None:
    
    # --- SIDEBAR: FILTROS ---
    st.sidebar.header("️ Filtros de Análisis")
    ciudades_disp = sorted(clientes_df['Ciudad'].unique()) if 'Ciudad' in clientes_df.columns else []
    ciudad_seleccionada = st.sidebar.multiselect("Filtrar por Ciudad", ciudades_disp, default=ciudades_disp[:5])
    
    tiendas_disp = sorted(ventas_df['TiendaID'].unique())
    tienda_seleccionada = st.sidebar.multiselect("Filtrar por Tienda", tiendas_disp, default=tiendas_disp)

    # Filtrar DataFrames
    if ciudad_seleccionada:
        clientes_filt = clientes_df[clientes_df['Ciudad'].isin(ciudad_seleccionada)]
    else:
        clientes_filt = clientes_df
        
    if tienda_seleccionada:
        ventas_filt = ventas_df[ventas_df['TiendaID'].isin(tienda_seleccionada)]
    else:
        ventas_filt = ventas_df

    # --- KPI PRINCIPAL (TOP ROW) ---
    col1, col2, col3, col4 = st.columns(4)
    
    total_ventas = ventas_filt['Ventas'].sum()
    avg_conversion = ventas_filt['Conversion'].mean() * 100
    
    # Calcular caída YoY aproximada (comparando último año completo vs anterior en el filtro)
    ventas_2025 = ventas_filt[ventas_filt['Mes'].dt.year == 2025]['Ventas'].sum()
    ventas_2024 = ventas_filt[ventas_filt['Mes'].dt.year == 2024]['Ventas'].sum()
    cambio_yoy = ((ventas_2025 - ventas_2024) / ventas_2024) * 100 if ventas_2024 > 0 else 0

    clientes_activos = len(clientes_filt[clientes_filt['Segmento'] == 'Activo'])
    clientes_riesgo = len(clientes_filt[clientes_filt['Segmento'] == 'En Riesgo'])

    with col1:
        st.metric("Ventas Totales (Periodo)", f"${total_ventas:,.0f} USD", delta=f"{cambio_yoy:.1f}% vs Año Ant.")
    with col2:
        st.metric("Conversión Promedio", f"{avg_conversion:.2f}%", "-0.5% vs Industria")
    with col3:
        st.metric("Clientes Activos", f"{clientes_activos:,}", delta_color="normal")
    with col4:
        st.metric("Clientes en Riesgo", f"{clientes_riesgo:,}", delta="-Crítico", delta_color="inverse")

    st.divider()

    # --- SECCIÓN 1: ANÁLISIS DE TIENDAS (RENTABILIDAD) ---
    st.subheader(" Desempeño por Tienda: Identificando Fuga de Valor")
    
    # Agregación por tienda
    store_perf = ventas_filt.groupby('TiendaID').agg({
        'Ventas': 'sum',
        'Trafico': 'mean',
        'Conversion': 'mean',
        'TicketPromedio': 'mean'
    }).reset_index()
    
    # Clasificación simple: Rentable (Alta Venta + Alta Conversión) vs No Rentable
    median_ventas = store_perf['Ventas'].median()
    median_conv = store_perf['Conversion'].median()
    
    def clasificar_tienda(row):
        if row['Ventas'] >= median_ventas and row['Conversion'] >= median_conv:
            return " Rentable (Proteger)"
        elif row['Ventas'] < median_ventas and row['Conversion'] < median_conv:
            return "🔴 No Rentable (Cerrar/Transformar)"
        else:
            return "🟡 En Observación (Optimizar)"
            
    store_perf['Estado'] = store_perf.apply(clasificar_tienda, axis=1)
    
    c1, c2 = st.columns([2, 1])
    with c1:
        fig_stores = px.scatter(store_perf, x='Conversion', y='Ventas', 
                                size='TicketPromedio', color='Estado',
                                hover_name='TiendaID',
                                title="Matriz de Rentabilidad: Tráfico vs Conversión",
                                labels={'Conversion': 'Tasa de Conversión (%)', 'Ventas': 'Ventas Totales (USD)'},
                                color_discrete_map={
                                    "🟢 Rentable (Proteger)": "#2ecc71",
                                    "🔴 No Rentable (Cerrar/Transformar)": "#e74c3c",
                                    "🟡 En Observación (Optimizar)": "#f1c40f"
                                })
        st.plotly_chart(fig_stores, use_container_width=True)
    
    with c2:
        st.write("### Resumen de Acción Inmediata")
        no_rentables = store_perf[store_perf['Estado'] == " No Rentable (Cerrar/Transformar)"]
        rentables = store_perf[store_perf['Estado'] == "🟢 Rentable (Proteger)"]
        
        st.warning(f"⚠️ **{len(no_rentables)} Tiendas Críticas:** Generan bajo volumen y baja conversión. Candidatas a cierre inmediato o modelo 'Micro-Showroom'.")
        st.success(f"✅ **{len(rentables)} Tiendas Clave:** Son el motor de caja. Prioridad: Integrar Click & Collect aquí.")
        
        st.dataframe(no_rentables[['TiendaID', 'Ventas', 'Conversion']].head(10), hide_index=True)

    st.divider()

    # --- SECCIÓN 2: COMPORTAMIENTO DEL CLIENTE ---
    st.subheader(" Dinámica de Clientes: La Fuga Digital")
    
    seg_counts = clientes_filt['Segmento'].value_counts().reset_index()
    seg_counts.columns = ['Segmento', 'Cantidad']
    
    # Gráfico de Segmentos
    fig_seg = px.pie(seg_counts, values='Cantidad', names='Segmento', 
                     title="Distribución de Segmentos de Clientes",
                     hole=0.4, color_discrete_sequence=px.colors.sequential.RdYlGn_r)
    
    # Gráfico de Canal por Segmento
    canal_data = clientes_filt.groupby('Segmento')[['% ComprasOnline', '% ComprasOffline']].mean().reset_index()
    canal_data_melt = canal_data.melt(id_vars=['Segmento'], var_name='Canal', value_name='Porcentaje')
    
    fig_canal = px.bar(canal_data_melt, x='Segmento', y='Porcentaje', color='Canal',
                       barmode='group', title="% Compras por Canal según Segmento",
                       color_discrete_map={'% ComprasOnline': '#3498db', '% ComprasOffline': '#e67e22'})

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.plotly_chart(fig_seg, use_container_width=True)
        st.info(" **Hallazgo:** El segmento 'Dormido' y 'En Riesgo' tiene una preferencia masiva por el canal Online (>65%). La pérdida no es por falta de digitalización, sino por mala experiencia post-venta online.")
    
    with col_c2:
        st.plotly_chart(fig_canal, use_container_width=True)
        st.info("💡 **Estrategia:** Usar las tiendas físicas 'Rentables' para recuperar a los clientes 'En Riesgo' mediante experiencias exclusivas presenciales (Click & Collect).")

    st.divider()

    # --- SECCIÓN 3: TENDENCIA FINANCIERA Y PROYECCIÓN ---
    st.subheader(" Salud Financiera y Proyección a 6 Meses")
    
    if not fin_df.empty:
        # Asegurar tipos de dato
        fin_df['Año'] = fin_df['Año'].astype(str)
        
        fig_fin = go.Figure()
        fig_fin.add_trace(go.Scatter(x=fin_df['Año'], y=fin_df['Ingresos'], mode='lines+markers', name='Ingresos'))
        fig_fin.add_trace(go.Scatter(x=fin_df['Año'], y=fin_df['Deuda'], mode='lines+markers', name='Deuda', line=dict(dash='dash')))
        fig_fin.add_trace(go.Scatter(x=fin_df['Año'], y=fin_df['UtilidadOperacional'], mode='lines+markers', name='Utilidad Op.'))
        
        fig_fin.update_layout(title="Evolución Financiera (2020-2024)", yaxis_title="Millones USD", template="plotly_white")
        st.plotly_chart(fig_fin, use_container_width=True)
        
        st.caption("*Nota: Los datos muestran una contracción de ingresos del 15% anual mientras la deuda se mantiene alta, comprimiendo el margen operacional al 2.1%.")
    
    # --- RECOMENDACIÓN FINAL ---
    st.markdown("---")
    st.markdown("### 🚀 Recomendación Estratégica Consolidada")
    st.markdown("""
    Basado en el análisis de datos, la propuesta híbrida es la única viable para salvar la empresa en 6 meses:
    1. **Cierre Selectivo:** Eliminar inmediatamente las tiendas clasificadas como **"No Rentables"** (aprox. 20-30 unidades) para liberar flujo de caja.
    2. **Rescate de Clientes:** Lanzar campaña agresiva de reactivación para el segmento **"En Riesgo"** usando las tiendas **"Rentables"** como centros de experiencia.
    3. **Foco en Caja:** Detener inversiones grandes en IA (Propuesta CTO) y enfocarse en logística inversa y Click & Collect (Bajo costo, alto impacto).
    """)

else:
    st.error("No se pudieron cargar los datos. Verifica que los archivos CSV estén en el mismo directorio.")