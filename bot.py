import telebot
import os
from flask import Flask
from threading import Thread

TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot de Bac Bo (Motor + Gale Controlado) a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

user_sessions = {}

def motor_dinamico_assertivo(historico):
    puros = [x for x in historico if x in ['A', 'V']]
    if len(puros) < 6:
        return None
    
    if len(puros) >= 6 and all(x == puros[-1] for x in puros[-6:]):
        return None

    if puros[-1] == puros[-2] == puros[-3]:
        return puros[-1]
    
    if puros[-1] != puros[-2] and puros[-2] != puros[-3] and puros[-3] != puros[-4]:
        return 'V' if puros[-1] == 'A' else 'A'

    if len(puros) >= 4 and puros[-1] == puros[-2] and puros[-3] == puros[-4] and puros[-1] != puros[-3]:
        return 'V' if puros[-1] == 'A' else 'A'

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
        'fase_gale': 0, # 0 = Entrada Normal, 1 = G1 (Gale 1)
        'cor_alvo': None,
        'stats': {'wins': 0, 'losses': 0}
    }
    
    texto = (
        "🤖 **Bac Bo - Elite com Gale Controlado & Empate** 🏆🔥\n\n"
        "Motor matemático ativo + Estrutura de recuperação (G1).\n"
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
        "📊 **Estatísticas do Canal (Com Gale):** 📈\n\n"
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
        
    # Vamos processar ronda a ronda para validar o Gale caso já estejamos em jogo ativo
    for resultado_real in novas_letras:
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 100:
            sessao['history'] = sessao['history'][-100:]
            
        # Se estivermos à espera do resultado de uma entrada anterior ou G1
        if sessao['cor_alvo'] is not None:
            cor_esperada = sessao['cor_alvo']
            
            # Se sair Empate (T), protege
            if resultado_real == 'T':
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(message, f"🟢 **WIN NO EMPATE (Proteção Coberta)** 🟡\n📊 Saiu T. Vamos à próxima!", parse_mode="Markdown")
                continue
                
            elif resultado_real == cor_esperada:
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(message, f"🎉 **WIN / GREEN!** 🟢✨\nSaiu `{resultado_real}` com sucesso!", parse_mode="Markdown")
                continue
                
            else:
                # Falhou a primeira (Normal). Vamos testar o Gale 1 (G1)?
                if sessao['fase_gale'] == 0:
                    sessao['fase_gale'] = 1 # Passa para G1 na mesma cor
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(message, 
                        f"⚠️ **LOSS na Entrada Principal (Saiu {resultado_real})**\n\n"
                        f"🔄 **ENTRADA DE RECUPERAÇÃO: GALE 1 (G1)** 🚨\n"
                        f"👉 **APOSTAR NA COR:** {cor_nome} (Dobrar a mão)\n"
                        f"🛡️ **PROTEGER NO EMPATE:** 🟡 (T)", 
                        parse_mode="Markdown"
                    )
                    continue
                else:
                    # Se falhou o G1, dá Loss definitivo e reseta
                    sessao['stats']['losses'] += 1
                    sessao['cor_alvo'] = None
                    sessao['fase_gale'] = 0
                    bot.reply_to(message, f"❌ **LOSS FINAL (G1 Não Pagou - Saiu {resultado_real})**\n🛑 A aguardar novo sinal limpo...", parse_mode="Markdown")
                    continue

    # Se não houver nenhuma jogada pendente de Gale, o motor procura uma nova oportunidade
    if sessao['cor_alvo'] is None:
        sugestao = motor_dinamico_assertivo(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"📊 **Mesa em Análise** ({len(sessao['history'])} rondas)\n"
                f"🛡️ *A aguardar padrão ideal para nova entrada...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🎲 **DADOS** 🎲\n"
                f"🚨 **ENTRADA CONFIRMADA (Sinal Principal)**\n"
                f"👉 **APOSTAR NA COR:** {cor_nome}\n"
                f"🛡️ **PROTEGER NO EMPATE:** 🟡 (T)"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
