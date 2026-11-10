import telebot
import os
from flask import Flask
from threading import Thread

TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot de Bac Bo (Motor Ultra-Seletivo) a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

user_sessions = {}

def motor_ultra_seletivo(historico):
    """
    MOTOR ULTRA-SELETIVO (ALTA EXIGÊNCIA):
    - Só dispara se houver um padrão limpo e forte.
    - Evita zonas de ruído e sapatos barulhentos para proteger a banca.
    """
    puros = [x for x in historico if x in ['A', 'V']]
    if len(puros) < 10:  
        return None
    
    if len(puros) >= 5 and all(x == puros[-1] for x in puros[-5:]):
        return None

    if puros[-1] == puros[-2] == puros[-3] == puros[-4]:
        return puros[-1]
    
    if (puros[-1] != puros[-2] and 
        puros[-2] != puros[-3] and 
        puros[-3] != puros[-4] and 
        puros[-4] != puros[-5]):
        return 'V' if puros[-1] == 'A' else 'A'

    ultimas_oito = puros[-8:]
    if ultimas_oito.count('A') >= 7:
        return 'V'
    elif ultimas_oito.count('V') >= 7:
        return 'A'

    return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'fase_gale': 0,
        'cor_alvo': None,
        'stats': {'wins': 0, 'losses': 0}
    }
    
    texto = (
        "🤖 **Bac Bo - Elite Ultra-Seletivo** 🏆🔥\n\n"
        "Motor reajustado para **zero ruído**. Só avança com padrões cristalinos.\n"
        "Envia o fluxo de resultados do sapato (ex: `A V V T A A V A...`)!"
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
        "📊 **Estatísticas do Canal (Seletivo):** 📈\n\n"
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
            'fase_gale': 0,
            'cor_alvo': None,
            'stats': {'wins': 0, 'losses': 0}
        }
    
    sessao = user_sessions[chat_id]
    
    novas_letras = [char for char in texto_input if char in ['A', 'V', 'T']]
    if not novas_letras:
        bot.reply_to(message, "⚠️ Envia resultados válidos (`A`, `V` ou `T`).", parse_mode="Markdown")
        return
        
    for resultado_real in novas_letras:
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 150:
            sessao['history'] = sessao['history'][-150:]
            
        if sessao['cor_alvo'] is not None:
            cor_esperada = sessao['cor_alvo']
            
            if resultado_real == 'T':
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(message, f"🟢 **WIN NO EMPATE (Proteção Coberta)** 🟡\n📊 Saiu T. A aguardar próxima oportunidade limpa...", parse_mode="Markdown")
                continue
                
            elif resultado_real == cor_esperada:
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(message, f"🎉 **WIN / GREEN!** 🟢✨\nSaiu `{resultado_real}` com rigor!", parse_mode="Markdown")
                continue
                
            else:
                if sessao['fase_gale'] == 0:
                    sessao['fase_gale'] = 1 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(message, 
                        f"⚠️ **Loss na Entrada Principal (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 1 (G1) OBRIGATÓRIO** 🚨\n"
                        f"👉 **APOSTAR NA COR:** {cor_nome} (Dobrar stake)\n"
                        f"🛡️ **PROTEGER NO EMPATE:** 🟡 (T)", 
                        parse_mode="Markdown"
                    )
                    continue
                else:
                    sessao['stats']['losses'] += 1
                    sessao['cor_alvo'] = None
                    sessao['fase_gale'] = 0
                    bot.reply_to(message, f"❌ **LOSS FINAL (G1 Não Respondeu - Saiu {resultado_real})**\n🛑 Silêncio no canal até aparecer padrão limpo...", parse_mode="Markdown")
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = motor_ultra_seletivo(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🛡️ **Mesa em Observação Rigorosa** ({len(sessao['history'])} rondas)\n"
                f"🚫 *Sem padrão seguro. A proteger a banca de entradas fracas...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🎲 **DADOS** 🎲\n"
                f"🎯 **OPORTUNIDADE DE ALTA CONVIÇÃO**\n"
                f"👉 **APOSTAR NA COR:** {cor_nome}\n"
                f"🛡️ **PROTEGER NO EMPATE:** 🟡 (T)"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
