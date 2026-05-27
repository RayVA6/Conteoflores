import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Control Calidad Flores", layout="wide")

st.title("📊 Dashboard de Control de Calidad: Botón Floral")
st.markdown("Sube el reporte semanal descargado para auditar ceros y valores atípicos.")

# 1. CARGA DEL ARCHIVO
archivo_subido = st.file_uploader("Sube el archivo Excel de Evaluaciones", type=["xlsx", "xls"])

# Caché para lectura optimizada
@st.cache_data
def cargar_datos(file):
    df = pd.read_excel(file, sheet_name='BD')
    
    # ---> LA SOLUCIÓN: Limpiar espacios invisibles en los nombres de las columnas <---
    df.columns = df.columns.str.strip()
    
    df['Semana'] = df['Semana'].astype(str)
    return df

if archivo_subido is not None:
    try:
        # Intentamos cargar la data de la hoja 'BD'
        df = cargar_datos(archivo_subido)
        columna_valor = 'BOTON_FLORAL'
        columna_tiempo = 'Semana'

        # 2. BARRA LATERAL: FILTROS EN CASCADA
        st.sidebar.header("🔍 Filtros de Análisis")

        # Filtro Semana 
        semanas_unicas = ['Todas'] + sorted(df[columna_tiempo].unique().tolist(), key=lambda x: int(x) if x.isdigit() else x)
        semana_sel = st.sidebar.selectbox("Semana:", semanas_unicas)

        # Filtro Fundo
        fundos_unicos = ['Todos'] + sorted(df['Nombre Fundo'].dropna().unique().tolist())
        fundo_sel = st.sidebar.selectbox("Fundo:", fundos_unicos)

        df_temp = df.copy()
        if fundo_sel != 'Todos':
            df_temp = df_temp[df_temp['Nombre Fundo'] == fundo_sel]

        # Filtro Módulo 
        modulos_unicos = ['Todos'] + sorted(df_temp['Nombre Modulo'].dropna().unique().tolist())
        modulo_sel = st.sidebar.selectbox("Módulo:", modulos_unicos)

        if modulo_sel != 'Todos':
            df_temp = df_temp[df_temp['Nombre Modulo'] == modulo_sel]

        # Filtro Lotes (Múltiple)
        lotes_unicos = ['Todos'] + sorted(df_temp['Lote Guia'].dropna().unique().tolist())
        lote_sel = st.sidebar.multiselect("Lotes:", lotes_unicos, default=['Todos'])

        # Filtro Variedad
        variedades_unicas = ['Todas'] + sorted(df_temp['Variedad'].dropna().unique().tolist())
        variedad_sel = st.sidebar.selectbox("Variedad:", variedades_unicas)

        # 3. APLICAR FILTROS AL DATAFRAME FINAL
        df_final = df_temp.copy()
        if semana_sel != 'Todas':
            df_final = df_final[df_final[columna_tiempo] == semana_sel]
        if variedad_sel != 'Todas':
            df_final = df_final[df_final['Variedad'] == variedad_sel]
        if 'Todos' not in lote_sel and len(lote_sel) > 0:
            df_final = df_final[df_final['Lote Guia'].isin(lote_sel)]

        # 4. RENDERIZADO DEL DASHBOARD
        if df_final.empty:
            st.warning("⚠️ No hay datos para esta combinación de filtros.")
        else:
            if len(lote_sel) == 1 and lote_sel[0] != 'Todos':
                eje_x = 'Planta cultivada'
                df_final[eje_x] = df_final[eje_x].astype(str)
                titulo_grafico = f'Detalle por Planta - Lote {lote_sel[0]} (Semana {semana_sel})'
                grupo_analisis = 'Planta cultivada'
            else:
                eje_x = 'Lote Guia'
                df_final[eje_x] = df_final[eje_x].astype(str)
                titulo_grafico = f'Comparativa por Lotes (Semana {semana_sel})'
                grupo_analisis = 'Lote Guia'

            # Gráfico Plotly
            fig = px.box(
                df_final, 
                x=eje_x, 
                y=columna_valor, 
                color=eje_x, 
                points='all', 
                hover_data=['Semana', 'Nombre Modulo', 'Lote Guia', 'Planta cultivada', 'Nombre Usuario'], 
                title=titulo_grafico
            )
            fig.update_xaxes(categoryorder='category ascending')
            st.plotly_chart(fig, use_container_width=True)

            # 5. TABLAS DE REPORTES (Lado a lado)
            col1, col2 = st.columns(2)
            columnas_reporte = ['Semana', 'Nombre Fundo', 'Nombre Modulo', 'Lote Guia', 'Planta cultivada', 'Variedad', 'Nombre Usuario', 'BOTON_FLORAL']

            with col1:
                st.subheader("⚠️ Valores en Cero")
                df_ceros = df_final[df_final[columna_valor] == 0]
                if df_ceros.empty:
                    st.success("No se registraron valores en cero.")
                else:
                    st.warning(f"{len(df_ceros)} evaluaciones en cero detectadas:")
                    st.dataframe(df_ceros[columnas_reporte].sort_values(by=['Semana', 'Lote Guia']), use_container_width=True)

            with col2:
                st.subheader("🚨 Valores Atípicos (Anomalías)")
                def calcular_iqr(grupo):
                    if len(grupo) < 4: return pd.DataFrame() 
                    Q1 = grupo[columna_valor].quantile(0.25)
                    Q3 = grupo[columna_valor].quantile(0.75)
                    IQR = Q3 - Q1
                    li = Q1 - 1.5 * IQR
                    ls = Q3 + 1.5 * IQR
                    return grupo[(grupo[columna_valor] < li) | (grupo[columna_valor] > ls)]
                
                df_atipicos = df_final.groupby(['Semana', grupo_analisis]).apply(calcular_iqr).reset_index(drop=True)
                
                if df_atipicos.empty:
                    st.success("No se detectaron atípicos estadísticos.")
                else:
                    st.error(f"{len(df_atipicos)} registros fuera de los rangos normales:")
                    st.dataframe(df_atipicos.sort_values(by=['Semana', columna_valor], ascending=[True, False])[columnas_reporte], use_container_width=True)

    # Manejo de errores
    except ValueError:
        st.error("❌ Error: No se encontró la pestaña llamada 'BD' en el archivo Excel. Asegúrate de subir el archivo correcto.")
    except KeyError as e:
        st.error(f"❌ Error: Falta una columna requerida en la hoja 'BD'. Asegúrate de que exista la columna: {e}")
    except Exception as e:
        st.error(f"❌ Ocurrió un error inesperado al procesar el archivo: {e}")

else:
    st.info("👆 Esperando archivo... Arrastra y suelta tu base de datos arriba para comenzar el análisis.")
