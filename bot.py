import telebot
import os
from flask import Flask
from threading import Thread

# Configuração do Bot de Telegram
TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

# Servidor Web integrado para manter o bot ativo 24/7 (Render / UptimeRobot)
app = Flask('')

@app.route('/')
def home():
    return "Bot Bac Bo 'Master Elite Blindado' (Com Travão Anti-Bait) a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões de múltiplos utilizadores em tempo real
user_sessions = {}

def motor_universal_blindado(historico):
    """
    MOTOR ESTATÍSTICO UNIVERSAL BLINDADO (COM TRAVÃO ANTI-BAIT):
    - Regra de Ouro: Trava e corta o sinal ao atingir 4 repetições de dragão (evita o bait da quebra na 5ª).
    - Mantém o ping-pong, desvio padrão e restantes filtros intocados.
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige um histórico encorpado mínimo para garantir estabilidade analítica
    if len(puros) < 10:
        return None
    
    # --- TRAVÃO ANTI-BAIT (EVITAR O FIM DO DRAGÃO) ---
    # Se uma cor já repetiu 4 vezes seguidas (ex: A-A-A-A), NÃO entramos na 5ª para não cair no engodo da casa!
    if len(puros) >= 4 and puros[-1] == puros[-2] == puros[-3] == puros[-4]:
        return None # Silêncio absoluto: recusa-se a entrar no esticanço do dragão

    # --- 1. TENDÊNCIA CONTROLADA DE SÉRIE (Até 3 repetições limpas) ---
    if puros[-1] == puros[-2] == puros[-3]:
        return puros[-1]
    
    # --- 2. PING-PONG PERFEITO (Alternância Cirúrgica) ---
    if (puros[-1] != puros[-2] and 
        puros[-2] != puros[-3] and 
        puros[-3] != puros[-4] and 
        puros[-4] != puros[-5]):
        return 'V' if puros[-1] == 'A' else 'A'

    # --- 3. PING-PONG DUPLO / PADRÃO DE BLOCOS (A-A-V-V ou V-V-A-A) ---
    if len(puros) >= 6:
        if puros[-1] == puros[-2] and puros[-3] == puros[-4] and puros[-1] != puros[-3]:
            return puros[-1]

    # --- 4. DESVIO PADRÃO SEVERO / EQUILÍBRIO DE SAPATO ---
    ultimas_dez = puros[-10:]
    total_a = ultimas_dez.count('A')
    total_v = ultimas_dez.count('V')
    
    if total_a >= 8: # Desvio massivo de Azul -> Correção para Vermelho
        return 'V'
    elif total_v >= 8: # Desvio massivo de Vermelho -> Correção para Azul
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
        "🤖 **BAC BO - MASTER ELITE BLINDADO (Com Travão Anti-Bait)** 🏆🔥💎\n\n"
        "• *Travão anti-dragão cego ativado (corta na 4ª repetição)*\n"
        "• *Gale controlado (G2 máximo) + Proteção obrigatória no Empate (T)*\n\n"
        "📜 **Envia o fluxo de resultados do sapato para começar (ex: `A V V T A A V A...`)!**"
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
        "📊 **Relatório de Desempenho (Anti-Bait):** 📈\n\n"
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
                    f"Aposta principal devolvida pela mesa. A aguardar nova oportunidade cirúrgica...", 
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
                    f"Saiu `{resultado_real}` com precisão matemática absoluta!", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                if sessao['fase_gale'] == 0:
                    sessao['fase_gale'] = 1 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(
                        message, 
                        f"⚠️ **Loss na Entrada Principal (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 1 (G1) OBRIGATÓRIO** 🚨\n"
                        f"👉 **Entrar no {cor_nome} + Proteger no T**", 
                        parse_mode="Markdown"
                    )
                    continue
                elif sessao['fase_gale'] == 1:
                    sessao['fase_gale'] = 2 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(
                        message, 
                        f"⚠️ **Loss no Gale 1 (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 2 (G2 - ÚLTIMO NÍVEL) OBRIGATÓRIO** 🚨\n"
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
                        f"❌ **LOSS FINAL (Ciclo G2 Esgotado - Saiu {resultado_real})**\n"
                        f"🛑 Silêncio total no canal. A proteger rigorosamente a banca contra sapatos atípicos...", 
                        parse_mode="Markdown"
                    )
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = motor_universal_blindado(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🛡️ **Mesa em Observação Rigorosa** ({len(sessao['history'])} rondas analisadas)\n"
                f"🚫 *Mercado com ruído ou zona de dragão esticado detetada. Travão anti-bait ativo...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🎲 **DADOS MASTER ELITE (ANTI-BAIT)** 🎲\n"
                f"🎯 **OPORTUNIDADE SEGURA ENCONTRADA!**\n"
                f"👉 **Entrar no {cor_nome} + Proteger no T**"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
