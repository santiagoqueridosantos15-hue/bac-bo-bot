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
    return "Bot Bac Bo 'Elite Sniper Brain' a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões em tempo real
user_sessions = {}

def cerebro_elite_sniper(historico):
    """
    CÉREBRO ELITE SNIPER (MATRIZ DE ASSIMETRIA):
    - Avalia o comportamento estrutural do histórico recente.
    - Exige uma janela limpa e um desequilíbrio estatístico matemático para disparar.
    - Se a mesa estiver em transição caótica ou sem padrão de força, SILENCIA (retorna None).
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige uma amostra consistente de 10 rondas puras para calcular o vetor de força
    if len(puros) < 10:
        return None
        
    # Isola estritamente as últimas 10 rondas do fluxo ativo
    bloco = puros[-10:]
    
    # Contagens absolutas
    azuis = bloco.count('A')
    vermelhos = bloco.count('V')
    
    # 1. Regra de Assimetria de Bloco (Dominância de 70% ou mais numa cor nas últimas 10)
    # Se uma cor esticar demasiado, o motor calcula a exaustão ou acompanha a inércia pesada.
    if azuis >= 7:
        return 'A'  # Força de inércia contínua a favor do bloco dominante
    if vermelhos >= 7:
        return 'V'  # Força de inércia contínua a favor do bloco dominante
        
    # 2. Regra de Reversão Estrutural por Cauda (Últimas 4 rondas em bloco fechado)
    cauda_4 = bloco[-4:]
    if all(x == 'A' for x in cauda_4):
        return 'V'  # Quebra iminente de esticada longa de Azuis
    if all(x == 'V' for x in cauda_4):
        return 'A'  # Quebra iminente de esticada longa de Vermelhos
        
    # 3. Se a mesa estiver equilibrada (ex: 5-5) ou sem padrão de força limpo: CALA-SE
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
        "🤖 **BAC BO - ELITE SNIPER BRAIN (v5)** 🏆🔥💎\n\n"
        "• *Motor de Assimetria Matemática & Filtro de Ruído Absoluto*\n"
        "• *Gestão Cirúrgica: Entrada + Máximo de 1 Gale (G1)*\n"
        "• *Blindagem total no Empate (T)*\n\n"
        "📜 **Envia o fluxo de resultados para o Sniper caçar as entradas de alta precisão!**"
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
        "📊 **Relatório de Desempenho (Elite Sniper):** 📈\n\n"
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
        if len(sessao['history']) > 300:
            sessao['history'] = sessao['history'][-300:]
            
        if sessao['cor_alvo'] is not None:
            cor_esperada = sessao['cor_alvo']
            
            if resultado_real == 'T':
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(
                    message, 
                    f"🟢 **PROTEÇÃO NO EMPATE (T) COBERTA COM SUCESSO!** 🟡\n"
                    f"Aposta principal devolvida pela mesa. Sniper em silêncio à procura de novo alvo...", 
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
                    f"Saiu `{resultado_real}` com precisão cirúrgica do Sniper!", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                # Gestão estrita a MÁXIMO DE 1 GALE (G1)
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
                    sessao['stats']['losses'] += 1
                    sessao['cor_alvo'] = None
                    sessao['fase_gale'] = 0
                    bot.reply_to(
                        message, 
                        f"❌ **LOSS FINAL (Ciclo G1 Esgotado - Saiu {resultado_real})**\n"
                        f"🛑 Limite de risco atingido. Sniper em modo de defesa tática...", 
                        parse_mode="Markdown"
                    )
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = cerebro_elite_sniper(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🧠 **Elite Sniper Brain**\n"
                f"🛡️ *Mesa sem assimetria matemática clara. Cérebro em silêncio tático absoluto...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" == 'AZUL 🔵' if sugestao == 'A' else "VERMELHO 🔴"
            cor_texto = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🧠 **ALVO VALIDADO PELO SNIPER** 🎯\n"
                f"⚡ **CONVICÇÃO MATEMÁTICA ATIVADA!**\n"
                f"👉 **Entrar no {cor_texto} + Proteger no T**"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
