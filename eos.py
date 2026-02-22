import requests
import webbrowser
import json
from urllib.parse import urlencode

# ========= USAR TUS CREDENCIALES REALES =========
# OBTÉN ESTAS DE: https://dev.epicgames.com/portal/
CLIENT_ID = "xyza7891vvKcnL7qzQfT9m73LtCJikI8"  # Reemplaza con el tuyo
CLIENT_SECRET = "TL6CvrvrXUsF4hNREbypaoPRjjLl/RW505+ZumPTthw"  # Reemplaza con el tuyo
REDIRECT_URI = "http://localhost:5000/callback"
# ===============================================

def get_friends_list():
    # Paso 1: Abrir navegador para login
    auth_params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "friends_list country presence",
        "display": "popup"
    }
    
    auth_url = f"https://www.epicgames.com/id/authorize?{urlencode(auth_params)}"
    
    print("🎮 Abriendo Epic Games para login...")
    webbrowser.open(auth_url)
    
    # Paso 2: Capturar el código (solo el código, sin "code=")
    full_code = input("Pega toda la URL o código después de login: ").strip()
    
    # Extraer solo el código
    if "code=" in full_code:
        code = full_code.split("code=")[1]
        # Limpiar parámetros adicionales
        if "&" in code:
            code = code.split("&")[0]
    else:
        code = full_code
    
    print(f"🔑 Código obtenido: {code}")
    
    # Paso 3: Obtener token (CORREGIDO)
    token_url = "https://api.epicgames.dev/epic/oauth/v1/token"
    
    # Datos CORRECTOS para token request
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    
    print("\n🔄 Obteniendo token de acceso...")
    
    # Hacer request CON Client ID y Secret en Basic Auth
    response = requests.post(
        token_url,
        data=token_data,
        auth=(CLIENT_ID, CLIENT_SECRET),  # ¡IMPORTANTE!
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"📡 Status Code: {response.status_code}")
    print(f"📥 Respuesta: {response.text}")
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print("Posibles causas:")
        print("1. Client ID o Secret incorrectos")
        print("2. Redirect URI no coincide")
        print("3. Código expirado (válido solo 5 minutos)")
        return []
    
    try:
        token_info = response.json()
        
        if "access_token" not in token_info:
            print("❌ No se recibió access_token")
            print("Respuesta completa:", token_info)
            return []
        
        token = token_info["access_token"]
        print(f"✅ Token obtenido! Tipo: {token_info.get('token_type', 'Bearer')}")
        print(f"   • Expira en: {token_info.get('expires_in', '?')} segundos")
        
    except Exception as e:
        print(f"❌ Error procesando respuesta: {e}")
        return []
    
    # Paso 4: Primero obtener TU cuenta ID
    print("\n👤 Obteniendo tu información...")
    headers = {"Authorization": f"Bearer {token}"}
    
    account_response = requests.get(
        "https://api.epicgames.dev/epic/id/v1/accounts",
        headers=headers
    )
    
    if account_response.status_code != 200:
        print(f"❌ Error obteniendo cuenta: {account_response.status_code}")
        return []
    
    accounts = account_response.json()
    if not accounts:
        print("❌ No se encontró información de cuenta")
        return []
    
    your_account_id = accounts[0]["accountId"]
    your_name = accounts[0]["displayName"]
    print(f"✅ Conectado como: {your_name} ({your_account_id})")
    
    # Paso 5: Obtener amigos
    print(f"\n👥 Obteniendo lista de amigos...")
    
    friends_url = f"https://api.epicgames.dev/epic/friends/v1/{your_account_id}/friends"
    
    friends_response = requests.get(friends_url, headers=headers)
    
    if friends_response.status_code != 200:
        print(f"❌ Error obteniendo amigos: {friends_response.status_code}")
        print(f"Respuesta: {friends_response.text}")
        return []
    
    friends_data = friends_response.json()
    
    if not friends_data:
        print("ℹ️ No tienes amigos en tu lista o no tienes permiso")
        return []
    
    # Paso 6: Obtener presencia
    print("\n📡 Obteniendo estados de presencia...")
    
    friend_ids = [friend.get("accountId") for friend in friends_data if friend.get("accountId")]
    
    presence_url = "https://api.epicgames.dev/epic/presence/v1/presence"
    presence_response = requests.post(
        presence_url,
        headers=headers,
        json={"accountIds": friend_ids[:50]}  # Límite de 50
    )
    
    presence_data = {}
    if presence_response.status_code == 200:
        presence_data = presence_response.json()
    
    # Paso 7: Mostrar resultados
    print("\n" + "="*60)
    print(f"🎮 AMIGOS DE EPIC GAMES - {your_name}")
    print("="*60)
    
    print(f"\n📊 Total de amigos: {len(friends_data)}")
    print("-"*60)
    
    # Contadores
    online_count = 0
    
    for friend in friends_data:
        friend_id = friend.get("accountId", "")
        friend_name = friend.get("displayName", "Desconocido")
        
        # Buscar presencia
        status = "⚫ Offline"
        
        if "responses" in presence_data:
            for presence in presence_data["responses"]:
                if presence.get("accountId") == friend_id:
                    if presence.get("online", False):
                        status = "🟢 En línea"
                        online_count += 1
                        
                        # Verificar juego
                        game = presence.get("productName", "")
                        if game:
                            status += f" | 🎮 {game}"
                    break
        
        print(f"{status} {friend_name}")
    
    print("-"*60)
    print(f"\n📈 Resumen: {online_count} en línea de {len(friends_data)}")
    print("="*60)
    
    # Guardar en archivo
    try:
        with open('epic_friends.json', 'w', encoding='utf-8') as f:
            json.dump({
                "your_account": {
                    "id": your_account_id,
                    "name": your_name
                },
                "friends": friends_data,
                "presence": presence_data,
                "summary": {
                    "total": len(friends_data),
                    "online": online_count,
                    "offline": len(friends_data) - online_count
                }
            }, f, indent=2, ensure_ascii=False)
        
        print("\n💾 Datos guardados en 'epic_friends.json'")
    except Exception as e:
        print(f"⚠️ No se pudo guardar archivo: {e}")
    
    return friends_data

# Ejecutar
if __name__ == "__main__":
    print("="*60)
    print("EPIC GAMES FRIENDS VIEWER")
    print("="*60)
    
    # Verificar credenciales
    if CLIENT_ID == "TU_CLIENT_ID_REAL" or CLIENT_SECRET == "TU_CLIENT_SECRET_REAL":
        print("\n❌ ERROR: Usas credenciales de ejemplo!")
        print("\n📋 PASOS PARA OBTENER TUS CREDENCIALES:")
        print("1. Ve a: https://dev.epicgames.com/portal/")
        print("2. Inicia sesión con tu cuenta Epic")
        print("3. Crea un nuevo producto o usa uno existente")
        print("4. Ve a 'Clients' → 'Create Client'")
        print("5. Configura:")
        print("   - Type: Confidential")
        print("   - Redirect URI: http://localhost:5000/callback")
        print("6. Copia Client ID y Client Secret")
        print("7. Pégales en este código")
    else:
        friends = get_friends_list()
        if friends:
            print("\n✨ ¡Proceso completado!")
            input("\nPresiona Enter para salir...")