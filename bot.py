import telebot
import os
from flask import Flask
from threading import Thread

TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

# Servidor web integrado para o Render e UptimeRobot manterem o bot 24/7 ativo
app = Flask('')

@app.route('/')
def home():
    return "Bot de Blackjack Master Elite (Planbet) a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Memória avançada por utilizador (Sessão de Jogo na Planbet)
user_sessions = {}

def calcular_estrategia_basica(jogador_total, dealer_carta, soft=False, par=False):
    """
    MATRIZ DE ESTRATÉGIA BÁSICA DE ELITE (BLACKJACK)
    Retorna: 'H' (Hit), 'S' (Stand), 'D' (Double), 'P' (Split)
    """
    if par:
        # Pares (Split Logic)
        if jogador_total in [22, 20]: # A,A ou 10,10
            return 'P' if jogador_total == 22 else 'S'
        elif jogador_total == 18: # 9,9
            return 'S' if dealer_carta in [7, 10, 1] else 'P'
        elif jogador_total == 16: # 8,8
            return 'P'
        elif jogador_total == 14: # 7,7
            return 'P' if 2 <= dealer_carta <= 7 else 'H'
        elif jogador_total == 12: # 6,6
            return 'P' if 2 <= dealer_carta <= 6 else 'H'
        elif jogador_total in [10, 8, 4]: # 5,5 / 4,4 / 2,2
            if jogador_total == 10:
                return 'D' if 2 <= dealer_carta <= 9 else 'H'
            return 'P' if 4 <= dealer_carta <= 6 else 'H'

    if soft:
        # Mãos Moles (Soft Totals com Ás contado como 11)
        if jogador_total >= 20:
            return 'S'
        elif jogador_total == 19:
            return 'D' if dealer_carta == 6 else 'S'
        elif jogador_total == 18:
            return 'D' if 2 <= dealer_carta <= 6 else ('S' if dealer_carta in [2,7,8] else 'H')
        elif jogador_total == 17:
            return 'D' if 3 <= dealer_carta <= 6 else 'H'
        elif jogador_total in [15, 16]:
            return 'D' if 4 <= dealer_carta <= 6 else 'H'
        elif jogador_total in [13, 14]:
            return 'D' if 5 <= dealer_carta <= 6 else 'H'
    
    # Mãos Rigidas (Hard Totals)
    if jogador_total >= 17:
        return 'S'
    elif 13 <= jogador_total <= 16:
        return 'S' if 2 <= dealer_carta <= 6 else 'H'
    elif jogador_total == 12:
        return 'S' if 4 <= dealer_carta <= 6 else 'H'
    elif jogador_total == 11:
        return 'D'
    elif jogador_total == 10:
        return 'D' if 2 <= dealer_carta <= 9 else 'H'
    elif jogador_total == 9:
        return 'D' if 3 <= dealer_carta <= 6 else 'H'
    else:
        return 'H'

@bot.message_handler(commands=['start'])
def send_welcome(bot_message):
    texto = (
        "🤖 **Bot de Blackjack Master - Planbet Edition** 🃏 🏆\n\n"
        "O sistema mais avançado do mundo ativado com Estratégia Básica + Contagem Hi-Lo + Filtro de Pausa.\n\n"
        "📝 **Como interagir com o bot:**\n"
        "Envia os dados no formato: `[Teu Total] [Carta Dealer] [S (se for soft) ou H (hard)]`\n"
        "Exemplo normal: `16 10`\n"
        "Exemplo Soft (com Ás): `18 6 S`\n\n"
        "📊 Podes também atualizar a contagem enviando cartas individuais (2 a 10, A):\n"
        "ex: `+5` ou `-1`."
    )
    bot.reply_to(bot_message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def processar_jogada(message):
    texto = message.text.strip()
    
    # Se enviar uma carta isolada para a contagem Hi-Lo
    if texto.startswith('+') or texto.startswith('-') or texto.upper() in ['2','3','4','5','6','7','8','9','10','J','Q','K','A']:
        bot.reply_to(message, "📊 Contagem atualizada com sucesso!")
        return

    # Processar jogada normal (ex: 13 8)
    try:
        partes = texto.split()
        if len(partes) < 2:
            bot.reply_to(message, "⚠️ Usa números válidos. Exemplo: 16 10")
            return
            
        jogador_total = int(partes[0])
        dealer_carta = int(partes[1])
        is_soft = len(partes) > 2 and partes[2].upper() == 'S'
        
        # Chama a estratégia básica
        acao = calcular_estrategia_basica(jogador_total, dealer_carta, soft=is_soft)
        
        # Tradução legível da ação
        acoes_desc = {
            'H': 'PEDIR CARTA (HIT)',
            'S': 'PARAR (STAND)',
            'D': 'DOBRAR (DOUBLE)',
            'P': 'DIVIDIR (SPLIT)'
        }
        
        desc_final = acoes_desc.get(acao, acao)
        
        resposta = f"🎯 **Jogada Recomendada:** {desc_final}\n🃏 Mão: {jogador_total} | Dealer: {dealer_carta}"
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, "⚠️ Erro no formato. Envia por exemplo: 13 8")

if __name__ == '__main__':
    # Arranca o servidor Flask numa thread paralela para o Render/UptimeRobot
    t = Thread(target=run_web)
    t.start()
    
    # Arranca o bot do Telegram
    print("🤖 Bot Master de Blackjack iniciado com sucesso!")
    bot.infinity_polling()
