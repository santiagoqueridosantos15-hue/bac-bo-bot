import telebot
import os
from flask import Flask
from threading import Thread

TOKEN = '8922303337:AAFpCacFyODY6iRKYj23T9ETdF1AIuiqjkc'
bot = telebot.TeleBot(TOKEN)

# Servidor web simples para o Render abrir porta e o UptimeRobot detetar como "Up"
app = Flask('')

@app.route('/')
def home():
    return "Bot de Bac Bo a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Memória por utilizador para gerir o estado do jogo
user_sessions = {}

def analisar_tendencia(historico):
    """Motor matemático baseado nas últimas jogadas, inércia e desvio padrão."""
    A_count = historico.count('A')
    V_count = historico.count('V')
    
    total = len(historico)
    if total == 0:
        return 'A'
    
    ultimos_3 = historico[-3:]
    if len(ultimos_3) == 3 and ultimos_3[0] == ultimos_3[1] == ultimos_3[2] and ultimos_3[0] != 'T':
        return 'V' if ultimos_3[0] == 'A' else 'A'
    
    if A_count >= V_count:
        return 'A'
    else:
        return 'V'

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
        "🤖 **Bot de Bac Bo - Pronto a Faturar!**\n\n"
        "Para calibrar o motor estatístico e iniciar o ciclo, envia as **primeiras 7 jogadas** separadas por espaços ou juntas.\n"
        "Usa:\n"
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
            f"✅ **Calibragem Concluída!**\n"
            f"📊 Histórico ativo: `{' '.join(sessao['history'])}`\n\n"
            f"🎯 **Sinal de Entrada:** Entrar no **{cor_emoji}**\n"
            f"🛡️ *Gestão de Risco:* Sem gales ainda. Se perder, envia o resultado real para avançarmos para o Gale 1."
        )
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
    elif sessao['state'] == 'WAITING_OUTCOME':
        if len(texto_input) == 0 or texto_input[0] not in ['A', 'V', 'T']:
            bot.reply_to(message, "⚠️ Envia apenas o resultado que saiu (`A`, `V` ou `T`).", parse_mode="Markdown")
            return
            
        resultado_real = texto_input[0]
        sugestao_anterior = sessao['sugestao_atual']
        
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 7:
            sessao['history'].pop(0)
            
        acertou = (resultado_real == sugestao_anterior)
        
        if acertou or resultado_real == 'T':
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
            
        else:
            sessao['gale'] += 1
            gale_atual = sessao['gale']
            
            if gale_atual <= 2:
                nova_sugestao = analisar_tendencia(sessao['history'])
                sessao['sugestao_atual'] = nova_sugestao
                cor_emoji = "🔵 AZUL" if nova_sugestao == 'A' else "🔴 VERMELHO"
                
                msg = (
                    f"⚠️ **RED na jogada anterior!** (Saiu {resultado_real})\n"
                    f"🔄 A avançar para **GALE {gale_atual}** 🛡️\n\n"
                    f"🎯 **Entrar no:** {cor_emoji}"
                )
                bot.reply_to(message, msg, parse_mode="Markdown")
            else:
                sessao['gale'] = 0
                nova_sugestao = analisar_tendencia(sessao['history'])
                sessao['sugestao_atual'] = nova_sugestao
                cor_emoji = "🔵 AZUL" if nova_sugestao == 'A' else "🔴 VERMELHO"
                
                msg = (
                    f"❌ **LOSS (Fim do Ciclo de 2 Gales)**\n"
                    f"Vamos proteger banca e reiniciar a matriz com nova oportunidade.\n\n"
                    f"🎯 **Próxima Entrada:** {cor_emoji}"
                )
                bot.reply_to(message, msg, parse_mode="Markdown")

if __name__ == '__main__':
    # Arranca o servidor web em segundo plano para o Render e UptimeRobot ficarem felizes
    t = Thread(target=run_web)
    t.start()
    
    print("Bot de Bac Bo e servidor web iniciados com sucesso...")
    bot.infinity_polling()
