#!/usr/bin/env python3
"""
WaterParty — Send Email Campaign to Telegram
Usage: python marketing/send-to-telegram.py
Requires: python-dotenv (pip install python-dotenv)
          TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file
"""

import os
import sys
import json
import urllib.request
import urllib.error

# Try to load .env file
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(dotenv_path)
except ImportError:
    print("Aviso: python-dotenv nao instalado. Usando variaveis de ambiente diretamente.")
    print("       Instale com: pip install python-dotenv")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

if not TOKEN:
    print("Erro: TELEGRAM_BOT_TOKEN nao definido.")
    print("      Adicione ao arquivo .env ou exporte como variavel de ambiente.")
    sys.exit(1)

if not CHAT_ID:
    print("Erro: TELEGRAM_CHAT_ID nao definido.")
    print("      Adicione ao arquivo .env ou exporte como variavel de ambiente.")
    print("")
    print("      Para encontrar seu CHAT_ID:")
    print("      1. Envie qualquer mensagem para o seu bot no Telegram")
    print("      2. Execute: curl -s https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates")
    print("      3. Procure por 'chat': {'id': SEU_NUMERO_AQUI} na resposta")
    sys.exit(1)

# ─── Email Content ───────────────────────────────────────────────────────────

contact_list = "contact@monashees.com, contato@domo.vc, info@canary.com.br, biz@cesar.org.br"

email_monashees = """EMAIL 1 — Monashees (VC - English)
To: contact@monashees.com
Subject: WaterParty — Tinder for parties, launching in Recife

Hi Monashees team,

I'm reaching out from Water Enterprises (Stellarium Foundation). We built WaterParty — a Tinder-style app for discovering parties and events, with integrated payments (tipping + crowdfunding) and auto-currency detection via GPS.

Why it matters: The global nightlife market is $150B+. No app combines discovery + chat + payments in one place. We do.

Traction: Production-ready MVP (React 19, Bun, Turso, Stripe). Cross-platform (iOS + Android). Multi-currency GPS detection. WebSocket real-time.

Launch strategy: Recife first (4M pop, 100K+ students, Porto Digital). Prove density, expand city-by-city.

The ask: Raising $250K-$500K pre-seed to acquire our first 25K users and expand to new cities.

Attached: pitch deck + exec summary. Would love 15 min to show the demo.

Best,
John Victor
Water Enterprises / Stellarium Foundation
water.enterprises.org@gmail.com"""

email_domo = """EMAIL 2 — DOMO.VC (VC - English)
To: contato@domo.vc
Subject: WaterParty — Tinder for parties, launching in Recife

Hi DOMO team,

I'm reaching out from Water Enterprises. We built WaterParty — a Tinder-style app for discovering parties and events, with integrated payments and auto-currency detection.

The ask: Raising $250K-$500K pre-seed launching in Recife.

Attached: pitch deck + exec summary. Would love to show you the demo.

Best,
John Victor
water.enterprises.org@gmail.com"""

email_cesar = u"""EMAIL 3 — CESAR Recife (Local - Portugues)
To: biz@cesar.org.br
Assunto: WaterParty — App de descoberta de festas, lancando em Recife

Ola equipe CESAR,

Sou da Water Enterprises e estamos lancando o WaterParty em Recife — um app estilo Tinder para descobrir festas e eventos, com pagamentos integrados e deteccao automatica de moeda por GPS.

Tracao: MVP pronto (React 19, Bun, Turso, Stripe). iOS + Android.

Pedido: Captando R$ 1M-R$ 2M pre-seed.

Gostaria de saber mais sobre programas de incubacao com o CESAR Labs.

Abraco,
John Victor
water.enterprises.org@gmail.com"""

# Build the full message
message = f"""WATERPARTY EMAIL CAMPAIGN

CONTATOS PARA ENVIAR EMAIL:
{contact_list}

---

{email_monashees}

---

{email_domo}

---

{email_cesar}"""

# ─── Send via Telegram API ────────────────────────────────────────────────────

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

payload = {
    "chat_id": CHAT_ID,
    "text": message
}

# Encode as JSON to preserve UTF-8 properly
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

print("Enviando campanha de email do WaterParty para o Telegram...")
print(f"  Chat ID: {CHAT_ID}")
print(f"  Tamanho da mensagem: {len(message)} caracteres")
print()

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))
        if result.get("ok"):
            msg_id = result["result"]["message_id"]
            print("OK! Campanha enviada com sucesso!")
            print(f"  Message ID: {msg_id}")
        else:
            print("Falha ao enviar:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)
except urllib.error.HTTPError as e:
    print(f"Erro HTTP {e.code}:")
    print(e.read().decode("utf-8"))
    sys.exit(1)
except urllib.error.URLError as e:
    print(f"Erro de conexao: {e.reason}")
    sys.exit(1)
