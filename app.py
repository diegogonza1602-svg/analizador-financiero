import streamlit as st
import yfinance as yf
import pandas as pd
from google import genai

# Configuración de la página
st.set_page_config(
    page_title="Analizador Multiactivo de Inversión",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Analizador Multiactivo de Inversión & IA")
st.caption("Evaluación de Acciones, ETFs, Criptomonedas y Materias Primas / Oro para GBM")

# Sidebar - Configuración de API Key
st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Formatos de Tickers recomendados:**
* **Acciones:** `NVDA`, `AAPL`, `WALMEX.MX`
* **ETFs:** `VOO`, `QQQ`, `IVVPESO.MX`
* **Cripto:** `BTC-USD`, `ETH-USD`, `SOL-USD`
* **Oro:** `GC=F` (Futuro) o `GLD` (ETF Oro)
""")

# Entrada de Ticker
ticker_input = st.text_input(
    "Escribe el ticker del activo a analizar:",
    value="NVDA"
).strip().upper()

btn_analizar = st.button("🚀 Generar Análisis Especializado")

def identificar_tipo_activo(info, symbol):
    """Detecta la clase de activo según la información de yfinance"""
    qtype = info.get('quoteType', '').upper()
    
    if qtype == 'CRYPTOCURRENCY' or symbol.endswith('-USD'):
        return 'CRIPTO'
    elif qtype == 'ETF':
        return 'ETF'
    elif qtype in ['FUTURE', 'COMMODITY'] or symbol in ['GC=F', 'GLD', 'IAU', 'SLV', 'SI=F']:
        return 'ORO_COMMODITY'
    else:
        return 'ACCION'

if btn_analizar:
    if not api_key:
        st.error("Por favor, ingresa tu API Key de Gemini en la barra lateral izquierda.")
    elif not ticker_input:
        st.warning("Por favor, ingresa un ticker válido.")
    else:
        with st.spinner(f"Descargando datos y analizando {ticker_input}..."):
            try:
                # 1. Obtención de datos de yfinance
                asset = yf.Ticker(ticker_input)
                info = asset.info
                hist = asset.history(period="1y")

                if hist.empty:
                    st.error(f"No se encontraron datos históricos para el ticker '{ticker_input}'. Verifica que esté bien escrito.")
                    st.stop()

                tipo_activo = identificar_tipo_activo(info, ticker_input)
                precio_actual = info.get('currentPrice') or info.get('regularMarketPrice') or (hist['Close'].iloc[-1] if not hist.empty else 0)
                
                st.subheader(f"📊 Panel Métrico: {info.get('shortName', ticker_input)} [{tipo_activo}]")

                # 2. Renderizado de métricas cuantitativas según tipo de activo
                if tipo_activo == 'ACCION':
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Precio Actual", f"${precio_actual:,.2f}")
                    c2.metric("Beta (Volatilidad)", f"{info.get('beta', 'N/A')}")
                    c3.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
                    c4.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.1f}%" if info.get('returnOnEquity') else "N/A")
                    c5.metric("Margen Neto", f"{info.get('profitMargins', 0)*100:.1f}%" if info.get('profitMargins') else "N/A")

                elif tipo_activo == 'ETF':
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Precio Actual", f"${precio_actual:,.2f}")
                    exp_ratio = info.get('netExpenseRatio') or info.get('expenseRatio')
                    c2.metric("Comisión Anual", f"{exp_ratio*100:.2f}%" if exp_ratio else "N/A")
                    aum = info.get('totalAssets')
                    c3.metric("AUM (Fondos)", f"${aum/1e9:,.2f}B" if aum else "N/A")
                    c4.metric("Rendimiento 1Y", f"{((hist['Close'].iloc[-1]/hist['Close'].iloc[0])-1)*100:.1f}%")

                elif tipo_activo == 'CRIPTO':
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Precio Actual", f"${precio_actual:,.2f}")
                    mcap = info.get('marketCap')
                    c2.metric("Cap. de Mercado", f"${mcap/1e9:,.2f}B" if mcap else "N/A")
                    circ_supply = info.get('circulatingSupply')
                    c3.metric("Oferta Circulante", f"{circ_supply:,.0f}" if circ_supply else "N/A")
                    c4.metric("Rendimiento 1Y", f"{((hist['Close'].iloc[-1]/hist['Close'].iloc[0])-1)*100:.1f}%")

                elif tipo_activo == 'ORO_COMMODITY':
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Precio Spot/Futuro", f"${precio_actual:,.2f}")
                    high_52 = info.get('fiftyTwoWeekHigh') or hist['High'].max()
                    low_52 = info.get('fiftyTwoWeekLow') or hist['Low'].min()
                    c2.metric("Máximo 52 Semanas", f"${high_52:,.2f}")
                    c3.metric("Mínimo 52 Semanas", f"${low_52:,.2f}")

                # Gráfica de Precio
                st.line_chart(hist['Close'], y_label="Precio (USD)")

                # 3. Construcción del Prompt dinámico para Gemini
                if tipo_activo == 'ACCION':
                    instrucción_matriz = """
                    Analiza la acción en la matriz de 10 Puntos Fundamentales:
                    1. Volatilidad (Beta)
                    2. Salud Financiera y Deuda (Net Debt/EBITDA)
                    3. Tendencia de Ingresos (3-5 años)
                    4. Rentabilidad (Margen Operativo / ROE)
                    5. Flujo de Caja Libre (FCF)
                    6. Valoración (P/E, EV/EBITDA, P/S)
                    7. Ventaja Competitiva (Moat)
                    8. Perspectivas de Crecimiento Futuro
                    9. Calidad del Equipo Directivo
                    10. Riesgos Externos y Macro
                    """
                elif tipo_activo == 'ETF':
                    instrucción_matriz = """
                    Analiza el ETF bajo la siguiente estructura para portafolios de GBM:
                    1. Eficiencia y Comisión Anual (Expense Ratio)
                    2. Índice que replica y Estrategia de Inversión
                    3. Concentración de Top Holdings y Diversificación
                    4. Liquidez, AUM y Tracking Error
                    5. Rol recomendado en un portafolio de inversión (Núcleo o Satélite)
                    """
                elif tipo_activo == 'CRIPTO':
                    instrucción_matriz = """
                    Analiza el activo cripto bajo la siguiente estructura de riesgo:
                    1. Tokenomía y Dinámica de Oferta (Estructura de emisión/quema)
                    2. Adopción de Red, Casos de Uso y TVL/Volumen
                    3. Perfil de Volatilidad y Drawdowns Históricos
                    4. Entorno Regulatorio y Descentralización
                    5. Tesis de Inversión y Nivel de Riesgo para un Inversionista
                    """
                elif tipo_activo == 'ORO_COMMODITY':
                    instrucción_matriz = """
                    Analiza el Oro/Commodity bajo la siguiente estructura macroeconómica:
                    1. Función como Cobertura de Inflación y Valor Refugio
                    2. Sensibilidad a Tasas de Interés Reales y Dólar (DXY)
                    3. Dinámica de Oferta y Demanda Global (Bancos Centrales, Industria)
                    4. Riesgos Geopolíticos y Ciclos Económicos
                    5. Porcentaje Sugerido de Asignación en Portafolio
                    """

                prompt = f"""
                Actúa como un Analista Financiero Senior para inversionistas en GBM.
                Realiza una evaluación profesional sobre el activo: {ticker_input} (Nombre: {info.get('shortName', ticker_input)}).
                Tipo de Activo detectado: {tipo_activo}.

                Datos clave obtenidos:
                - Precio actual: ${precio_actual}
                - Resumen de perfil: {info.get('longBusinessSummary', 'No disponible')[:800]}

                Instrucciones:
                {instrucción_matriz}

                Concluye obligatoriamente con un dictamen claro: [ATRACTIVO / NEUTRAL / RIESGOSO] y una recomendación práctica de ejecución.
                """

            # 4. Consulta a Gemini mediante Google GenAI SDK
                clave_limpia = api_key.strip().replace('"', '').replace("'", "")
                client = genai.Client(api_key=clave_limpia)

                try:
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt
                    )
                except Exception as err:
                    # Fallback por si la cuenta tiene asignado el nombre alternativo de ruta
                    response = client.models.generate_content(
                        model='models/gemini-3.8-flash',
                        contents=prompt
                    )

                st.markdown("---")
                st.subheader("📝 Dictamen y Análisis Cualitativo por IA")
                st.write(response.text)

                # Opción de Descarga del Reporte
                resumen_txt = f"ANÁLISIS DE INVERSIÓN: {ticker_input} ({tipo_activo})\n" + "="*50 + f"\n\n{response.text}"
                st.download_button(
                    label="📄 Descargar Reporte (.txt)",
                    data=resumen_txt,
                    file_name=f"reporte_{ticker_input}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"Ocurrió un error al procesar el activo: {str(e)}")

st.markdown("---")
st.caption("Nota: Herramienta desarrollada para investigación académica y análisis patrimonial.")