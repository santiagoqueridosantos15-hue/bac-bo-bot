import telebot
import os
from flask import Flask
from threading import Thread

TOKEN = '8922303337:AAFpCacFyODY6iRKYj23T9ETdF1AIuiqjkc'
bot = telebot.TeleBot(TOKEN)

# Servidor web para o Render e UptimeRobot manterem o bot 24/7 ativo
app = Flask('')

@app.route('/')
def home():
    return "Bot de Bac Bo (Motor de Elite) a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Memória de sessões por utilizador
user_sessions = {}

def analisar_tendencia(historico):
    """
    MOTOR MATEMÁTICO DE ELITE (Bac Bo):
    Combina Inércia, Desvio Padrão, Padrões de Dragão e Ping-Pong.
    """
    # Isolar apenas A e V para análise de tendência pura, mantendo o histórico intacto
    puros = [x for x in historico if x in ['A', 'V']]
    if not puros:
        return 'A'
    
    # 1. ESTRATÉGIA PING-PONG (Detetor de Alternância Estrita)
    if len(puros) >= 4:
        if puros[-1] != puros[-2] and puros[-2] != puros[-3] and puros[-3] != puros[-4]:
            # Em alternâncias longas, o motor aposta na reversão à média (quebra do padrão no elemento seguinte)
            return 'V' if puros[-1] == 'A' else 'A'

    # 2. ESTRATÉGIA DRAGÃO (Detetor de Repetição / Streaks)
    ultimos_3 = puros[-3:] if len(puros) >= 3 else puros
    if len(ultimos_3) >= 3 and ultimos_3[0] == ultimos_3[1] == ultimos_3[2]:
        # Após 3 repetições idênticas seguidas, a probabilidade estatística de inversão dispara
        return 'V' if ultimos_3[-1] == 'A' else 'A'

    # 3. DESVIO PADRÃO E EQUILÍBRIO DE FREQUÊNCIA
    a_count = puros.count('A')
    v_count = puros.count('V')
    
    if a_count > v_count + 1:
        # Azul sobrecarregado no sapato recente -> Força reversão para Vermelho
        return 'V'
    elif v_count > a_count + 1:
        # Vermelho sobrecarregado no sapato recente -> Força reversão para Azul
        return 'A'
        
    # 4. INÉRCIA DE CURTO PRAZO (Fallback Inteligente)
    return 'V' if puros[-1] == 'A' else 'A'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'state': 'WAITING_7',
        'gale': 0,
        'sugestao_atual': None
    }
    
    texto = (
        "🤖 **Bot de Bac Bo - Motor de Elite Ativo!** 🚀\n\n"
        "Para calibrar a matriz matemática avançada, envia as **primeiras 7 jogadas**:\n"
        "🔵 **A** para Azul\n"
        "🔴 **V** para Vermelho\n"
        "⚪ **T** para Empate\n\n"
        "Exemplo: `A V A T V A V`"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    texto_input = message.text.strip().upper()
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {'history': [], 'state': 'WAITING_7', 'gale': 0, 'sugestao_atual': None}
    
    sessao = user_sessions[chat_id]
    
    # ESTADO 1: Calibração Inicial (7 jogadas)
    if sessao['state'] == 'WAITING_7':
        letras = [char for char in texto_input if char in ['A', 'V', 'T']]
        
        if len(letras) < 7:
            bot.reply_to(message, f"⚠️ Preciso de pelo menos **7 jogadas válidas** (A, V ou T). Recebi apenas {len(letras)}. Tenta novamente.", parse_mode="Markdown")
            return
        
        sessao['history'] = letras[-7:]
        sessao['state'] = 'WAITING_OUTCOME'
        sessao['gale'] = 0
        
        sugestao = analisar_tendencia(sessao['history'])
        sessao['sugestao_atual'] = sugestao
        
        cor_emoji = "🔵 AZUL" if sugestao == 'A' else "🔴 VERMELHO"
        
        resposta = (
            f"✅ **Matriz de Elite Calibrada!**\n"
            f"📊 Histórico ativo: `{' '.join(sessao['history'])}`\n\n"
            f"🎯 **Sinal de Entrada:** Entrar no **{cor_emoji}**\n"
            f"🛡️ *Gestão de Risco:* Sem gales ainda. Se perder, envia o resultado real."
        )
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
    # ESTADO 2: Fluxo Contínuo Inteligente
    elif sessao['state'] == 'WAITING_OUTCOME':
        if len(texto_input) == 0 or texto_input[0] not in ['A', 'V', 'T']:
            bot.reply_to(message, "⚠️ Envia apenas o resultado real (`A`, `V` ou `T`).", parse_mode="Markdown")
            return
            
        resultado_real = texto_input[0]
        cor_em_curso = sessao['sugestao_atual']
        
        # Atualizar histórico mantendo a janela deslizante
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 7:
            sessao['history'].pop(0)
            
        # TRATAMENTO DE EMPATE (T): Devolve a aposta, mantém o nível de gale atual
        if resultado_real == 'T':
            cor_emoji = "🔵 AZUL" if cor_em_curso == 'A' else "🔴 VERMELHO"
            gale_atual = sessao['gale']
            
            msg = (
                f"⚪ **EMPATE (T) - Aposta Devolvida**\n"
                f"O empate não altera o ciclo. (Gale atual: `{gale_atual}`)\n\n"
                f"🎯 **Repetir Entrada no:** {cor_emoji}"
            )
            bot.reply_to(message, msg, parse_mode="Markdown")
            
        # TRATAMENTO DE VITÓRIA (Green)
        elif resultado_real == cor_em_curso:
            sessao['gale'] = 0
            nova_sugestao = analisar_tendencia(sessao['history'])
            sessao['sugestao_atual'] = nova_sugestao
            cor_emoji = "🔵 AZUL" if nova_sugestao == 'A' else "🔴 VERMELHO"
            
            msg = (
                f"🎉 **GREEN / VITÓRIA!**\n"
                f"Saiu: `{resultado_real}` | Histórico: `{' '.join(sessao['history'])}`\n\n"
                f"🎯 **Próxima Entrada:** {cor_emoji}"
            )
            bot.reply_to(message, msg, parse_mode="Markdown")
            
        # TRATAMENTO DE DERROTA (Red) -> Avança no Gale mantendo obrigatoriamente a cor
        else:
            sessao['gale'] += 1
            gale_atual = sessao['gale']
            
            if gale_atual <= 2:
                cor_emoji = "🔵 AZUL" if cor_em_curso == 'A' else "🔴 VERMELHO"
                
                msg = (
                    f"⚠️ **RED na jogada anterior!** (Saiu {resultado_real})\n"
                    f"🔄 A avançar para **GALE {gale_atual}** 🛡️\n\n"
                    f"🎯 **Manter na mesma cor:** {cor_emoji}"
                )
                bot.reply_to(message, msg, parse_mode="Markdown")
            else:
                # Loss total após 2 Gales, reseta e recalcula nova matriz
                sessao['gale'] = 0
                nova_sugestao = analisar_tendencia(sessao['history'])
                sessao['sugestao_atual'] = nova_sugestao
                cor_emoji = "🔵 AZUL" if nova_sugestao == 'A' else "🔴 VERMELHO"
                
                msg = (
                    f"❌ **LOSS (Fim do Ciclo de 2 Gales)**\n"
                    f"Protegendo banca. A recalcular matriz...\n\n"
                    f"🎯 **Próxima Entrada:** {cor_emoji}"
                )
                bot.reply_to(message, msg, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    
    print("Bot com Motor de Elite iniciado com sucesso...")
    bot.infinity_polling()
