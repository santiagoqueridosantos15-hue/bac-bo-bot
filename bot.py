import telebot
import os
from flask import Flask
from threading import Thread
from collections import Counter

TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot de Bac Bo (Elite Dynamic Flow) a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

user_sessions = {}

def motor_dinamico_assertivo(historico):
    """
    MOTOR DINÂMICO DE ALTA FREQUÊNCIA:
    - Analisa dragões, ping-pong, duplets e desvio de curto prazo de forma mais ágil.
    - Garante um fluxo constante de entradas sem perder a qualidade.
    """
    puros = [x for x in historico if x in ['A', 'V']]
    if len(puros) < 6:
        return None
    
    # 1. Filtro leve de exaustão (só pausa se a cor repetir 6 vezes seguidas)
    if len(puros) >= 6 and all(x == puros[-1] for x in puros[-6:]):
        return None

    # 2. TENDÊNCIA FORTE / DRAGÃO (Se os últimos 3 resultados são iguais)
    if puros[-1] == puros[-2] == puros[-3]:
        return puros[-1]
    
    # 3. PING-PONG PERFEITO (Alternância nos últimos 4)
    if puros[-1] != puros[-2] and puros[-2] != puros[-3] and puros[-3] != puros[-4]:
        return 'V' if puros[-1] == 'A' else 'A'

    # 4. PADRÃO DE DUPLETS / PARES GÊMEOS (ex: A A V V)
    if len(puros) >= 4 and puros[-1] == puros[-2] and puros[-3] == puros[-4] and puros[-1] != puros[-3]:
        return 'V' if puros[-1] == 'A' else 'A'

    # 5. LEI DE COMPENSAÇÃO RÁPIDA (Se houver desvio nas últimas 6 jogadas)
    ultimas_seis = puros[-6:]
    if ultimas_seis.count('A') >= 5:
        return 'V'
    elif ultimas_seis.count('V') >= 5:
        return 'A'

    return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'stats': {'wins': 0, 'losses': 0}
    }
    
    texto = (
        "🤖 **Bac Bo - Elite Dynamic (Zero Gale & Empate)** 🏆🔥\n\n"
        "Motor ajustado para dar mais entradas sem perder a assertividade.\n"
        "Envia o fluxo de resultados do sapato (ex: `A V V T A A V A...`) para começar a operar ativamente!"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def send_stats(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        bot.reply_to(message, "⚠️ Sem sessão ativa. Usa `/start` para iniciar.", parse_mode="Markdown")
        return
        
    sessao = user_sessions[chat_id]
    wins = sessao['stats']['wins']
    losses = sessao['stats']['losses']
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    texto = (
        "📊 **Estatísticas do Canal (Dynamic):** 📈\n\n"
        f"🎉 **Wins (Acertos):** `{wins}`\n"
        f"❌ **Losses (Erros):** `{losses}`\n"
        f"🎯 **Taxa de Assertividade:** `{win_rate:.2f}%`\n"
        f"📜 Histórico Ativo: `{len(sessao['history'])} rondas`"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    texto_input = message.text.strip().upper()
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            'history': [], 
            'stats': {'wins': 0, 'losses': 0}
        }
    
    sessao = user_sessions[chat_id]
    
    novas_letras = [char for char in texto_input if char in ['A', 'V', 'T']]
    if not novas_letras:
        bot.reply_to(message, "⚠️ Envia resultados válidos (`A`, `V` ou `T`).", parse_mode="Markdown")
        return
        
    # Acumular histórico no sapato (mantém as últimas 100 rondas)
    sessao['history'].extend(novas_letras)
    if len(sessao['history']) > 100:
        sessao['history'] = sessao['history'][-100:]
        
    # Executar motor dinâmico
    sugestao = motor_dinamico_assertivo(sessao['history'])
    
    if sugestao is None:
        resposta = (
            f"📊 **Mesa em Análise Dinâmica** ({len(sessao['history'])} rondas)\n"
            f"🛡️ *A aguardar padrão claro de curto prazo...*"
        )
    else:
        cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
        resposta = (
            f"🎲 **DADOS** 🎲\n"
            f"🚨 **ENTRADA CONFIRMADA**\n"
            f"👉 **APOSTAR NA COR:** {cor_nome}\n"
            f"🛡️ **PROTEGER NO EMPATE:** 🟡 (T)"
        )
        
    bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
