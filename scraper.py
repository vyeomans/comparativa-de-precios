import time
import os
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
# Nuevas librerías para las esperas inteligentes
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def limpiar_precio(texto_precio):
    match = re.search(r'([\d\.]+)', texto_precio)
    if match:
        return match.group(1).replace('.', '')
    return "0"

def obtener_precios_lider(driver, producto):
    resultados_lider = []
    base_url = "https://www.lider.cl"
    try:
        url_lider = f"{base_url}/search?q={producto}"
        driver.get(url_lider)
        print(f"Buscando productos para '{producto}' en Lider.cl...")
        
        # ESPERA INTELIGENTE: Espera hasta 15 segundos a que aparezca el primer contenedor de producto
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='group']"))
        )
        print("Productos de Lider cargados.")
        
        html_final = driver.page_source
        soup = BeautifulSoup(html_final, 'html.parser')
        
        for item in soup.find_all('div', attrs={'role': 'group'}):
            nombre_tag = item.find('span', attrs={'data-automation-id': 'product-title'})
            if not nombre_tag: continue
            precio_tag = item.find('div', attrs={'data-automation-id': 'product-price'})
            imagen_tag = item.find('img', attrs={'data-testid': 'productTileImage'})
            link_tag = item.find('a', attrs={'link-identifier': True})
            nombre = nombre_tag.get_text(strip=True)
            
            precio_final_texto = "No encontrado"
            if precio_tag:
                precio_final_tag = precio_tag.find('div')
                if precio_final_tag: precio_final_texto = precio_final_tag.get_text(strip=True)
            
            precio_limpio = limpiar_precio(precio_final_texto)
            imagen_url = imagen_tag['src'] if imagen_tag and imagen_tag.has_attr('src') else "No encontrada"
            url_producto = base_url + link_tag['href'] if link_tag and link_tag.has_attr('href') else "No encontrada"

            resultados_lider.append({
                'Producto': nombre, 'Supermercado': 'Lider', 'Precio': precio_limpio,
                'Imagen': imagen_url, 'Categoria': 'Barras de Proteína', 'URL': url_producto
            })
        print(f"Se encontraron {len(resultados_lider)} productos en Lider.")
    except Exception as e:
        print(f"Ocurrió un error en Lider: {e}")
    return resultados_lider

def obtener_precios_jumbo(driver, producto):
    resultados_jumbo = []
    base_url = "https://www.jumbo.cl"
    try:
        url_jumbo = f"{base_url}/busqueda?ft={producto}"
        driver.get(url_jumbo)
        print(f"\nBuscando productos para '{producto}' en Jumbo.cl...")

        # ESPERA INTELIGENTE: Espera hasta 15 segundos a que aparezca el primer contenedor de producto
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cnstrc-item-id]"))
        )
        print("Productos de Jumbo cargados.")
        
        html_final = driver.page_source
        soup = BeautifulSoup(html_final, 'html.parser')

        for item in soup.find_all('div', attrs={'data-cnstrc-item-id': True}):
            nombre_tag = item.find('h2', class_='product-card-name')
            imagen_tag = item.find('img')
            link_tag = item.find('a')
            
            precio_final_texto = "No encontrado"
            precio_container = item.find('div', class_='text-neutral700')
            if precio_container: precio_final_texto = precio_container.get_text(strip=True)
            
            nombre = nombre_tag.get_text(strip=True) if nombre_tag else "No encontrado"
            precio_limpio = limpiar_precio(precio_final_texto)
            imagen_url = imagen_tag['src'] if imagen_tag and imagen_tag.has_attr('src') else "No encontrada"
            url_producto = base_url + link_tag['href'] if link_tag and link_tag.has_attr('href') else "No encontrada"

            if nombre != "No encontrado":
                resultados_jumbo.append({
                    'Producto': nombre, 'Supermercado': 'Jumbo', 'Precio': precio_limpio,
                    'Imagen': imagen_url, 'Categoria': 'Barras de Proteína', 'URL': url_producto
                })
        print(f"Se encontraron {len(resultados_jumbo)} productos en Jumbo.")
    except Exception as e:
        print(f"Ocurrió un error en Jumbo: {e}")
    return resultados_jumbo

if __name__ == "__main__":
    producto_a_buscar = "barras de proteina"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    resultados_lider = obtener_precios_lider(driver, producto_a_buscar)
    resultados_jumbo = obtener_precios_jumbo(driver, producto_a_buscar)
    driver.quit()
    todos_los_resultados = resultados_lider + resultados_jumbo

    if todos_los_resultados:
        print(f"\n--- Total de productos encontrados: {len(todos_los_resultados)} ---")
        try:
            print("📦 Conectando con Google Sheets...")
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            client = gspread.authorize(creds)
            
            sheet = client.open("Comparativa de Precios").sheet1
            print("✅ Conexión exitosa. Actualizando la hoja de cálculo...")

            df = pd.DataFrame(todos_los_resultados)
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            
            print("¡Éxito! Tu Google Sheet ha sido actualizado.")

        except Exception as e:
            print(f"❌ Ocurrió un error al conectar o escribir en Google Sheets: {e}")
