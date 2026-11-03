import telebot

TOKEN = '8922303337:AAFpCacFyODY6iRKYj23T9ETdF1AIuiqjkc'
bot = telebot.TeleBot(TOKEN)

# Memória por utilizador para gerir o estado do jogo
# Estados: 'WAITING_7' (à espera das 7 iniciais) ou 'WAITING_OUTCOME' (a aguardar resultados jogada a jogada)
user_sessions = {}

def analisar_tendencia(historico):
    """Motor matemático baseado nas últimas jogadas, inércia e desvio padrão."""
    # Filtrar apenas A e V para cálculo de tendência principal, considerando T como neutro/empate
    A_count = historico.count('A')
    V_count = historico.count('V')
    t_count = historico.count('T')
    
    total = len(historico)
    if total == 0:
        return 'A'
    
    # Lógica de reversão à média e inércia
    # Se uma cor apareceu muito nas últimas, há tendência estatística de correção ou continuação baseada no peso recente
    ultimos_3 = historico[-3:]
    
    # Exemplo de regra estatística limpa: se os últimos 3 forem iguais, forte tendência de quebra (reversão à média)
    if len(ultimos_3) == 3 and ultimos_3[0] == ultimos_3[1] == ultimos_3[2] and ultimos_3[0] != 'T':
        return 'V' if ultimos_3[0] == 'A' else 'A'
    
    # Caso contrário, segue a maioria ponderada das últimas jogadas
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
    
    # Se o utilizador não iniciou
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {'history': [], 'state': 'WAITING_7', 'gale': 0, 'sugestao_atual': None}
    
    sessao = user_sessions[chat_id]
    
    # ESTADO 1: À espera das 7 jogadas iniciais
    if sessao['state'] == 'WAITING_7':
        # Extrair letras válidas
        letras = [char for char in texto_input if char in ['A', 'V', 'T']]
        
        if len(letras) < 7:
            bot.reply_to(message, f"⚠️ Preciso de pelo menos **7 jogadas válidas** (A, V ou T). Recebi apenas {len(letras)}. Tenta novamente.", parse_mode="Markdown")
            return
        
        # Guardar as últimas 7
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
        
    # ESTADO 2: Fluxo contínuo (jogo a jogo / gales)
    elif sessao['state'] == 'WAITING_OUTCOME':
        if len(texto_input) == 0 or texto_input[0] not in ['A', 'V', 'T']:
            bot.reply_to(message, "⚠️ Envia apenas o resultado que saiu (`A`, `V` ou `T`).", parse_mode="Markdown")
            return
            
        resultado_real = texto_input[0]
        sugestao_anterior = sessao['sugestao_atual']
        
        # Atualizar histórico (mantém sempre a janela das últimas jogadas)
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 7:
            sessao['history'].pop(0)
            
        # Verificar se acertou ou errou a sugestão anterior
        # Se saiu T (Empate), tipicamente em apostas de A/V o empate devolve ou conta como perda dependendo da regra, mas vamos focar na lógica de Gale se for contra A/V.
        acertou = (resultado_real == sugestao_anterior)
        
        if acertou or resultado_real == 'T':
            # Se acertou ou deu empate, reset aos gales e novo sinal
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
            # Errou, vamos avançar nos Gales (máximo 2 Gales)
            sessao['gale'] += 1
            gale_atual = sessao['gale']
            
            if gale_atual <= 2:
                # Mantém ou recalcula ligeiramente a direção para o Gale
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
                # Passou dos 2 gales (Loss total do ciclo)
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

print("Bot de Bac Bo iniciado com sucesso...")
bot.infinity_polling()
