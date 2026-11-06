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
        if jogador_total in [22, 20]:  # A,A ou 10,10
            return 'P' if jogador_total == 22 else 'S'
        elif jogador_total == 18:  # 9,9
            return 'S' if dealer_carta in [7, 10, 1] else 'P'
        elif jogador_total == 16:  # 8,8
            return 'P'
        elif jogador_total == 14:  # 7,7
            return 'P' if 2 <= dealer_carta <= 7 else 'H'
        elif jogador_total == 12:  # 6,6
            return 'P' if 2 <= dealer_carta <= 6 else 'H'
        elif jogador_total in [10, 8, 4]:  # 5,5 / 4,4 / 2,2
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
            return 'D' if 2 <= dealer_carta <= 6 else ('H' if dealer_carta in [9, 10, 1] else 'S')
        elif jogador_total == 17:
            return 'D' if 3 <= dealer_carta <= 6 else 'H'
        elif jogador_total in [15, 16]:
            return 'D' if 4 <= dealer_carta <= 6 else 'H'
        elif jogador_total in [13, 14]:
            return 'D' if 5 <= dealer_carta <= 6 else 'H'
        else:
            return 'H'
    else:
        # Mãos Duras (Hard Totals)
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
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'running_count': 0,
        'maos_jogadas': 0
    }
    
    texto = (
        "🤖 **Bot de Blackjack Master - Planbet Edition** 🃏🏆\n\n"
        "O sistema mais avançado do mundo ativado com **Estratégia Básica + Contagem Hi-Lo + Filtro de Pausa**.\n\n"
        "📝 **Como interagir com o bot:**\n"
        "Envia os dados no formato: `[Teu Total] [Carta Dealer] [S (se for soft) ou H (hard)]`\n"
        "Exemplo normal: `16 10`\n"
        "Exemplo Soft (com Ás): `18 6 S`\n\n"
        "📊 Podes também atualizar a contagem enviando cartas individuais (`2` a `10`, `A`): ex: `+5` ou `-1`."
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    texto_input = message.text.strip().upper()
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {'running_count': 0, 'maos_jogadas': 0}
        
    sessao = user_sessions[chat_id]
    
    # Atualização manual de contagem se o utilizador enviar cartas isoladas
    if texto_input in ['2', '3', '4', '5', '6']:
        sessao['running_count'] += 1
        bot.reply_to(message, f"📈 Carta baixa contabilizada (+1). Running Count atual: `{sessao['running_count']}`", parse_mode="Markdown")
        return
    elif texto_input in ['10', 'J', 'Q', 'K', 'A']:
        sessao['running_count'] -= 1
        bot.reply_to(message, f"📉 Carta alta contabilizada (-1). Running Count atual: `{sessao['running_count']}`", parse_mode="Markdown")
        return

    partes = texto_input.split()
    if len(partes) < 2:
        bot.reply_to(message, "⚠️ Formato inválido. Envia o teu total e a carta do dealer. Exemplo: `16 10`", parse_mode="Markdown")
        return
        
    try:
        jogador_total = int(partes[0])
        dealer_carta = int(partes[1])
        soft = len(partes) > 2 and partes[2] == 'S'
    except ValueError:
        bot.reply_to(message, "⚠️ Usa números válidos. Exemplo: `16 10`", parse_mode="Markdown")
        return
        
    # Filtro de Pausa / Contagem Crítica
    # Se a contagem estiver muito negativa, o sapato está desfavorável
    rc = sessao['running_count']
    if rc <= -3:
        aviso_contagem = "🟡 **MESA DESFAVORÁVEL (Contagem Baixa)**\n🛑 *Sugestão:* **AGUARDAR / APOSTAR MÍNIMO (0.20€)**"
    elif rc >= 3:
        aviso_contagem = "🟢 **MESA QUENTE! (Vantagem do Jogador)**\n💰 *Sugestão:* **Aumentar ligeiramente a aposta (Oportunidade de Ouro!)**"
    else:
        aviso_contagem = "⚪ **Mesa Neutra.** Gestão normal de 1 unidade (Min: 0.20€).[span_2](start_span)"[span_2](end_span)

    # Decisão da Estratégia Básica
    acao = calcular_estrategia_basica(jogador_total, dealer_carta, soft=soft)
    
    if acao == 'H':
        sinal = "📥 **PEDIR (HIT)** — Puxar carta com segurança matemática."
    elif acao == 'S':
        sinal = "🛑 **PARAR (STAND)** — Manter o total atual."
    elif acao == 'D':
        sinal = "💰 **DOBRAR (DOUBLE)** — A jogada de maior lucro estatístico!"
    elif acao == 'P':
        sinal = "✂️ **DIVIDIR (SPLIT)** — Separar o par obrigatoriamente."
    else:
        sinal = "🟡 **AGUARDAR / NÃO OPERAR**"
        
    resposta = (
        f"🃏 **Análise Profissional de Blackjack (Planbet)**[span_3](start_span)[span_3](end_span)\n"
        f"📊 A sua mão: `{jogador_total}` {'(Soft)' if soft else ''} | Dealer: `{dealer_carta}`\n\n"
        f"🎯 **Decisão Ótima:**\n{sinal}\n\n"
        f"-----------------------------------\n"
        f"{aviso_contagem}\n"
        f"🔢 *Running Count:* `{rc}`"
    )
    bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    
    print("Bot Master de Blackjack iniciado com sucesso na porta 10000...")
    bot.infinity_polling()
