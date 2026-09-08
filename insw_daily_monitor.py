#!/usr/bin/env python3
"""
INSW & Tanker Market Risk Monitor
---------------------------------
Este script recopila diariamente:
1. Métricas financieras y de cotización de INSW (vía Yahoo Finance).
2. Novedades y noticias clave sobre tarifas marítimas, VLCC, estrecho de Ormuz y el Canal de Suez.
3. Alertas sobre nuevas presentaciones trimestrales (10-Q / 8-K) en la SEC EDGAR.
4. Genera un reporte formateado y lo envía por correo electrónico (o Telegram).
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import urllib.request
import json
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURACIÓN DE NOTIFICACIONES (EMAIL)
# ==========================================
SMTP_SERVER = ""
SMTP_PORT = 465
SENDER_EMAIL = ""
SENDER_PASSWORD = ""  # Contraseña de aplicación de Google
RECIPIENT_EMAIL = ""

def get_stock_data():
    """Obtiene datos de cotización de INSW usando endpoints públicos de Yahoo Finance."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/INSW?interval=1d&range=5d"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            meta = data['chart']['result'][0]['meta']
            price = meta.get('regularMarketPrice')
            prev_close = meta.get('chartPreviousClose')
            change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
            return {
                "price": price,
                "prev_close": prev_close,
                "change_pct": change_pct,
                "52w_high": meta.get('fiftyTwoWeekHigh'),
                "52w_low": meta.get('fiftyTwoWeekLow')
            }
    except Exception as e:
        return {"error": str(e)}

def get_shipping_news():
    """Recopila noticias recientes sobre tanqueros, tarifas spot y rutas estratégicas."""
    query = "VLCC+tanker+rates+OR+International+Seaways+OR+Hormuz+tanker"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
    headlines = []
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text
                link = item.find('link').text
                pub_date = item.find('pubDate').text
                headlines.append({"title": title, "link": link, "date": pub_date})
    except Exception as e:
        headlines.append({"title": f"Error al consultar noticias: {e}", "link": "#", "date": ""})
    return headlines

def get_sec_filings():
    """Verifica si International Seaways ha publicado nuevos reportes (10-K, 10-Q, 8-K) en SEC EDGAR."""
    cik = "0001643650"  # CIK de International Seaways, Inc.
    sec_feed = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&dateb=&owner=exclude&start=0&count=5&output=atom"
    req = urllib.request.Request(sec_feed, headers={'User-Agent': 'InvestorMonitoringBot admin@myemail.com'})
    filings = []
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            # Namespace de Atom
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns)[:3]:
                title = entry.find('atom:title', ns).text
                link = entry.find('atom:link', ns).attrib.get('href', '#')
                updated = entry.find('atom:updated', ns).text
                filings.append({"title": title, "link": link, "date": updated})
    except Exception as e:
        filings.append({"title": f"Error consultando SEC EDGAR: {e}", "link": "#", "date": ""})
    return filings

def build_html_report(stock, news, filings):
    """Construye un reporte HTML estilizado y fácil de leer en dispositivos móviles."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    price_color = "#28a745" if stock.get("change_pct", 0) >= 0 else "#dc3545"
    price_sign = "+" if stock.get("change_pct", 0) >= 0 else ""
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; padding: 24px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            h2 {{ color: #1a202c; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 0; }}
            h3 {{ color: #2d3748; margin-top: 20px; font-size: 16px; text-transform: uppercase; letter-spacing: 0.5px; }}
            .metric-box {{ background: #f8fafc; border-left: 4px solid #3182ce; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px; }}
            .metric-val {{ font-size: 24px; font-weight: bold; color: {price_color}; }}
            ul {{ list-style-type: none; padding-left: 0; }}
            li {{ padding: 8px 0; border-bottom: 1px solid #edf2f7; }}
            a {{ color: #3182ce; text-decoration: none; font-weight: 500; }}
            a:hover {{ text-decoration: underline; }}
            .footer {{ font-size: 12px; color: #a0aec0; margin-top: 24px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🚢 Monitor Diario: International Seaways (INSW)</h2>
            <p style="color: #718096; font-size: 14px;">Fecha del reporte: <strong>{now}</strong></p>
            
            <div class="metric-box">
                <div style="font-size: 14px; color: #4a5568;">Cotización INSW (NYSE)</div>
                <div class="metric-val">${stock.get('price', 'N/A')} <span style="font-size: 16px;">({price_sign}{stock.get('change_pct', 0):.2f}%)</span></div>
                <div style="font-size: 12px; color: #718096; margin-top: 4px;">52-Week Range: ${stock.get('52w_low', '-')} - ${stock.get('52w_high', '-')}</div>
            </div>

            <h3>1. Últimos Reportes Regulatorios (SEC EDGAR)</h3>
            <ul>
    """
    for f in filings:
        html += f'<li><a href="{f["link"]}">{f["title"]}</a><br><small style="color: #a0aec0;">{f["date"]}</small></li>'
    
    html += """
            </ul>

            <h3>2. Titulares Clave: Tarifas & Geopolítica (Ormuz / Suez / VLCC)</h3>
            <ul>
    """
    for n in news:
        html += f'<li><a href="{n["link"]}">{n["title"]}</a><br><small style="color: #a0aec0;">{n["date"]}</small></li>'

    html += """
            </ul>

            <div class="footer">
                Monitor automatizado de riesgo para transporte marítimo de energía.
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_email(html_content):
    """Envía el correo electrónico formateado."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 Alerta Diaria INSW & Mercado de Tanqueros - {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print("Reporte enviado exitosamente.")
    except Exception as e:
        print(f"Error enviando correo: {e}")

if __name__ == "__main__":
    print("Obteniendo métricas de INSW...")
    stock = get_stock_data()
    print("Obteniendo noticias marítimas...")
    news = get_shipping_news()
    print("Verificando reportes en SEC EDGAR...")
    filings = get_sec_filings()
    
    report = build_html_report(stock, news, filings)
    
    # Guarda una copia local en HTML
    with open("reporte_diario_insw.html", "w", encoding="utf-8") as f:
        f.write(report)
    print("Reporte guardado localmente en 'reporte_diario_insw.html'")
    
    # Descomentar la siguiente línea para enviar por correo si configuraste tus credenciales SMTP:


    # send_email(report)
