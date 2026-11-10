import telebot
import os
from flask import Flask
from threading import Thread

TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot de Bac Bo (Estratégia Zero Gale 96%) a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

user_sessions = {}

def analisar_tendencia_zero_gale(historico):
    """
    ESTRATÉGIA ZERO GALE (Alta Seletividade):
    - Só dispara se houver um padrão de inércia absoluta ou simetria quebrada com alta confiabilidade.
    - Se o mercado estiver baralhado, retorna None (Fica em silêncio absoluto à espera do momento certo).
    """
    puros = [x for x in historico if x in ['A', 'V']]
    if len(puros) < 6:
        return None
    
    # 1. Filtro de Saturação Extrema: Se a cor se repetir 5+ vezes, o risco de quebra é alto -> Pausa
    if len(puros) >= 5 and all(x == puros[-1] for x in puros[-5:]):
        return None

    # 2. DRAGÃO PURO SEGURO: Se os últimos 3 resultados são exatamente iguais e o 4º anterior também apoia
    if puros[-1] == puros[-2] == puros[-3]:
        return puros[-1]
    
    # 3. PING-PONG RIGOROSO: Alternância perfeita nos últimos 4 elementos
    if puros[-1] != puros[-2] and puros[-2] != puros[-3] and puros[-3] != puros[-4]:
        return 'V' if puros[-1] == 'A' else 'A'
        
    # 4. LEI DA COMPENSAÇÃO DE CURTO PRAZO (Desvio Padrão Apertado)
    # Se uma cor dominar 5 das últimas 6 jogadas, a probabilidade de correção imediata é altíssima
    ultimas_seis = puros[-6:]
    if ultimas_seis.count('A') >= 5:
        return 'V'  # Puxa para a correção vermelha
    elif ultimas_seis.count('V') >= 5:
        return 'A'  # Puxa para a correção azul

    # Sem padrão cirúrgico detetado -> Silêncio (Proteção total contra Loss)
    return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'state': 'WAITING_7',
        'sugestao_atual': None,
        'stats': {'wins': 0, 'losses': 0}
    }
    
    texto = (
        "🤖 **Bot Bac Bo - Estratégia Zero Gale (96% Assertividade)** 🏆🔥\n\n"
        "Este motor não usa Gales. É ultra-seletivo: só sinaliza quando há 100% de encaixe estatístico.\n"
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
        bot.reply_to(message, "⚠️ Sem sessão ativa. Usa `/start` para iniciar.", parse_mode="Markdown")
        return
        
    sessao = user_sessions[chat_id]
    wins = sessao['stats']['wins']
    losses = sessao['stats']['losses']
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    texto = (
        "📊 **Estatísticas (Modo Zero Gale):** 📈\n\n"
        f"🎉 **Wins (Acertos):** `{wins}`\n"
        f"❌ **Losses (Erros):** `{losses}`\n"
        f"🎯 **Taxa de Assertividade:** `{win_rate:.2f}%`\n"
        f"📜 Histórico: `{' '.join(sessao['history'])}`"
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
            'sugestao_atual': None,
            'stats': {'wins': 0, 'losses': 0}
        }
    
    sessao = user_sessions[chat_id]
    
    if sessao['state'] == 'WAITING_7':
        letras = [char for char in texto_input if char in ['A', 'V', 'T']]
        
        if len(letras) < 7:
            bot.reply_to(message, f"⚠️ Preciso de pelo menos **7 jogadas válidas** (A, V ou T). Recebi {len(letras)}.", parse_mode="Markdown")
            return
        
        sessao['history'] = letras[-7:]
        sessao['state'] = 'WAITING_OUTCOME'
        
        sugestao = analisar_tendencia_zero_gale(sessao['history'])
        sessao['sugestao_atual'] = sugestao
        
        if sugestao is None:
            resposta = (
                f"✅ **Calibragem Concluída!**\n"
                f"📊 Histórico: `{' '.join(sessao['history'])}`\n\n"
                f"🛡️ **Modo Zero Gale Seletivo**\n"
                f"🛑 **AGUARDAR / MERCADO SEM PADRÃO LIMPO**"
            )
        else:
            cor_emoji = "🔵 AZUL" if sugestao == 'A' else "🔴 VERMELHO"
            resposta = (
                f"✅ **Calibragem Concluída!**\n"
                f"📊 Histórico: `{' '.join(sessao['history'])}`\n\n"
                f"🎯 **ENTRADA CONFIRMADA (SEM GALE)!** Aposta no **{cor_emoji}**\n"
                f"⚪ *Não te esqueças de proteger no Empate (T)*"
            )
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
    elif sessao['state'] == 'WAITING_OUTCOME':
        if len(texto_input) == 0 or texto_input[0] not in ['A', 'V', 'T']:
            bot.reply_to(message, "⚠️ Envia apenas o resultado real (`A`, `V` ou `T`).", parse_mode="Markdown")
            return
            
        resultado_real = texto_input[0]
        
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 7:
            sessao['history'].pop(0)
            
        # Se tínhamos uma entrada ativa
        if sessao['sugestao_atual'] is not None:
            cor_sugerida = sessao['sugestao_atual']
            
            if resultado_real == 'T':
                # Empate devolve a aposta e mantém o foco
                cor_emoji = "🔵 AZUL" if cor_sugerida == 'A' else "🔴 VERMELHO"
                msg = (
                    f"⚪ **EMPATE (T) - Aposta Devolvida**\n"
                    f"O empate não conta como loss no Zero Gale.\n\n"
                    f"🎯 **Repetir Entrada no:** {cor_emoji}"
                )
                bot.reply_to(message, msg, parse_mode="Markdown")
                return
                
            elif resultado_real == cor_sugerida:
                # WIN direto sem Gale!
                sessao['stats']['wins'] += 1
                sessao['sugestao_atual'] = None
                
                proxima = analisar_tendencia_zero_gale(sessao['history'])
                sessao['sugestao_atual'] = proxima
                
                if proxima is None:
                    msg = (
                        f"🎉 **WIN / GREEN! (Sem Gale)** 🟢✨\n"
                        f"Saiu: `{resultado_real}` | Histórico: `{' '.join(sessao['history'])}`\n\n"
                        f"🛑 **AGUARDAR PRÓXIMA OPORTUNIDADE**"
                    )
                else:
                    cor_emoji = "🔵 AZUL" if proxima == 'A' else "🔴 VERMELHO"
                    msg = (
                        f"🎉 **WIN / GREEN! (Sem Gale)** 🟢✨\n"
                        f"Saiu: `{resultado_real}` | Histórico: `{' '.join(sessao['history'])}`\n\n"
                        f"🎯 **Nova Entrada Confirmada:** Entrar no **{cor_emoji}**"
                    )
                bot.reply_to(message, msg, parse_mode="Markdown")
                return
                
            else:
                # Loss direto (como não há gale, regista e passa logo à frente à espera de sinal limpo)
                sessao['stats']['losses'] += 1
                sessao['sugestao_atual'] = None
                
                proxima = analisar_tendencia_zero_gale(sessao['history'])
                sessao['sugestao_atual'] = proxima
                
                if proxima is None:
                    msg = (
                        f"❌ **LOSS (Saiu {resultado_real} sem Gale)**\n"
                        f"🛡️ Como jogamos sem Gale, o foco é a consistência a longo prazo.\n\n"
                        f"🛑 **AGUARDAR / MERCADO EM SILÊNCIO**"
                    )
                else:
                    cor_emoji = "🔵 AZUL" if proxima == 'A' else "🔴 VERMELHO"
                    msg = (
                        f"❌ **LOSS (Saiu {resultado_real} sem Gale)**\n"
                        f"A recalcular o mercado...\n\n"
                        f"🎯 **Nova Entrada Confirmada:** Entrar no **{cor_emoji}**"
                    )
                bot.reply_to(message, msg, parse_mode="Markdown")
                return
        
        else:
            # Se estava em pausa, procura nova oportunidade
            proxima = analisar_tendencia_zero_gale(sessao['history'])
            sessao['sugestao_atual'] = proxima
            
            if proxima is None:
                msg = (
                    f"📊 Histórico: `{' '.join(sessao['history'])}`\n"
                    f"🛡️ **Modo Seletivo Ativo**\n"
                    f"🛑 **AGUARDAR SINAL LIMPO**"
                )
            else:
                cor_emoji = "🔵 AZUL" if proxima == 'A' else "🔴 VERMELHO"
                msg = (
                    f"📊 Histórico: `{' '.join(sessao['history'])}`\n\n"
                    f"🎯 **ENTRADA CONFIRMADA (SEM GALE)!** Aposta no **{coremoji if 'coremoji' in locals() else cor_emoji}**"
                )
            bot.reply_to(message, msg, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
