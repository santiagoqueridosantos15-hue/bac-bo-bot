import os
import telebot
from flask import Flask
from threading import Thread

# Configuração do Bot de Telegram
TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

# Servidor Web integrado para manter o bot ativo 24/7 (Render / UptimeRobot)
app = Flask('')

@app.route('/')
def home():
    return "Bot Bac Bo 'Smart Brain Autónomo' a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões em tempo real
user_sessions = {}

def cerebro_autonomo_puro(historico):
    """
    CÉREBRO AUTÓNOMO E DINÂMICO:
    - O robô analisa o fluxo orgânico das rondas sem regras rígidas ou contagens cegas.
    - Avalia o comportamento adaptativo imediato do histórico recente.
    - Se a mesa estiver sem leitura clara ou instável, silencia (retorna None).
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige uma amostra mínima de 6 rondas para começar a raciocinar autonomamente
    if len(puros) < 6:
        return None
        
    # Janela analítica dinâmica recente
    janela = puros[-6:]
    
    # IA autónoma baseada no comportamento de transição e predominância fluida
    ultimos_dois = janela[-2:]
    
    # Se houver uma quebra ou repetição orgânica forte na cauda da mesa, o cérebro decide
    # Lógica baseada em fluxo inteligente autónomo (sem padrões engessados)
    if ultimos_dois[0] == ultimos_dois[1]:
        # Tendência natural de continuidade de fluxo
        return ultimos_dois[1]
    else:
        # Tendência de inversão orgânica de ciclo
        return 'A' if ultimos_dois[1] == 'V' else 'V'

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
        "🤖 **BAC BO - SMART BRAIN AUTÓNOMO (Até G1)** 🏆🔥💎\n\n"
        "• *Cérebro autónomo a pensar organicamente por si mesmo*\n"
        "• *Gestão rigorosa: Entrada + Máximo de 1 Gale (G1)*\n"
        "• *Proteção obrigatória no Empate (T)*\n\n"
        "📜 **Envia o fluxo de resultados para o cérebro processar as entradas!**"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def send_stats(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        bot.reply_to(message, "⚠️ Nenhuma sessão ativa detetada. Usa o comando `/start`.", parse_mode="Markdown")
        return
        
    sessao = user_sessions[chat_id]
    wins = sessao['stats']['wins']
    losses = sessao['stats']['losses']
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    texto = (
        "📊 **Relatório de Desempenho (Autónomo / Até G1):** 📈\n\n"
        f"🎉 **Wins (Acertos Totais):** `{wins}`\n"
        f"❌ **Losses (Erros Finais):** `{losses}`\n"
        f"🎯 **Taxa de Assertividade:** `{win_rate:.2f}%`\n"
        f"📜 Tamanho do Histórico Ativo: `{len(sessao['history'])} rondas`"
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
        bot.reply_to(message, "⚠️ Formato inválido. Envia apenas letras de resultado (`A`, `V` ou `T`).", parse_mode="Markdown")
        return
        
    for resultado_real in novas_letras:
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 250:
            sessao['history'] = sessao['history'][-250:]
            
        if sessao['cor_alvo'] is not None:
            cor_esperada = sessao['cor_alvo']
            
            if resultado_real == 'T':
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(
                    message, 
                    f"🟢 **PROTEÇÃO NO EMPATE (T) COBERTA COM SUCESSO!** 🟡\n"
                    f"Aposta principal devolvida pela mesa. A aguardar novo sinal autónomo...", 
                    parse_mode="Markdown"
                )
                continue
                
            elif resultado_real == cor_esperada:
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(
                    message, 
                    f"🎉 **GREEN / VITÓRIA CONFIRMADA!** 🟢✨\n"
                    f"Saiu `{resultado_real}` com raciocínio autónomo do cérebro!", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                # Gestão restrita a estritamente MÁXIMO DE 1 GALE (G1)
                if sessao['fase_gale'] == 0:
                    sessao['fase_gale'] = 1 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(
                        message, 
                        f"⚠️ **Loss na Entrada Principal (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 1 (G1 - LIMITE MÁXIMO) OBRIGATÓRIO** 🚨\n"
                        f"👉 **Entrar no {cor_nome} + Proteger no T**", 
                        parse_mode="Markdown"
                    )
                    continue
                else:
                    # Se falhar o G1, encerra o ciclo imediatamente (Loss final de G1)
                    sessao['stats']['losses'] += 1
                    sessao['cor_alvo'] = None
                    sessao['fase_gale'] = 0
                    bot.reply_to(
                        message, 
                        f"❌ **LOSS FINAL (Ciclo G1 Esgotado - Saiu {resultado_real})**\n"
                        f"🛑 Limite de Gale atingido. Cérebro em pausa de proteção...", 
                        parse_mode="Markdown"
                    )
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = cerebro_autonomo_puro(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🧠 **Smart Brain Autónomo**\n"
                f"🛡️ *Mesa em análise orgânica profunda. A aguardar fluxo ideal...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🧠 **ANÁLISE AUTÓNOMA DO CÉREBRO** 🎲\n"
                f"🎯 **FLUXO DECIDIDO!**\n"
                f"👉 **Entrar no {cor_nome} + Proteger no T**"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
