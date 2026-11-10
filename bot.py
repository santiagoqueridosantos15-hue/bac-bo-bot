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
    return "Bot de Bac Bo (Motor Ultimate Profissional) a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Memória de sessões por utilizador com estatísticas avançadas
user_sessions = {}

def analisar_tendencia(historico):
    """
    MOTOR MATEMÁTICO ORIGINAL & ÁGIL (Bac Bo):
    - Analisa Dragão, Ping-Pong, Desvio Padrão e Limite de Exaustão nas últimas 7 rondas.
    - Retorna 'A', 'V' ou None (Pausa de Segurança).
    """
    puros = [x for x in historico if x in ['A', 'V']]
    if len(puros) < 6:
        return None
    
    # Filtro de Exaustão: Se a mesma cor se repetir 6+ vezes, o mercado está saturado -> Pausa
    if len(puros) >= 6 and all(x == puros[-1] for x in puros[-6:]):
        return None
    
    # 1. TENDÊNCIA FORTE / DRAGÃO: Se os últimos 3 resultados são iguais, segue a inércia
    if puros[-1] == puros[-2] == puros[-3]:
        return puros[-1]
    
    # 2. PING-PONG PERFEITO: Alternância estrita nos últimos 4 elementos
    if puros[-1] != puros[-2] and puros[-2] != puros[-3] and puros[-3] != puros[-4]:
        return 'V' if puros[-1] == 'A' else 'A'
        
    # 3. DESVIO PADRÃO / EQUILÍBRIO DE FREQUÊNCIA
    a_count = puros.count('A')
    v_count = puros.count('V')
    
    if a_count >= v_count + 2:
        return 'V'
    elif v_count >= a_count + 2:
        return 'A'
        
    # Mercado caótico ou volátil -> Pausa obrigatória para proteger banca
    return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'state': 'WAITING_7',
        'gale': 0,
        'sugestao_atual': None,
        'stats': {'wins': 0, 'losses': 0}
    }
    
    texto = (
        "🧠 **Bac Bo AI - Motor Profissional Ativo!** 🏆🔥\n\n"
        "Estrutura limpa e avançada com a matemática original de alta assertividade.\n"
        "Envia as **primeiras 7 jogadas** para calibrar:\n"
        "🔵 **A** para Azul\n"
        "🔴 **V** para Vermelho\n"
        "⚪ **T** para Empate\n\n"
        "Exemplo: `A V A T V A V`"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def send_stats(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        bot.reply_to(message, "⚠️ Ainda não tens nenhuma sessão ativa. Usa o comando /start para começar.", parse_mode="Markdown")
        return
        
    sessao = user_sessions[chat_id]
    wins = sessao['stats']['wins']
    losses = sessao['stats']['losses']
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    texto = (
        "📊 **Estatísticas da Sessão Atual:** 📈\n\n"
        f"🎉 **Greens (Vitórias):** `{wins}`\n"
        f"❌ **Losses (Derrotas):** `{losses}`\n"
        f"🎯 **Assertividade (Win Rate):** `{win_rate:.1f}%`\n"
        f"📜 Histórico Ativo: `{' '.join(sessao['history'])}`"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    texto_input = message.text.strip().upper()
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            'history': [], 
            'state': 'WAITING_7', 
            'gale': 0, 
            'sugestao_atual': None,
            'stats': {'wins': 0, 'losses': 0}
        }
    
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
        
        if sugestao is None:
            resposta = (
                f"✅ **Calibragem Concluída!**\n"
                f"📊 Histórico: `{' '.join(sessao['history'])}`\n\n"
                f"🟡 **MERCADO VOLÁTIL**\n"
                f"🛑 **AGUARDAR / NÃO OPERAR**"
            )
        else:
            cor_emoji = "🔵 AZUL" if sugestao == 'A' else "🔴 VERMELHO"
            resposta = (
                f"✅ **Calibragem Concluída!**\n"
                f"📊 Histórico: `{' '.join(sessao['history'])}`\n\n"
                f"🎯 **Oportunidade de Ouro!** Entrar no **{cor_emoji}**"
            )
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
    # ESTADO 2: Fluxo Contínuo Inteligente
    elif sessao['state'] == 'WAITING_OUTCOME':
        if len(texto_input) == 0 or texto_input[0] not in ['A', 'V', 'T']:
            bot.reply_to(message, "⚠️ Envia apenas o resultado real (`A`, `V` ou `T`).", parse_mode="Markdown")
            return
            
        resultado_real = texto_input[0]
        
        # Atualizar histórico mantendo a janela deslizante de 7
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 7:
            sessao['history'].pop(0)
            
        # Se temos uma aposta/ciclo ativo em curso
        if sessao['gale'] > 0 or sessao['sugestao_atual'] is not None:
            cor_em_curso = sessao['sugestao_atual']
            
            # TRATAMENTO DE EMPATE (T): Devolve a aposta, mantém o nível e repete
            if resultado_real == 'T':
                cor_emoji = "🔵 AZUL" if cor_em_curso == 'A' else "🔴 VERMELHO"
                gale_atual = sessao['gale']
                
                msg = (
                    f"⚪ **EMPATE (T) - Aposta Devolvida**\n"
                    f"O empate não altera o ciclo. (Gale atual: `{gale_atual}`)\n\n"
                    f"🎯 **Repetir Entrada no:** {cor_emoji}"
                )
                bot.reply_to(message, msg, parse_mode="Markdown")
                return
                
            # TRATAMENTO DE VITÓRIA (Green)
            elif resultado_real == cor_em_curso:
                sessao['stats']['wins'] += 1
                sessao['gale'] = 0
                sessao['sugestao_atual'] = None
                
                proxima = analisar_tendencia(sessao['history'])
                sessao['sugestao_atual'] = proxima
                
                if proxima is None:
                    msg = (
                        f"🎉 **GREEN / VITÓRIA!** 🟢\n"
                        f"Saiu: `{resultado_real}` | Histórico: `{' '.join(sessao['history'])}`\n\n"
                        f"🟡 **MERCADO EM PAUSA**\n"
                        f"🛑 **AGUARDAR / NÃO OPERAR**"
                    )
                else:
                    cor_emoji = "🔵 AZUL" if proxima == 'A' else "🔴 VERMELHO"
                    msg = (
                        f"🎉 **GREEN / VITÓRIA!** 🟢\n"
                        f"Saiu: `{resultado_real}` | Histórico: `{' '.join(sessao['history'])}`\n\n"
                        f"🎯 **Nova Oportunidade:** Entrar no **{cor_emoji}**"
                    )
                bot.reply_to(message, msg, parse_mode="Markdown")
                return
                
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
                    # Loss total após 2 Gales
                    sessao['stats']['losses'] += 1
                    sessao['gale'] = 0
                    sessao['sugestao_atual'] = None
                    
                    proxima = analisar_tendencia(sessao['history'])
                    sessao['sugestao_atual'] = proxima
                    
                    if proxima is None:
                        msg = (
                            f"❌ **LOSS (Fim do Ciclo de 2 Gales)**\n"
                            f"Protegendo banca rigorosamente.\n\n"
                            f"🟡 **MERCADO VOLÁTIL**\n"
                            f"🛑 **AGUARDAR / NÃO OPERAR**"
                        )
                    else:
                        cor_emoji = "🔵 AZUL" if proxima == 'A' else "🔴 VERMELHO"
                        msg = (
                            f"❌ **LOSS (Fim do Ciclo de 2 Gales)**\n"
                            f"Protegendo banca. A recalcular...\n\n"
                            f"🎯 **Nova Oportunidade:** Entrar no **{cor_emoji}**"
                        )
                    bot.reply_to(message, msg, parse_mode="Markdown")
                return
        
        else:
            # Se estava em pausa, avalia se já apareceu uma oportunidade de ouro
            proxima = analisar_tendencia(sessao['history'])
            sessao['sugestao_atual'] = proxima
            
            if proxima is None:
                msg = (
                    f"📊 Histórico atualizado: `{' '.join(sessao['history'])}`\n"
                    f"🟡 **Mercado ainda instável.**\n"
                    f"🛑 **AGUARDAR / NÃO OPERAR**"
                )
            else:
                cor_emoji = "🔵 AZUL" if proxima == 'A' else "🔴 VERMELHO"
                msg = (
                    f"📊 Histórico atualizado: `{' '.join(sessao['history'])}`\n\n"
                    f"🎯 **Oportunidade de Ouro Encontrada!** Entrar no **{cor_emoji}**"
                )
            bot.reply_to(message, msg, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
